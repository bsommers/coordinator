import os
import subprocess

import pytest

from coordinator import engine
from coordinator.scan import discover
from coordinator.store import Store
from conftest import CHECKPOINT, git


def test_discover_nested_and_skips_ignored(cfg, make_repo):
    make_repo("grp/one"); make_repo("two")
    (cfg.root / "node_modules" / "pkg" / ".git").mkdir(parents=True)
    names = sorted(str(p.relative_to(cfg.root)) for p in discover(cfg))
    assert names == ["grp/one", "two"]


def test_scan_incremental_and_full(cfg, make_repo):
    p = make_repo("a", {"docs/CHECKPOINT.md": CHECKPOINT})
    st = Store(cfg.db_path)
    assert engine.scan(cfg, st)["new"] == 1
    assert engine.scan(cfg, st)["unchanged"] == 1
    (p / "docs/CHECKPOINT.md").write_text(CHECKPOINT.replace("IN PROGRESS", "COMPLETE"))
    r = engine.scan(cfg, st)
    assert r["changed"] == 1 and st.resolve("a").status.startswith("COMPLETE")
    assert engine.scan(cfg, st, full=True)["changed"] == 1


def test_new_signal_file_detected(cfg, make_repo):
    p = make_repo("a")
    st = Store(cfg.db_path)
    engine.scan(cfg, st)
    assert "no-status-doc" in st.resolve("a").gaps
    (p / "STATUS.md").write_text("Status: ok\n")
    assert engine.scan(cfg, st)["changed"] == 1


def test_refresh_writes_status_repo_only_on_change(cfg, make_repo):
    make_repo("a", {"CHECKPOINT.md": CHECKPOINT})
    st = Store(cfg.db_path)
    engine.scan(cfg, st); st.track("a"); st.commit()
    assert engine.refresh(cfg, st)["status_repo_committed"] is True
    assert engine.refresh(cfg, st)["status_repo_committed"] is False
    assert (cfg.status_dir / "projects/a.md").is_file()
    log = subprocess.run(["git", "-C", str(cfg.status_dir), "log", "--oneline"], capture_output=True, text=True)
    assert len(log.stdout.splitlines()) == 1


def test_scan_does_not_touch_repo_index(cfg, make_repo):
    p = make_repo("a")
    (p / "dirty.txt").write_text("d")
    before = (p / ".git/index").stat().st_mtime_ns
    engine.scan(cfg, Store(cfg.db_path))
    assert (p / ".git/index").stat().st_mtime_ns == before


def test_data_dir_inside_root_is_ignored(cfg, make_repo):
    from dataclasses import replace
    make_repo("a")
    inner = replace(cfg, data_dir=cfg.root / "data")
    (inner.data_dir / "status").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(inner.data_dir / "status")], check=True)
    assert [p.name for p in discover(inner)] == ["a"]


def test_lock_blocks_reentry(cfg, monkeypatch):
    with engine.lock(cfg):
        with pytest.raises(engine.Busy):
            with engine.lock(cfg):
                pass
    with engine.lock(cfg):  # released afterwards
        pass
    assert "COORDINATOR_ACTIVE" not in os.environ


def test_self_repo_refreshed_last(cfg, make_repo, monkeypatch):
    a = make_repo("a", {"CHECKPOINT.md": CHECKPOINT})
    b = make_repo("zz-self", {"CHECKPOINT.md": CHECKPOINT})
    monkeypatch.setattr("coordinator.scan.self_root", lambda: b.resolve())
    monkeypatch.setattr("coordinator.engine.self_root", lambda: b.resolve())
    st = Store(cfg.db_path)
    engine.scan(cfg, st)
    for k in ("a", "zz-self"):
        st.track(k)
    st.commit()
    seen = []
    import coordinator.engine as E
    real = E.scan_project
    monkeypatch.setattr(E, "scan_project", lambda path, c, now=None: (seen.append(path.name), real(path, c, now))[1])
    engine.refresh(cfg, st)
    assert seen[-1] == "zz-self"
