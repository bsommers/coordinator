"""SDD-tool adapters: detect a framework in a repo and parse status facts from
its files with plain text rules (no LLM). Each adapter returns a Facts record."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

MAX_READ = 256 * 1024

_STATUS = re.compile(r"^\s*(?:[-*]\s+)?\*{0,2}status\*{0,2}\s*:\s*\*{0,2}\s*(.+?)\s*$", re.I | re.M)
_BOX = re.compile(r"^\s*[-*]\s+\[([ xX])\]", re.M)
_NEXT_HEAD = re.compile(r"^#{1,4}\s*(?:\d+[.)]?\s*)?(next\s+steps?|next\s+actions?|resume|todo)\b.*$", re.I | re.M)
_ITEM = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(?:\[[ xX]\]\s*)?(.+?)\s*$")


@dataclass
class Facts:
    framework: str
    files: list[str] = field(default_factory=list)  # signal files (relative)
    status: str = ""
    status_file: str = ""
    phase: str = ""
    next_step: str = ""
    done: int = 0
    total: int = 0
    depends: list[str] = field(default_factory=list)


def read(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return f.read(MAX_READ)
    except OSError:
        return ""


def frontmatter(text: str) -> dict[str, str]:
    """Flat `key: value` frontmatter; nested keys are flattened as parent.child."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    out: dict[str, str] = {}
    parent = ""
    for line in text[3:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^(\s*)([\w.-]+)\s*:\s*(.*)$", line)
        if not m:
            continue
        indent, k, v = m.groups()
        v = v.strip().strip('"').strip("'")
        if not indent:
            parent = k if not v else ""
            if v:
                out[k] = v
        elif parent:
            out[f"{parent}.{k}"] = v
    return out


def parse_list(value: str) -> list[str]:
    value = value.strip().strip("[]")
    return [p.strip().strip('"').strip("'") for p in value.split(",") if p.strip()]


def status_line(text: str) -> str:
    m = _STATUS.search(text)
    return m.group(1).strip("* ") if m else ""


def checkboxes(text: str) -> tuple[int, int]:
    marks = _BOX.findall(text)
    return sum(1 for m in marks if m.lower() == "x"), len(marks)


def next_step(text: str) -> str:
    m = _NEXT_HEAD.search(text)
    if not m:
        return ""
    for line in text[m.end():].splitlines():
        if line.startswith("#"):
            break
        im = _ITEM.match(line)
        if im:
            return im.group(1)
    return ""


def _exists(root: Path, rels: list[str]) -> list[str]:
    return [r for r in rels if (root / r).is_file()]


def _glob(root: Path, pattern: str) -> list[str]:
    try:
        return sorted(str(p.relative_to(root)) for p in root.glob(pattern) if p.is_file())
    except OSError:
        return []


def _newest(root: Path, rels: list[str]) -> str:
    best, best_m = "", -1.0
    for r in rels:
        try:
            m = (root / r).stat().st_mtime
        except OSError:
            continue
        if m > best_m:
            best, best_m = r, m
    return best


def _sum_boxes(root: Path, rels: list[str]) -> tuple[int, int]:
    d = t = 0
    for r in rels:
        a, b = checkboxes(read(root / r))
        d, t = d + a, t + b
    return d, t


# --- adapters -----------------------------------------------------------------


def gsd(root: Path) -> Facts | None:
    """GSD / OpenGSD: .planning/{STATE,ROADMAP,PROJECT}.md (+ CHECKPOINT.md)."""
    if not (root / ".planning").is_dir():
        return None
    files = _exists(root, [".planning/STATE.md", ".planning/ROADMAP.md", ".planning/PROJECT.md",
                           ".planning/REQUIREMENTS.md"])
    f = Facts("gsd", files)
    state = read(root / ".planning/STATE.md")
    fm = frontmatter(state)
    f.status = fm.get("status") or status_line(state)
    f.status_file = ".planning/STATE.md" if f.status else ""
    name = fm.get("current_phase_name", "")
    num = fm.get("current_phase", "")
    f.phase = f"{num} {name}".strip()
    try:
        f.done = int(fm.get("progress.completed_plans", 0))
        f.total = int(fm.get("progress.total_plans", 0))
    except ValueError:
        pass
    if not f.total:
        f.done, f.total = checkboxes(read(root / ".planning/ROADMAP.md"))
    f.next_step = fm.get("stopped_at", "") if not f.status.lower().startswith("complete") else ""
    f.depends = parse_list(fm.get("depends", ""))
    return f


def speckit(root: Path) -> Facts | None:
    """GitHub spec-kit: .specify/ + specs/<feature>/{spec,plan,tasks}.md."""
    if not ((root / ".specify").is_dir() or (root / "specs").is_dir()):
        return None
    tasks = _glob(root, "specs/*/tasks.md")
    if not tasks and not (root / ".specify").is_dir():
        return None
    files = tasks + _glob(root, "specs/*/spec.md") + _glob(root, "specs/*/plan.md")
    files += _exists(root, [".specify/memory/constitution.md"])
    f = Facts("spec-kit", files)
    f.done, f.total = _sum_boxes(root, tasks)
    if tasks:
        f.phase = Path(_newest(root, tasks)).parent.name
    return f


def openspec(root: Path) -> Facts | None:
    """OpenSpec: openspec/{specs,changes}/ ; active changes are the work in flight."""
    if not (root / "openspec").is_dir():
        return None
    changes = [p for p in _glob(root, "openspec/changes/*/tasks.md") if "/archive/" not in p]
    files = changes + _glob(root, "openspec/changes/*/proposal.md")
    f = Facts("openspec", files)
    f.done, f.total = _sum_boxes(root, changes)
    if changes:
        f.phase = Path(_newest(root, changes)).parent.name
    return f


def superpowers(root: Path) -> Facts | None:
    """Superpowers: docs/superpowers/{specs,plans}/*.md and .superpowers/ notes."""
    has_docs = (root / "docs/superpowers").is_dir()
    if not (has_docs or (root / ".superpowers").is_dir()):
        return None
    plans = _glob(root, "docs/superpowers/plans/*.md")
    files = plans + _glob(root, "docs/superpowers/specs/*.md") + _glob(root, ".superpowers/*.md")
    f = Facts("superpowers", files)
    f.done, f.total = _sum_boxes(root, plans)
    if plans:
        f.phase = Path(_newest(root, plans)).stem
    return f


def kiro(root: Path) -> Facts | None:
    if not (root / ".kiro/specs").is_dir():
        return None
    tasks = _glob(root, ".kiro/specs/*/tasks.md")
    f = Facts("kiro", tasks + _glob(root, ".kiro/specs/*/requirements.md"))
    f.done, f.total = _sum_boxes(root, tasks)
    return f


def bmad(root: Path) -> Facts | None:
    if not any((root / d).is_dir() for d in (".bmad-core", "_bmad", "bmad")):
        return None
    stories = _glob(root, "docs/stories/*.md") + _glob(root, "docs/prd.md")
    f = Facts("bmad", stories)
    f.done, f.total = _sum_boxes(root, stories)
    return f


CHECKPOINT_FILES = [
    "CHECKPOINT.md", "HANDOFF.md", "STATUS.md",
    "docs/CHECKPOINT.md", "docs/HANDOFF.md", "docs/STATUS.md",
    ".planning/CHECKPOINT.md", ".superpowers/checkpoint.md",
]


def checkpoint(root: Path) -> Facts | None:
    """Tool-agnostic checkpoint/status docs (see the handing-off-sessions skill)."""
    files = _exists(root, CHECKPOINT_FILES)
    if not files:
        return None
    f = Facts("checkpoint", files)
    top = _newest(root, files)
    text = read(root / top)
    fm = frontmatter(text)
    f.status = fm.get("status") or status_line(text)
    f.status_file = top if f.status else ""
    f.next_step = fm.get("next") or next_step(text)
    f.depends = parse_list(fm.get("depends", ""))
    return f


# Order = precedence for phase/progress. checkpoint is handled specially (status, next).
ADAPTERS = [gsd, speckit, openspec, superpowers, kiro, bmad, checkpoint]


def detect(root: Path) -> list[Facts]:
    return [f for a in ADAPTERS if (f := a(root)) is not None]
