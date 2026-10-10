# Autonomous task-branch publication

All execution agents publish their own scoped task branch with native `git push -u origin HEAD`. They do not wait for the user to tell them to push or create a PR.

On a remote push to `task/**`, [Task Branch Auto PR](workflows/task-branch-auto-pr.yml) verifies the pushed head, searches for an existing open PR, and uses a **scoped ephemeral GitHub Actions token** to open an ordinary review PR when no PR exists. It never merges, awards progress points, authenticates local private artifacts, or bypasses source/data gates.

The GitHub setting permitting Actions to create pull requests must be enabled for full no-intervention behavior; if disabled, Actions visibly fails and the agent must use an approved authenticated connector instead. Ordinary local Git credentials are still required to publish locally created commits. Keep secrets, image bytes, weights and private inference reports outside the repository.

## Live end-to-end smoke

This document was created as the first fresh `task/**` push after landing the workflow under `overseer/agent-auto-publish-pr-policy` (merged `bffe9b649f2c845fee0905423c212abaccd00c5d`). Its own branch must be turned into a nonduplicate pull request by the workflow without the user or overseer manually opening one. Hosted run, PR and exact head provide acceptance evidence; an unsuccessful run remains a visible blocker, not a substitute success claim.
