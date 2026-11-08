# 7. Troubleshooting and FAQ

[← Back to Project README](../../README.md) · [Manual index](README.md)

| Symptom | Cause | Fix |
|---|---|---|
| `found=0` | Wrong root, or repos deeper than `max_depth`, or in an ignored dir | `coordinator paths`; set `--root`; raise `max_depth` |
| `list` says `(none — run: coordinator scan)` | Index empty, or nothing active in 7 days | `scan`, then `list --horizon all` |
| `unknown project 'x'` (exit 1) | Not indexed or misspelt | `list --horizon all`, then `scan --full` |
| `ambiguous 'x': a/x, b/x` | Same basename twice | Use the full key |
| `coordinator: another coordinator run holds the lock` (exit 3) | A `watch`/`refresh` is running | Wait; the lock is released automatically when the process exits |
| Status shows `-` and gap `no-status-line` | No parsable status | See [chapter 5](05-writing-status-docs.md) |
| Dirty count or branch looks old | Incremental scan did not see the change | `coordinator refresh` (tracked) or `scan --full` |
| Project missing after moving it | Key is path-relative | `scan --full` prunes the old key; re-`track` the new one |
| `config 'horizons' must be 3 ascending day counts` | Bad `config.toml` | Fix e.g. `horizons = [7, 30, 90]` |

**Does it modify my repos?** No. It reads files and runs read-only git commands with `GIT_OPTIONAL_LOCKS=0`.

**Where is my data?** `coordinator paths`. Delete the data dir to reset everything.

**Can I track coordinator itself?** Yes; loop protections are described in [architecture](../architecture.md#loop-breakers).

**A hook calls coordinator and nothing happens.** If `COORDINATOR_ACTIVE` is set (a run is in progress) the call exits 0 on purpose.

**Windows?** Not supported (uses `fcntl`).
