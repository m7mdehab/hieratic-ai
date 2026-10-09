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
| `llama-3.2-11b-vision-instruct` | Llama 3.2 11B Vision Instruct | `MllamaForConditionalGeneration` | `9eb2daaa8597bf192a8b0e73f848f3a102794df5` | Llama-3.2-Community | `live_local_open_weight` | CUDA GPU (>= 24 GB VRAM) |
| `smolvlm-256m-instruct` | SmolVLM 256M Instruct | `Idefics3ForConditionalGeneration` | `7e3e67edbbed1bf9888184d9df282b700a323964` | Apache-2.0 | `live_local_open_weight` | CPU (x86_64, >= 4 GB RAM) |


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

### 7.5 Audited Host Environment Resource Inventory (Wave 7)

An exhaustive hardware and environment audit of the active execution host reveals the following concrete barriers:
- **Operating System:** Windows 11 (AMD64), Python 3.12.10.
- **GPU Architecture:** AMD Radeon(TM) Graphics (integrated GPU, 512 MB AdapterRAM). **Zero NVIDIA CUDA GPU devices are present** (`torch.cuda.is_available() == False`).
- **Host System RAM:** 7.74 GB visible memory total.
- **Virtual Environment:** Python `.venv` contains minimal metadata dependencies (`jsonschema`, `pyyaml`, `attrs`). PyTorch (`torch`), Hugging Face Transformers (`transformers`), `torchvision`, `accelerate`, and `PIL` are **not installed**.
- **Model Weights Cache:** Checked `$env:USERPROFILE\.cache\huggingface\hub`. Contains only text embedding models (`ModernBERT-base`, `kompress-v2-base`). **Zero multimodal vision-language model weights exist on disk.**
- **Zero-Spend Constraint:** Strict $0.00 spend cap enforced per ADR-0023. Cloud GPU provisioning and commercial VLM API calls are strictly unapproved.

### 7.6 Reproducible Environment Provisioning Specification

To enable genuine open-weight VLM evaluation when compliant hardware and approved weights are provisioned, the following environment specification is registered:

1. **Host Compute & Accelerator:**
   - **OS:** Linux x86_64 (Ubuntu 22.04 LTS or 24.04 LTS recommended)
   - **System RAM:** $\ge 32$ GB (64 GB recommended for 12B models)
   - **GPU:** Dedicated NVIDIA CUDA GPU with Tensor Cores (Ampere, Ada Lovelace, or Hopper)
   - **VRAM:** $\ge 16$ GB VRAM for 7B models (`qwen2.5-vl-7b-instruct`); $\ge 24$ GB VRAM for 11B/12B models (`pixtral-12b-2409`, `llama-3.2-11b-vision-instruct`). Examples: NVIDIA RTX 4090 (24 GB), A10G (24 GB), A100 (40/80 GB).
   - **CUDA Drivers:** CUDA Toolkit 12.1+ / NVIDIA Driver $\ge 535.54.03$.

2. **Python Dependencies:**
   ```bash
   pip install torch==2.4.0 torchvision==0.19.0 --index-url https://download.pytorch.org/whl/cu121
   pip install transformers>=4.49.0 accelerate>=0.26.0 pillow>=10.0.0 safetensors>=0.4.0
   ```

3. **Pinned Checkpoint Snapshots:**
   - **Qwen 2.5 VL 7B Instruct:** `Qwen/Qwen2.5-VL-7B-Instruct` @ commit `bfb8829e3c6c0ebad5da954181947bb9df50b0e0`
   - **Mistral Pixtral 12B:** `mistralai/Pixtral-12B-2409` @ commit `31ea79a32c256037a503023e6022e3427f79612c`
   - **Meta Llama 3.2 11B Vision Instruct:** `meta-llama/Llama-3.2-11B-Vision-Instruct` @ commit `9eb2daaa8597bf192a8b0e73f848f3a102794df5`

### 7.7 Six-Grade Evidence Matrix (Wave 7 Brief 2 Standard)

Under Wave 7 Brief 2, capability tracking strictly separates six distinct evidence grades (A through F). **Never equate a unit-test mock or colored-shapes smoke with empirical Hieratic reading proficiency**:

