import json
import os
import subprocess
import sys

from conftest import CHECKPOINT


def cli(cfg, *a):
    env = {**os.environ, "PYTHONPATH": "src", "COORDINATOR_HOME": str(cfg.data_dir)}
    r = subprocess.run([sys.executable, "-m", "coordinator", "--root", str(cfg.root), *a],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_end_to_end_workflow(cfg, make_repo):
    make_repo("g/alpha", {"docs/CHECKPOINT.md": CHECKPOINT})
    make_repo("beta")
    cli(cfg, "scan")
    rows = json.loads(cli(cfg, "--json", "list", "--horizon", "all", "--top", "0"))
    assert {r["key"] for r in rows} == {"g/alpha", "beta"}
    cli(cfg, "track", "auto", "--top", "5")
    assert set(json.loads(cli(cfg, "--json", "track", "list"))) == {"g/alpha", "beta"}
    cli(cfg, "refresh")
    gaps = json.loads(cli(cfg, "--json", "gaps"))
    assert gaps == [{"key": "beta", "gaps": ["no-status-doc"]}]
    cli(cfg, "note", "beta", "agent says hi", "--status", "spiking", "--next", "write tests")
    assert json.loads(cli(cfg, "--json", "show", "beta"))["status"] == "spiking"
    assert "Task:" in cli(cfg, "brief", "beta")
    assert "alpha" in cli(cfg, "tui", "--once")
