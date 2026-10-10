# Automatic task PR publication — W27 governance smoke

**Status:** live verification on 2026-10-10. This scoped FND-006 task-branch file documents the automated publication contract and provides a real CI probe. **No scientific capability points are associated with this work.**

## Expected single-dispatch behavior

1. Every execution agent commits and autonomously runs native `git push -u origin HEAD`. An absent `gh auth login` is not grounds to skip native Git publishing. Agents never ask the user to relay standard Git operations.
2. The read-scoped, `pull-requests: write` [Task Branch Auto PR](../../.github/workflows/task-branch-auto-pr.yml) responds to `task/**` pushes and creates **at most one open PR per task branch**, based on the exact remote SHA. It cannot automatically merge, release restricted third-party material or award scientific scores.
3. The independently [governed task-push CI](../../.github/workflows/governance.yml) runs on `task/**` pushes directly, and applies the real changed-file write scope using `git merge-base origin/main HEAD`. This avoids depending exclusively on bot-created PR workflow events, which can require manual approval.
4. The actual PR is an overseer review request, not scientific acceptance. The agent must still provide evidence and the overseer approves/merges only after actual required checks pass.

## Reproduced original permission gate and resolution

- Initial auto-PR smoke [run 38082195400 attempt 1](https://github.com/m7mdehab/hieratic-ai/actions/runs/38082195400) failed with GitHub HTTP 403 because the repository disabled Actions-created PRs.
- User enabled **Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create and approve pull requests**.
- [The identical run, attempt 2](https://github.com/m7mdehab/hieratic-ai/actions/runs/38082195400), then succeeded, creating [PR #152](https://github.com/m7mdehab/hieratic-ai/pull/152) without manual PR creation.
- A second source push to that same task branch triggered [run 38083052566](https://github.com/m7mdehab/hieratic-ai/actions/runs/38083052566) and correctly kept the single existing PR (idempotence).
- The original bot-authored PR event yielded `action_required`; governance was therefore additionally made available on task branch push in [PR #153](https://github.com/m7mdehab/hieratic-ai/pull/153), merged `f09ff7142bcb4398f8f5501db3b72901408c5649`.
- Initial push-CI smoke used completed `CTRL-004`, not an active registered task scope, and correctly failed the hard gate. PR #154 was closed rather than bypassing the registry.

## Final exact-head acceptance

The commit adding this document, under registered **FND-006** allowed `docs/governance/**` scope, serves as the end-to-end test: GitHub must automatically open a new PR, full task-push Project Governance must run and pass on this exact commit, and no user or agent must manually create a PR. Record the run URLs and PR number in this review; a CI or source-scope failure is a genuine blocker.