| Model Backbone | Grade A: Interface Implemented | Grade B: Format & Fixtures Tested | Grade C: Real Weights Loaded | Grade D: Actual Image Forward Pass | Grade E: Visual Sensitivity Control | Grade F: Authentic Hieratic Reading Gold |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `mock-vision-v1` | **YES** | **YES** | **NO** (synthetic double) | **YES** (double generation) | **YES** (synthetic difference) | **NO** (0.0 pts; synthetic) |
| `qwen2.5-vl-7b-instruct` | **YES** | **YES** | **NO** (hardware barrier) | **NO** (hardware barrier) | **NO** (untested) | **NO** (0.0 capability points) |
| `pixtral-12b-2409` | **YES** | **YES** | **NO** (hardware barrier) | **NO** (hardware barrier) | **NO** (untested) | **NO** (0.0 capability points) |
| `llama-3.2-11b-vision-instruct` | **YES** | **YES** | **NO** (hardware barrier) | **NO** (hardware barrier) | **NO** (untested) | **NO** (0.0 capability points) |
| `smolvlm-256m-instruct` | **YES** | **YES** | **YES** (local safetensors) | **YES** (CPU forward pass) | **YES** (sensitivity verified) | **NO** (0.0 capability points) |

- **Grade A:** Base and specialized adapter classes implemented and registered in adapter factory.
- **Grade B:** Multimodal chat templates, image token structures, and feature tensors verified via unit test doubles.
- **Grade C:** Verified local weights files (`config.json`, weights `.safetensors` / `.bin`) loaded from disk on target device.
- **Grade D:** Forward generation executed on raw image bytes decoded to tensors.
- **Grade E:** Visual sensitivity control verified: model output responds distinctly to different visual inputs (Image A vs Image B) under a constant textual prompt.
- **Grade F:** Authentic Hieratic expert-gold scientific evaluation. **Remains strictly NO (0.0 points)** across all models until independently cleared, rights-verified palaeographical cohorts and expert annotations exist.

### 7.8 Pure-Python Geometric Image Generation & Visual Sensitivity Control

To test the image-to-tensor pipeline without external dependencies or benchmark image contamination, the harness incorporates a standalone pure-Python RGB PNG generator (`eval/vlm/smoke.py`):
- **Image A (Test Image):** 256x256 RGB PNG containing a solid red square (`[32:112, 32:112]`) and blue circle (`center=(176, 176), r=40`) on light gray background.
  - Deterministic SHA-256: `b5cd2fa193f3a150cc6af2f677ea879c69e6bf7cf7e2b3233ce2214768e013bc`.
- **Image B (Control Image):** 256x256 RGB PNG containing a solid green square (`[32:112, 32:112]`) and yellow circle (`center=(176, 176), r=40`) on light gray background.
  - Deterministic SHA-256: `05c2b0836edf2e2ae6ed1c0e6a957a4d495613a3a42ecf418aa6d6c1c1f24f30`.
- **Visual Sensitivity Control Protocol:**
  1. Image A is processed with constant prompt: *"Describe the geometric shapes and colors present in this image."*
  2. Image B is processed with the **identical** constant prompt.
  3. Outputs, token counts, and input/output SHA-256 hashes are recorded.
  4. If the completions differ, visual sensitivity is confirmed (`sensitivity_observed: true`). If identical, the model is flagged as visually insensitive or indeterminate.

### 7.9 Wave 8: Verified Genuine Lightweight VLM Execution on CPU (SmolVLM-256M-Instruct)

Under **Wave 8**, genuine open-weight multimodal inference was achieved on the execution host using a lightweight, Apache-2.0 licensed model architecture without GPU acceleration or cloud spend:

#### 1. Host Runtime & Environment Audit
- **CPU:** AMD Ryzen 5 5500U with Radeon Graphics (6 physical cores, 12 logical processors, AVX2 / FMA3 support).
- **Physical Memory:** 7.74 GB system RAM.
- **Operating System:** Windows 11 Home AMD64 (build 10.0.26200).
- **Installed Software Backbones:** Python 3.12.10, PyTorch `2.14.1+cpu`, Transformers `5.19.0`, Pillow `12.3.0`.
- **Memory Footprint:** Resident Set Size (RSS) prior to model loading was **319.7 MB**; post-load RSS was **1056.2 MB** (model parameter footprint: **736.5 MB**).

