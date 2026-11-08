# 1. Getting started

[← Back to Project README](../../README.md) · [Manual index](README.md)

## Contents
- [Prerequisites](#prerequisites) · [Install](#install) · [Init → verify → first run](#init--verify--first-run)

## Prerequisites
Linux or macOS, Python ≥ 3.11, `git`. No packages to install.

## Install
```bash
cd coordinator
PYTHONPATH=src python3 -m coordinator paths     # works without installing
scripts/install.sh                              # optional: `coordinator` on PATH (uv or pipx)
```

## Init → verify → first run
There is no `init` step: the first command creates `~/.local/share/coordinator` on demand.

1. **Check paths:** `coordinator paths` shows the scan root (default `~/src`) and data dir. Use `--root DIR` or `COORDINATOR_ROOT` to change the root.
2. **Index:** `coordinator scan --full` prints `found=N, new=N, …`. `found=0` means no repo was discovered under the root; see [troubleshooting](07-troubleshooting-and-faq.md).
3. **Look:** `coordinator list` shows projects active in the last 7 days; `coordinator tui` is the interactive version.
4. **Optionally verify the install itself:** `scripts/verify.sh --quick` (checkout only).

Coordinator only reads your repos. Everything it stores is under the data dir.
