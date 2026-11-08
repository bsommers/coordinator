# 5. Writing status docs coordinator can read

[← Back to Project README](../../README.md) · [Manual index](README.md)

The most reliable format is frontmatter on a `CHECKPOINT.md` (also read: `HANDOFF.md`, `STATUS.md`, in the root, `docs/` or `.planning/`; and `.superpowers/checkpoint.md`):

```markdown
---
status: Phase 2 in progress
next: run pytest tests/unit
depends: [lib]
---
```

Without frontmatter coordinator falls back to:
- a line `**Status:** text` (or `Status: text`);
- the first list item under a heading named *Next steps*, *Next actions*, *Resume* or *TODO*.

If several checkpoint files exist, the most recently modified one is used.

## Planning frameworks
| You use | Coordinator reads |
|---|---|
| GSD | `.planning/STATE.md` frontmatter, else ROADMAP checkboxes; `stopped_at` becomes the next step |
| spec-kit | checkboxes in `specs/*/tasks.md` |
| OpenSpec | checkboxes in active `openspec/changes/*/tasks.md` |
| Superpowers | checkboxes in `docs/superpowers/plans/*.md` |
| Kiro / BMAD | `.kiro/specs/*/tasks.md`; `docs/stories/*.md` |

Progress is `done/total` checkboxes (`- [x]` / `- [ ]`).

## Dependencies
`depends: [a, b]` lists project keys or unique basenames. Only hand-written docs create edges.