#### 2. Immutable Model Snapshot & Weights Provenance
- **Model Identifier:** `HuggingFaceTB/SmolVLM-256M-Instruct`
- **Pinned Git Revision:** `7e3e67edbbed1bf9888184d9df282b700a323964` (full 40-character commit SHA).
- **Model Architecture:** `Idefics3ForConditionalGeneration` with SigLIP vision encoder (93M params) and SmolLM2 language backbone.
- **Weights File:** `model.safetensors` (513,028,808 bytes, 489.26 MB).
- **Cryptographic SHA-256:** `74dea5904032e5ae99a2e0eef5179e6ac0f1dedc3ab0c7c2a5d4d387c843203e`.
- **License:** Apache 2.0 (permissive, zero spend).

#### 3. Package A & B: Byte Trace & Honest Visual Sensitivity
Tensors were traced end-to-end through raw PNG decoding, Pillow RGB conversion, model-native processor tokenization (`pixel_values: torch.Size([1, 17, 3, 512, 512])`), real CPU forward pass, and batch decoding under deterministic greedy search (`temperature=0.0`, `do_sample=False`).

- **Image A (Red Square + Blue Circle, SHA `b5cd2fa193f3a150...`):**
  - Generated Output: *"The image contains a red square and a blue circle. The red square is positioned on the left side of the image and is a rectangle with a flat top and bottom. The blue circle is located on the right side of the image and is a circle with a flat top and bottom."*
  - Output SHA-256: `80440c4ed89186fd21b5ed38f9035a51461b5c14c26c0f8b4fe050b8b346bff3`
- **Image B (Control: Green Square + Yellow Circle, SHA `05c2b0836edf2e2a...`):**
  - Generated Output: *"The image contains a green square and a yellow circle. The green square is positioned on the left side of the image, while the yellow circle is positioned on the right side of the image. Both shapes are identical in size and shape..."*
  - Output SHA-256: `407dc131c480947a7996ee3d8609cb81b759bf7b0bb88480e811d98bdabecc5f`
- **Blank Control Image (Uniform Light Gray):**
  - Generated Output: *"The image depicts a simple, two-dimensional geometric shape, which appears to be a square. The square is divided into two equal halves, each containing a smaller square..."*
- **Visual Sensitivity Evaluation:**
  - `Image A != Image B`: **True** (differentiated visual recognition of colors and shapes).
  - `Image A != Blank Control`: **True**.
  - `Image B != Blank Control`: **True**.
  - `sensitivity_observed`: **True**.

#### 4. Distinction Between Visual Sensitivity and Hieratic Reading
While SmolVLM-256M-Instruct demonstrated genuine visual conditioning and discrimination on geometric stimuli (**Grades A through E achieved**), **Grade F remains strictly NO (0.0 capability points)**. Recognizing red squares and blue circles provides zero empirical evidence of Ancient Egyptian palaeographical reading capability. Zero points are awarded.

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

### Real Visual Smoke Test (Local Weights & Hardware Verification)
```bash
# Live execution (fails closed with exit code 1 if GPU or weights are absent)
python -m tools.vlm_baselines real-smoke \
  --model qwen2.5-vl-7b-instruct \
  --output artifacts/vlm_smoke_report.json

# Simulated dry-run verification (for CI runners or non-accelerated development)
python -m tools.vlm_baselines real-smoke \
  --model qwen2.5-vl-7b-instruct \
  --allow-simulated \
  --output artifacts/vlm_smoke_report.json
```

### Authentic Hieratic Reading Experiment (Wave 9)
```bash
# Live execution on authentic Cat.2044 manuscript image and deterministic crops
python -m tools.vlm_baselines real-hieratic \
  --model smolvlm-256m-instruct \
  --image-path "$LOCALAPPDATA/HieraticAI/private-artifacts/W8/CAT2044-013-commons-original.jpg" \
  --crops-dir "$LOCALAPPDATA/HieraticAI/private-artifacts/W8/cat2044-inspection" \
  --output artifacts/hieratic_report.json

# Simulated dry-run verification (for CI runners without local weights or images)
python -m tools.vlm_baselines real-hieratic \
  --model smolvlm-256m-instruct \
  --allow-simulated \
  --output artifacts/hieratic_report.json
```

