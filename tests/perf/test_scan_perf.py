import time

from coordinator import engine
from coordinator.store import Store


def test_incremental_scan_of_many_repos_is_fast(cfg, make_repo):
    for i in range(40):
        make_repo(f"g{i % 4}/p{i}", {"CHECKPOINT.md": "Status: x\n"})
    st = Store(cfg.db_path)
    engine.scan(cfg, st)
    t = time.time()
    r = engine.scan(cfg, st)
    assert r["unchanged"] == 40 and time.time() - t < 3
