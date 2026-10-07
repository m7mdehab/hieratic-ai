# Overseer Handoff — Hieratic AI

**Last reconciled:** 2026-10-08, approved W2 overseer batch complete. `PROJECT_STATE.yaml` and `TASKS.yaml` on `main` are authoritative; this document is a compact, derived handoff.

## Verified project progress

- **20.5 / 100 earned; 79.5 remaining.** Research coverage **14%** (unchanged).
- Current capability phase P2 Evaluation: **8.5 / 10 (85%)**; P1 Foundation **5 / 5 (100%)**; P3 Data Engine **7 / 20 (35%)**; P4–P8 no earned points.
- Control-plane acceptance **4/5 (80%)**; CTRL-003 still active/revision-required, awaiting Anti-Gravity response.
- **Validated experiments:** 0; **trained models:** 0; **demonstrated unseen Hieratic reading:** not yet established.
- Last accepted weighted task: **EVAL-006 (+2)**.
- EVAL-003 remains **active** but earns **0/1.5** until actual authorized frontier inference and independent official scoring.

## W2 overseer results — completed

1. **EVAL-006 sealed evaluation and contamination-release protocol:** implementation PR [#35](https://github.com/m7mdehab/hieratic-ai/pull/35) + cross-layer integrity PR [#40](https://github.com/m7mdehab/hieratic-ai/pull/40), independently checked, merged. Frozen policy is `eval/sealed/protocol.yaml`, task acceptance `tasks/EVAL-006.md`; validator `eval/sealed/protocolctl.py` and redacted diagnostic validator `eval/sealed/report_audit.py`. Machine gates cover prerun hashes, custodian/scorer/developer separation, item rights and benchmark overlap, failures/abstentions/denominator reconciliation, document-level uncertainty, multiple experts, contamination response and staged release.
2. **EVAL-003 benchmark preflight hardening:** PR [#38](https://github.com/m7mdehab/hieratic-ai/pull/38) merged. `eval/baselines/public_freeze.py` externally freezes/reverifies 116 public script-ID and 150 public sign item-rung records and upstream prompt-source SHA against the exact EVAL-002 pinned checkout. Provider inference remains **unapproved and unexecuted**; exact rendered prompts must still be frozen before paid runs.
3. **Cross-layer evidence gates:** PR #40 adds 21 new synthetic tests and structure for EVAL-001 metric ID/unit/profile consistency, scorable-gold denominators including refusals/abstentions, stage-specific claims, document-clustered intervals and paired comparison integrity.

Latest GitHub CI for PR #40: **34 governance + 51 data + 145 evaluation tests passed**, approved six-file task scope. PR #38 dedicated baseline CI reproduced the pinned public metadata+prompt-source freeze and verified it. No new source images, benchmark gold, trained models, provider credentials, or actual model calls.

## W2 Luna package — user copy-ready dispatch issued

Four **dependency-ready but not yet validated** independent tasks:

- DATA-003 — deterministic preprocessing and dataset versioning (3 points)
- DATA-005 — sign identity and palaeography mappings (2 points)
- DATA-006 — image-to-transliteration alignment with ambiguities (3 points)
- DATA-007 — expert QA/adjudication and uncertainty (2 points)

Write scopes for Luna's four branches, and EVAL-006, were preregistered in governance PR [#34](https://github.com/m7mdehab/hieratic-ai/pull/34) and merged before start. Luna work is 10 potential points, but only after independent PR tests/review. Prevent DATA-006 from building on locally completed unvalidated DATA-003; both must use *accepted* DATA-002/DATA-004 interfaces. Real manuscript use requires independent licenses and image/benchmark clearance.

The Anti-Gravity lane (Sonnet **or** Gemini 3.8 Flash, not both) continues CTRL-003 PR #27. Earlier review found stale canonical-state snapshots, 320px layout defects and missing final npm audit/accessibility evidence. Do not self-accept any revisions without checking the actual new head and CI.

## Core scientific guardrails

- Script ID, sign recognition, Hieratic grapheme sequences, hieroglyphic rendering, transliteration, normalization and translation have separate metrics; no composite-primary or fluent hallucination claims.
- EVAL-002 reproduces a *historical upstream* HieraticBench run and uses pinned SHA `d587dc990013f18007f1e7a8f56f96ff2f7127e2`; 268 items (266 public + 2 sealed) remain evaluation-only. Public benchmark near-duplicates cannot train/dev.
- A machine-valid `review.status: clear` does not independently prove data rights or exhaustive overlap comparison; human evidence is mandatory.
- EVAL-006 **policy freeze** is not the same as an actual frozen sealed corpus, scored blind evaluation or generalization result.
- Agents cannot alter canonical progress/weights or self-validate; overseer reviews CI/code/rights and merges separate acceptance state PRs.

## Exact next steps

1. Finalize/merge EVAL-006 acceptance state PR after independent green governance CI.
2. Review Luna DATA-003/005/006/007 PRs as they arrive, task by task; do not mark ready tasks validated early.
3. Independently review Anti-Gravity CTRL-003 final state integration, 320px screenshots, npm security/license audit and evidence; control gate only closes on verified acceptance.
4. Keep EVAL-003 active and do not authorize paid calls without the user's separate budget/credential approval; require actual raw response archive and official score reproduction for baseline credit.
5. Present next multi-lane wave with a substantive overseer task, and **obtain user approval before beginning it**.
