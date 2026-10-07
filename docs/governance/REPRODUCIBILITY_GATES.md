# Operational Reproducibility and Governance Gates

**Task:** FND-006  
**Version:** 1.0.0  
**Status:** Accepted / operational v1.0  
**Date:** 2026-10-08

## Scope and scientific boundary

FND-006 is the final **foundation-governance** milestone; it is not acceptance of the still-unfinished dashboard (CTRL-003) and does not certify actual trained models or dataset rights. It closes the tested **operating contract** for heterogeneous agents, task evidence, branch scopes, progress reconciliation, and experiment reproducibility.

This work makes existing policy enforceable at the interface level. Governance validators cannot independently verify that a remote API was genuinely called, that a museum grant is authentic, or that a submitted artifact reference is accessible. Those remain overseer review requirements.

## Canonical controls

| Control | Executable check | Enforced boundary |
|---|---|---|
| DAG, task status, weights and progress | `python -m tools.projectctl validate` | Invalid task transitions and inflated verified progress fail |
| DATA-001 source registry | `python -m tools.source_registry validate` | Source registry schema/rights decisions remain parseable |
| Agent evidence package | `python -m tools.governance_contract evidence --input path.yaml` | Branch/SHA/files/test evidence/acceptance/legal risks present and self-award false |
| Task write scope | `python -m tools.governance_contract scope --task-id FND-006 --file tools/governance_contract.py` | Unauthorized writes fail closed |
| Experiment record | `python -m tools.governance_contract experiment --input record.yaml` | Validated experiments require immutable provenance, predictions, scores and config |
| Python tests | `python -m unittest discover -s tests/governance -v`, `-s tests/data`, `-s tests/evaluation` | Negative regression tests remain enforceable |

The authoritative source of each task's allowed paths is `docs/governance/TASK_WRITE_SCOPES.yaml`. This is an additional *machine-policy index* for scopes—not a new status database. When a task's accepted brief or write scope changes, update both its brief and this index through overseer review. An unregistered `task/<TASK-ID>-...` PR must fail CI until its approved scope is registered.

## CI and branch discipline

`.github/workflows/governance.yml` now executes:
- existing projectctl/schema/task DAG checks;
- the source registry validator;
- all governance, data, and evaluation tests, including the accepted EVAL-001/002/005 suites;
- PR-branch task write-scope enforcement based on the **actual Git diff against the target base**, not an agent's self-reported file list.

No write permissions or credentials are required. Scope matching uses task ID from the incoming GitHub branch name and a registry that defaults to refusal for unknown task IDs. State/governance branches intentionally do not claim to be a single execution-agent task; they still run every other governance check.

**Caveat:** CI on the PR's current branch is not a substitute for branch-protection requirements or post-merge smoke tests. GitHub environment permissions and required-check settings must be verified separately for production deployment.

## Evidence bundle semantics

`schemas/agent_evidence.schema.json` captures:
- canonical task ID, task branch, actual 40-character Git commit hash and pull request;
- asserted changed files;
- command/status/summary with evidence reference;
- individual acceptance checks, evidence links, output artifacts;
- deviations, unresolved risks, licensing and third-party assets;
- explicit `self_awarded_progress: false`.

The separate CI scope check verifies the actual changed files. If claimed files disagree with the Git diff, the overseer must reject or require correction. A self-authored `status: passed` does not prove the command succeeded; the overseer verifies CI logs.

## Experiment reproducibility semantics

`schemas/experiment_record.schema.json` supports planned/running/completed/validated/invalidated records.

To be *structurally eligible* for validated status, an experiment requires:
- immutable 40-character code commit;
- dataset and split versions;
- named model/checkpoint;
- actual model/config parameters;
- seed(s);
- dependency/runtime environment;
- reproducible entry point;
- metric results;
- hashed output artifacts including raw predictions, scores and config;
- recorded conclusion and provenance review.

Actual model experiment validity also requires independent comparison to the accepted EVAL-001 metric/scoring contract, proper leakage-split clearance, FND-005 data rights and, where relevant, expert review. A syntactically valid experiment object **does not** itself increment `state.validated_experiments`. Only a reviewed canonical transition may do so.

## Parallel-agent and release discipline

1. An agent executes only its approved write scope and returns the completed evidence package.
2. The overseer reviews actual Git changes, test outputs, dependency rights, and task acceptance criteria.
3. Revision-required tasks remain unweighted until corrected; no partial points are awarded.
4. Every accepted task yields a status report and a distinct canonical state update.
5. Luna receives multiple **independently dependency-ready** tasks per package where safe.
6. Sonnet and Gemini share one Anti-Gravity lane. Provider switches do not duplicate work.
7. The overseer takes a substantial independent task after wave approval.
8. A sealed test, benchmark or rights-unknown source never becomes training/dev data.

## FND-006 acceptance checklist

- [x] Canonical validation/weight reconciliation operational and passing on current `main`.
- [x] Evidence + experiment schemas, validators, and fail-closed scope policy created.
- [x] Cross-domain governance/data/eval negative test suites pass under CI.
- [x] CI checks actual task-branch diff scope.
- [x] Agent/handoff/reproducibility constraints documented with clear human-verification limits.
- [x] No third-party data or fictitious model results introduced.
- [x] Separate overseer acceptance with verified CI, then award +0.5 points.

FND-006 completing does not close `GATE-CONTROL` while CTRL-003 is still unaccepted; it completes the remaining research-foundation item.
