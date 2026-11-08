import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ.pop("COORDINATOR_ACTIVE", None)


def git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                   check=True, capture_output=True)


@pytest.fixture
def make_repo(tmp_path):
    """make_repo('grp/proj', {'docs/CHECKPOINT.md': '...'}, commit=True) under tmp_path/src."""
    def _make(rel: str, files: dict[str, str] | None = None, commit: bool = True) -> Path:
        p = tmp_path / "src" / rel
        p.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(p)], check=True)
        for name, text in (files or {}).items():
            f = p / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text)
        if commit:
            (p / "README.md").write_text("x")
            git(p, "add", "-A")
            git(p, "commit", "-q", "-m", "init")
        return p
    return _make


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    from coordinator.config import Config
    (tmp_path / "src").mkdir(exist_ok=True)
    monkeypatch.setenv("COORDINATOR_HOME", str(tmp_path / "data"))
    return Config(root=(tmp_path / "src").resolve(), data_dir=tmp_path / "data")


CHECKPOINT = """# Checkpoint
**Status:** IN PROGRESS — needs resume
## Next steps
1. `pytest -q`
2. ship
"""
