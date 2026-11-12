# How-to recipes

[← Back to Project README](../README.md) · [Docs index](README.md)

Commands assume `coordinator` is on PATH (or use `PYTHONPATH=src python3 -m coordinator`).
Each was run against a throwaway root before being documented.

## Contents
- [See what is hot right now](#see-what-is-hot-right-now)
- [Keep a standing set of projects up to date](#keep-a-standing-set-of-projects-up-to-date)
- [Make a repo report status and next step](#make-a-repo-report-status-and-next-step)
- [Fill gaps with an agent](#fill-gaps-with-an-agent)
- [Declare dependencies between repos](#declare-dependencies-between-repos)
- [Run it on a schedule](#run-it-on-a-schedule)
- [Export a snapshot for sharing](#export-a-snapshot-for-sharing)
- [Try it safely on a sandbox](#try-it-safely-on-a-sandbox)

## See what is hot right now

```bash
coordinator scan
coordinator list                      # last 7 days
coordinator list --horizon 2 --top 0  # 7–30 days, everything
coordinator show myrepo
```

Row layout: `[*tracked][!gaps] H1 age key frameworks done/total status next-step`.

```
   H1   0m demo      checkpoint     -  Phase 2 in progress   run pytest
```

## Keep a standing set of projects up to date

```bash
coordinator track auto --top 5        # or: track add repoA repoB
coordinator track auto --top 5 --prune  # make the set exactly the top 5
coordinator refresh
cd ~/.local/share/coordinator/status && git log --oneline && cat INDEX.md
```

## Make a repo report status and next step

Put this at the top of `CHECKPOINT.md` (root, `docs/`, or `.planning/`):

```markdown
---
status: Phase 2 in progress
next: run pytest tests/unit
depends: [lib]
---
```

Or, without frontmatter, a `**Status:** …` line plus:

```markdown
## Next steps
- run pytest tests/unit
```

## Fill gaps with an agent

```bash
coordinator gaps --all                # which projects have gaps
coordinator brief lib                 # paste into an agent session
coordinator note lib --status 'idle, no tests yet' --next 'write tests' 'why'
```

Preferred fix: have the agent update the project's own `CHECKPOINT.md`, which makes the note unnecessary. A note stops applying as soon as any signal file in that project is edited after it.

## Declare dependencies between repos

Add `depends: [lib, tools/other]` to a status doc's frontmatter (key, or unique basename).

```bash
coordinator graph
# 3 projects, 2 edges (1 inferred), 0 cycle(s)
# demo -> lib        declared (depends: frontmatter)
# tool ~> lib        inferred from a local-path dependency in a manifest
#
# no dependencies (1):
#   other

coordinator graph --markdown > deps.md   # Mermaid flowchart + edges table
coordinator graph --tui                  # scrollable view (also `g` inside `coordinator tui`)
```

Edges are also inferred from local-path dependencies in `pyproject.toml`, `Cargo.toml`, `package.json` (`file:`/`link:`) and `go.mod` (`replace`). Every project is listed; those without edges appear under "no dependencies". Inferred edges are display-only (dashed in Mermaid) and do not affect rollup.

A project's rollup activity is the max of its own and its dependencies'. Cycles are reported and collapsed, not errors.

## Run it on a schedule

```bash
coordinator watch --interval 300      # foreground loop
# or cron: */10 * * * * coordinator refresh
```

If a run is still going, the next one exits with code 3 (`watch` prints `skipped:` instead).

## Export a snapshot for sharing

```bash
coordinator --json list --horizon all --top 0 > output/snapshot.json
```

`output/` is git-ignored.

## Try it safely on a sandbox

```bash
export COORDINATOR_HOME=$(mktemp -d) COORDINATOR_CONFIG=/dev/null
coordinator --root ./some/dir scan --full && coordinator --root ./some/dir list --horizon all
```

Nothing is written into the scanned directory.
