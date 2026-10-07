# Operating Model v0.1

## Core principle

Global reasoning is centralized; local execution is parallelized.

The overseer maintains a coherent research program and gives execution agents bounded, evidence-driven work. Agents are interchangeable implementation resources, not independent project managers.

## Lifecycle

1. **Research / reason** — overseer determines what capability or infrastructure is actually needed.
2. **Specify** — overseer writes a task brief with dependencies, scope, interfaces, acceptance criteria, tests, and prohibited shortcuts.
3. **Dispatch** — every dependency-safe task may be assigned in parallel.
4. **Execute** — agent works on an isolated branch/worktree.
5. **Return evidence** — agent provides code/artifacts plus test/evaluation evidence.
6. **Audit** — overseer inspects actual changes and evidence, not only the summary.
7. **Report** — overseer gives Mohammed the mandatory completion/pending/progress/checklist status report.
8. **Verdict** — accepted, revision-required, or rejected.
9. **Integrate** — accepted work merges; canonical state updates.
10. **Unblock** — newly dependency-safe tasks are dispatched.

## Task verdicts

**Accepted**
: all required criteria and evidence are satisfied. Weighted tasks may earn their points.

**Revision required**
: the core direction is usable but one or more acceptance criteria are unmet. The overseer issues a bounded remediation brief.

**Rejected**
: implementation is unsafe, methodologically invalid, non-reproducible, outside scope, or not worth repairing.

## Mandatory review response

Every time an execution-agent result or remediation result is brought back for review, the overseer must produce a user-facing review report following `REVIEW_REPORTING_PROTOCOL.md`.

The report is mandatory even when:
- the task is fully accepted;
- no goal-progress points change;
- the work is an unweighted control-plane task;
- the returned result is incomplete;
- the agent reports success but evidence is missing.

The report must distinguish:
- **verified capability progress** from
- **research coverage** from
- **operational/task completion**.

This prevents infrastructure progress, partial acceptance criteria, or agent-reported completion from being mistaken for scientific capability.

## Parallelization policy

Parallel by default if:
- dependencies are satisfied;
- write scopes do not collide materially;
- outputs meet an already-defined interface;
- tasks do not mutate the same benchmark/test split;
- tasks do not independently redefine canonical schemas.

Serialize or coordinate when:
- one task establishes an interface another consumes;
- both tasks change canonical state;
- both write the same data artifact;
- evaluation leakage is possible;
- integration cost is likely to exceed throughput gain.

## Safe concurrency

Preferred:
- task-specific branches/worktrees;
- immutable/versioned experiment inputs;
- deterministic manifests;
- task-specific artifact directories;
- merge through reviewed PRs.

Avoid:
- multiple agents directly editing `main`;
- shared mutable notebooks/checkpoints;
- agents choosing their own benchmark splits;
- independent copies of the same project state.

## State updates

Execution agents do not mark themselves accepted.

After acceptance, the overseer updates:
- task status/evidence;
- goal progress if weighted;
- research coverage when justified;
- last accepted task;
- handoff;
- decisions/experiments if affected.

The status report shown to Mohammed must reflect the **post-review canonical state** when the state update has already been applied, or explicitly say that the displayed state is **pre-merge/pre-state-update** when it has not.

## Adaptation

Methods, models, and tools may change rapidly. When evidence invalidates an assumption:
- record the finding;
- update the decision log;
- revise affected task briefs;
- version the roadmap/schema if required;
- preserve old evidence;
- never rewrite history to make the project appear more linear than it was.
