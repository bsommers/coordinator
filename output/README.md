# output/

Reproducible artifacts for sharing or debugging (e.g. `coordinator --json list --horizon all > output/snapshot.json`).

- **Regenerate:** re-run the command; nothing here is hand-edited.
- **Not the status store.** Live state lives outside the repo, in `~/.local/share/coordinator` (see docs/SPEC.md §Data layout).
- Everything except this README is git-ignored.
