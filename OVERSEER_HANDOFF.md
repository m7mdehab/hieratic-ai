# Overseer Handoff — Hieratic AI

Updated: 2026-10-08. This file is a compact current handoff. Historical evidence remains in accepted PRs, DECISIONS.md and RESEARCH.md.

## Canonical status

- **Verified goal progress:** 11.5 / 100; remaining 88.5.
- **Research coverage:** ~14%, unchanged pending a defined denominator.
- **Phase 1 foundation:** 5.0 / 5 = 100%.
- **Phase 2 evaluation:** 4.5 / 10 = 45%.
- **Phase 3 data engine:** 2.0 / 20 = 10%.
- **Control-plane:** 3/5 accepted = 60%.
- **Validated experiments:** 0.
- **Trained models:** 0.
- **Last accepted task:** FND-006.
- **Currently active (last confirmed):** CTRL-003 in the Anti-Gravity/Sonnet lane.

See `PROJECT_STATE.yaml` for the current authoritative progress and `TASKS.yaml` for task dependencies/status.

## Current three-lane operating model

1. Luna: execution lane, normally 2–3 **independent ready** tasks in a larger package.
2. Anti-Gravity: **one** shared execution lane, Sonnet or Gemini 3.8 Flash (user chooses based on limits). It is not two simultaneous lanes.
3. Overseer: research, scientific methodology, architecture, review/integration.

User approves the full wave before overseer-owned work begins. Each accepted PR must have actual evidence inspected. Only accepted weighted tasks earn capability points.

## Latest completed wave: EVAL-002

**EVAL-002 — ACCEPTED**, merged in PR #21 (implementation) and the follow-up canonical state PR.

Verified external HieraticBench:
- pinned official SHA `d587dc990013f18007f1e7a8f56f96ff2f7127e2` / harness `0.1.0`;
- 268 items = 266 public + 2 sealed, 150 public single-sign examples, 118 identify-eligible images;
- 13 model rows in published snapshot;
- no public answer key/scored transliteration or translation for the single secret sentence in two hands;
- original scoring rules are **not** to be replaced by our project EVAL-001 normalization;
- external benchmark and near-duplicates remain quarantined from training/dev.

