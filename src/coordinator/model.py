"""Project record + horizon classification."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields

DAY = 86400


@dataclass
class Project:
    key: str  # path relative to scan root, e.g. "tools/coordinator"
    path: str
    name: str
    frameworks: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)  # signal files, relative
    last_commit_ts: int = 0
    last_commit_subject: str = ""
    branch: str = ""
    dirty: int = 0
    ahead: int = 0
    behind: int = 0
    signal_ts: int = 0  # newest signal-file mtime
    activity_ts: int = 0  # max(commit, signal)
    rollup_ts: int = 0  # join of own + dependencies' activity (graph.py)
    status: str = ""
    status_source: str = ""
    phase: str = ""
    next_step: str = ""
    done: int = 0
    total: int = 0
    depends: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    fingerprint: str = ""
    scanned_ts: int = 0
    is_self: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})


def horizon(ts: int, now: int, horizons: tuple[int, int, int]) -> int:
    """1/2/3 for the three horizons, 0 for dormant (older than the last)."""
    if ts <= 0:
        return 0
    age = max(0, now - ts)
    for i, days in enumerate(horizons, start=1):
        if age < days * DAY:
            return i
    return 0


def age_label(ts: int, now: int) -> str:
    if ts <= 0:
        return "-"
    age = max(0, now - ts)
    if age < 3600:
        return f"{age // 60}m"
    if age < DAY:
        return f"{age // 3600}h"
    return f"{age // DAY}d"
