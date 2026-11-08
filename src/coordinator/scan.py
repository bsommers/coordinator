"""Discovery + per-project scan. Pure reads: never writes into scanned repos."""

from __future__ import annotations

import hashlib
import os
import subprocess
import time
from pathlib import Path

from . import adapters
from .config import Config
from .model import DAY, Project

MARKERS = (".git", ".planning", ".specify", "openspec", ".kiro")
GIT_ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C"}  # no opportunistic index writes


def self_root() -> Path | None:
    """Repo root of this tool, if running from a checkout (for self-tracking guards)."""
    p = Path(__file__).resolve().parents[2]
    return p if (p / "pyproject.toml").is_file() else None


def discover(cfg: Config) -> list[Path]:
    """Find project roots under cfg.root. A project root is not descended into."""
    found: list[Path] = []
    data = cfg.data_dir.resolve()
    root = cfg.root
    if not root.is_dir():
        return found
    for cur, dirs, _files in os.walk(root, followlinks=False):
        here = Path(cur)
        depth = len(here.relative_to(root).parts)
        if here.resolve() == data or data in here.resolve().parents:
            dirs[:] = []
            continue
        if any((here / m).exists() for m in MARKERS) and here != root:
            found.append(here)
            dirs[:] = []
            continue
        if depth >= cfg.max_depth:
            dirs[:] = []
            continue
        dirs[:] = sorted(d for d in dirs if d not in cfg.ignore and not d.startswith(".")
                         and not (here / d).is_symlink())
    return found


def _mtime(p: Path) -> int:
    try:
        return int(p.stat().st_mtime)
    except OSError:
        return 0


def _mtime_ns(p: Path) -> int:
    try:
        return p.stat().st_mtime_ns
    except OSError:
        return 0


def fingerprint(path: Path, signals: list[str]) -> str:
    """Cheap change detector: signal-file stats + git HEAD/index/reflog mtimes."""
    h = hashlib.sha1()
    for rel in sorted(signals):
        try:
            st = (path / rel).stat()
            h.update(f"{rel}:{st.st_mtime_ns}:{st.st_size}\n".encode())
        except OSError:
            h.update(f"{rel}:gone\n".encode())
    for d in (".", "docs", ".planning", ".specify", "specs", "openspec", ".superpowers"):
        h.update(f"dir/{d}:{_mtime_ns(path / d)}\n".encode())  # new/removed signal files
    g = path / ".git"
    for rel in ("HEAD", "index", "logs/HEAD"):
        h.update(f"git/{rel}:{_mtime_ns(g / rel)}\n".encode())
    return h.hexdigest()[:16]


def _git(path: Path, *args: str) -> str:
    try:
        r = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True,
                           timeout=15, env=GIT_ENV)
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def git_info(path: Path) -> dict:
    info = {"last_commit_ts": 0, "last_commit_subject": "", "branch": "", "dirty": 0,
            "ahead": 0, "behind": 0}
    if not (path / ".git").exists():
        return info
    log = _git(path, "log", "-1", "--format=%ct%x09%s").strip()
    if "\t" in log:
        ts, subj = log.split("\t", 1)
        info["last_commit_ts"] = int(ts)
        info["last_commit_subject"] = subj[:120]
    out = _git(path, "status", "--porcelain=v1", "-b").splitlines()
    if out and out[0].startswith("## "):
        head = out[0][3:]
        info["branch"] = head.split("...")[0].split(" ")[0]
        if "[" in head:
            for part in head[head.index("[") + 1:].rstrip("]").split(","):
                part = part.strip()
                if part.startswith("ahead "):
                    info["ahead"] = int(part[6:])
                elif part.startswith("behind "):
                    info["behind"] = int(part[7:])
        info["dirty"] = len(out) - 1
    return info


def compute_gaps(p: Project, now: int, stale_days: int) -> list[str]:
    """Deterministic status gaps: the only place an agent/LLM is worth invoking."""
    gaps: list[str] = []
    if not p.signals:
        gaps.append("no-status-doc")
        return gaps
    if not p.status:
        gaps.append("no-status-line")
    if not p.next_step and not (p.total and p.done >= p.total):
        gaps.append("no-next-step")
    if p.last_commit_ts and p.signal_ts and p.last_commit_ts - p.signal_ts > stale_days * DAY:
        gaps.append("stale-status")
    return gaps


def scan_project(path: Path, cfg: Config, now: int | None = None) -> Project:
    now = now or int(time.time())
    facts = adapters.detect(path)
    signals = sorted({f for fc in facts for f in fc.files})
    p = Project(key=str(path.relative_to(cfg.root)), path=str(path), name=path.name,
                frameworks=[fc.framework for fc in facts], signals=signals)
    p.__dict__.update(git_info(path))
    p.signal_ts = max((_mtime(path / s) for s in signals), default=0)
    p.activity_ts = max(p.last_commit_ts, p.signal_ts)

    # status/next: newest status-bearing file wins; phase/progress: first adapter that has them
    best = ""
    for fc in facts:
        if fc.status and (not best or _mtime(path / fc.status_file) > _mtime(path / best)):
            best, p.status, p.status_source = fc.status_file, fc.status, fc.framework
    cps = [fc for fc in facts if fc.framework == "checkpoint" and fc.next_step]
    if cps:
        p.next_step = cps[0].next_step
    for fc in facts:
        if not p.phase and fc.phase:
            p.phase = fc.phase
        if not p.total and fc.total:
            p.done, p.total = fc.done, fc.total
        if not p.next_step and fc.next_step:
            p.next_step = fc.next_step
        p.depends += [d for d in fc.depends if d not in p.depends]
    sr = self_root()
    p.is_self = bool(sr and path.resolve() == sr)
    p.fingerprint = fingerprint(path, signals)
    p.scanned_ts = now
    p.gaps = compute_gaps(p, now, cfg.stale_days)
    return p
