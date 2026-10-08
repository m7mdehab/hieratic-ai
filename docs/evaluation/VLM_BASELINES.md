# VLM Baseline Evaluation Protocol: Zero-Shot & Few-Shot Benchmarking

## 1. Overview & Scientific Purpose

This protocol establishes a scientifically reproducible, untuned zero-shot and few-shot Vision-Language Model (VLM) baseline evaluation suite for Ancient Egyptian Hieratic script reading across four canonical reading rungs:
1. **Script Identification (`identify`):** Classifying ancient Egyptian manuscript fragments into Hieratic, Hieroglyphic, Demotic, or Coptic.
2. **Isolated Sign Recognition (`signs`):** Identifying individual Hieratic characters and sign clusters into canonical Gardiner sign codes.
3. **Sequential Transliteration (`transliterate`):** Transcribing continuous line passages into standardized Egyptological transliteration.
4. **Translation (`translate`):** Translating continuous Hieratic texts into grammatical English.

This suite is developed independently from the overseer's `EVAL-003` frontier proprietary model comparison (`eval/baselines/**`). It focuses on:
- Open-weight multimodal vision-language architectures (`transformers`, `torch`).
- Cryptographic prompt contracts with immutable SHA-256 integrity verification.
- Strictly quarantined few-shot demonstration banks with fail-closed provenance gates.
- Complete attempt accounting across all outcomes (success, abstention, refusal, timeout, failure).
- Document-clustered non-parametric bootstrap uncertainty reporting ($B=2,000$) conforming to `EVAL-006`.
- Explicit separation between upstream official HieraticBench benchmark scoring and project-native `EVAL-001` diagnostic metrics.
- Promotion prevention mechanisms ensuring synthetic CI fixtures cannot masquerade as certified empirical findings.

---

## 2. Frozen Evaluation Suite (`eval/vlm/suite.yaml`)

### 2.1 Model Candidates

| Key | Model Name | Architecture / Loader Class | Revision (Pinned) | License | Execution Tier | Hardware Prerequisite |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `mock-vision-v1` | Deterministic Synthetic Baseline | Synthetic test harness | `v1.0.0` | Apache-2.0 | `synthetic_ci_fixture` | CPU (Offline) |
| `qwen2.5-vl-7b-instruct` | Qwen 2.5 VL 7B Instruct | `Qwen2_5_VLForConditionalGeneration` | `bfb8829e3c6c0ebad5da954181947bb9df50b0e0` | Apache-2.0 | `live_local_open_weight` | CUDA GPU (>= 16 GB VRAM) |
| `pixtral-12b-2409` | Pixtral 12B | `LlavaForConditionalGeneration` | `31ea79a32c256037a503023e6022e3427f79612c` | Apache-2.0 | `live_local_open_weight` | CUDA GPU (>= 24 GB VRAM) |
| `llama-3.2-11b-vision-instruct` | Llama 3.2 11B Vision Instruct | `MllamaForConditionalGeneration` | `9eb2daaa85` | Llama-3.2-Community | `live_local_open_weight` | CUDA GPU (>= 24 GB VRAM) |

### 2.2 Execution Gates

To eliminate unapproved API spending and enforce rigorous scientific constraints:
- `max_paid_spend_usd: 0.0`: Unapproved paid external API calls are strictly blocked ($0.00 spend cap).
- `require_image_conditioning: true`: All evaluation runs require valid raw image bytes. Text-only guesses or unconditioned mock shortcuts fail closed.
- `allow_network_inference: false`: Evaluations default to local, offline-verifiable execution.
- `offline_reproducible: true`: Artifact generation and metric scoring must be entirely deterministic offline.

### 2.3 Image Preprocessing Standards

To ensure consistent model conditioning:
- **Maximum Dimension:** 1024 px along the longest edge (aspect ratio strictly preserved).
- **Minimum Dimension:** 64 px.
- **Color Space:** Standard 3-channel RGB.
- **Format:** High-quality JPEG or lossless PNG.
- **Normalization:** Standard RGB channel mean/variance scaling when processed by neural vision encoders.

### 2.4 Decoding Parameters

All baseline comparisons use deterministic greedy decoding to eliminate sampling variance:
- `temperature`: `0.0` (greedy search)
- `top_p`: `1.0`
- `max_new_tokens`: `256`
- `seed`: `42`
- `stop_sequences`: `["\n\n", "<|im_end|>", "</s>"]`

### 2.5 Cryptographic Prompt Contracts

