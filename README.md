# coordinator

TUI + CLI that watches the planning and checkpoint files across all your repos under `~/src`
and answers "what is hot, where did I stop, what is next?" without calling an LLM. LLMs are
only for filling gaps the scripts can't (`coordinator gaps`, `coordinator brief`).

Status: **v0.1 working prototype** — spec in [docs/SPEC.md](docs/SPEC.md); refine after use.

## Quickstart (all commands verified)

```bash
PYTHONPATH=src python3 -m coordinator scan --full     # index ~/src (repos at any depth)
PYTHONPATH=src python3 -m coordinator list            # H1 (<7d), top 10
PYTHONPATH=src python3 -m coordinator track auto      # track the top-N H1 set
PYTHONPATH=src python3 -m coordinator refresh         # rescan tracked + update status repo
PYTHONPATH=src python3 -m coordinator tui             # interactive
scripts/install.sh                                    # puts `coordinator` on PATH (--copy / --uninstall also available)
scripts/verify.sh --quick                             # lint + smoke + unit
```

## Documentation

Start at [docs/README.md](docs/README.md): [purpose](docs/purpose.md), [architecture](docs/architecture.md), [using & configuration](docs/running.md), [how-to recipes](docs/how-to.md), [user manual](docs/usermanual/README.md).

## Layout

| Path | Holds |
|---|---|
| `src/coordinator/` | adapters, scan, store, graph, export, engine, cli, tui |
| `tests/` | smoke, unit, integration, system, perf, stress, torture |
| `scripts/verify.sh` | tiered test runner → `target/verify/` |
| `docs/` | purpose, architecture, running, how-to, usermanual/, SPEC.md |
| `input/`, `output/` | git-ignored data (READMEs tracked) |

Runtime state is **not** in this repo: `~/.local/share/coordinator/` (override `COORDINATOR_HOME`),
config in `~/.config/coordinator/config.toml`.
