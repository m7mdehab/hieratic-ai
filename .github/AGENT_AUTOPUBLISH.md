# Autonomous agent branch publication and review

Every execution agent must finish its task by committing scoped changes and running native `git push -u origin HEAD`. A local GitHub CLI login is **not** required when existing native Git credentials or the approved GitHub integration can push. The user must not relay routine push/PR commands to the agents.

The [Task Branch Auto PR](workflows/task-branch-auto-pr.yml) workflow opens a **single**, review-only pull request when a `task/**` branch is pushed. It checks the exact pushed remote commit and existing PRs before creation. It never merges, grants data licenses or awards scientific milestone points. The action requires the repository's GitHub Actions setting **Allow GitHub Actions to create and approve pull requests**; owner enabled this on 2026-10-10.

The workflow was verified by [hosted run 38082195400, attempt 2](https://github.com/m7mdehab/hieratic-ai/actions/runs/38082195400), automatically creating [PR #152](https://github.com/m7mdehab/hieratic-ai/pull/152) without a user or overseer PR-creation command. A subsequent push to that same branch was processed successfully by [run 38083052566](https://github.com/m7mdehab/hieratic-ai/actions/runs/38083052566) and reused PR #152, proving no duplicate was created.

GitHub held the initial bot-created PR's governance event for approval (`action_required`, run 38082782616). To avoid relying on bot PR events, the [Task Branch Push CI guard](workflows/governance.yml) now also runs the full Project Governance suite on `push task/**`, validates full task write scope from the merge base, and reports CI independently on the submitted commit.

This file is published from a **new task branch based on the CI-enabled main** to verify both the auto-PR workflow and the task-push Project Governance workflow are triggered by a single normal branch push, without manual review dispatch. Source permissions, independent reviewer acceptance, any external model inference receipts and other specialist task-specific gates remain independent.
