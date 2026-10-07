# Project control CLI

The provider-neutral control CLI validates canonical state and generates bounded context packets. It never writes to canonical files. Context output goes to stdout; redirect it only to a local generated location such as `.projectctl/`, which is ignored by Git.

## Setup

From the repository root, install the small runtime dependencies:

```bash
python -m pip install -r requirements-projectctl.txt
```

Python 3.11 or newer is required.

## Commands

```bash
python -m tools.projectctl validate
python -m tools.projectctl context --overseer
python -m tools.projectctl context --task CTRL-003
```

The optional `--root PATH` argument selects another repository checkout, mainly for fixture-based validation. `validate` checks both JSON Schemas and cross-file invariants: task identity and graph integrity, status/dependency rules, phase and task weights, state-array membership, and reconciliation of validated task weights to both reported progress values.

Overseer context reads `PROJECT_STATE.yaml`, `TASKS.yaml`, `START_HERE.md`, `OVERSEER_HANDOFF.md`, and `DECISIONS.md`. Task context reads the task brief, `TASKS.yaml`, `PROJECT_STATE.yaml`, and `AGENTS.md`; it summarizes these inputs instead of dumping whole repository documents.

Generated packets are disposable views. Canonical truth remains in the repository's accepted decisions, project state, task graph, roadmap, and task briefs.
