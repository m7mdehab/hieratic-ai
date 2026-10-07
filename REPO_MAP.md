# Repository Map

This file is a navigation aid. It describes where information belongs so a new human or AI session can avoid broad repository exploration.

## Root control files

| File | Purpose |
|---|---|
| `START_HERE.md` | first-read orientation and authority rules |
| `PROJECT_STATE.yaml` | current machine-readable state |
| `ROADMAP.md` | stable capability phases and point weights |
| `TASKS.yaml` | canonical dependency/task graph |
| `AGENTS.md` | provider-agnostic execution contract |
| `OVERSEER_HANDOFF.md` | current cross-chat continuity packet |
| `DECISIONS.md` | accepted architectural/research decisions |
| `EXPERIMENTS.md` | experiment registry |
| `RESEARCH.md` | research registry, evidence status, open questions |
| `README.md` | public-facing project overview |

## Planned implementation areas

`tasks/`
: self-contained task briefs and remediation briefs.

`docs/governance/`
: schemas, operating procedures, and project-control specifications.

`docs/research/`
: detailed research notes that support the compact `RESEARCH.md` registry.

`docs/evaluation/`
: benchmark protocols, metrics, split design, leakage controls.

`data/`
: manifests, metadata, and data-processing structure. Raw third-party assets must not be committed merely because they are downloadable.

`src/`
: core ML/research software.

`eval/`
: evaluation implementations and benchmark adapters.

`experiments/`
: experiment configs and reproducible run metadata, not uncontrolled checkpoint dumps.

`models/`
: model documentation and lightweight manifests. Large weights should use appropriate artifact hosting.

`tools/`
: project automation, state validation, data utilities, context generation.

`tests/`
: software, data-integrity, evaluation, and governance tests.

`dashboard/`
: live web control plane / public project interface.

`.github/`
: CI, PR templates, and repository automation.

## Authority boundaries

The dashboard is a **view over canonical repo state**, not an independent source of truth.

Generated context packets are caches, not authority. If they disagree with canonical files, canonical files win.

Large datasets and model artifacts should be referenced by versioned manifests/checksums rather than placed in Git unless they are small, licensed, and appropriate for Git.
