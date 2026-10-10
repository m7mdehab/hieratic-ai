# Wave 28 — Coordinated Dispatch Contract (PREPARATION ONLY)

> **Status: PREPARED, NOT STARTED.** This document gives copy-ready dispatch prompts and governance checkpoints. Publishing this file, creating issues, or passing planning CI does not authorize third-party data use, paid model calls, museum outreach or experiment-result claims. Agents start when the user forwards their prompt; the overseer starts only after the user returns with the W28 nudge.

## Frozen preparation baseline

- Repository: https://github.com/m7mdehab/hieratic-ai
- Main at preparation: 828f7eb09afbb995379b2a97e97d4392b7fe5471 (re-read before execution).
- Canonical scored goal: 34.5/100; 65.5 remains. Research-space coverage: 18/100, **qualitative**, distinct from weighted capability. Zero validated actual Hieratic model experiments and zero accepted trained reading models. No open integration PRs at dispatch preparation.
- Active weighted critical path: DATA-008 0/3 (first real licensed rights-cleared corpus v1); VLM-001 0/2 (valid zero/few-shot reading baseline); LING-003 0/2 (actual meaning/translation); EVAL-003 0/1.5 (untuned provider frontier evaluation). Total **8.5 potential points**, but **not expected points**, pending independent genuine acceptance. P4/P5 and generalization/release still depend on those gates.
- Past verified work: W27 overseer historical Tokyo Möller printed-book IIIF original pixels 24, real provisional sign 1NN 2/8 vs nonvisual 1/8; not original papyrus or manuscript-witness holdout. W27 Luna DDD admission 0/159 rights-cleared original images; no model. W27 Gemini new prospective 3-prompt 69-attempt engine and durable ledger; hosted **simulated CI** and self-reported local original CPU execution are distinct. W27 actual CPU raw ledger/weights/image hashes not independently audited. Engineering merged: Luna #149, Gemini #150; score unchanged.
- DATA-008 canonical production corpus hard-disabled pending protected independent rights-review and trusted institutional/reviewer authority, complete original photo rights, real acquisition/provenance, expert gold and qualified source-disjoint holdout.
- TPOP/Museo Egizio Cat1880 original CC0 still separate from scholarly *transliteration* rights; even the physical-document edition reference and photo source hash do not prove exact same handwritten line. DDD original 159 images have CC BY-NC-SA metadata/annotations and separately restricted photo rights. Printed HPDB/Möller, published AKU-PAL SVG/WebP, source genealogy and source-manuscript IDs must not be conflated.
- W16 genuine TLA text-to-German transfer poor (German word micro-F1 0.01803378 on 3,606 complete references). Earlier W9–W16 texts and their evaluation labels have been revealed. They cannot be relabeled new heldout gold.
- W27 automation: native Git push + GitHub auto-created PR and push-triggered governance validated on legitimate registered FND-006 smoke #155, merged; do not ask user to push.

## Wave documents and tracking

1. Luna: [W28_LUNA_DATA008.md](W28_LUNA_DATA008.md) — DATA-008 source/photo annotation admissibility and physical manuscript release path; issue #157.
2. Gemini 3.8 Flash: [W28_GEMINI_VLM001.md](W28_GEMINI_VLM001.md) — independent authentic open-weight VLM CPU proof, controls, raw audited ledger; issue #158, linked science gap #145.
3. GPT-6 overseer: [W28_OVERSEER_GPT6.md](W28_OVERSEER_GPT6.md) — primary LING-003 translation competence challenge, separate EVAL-003 provider gate and R-024/Cat1880 expert-ready corpus rights/line alignment; issue #159. Coordinating umbrella issue #156.
4. Operational dispatch by user: forward Luna and Gemini their respective complete prompts **once**, then return to overseer chat and send the nudge printed at the end of the master prompt or in the user response.

## Non-overlapping write ownership

