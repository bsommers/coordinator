"""Dependency graph with cycle breaking.

Edges come only from authored docs (`depends:` frontmatter), never from files this
tool writes. Cycles (incl. self-dependency) are collapsed into strongly connected
components; the condensation is a DAG, so a single pass in topological order is
enough and monotone joins (max) converge without iterating to a fixpoint.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from .model import Project

MAX_MANIFEST = 1 << 20  # never read more than 1 MiB of a manifest


def build_edges(projects: list[Project]) -> dict[str, set[str]]:
    by_name: dict[str, list[str]] = {}
    for p in projects:
        by_name.setdefault(p.name, []).append(p.key)
    keys = {p.key for p in projects}
    edges: dict[str, set[str]] = {p.key: set() for p in projects}
    for p in projects:
        for d in p.depends:
            targets = [d] if d in keys else (by_name.get(d, []) if len(by_name.get(d, [])) == 1 else [])
            edges[p.key] |= {t for t in targets if t != p.key}  # drop self-edges
    return edges


def sccs(edges: dict[str, set[str]]) -> list[list[str]]:
    """Tarjan, iterative. Returned components are in reverse-topological order
    of 'depends on' edges, i.e. dependencies come first."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on: set[str] = set()
    stack: list[str] = []
    out: list[list[str]] = []
    counter = 0
    for start in sorted(edges):
        if start in index:
            continue
        work = [(start, iter(sorted(edges[start])))]
        index[start] = low[start] = counter
        counter += 1
        stack.append(start)
        on.add(start)
        while work:
            v, it = work[-1]
            advanced = False
            for w in it:
                if w not in index:
                    index[w] = low[w] = counter
                    counter += 1
                    stack.append(w)
                    on.add(w)
                    work.append((w, iter(sorted(edges.get(w, ())))))
                    advanced = True
                    break
                if w in on:
                    low[v] = min(low[v], index[w])
            if advanced:
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[v])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    on.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                out.append(sorted(comp))
    return out


def rollup(projects: list[Project]) -> list[list[str]]:
    """Set rollup_ts = max(own, deps') in one pass over the condensation.
    Returns the components (dependencies first); size>1 components are cycles."""
    by_key = {p.key: p for p in projects}
    edges = build_edges(projects)
    comps = sccs(edges)
    comp_of = {k: i for i, c in enumerate(comps) for k in c}
    val: list[int] = [0] * len(comps)
    for i, comp in enumerate(comps):  # deps precede dependents
        v = max(by_key[k].activity_ts for k in comp)
        for k in comp:
            for d in edges[k]:
                if comp_of[d] != i:
                    v = max(v, val[comp_of[d]])
        val[i] = v
    for k, i in comp_of.items():
        by_key[k].rollup_ts = val[i]
    return comps


def refresh_order(keys: list[str], projects: list[Project], self_keys: set[str]) -> list[str]:
    """Dependencies first; the tool's own repo always last (it observes, never feeds)."""
    ps = [p for p in projects if p.key in set(keys)]
    comps = sccs(build_edges(ps))
    ordered = [k for c in comps for k in c]
    return [k for k in ordered if k not in self_keys] + [k for k in ordered if k in self_keys]


# ---- inferred edges (display only; never feed rollup or refresh order) ----------------

def _read(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_MANIFEST:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _toml(path: Path) -> dict:
    try:
        return tomllib.loads(_read(path))
    except tomllib.TOMLDecodeError:
        return {}


def _toml_path_deps(doc: dict) -> list[str]:
    """Every `path = "..."` value in dependency-like tables (Cargo, uv, poetry)."""
    out: list[str] = []

    def walk(node, in_deps: bool) -> None:
        if isinstance(node, dict):
            if in_deps and isinstance(node.get("path"), str):
                out.append(node["path"])
            for k, v in node.items():
                walk(v, in_deps or "dependencies" in k or k in ("sources", "patch", "replace"))
        elif isinstance(node, list):
            for v in node:
                walk(v, in_deps)

    walk(doc, False)
    return out


def _manifest_paths(d: Path) -> list[str]:
    """Relative filesystem dependency targets declared by a project's manifests."""
    out: list[str] = []
    for name in ("pyproject.toml", "Cargo.toml"):
        if (d / name).is_file():
            out += _toml_path_deps(_toml(d / name))
    if (d / "package.json").is_file():
        try:
            pj = json.loads(_read(d / "package.json"))
        except ValueError:
            pj = {}
        for sect in ("dependencies", "devDependencies", "optionalDependencies"):
            vals = pj.get(sect) if isinstance(pj, dict) else None
            for v in (vals.values() if isinstance(vals, dict) else ()):
                if isinstance(v, str) and v.startswith(("file:", "link:")):
                    out.append(v.split(":", 1)[1])
    if (d / "go.mod").is_file():
        out += re.findall(r"=>\s*(\.{1,2}/[^\s]+)", _read(d / "go.mod"))
    return out


def infer_edges(projects: list[Project]) -> dict[str, set[str]]:
    """Edges implied by local-path dependencies in manifests (pyproject, Cargo, package.json,
    go.mod). A target resolves to the deepest scanned project containing it. Read-only."""
    roots = {}
    for p in projects:
        try:
            roots[Path(p.path).resolve()] = p.key
        except OSError:
            continue
    edges: dict[str, set[str]] = {p.key: set() for p in projects}
    for p in projects:
        base = Path(p.path)
        for rel in _manifest_paths(base):
            try:
                tgt = (base / rel).resolve()
            except (OSError, RuntimeError, ValueError):
                continue
            for cand in (tgt, *tgt.parents):
                k = roots.get(cand)
                if k:
                    if k != p.key:
                        edges[p.key].add(k)
                    break
    return edges


def full_graph(projects: list[Project]):
    """(edges, inferred_only, comps): declared + inferred edges merged. `inferred_only` is the
    set of (src, dst) pairs not backed by a declared `depends:`. Cycles are over the union."""
    declared = build_edges(projects)
    inferred = infer_edges(projects)
    merged = {k: declared[k] | inferred.get(k, set()) for k in declared}
    only = {(a, b) for a, bs in merged.items() for b in bs if b not in declared[a]}
    return merged, only, sccs(merged)