Prompt templates are frozen and verified via SHA-256 hashes of the combined `system_prompt` and `user_template` strings:

| Rung | Shot Mode | Prompt SHA-256 |
| :--- | :--- | :--- |
| `identify` | Zero-Shot | `157cd45118c683fbd3d9874ba93771fe4e56094ec4de47d9ca59892a1b7e0ada` |
| `identify` | Few-Shot | `0dc7417157dbac17ae1fdc58cb62cf3cdaaa082ba58434e8606e6810b7c631a2` |
| `signs` | Zero-Shot | `bcffa49578301c49aca23b0b08be8c45f588ed2f920bffdfc02bf301de6ebc15` |
| `signs` | Few-Shot | `72b238b0d7900465ef19435bcf13aa2368ee954ec33c107f60deefa52b54329d` |
| `transliterate` | Zero-Shot | `884c40a8ba28b00a2faa34bfb16f455c6d64cb2d829ffc8565cee5920f4f5396` |
| `transliterate` | Few-Shot | `8c7b0f1b685c24d538905a66522a1604dc1d5c0bbe7cd8c8a9493df42da54b33` |
| `translate` | Zero-Shot | `45cd8e5ba5ded5e934f1b2690ea004209b7f9d72108b3230132e5118657f3ad5` |
| `translate` | Few-Shot | `1c7abea20d7cbe3926716dd0f88575b5f45c5ac1d1dca0959e9ce0e1b4146c76` |

Any modification to prompt text without updating the recorded hash fails validation immediately.

---

## 3. HieraticBench Quarantine & Quarantined Demonstration Bank

### 3.1 HieraticBench Quarantine Policy

As mandated by `DATA_LICENSING_AND_PROVENANCE_POLICY.md` and `eval/benchmarks/hieraticbench/manifest.yaml`:
- HieraticBench assets are licensed strictly for **external evaluation only**.
- Public benchmark items, test images, references, and near-duplicates **must never** be used as few-shot demonstrations, prompt optimization examples, or fine-tuning datasets.

### 3.2 Demonstration Bank Status (`eval/vlm/demonstrations.yaml`)

The canonical demonstration repository `eval/vlm/demonstrations.yaml` is formally classified as:
- `status`: `"synthetic_fixture_only"`
- `rights_review_status`: `"synthetic_placeholder_unreviewed"`
- `quarantine_verified`: `false`

The records contain synthetic facsimile references for CI regression testing. They are **not** cleared for authentic scientific evaluation.

### 3.3 Fail-Closed Few-Shot Clearance Policy

Real few-shot evaluation must **fail closed** (`LiveFewShotBlockedError` or `UnverifiedDemonstrationError`) unless all of the following conditions are satisfied:
1. **Unconditional Model Architecture Gate:** In `OpenWeightVLMAdapter`, live few-shot evaluation on open-weight backbones is unconditionally blocked (`LiveFewShotBlockedError`) until verified multi-image vision templates, exemplar pixels, and provenance receipts exist.
2. **Actual Pixels on Disk:** Demonstration items must point to genuine image files on disk. Pure URI placeholders (`facsimile://...`) or unverified records fail closed.
3. **Cryptographic SHA-256 Hash Verification:** On-disk image bytes must match the recorded SHA-256 hash exactly.
4. **Item-Specific Rights Review:** The demonstration bank must carry `rights_review_status: "approved_with_evidence"` backed by independent provenance review. Asserting `approved_with_evidence` without verifiable on-disk images fails closed.
5. **Partition Quarantine:** Image hashes and item identifiers must be verified not to overlap with HieraticBench or any training/evaluation split.
6. **Forbidden Prefix Rejection:** Reserved HieraticBench ID prefixes (`AKU-`, `CBL-`, `HB-`, `MET-`, `WM-`, `YPM-`) are strictly forbidden.

Synthetic fixtures are permitted **only** in the synthetic CI harness tier (`mock-vision-v1`) when explicitly operating under `synthetic_ci_fixture`.

---

## 4. Attempt Preservation & Denominator Accounting

In accordance with empirical benchmark standards, **every attempted evaluation item must be preserved**:
- **Success (`success`):** Model returned a valid completion within latency and resource limits.
- **Abstention (`abstained`):** Model explicitly declined to predict due to uncertainty (e.g., `[ABSTAIN]`, `UNCERTAIN`).
- **Refusal (`refused`):** Model safety filters blocked output generation.
- **Timeout (`timeout`):** Model exceeded inference latency threshold.
- **Failure (`failed`):** Runtime crash, memory error, or unhandled exception.