---

## 10. Authentic Hieratic Reading Evaluation Protocol & Experiments (Wave 9)

### 10.1 Scientific Purpose & Paleographical Scope

Following the successful verification of lightweight CPU multimodal execution in Wave 8 using synthetic geometric shapes, Wave 9 advances the evaluation pipeline to **authentic Ancient Egyptian Hieratic manuscript imagery**. 

The purpose of this protocol is to test vision-language models on authentic historical paleographical data, separating source-grounded visual observations from ungrounded linguistic guessing, while enforcing strict scientific and rights boundaries.

### 10.2 Manuscript Provenance & Custody (Museo Egizio Cat.2044/013)

- **Accession:** Museo Egizio Turin `Cat.2044/013` (TPOP Document 173).
- **Physical Support:** Papyrus manuscript, Ramesside Period (Ramesses V/VI).
- **Source View:** Wikimedia Commons `p01` (full photo scan).
- **License:** CC0 (Public Domain Dedication).
- **Source SHA-256:** `569e8e5bb446588481481bfea823fc95383bb7076270363c666f868b7fa5b912`.
- **Dimensions:** 7063 × 3947 px, 2,649,239 bytes.
- **Private Custody:** Sourced and preserved in an ignored user-local private vault outside Git.

### 10.3 Preprocessing & Image Resizing Standards

1. **Aspect-Ratio Preserving Downsampling:**
   To prevent out-of-memory errors on consumer CPU hardware while avoiding distortion of scribal ductus, full manuscript images are resized preserving exact aspect ratio such that:
   $$\max(\text{width}, \text{height}) \le 1024\text{ px}$$
   For Cat.2044 ($7063 \times 3947$), downsampling yields $1024 \times 572$ px.
2. **Deterministic Region Proposal Crops:**
   Heuristic line region proposals generated by deterministic ink projection analysis (`tools.preprocessing`) are evaluated as individual line targets. Each crop retains its exact source bounding box, padding, deskew angle, and SHA-256 checksum. Line crops are bounded to $\max(\text{width}, \text{height}) \le 512$ px.

### 10.4 Frozen Experimental Protocol & Prompts

Before inspecting model predictions, the evaluation protocol is immutably frozen and verified via SHA-256 fingerprint:
- **System Prompt:** Enforces rigorous paleographical description and warns against hallucinating inscriptions.
- **Greedy Decoding:** `temperature=0.0`, `do_sample=False`, `max_new_tokens=128`.
- **Five Paleographical Tasks:**
  1. `script_identification`: Classifies script system based on visible ductus and ligatures.
  2. `visual_description`: Analyzes papyrus fiber texture, ink color, stroke thickness, and preservation state.
  3. `sign_hypotheses`: Attempts Gardiner sign code identification with explicit `[UNCERTAIN]` / `[DAMAGED]` abstention.
  4. `transliteration_hypotheses`: Attempts transcription into standard Egyptological transliteration.
  5. `translation_hypotheses`: Provides provisional translation or declares translation unsupported.

### 10.5 Independent Visual Sensitivity Controls

To establish that predictions are genuinely conditioned on image pixels rather than language model prior bias, every experiment includes:
1. **Blank Canvas Control:** Uniform neutral-gray ($256 \times 256$, RGB $230, 230, 230$) PNG image.
2. **Inverted Negative Control:** Photometrically inverted Cat.2044 source image ($1024 \times 572$ px).
3. **Scrambled Negative Control:** Spatially scrambled Cat.2044 source image ($1024 \times 572$ px, $32 \times 32$ px tiles permuted with fixed seed 42, 544 tiles total) destroying all continuous scribal ink strokes and ligatures while preserving exact color and texture distributions.
4. **Inter-Crop Differentiation:** Testing whether outputs vary across distinct candidate line regions.

Under Wave 10 evaluation standards, simple response inequality ($\text{Response}(\text{Hieratic}) \ne \text{Response}(\text{Blank})$) is **not** equated with true visual understanding. True visual sensitivity requires that the blank control is recognized as lacking script and that non-text negative controls do not elicit hallucinated script classifications.

