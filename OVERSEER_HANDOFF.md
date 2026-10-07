# Overseer Handoff — Hieratic AI

**Latest authoritative review:** 2026-10-08, Luna W1 corrected submissions accepted. Check `PROJECT_STATE.yaml` and `TASKS.yaml` on current `main` for authoritative live status; earlier archived handoffs and task briefs are historical evidence.

## Live project snapshot

- **Verified goal progress:** 18.5 / 100 (81.5 remaining).
- **Research coverage:** 14%, unchanged; do not conflate with capability.
- **Current capability phase:** P2 Evaluation.
- **P1 Foundation:** 5 / 5, 100%.
- **P2 Evaluation:** 6.5 / 10, 65%.
- **P3 Data Engine:** 7 / 20, 35%.
- **P4–P8:** 0 earned.
- **Control-plane gate:** 4 / 5 = 80%; CTRL-003 still requires reviewer approval.
- **Validated experiments:** 0. **Trained models:** 0. **Demonstrated HTR/generalization:** none.
- **Last accepted task:** DATA-002 (last merged within W1).

## Accepted W1 execution artifacts

All three were independently source-reviewed and corrected; final PR branches passed GitHub governance CI and exact file-scope checks before merge.

| Task | PR | Points | Accepted deliverables |
|---|---|---:|---|
| DATA-002 | #20 | 2.0 | Rights/provenance-aware metadata acquisition planner with reviewer + item-license + benchmark-overlap clearance gates, no actual ingestion |
| DATA-004 | #23 | 3.0 | Hieratic reading/annotation schema with certain/alternative gold, reviewer, layout, token and sign relations; rejects unselected certain readings, repeated reading-order entries, cycles and invalid cross-line refs |
| EVAL-004 | #24 | 2.0 | Deterministic document/scribe/source/period split planning, near-duplicate audit queue, high-risk benchmark item exclusion pending recorded independent clearance |

**W1 verified capability delta +7.0:** 11.5 → 18.5 points. Research coverage still 14%. The source-registry and rights policy are **deny-by-default**. An accepted *planner* is not a human-approved, licensed source asset. EVAL-004 benchmark roster is **aggregate-only** and a recorded clearance attestation is not automatic proof that an image is novel. No production training/dev corpus or sealed evaluation split has been certified.

CI for DATA-002 final rebased branch: [run 37699384109](https://github.com/m7mdehab/hieratic-ai/actions/runs/37699384109); 34 governance, 51 data, 78 evaluation tests and nine-file scope passed.
CI for DATA-004: [run 37698566109](https://github.com/m7mdehab/hieratic-ai/actions/runs/37698566109); 34 governance, 32 data, 57 evaluation tests and six-file scope passed.
CI for EVAL-004: [run 37698578242](https://github.com/m7mdehab/hieratic-ai/actions/runs/37698578242); 34 governance, 13 data, 78 evaluation tests and seven-file scope passed.

## Ready, active and blocked work

**Newly ready but not dispatched:**
- `EVAL-006` — freeze sealed evaluation protocol; prerequisites EVAL-004 and EVAL-005 validated (2.0 points).
- `DATA-003` — reproducible preprocessing and dataset versioning; DATA-002 validated (3.0).
- `DATA-005` — sign/palaeographic mapping; DATA-001 and DATA-004 validated (2.0).
- `DATA-006` — image–transliteration target alignment; DATA-002 and DATA-004 validated (3.0).
- `DATA-007` — ambiguity and expert QA; DATA-004 validated (2.0).

**Still active:** `CTRL-003` Anti-Gravity dashboard (draft PR #27, reviewer found current-main stale-state tests, 320px readability/overflow shortcomings, and unresolved npm audit/licensing evidence); `EVAL-003` overseer baseline design/tooling staged via PR #31 but no approved actual model runs, so **0/1.5 earned**.

**Downstream remains blocked:** DATA-008, specialist recognition, VLM learning, linguistic interpretation, generalization and public release. Sealed-test methodology is not the same as submitting to the sealed benchmark.

## Operating rules

1. **Three lanes at most:** Luna execution lane; one shared Anti-Gravity slot (Sonnet *or* Gemini 3.8 Flash); and overseer (scientific research/evaluation/architecture/review). Switching model does not create another lane.
2. Before a new wave, propose concrete substantial overseer-owned work and agent scopes/dependencies; **obtain user approval before starting the overseer's task**.
3. Luna can receive a larger bundle (multiple independent tasks) provided they are dependency-ready and have disjoint PR scopes. Never dispatch downstream tasks before required prior PRs are *validated*.
4. Execution-agent tasks may not self-mark validated, self-award points, or change weights. Review actual source/diffs, test logs, rights and artifacts. Use the full checklist/progress report of `docs/governance/REVIEW_REPORTING_PROTOCOL.md`.
5. Every accepted weighted PR needs a **separate state acceptance PR** and passing `projectctl`/governance CI; no claimed score until merged.
6. EVAL-001 distinguishes script ID, signs, hieroglyphic rendering, transliteration and translation; EVAL-002 pins HieraticBench to `d587dc990013f18007f1e7a8f56f96ff2f7127e2` and its native scorer. Published upstream results are **not fresh experiment results**.
7. FND-005 denies unknown rights or benchmark overlaps. HieraticBench and near-duplicates must stay out of train/dev, and commissioned answer gold is not publicly reproducible.

## Exact next overseer action

1. Finish W1 canonical state acceptance PR CI and merge (this snapshot should then be live).
2. Wait for and review CTRL-003's corrected PR #27 evidence; do not rush production deployment.
3. Propose the next dependency-safe larger Luna package from DATA-003, DATA-005, DATA-006, DATA-007; consider EVAL-006 for overseer scientific heavy lifting, avoiding scope collisions with EVAL-003 until provider/budget approval.
4. Obtain user approval for the next wave, including overseer's own substantial task, before starting it.
5. Keep capability at 18.5 until further tasks have independent acceptance and true run evidence. No synthetic or external scores are model capabilities.
