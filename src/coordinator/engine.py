"""Scan / refresh orchestration, with a re-entrancy + single-writer lock."""

from __future__ import annotations

import contextlib
import fcntl
import os
import time
from pathlib import Path

from . import export, graph
from .config import Config
from .scan import discover, scan_project, self_root
from .store import Store

ACTIVE_ENV = "COORDINATOR_ACTIVE"


class Busy(RuntimeError):
    pass


@contextlib.contextmanager
def lock(cfg: Config):
    """One run at a time, and never re-entrant: a hook inside a tracked repo that
    calls us while we are running exits instead of looping."""
    if os.environ.get(ACTIVE_ENV):
        raise Busy("re-entrant call (COORDINATOR_ACTIVE set)")
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    fh = open(cfg.data_dir / ".lock", "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        fh.close()
        raise Busy("another coordinator run holds the lock") from None
    os.environ[ACTIVE_ENV] = "1"
    try:
        yield
    finally:
        os.environ.pop(ACTIVE_ENV, None)
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


def _rollup_and_save(store: Store) -> None:
    projs = store.all()
    graph.rollup(projs)
    for p in projs:
        store.put(p)


def scan(cfg: Config, store: Store, full: bool = False, now: int | None = None) -> dict:
    """Discover repos; re-parse only those whose fingerprint changed (unless full)."""
    now = now or int(time.time())
    old = {p.key: p for p in store.all()}
    seen: set[str] = set()
    n_new = n_changed = n_same = 0
    for path in discover(cfg):
        key = str(path.relative_to(cfg.root))
        seen.add(key)
        prev = old.get(key)
        if prev and not full:
            from .scan import fingerprint
            if fingerprint(path, prev.signals) == prev.fingerprint:
                n_same += 1
                continue
        store.put(scan_project(path, cfg, now))
        if prev:
            n_changed += 1
        else:
            n_new += 1
    removed = store.delete_except(seen)
    _rollup_and_save(store)
    store.commit()
    return {"found": len(seen), "new": n_new, "changed": n_changed, "unchanged": n_same,
            "removed": removed}


def refresh(cfg: Config, store: Store, now: int | None = None) -> dict:
    """Re-scan the tracked set (always), then regenerate the status repo."""
    now = now or int(time.time())
    projs = {p.key: p for p in store.all()}
    tracked = [k for k in store.tracked() if k in projs]
    sr = self_root()
    self_keys = {k for k in tracked if projs[k].is_self or (sr and Path(projs[k].path).resolve() == sr)}
    order = graph.refresh_order(tracked, list(projs.values()), self_keys)
    for key in order:  # single pass; the tool's own repo is last
        path = Path(projs[key].path)
        if path.is_dir():
            store.put(scan_project(path, cfg, now))
    _rollup_and_save(store)
    store.commit()
    committed = export.write(cfg, store)
    return {"refreshed": len(order), "status_repo_committed": committed}