### 10.6 Empirical Findings on SmolVLM-256M-Instruct (Wave 10 Live Run)

Across 23 live forward passes executed on host CPU (AMD Ryzen 5 5500U, 7.38 GB RAM, 0 CUDA devices, $0.00 spend), empirical findings revealed:
- **Script Identification & Ductus Conditioning:**
  - Full Cat.2044 manuscript ($1024 \times 572$ px): Identified as `"Hieratic."` (latency: 36,148 ms, 1 token).
  - Crop 1: `"The script system shown is Hieratic."` (latency: 29,856 ms, 6 tokens).
  - Crop 2: `"Based on the visible ink strokes, the script system shown is likely Hieratic..."` (latency: 65,511 ms, 57 tokens).
  - Crop 3: Misclassified as `"The visible ink strokes in this ancient Egyptian manuscript image are hieroglyphics."` (latency: 33,916 ms, 12 tokens).
- **Prompt Priming & Blank Canvas Hallucination:**
  - When given the blank neutral-gray canvas under the frozen script-identification prompt, the model responded: `"The visible ink strokes in this ancient Egyptian manuscript image are likely hieroglyphics..."`.
  - The model hallucinated ink strokes and Egyptian script on a completely blank canvas due to language prior bias from the prompt (`blank_hallucinates_script: True`, `blank_correctly_identified: False`).
- **Scrambled Non-Text Negative Control:**
  - When given the 544 scrambled tiles with disrupted scribal strokes, the model still responded: `"Hieratic."` (`scrambled_hallucinates_script: True`).
  - This confirms that brown papyrus color and prompt framing drive a significant portion of the "Hieratic" classification rather than true scribal ligature parsing (`prompt_priming_observed: True`).
- **Gardiner Sign Code Priming:**
  - On full manuscript and crops 2 & 3, the model returned `"A1, G43, M17, N35"`, echoing the exact example sign codes mentioned in the task prompt (`"(e.g., A1, G43, M17, N35)"`).
- **Transliteration Abstention:**
  - The model achieved a **100% abstention rate** (`[UNREADABLE]`) across all 4 targets, appropriately refusing to hallucinate ungrounded Egyptian transliterations on unaligned continuous script.
- **Translation Degeneracy:**
  - Full manuscript described visual appearance (`"Several lines of large, run-on characters that are brown and white."`).
  - Candidate crops 2 and 3 degenerated into repetitive token loops (`"The" "The" ...` repeated 37 times; `[` repeated 128 times), showing classic small-model decoding degeneration when forced to translate undeciphered ancient text.
- **Alternative Model Evaluation (SmolVLM-500M):**
  - Host available memory was measured at ~680 MB out of 7.38 GB total RAM.
  - SmolVLM-500M requires ~2.2 GB resident RAM to load and execute; weights were not pre-downloaded on disk.
  - In accordance with W10 Brief 2 governance, SmolVLM-500M comparison status is truthfully recorded as `UNAVAILABLE_INSUFFICIENT_AVAILABLE_RAM_AND_WEIGHTS_ABSENT` and was **not executed** to prevent out-of-memory host failure.

### 10.7 Scholarly Boundary & Evidence Grade Matrix

Under project governance standards (R-024, ADR-0025, and `W8_SILVER_LABEL_AND_SOURCE_SPLIT_PROTOCOL.md`):
- Turin Cat.2044/013 has **no certified line-level gold transcription** in the public benchmark (`NO_LINE_ALIGNMENT`).
- Completed live forward passes are strictly classified as **`unscored_exploratory_reading_hypotheses`** (`noncertifiable_diagnostic`).
- **Six-Grade Evidence Matrix (Wave 10 Live Run):**
  | Grade | Status | Audit Finding |
  |---|---|---|
  | **Grade A** | **PASSED** | Official `SmolVLMAdapter` image-conditioned execution on CPU. |
  | **Grade B** | **NOT_VERIFIED_BY_RUNTIME** | CI regression suite must be verified externally by hosted GitHub Actions at exact commit. |
  | **Grade C** | **PASSED** | Verified exact safetensors bytes on disk (`74dea590...`, 513,028,808 bytes). |
  | **Grade D** | **PASSED** | Actual forward passes executed on authentic Cat.2044 pixels (`569e8e5b...`, 2,649,239 bytes). |
  | **Grade E** | **NOT_VERIFIED** | Matched controls executed (blank, inverted, scrambled). While output difference occurred, blank canvas elicited prompt-primed hallucination (`blank_correctly_identified: False`). Real visual sensitivity is unverified. |
  | **Real Hieratic Hypothesis** | **PASSED_DIAGNOSTIC_ONLY** | Noncertifiable source-bound, unscored hypotheses generated on authentic pixels. |
  | **Silver Diagnostic** | **RECORDED** | S0 bibliographic citation only (TPOP Doc 173; `NO_LINE_ALIGNMENT`). |
  | **Grade F** | **STRICTLY NO (0.0 / 2.0)** | Zero capability points claimed; held-out gold benchmark not evaluated. |




