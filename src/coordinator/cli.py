"""coordinator CLI. Every capability here is also reachable from the TUI (tui.py)."""

from __future__ import annotations

import argparse
import json
import sys
import time

from . import engine, graph, view
from .config import Config, config_file, load
from .model import horizon
from .store import Store

HZ = {"1": 1, "2": 2, "3": 3, "all": None}


def _store(cfg: Config) -> Store:
    return Store(cfg.db_path)


def _need(store: Store, name: str):
    try:
        p = store.resolve(name)
    except LookupError as e:
        sys.exit(str(e))
    if not p:
        sys.exit(f"unknown project '{name}' (try: coordinator scan; coordinator list --horizon all)")
    return p


def _emit(args, payload, lines: list[str]) -> None:
    print(json.dumps(payload, indent=2) if args.json else "\n".join(lines))


def cmd_paths(cfg, args):
    info = {"root": str(cfg.root), "data_dir": str(cfg.data_dir), "db": str(cfg.db_path),
            "status_repo": str(cfg.status_dir), "config_file": str(config_file()),
            "horizons_days": list(cfg.horizons)}
    _emit(args, info, [f"{k:13} {v}" for k, v in info.items()])


def cmd_scan(cfg, args):
    with engine.lock(cfg):
        st = _store(cfg)
        res = engine.scan(cfg, st, full=args.full)
    _emit(args, res, [", ".join(f"{k}={v}" for k, v in res.items())])


def cmd_list(cfg, args):
    st = _store(cfg)
    now = int(time.time())
    hz = HZ[args.horizon]
    ps = view.select(cfg, st, now, hz, args.top, args.tracked)
    tr = st.tracked()
    _emit(args, [p.to_dict() | {"tracked": p.key in tr} for p in ps],
          [view.row(p, now, cfg, p.key in tr, 200) for p in ps] or ["(none — run: coordinator scan)"])


def cmd_show(cfg, args):
    st = _store(cfg)
    p = _need(st, args.name)
    from .store import effective
    note = st.latest_note(p.key)
    q = effective(p, note)
    _emit(args, q.to_dict() | {"note": note}, view.detail(q, int(time.time()), cfg, note))


def cmd_track(cfg, args):
    st = _store(cfg)
    now = int(time.time())
    if args.action == "add":
        for n in args.names:
            st.track(_need(st, n).key)
    elif args.action == "rm":
        for n in args.names:
            st.untrack(_need(st, n).key)
    elif args.action == "clear":
        st.set_tracked(set())
    elif args.action == "auto":  # add the top-n most recent H1 projects
        top = view.select(cfg, st, now, 1, args.top)
        if args.prune:  # drop tracked projects that are no longer in the H1 set
            st.set_tracked({p.key for p in top})
        for p in top:
            st.track(p.key)
    st.commit()
    keys = sorted(st.tracked())
    _emit(args, keys, keys or ["(no tracked projects)"])


def cmd_refresh(cfg, args):
    with engine.lock(cfg):
        st = _store(cfg)
        res = engine.refresh(cfg, st)
    _emit(args, res, [", ".join(f"{k}={v}" for k, v in res.items())])


def cmd_watch(cfg, args):
    n = 0
    print(f"watching every {args.interval}s (full scan every {args.full_every} cycles); ctrl-c to stop")
    try:
        while True:
            try:
                with engine.lock(cfg):
                    st = _store(cfg)
                    s = engine.scan(cfg, st, full=(n % args.full_every == 0))
                    r = engine.refresh(cfg, st)
                print(time.strftime("%H:%M:%S"), s, r, flush=True)
            except engine.Busy as e:
                print("skipped:", e, flush=True)
            n += 1
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return


def cmd_gaps(cfg, args):
    st = _store(cfg)
    ps = [p for p in view.select(cfg, st, int(time.time()), None, 0, not args.all) if p.gaps]
    _emit(args, [{"key": p.key, "gaps": p.gaps} for p in ps],
          [f"{p.key:40} {','.join(p.gaps)}" for p in ps] or ["no gaps"])


