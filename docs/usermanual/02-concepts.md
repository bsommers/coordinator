# 2. Concepts

[← Back to Project README](../../README.md) · [Manual index](README.md)

| Term | Meaning |
|---|---|
| **Project** | A directory under the root containing `.git`, `.planning`, `.specify`, `openspec` or `.kiro`. Found at any depth up to `max_depth` (6); a project is not searched for nested projects. |
| **Key** | The project's path relative to the root, e.g. `tools/coordinator`. You can also use the basename when it is unique. |
| **Signal files** | Planning or checkpoint files coordinator parses (STATE.md, tasks.md, CHECKPOINT.md …). |
| **Framework** | Which planning tool was detected: gsd, spec-kit, openspec, superpowers, kiro, bmad, checkpoint. |
| **Activity** | Newer of last commit and newest signal-file modification. |
| **Horizon** | H1 < 7 days, H2 < 30, H3 < 90, otherwise dormant. |
| **Tracked** | Projects you chose to keep refreshed and exported. |
| **Gap** | A deterministic hint that status is missing or stale: `no-status-doc`, `no-status-line`, `no-next-step`, `stale-status`. |
| **Note** | An agent- or human-supplied status/next override, valid until the project's docs change. |
| **Rollup** | A project's activity combined with that of repos it `depends:` on. |

Scan vs refresh: **scan** looks at every repo but skips unchanged ones; **refresh** re-reads tracked repos unconditionally and rewrites the status repo.
