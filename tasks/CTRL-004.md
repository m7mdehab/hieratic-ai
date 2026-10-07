# CTRL-004 — CI Governance Checks and PR Guardrails

- **Task ID:** CTRL-004
- **Branch:** `task/CTRL-004-ci-governance`
- **Owner:** execution agent
- **Depends on:** CTRL-002 — validated
- **Status at dispatch:** ready
- **Primary write scope:** `.github/`, `tests/governance/`, `tools/`, minimal dependency/config files required for CI
- **Do not edit:** roadmap weights, research conclusions, benchmark/evaluation content, data licenses, or goal-progress values except when explicitly authorized by the overseer

## Context

CTRL-002 established the provider-neutral `projectctl` CLI and schemas. CTRL-004 turns those checks into repository guardrails so malformed state cannot be merged unnoticed.

The objective is not to build generic DevOps. It is to enforce the scientific/project-governance invariants already encoded in the repository.

## Objective

Add a lean GitHub Actions/PR governance layer that:

1. runs canonical state validation on every relevant pull request and push to `main`;
2. runs governance tests;
3. fails visibly on malformed task graphs, progress mismatches, dependency violations, or schema errors;
4. standardizes PR evidence so execution-agent work returns the information the overseer needs;
5. remains fast and maintainable.

## Required implementation

### GitHub Actions

Create a workflow under `.github/workflows/` that runs on:
- pull requests targeting `main`;
- pushes to `main`.

Use a current supported Python version compatible with CTRL-002 (3.11+).

Workflow steps should, at minimum:
- checkout repository;
- set up Python;
- install `requirements-projectctl.txt`;
- run `python -m tools.projectctl validate`;
- run `python -m unittest discover -s tests/governance -v`.

Keep permissions least-privilege. Read-only repository contents are sufficient unless a concrete step proves otherwise.

Use dependency caching only if it is simple and deterministic; do not add unnecessary CI complexity.

### PR template

Add `.github/pull_request_template.md` requiring:
- task ID;
- objective;
- branch/commit;
- exact files changed;
- tests/commands run and results;
- acceptance-criteria checklist;
- evidence/artifact links;
- deviations from brief;
- unresolved risks;
- licensing/provenance impact;
- benchmark/evaluation impact;
- explicit statement that the agent did not self-award progress unless authorized.

The template should be concise enough that agents actually complete it.

### Governance regression tests

Add tests that prove the validator fails for at least:
- progress mismatch;
- dependency cycle;
- invalid ready/active dependency state;
- phase/task weight inconsistency.

CTRL-002 already has unit coverage for these cases. Do not duplicate implementation for its own sake. Instead add only what is needed to prove the CI entrypoint and repository fixtures are correctly wired.

### Failure visibility

A failed validator/test command must cause a non-zero workflow result.

Do not swallow failures with `continue-on-error`, `|| true`, or equivalent.

## Acceptance criteria

- [ ] PR/push workflow exists and is syntactically valid.
- [ ] Workflow runs canonical project validation.
- [ ] Workflow runs governance tests.
- [ ] CI failure propagates when validation/tests fail.
- [ ] PR template captures the required overseer evidence package.
- [ ] No write/admin permissions are unnecessarily granted.
- [ ] Existing local governance tests still pass.
- [ ] No canonical progress/weights are changed merely to satisfy CI.

## Tests / evidence

Return:
- workflow file;
- PR template;
- any new tests;
- local validator output;
- local governance test output;
- GitHub Actions run URL/status from the PR if available;
- deliberate failing-case evidence, preferably a test/fixture proving non-zero failure without corrupting canonical main.

If GitHub Actions cannot run because of account/repository platform limits, report that precisely. The implementation can still be reviewed, but do not claim CI passed when no run occurred.

## Prohibited shortcuts

- duplicating project-state rules in YAML instead of invoking `projectctl`;
- suppressing failed commands;
- granting broad repository write permissions;
- hard-coding current progress values into the workflow;
- auto-editing canonical files to "fix" validation;
- merging a workflow that silently skips when governance files change.

## Evidence package on return

Return:
- task ID;
- branch and commit SHA;
- files changed;
- workflow triggers/permissions;
- commands/tests and outputs;
- Actions run link/status if available;
- acceptance checklist;
- deviations/risks;
- licensing/dependency impact.

Do **not** self-mark CTRL-004 validated.
