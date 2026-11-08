# coordinator — spec (v0.1, as built)

## Goal
One place to see the state of every project under `~/src`: what is active, where work stopped,
what comes next. Status comes from artifacts already on disk, parsed by scripts. LLMs are a
last resort for gaps, invoked from an agent session, never by this tool.

## Scope decisions
| Topic | Decision |
|---|---|
| Scan root | `~/src` (`--root`, `COORDINATOR_ROOT`, or `root` in config.toml). Repos found at any depth ≤ `max_depth` (6); a repo root is not descended into. Dirs with `.git`, `.planning`, `.specify`, `openspec`, or `.kiro` count as projects. |
| Horizons | H1 < 7d, H2 < 30d, H3 < 90d (configurable `horizons`). Age = newest of last commit and newest signal-file mtime. Default `list` = H1, top 10. Older = dormant (`--horizon all`). |
| Signal sources | `.planning/` and `docs/` plus generic checkpoint files: `CHECKPOINT.md`, `HANDOFF.md`, `STATUS.md` (root, `docs/`, `.planning/`), `.superpowers/checkpoint.md`. |
| SDD awareness | GSD/OpenGSD (`.planning/STATE.md` frontmatter, ROADMAP checkboxes), spec-kit (`.specify/`, `specs/*/tasks.md`), OpenSpec (`openspec/changes/*/tasks.md`), Superpowers (`docs/superpowers/{specs,plans}`), Kiro (`.kiro/specs`), BMAD (`.bmad-core`/`_bmad`, `docs/stories`). New tool = one function in `adapters.py`. |
| Tracking set | Explicit list in sqlite. `track add/rm/clear/auto` (auto = add top-N H1). Only tracked projects are refreshed continuously and exported. |
| Refresh | `scan` is incremental (fingerprint = signal-file stats + dir mtimes + git HEAD/index/reflog mtimes); `scan --full` re-parses all and prunes vanished repos. `refresh` rescans tracked projects unconditionally, then rewrites the status repo. `watch` loops both (full scan every 12 cycles). Schedule with systemd timer/cron if preferred. |
| LLM use | None in-tool. `gaps` lists deterministic gaps (`no-status-doc`, `no-status-line`, `no-next-step`, `stale-status`). `brief <p>` emits a fact pack for an agent. The agent writes back via `note` (status/next override, valid only until the project's docs are newer) or, better, by updating the project's own CHECKPOINT.md. |
| Self-tracking | Allowed. Loop breakers: (1) data dir excluded from discovery; (2) status repo is outside the tracked repo; (3) git run with `GIT_OPTIONAL_LOCKS=0` so reads never touch repo state; (4) own repo is refreshed last; (5) non-reentrant lock + `COORDINATOR_ACTIVE` env (a hook calling us mid-run exits 0); (6) dependency cycles collapse to SCCs and rollups are one monotone-max pass over the condensation DAG, never iterated to a fixpoint. |
| Dependencies | Optional `depends: [name, ...]` in a status doc's frontmatter. Only authored docs create edges, never generated files. |

## Data layout (kept out of the repo and out of GitHub)
`~/.local/share/coordinator/` (XDG data home; `COORDINATOR_HOME` overrides). Not
`~/.local/data`, which is not an XDG dir.
- `coordinator.db` — sqlite index: projects, tracked set, agent notes.
- `status/` — local-only git repo: `INDEX.md` + `projects/<key>.md` for tracked projects, committed only when content changes (no generation timestamps). Add a private remote yourself if you want backup.
- `.lock`
Config: `~/.config/coordinator/config.toml` (keys: `root`, `data_dir`, `horizons`, `top_n`, `max_depth`, `stale_days`, `ignore`, `auto_commit`).

## Surfaces (parity)
CLI (all take `--json`): `paths scan list show track refresh watch gaps brief note graph tui`.
TUI (curses, stdlib): horizon filter 1/2/3/a, move j/k, enter = detail, `t` track, `s` scan, `r` refresh. List/detail rendering shares `view.py` with the CLI.

## Status fields
`status` (newest `status:` frontmatter / `**Status:**` line among signal files), `phase`, `done/total`
(checkbox or GSD plan counts), `next_step` (frontmatter `next:`, first item under a "Next steps" heading, or GSD `stopped_at`), git branch/dirty/ahead/behind.

## Recommended doc convention (see handing-off-sessions skill)
Frontmatter on CHECKPOINT.md: `status:`, `next:`, `depends:`. Keeps parsing exact and gaps rare.

## Known limits / next
- Dirty-count freshness: incremental scans don't see working-tree edits that touch neither signal files nor the git index; `refresh`/`--full` do.
- Parsing is heuristic (regex); odd formats surface as gaps rather than errors.
- Not yet: remote repos, notifications, per-horizon rollups in TUI, stale-tracked auto-demotion, Windows (uses `fcntl`).
