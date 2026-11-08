# Using & Configuration

[← Back to Project README](../README.md) · [Docs index](README.md)

## Contents
- [Prerequisites](#prerequisites)
- [Install](#install)
- [First run](#first-run)
- [CLI reference](#cli-reference)
- [TUI keys](#tui-keys)
- [Configuration](#configuration)
- [Environment variables](#environment-variables)
- [Exit codes](#exit-codes)
- [Verification](#verification)

## Prerequisites

Linux or macOS (needs `fcntl`), Python ≥ 3.11, `git` on PATH. No other dependencies.

## Install

```bash
# run from a checkout, no install
PYTHONPATH=src python3 -m coordinator paths

# or put `coordinator` on PATH (uv or pipx; user-level, no root)
scripts/install.sh              # editable; --copy for a standalone install, --uninstall to remove
```

The examples below use `coordinator` for brevity; substitute the `PYTHONPATH=src python3 -m coordinator` form if not installed.

## First run

```bash
coordinator paths          # confirm root, data dir, config file
coordinator scan --full    # index every repo under the root
coordinator list           # H1 (< 7 days), top 10
coordinator track auto     # track the top-N H1 projects
coordinator refresh        # rescan tracked + write the status repo
coordinator tui
```

## CLI reference

Global flags go **before** the subcommand: `coordinator --root ~/work --json list`.

| Flag | Meaning |
|---|---|
| `--root PATH` | Scan root (overrides env and config) |
| `--json` | Machine-readable output for every command |

| Command | Options | Purpose |
|---|---|---|
| `paths` | | Show resolved root, data dir, db, status repo, config file, horizons |
| `scan` | `--full` | Discover and index repos; incremental unless `--full` (which also prunes vanished repos) |
| `list` | `--horizon {1,2,3,all}` (default `1`), `--top N` (0 = all), `--tracked` | Projects ranked by recent activity. Row marks: `*` tracked, `!` has gaps |
| `show NAME` | | Full detail for one project (key or unique basename) |
| `track ACTION [NAMES…]` | `add`, `rm`, `list`, `clear`, `auto`; `--top N`, `--prune` for `auto` | Manage the tracked set; prints the resulting set. `list` only prints it. `auto` adds the top-N H1 projects; with `--prune` it also untracks everything outside that set |
| `refresh` | | Rescan tracked projects unconditionally, rewrite the status repo |
| `watch` | `--interval SECS` (300), `--full-every N` (12) | Loop `scan` + `refresh`; Ctrl-C stops |
| `gaps` | `--all` | Projects with gaps (tracked only unless `--all`) |
| `brief NAME` | | Fact pack for an agent session; no LLM is called |
| `note NAME TEXT` | `--status`, `--next`, `--source` (default `agent`) | Record an override that holds until the project's docs are newer |
| `graph` | `--markdown`, `--tui`, `--once` | Dependency edges and collapsed cycles. Default prints text to stdout; `--markdown` prints a report with a Mermaid flowchart (redirect to save it); `--tui` opens the TUI graph view, and `--tui --once` prints one frame. `--json` takes precedence over `--markdown` |
| `tui` | `--once`, `--horizon {1,2,3,all}` | Interactive UI; `--once` prints one frame |

Gap codes: `no-status-doc`, `no-status-line`, `no-next-step`, `stale-status`.

## TUI keys

| Key | Action |
|---|---|
| `j` / `k` (or arrows) | Move |
| `1` `2` `3` `a` | Horizon H1 / H2 / H3 / all |
| `Enter` | Toggle detail view |
| `t` | Track / untrack selected |
| `s` | Incremental scan |
| `r` | Refresh |
| `g` | Toggle dependency graph view (`j`/`k` scroll) |
| `q` | Quit |

## Configuration

Optional `~/.config/coordinator/config.toml`:

```toml
root = "~/src"
data_dir = "~/.local/share/coordinator"
horizons = [7, 30, 90]     # three ascending day counts
top_n = 10                 # default list length
max_depth = 6              # how deep to look for repos
stale_days = 2             # commit-newer-than-checkpoint threshold for stale-status
ignore = [".git", "node_modules", ".venv", "target"]   # replaces the default ignore list
auto_commit = true         # commit the status repo after refresh
```

Precedence for the root: `--root` > `COORDINATOR_ROOT` > `root` in config > `~/src`.
Note `ignore` replaces, not extends, the defaults (`.git node_modules .venv venv __pycache__ target dist build .cache .tox .mypy_cache .pytest_cache site-packages .codegraph graphify-out`). Hidden directories are always skipped.

## Environment variables

| Variable | Effect |
|---|---|
| `COORDINATOR_ROOT` | Scan root |
| `COORDINATOR_HOME` | Data directory |
| `COORDINATOR_CONFIG` | Path to `config.toml` |
| `XDG_DATA_HOME`, `XDG_CONFIG_HOME` | Base dirs when the above are unset |
| `COORDINATOR_ACTIVE` | Set by the tool while running; if already set, a nested call exits 0 without doing anything |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success (also a re-entrant call that was skipped) |
| 1 | Unknown or ambiguous project name (message on stderr) |
| 2 | Usage error (argparse) |
| 3 | Another coordinator run holds the lock |

## Verification

```bash
scripts/verify.sh --quick     # lint + smoke + unit (gate before commit)
scripts/verify.sh             # all tiers (before release)
scripts/verify.sh --list      # stage inventory
scripts/verify.sh --status    # last result, one line
```

Results land in `target/verify/` (`STATUS`, `summary.tsv`, `report.md`, `junit.xml`, per-stage `log` and `fail.txt`).
