"""SQLite index (local only) of scanned projects, tracking set, notes."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .model import Project

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects(key TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tracked(key TEXT PRIMARY KEY, added_ts INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY, key TEXT NOT NULL, ts INTEGER NOT NULL,
  source TEXT NOT NULL, status TEXT, next_step TEXT, text TEXT);
"""


class Store:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    # projects
    def all(self) -> list[Project]:
        return [Project.from_dict(json.loads(r[0])) for r in self.db.execute("SELECT data FROM projects")]

    def put(self, p: Project) -> None:
        self.db.execute("INSERT OR REPLACE INTO projects(key,data) VALUES(?,?)",
                        (p.key, json.dumps(p.to_dict())))

    def delete_except(self, keys: set[str]) -> int:
        gone = [p.key for p in self.all() if p.key not in keys]
        for k in gone:
            self.db.execute("DELETE FROM projects WHERE key=?", (k,))
            self.db.execute("DELETE FROM tracked WHERE key=?", (k,))
        return len(gone)

    def commit(self) -> None:
        self.db.commit()

    def resolve(self, name: str) -> Project | None:
        """Look up by exact key, else by unique basename."""
        projs = self.all()
        for p in projs:
            if p.key == name:
                return p
        hits = [p for p in projs if p.name == name]
        if len(hits) > 1:
            raise LookupError(f"ambiguous '{name}': " + ", ".join(p.key for p in hits))
        return hits[0] if hits else None

    # tracking
    def tracked(self) -> set[str]:
        return {r[0] for r in self.db.execute("SELECT key FROM tracked")}

    def track(self, key: str) -> None:
        self.db.execute("INSERT OR IGNORE INTO tracked VALUES(?,?)", (key, int(time.time())))

    def untrack(self, key: str) -> None:
        self.db.execute("DELETE FROM tracked WHERE key=?", (key,))

    def set_tracked(self, keys: set[str]) -> None:
        self.db.execute("DELETE FROM tracked")
        for k in sorted(keys):
            self.track(k)

    # notes (agent-written overrides)
    def add_note(self, key: str, text: str, status: str = "", next_step: str = "",
                 source: str = "agent") -> None:
        self.db.execute("INSERT INTO notes(key,ts,source,status,next_step,text) VALUES(?,?,?,?,?,?)",
                        (key, int(time.time()), source, status, next_step, text))
        self.db.commit()

    def latest_note(self, key: str) -> dict | None:
        r = self.db.execute("SELECT ts,source,status,next_step,text FROM notes WHERE key=? "
                            "ORDER BY id DESC LIMIT 1", (key,)).fetchone()
        return dict(zip(("ts", "source", "status", "next_step", "text"), r)) if r else None


def effective(p: Project, note: dict | None) -> Project:
    """Apply an agent note over parsed fields only while it is newer than the docs."""
    if not note or note["ts"] <= p.signal_ts:
        return p
    q = Project.from_dict(p.to_dict())
    if note["status"]:
        q.status, q.status_source = note["status"], "note"
    if note["next_step"]:
        q.next_step = note["next_step"]
    q.gaps = [g for g in q.gaps if not (g in ("no-status-line", "stale-status") and note["status"])
              and not (g == "no-next-step" and note["next_step"])]
    return q
