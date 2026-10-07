# Parallel Wave Protocol

**Status:** Mandatory  
**Effective:** 2026-10-08

## Purpose

Maximize useful project throughput while preserving dependency safety and centralized scientific judgment.

A dispatch is not complete when only execution agents receive work. When a substantial dependency-ready task is suitable for the overseer, the overseer must work too.

## Required pre-wave output

Before the overseer begins its own task, present Mohammed with a compact assignment table covering:

- Luna
- the Anti-Gravity execution lane (Sonnet **or** Gemini 3.8 Flash, whichever Mohammed says is currently available)
- the overseer

For each lane, state the assigned task, why that lane is appropriate, dependency status, collision risk, and expected project effect.

Also state:
- expected capability points if the task is weighted;
- expected infrastructure/gate movement if it is unweighted;
- what becomes newly unblocked if the task succeeds.

## Approval gate

The overseer waits for Mohammed's approval before beginning the overseer-owned task.

Already-dispatched execution agents may continue while that approval is pending.

## Overseer task-selection priority

Prefer, in order:
1. evaluation and scientific-method design;
2. architecture and interface contracts;
3. primary-source research and synthesis;
4. capability and task decomposition;
5. integration design;
6. high-risk analysis that benefits from centralized reasoning.

Do not choose clerical filler solely to appear busy.

## Concurrency safety

The overseer task must not:
- edit the same mutable files as an active agent unless deliberately coordinated;
- redefine an interface that an active agent is simultaneously implementing;
- create avoidable evaluation contamination;
- invalidate a live task brief without notifying the affected agent.

If overlap is unavoidable, serialize instead.

## End-of-wave synthesis

When Mohammed returns agent feedback, the overseer combines:
- each agent's reviewed result;
- the overseer's own completed work;
- state and percentage changes;
- newly unblocked tasks;
- unresolved blockers.

The next response should end with the next proposed parallel wave and the overseer assignment awaiting approval.


## Execution-lane topology

The default operating topology is **three concurrent lanes**, not four:

1. **Luna lane** — persistent execution lane for coding/tooling/implementation work.
2. **Anti-Gravity lane** — one shared execution lane using either **Sonnet** or **Gemini 3.8 Flash** at a time.
3. **Overseer lane** — research, architecture, evaluation, synthesis, and review-heavy work.

Sonnet and Gemini are not assumed to run concurrently. Mohammed decides which model occupies the Anti-Gravity lane based on current usage limits and availability.

When the Anti-Gravity model changes:
- the task identity does not automatically change;
- the replacement model must read the canonical repo state, task brief, and any task-specific handoff before continuing;
- prior model summaries are non-authoritative unless reconciled into the repository;
- the switch itself does not reset progress or create a new task;
- if the outgoing model leaves uncommitted/unreviewed work, the overseer decides whether the incoming model continues it or starts from the last accepted commit.

Wave plans should therefore name the lane first and the currently selected model second, for example:
`Anti-Gravity lane (Sonnet) -> CTRL-003`
or
`Anti-Gravity lane (Gemini 3.8 Flash) -> CTRL-003 continuation`.


## Luna work-package sizing

Luna may receive a **multi-task work package** rather than one small task when several independent tasks are simultaneously dependency-ready.

The goal is to keep the fast execution lane productive for approximately the same review cycle as the overseer lane without weakening task boundaries.

Requirements:
- every task in the package must already have all dependencies validated at dispatch time;
- each canonical task keeps its own task ID, acceptance criteria, evidence package, and preferably its own branch/PR;
- tasks in the same package should have disjoint or deliberately partitioned write scopes;
- Luna may finish the whole package before returning to the overseer;
- a task may **not** begin based on another package task merely being locally complete if the dependency requires overseer validation;
- no acceptance threshold is reduced because tasks are batched;
- the overseer reviews and awards points task-by-task.

Default sizing heuristic:
- target 2–3 independent Luna tasks per wave when that many suitable tasks are ready;
- prefer a mixed package of implementation/data/evaluation tooling rather than artificially splitting one tiny task;
- reduce the package if tasks share volatile interfaces or would cause merge conflicts.
