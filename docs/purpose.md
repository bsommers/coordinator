# Purpose

[← Back to Project README](../README.md) · [Docs index](README.md)

## Problem

If you work across many repos, each one carries its own planning artifacts: GSD `.planning/`,
spec-kit `specs/`, OpenSpec changes, Superpowers plans, hand-written `CHECKPOINT.md` files. Answering
"what is hot, where did I stop, what is next?" means opening each repo and reading its docs.
Asking an LLM to do that every time is slow, costs tokens, and gives answers that drift between runs.

## What coordinator does

It scans a root directory (default `~/src`), recognises the planning framework in each repo,
extracts status, phase, progress and next step with plain text rules, and shows the result in a
CLI and a curses TUI. It also writes a deterministic markdown snapshot of the repos you track into a
local git repo, so status history is diffable.

## Tenets

| Tenet | What it means in practice |
|---|---|
| **Scripts first, LLM last** | The tool never calls an LLM. It reports deterministic *gaps*; an agent session can fill them (`gaps` → `brief` → `note`). |
| **Read-only toward your repos** | Never writes into scanned repos. Git runs with `GIT_OPTIONAL_LOCKS=0`, so scanning does not touch the index. |
| **State lives outside the repo** | Index, notes and status repo live in `~/.local/share/coordinator` (`COORDINATOR_HOME` overrides). |
| **Stdlib only** | Python ≥ 3.11, no runtime dependencies (`pytest` for development). |
| **One behaviour, two surfaces** | CLI and TUI share selection and formatting in `view.py`. Every CLI command takes `--json`. |
| **No feedback loops** | Tracking coordinator's own repo is safe; see [loop breakers](architecture.md#loop-breakers). |

## Non-goals (v0.1)

Remote repositories, notifications, Windows (uses `fcntl`), per-horizon rollups in the TUI,
and auto-demotion of stale tracked projects. Parsing is regex-based: unusual formats show up as
gaps, not errors.

## Who it is for

A developer, or a developer plus coding agents, juggling several repos. The main output is a
ranked list of recently active projects with their status and exact next step.

See [docs/SPEC.md](SPEC.md) for the decision table this document summarises.
