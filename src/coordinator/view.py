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


def graph_lines(n_projects: int, edges: dict[str, set[str]], comps: list[list[str]]) -> list[str]:
    """Plain-text dependency graph (shared by `graph` stdout and the TUI graph view)."""
    cyc = [c for c in comps if len(c) > 1]
    ls = [f"{n_projects} projects, {sum(len(v) for v in edges.values())} edges, {len(cyc)} cycle(s)"]
    ls += [f"cycle (collapsed): {' <-> '.join(c)}" for c in cyc]
    ls += [f"{k} -> {', '.join(sorted(v))}" for k, v in sorted(edges.items()) if v]
    return ls


def graph_markdown(n_projects: int, edges: dict[str, set[str]], comps: list[list[str]]) -> str:
    """Markdown report with a Mermaid flowchart (renders on GitHub and most viewers).
    Node ids are synthetic (n0, n1...) so arbitrary project keys cannot break the syntax."""
    cyc = [c for c in comps if len(c) > 1]
    nodes = sorted({k for k, v in edges.items() if v} | {d for v in edges.values() for d in v})
    nid = {k: f"n{i}" for i, k in enumerate(nodes)}
    in_cycle = {k for c in cyc for k in c}

    def label(k: str) -> str:
        return k.replace('"', "'").replace("<", "&lt;").replace(">", "&gt;")

    out = ["# Dependency graph", "",
           f"{n_projects} projects, {sum(len(v) for v in edges.values())} edges, {len(cyc)} cycle(s). "
           "An arrow `A --> B` means A depends on B.", ""]
    if not nodes:
        return "\n".join(out + ["_No dependencies declared (`depends:` frontmatter)._", ""])
    out += ["```mermaid", "flowchart LR"]
    out += [f'  {nid[k]}["{label(k)}"]' for k in nodes]
    out += [f"  {nid[k]} --> {nid[d]}" for k in nodes for d in sorted(edges.get(k, ()))]
    if in_cycle:
        out += ["  classDef cyc stroke:#d33,stroke-width:2px;",
                "  class " + ",".join(nid[k] for k in nodes if k in in_cycle) + " cyc;"]
    out += ["```", ""]
    if cyc:
        out += ["## Cycles (collapsed)", ""] + [f"- {' ↔ '.join(f'`{k}`' for k in c)}" for c in cyc] + [""]
    out += ["## Edges", "", "| Project | Depends on |", "|---|---|"]
    out += [f"| `{k}` | {', '.join(f'`{d}`' for d in sorted(edges[k]))} |"
            for k in sorted(edges) if edges[k]]
    return "\n".join(out) + "\n"
