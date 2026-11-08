import subprocess
import sys


def run(*a, env=None):
    return subprocess.run([sys.executable, "-m", "coordinator", *a], capture_output=True, text=True,
                          env=env)


def test_help_lists_commands(tmp_path):
    import os
    env = {**os.environ, "PYTHONPATH": "src", "COORDINATOR_HOME": str(tmp_path)}
    r = run("--help", env=env)
    assert r.returncode == 0
    for c in ("scan", "list", "track", "refresh", "gaps", "brief", "graph", "tui"):
        assert c in r.stdout


def test_paths_json(tmp_path):
    import json, os
    env = {**os.environ, "PYTHONPATH": "src", "COORDINATOR_HOME": str(tmp_path / "d")}
    r = run("--json", "paths", env=env)
    assert json.loads(r.stdout)["data_dir"] == str(tmp_path / "d")
