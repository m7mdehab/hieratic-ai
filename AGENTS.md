# Agent Operating Contract

These rules apply to every execution agent regardless of provider or model.

## Before work

Read:
1. `START_HERE.md`
2. this file
3. your assigned task brief
4. only the dependencies/files explicitly referenced by the task unless more context is necessary

If the task brief conflicts with a canonical accepted decision, stop and report the conflict.

## Dispatch is execution authorization

When Mohammed sends or forwards a concrete task/continuation prompt, **start its authorized work immediately**. Do not ask for a second approval, repeat the wave plan as a substitute for implementation, or claim that work will begin later. Complete all dependency-safe, within-scope work and return evidence. If a missing external capability prevents one portion, execute independent portions and report the exact remaining blocker.

The prompt does **not** authorize paid model inference, nontrivial spending, use of restricted/uncleared third-party data, secret disclosure, irreversible destructive activity, or release/unblinding of sealed material. Those operations remain separately gated. Never self-approve your own PR, capability points, task status or scientific claims.

## Your role

Execution agents are implementation workers. They are expected to execute a bounded specification well, not redesign the program.

You may make local implementation decisions when all of the following are true:
- the decision is reversible;
- it stays inside the task's declared write scope;
- it does not change project goals, evaluation semantics, data licensing, benchmark splits, task weights, public claims, or cross-task interfaces;
- it does not create a new external dependency with material security/licensing/maintenance impact.

Escalate instead of deciding locally when any of those conditions fail.

## Branch discipline

Use one primary task per branch:

`task/<TASK-ID>-<short-slug>`

Do not modify files outside the task's write scope without explicit authorization.

Parallel agents must not share mutable output directories or edit the same canonical file concurrently unless the overseer explicitly coordinates the merge.

## Automatic remote publication and PR handoff (mandatory)

**A local commit is not task completion.** When an execution agent finishes its within-scope work, it must autonomously publish the task branch to the canonical remote and hand over a remotely reviewable PR. This is part of the original task dispatch, not a separate user approval or follow-up request.

1. Verify the repo remote, current branch, latest commit and clean or explicitly accounted-for working tree. Keep unrelated user changes, credentials, private inference ledgers, copyrighted pixels/weights and unapproved artifacts out of Git.
2. Run the task's local checks. Commit the scoped changes on `task/<TASK-ID>-<short-slug>` with a substantive message.
3. Publish with native `git push -u origin HEAD` using configured credential helpers or the agent's approved GitHub connector. **Do not assume that lack of `gh` CLI authentication prevents a normal Git push.** Do not ask the user to issue the push command or copy code between agents.
4. **PR creation is automatic on every task branch push** using `.github/workflows/task-branch-auto-pr.yml`, if repository Actions permissions allow it. Prefer the agent's authenticated GitHub connector or `gh pr create` to publish a complete acceptance/evidence description. Check for an existing PR before creating another; never create duplicate PRs. If automated opening fails, the agent must try an approved GitHub integration and report the exact auth/policy error to the overseer.
5. The final agent handoff must include actual remote branch URL, exact `origin/<branch>` SHA, PR URL/number (or a clear `PR_CREATION_BLOCKED` status), hosted check links/status where available, scoped changed files, test evidence, and source/rights/claim boundaries. **Never describe a local-only branch or past-wave CI as remotely verifiable W27 evidence.**
6. CI failure is not completion: fix within scope, push to the same branch, watch exact-head checks and repeat until they pass or a concrete externally blocked gate is identified. The independent overseer—not the execution agent—reviews, merges, and awards any scientific credit.

If `git push` fails due to credentials/host restrictions: use a previously approved connector/credential manager without revealing tokens. If no approved route works, export a precise patch/source archive without secrets and explicitly declare `REMOTE_PUBLICATION_BLOCKED`. Do not pretend the work was published, and do not wait for the user to ask whether it has been pushed.

## Scientific integrity

Never:
- train on evaluation/test/sealed material;
- move hard examples from test to train to improve metrics;
- report the best run without preserving the evaluation procedure;
- infer a license from convenience or availability;
- claim a paper/dataset/result was verified when it was not;
- fabricate citations, experiment outputs, benchmark numbers, or completed tests;
- silently drop failed examples or incompatible records;
- change metrics after seeing results merely to improve the headline number.

## Reproducibility

For experiments, record enough information to identify:
- task/experiment ID;
- Git commit;
- dataset/manifests and version;
- train/dev/test split version;
- model/checkpoint;
- configuration/hyperparameters;
- random seed(s) where relevant;
- environment/dependencies;
- command or entry point;
- metrics/output artifacts;
- known failures/deviations.

## Required return package

Do not return only a prose summary. Return:

- task ID;
- branch and commit SHA;
- exact files changed;
- commands/tests run;
- test results;
- deliverables/artifact paths;
- acceptance-criterion checklist;
- deviations from brief;
- unresolved risks;
- licensing/provenance impact;
- suggested next steps only if directly implied by the implementation.

The overseer decides whether the task is accepted, revision-required, or rejected.

## Progress authority

Execution agents must not award themselves capability points or edit `PROJECT_STATE.yaml` progress numbers unless the task explicitly authorizes that exact state transition.

"Code written", "training completed", and "looks correct" are not equivalent to validated capability.


## Data rights and provenance

Before downloading, committing, transforming, or training on any third-party image, annotation, text corpus, edition, dataset, or model artifact, follow `docs/governance/DATA_LICENSING_AND_PROVENANCE_POLICY.md`.

Hard requirements:

- no asset with unknown/unclear rights may enter a training corpus;
- software licenses do not automatically license bundled source images/data;
- publication licenses do not automatically license the underlying dataset;
- benchmark/evaluation material must remain quarantined from training;
- per-item licenses must be recorded per item;
- non-commercial/restricted material must not silently contaminate a release intended for unrestricted reuse;
- provenance manifests and hashes are required before an asset is admitted;
- when rights are uncertain, record metadata only and escalate rather than copying the asset.

Execution agents may not downgrade a restriction or infer permission from public accessibility.
