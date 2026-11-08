# 3. Daily workflow

[← Back to Project README](../../README.md) · [Manual index](README.md)

```bash
coordinator scan                       # cheap, incremental
coordinator list                       # what moved this week
coordinator list --horizon all --top 0 # everything, including dormant
coordinator show NAME                  # branch, dirty count, status, next step, gaps, signal files
coordinator tui
```

## Reading a row
```
 *!  H1   3h  tools/coordinator   gsd    4/9   Phase 2 in progress   run pytest
 │└─ has gaps     │       │         │      │      └ status          └ next step
 └── tracked      │       │         │      └ done/total tasks
                  │       │         └ frameworks
                  │       └ key
                  └ age of last activity
```

## TUI
Start with `coordinator tui` (`--horizon 2` or `all` to open elsewhere). Keys: `j/k` move, `1 2 3 a` horizon, `Enter` detail, `t` track, `s` scan, `r` refresh, `g` dependency graph (toggle), `q` quit. `coordinator tui --once` prints a single frame, which is handy for scripts.

## Scripting
Put `--json` before the command: `coordinator --json list | jq '.[].next_step'`.
