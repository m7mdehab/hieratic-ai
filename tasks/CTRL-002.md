# CTRL-002 — Project-State Validator and Context Generator

- **Task ID:** CTRL-002
- **Branch:** `task/CTRL-002-state-context-tooling`
- **Owner:** execution agent
- **Depends on:** CTRL-001 — validated
- **Status at dispatch:** ready
- **Primary write scope:** `tools/`, `schemas/`, `tests/governance/`, minimal dependency/config files required for this tooling
- **Do not edit:** `ROADMAP.md`, task weights, benchmark/evaluation content, progress numbers, research conclusions

## Context

Hieratic AI is designed to survive many chats and many model providers. Canonical project state lives in the repository. We need deterministic tooling so a fresh overseer or execution agent can validate that state and load only the context it needs.

The tool must be provider-neutral and usable locally and later from CI.

## Objective

Implement a small, reliable project-control CLI that:

1. validates canonical project/task state;
2. proves the task graph is structurally sane;
3. proves validated weighted tasks reconcile with reported goal progress;
4. emits compact context packets for a new overseer chat or a specific execution task.

## Required implementation

Use **Python 3.11+** unless a concrete repository constraint makes that impossible. Keep dependencies minimal and explicit.

Provide a stable CLI. Preferred interface:

```bash
python -m tools.projectctl validate
python -m tools.projectctl context --overseer
python -m tools.projectctl context --task CTRL-003
```

Equivalent ergonomics are acceptable only if documented and equally simple.

### Validation must detect at minimum

- invalid YAML / schema shape;
- duplicate task IDs;
- unknown task status;
- missing dependency IDs;
- dependency cycles;
- negative weights;
- control-plane tasks with non-zero capability weight;
- phase weights not summing to 100 across P1-P8;
- task weights not summing to their declared phase weight;
- a task marked ready/active/under_review while a dependency is not validated;
- validated weighted-task sum not equaling `PROJECT_STATE.yaml -> progress.goal_progress`;
- `TASKS.yaml -> rules.progress.validated_weighted_tasks_expected` disagreement with actual validated weighted sum;
- unknown task IDs listed in `PROJECT_STATE.yaml` ready/active/review arrays;
- duplicate membership of the same task across incompatible state arrays.

### Schemas

Create explicit machine-readable schemas under `schemas/` for at least:
- `PROJECT_STATE.yaml`;
- `TASKS.yaml`.

Choose JSON Schema or an equivalently inspectable format. Do not invent a framework-heavy validation stack.

### Context generation

`--overseer` should output a compact Markdown packet containing:
- mission;
- goal progress + research coverage;
- current phase/wave/gates;
- last accepted task;
- ready/active/review/blocker state;
- latest handoff;
- canonical authority/read order;
- relevant open decisions;
- next overseer action.

`--task <ID>` should output only the execution context needed for that task:
- mission summary;
- agent contract summary/reference;
- task metadata;
- dependency state;
- acceptance summary;
- declared write scope if present;
- links/paths to the task brief and canonical dependencies;
- explicit warning not to alter progress/weights unless authorized.

Generated packets must go to a clearly generated/ignored location or stdout by default. They are caches, never canonical state.

## Tests

Add automated tests covering valid state and each major failure class above.

At minimum demonstrate:
- current repo state passes;
- a dependency cycle fails;
- a fake missing dependency fails;
- progress mismatch fails;
- phase/task weight mismatch fails;
- invalid ready state with blocked dependency fails;
- overseer context output includes current 2.5 / 14 state;
- task context for CTRL-003 excludes unrelated deep research content.

Tests must use fixtures/copies; do not corrupt canonical files to test failure modes.

## Deliverables

Expected paths:
- `tools/projectctl.py` or equivalent module structure;
- `schemas/project_state.schema.json` or equivalent;
- `schemas/tasks.schema.json` or equivalent;
- `tests/governance/...`;
- dependency/config file(s) only as needed;
- short usage documentation.

## Acceptance criteria

All criteria in `TASKS.yaml` plus the detailed requirements above.

## Prohibited shortcuts

- hard-coding "2.5" as the validator's expected progress;
- parsing roadmap weights from presentation text when machine-readable task/phase fields already exist;
- silently repairing invalid state;
- ignoring cycles because current graph happens to be acyclic;
- generating context by dumping whole repository files;
- creating a second mutable state database.

## Evidence package on return

Return:
- task ID;
- branch;
- commit SHA;
- exact files changed;
- install/setup command;
- validation command + output;
- test command + output;
- sample overseer context packet;
- sample CTRL-003 context packet;
- acceptance checklist;
- deviations/risks;
- dependency/licensing impact.

Do **not** self-mark the task validated.