### 4.1 Composite Attempt Identity

Attempts are identified by the composite tuple:
$$\text{Composite Identity} = (\text{item\_id}, \text{rung}, \text{shot\_mode}, \text{sample\_index})$$

This composite key prevents collisions across multi-mode evaluation runs and guarantees exact 1-to-1 pairing in paired comparisons.

### 4.2 Independent Evaluation Universe Contract (`eval/vlm/universe.yaml`)

To ensure that attempt deletion cannot conceal failures, drop difficult items, or alter denominator totals, the runner and auditor enforce an independently pinned evaluation universe:
- **`universe.yaml`:** Canonical evaluation universe specifying exact dataset ID (`hieratic_vlm_synthetic_preflight_universe_v1`), licensed items, scale levels, dimensions, reading directions, and expected attempt Cartesian product.
- **Canonical SHA-256:** Computed deterministically via `compute_universe_sha256` over the sorted canonical representation of items and scheduled attempts (`fd72f77473b0c07074a18ceafbddc40449f4f9690be99e522100b313e3b0780d`).
- **Independent Manifest Auditing:** The manifest auditor does not rely solely on self-contained manifest declarations. It compares observed attempt records strictly against `eval/vlm/universe.yaml`. Dropping an item, deleting an attempt, and recalculating in-manifest counts or hashes fails closed with `Independent universe violation`.
- **Dataset Admission Tiers:**
  - `synthetic_preflight_universe` / `synthetic_ci_items`: Synthetic test items for pipeline verification. Non-promotable.
  - `unverified_external_inputs`: Arbitrary external items supplied without an audited admission receipt. Strictly non-promotable to certified scientific baseline results.
  - `approved_evaluation_cohort`: Genuine palaeographical cohort backed by an independent admission receipt (`rights_review_status: "approved_with_evidence"`, `quarantine_verified: true`, `permitted_cohort_tier: "approved_evaluation_cohort"` with named independent reviewer).
- **Image Decoding & Integrity Validation:** `validate_image_file` verifies image existence, format (PNG/JPEG magic bytes), dimensions ($\ge 16$ px, $\le 1024$ px), and cryptographic SHA-256 byte hashes.

### 4.3 Full Denominator Accounting

To prevent survivorship bias, the evaluation suite reports two distinct metric variants:
1. **Intention-to-Test Score (`intention_to_test_score`):**
   Evaluates all attempted items ($N_{\text{total}}$), assigning a score of $0.0$ to non-successes (failures, timeouts, abstentions, refusals) for higher-is-better metrics, or $1.0$ penalty for lower-is-better error metrics (`TR_CER`). This is the primary scientific metric.
2. **Conditional Score (`conditional_score`):**
   Evaluates only successful completions ($N_{\text{success}}$), reported alongside explicit counts for failures, abstentions, timeouts, and refusals.

$$\text{Coverage Rate} = \frac{N_{\text{success}}}{N_{\text{total attempts}}}$$

---

## 5. Dual-Channel Scoring & Statistical Standards (EVAL-006)

### 5.1 Official HieraticBench vs. Project-Native Metrics

To prevent misleading claims, scoring channels are strictly separated:
1. **Official Upstream Benchmark (`official_hieraticbench`):**
   - Authoritative scoring implemented by the pinned TypeScript scorer (`bench/src/score.ts`).
   - In this offline preflight harness, official scoring is explicitly reported with `official_scoring_status: "NOT_INTEGRATED"` and `official_hieraticbench: null`.
   - Never accepts caller-injected arbitrary score summaries as authoritative evidence; supplying `official_replay_summary` to `score_manifest` raises a fatal `ScorerError`.
2. **Project-Native Diagnostics (`project_native_eval001`):**
   - In-house metrics strictly conforming to `eval/metric_contract.yaml`:
     - Script Identification: `SCRIPT_ACC` (direction: higher, unit: proportion)
     - Isolated Sign Recognition: `SIGN_TOP1` (direction: higher, unit: proportion)
     - Sequential Transliteration: `TR_CER` (direction: lower, unit: edit_error_rate, Levenshtein CER, 1.0 penalty for unfulfilled attempts)
     - Translation: `TRANS_CHRF` (direction: higher, unit: score)
   - Secondary diagnostics: `TR_TER` (WER), `DIAG_ACCURACY` ($\max(0.0, 1.0 - \text{CER})$), and `VLM_DIAG_BLEU_4`.
   - Direction handling: for `TR_CER` (`direction: lower`), paired differences are reported as $\Delta = \text{Score}_B - \text{Score}_A$ (negative values indicate lower error rate for $B$, hence improvement).
   - Clearly labeled under the `project_native_eval001` channel to prevent conflation with official upstream leaderboard scores.