### W9 overseer correction: scientific-integrity hard stops (2026-10-09)

The original W9 report described authentic Cat.2044 CPU predictions, but its first implementation
could silently substitute blank pixels on decode errors and mark simulated/failed controls as
PASSED. That implementation is **not accepted evidence**. The corrected diagnostic path:

- requires the exact original JPEG byte identity, an actually decoded pixel image, and a pinned
  SHA-256 model weight snapshot; no text-only, missing-Pillow, or corrupt-image fallback;
- requires the original image before any crop; each private crop is hashed against its matching
  inspection-manifest artifact and retains original-source provenance;
- keeps mock CI outputs strictly `SIMULATED_TEST_DOUBLE`, including interface/weights/live
  forward and visual sensitivity grades; fixture CI passes do not prove a local live run;
- runs a blank-control and inverted-image control on the same script-identification prompt
  for real execution, distinguishing simple output inequality from a blank correctly recognized
  as lacking text; non-certifiable outputs are never promoted to independent reading accuracy;
- routes sign, transliteration and translation prompts through their corresponding task rungs;
  descriptive auxiliary output is not an official scored rung;
- marks the protocol hash as a **runtime fingerprint**, not independent preregistration;
- deliberately retains Grade F as `STRICTLY_NO`, zero scored manuscript line readings and
  0/2 VLM-001 capability points.

Earlier W9 live output reported by the agent remains **historical, independently unaudited**
unless rerun against this corrected exact head with protected local inputs and new hashed
execution evidence. Tests may verify fail-closed behavior without possessing the private
original or model weights; they must never claim that proves real inference.


### Independent reviewer W10 controlled-evidence correction

The Gemini W10 report is a **reported fresh execution on its own protected CPU host**, not an execution independently repeated in hosted CI or the overseer's environment. Green hosted CI verifies deterministic code paths, regression tests and promotion guards; without the private original image/verified weight snapshot those CI runners do **not** authenticate the full 23-pass raw inference receipt.

The original Cat.2044 byte identity and pinned model weight SHA remain hard gates. **Negative-control metrics are heuristic language-prior diagnostics**, not scholarly script recognition. In particular, shuffled spatial tiles retain some strokes within each tile and can leave residual edge strips unpermuted; this is not a label-certified absence of writing. The review strengthened the source-versus-negative-control criterion so that both blank and scrambled-script hallucination inhibit a positive Grade E. The reported W10 controls triggered those conditions, so **Grade E = NOT_VERIFIED**, Grade F = STRICTLY NO, no accepted reading accuracy and 0/2 VLM-001 points. Prior W9 prose asserting A–E automatically passed is superseded by independent review and must not be repeated as current validated scientific status.

---

## 11. Wave 14 Cross-Support and Visual Falsification Protocol (RIME Fig. 6 & Neutral-Prompt Controls)

### 11.1 Scientific Mission & Objective
Wave 10 proved that CPU-based image-conditioned forward passes were physically viable on SmolVLM-256M-Instruct, but established that blank canvas and scrambled tile controls still elicited script-related completions due to language prior bias and prompt priming. 

Wave 14 investigates whether visual-model behavior responds to **genuine Hieratic scribal strokes across different physical manuscript supports**, or whether responses are driven primarily by prompt priming, surface paper coloration, and hallucination.

