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


def test_track_list_is_readonly_and_auto_prune(cfg, make_repo):
    make_repo("alpha", {"docs/CHECKPOINT.md": CHECKPOINT})
    make_repo("beta")
    cli(cfg, "scan")
    cli(cfg, "track", "add", "alpha")
    assert json.loads(cli(cfg, "--json", "track", "list")) == ["alpha"]
    cli(cfg, "track", "auto", "--top", "1")  # adds, never removes
    assert len(json.loads(cli(cfg, "--json", "track", "list"))) >= 1
    cli(cfg, "track", "add", "beta")
    kept = json.loads(cli(cfg, "--json", "track", "auto", "--top", "1", "--prune"))
    assert len(kept) == 1


def test_graph_markdown_and_tui_once(cfg, make_repo):
    make_repo("a", {"CHECKPOINT.md": "---\ndepends: [b]\n---\nStatus: x\n"})
    make_repo("b", {"CHECKPOINT.md": "Status: y\n"})
    make_repo("c", {"CHECKPOINT.md": "Status: z\n"})
    cli(cfg, "scan")
    assert "a -> b" in cli(cfg, "graph") and "no dependencies" in cli(cfg, "graph")
    md = cli(cfg, "graph", "--markdown")
    assert "```mermaid" in md and "-->" in md
    assert "a -> b" in cli(cfg, "graph", "--tui", "--once")
    assert "components" in cli(cfg, "--json", "graph", "--markdown")  # --json wins
