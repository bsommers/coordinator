"""Curses TUI (stdlib only). Rendering is a pure function so it is testable."""

from __future__ import annotations

import curses
import time

from . import engine, graph, view
from .config import Config
from .store import Store

HELP = "j/k move  g graph  1/2/3/a horizon  t track  r refresh  s scan  enter detail  q quit"


def frame(cfg: Config, store: Store, hz: int | None, sel: int, now: int, width: int,
          height: int, detail: bool, show_graph: bool = False) -> list[str]:
    if show_graph:
        projs = store.all()
        comps = graph.rollup(projs)
        gl = view.graph_lines(len(projs), graph.build_edges(projs), comps)
        body = height - 3
        off = max(0, min(sel, len(gl) - body))
        return (["coordinator  graph  (j/k scroll  g back  q quit)"[:width], "-" * min(width, 100)]
                + [l[:width] for l in gl[off:off + body]])
    ps = view.select(cfg, store, now, hz, 0)
    tr = store.tracked()
    label = "all" if hz is None else f"H{hz}"
    out = [f"coordinator  {label}  {len(ps)} projects  {len(tr)} tracked  root={cfg.root}"[:width],
           HELP[:width], "-" * min(width, 100)]
    body = height - len(out) - 1
    if detail and ps:
        out += [l[:width] for l in view.detail(ps[sel], now, cfg, store.latest_note(ps[sel].key))][:body]
    else:
        top = max(0, min(sel - body + 1, len(ps) - body)) if sel >= body else 0
        for i, p in enumerate(ps[top:top + body], start=top):
            out.append((">" if i == sel else " ") + view.row(p, now, cfg, p.key in tr, width - 1))
        if not ps:
            out.append("(no projects in this horizon — press s to scan)")
    return out


def _loop(scr, cfg: Config, hz: int | None, graph_mode: bool = False) -> None:
    curses.curs_set(0)
    store = Store(cfg.db_path)
    sel, detail, msg = 0, False, ""
    show_graph = graph_mode
    while True:
        h, w = scr.getmaxyx()
        now = int(time.time())
        ps = view.select(cfg, store, now, hz, 0)
        sel = max(0, sel) if show_graph else max(0, min(sel, len(ps) - 1))
        scr.erase()
        lines = frame(cfg, store, hz, sel, now, w, h, detail, show_graph)
        for y, l in enumerate(lines[:h - 1]):
            scr.addnstr(y, 0, l, w - 1)
        scr.addnstr(h - 1, 0, msg, w - 1)
        scr.refresh()
        k = scr.getkey()
        msg = ""
        if k in ("q", "Q"):
            return
        elif k in ("j", "KEY_DOWN"):
            sel += 1
        elif k in ("k", "KEY_UP"):
            sel -= 1
        elif k == "g":
            show_graph, sel = not show_graph, 0
        elif k in ("1", "2", "3"):
            hz, sel = int(k), 0
        elif k == "a":
            hz, sel = None, 0
        elif k in ("\n", "KEY_ENTER"):
            detail = not detail
        elif k == "t" and ps:
            (store.untrack if ps[sel].key in store.tracked() else store.track)(ps[sel].key)
            store.commit()
        elif k in ("r", "s"):
            try:
                with engine.lock(cfg):
                    msg = str(engine.scan(cfg, store, full=False) if k == "s" else engine.refresh(cfg, store))
            except engine.Busy as e:
                msg = str(e)


def run(cfg: Config, once: bool = False, hz: int | None = 1, graph: bool = False) -> None:
    if once:
        store = Store(cfg.db_path)
        print("\n".join(frame(cfg, store, hz, 0, int(time.time()), 140, 40, False, graph)))
        return
    curses.wrapper(_loop, cfg, hz, graph)