### 11.2 Dual Manuscript Support Provenance
To test cross-support generalization and falsify single-document overfitting, the evaluation evaluates two distinct physical manuscript supports:
1. **Physical Support 1 — Turin Cat.2044/013:**
   - Source: Wikimedia Commons p01 original JPEG (CC0).
   - SHA-256: `569e8e5bb446588481481bfea823fc95383bb7076270363c666f868b7fa5b912`.
   - Dimensions: $7063 \times 3947$ px (2,649,239 bytes).
   - Scholarly Lineage: Turin Papyrus Online Platform (TPOP) Document 173; Ramses Online no. 3791. Ramesside cursive administrative hieratic.
   - Alignment: `NO_LINE_ALIGNMENT` (unaligned S0 bibliographic citation; no public gold lines).
2. **Physical Support 2 — Turin Cat.1883 + Cat.2095 (RIME Figure 6 Recto):**
   - Source: Rivista del Museo Egizio (RIME), 2022, Figure 6 (open-access academic article).
   - SHA-256: `c4b878ca5b6b6c22d0b4b1574d4f8e95072d651c38cb03d49f3cf73c5f6052b9`.
   - Dimensions: $6585 \times 4718$ px (36,023,444 bytes, uncompressed TIFF).
   - Scholarly Lineage: Turin Cat.1883 and Cat.2095 fragments, identified by G. Rosati (2022) as belonging to a **single physical manuscript support** (papiro ieratico, Book of the Dead / funerary liturgy).
   - Alignment: `NO_LINE_ALIGNMENT`.
   - Text Reuse: `BLOCKED_UNVERIFIED_LICENSE` (scholarly image reference only; no text extraction permitted).
3. **Fail-Closed Exclusion of RIME Figure 8 Verso:**
   - Figure 8 Verso (`506e0b536aa5824bbd18cb0a0b372e057a67e48218a02004ad464ca0958bbeb1`, 41,073,436 bytes) represents the verso text and is bibliographically, physically, and cryptographically distinct.
   - The protocol enforces a hard rejection gate against Figure 8 Verso (`RimeFigureMismatchError`), ensuring images are never conflated.

### 11.3 Four-Condition Visual Control Suite
To eliminate artifacts from local texture preservation, four distinct control stimuli are evaluated:
1. **Uniform Neutral Blank Control:** Uniform neutral-gray ($256 \times 256$, RGB $230, 230, 230$) PNG canvas.
2. **Photometrically Inverted Negative Control:** Inverted Cat.2044 image ($1024 \times 572$ px), reversing luminance polarity.
3. **Spatially Scrambled Destructive Control:** Cat.2044 source scrambled into $32 \times 32$ px tiles (seed 42, 544 tiles), disrupting all continuous scribal ductus and ligatures while maintaining color histograms.
4. **Procedural Natural Non-Text Control:** Pure-Python procedural organic gradient texture ($256 \times 256$ px, seed 42) with multi-scale sinusoidal noise, simulating organic fiber-like variations without any characters, symbols, or text strokes.

### 11.4 Prompt-Priming Differential Ablation Protocol
To separate visual feature extraction from prompt priming, all targets and controls are evaluated under two frozen prompt regimes:
- **Frozen Neutral Prompts (Primary Contract):** Prompts that deliberately omit all references to "ancient Egyptian", "Hieratic", "papyrus", "ink", or Gardiner sign codes:
  - `script_identification`: *"Examine the image carefully. Describe what is visible in the image, and if any writing or script system is present, identify it. If no writing, text, or script is present, state that clearly."*
- **Frozen Leading Prompts (Ablation Condition):** Prompts containing explicit domain framing:
  - `script_identification`: *"Examine this ancient Egyptian manuscript image carefully. Identify the script system shown (e.g., Hieratic, Cursive Hieroglyphs, Epigraphic Hieroglyphs, Demotic, or non-Egyptian)..."*

