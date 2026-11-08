# 4. Tracking and the status repo

[← Back to Project README](../../README.md) · [Manual index](README.md)

```bash
coordinator track add repoA repoB
coordinator track rm repoA
coordinator track auto --top 5   # add the 5 most recent H1 projects
coordinator track list
coordinator track clear
coordinator refresh
```

`track auto` only adds. Add `--prune` to make the tracked set exactly the selected H1 projects (it untracks the rest). Projects that disappear from disk are dropped from the tracked set at the next `scan --full`.

## Status repo
`refresh` writes `~/.local/share/coordinator/status/` (a local git repo, branch `main`):

- `INDEX.md` — table of tracked projects: status, next, gaps, last activity day.
- `projects/<key with / replaced by __>.md` — one file per project.

It commits only when content changes (files contain no generation timestamp), so `git log` is a real history of status changes. Set `auto_commit = false` to write files without committing. There is no remote; add a private one yourself if you want a backup.

## Keeping it fresh
`coordinator watch` loops scan + refresh every 300 s (a full scan every 12th cycle), or schedule `coordinator refresh` with cron or a systemd timer.