| Lane | Write owner and branch | Exact registered task write scope |
|---|---|---|
| Luna | DATA-008: task/DATA-008-w28-original-manuscript-cohort | tasks/DATA-008.md; data/releases/**; schemas/dataset_release.schema.json; tools/release_corpus.py; tests/data/test_corpus_release.py; docs/data/CORPUS_V1_RELEASE.md |
| Gemini | VLM-001: task/VLM-001-w28-original-hosted-cpu-audit | tasks/VLM-001.md; eval/vlm/**; schemas/vlm_baselines.schema.json; tools/vlm_baselines.py; tests/evaluation/test_vlm_baselines.py; docs/evaluation/VLM_BASELINES.md; .github/workflows/vlm-baselines.yml |
| Overseer A | LING-003: task/LING-003-w28-compositional-meaning-evidence | tasks/LING-003.md; ling/translation/**; tools/translation_layer.py; tests/linguistics/test_translation_layer.py; docs/linguistics/TRANSLATION_PROTOCOL.md |
| Overseer B | EVAL-003: task/EVAL-003-w28-frontier-artifact-admission | tasks/EVAL-003.md; eval/baselines/**; docs/evaluation/FRONTIER_BASELINES.md; tests/evaluation/test_frontier_baselines.py; .github/workflows/frontier-baselines.yml |
| Overseer research | overseer/w28-cat1880-source-gold-gate | docs/research/** and research-only independent issue comments; no mutation of Luna's data/releases or other's benchmark data |

**Do not create task branches before actual execution**, since branch pushes themselves trigger hosted workflows and can automatically create placeholder PRs. Agent owns branch from freshest accepted main at time of dispatch, not the stale W27 parent.

If a task requires changing someone else's files, propose a separate scoped overseer PR or explicit scope registration via governance **first**, never silently widen the existing task or evade the CI scope gate. For a new model or research library dependency, record license, pinned version, installation and attack surface in the owning task.

## Mandatory evidence hierarchy (no substitutions)

- **D0** Source or tool metadata only — useful feasibility; no source image, external rights or model output attested.
- **D1** Original source content retrieved under verified file/asset permission, hashed with independently reproducible receipt; content must be genuine for the exact scientific object/view.
- **D2** Actual model forward passes on decoded authentic pixels, pinned actual model weight bytes, exact raw outputs and complete durable record, with independently replayable hosted or private inspection. Simulated doubles remain separate.
- **D3** Lawfully usable training/dev/evaluation original-photo + independently authorized scholarly annotations, exact pixel-to-target coordinates, physically disjoint and benchmark-independent holdout.
- **D4** Unseen exact-line diplomatic gold from qualified independent scholarly reviewers, calibrated disagreement and uncertainty, blind evaluation and accepted end-to-end reading/translation.
- **Capability milestones** may be awarded **only per their own approved acceptance contract**, never simply on reaching a generic D1/D2 or running larger scripts. No task agent assigns its own state or points.

## Mutually exclusive scientific roles of sources

- Cat.1880, Cat.2044/013, S.6759: real object photos where individually verified; one physical support per accession despite many views. Cat.2169 photo is an ostracon whose prior usage as a generic negative/monogram is contested; inspect publisher original record and determine text/not-text honestly, never assume the control is not writing.
- DDD 159 images, 50 source supports, 17,885 scholarly labels, 504 classes: **metadata/annotation source**; rights and precise image crop coordinate binding currently 0/159 cleared. Do not treat NC-SA dataset license as photo rights.
- Tokyo IIIF 24 printed Möller book strips: a real pixel-only source with labeled provisional catalogue numbers, not a disjoint handwritten papyrus or expert blind gold.
- AKU-PAL W19 actual original per-item CC BY4 receipts: 15 media pieces among 6 physical manuscript sources; 8 SVG facsimiles, 5 printed scan WebPs, 2 derivative outlines. Published labels are metadata, the five photo-like WebPs depict published print scans, not original manuscript photographic pages. Many scanned media are exact public-source benchmark matches or ancestry unknown.
- Authentic official HieraticBench: 266 public + 2 sealed. The sealed set is never accessed or released; public eval material is evaluation-only and not a training or development signal. No “no metadata match” can grant universal clearance.
- AES/TLA/UD Egyptian publisher text: authentic ancient Egyptian language/editorial work, not input images of Hieratic. Physical-witness genealogy, modern German editor translations and restricted text licenses remain independently checked.

## Parallel execution and integration

- Commit proper **prospective** cohort selection, exact prompt/model/input identities and thresholds **before reading new target labels or seeing model outputs**. If results change after freezing, revision means new protocol and new untouched cohort, not retuning old gold.
- Each lane must execute dependency-safe independent packages even if a rights/provider/expert gate remains externally blocked. Include 10+ targeted adversarial tests for new interfaces and explicit negative result if the science is impossible without credentials.
- Native Git push, no manual user relay. GitHub auto-PR on task/** branch push; task-push CI independently validates all governance suites. Add task-specific hosted source/inference runs only when lawful and feasible; exactly pin the hosted head SHA and separate model execution vs mocks.
- Overseer personally reviews code, rights, scope, original receipts, CI exact head, failures, numerical denominators and scientifically meaningful holdout. Independent merge sequence must keep same-scoped TASKS/PROJECT_STATE edits to overseer-only separate acceptance PR, not agent PRs.
- Dedicated no-spend, no-outreach, no-restricted-use safety perimeter. The user approving this task wave is **not** authorizing unrestricted spending, contacting museums/experts, sealed benchmark access, or a release of third-party copyrighted images.
- The goal is maximum **honestly earnable** weighted progress with sustained reproducibility, not number inflation. Report before/after baseline, actual newly accepted points, remaining points and remaining root blockers.

## Start condition and nudge

Send Luna and Gemini complete prompts from linked pages. Afterwards return here and send:

> **Start Wave 28 now. Execute your full GPT-6 overseer assignment from docs/waves/W28_OVERSEER_GPT6.md on the latest main while Luna and Gemini run their lanes. Complete all independent, lawful, no-cost work in one substantial batch, push separate scoped branches, verify exact-head hosted CI, review/merge eligible changes, and report verified capability-point movement and blockers. Do not wait for further routine approvals.**

**Not yet executed:** prompt handoff, original image acquisition, model inference, independent professional review, actual translated output, frontier paid model APIs and task acceptance.