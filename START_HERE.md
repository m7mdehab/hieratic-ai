# START HERE

This is the canonical orientation document for **Hieratic AI**.

If you are a new ChatGPT conversation, Codex session, Copilot agent, Gemini session, Claude/Sonnet agent, Luna session, or future execution agent: **read this file before making changes.**

## 1. Mission

The project is building a reproducible, public multimodal AI system that can read previously unseen ancient Egyptian Hieratic handwriting, produce defensible transliteration/normalization, and ultimately derive meaning/translation with calibrated uncertainty.

Success is not "recognize that the image is Hieratic." Success requires progressively stronger reading capability and evidence of generalization.

## 2. Operating model

There are two roles.

### Overseer

The overseer owns:
- research and source verification;
- system architecture;
- roadmap and capability weights;
- task decomposition;
- experiment design;
- acceptance criteria;
- review of code, data, claims, and evidence;
- project-state updates;
- dispatch of newly unblocked work.

### Execution agents

Execution agents implement bounded tasks from explicit briefs. They do not redefine project goals, success metrics, benchmark splits, licensing rules, or task weights unless the task explicitly authorizes it.

The intended cycle is:

`research/reason -> brief -> parallel execution -> evidence -> overseer review -> accept/revise -> state update -> next wave`

## 3. Current state

Read [PROJECT_STATE.yaml](PROJECT_STATE.yaml) for the live state.

At bootstrap:
- verified goal progress: **2.5%**
- research coverage: **~14%**
- trained models: **0**
- validated experiments: **0**
- current focus: foundation, reproducibility, evaluation planning, and control-plane infrastructure

## 4. Canonical authority order

When information conflicts, use this order:

1. explicit accepted decision in `DECISIONS.md`;
2. `PROJECT_STATE.yaml`;
3. `TASKS.yaml`;
4. `ROADMAP.md`;
5. an accepted task brief under `tasks/`;
6. `RESEARCH.md` / `EXPERIMENTS.md`;
7. implementation code and local notes;
8. chat history or agent memory.

If a conflict remains, stop and escalate to the overseer. Do not silently reconcile it.

## 5. Read only what you need

For a new overseer chat:
1. `START_HERE.md`
2. `OVERSEER_HANDOFF.md`
3. `PROJECT_STATE.yaml`
4. relevant parts of `TASKS.yaml`
5. only then follow links to decisions/research/experiments/code

For an execution agent:
1. `START_HERE.md`
2. `AGENTS.md`
3. assigned task brief
4. the task's declared dependencies and referenced files only

Avoid loading the entire repository into context unless necessary.

## 6. Hard rules

- Progress is earned by verified capability, not elapsed time, token usage, code volume, or training runs.
- Never train on benchmark/test material.
- Never change evaluation splits or sealed test material as a convenience.
- Never claim a source, metric, license, or result that was not verified.
- Never redistribute third-party material without a recorded license basis.
- Every experiment must be reproducible enough to identify data version, code version, configuration, model/checkpoint, and evaluation output.
- Every task must have acceptance criteria and an evidence package.
- Parallel work is preferred when dependencies and file ownership make it safe.
- One task/branch should have a bounded write scope.
- The implementation may change; the capability goal and scientific integrity do not.

## 7. Progress semantics

Two numbers are maintained:

**Goal progress (0-100):** demonstrated capability toward the ultimate goal. Only accepted weighted milestones count.

**Research coverage:** how much of the planned research/experimental search space has been investigated. This can rise without goal progress.

A negative experiment can increase research coverage while adding zero goal-progress points.

## 8. Continuity protocol

Before ending a major overseer cycle, update `OVERSEER_HANDOFF.md` with:
- current verified progress;
- research coverage;
- last accepted task;
- active/review/blocked tasks;
- latest important finding;
- open decisions;
- next overseer action.

A future chat should be able to resume by reading this repository rather than relying on chat memory.
