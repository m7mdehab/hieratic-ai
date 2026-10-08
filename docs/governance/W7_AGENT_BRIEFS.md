# Hieratic-AI W7 — Two complete execution briefs, staged for dispatch

**Status:** ready to forward; **not dispatched by this document**. User controls external-agent activation. **Date:** 2026-10-08.

## Mandatory acceleration protocol (owner-authoritative)

1. **Overseer owns small repairs immediately.** Before sending a revised implementation prompt to Luna/Codex or Gemini/Anti-Gravity, the overseer must independently inspect actual code and determine whether a bounded fix can be safely patched on the task branch with targeted tests and hosted CI. If yes, patch directly, verify, review, and merge. Do not burn agent cycles on small patches, changed error messages, documentation or simple regressions.
2. **Delegate only substantive work** that materially benefits from parallel local execution, dedicated hardware, provider credentials, long context, or major architectural changes. Do not reflexively send a correction loop back to an agent.
3. **No blind green-CI merges.** Review diff, acceptance criteria, authenticity of evidence, exact-head hosted actions, branch scope, contamination, security, and protected canonical state. If a test fails, fetch real job logs and correct the causal problem.
4. **Do not inflate science.** Documentation, source catalogues, fixture-model forwards, simulated reviews, output integrity and synthetic tests earn **zero** scientific points. Only independently accepted authentic task evidence counts.
5. **ADR-0023 dispatch:** both complete agent briefs are provided first; once owner confirms forwarding, oversee the independent lane without waiting for another implementation approval. No automatic third-party correspondence, funding, licensing acceptance, copyrighted publication or paid API calls.
6. **No parallel file conflicts:** Luna owns one source-acquisition branch, Gemini owns one model-runtime branch, overseer owns reviews and separate research/governance, with clear write scopes. Agents do not self-merge. Main merges require green hosted tests and exact SHA.

