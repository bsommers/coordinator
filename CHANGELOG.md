# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com/); versions follow SemVer.

## [v0.1.0] - 2026-11-08

### Added
- Initial release: cross-repo status tracker with CLI and curses TUI.
- Adapters for GSD, spec-kit, OpenSpec, Superpowers, Kiro, BMAD and generic checkpoint files.
- Incremental scan, tracked set, local status git repo, dependency rollup, gaps/brief/note workflow for agents.
- Documentation suite: purpose, architecture, running, how-to, seven-chapter user manual.
- `coordinator track auto --prune` to make the tracked set exactly the top-N H1 projects.

### Fixed
- Repos with no commits reported their branch as `No`; the real branch name is now shown.
- `track list` no longer relies on a special case in `main()`.
