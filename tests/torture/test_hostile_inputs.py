import os

from coordinator import engine
from coordinator.store import Store
from conftest import CHECKPOINT


def test_binary_huge_and_unreadable_signal_files(cfg, make_repo):
    p = make_repo("a", {"CHECKPOINT.md": CHECKPOINT})
    (p / "STATUS.md").write_bytes(os.urandom(4096))
    (p / "docs").mkdir(exist_ok=True)
    (p / "docs/HANDOFF.md").write_text("Status: x\n" + "y" * (5 * 1024 * 1024))
    (p / "docs/STATUS.md").write_text("x")
    os.chmod(p / "docs/STATUS.md", 0)
    engine.scan(cfg, Store(cfg.db_path), full=True)


def test_symlink_loop_and_cyclic_depends(cfg, make_repo):
    make_repo("a", {"CHECKPOINT.md": "---\ndepends: [b]\n---\nStatus: x\n"})
    make_repo("b", {"CHECKPOINT.md": "---\ndepends: [a, a, nope]\n---\nStatus: y\n"})
    os.symlink(cfg.root, cfg.root / "loop")
    st = Store(cfg.db_path)
    engine.scan(cfg, st)
    assert {p.key for p in st.all()} == {"a", "b"}
