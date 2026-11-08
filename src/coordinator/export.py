"""Status repo: deterministic markdown snapshots of the tracked set, in a local git
repo under the data dir. No timestamps-of-generation, so commits happen only on change."""

from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone

from .config import Config
from .store import Store, effective

GIT = ["git", "-c", "user.name=coordinator", "-c", "user.email=coordinator@localhost"]


def _day(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d") if ts else "-"


def project_md(p) -> str:
    lines = [f"# {p.key}", "",
             f"- frameworks: {', '.join(p.frameworks) or '-'}",
             f"- branch: {p.branch or '-'}  dirty: {p.dirty}  ahead/behind: {p.ahead}/{p.behind}",
             f"- last activity: {_day(p.activity_ts)}  last commit: {_day(p.last_commit_ts)} "
             f"{p.last_commit_subject}",
             f"- status: {p.status or '-'}  (source: {p.status_source or '-'})",
             f"- phase: {p.phase or '-'}  progress: {p.done}/{p.total}",
             f"- next: {p.next_step or '-'}",
             f"- gaps: {', '.join(p.gaps) or 'none'}",
             f"- depends: {', '.join(p.depends) or '-'}", "", "## Signal files", ""]
    lines += [f"- {s}" for s in p.signals] or ["- (none)"]
    return "\n".join(lines) + "\n"


def write(cfg: Config, store: Store) -> bool:
    d = cfg.status_dir
    (d / "projects").mkdir(parents=True, exist_ok=True)
    if not (d / ".git").exists():
        subprocess.run(["git", "init", "-q", "-b", "main", str(d)], check=True)
    tracked = store.tracked()
    projs = sorted((effective(p, store.latest_note(p.key)) for p in store.all() if p.key in tracked),
                   key=lambda p: p.key)
    want = set()
    rows = ["# Tracked projects", "", "| project | status | next | gaps | last activity |",
            "|---|---|---|---|---|"]
    for p in projs:
        fn = p.key.replace("/", "__") + ".md"
        want.add(fn)
        (d / "projects" / fn).write_text(project_md(p))
        rows.append(f"| [{p.key}](projects/{fn}) | {p.status or '-'} | {p.next_step or '-'} | "
                    f"{','.join(p.gaps) or '-'} | {_day(p.activity_ts)} |")
    for f in (d / "projects").glob("*.md"):
        if f.name not in want:
            f.unlink()
    (d / "INDEX.md").write_text("\n".join(rows).replace("\n", "\n") + "\n")
    if not cfg.auto_commit:
        return False
    subprocess.run(GIT + ["-C", str(d), "add", "-A"], check=True, capture_output=True)
    if subprocess.run(GIT + ["-C", str(d), "diff", "--cached", "--quiet"]).returncode == 0:
        return False
    subprocess.run(GIT + ["-C", str(d), "commit", "-q", "-m",
                          f"refresh {time.strftime('%Y-%m-%d %H:%M')} ({len(projs)} tracked)"],
                   check=True, capture_output=True)
    return True