3. **Adversarial Parity Testing:**
   - Dedicated adversarial parity tests (`test_adversarial_parity_exposes_differences_with_official_scoring`) demonstrate where in-house metrics diverge from upstream scoring (e.g., conversational framing wrappers, multi-sign Gardiner array matching), preventing unwarranted claims of parity.

### 5.2 Document-Clustered Bootstrap Uncertainty

In accordance with `EVAL-006`:
- **Document Clustering:** Attempts are clustered by `document_id`. Entire documents are resampled with replacement across $B=2,000$ bootstrap iterations.
- **Support Gate:** When the number of independent document clusters is $\le 1$, the bootstrap confidence interval **must return `null`** (`insufficient_document_clusters`). Fabricating zero-width or single-point confidence intervals is strictly prohibited.
- **Paired Comparisons:** Paired differences ($\Delta = \text{Score}_B - \text{Score}_A$) are evaluated over aligned composite keys using clustered bootstrap resampling, requiring explicit `--shot-mode-a` and `--shot-mode-b` condition filters when comparing multi-mode manifests.

---

## 6. Promotion Prevention & Execution Tiers

To safeguard benchmark integrity, artifacts and runs are categorized into explicit tiers conforming to `schemas/vlm_baselines.schema.json`:

| Execution Tier | Scientific Validity | Certification Status | Promotable to Certified Results? |
| :--- | :--- | :--- | :--- |
| `synthetic_ci_fixture` | `non_scientific_test_fixture` | `uncertified_synthetic_only` | **NO** (Strictly blocked) |
| `live_local_open_weight` (unaccelerated/barrier) | `candidate_baseline` | `preflight_passed_pending_review` | **NO** (Hardware barrier blocked) |
| `live_local_open_weight` (hardware-accelerated) | `certified_baseline` | `certified` | Yes (requires verified admission receipt & audit) |

The manifest auditor (`tools/vlm_baselines.py audit-manifest --require-certified`) fails closed with `Promotion rejection` unconditionally for all preflight runs because user-editable manifest fields and self-declared receipt references cannot establish certification without an integrated external authorization authority (signed DATA-008 receipt, source evidence, and model-inference receipt).

Furthermore, manifest publication uses atomic no-clobber semantics (`write_json_no_clobber`, `write_bytes_no_clobber`), preventing overwrite of existing artifacts. Scoring and paired-comparison commands pre-audit all inputs against the code-pinned universe anchor, refuse unaudited inputs without `--diagnostic-only`, and wrap all outputs in an immutable `noncertifiable_diagnostic` classification envelope with an explicit `audit_receipt`.

---

## 7. Open-Weight Inference Architecture & Hardware Boundaries

### 7.1 Architecture & Implementation

The harness implements a modular model-adapter architecture (`eval/vlm/adapter.py`):
1. **`BaseVLMAdapter`:** Abstract interface defining `preprocess_image`, image conditioning validation, and `check_availability`.
2. **`MockVLMAdapter`:** Deterministic synthetic test harness for CI pipelines and offline validation.
3. **`OpenWeightVLMAdapter`:** Base open-weight dispatcher managing GPU detection, model weights on disk, and forward decoding.
4. **Specialized Multimodal Adapters:**
   - `Qwen2_5_VLAdapter`: Multimodal chat template with `<|image_pad|>` visual placeholder.
   - `PixtralVLMAdapter`: Mistral/Pixtral chat format with structured `{"type": "image"}` tokens.
   - `Llama3_2_VisionAdapter`: Llama 3.2 vision prompt format with `<|image|><|begin_of_text|>` token headers.
5. **Dependency-Isolated Testing:** Adapters accept `processor_override` and `model_override` injection, enabling exhaustive unit testing of chat templates and OOM exception handling without local GPU weights.

### 7.2 Hardware & Weight Requirements

Real open-weight VLM inference requires:
- Local GPU hardware: NVIDIA CUDA with $\ge 16$ GB VRAM (for 7B models) or $\ge 24$ GB VRAM (for 12B models).
- Downloaded, approved model weights residing in a verified local cache.
- Explicit approval for local execution under zero-spend policy ($0.00 spend).

