"""Shared selection + formatting used by both CLI and TUI (one behavior, two surfaces)."""

from __future__ import annotations

from .config import Config
from .model import Project, age_label, horizon
from .store import Store, effective


def select(cfg: Config, store: Store, now: int, hz: int | None = 1, top: int | None = None,
           tracked_only: bool = False) -> list[Project]:
    tr = store.tracked()
    out = []
    for p in store.all():
        if tracked_only and p.key not in tr:
            continue
        if hz is not None and horizon(p.activity_ts, now, cfg.horizons) != hz:
            continue
        out.append(effective(p, store.latest_note(p.key)))
    out.sort(key=lambda p: (-p.activity_ts, p.key))
    n = cfg.top_n if top is None else top
    return out[:n] if n and n > 0 else out


def row(p: Project, now: int, cfg: Config, tracked: bool, width: int = 100) -> str:
    h = horizon(p.activity_ts, now, cfg.horizons)
    prog = f"{p.done}/{p.total}" if p.total else "-"
    gap = "!" if p.gaps else " "
    s = (f"{'*' if tracked else ' '}{gap} H{h or '-'} {age_label(p.activity_ts, now):>4} "
         f"{p.key[:34]:<34} {','.join(p.frameworks)[:16]:<16} {prog:>7}  "
         f"{(p.status or '-')[:28]:<28} {p.next_step}")
    return s[:width]


def detail(p: Project, now: int, cfg: Config, note: dict | None = None) -> list[str]:
    ls = [p.key, f"  path:       {p.path}",
          f"  frameworks: {', '.join(p.frameworks) or '-'}",
          f"  horizon:    H{horizon(p.activity_ts, now, cfg.horizons) or '-'}  (age {age_label(p.activity_ts, now)})",
          f"  git:        {p.branch or '-'} dirty={p.dirty} ahead={p.ahead} behind={p.behind}",
          f"  last commit:{p.last_commit_subject or '-'}",
          f"  status:     {p.status or '-'}  [{p.status_source or '-'}]",
          f"  phase:      {p.phase or '-'}   progress {p.done}/{p.total}",
          f"  next:       {p.next_step or '-'}",
          f"  gaps:       {', '.join(p.gaps) or 'none'}",
          f"  depends:    {', '.join(p.depends) or '-'}"]
    if note:
        ls.append(f"  note({note['source']}): {note['text']}")
    ls += ["  signals:"] + [f"    {s}" for s in p.signals]
    return ls


def _stats(keys, edges, comps):
    cyc = [c for c in comps if len(c) > 1]
    linked = {k for k, v in edges.items() if v} | {d for v in edges.values() for d in v}
    iso = sorted(k for k in keys if k not in linked)
    return cyc, sorted(linked), iso


def graph_lines(keys: list[str], edges: dict[str, set[str]], comps: list[list[str]],
                inferred: set[tuple[str, str]] = frozenset()) -> list[str]:
    """Plain-text dependency graph (shared by `graph` stdout and the TUI graph view).
    `a -> b` is declared; `a ~> b` is inferred from manifests."""
    cyc, linked, iso = _stats(keys, edges, comps)
    n_edges = sum(len(v) for v in edges.values())
    ls = [f"{len(keys)} projects, {n_edges} edges ({len(inferred)} inferred), {len(cyc)} cycle(s)"]
    ls += [f"cycle (collapsed): {' <-> '.join(c)}" for c in cyc]
    for k in sorted(edges):
        dec = sorted(d for d in edges[k] if (k, d) not in inferred)
        inf = sorted(d for d in edges[k] if (k, d) in inferred)
        if dec:
            ls.append(f"{k} -> {', '.join(dec)}")
        if inf:
            ls.append(f"{k} ~> {', '.join(inf)}")
    if iso:
        ls += ["", f"no dependencies ({len(iso)}):"] + [f"  {k}" for k in iso]
    return ls


def graph_markdown(keys: list[str], edges: dict[str, set[str]], comps: list[list[str]],
                   inferred: set[tuple[str, str]] = frozenset()) -> str:
    """Markdown report with a Mermaid flowchart (renders on GitHub and most viewers).
    Node ids are synthetic (n0, n1...) so arbitrary project keys cannot break the syntax."""
    cyc, linked, iso = _stats(keys, edges, comps)
    allk = linked + iso
    nid = {k: f"n{i}" for i, k in enumerate(allk)}
    in_cycle = {k for c in cyc for k in c}

    def label(k: str) -> str:
        return k.replace('"', "'").replace("<", "&lt;").replace(">", "&gt;")

    def cell(k: str) -> str:
        return f"`{k}`".replace("|", "\\|")

    n_edges = sum(len(v) for v in edges.values())
    out = ["# Dependency graph", "",
           f"{len(keys)} projects, {n_edges} edges ({len(inferred)} inferred), {len(cyc)} cycle(s). "
           "An arrow `A --> B` means A depends on B; a dashed arrow is inferred from manifests "
           "(local path dependencies in pyproject/Cargo/package.json/go.mod).", ""]
    out += ["```mermaid", "flowchart LR"]
    out += [f'  {nid[k]}["{label(k)}"]' for k in linked]
    for k in linked:
        for d in sorted(edges.get(k, ())):
            out.append(f"  {nid[k]} {'-.->' if (k, d) in inferred else '-->'} {nid[d]}")
    if iso:
        out += ['  subgraph iso["No dependencies"]', "    direction TB"]
        out += [f'    {nid[k]}["{label(k)}"]' for k in iso]
        out += ["  end"]
    if in_cycle:
        out += ["  classDef cyc stroke:#d33,stroke-width:2px;",
                "  class " + ",".join(nid[k] for k in linked if k in in_cycle) + " cyc;"]
    out += ["```", ""]
    if not linked:
        out += ["_No dependencies found (no `depends:` frontmatter or local-path manifest deps)._", ""]
    if cyc:
        out += ["## Cycles (collapsed)", ""] + [f"- {' ↔ '.join(cell(k) for k in c)}" for c in cyc] + [""]
    if linked:
        out += ["## Edges", "", "| Project | Depends on | Source |", "|---|---|---|"]
        for k in sorted(edges):
            for d in sorted(edges[k]):
                out.append(f"| {cell(k)} | {cell(d)} | {'inferred' if (k, d) in inferred else 'declared'} |")
        out.append("")
    if iso:
        out += [f"## No dependencies ({len(iso)})", ""] + [f"- {cell(k)}" for k in iso] + [""]
    return "\n".join(out)