def cmd_brief(cfg, args):
    """Compact fact pack for an agent session to fill gaps. No LLM is called here."""
    st = _store(cfg)
    from .store import effective
    base = _need(st, args.name)
    p = effective(base, st.latest_note(base.key))
    lines = ["# Coordinator brief — fill the gaps, then record the result", ""]
    lines += view.detail(p, int(time.time()), cfg)
    lines += ["", "Task: read the signal files above plus `git log -10 --oneline` in the project path.",
              "For each gap, determine the true state. Prefer updating the project's own",
              "docs/CHECKPOINT.md (with a `**Status:**` line and `## Next steps`); otherwise record:",
              f"  coordinator note {p.key} --status '<one line>' --next '<exact next command>' 'why'"]
    print("\n".join(lines))


def cmd_note(cfg, args):
    st = _store(cfg)
    p = _need(st, args.name)
    st.add_note(p.key, args.text, args.status or "", args.next or "", args.source)
    print(f"noted {p.key}")


def cmd_graph(cfg, args):
    if args.tui:
        from . import tui
        tui.run(cfg, once=args.once, graph=True)
        return
    projs = _store(cfg).all()
    edges, inferred, comps = graph.full_graph(projs)
    keys = sorted(p.key for p in projs)
    payload = {"components": comps, "cycles": [c for c in comps if len(c) > 1],
               "edges": {k: sorted(v) for k, v in edges.items() if v},
               "inferred": sorted([a, b] for a, b in inferred),
               "isolated": view._stats(keys, edges, comps)[2]}
    if args.markdown and not args.json:
        print(view.graph_markdown(keys, edges, comps, inferred), end="")
        return
    _emit(args, payload, view.graph_lines(keys, edges, comps, inferred))


def cmd_tui(cfg, args):
    from . import tui
    tui.run(cfg, once=args.once, hz=HZ[args.horizon])


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="coordinator", description=__doc__)
    ap.add_argument("--root", help="scan root (default: ~/src or config)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        sp = sub.add_parser(name, help=help_)
        sp.set_defaults(fn=fn)
        return sp

    add("paths", cmd_paths, "show resolved paths and settings")
    sp = add("scan", cmd_scan, "discover repos and index them (incremental by default)")
    sp.add_argument("--full", action="store_true", help="re-parse everything")
    sp = add("list", cmd_list, "list projects by horizon (default: H1, top N)")
    sp.add_argument("--horizon", choices=list(HZ), default="1")
    sp.add_argument("--top", type=int, help="limit (0 = all)")
    sp.add_argument("--tracked", action="store_true")
    sp = add("show", cmd_show, "full detail for one project")
    sp.add_argument("name")
    sp = add("track", cmd_track, "manage the active tracking set")
    sp.add_argument("action", choices=["add", "rm", "list", "clear", "auto"])
    sp.add_argument("names", nargs="*")
    sp.add_argument("--top", type=int, help="for 'auto': how many H1 projects")
    sp.add_argument("--prune", action="store_true",
                    help="for 'auto': also untrack projects outside the selected H1 set")
    add("refresh", cmd_refresh, "re-scan tracked projects and update the status repo")
    sp = add("watch", cmd_watch, "scan + refresh on an interval")
    sp.add_argument("--interval", type=int, default=300)
    sp.add_argument("--full-every", type=int, default=12)
    sp = add("gaps", cmd_gaps, "projects whose status is missing/stale (agent work list)")
    sp.add_argument("--all", action="store_true", help="not only tracked")
    sp = add("brief", cmd_brief, "fact pack to hand to an agent session for one project")
    sp.add_argument("name")
    sp = add("note", cmd_note, "record an agent-supplied status/next step (until docs update)")
    sp.add_argument("name")
    sp.add_argument("text")
    sp.add_argument("--status")
    sp.add_argument("--next")
    sp.add_argument("--source", default="agent")
    sp = add("graph", cmd_graph, "dependency graph, cycles collapsed (stdout, --markdown, or --tui)")
    sp.add_argument("--markdown", action="store_true", help="render a Markdown report with a Mermaid diagram")
    sp.add_argument("--tui", action="store_true", help="show in the interactive terminal UI")
    sp.add_argument("--once", action="store_true", help="with --tui: print one frame and exit")
    sp = add("tui", cmd_tui, "interactive terminal UI")
    sp.add_argument("--once", action="store_true", help="print one frame and exit")
    sp.add_argument("--horizon", choices=list(HZ), default="1")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load(args.root)
    try:
        args.fn(cfg, args)
    except engine.Busy as e:
        print(f"coordinator: {e}", file=sys.stderr)
        return 0 if "re-entrant" in str(e) else 3
    return 0
