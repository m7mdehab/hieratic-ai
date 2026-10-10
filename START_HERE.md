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
- dispatch of newly unblocked work;
- selection of a substantive overseer-owned task for every safe parallel work wave;
- execution of the assigned, nonconflicting overseer task after Mohammed has received/forwarded the prompts and returned to the overseer chat to start the synchronized parallel work;
- a complete user-facing status report after every returned agent task/revision is reviewed.

### Execution agents

Execution agents implement bounded tasks from explicit briefs. They do not redefine project goals, success metrics, benchmark splits, licensing rules, or task weights unless the task explicitly authorizes it.

The intended cycle is:

`research/reason -> wave plan + agent prompts + overseer assignment -> user dispatches agents once -> agents implement, test, commit and automatically push task branches -> GitHub automatically opens review PRs when permitted -> agents report exact remote SHA, PR and hosted CI -> overseer independently reviews/merges -> state update -> next wave`

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
- Every returned execution-agent result must receive an overseer review before acceptance.
- Every overseer review must end with the standardized status report defined in `docs/governance/REVIEW_REPORTING_PROTOCOL.md`.
- Parallel work is preferred when dependencies and file ownership make it safe.
- Every dispatch wave should include meaningful overseer work when a dependency-safe, high-value task exists; the overseer must not sit idle merely because execution agents are running.
- Before dispatch, the overseer presents each lane's assignment and writes copy-ready prompts. Once Mohammed sends a prompt to an agent, the agent starts immediately; no second approval or planning-only reply. The overseer waits for Mohammed to return after forwarding the agent prompts, then starts its own nonconflicting work immediately without requesting a separate formal approval. Spending, restricted data, protected evaluation and other explicit external gates remain separate.
- One task/branch should have a bounded write scope.
- Each agent must push its task branch autonomously and ensure a remotely reviewable PR exists; no manual user relay or post-handoff push request. GitHub workflow `.github/workflows/task-branch-auto-pr.yml` auto-opens nonduplicate task PRs after branch pushes, subject to repository Actions permissions; native Git push must work without relying on `gh` CLI authentication. See `AGENTS.md` for fail-closed fallback.
- The implementation may change; the capability goal and scientific integrity do not.

## 7. Progress semantics

Two project-level numbers are maintained:

**Goal progress (0-100):** demonstrated capability toward the ultimate goal. Only accepted weighted milestones count.

**Research coverage:** how much of the planned research/experimental search space has been investigated. This can rise without goal progress.

A negative experiment can increase research coverage while adding zero goal-progress points.

Review reports may also show operational percentages such as task acceptance-criteria completion or control-plane gate completion. These must be labeled separately and must never be conflated with verified goal progress.

## 8. Review reporting protocol

Whenever Mohammed brings back execution-agent feedback, a PR, commit, evidence package, or remediation result, the overseer must inspect the actual evidence and then report:

- verdict: accepted / revision required / rejected;
- what has been completed;
- what remains pending;
- task acceptance checklist with completed items checked and incomplete items unchecked;
- verified goal progress and how much remains;
- research coverage;
- current phase earned points / phase weight;
- relevant operational gate/task completion;
- next checklist, including newly unblocked work.

The authoritative format is defined in `docs/governance/REVIEW_REPORTING_PROTOCOL.md`.

## 9. Continuity protocol

Before ending a major overseer cycle, update `OVERSEER_HANDOFF.md` with:
- current verified progress;
- research coverage;
- last accepted task;
- active/review/blocked tasks;
- latest important finding;
- open decisions;
- next overseer action.

A future chat should be able to resume by reading this repository rather than relying on chat memory.