**Verified W6 integration baseline:** DATA-002 [PR #71](https://github.com/m7mdehab/hieratic-ai/pull/71) merged at `2c7d6aca0862abf5fcd99f5229f4fd09cac884d0`; VLM-001 [PR #72](https://github.com/m7mdehab/hieratic-ai/pull/72) merged at `175165f6c18ed2570a45d274c31a1fc214e0fe50`. Project goal progress `32.5/100`, research coverage `14%`, 0 independently validated real experiments, 0 trained models. DATA-008 **production hard disabled**, VLM-001 **scientific certification hard disabled**. Actual original image byte hashes and expert gold remain missing.

---

# BRIEF 1 — Luna/Codex: W7 / DATA authentic original-image evidence, without corpus promotion

**Repository:** `m7mdehab/hieratic-ai`  
**Start branch:** `task/DATA-003-original-photo-evidence-w7` from the newest `main`.  
**Contract:** DATA-002 exact Met object metadata → DATA-003 deterministic original-asset continuity → DATA-008 future protected admission. **Do not mark DATA-003 unvalidated or change its accepted weight; this is new item-level evidence engineering, not duplicate milestone credit.**

**Write scope:** `data/acquisition/**`, `data/preprocessing/**` where established existing DATA-003 contract permits, `tools/acquisition.py` and corresponding original-asset helpers, `tests/data/**`, `docs/data/**` describing the item-specific process. Do not edit `PROJECT_STATE.yaml`, `TASKS.yaml`, `data/releases/trust_anchors.yaml`, benchmark images or any VLM/EVAL-003 agent files. Honor actual governance scope tests; propose a new scope only in a governance-only isolated request rather than bypassing it.

## Why this task, not another metadata survey

PR #71 already captured **nine genuinely requested** Met official object API JSON responses: real public-domain flags, accession identity, actual original image URL references and response hashes. **What remains missing is original image bytes**, a lawful asset-specific path, source-side view identity, actual media pixel SHA-256, rights evidence and qualified gold. Move beyond repeated metadata without crossing those boundaries.

**Primary object:** Met object `561345`, accession `09.184.703`. Its publicly captured first image filename contains `09.184.728-09.184.703` — **this potentially frames multiple object identifiers**; do not assume a single physical support or use it as a clean holdout until independently reviewed. **Backup:** `561392` / `09.184.751` with two views, one original support until proven otherwise.

## Concrete implementation packages

### 1. Secure, exact-source photo acquisition decision

Read current `data/acquisition/met/objects/{id}.json` and the Met [OA policy](https://www.metmuseum.org/hubs/open-access). Define a **read-only dry-run, fail-closed** workflow to select exactly one of the API-observed `primaryImage`/`additionalImages` original-image references, verify the URL is exactly in the authenticated metadata packet and the approved image CDN, and preflight required original asset rights.

**No image bytes can be requested until actual owner-approved retrieval is independently recorded.** If the owner/overseer provides clear approval for a specifically eligible original CC0 Met image, execute one bounded single-image fetch **only to an ignored, access-controlled private local vault outside public Git**, never to a tracked repository path; otherwise produce the complete safe command/receipt template and leave actual bytes/hash explicitly null. A CLI flag or submitter-authored YAML alone is not an independent legal-authorization signature and must not promote DATA-008.

### 2. Provenance and image equivalence

Bind exact `objectID`, museum accession, official object page, source-packet SHA, exact image view URL, download timestamp and retrieved **actual image byte SHA**, MIME/magic validation, byte size, pixel dimensions, decoder, EXIF orientation, side/exposure status, frame-level inscription overlap and detected multi-accession reference. Decode with bounded pixels; defend against decompression bombs and corrupt/truncated files.

Keep all views grouped by **physical original support**, not by image SHA or portal record. Do not infer separate manuscripts from an alternate side, color copy, crop, rescaling or editorial edition. Capture source confidence and unreadable cases.

### 3. Rights, contamination and safe custody

Record Met's `isPublicDomain` from API and institution CC0 policy as **distinct** evidence. An exact eligible image still needs actual original byte validation, physical-object grouping and purpose-specific rights review before any release. Scholarly/editor text rights and annotations are separate; no gold exists. Preserve R-017 266 public metadata exclusion, direct R-021 Abbott/Hearst manuscript collisions and unknown source-alias/perceptual overlap status.

No image bytes or restricted private agreement contents may appear in a public PR, CI log or GitHub artifact. Public output contains hashes/provenance/redacted status only. Never ingest benchmark image/gold or sealed items.

### 4. Gold-authorship handoff

Provide an **item-specific empty intake dossier** for independent Egyptologist(s): source support and selected exposure, face/region/line geometry, original exact image SHA (when truly obtained), diplomatic transliteration with alternatives/uncertainty/damage, editor authorship, two-reader adjudication, usage/derivative licences, benchmark holdout group and protected authority receipts. Every annotation/text/rights status remains pending until actual independent evidence exists. The intake cannot create permissions by its mere presence.

### 5. Production separation and tests

Do not weaken DATA-008 production hard disable, self-authorize a reviewer, or label photo metadata as corpus. Tests need real network **off** by default, controlled stubbed bytes for JPEG/PNG, hostile redirects/DNS rebinding/private IP, forged API packet URL, content mismatch/oversize/decompression bombs, wrong image bytes/hash, same-support view duplicates, photo filename referencing another accession, tainted source, symlink/parent swaps, concurrent publishers, archive/private-path leakage and incomplete annotation.

The prior hardened publisher in `tools/acquisition.py` is POSIX secure-dirfd only; do not inadvertently restore unsafe Windows fallback. Maintain `--help`/failure behavior and no-clobber.

### 6. Scientific and operational evidence

Provide a concise object-by-object **go/no-go** matrix. If a specifically authorized public-domain photo was lawfully fetched to a private vault, record its SHA and exact API provenance and **still keep DATA-008 blocked**. If not authorized, do not fabricate an image SHA or an inference result; report a clear single actionable rights/ownership blocker.

Run the complete data, source registry, evaluation interoperability, linguistics and governance suites on local/hosted Linux; exact-head hosted CI must pass. No autonomous merge; provide branch, PR URL, exact SHA, new tests, genuine observed bytes (if any) and remaining blockers. **No credit for metadata alone; no gold or real model result is implied.**

---

# BRIEF 2 — Gemini/Anti-Gravity: W7 / Actual open-weight image inference proof or truthful hardware barrier

**Repository:** `m7mdehab/hieratic-ai`  
**Branch:** `task/VLM-001-real-visual-smoke-w7`, based on newest `main`.  
**Write scope:** `eval/vlm/**`, `tools/vlm_baselines.py`, `tests/evaluation/test_vlm_baselines.py`, `docs/evaluation/VLM_BASELINES.md`, `tasks/VLM-001.md`, and VLM-specific hosted workflow. **Do not** change DATA-002/003, EVAL-003 proprietary model suite, `TASKS.yaml` or `PROJECT_STATE.yaml`.

## The critical gap

W6 PR #72 engineered architecture-specific Hugging Face loaders, template enforcement and image-feature checks and pinned complete Llama SHA `9eb2daaa8597bf192a8b0e73f848f3a102794df5`. Its unit tests use **injected doubles**; they do **not** demonstrate an actual selected model, checkpoint, processor, visual tensor or image-conditioned output. The W6 status matrix has been corrected to mark actual loader integration and real inference **NO**.

Your task is **genuine runtime execution whenever legitimately possible**, not adding scores over further mocks. Read the official model cards, HF Transformers per-family live documentation, existing runner, code-pinned synthetic universe, DATA-008 rights gates and current QA first.

## Execution strategy: shortest valid authentic path

**First check resources, do not implement blindly.** Determine whether any permitted local/open-weight model weights, CPU/GPU capability and compatible Transformers runtime are **already** accessible. Record inventory: GPU type/VRAM, available RAM, CUDA support, Python/torch/transformers versions, local model snapshot SHA, gated model access, correct processor and actual image support. Do not claim resource access from packages or mock classes alone.

**Prefer one small legitimate local image-capable checkpoint** that fits genuinely available resources for a smoke test (e.g. documented smaller Qwen2.5-VL family model if actually available and licensed). The purpose is **real visual inference on a self-generated, clearly non-Hieratic test image**, not an official Hieratic score. Do not silently download multi-GB gated models, create cloud paid inference, spend money or bypass model license terms.

### 1. Model architecture and trust

Use correct `Qwen2_5_VLForConditionalGeneration`, `LlavaForConditionalGeneration` for verified Pixtral compatible checkpoints, and `MllamaForConditionalGeneration` for Meta Llama 3.2 Vision. Ensure exact pinned revision and actual snapshot files (weights/index/config/processor) match, model family checkpoint architectures are compatible, and gated licenses/terms are explicitly honored. Unsupported hardware/weights must **fail closed** and remain `untested` — no invented smoke.

### 2. True image-to-tensor proof

For a locally generated source-independent test image (e.g., a red square and a blue circle with randomized positions and no external copyright), show byte hash → pixel decoder → actual processor image feature tensors → model device/dtype → real model generation, with reproducible token counts and input/output hashes. Show an image-swap or blank-image control, preserving prompt constant and actual difference/indeterminate observation; a model is not presumed image-sensitive merely for receiving a nonempty tensor.

No claim of Hieratic proficiency from a colored-shapes image. Do not use official HieraticBench evaluation pixels/gold or sealed items for tuning.

### 3. Fidelity and reproducibility

Fix any family-specific actual preprocessing error exposed by a real checkpoint, particularly Qwen images, Pixtral chat templates, Meta system-role restrictions, `stop_strings` vs tokenizer semantics, returned decoder token sequence shape, prompt stripping, attention/image masks, quantization, CPU/GPU transfers, no arbitrary timing assumptions and OOM/cuda errors. Report exact library and checkpoint digests. Optional code patch must correspond to a reproduced, model-specific problem, not speculative generic complexity.

### 4. Scientific and safety gates

Keep DATA-008 protected trust-root absence, VLM-001 approved-evaluation-cohort false and `--require-certified` hard-disabled. Synthetic tests, stubbed visual tensors, missing image data or claimed self-issued rights cannot earn model skill. No official HieraticBench scores, few-shot visual demonstrations or LING claims. If no real resources, create a **reproducible environment provisioning specification and precise missing resources**, not a falsely green live smoke.

### 5. Evidence grades

For every reported model family, differentiate **A. interface implemented**, **B. processor/format fixture tests**, **C. actual architecture model loaded from real weights**, **D. actual image-conditioned forward**, **E. visual sensitivity control**, **F. authentic Hieratic expert-gold scientific evaluation**. Never use a single YES to stand in for another grade. Real smoke (D/E) may still occur with **0 scientific capability points** and F remains NO.

### 6. Verification and delivery

Add only focused adversarial tests (text-only shortcut, fake image-tag, missing pixel data, wrong processor model, forged hardware/weight snapshot, non-full revision, image swap, empty response, GPU/OOM, unsupported `stop_strings` or decoding miscount) plus a **separate optional real-smoke command** explicitly requiring actual local weights and hardware. CI remains entirely offline, resource-independent, and noncertifiable.

Submit an end-to-end PR with exact SHA and hosted CI. Include authentic run logs/hashes **only if a genuine model was run** and label test-double outputs distinctly. Do not self-merge, alter protected project state or give task points.

---

# Independent overseer W7 lane (starts after owner confirms both briefs forwarded)

1. Review actual original Met image use evidence, original photo identity and item-specific catalogue/source licences; resolve `561345` multi-accession image warning by primary museum/source proof, not inference from filename alone. If permissions require institutional correspondence, prepare authentic owner-ready letter, **do not send** without owner approval.
2. Independently assess availability of a **qualified Egyptologist line transcription and second review** (first core domain pair Met 561345 or Turin Cat.1896); ascertain actual access/rights/fee, not speculative gold.
3. Improve EVAL-003 **actual run decision readiness** for one carefully selected, frozen, image-rights-eligible public item using documented public model API limits, owner budget and private-response custody **without running paid calls absent approval**; no benchmark image/gold used for development.
4. Review both agent PRs, **directly patch bounded findings on their task branches**, fetch log failures, rerun hosted CI and merge only scientifically honest infrastructure. Update canonical W7 pointer and handoff after both accepted; preserve 32.5/100 unless genuine new science passes independent acceptance.
5. Publish concise evidence-bearing status and requirements for the *first authentic image+expert diplomatic line* and *first genuine image-conditioned model output* separately.

## External authorization boundary

Dispatching these prompts does not grant institutional correspondence, acquisition of restricted third-party images, protected storage/legal permissions, model provider credentials, GPU purchases, paid API billing or corpus/trained-weight redistribution. Only already-permitted public metadata, checked-in code and synthetic fixtures can be processed by default; optional authentic pixels and weights require individually supported rights/resources. All records remain quarantined until independent authority exists.
