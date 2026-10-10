# Autonomous task-branch publication

All execution agents publish their own scoped task branch with native `git push -u origin HEAD`. They do not wait for the user to tell them to push or create a PR.

On a remote push to `task/**`, [Task Branch Auto PR](workflows/task-branch-auto-pr.yml) verifies the pushed head, searches for an existing open PR, and uses a **scoped ephemeral GitHub Actions token** to open an ordinary review PR when no PR exists. It never merges, awards progress points, authenticates local private artifacts, or bypasses source/data gates.

The GitHub setting permitting Actions to create pull requests must be enabled for full no-intervention behavior; if disabled, Actions visibly fails and the agent must use an approved authenticated connector instead. Ordinary local Git credentials are still required to publish locally created commits. Keep secrets, image bytes, weights and private inference reports outside the repository.

## Live end-to-end smoke

This document was created as the first fresh `task/**` push after landing the workflow under `overseer/agent-auto-publish-pr-policy` (merged `bffe9b649f2c845fee0905423c212abaccd00c5d`). The first automatic PR creation attempt correctly failed with HTTP 403 because the GitHub repo policy disabled Actions-created PRs. After the owner explicitly enabled the repo setting, rerunning the same task-push workflow **succeeded**, creating [PR #152](https://github.com/m7mdehab/hieratic-ai/pull/152) automatically without a manual creation command: [run 38082195400, attempt 2](https://github.com/m7mdehab/hieratic-ai/actions/runs/38082195400).

The bot-created `pull_request` governance run was marked `action_required`; GitHub PR authorship can require separate approval for this class of event. Hence [PR #153](https://github.com/m7mdehab/hieratic-ai/pull/153) adds full **push-triggered task-branch governance** with `git merge-base origin/main HEAD` write-scope checking. This ensures task code is audited automatically on push even when the bot PR event is held for approval.

The next commit to this same test branch tests both that a second task-branch push does **not** create a duplicate open PR and that hosted task-branch push governance actually passes. Verify the exact run results and retain the evidence; never claim the automatic process includes model-specific workflows that have not been independently replayed.
