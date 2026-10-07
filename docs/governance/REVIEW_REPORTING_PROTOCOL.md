# Overseer Review & Status Reporting Protocol

**Status:** Mandatory  
**Applies to:** every execution-agent result, PR, commit, evidence package, remediation response, or other implementation feedback brought back to the overseer for review.

## Purpose

The user should never have to infer project state from a technical code-review response.

After each review, the overseer must make four things immediately clear:

1. what the agent actually completed;
2. what is still incomplete or needs revision;
3. exactly where the project stands numerically;
4. exactly what happens next.

This protocol is user-facing governance. It does not change scientific acceptance criteria or award capability points by itself.

## Review order

The overseer must:

1. identify the task/PR/commit being reviewed;
2. inspect the actual diff, files, tests, artifacts, metrics, and evidence available;
3. compare evidence against the task brief and canonical acceptance criteria;
4. identify scope violations, regressions, unsupported claims, licensing/provenance issues, or missing evidence;
5. assign one verdict:
   - **ACCEPTED**
   - **REVISION REQUIRED**
   - **REJECTED**
6. update canonical state when appropriate;
7. produce the mandatory status report below.

Do not accept a task from the execution agent's prose summary alone when the repository/artifacts are available.

## Mandatory user-facing report

Every review response must contain the following sections.

### 1. Review verdict

State:
- task ID and title;
- branch/PR/commit when known;
- verdict;
- one concise reason.

### 2. Completed in this review

Use checked checklist items.

Example:

- [x] State validator implemented
- [x] Dependency-cycle detection tested
- [x] Context generator produces task-specific packets

Only check items that the overseer has verified.

### 3. Still pending / revision required

Use unchecked checklist items.

Example:

- [ ] Progress mismatch fixture does not yet fail correctly
- [ ] Add licensing note for new dependency

If nothing remains for the reviewed task, explicitly state:

- [x] No remaining acceptance criteria for this task

### 4. Acceptance-criteria score

Show operational completion for the reviewed task as:

`verified criteria satisfied / total auditable criteria`

and, when useful:

`task evidence completion = X%`

This is an **operational review percentage**, not goal progress.

Do not award fractional project capability points merely because some acceptance criteria passed. A weighted milestone earns its roadmap points only when its acceptance gate is satisfied according to the roadmap/task rules.

### 5. Project status after review

Always report:

| Metric | Required value |
|---|---|
| Verified goal progress | X / 100 |
| Goal remaining | 100 - X |
| Research coverage | Y% |
| Current capability phase | phase name |
| Current phase progress | earned weighted points / phase weight |
| Validated experiments | count |
| Trained models | count |
| Last accepted task | task ID |
| Control-plane / relevant gate | status or verified completed/total tasks |

If a number cannot be established from canonical state, say **unknown / not yet measured** rather than inventing it.

### 6. Phase progress snapshot

Show P1-P8 with:
- earned verified points;
- phase weight;
- checked state only for fully earned/validated milestones.

A compact table is acceptable. Do not treat unweighted control-plane work as capability progress.

### 7. Next checklist

Show the immediate dependency-aware next actions.

Use:
- [x] for already completed prerequisite items;
- [ ] for pending items.

Group when useful:
- current task remediation;
- parallel active work;
- newly unblocked work;
- overseer-owned research.

Do not list distant roadmap items unless they are needed to understand immediate sequencing.

### 8. Percentage-change note

Explicitly state whether the review changed:
- verified goal progress;
- research coverage;
- operational gate/task completion.

If a metric did not change, say so.

## Compact example

### Review verdict — CTRL-002
**ACCEPTED.** Validator, context generation, and required tests are verified.

### Completed
- [x] YAML/schema validation
- [x] DAG cycle detection
- [x] Goal-progress reconciliation
- [x] Overseer context packet
- [x] Task-specific context packet

### Pending
- [x] No remaining acceptance criteria for CTRL-002

**Task evidence completion:** 5/5 = 100%

### Project status
- **Verified goal progress:** 2.5 / 100
- **Remaining:** 97.5
- **Research coverage:** 14%
- **Phase 1:** 2.5 / 5
- **Control-plane gate:** 2/4 core implementation tasks validated

### Next
- [x] CTRL-001 bootstrap
- [x] CTRL-002 validator/context tooling
- [ ] CTRL-003 dashboard shell
- [ ] CTRL-004 CI governance
- [ ] FND-003 problem map
- [ ] FND-004 verified research/data registry

**Change this review:** goal progress +0.0; research coverage +0.0 unless separately justified; control-plane completion increased.

## Precision rules

- The checklist reflects verified evidence, not agent self-report.
- "Merged" is not synonymous with "scientifically validated" unless acceptance occurred.
- "100% task evidence completion" is not "100% project completion."
- Infrastructure work may advance a mandatory gate while changing goal progress by 0.
- Research coverage changes only when actual planned research space has been investigated and recorded.
- If review reveals prior progress was overstated, correct the canonical state and state the correction explicitly.
- If canonical state and repository evidence disagree, report the inconsistency before presenting final percentages.