### 7.3 Wave 6 Technical Verification Status Matrix

Under Wave 6 audit standards, capability claims are broken down strictly into five verifiable states. **A stubbed loader/processor is not an actual integrated checkpoint test**, and a mock scored against synthetic fixture text is not evaluated Hieratic reading:

| Model Backbone | (1) Implemented Interface | (2) Unit-Tested Formatting | (3) Integration-Tested Loader | (4) Executed Inference | (5) Evaluated Hieratic Reading |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `mock-vision-v1` | **YES** | **YES** | **YES — synthetic only** | **YES — test-double generation only** | **NO — fixture outputs are not scientific reading evidence** |
| `qwen2.5-vl-7b-instruct` | **YES** | **YES — doubles** | **NO — loader dispatch checked against synthetic/fake dependency interfaces only** | **NO — no weights/GPU proven** | **NO** |
| `pixtral-12b-2409` | **YES** | **YES — doubles** | **NO — loader dispatch checked against synthetic/fake dependency interfaces only** | **NO — no weights/GPU proven** | **NO** |
| `llama-3.2-11b-vision-instruct` | **YES** | **YES — doubles** | **NO — loader dispatch checked against synthetic/fake dependency interfaces only** | **NO — no weights/GPU proven** | **NO** |

### 7.4 Fail-Closed Barrier Disclosure

When running in environments without dedicated GPU accelerators or downloaded local weights (such as standard CPU CI runners or developer laptops):
- `OpenWeightVLMAdapter` **fails closed** cleanly, reporting `Inference blocked by hardware/weights barrier` with an exact explanation of missing prerequisites (`cuda_available: false`, unprovisioned weights).
- It does **not** fabricate synthetic model completions.
- It does **not** make unapproved paid external API calls.
- Task `VLM-001` remains **scientifically unvalidated** (0.0 / 2.0 capability points) until genuine inference on approved local hardware is conducted and independently audited.

---

## 8. CLI Reference Guide

The baseline CLI tool (`tools/vlm_baselines.py`) provides controlled, reproducible operations:

### Validate Suite Configuration
```bash
python -m tools.vlm_baselines validate-suite
```

### Validate Quarantined Demonstration Bank
```bash
python -m tools.vlm_baselines validate-demonstrations
```

### Run Synthetic CI Evaluation
```bash
# Synthetic CI run (default built-in items)
python -m tools.vlm_baselines run \
  --model mock-vision-v1 \
  --shot-mode both \
  --output artifacts/vlm_manifest.json

# Run on verified external items (tagged as verified_external_items)
python -m tools.vlm_baselines run \
  --model mock-vision-v1 \
  --items data/verified_items.json \
  --shot-mode zero-shot \
  --output artifacts/vlm_manifest.json
```

### Audit Run Manifest (Strict Certification & Gold Integrity)
```bash
# Standard validation with frozen universe audit and gold eligibility verification
python -m tools.vlm_baselines audit-manifest \
  --manifest artifacts/vlm_manifest.json

# Allow incomplete gold labels (for unannotated pilot runs)
python -m tools.vlm_baselines audit-manifest \
  --manifest artifacts/vlm_manifest.json \
  --allow-incomplete-gold

# Certified results gate (fails closed on synthetic fixtures)
python -m tools.vlm_baselines audit-manifest \
  --manifest artifacts/vlm_manifest.json \
  --require-certified
```

### Score Run Manifest (Document-Clustered Bootstrap)
```bash
python -m tools.vlm_baselines score \
  --manifest artifacts/vlm_manifest.json \
  --output artifacts/vlm_score_report.json

# With incomplete gold tolerance:
python -m tools.vlm_baselines score \
  --manifest artifacts/vlm_manifest.json \
  --allow-incomplete-gold \
  --output artifacts/vlm_score_report.json
```

### Paired Comparison
```bash
# Paired comparison between distinct zero-shot and few-shot manifests
python -m tools.vlm_baselines paired-compare \
  --manifest-a artifacts/vlm_manifest_zero.json \
  --manifest-b artifacts/vlm_manifest_few.json \
  --output artifacts/vlm_comparison.json

# Paired comparison on multi-mode manifest using explicit condition filters
python -m tools.vlm_baselines paired-compare \
  --manifest-a artifacts/vlm_manifest_both.json \
  --manifest-b artifacts/vlm_manifest_both.json \
  --shot-mode-a zero-shot \
  --shot-mode-b few-shot \
  --output artifacts/vlm_comparison.json
```

