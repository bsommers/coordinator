# coordinator

- Python ≥3.11, stdlib only at runtime (pytest for dev). Run: `PYTHONPATH=src python3 -m coordinator`.
- Gate: `scripts/verify.sh --quick` before commit; full run before release.
- Never write into scanned repos. Git calls must keep `GIT_OPTIONAL_LOCKS=0` (index writes would defeat incremental fingerprints and create feedback loops).
- Runtime data lives in `~/.local/share/coordinator`, never in this repo. Spec: docs/SPEC.md.