Read-only CI proof: [HieraticBench audit run 37693626552](https://github.com/m7mdehab/hieratic-ai/actions/runs/37693626552), successful.
- 13 synthetic adapter tests passed;
- 8 upstream TypeScript scorer tests passed;
- 1,892 public scored/unscored run records checked;
- 1,738 per-item/model/rung means reproduced;
- 17 model/rung numeric aggregates matched;
- no benchmark images or secret answers checked out/committed.

Files:
- `docs/evaluation/HIERATICBENCH_REPRODUCTION.md`
- `eval/benchmarks/hieraticbench/manifest.yaml`
- `eval/benchmarks/hieraticbench/adapter.py`
- `eval/benchmarks/hieraticbench/README.md`
- `tests/evaluation/test_hieraticbench_adapter.py`
- `.github/workflows/hieraticbench-audit.yml`

EVAL-002 earned +2.0 points: 8.0 → 10.0. EVAL-003 is now **ready**.

## Other completed foundation work

- CTRL-001, CTRL-002, CTRL-004: canonical operating system, state validator/context CLI, CI governance.
- FND-001 to FND-005: mission/scope, feasibility, Hieratic problem map, prior-art/data research, deny-by-default licensing/provenance policy.
- EVAL-001: versioned layered metrics/normalization/uncertainty evaluation contract; no primary composite score in v1.
- DATA-001: machine-readable 8-source registry, policy validator and tests.

## Pending work and dependencies

- **Luna approved W1 large package:** DATA-002 (2 points), DATA-004 (3), EVAL-004 (2). Brief `tasks/batches/LUNA-W1-LARGE.md`. Each task must have its own PR and reviewed acceptance.
- **Anti-Gravity/Sonnet:** CTRL-003 dashboard/control plane. No accepted return yet.
- **FND-006** (0.5) validated via PR #29 and follow-up state acceptance; Phase 1 closed.
- **EVAL-003** (1.5) active in overseer lane because EVAL-001 + EVAL-002 are validated.
- **EVAL-005** (1.0) validated (PR #25/#26).
- DATA-003, DATA-005, DATA-006, DATA-007 and EVAL-006 have additional dependency gates and must not start merely because an unreviewed Luna task appears locally complete.

## Required next overseer behavior

1. Review each Luna W1 PR from source code, tests, CI, scientific methodology, provenance, and branch scopes.
2. Review Sonnet CTRL-003 when returned; audit against canonical state and responsiveness.
3. Give the user a **full checked/unchecked report**, task evidence %, earned/remaining goal %, research coverage, phase and control-plane gate status, blockers, and exact point changes.
4. Update canonical state and merge accepted PRs; issue precise revision briefs otherwise.
5. Prepare the next approved parallel wave with a substantial overseer-owned task; avoid assigning a task that collides with unresolved branches.

Do not treat source repository code, scientific claims, or leaderboard results as model training data. Do not pretend the public HieraticBench sealed reading can be scored automatically.

## Latest overseer parallel task — EVAL-005

**Accepted and merged via PR #25**, with canonical acceptance recorded in a follow-up PR. Adds 48 coded failure categories spanning 16 layers; an evidence-linked review JSON Schema; a deterministic CLI with causal/reference/gold/contamination checks; synthetic examples; 23 new tests; and a dedicated CI workflow. The evaluation suite ran 36 tests and governance/analysis CI passed.

Research: errors are observations requiring adjudication, not model accuracy rates. Sealed record details do not appear in public summaries. Gold ambiguity and contamination prevent spurious confirmed reading claims.

Goal progress +1.0: 10.0 → 11.0. EVAL-006 still depends on Luna's EVAL-004.

## Latest execution-lane visibility

Luna PRs #20 (DATA-002) and #23 (DATA-004) were visible open at the latest check; EVAL-004 return still pending. No GitHub branch or PR for Sonnet's CTRL-003 was visible; work may be local/unpushed. The overseer cannot inspect Anti-Gravity's active internal session and should ask Mohammed to request a pushed WIP checkpoint, test/build status, blockers, and remaining checklist.

## W1 Luna package — overseer revision review (2026-10-08)

All three tasks have substantive implementations, separate open PRs and passing governance CI, but **all remain unaccepted pending targeted scientific/control-plane corrections**:

- DATA-002 / PR #20: conditional PER-ITEM acquisition allows self-declared evidence and reviewerless `ALLOWED WITH RECORDED CONDITIONS`. Require explicit item license/rightsholder, reviewer signoff, benchmark-overlap assessment, adversarial tests. Comment 6048205649.
- DATA-004 / PR #23: a `certain` gold value may have no `selected_value_id` and page reading_order permits duplicate region references, corrupting evaluation gold. Comment 6048206126.
- EVAL-004 / PR #24: configured benchmark roster lists only two sealed items while HieraticBench also has 266 public items including 150 AKU-PAL sign crops; high-risk unreviewed items can enter train/dev. Require evidenced overlap clearance or fail closed. Comment 6048206647.

Statuses are `revision_required`. Goal progress **11/100**; research coverage **14%**; Phase 1 **4.5/5**; Phase 2 **4.5/10**; Phase 3 **2/20**; control plane **3/5**; trained models and verified experiments **0**. No downstream tasks unblocked.

Sonnet has pushed draft PR #27 (the earlier no-branch checkpoint is superseded); reviewer posted stale-state tests, mobile layout bugs, accessibility, audit and final QA requirements. Not accepted.

Next: Luna fixes the three existing PR branches, Sonnet fixes #27, overseer proposes independent EVAL-003 scientific-baseline task for the next approved wave.

## FND-006 completed and EVAL-003 commenced

FND-006 merged via PR #29: evidence/experiment JSON Schemas, approved PR branch scopes, CI diff-scope enforcement, 16 new synthetic contract tests, and complete governance/data/evaluation CI coverage. Proof: [Actions run 37697693576](https://github.com/m7mdehab/hieratic-ai/actions/runs/37697693576): 34 governance + 13 data + 36 evaluation = **83 tests passed**; eight changed task files matched the approved scope. No third-party assets/experiments were added.

Award +0.5: **11.0 -> 11.5/100**, Phase 1 **5/5**. Current capability phase now **P2_EVALUATION**; P2 remains **4.5/10**. GATE-CONTROL still incomplete because CTRL-003 dashboard remains in revision/draft.

EVAL-003 is **active** in overseer lane. Distinguish protocol/tooling completion from verified untuned model runs: no API credentials/budget or fresh runs have been approved; no EVAL-003 points are yet available. Existing upstream HieraticBench leaderboard belongs to EVAL-002 and cannot be passed off as new local inference.


## EVAL-003 pre-registered baseline system — staged, not validated

Merged [PR #31](https://github.com/m7mdehab/hieratic-ai/pull/31) on 2026-10-08. Dedicated and existing CI passed: **34 governance, 13 data, 57 evaluation tests**, including 21 new offline frontier-baseline tests. The baseline preflight intentionally fails without authorizing real provider execution.

Files:
- `tasks/EVAL-003.md`
- `eval/baselines/suite.yaml` and `suite.schema.json`
- `eval/baselines/baselinectl.py`
- `docs/evaluation/FRONTIER_BASELINES.md`
- `tests/evaluation/test_frontier_baselines.py`
- `.github/workflows/frontier-baselines.yml`

**Do not claim EVAL-003 completed.** It remains `active`, earns **0/1.5 points**, and has no model runs/validated experiments. The complete scientific baseline still needs immutable public item/prompt snapshots, verified actual model IDs/configs, credential/terms review, explicitly approved spending cap, private artifact storage, actual untuned inference, upstream official scoring and independent acceptance. Published EVAL-002 scores are not fresh runs.

Current project numbers: **11.5/100** verified, **88.5 remaining**, research coverage **14%**, P1 **5/5 complete**, P2 **4.5/10**, P3 **2/20**, 0 experiments, 0 models. Control gate **4/5 core constituents complete?** The five-item tracker includes CTRL-001 to CTRL-004 plus FND-006, so **4/5** (CTRL-003 alone remaining). Three CTRL core tasks + FND-006 verified.

Agent PRs were still open at last checkpoint; #20 and #23 received new commits after remediation comments, #27 had a new commit and was no longer a draft; #24 remained at its earlier SHA. These updates **have not yet been overseer-reviewed or accepted**.

Next: when Mohammed brings the combined Luna/Sonnet feedback, inspect actual post-review diffs, CI, rights/overlap test evidence; then decide acceptance task by task. Do not auto-advance DATA-003/EVAL-006 until validated prerequisites.