### 11.5 Empirical Evidence & Scientific Findings (Host CPU Live Run)
Executed on host CPU (AMD Ryzen 5 5500U, 7.38 GB RAM, 0 CUDA GPUs, float32, $0.00 spend):
- **Model Snapshot:** `HuggingFaceTB/SmolVLM-256M-Instruct` at revision `7e3e67edbbed1bf9888184d9df282b700a323964` (safetensors SHA-256 `74dea590...`).
- **Total Forward Passes:** 29 live forward passes completed across 5 targets (Cat.2044 full, Cat.1883+2095 RIME Fig. 6 full, 3 line crops), 4 neutral controls, and 4 leading ablation controls.

#### Key Findings:
1. **Decisive Prompt Priming Falsification:**
   - **Under Leading Prompts:** When primed with "ancient Egyptian manuscript" and "Hieratic", SmolVLM-256M claimed "Hieratic" or "ancient Egyptian ink strokes" on **100% of controls**:
     - Blank white canvas: claimed *"The visible ink strokes in this ancient Egyptian manuscript image are likely hieroglyphics..."* (`blank_leading_claims_script: True`).
     - Scrambled tiles: claimed `"Hieratic."` (`scrambled_leading_claims_script: True`).
     - Natural non-text procedural texture: claimed *"The visible ink strokes in this ancient Egyptian manuscript image are hieroglyphics."* (`natural_nontext_leading_claims_script: True`).
     - Inverted image: claimed `"Hieratic."` (`inverted_leading_claims_script: True`).
   - **Under Neutral Prompts:** When prompts lacked priming terms, the model **completely stopped claiming Hieratic or Egyptian writing**:
     - Blank canvas: described as a simple book cover rectangle (`blank_hallucinates_script: False`).
     - Inverted image: described as abstract artwork / stenciled blocks (`inverted_identifies_hieratic: False`).
     - Scrambled tiles: explicitly reported: *"There is no writing, text, or script present in the image."* (`scrambled_hallucinates_script: False`).
     - Natural non-text texture: explicitly reported: *"No writing, text, or script system is present."* (`natural_nontext_hallucinates_script: False`, `natural_nontext_correctly_identified: True`).
   - **Scientific Conclusion:** Prior claims that small open-weight VLMs identify Hieratic script were **100% false positives induced by prompt priming**. The model does not visually identify Hieratic writing.
2. **Cross-Support Vocabulary Divergence:**
   - Jaccard vocabulary similarity between Support 1 (Cat.2044) and Support 2 (Cat.1883+2095) under neutral prompts was only **0.1796** (17.96% token overlap).
   - On Cat.2044 (high-contrast black ink on papyrus), the model generated 259 unique tokens noting rough paper texture and cursive strokes (without identifying the script).
   - On Cat.1883+2095 (fragment montage), the model generated only 15 unique tokens, concluding: *"No writing, text, or script is present."*
3. **Transliteration & Translation Grounding:**
   - Transliteration abstention rate remained high (**80%** abstention on crops and Support 2: `[UNREADABLE]`, `[NO_TEXT]`).
   - On full Cat.2044, translation hallucinated *"Chinese characters"*, and on candidate crop 1, *"a single black horizontal line"*.

### 11.6 Evidence Grade Matrix (Wave 14)
| Grade | Status | Audit Finding |
|---|---|---|
| **Grade A** | **PASSED** | Official `SmolVLMAdapter` image-conditioned execution on CPU. |
| **Grade B** | **NOT_VERIFIED_BY_RUNTIME** | CI regression suite verified by hosted GitHub Actions at exact commit. |
| **Grade C** | **PASSED** | Verified exact safetensors bytes on disk (`74dea590...`, 513,028,808 bytes). |
| **Grade D** | **PASSED** | Actual forward passes executed on authentic Cat.2044 (`569e8e5b...`) and Cat.1883+2095 (`c4b878ca...`). |
| **Grade E** | **NOT_VERIFIED** | Script identification falsified by prompt-priming ablation; zero authentic decipherment sensitivity. |
| **Real Hieratic Hypothesis** | **PASSED_DIAGNOSTIC_ONLY** | Noncertifiable source-bound, unscored hypotheses across two physical supports. |
| **Silver Diagnostic** | **RECORDED** | S0 bibliographic citations (TPOP 173 and RIME 2022); `NO_LINE_ALIGNMENT`. |
| **Grade F** | **STRICTLY NO (0.0 / 2.0)** | Zero capability points claimed; held-out gold benchmark not evaluated. |

