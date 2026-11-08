# 6. Working with agents

[← Back to Project README](../../README.md) · [Manual index](README.md)

Coordinator never calls an LLM. It tells you where one is needed.

```bash
coordinator gaps --all          # projects with missing or stale status
coordinator brief myrepo        # facts + instructions to paste into an agent session
```

The agent should then do **one** of:

1. **Preferred:** edit the project's own `docs/CHECKPOINT.md` (frontmatter or a `**Status:**` line plus `## Next steps`). Gaps clear on the next scan, and the knowledge lives with the repo.
2. **Fallback:** `coordinator note myrepo --status 'one line' --next 'exact command' 'why'`.

A note overrides the parsed status/next only while it is newer than every signal file in that project. Editing a doc afterwards makes the doc authoritative again. `show` and the TUI detail view display the latest note.

Gap meanings: `no-status-doc` no signal files at all · `no-status-line` none found · `no-next-step` none found and work is not complete · `stale-status` last commit is more than `stale_days` (default 2) newer than the newest status file.
