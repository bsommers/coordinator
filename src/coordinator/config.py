"""Paths and settings. Everything is overridable by env var or config.toml."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_IGNORE = (
    ".git", "node_modules", ".venv", "venv", "__pycache__", "target", "dist",
    "build", ".cache", ".tox", ".mypy_cache", ".pytest_cache", "site-packages",
    ".codegraph", "graphify-out",
)


def data_dir() -> Path:
    """Local-only state (sqlite index + status repo). XDG data home by default."""
    if env := os.environ.get("COORDINATOR_HOME"):
        return Path(env).expanduser()
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base).expanduser() / "coordinator"


def config_file() -> Path:
    if env := os.environ.get("COORDINATOR_CONFIG"):
        return Path(env).expanduser()
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base).expanduser() / "coordinator" / "config.toml"


@dataclass(frozen=True)
class Config:
    root: Path
    data_dir: Path
    horizons: tuple[int, int, int] = (7, 30, 90)  # days: H1 < 7, H2 < 30, H3 < 90
    top_n: int = 10
    max_depth: int = 6
    stale_days: int = 2  # checkpoint older than last commit by this much => gap
    ignore: tuple[str, ...] = DEFAULT_IGNORE
    auto_commit: bool = True  # commit status repo after refresh

    @property
    def db_path(self) -> Path:
        return self.data_dir / "coordinator.db"

    @property
    def status_dir(self) -> Path:
        return self.data_dir / "status"


def load(root: str | os.PathLike | None = None) -> Config:
    raw: dict = {}
    cf = config_file()
    if cf.is_file():
        raw = tomllib.loads(cf.read_text())
    chosen = root or os.environ.get("COORDINATOR_ROOT") or raw.get("root") or "~/src"
    horizons = tuple(raw.get("horizons", (7, 30, 90)))
    if len(horizons) != 3 or sorted(horizons) != list(horizons):
        raise ValueError("config 'horizons' must be 3 ascending day counts")
    return Config(
        root=Path(chosen).expanduser().resolve(),
        data_dir=Path(raw.get("data_dir", data_dir())).expanduser(),
        horizons=horizons,  # type: ignore[arg-type]
        top_n=int(raw.get("top_n", 10)),
        max_depth=int(raw.get("max_depth", 6)),
        stale_days=int(raw.get("stale_days", 2)),
        ignore=tuple(raw.get("ignore", DEFAULT_IGNORE)),
        auto_commit=bool(raw.get("auto_commit", True)),
    )
