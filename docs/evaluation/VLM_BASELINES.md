# VLM Baseline Evaluation Protocol: Zero-Shot & Few-Shot Benchmarking

## 1. Overview & Scientific Purpose

This protocol establishes a scientifically reproducible, untuned zero-shot and few-shot Vision-Language Model (VLM) baseline suite for Hieratic script reading across multiple reading stages:
1. **Script Identification (`identify`):** Classifying ancient Egyptian manuscript fragments into Hieratic, Hieroglyphic, Demotic, or Coptic.
2. **Isolated Sign Recognition (`signs`):** Identifying individual Hieratic characters and sign clusters into canonical Gardiner sign codes.
3. **Sequential Transliteration (`transliterate`):** Transcribing continuous line passages into standardized Egyptological transliteration.
4. **Translation (`translate`):** Translating continuous Hieratic texts into grammatical English.

This suite is developed independently from the overseer's `EVAL-003` frontier proprietary model comparison (`eval/baselines/**`). It focuses on open-weight multimodal architectures, cryptographic prompt contracts, quarantined few-shot demonstration banks, complete attempt accounting, and rigorous uncertainty reporting.

---

## 2. Frozen Evaluation Suite (`eval/vlm/suite.yaml`)

### 2.1 Model Candidates

| Key | Model Name | Architecture / Provider | License | Modality | Hardware Prerequisite |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `mock-vision-v1` | Deterministic Synthetic Baseline | Internal synthetic harness | Apache-2.0 | Multimodal (Image + Text) | CPU (Offline) |
| `qwen2.5-vl-7b-instruct` | Qwen 2.5 VL 7B Instruct | Alibaba Cloud / Qwen | Apache-2.0 | Multimodal (Vision-Language) | CUDA GPU (>= 16 GB VRAM) |
| `pixtral-12b-2409` | Pixtral 12B | Mistral AI | Apache-2.0 | Multimodal (Vision-Language) | CUDA GPU (>= 24 GB VRAM) |
| `llama-3.2-11b-vision-instruct` | Llama 3.2 11B Vision Instruct | Meta | Llama-3.2-Community | Multimodal (Vision-Language) | CUDA GPU (>= 24 GB VRAM) |

### 2.2 Execution Gates

To eliminate unapproved API spending and ensure scientific reproducibility, the evaluation suite enforces strict gates:
- `max_paid_spend_usd: 0.0`: Unapproved paid external API calls are strictly blocked.
- `require_image_conditioning: true`: All evaluation runs must provide valid image bytes. Text-only guesses or unconditioned mock shortcuts fail closed.
- `allow_network_inference: false`: Tests and evaluations default to local, offline-verifiable execution.
- `offline_reproducible: true`: Artifact generation and metric scoring must be entirely deterministic offline.

### 2.3 Image Preprocessing Standards

To ensure consistent model conditioning:
- **Maximum Dimension:** 1024 px along the longest edge (aspect ratio strictly preserved).
- **Minimum Dimension:** 64 px.
- **Color Space:** Standard 3-channel RGB.
- **Format:** High-quality JPEG or lossless PNG.
- **Normalization:** Standard RGB channel mean/variance scaling when loaded by neural vision backbones.

### 2.4 Decoding Parameters

All baseline comparisons use deterministic greedy decoding to avoid sampling variance:
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

As established in `DATA_LICENSING_AND_PROVENANCE_POLICY.md` and `eval/benchmarks/hieraticbench/manifest.yaml`:
- HieraticBench assets are licensed strictly for **external evaluation only**.
- Public benchmark items, test images, references, and near-duplicates **must never** be used as few-shot demonstrations, prompt optimization examples, or fine-tuning datasets.

### 3.2 Quarantined Demonstration Bank (`eval/vlm/demonstrations.yaml`)

To permit scientifically valid few-shot evaluation without test contamination:
1. **Independent Sourcing:** Demonstrations are drawn exclusively from public domain palaeographical facsimiles:
   - Georg Möller, *Hieratische Paläographie* (Vols. 1–3, 1909–1912; Public Domain).
   - Richard Lepsius, *Denkmäler aus Aegypten und Aethiopien* (1849; Public Domain).
   - Wilhelm Spiegelberg, *Demotische Grammatik* (1925; Public Domain).
2. **Rights Review:** Formally approved under rights class `OPEN-PD` (`rights_review_status: "approved_with_evidence"`).
3. **Automated Leakage Checks:** The CLI (`tools/vlm_baselines.py validate-demonstrations`) and test suite verify:
   - Zero overlap with evaluation items or split manifests.
   - Prohibition of reserved HieraticBench ID prefixes (`AKU-`, `CBL-`, `HB-`, `MET-`, `WM-`, `YPM-`).

---

## 4. Attempt Preservation & Missing-Data Accounting

In accordance with empirical benchmarks standards, **every attempted evaluation item must be preserved**:
- **Success (`success`):** Model returned a valid completion within latency and resource limits.
- **Abstention (`abstained`):** Model explicitly declined to predict due to uncertainty (e.g., `[ABSTAIN]`, `UNCERTAIN`).
- **Refusal (`refused`):** Model safety filters blocked output generation.
- **Timeout (`timeout`):** Model exceeded inference latency threshold.
- **Failure (`failed`):** Runtime crash, memory error, or unhandled exception.

### Coverage Rate Calculation

$$\text{Coverage Rate} = \frac{N_{\text{success}}}{N_{\text{total attempts}}}$$

The evaluation auditor (`tools/vlm_baselines.py audit-manifest`) rejects any run manifest where:
- Attempt count does not match the total sample universe.
- Any failed or abstained attempt has been silently omitted.
- Raw outputs or error messages are missing.

---

## 5. Scoring & Uncertainty Quantification

### 5.1 Stage Metrics Aligned with `eval/metric_contract.yaml`

1. **Script Identification (`identify`):**
   - **Primary Metric:** Script Classification Accuracy (`SCRIPT_ACC`)
   - **Selective Reporting:** Abstention rate and selective risk.
2. **Sign Recognition (`signs`):**
   - **Primary Metric:** Gardiner Code Exact Match Accuracy (`SIGN_ACC`).
3. **Transliteration (`transliterate`):**
   - **Primary Metric:** Character Error Rate ($\text{CER} = \frac{\text{Levenshtein}(R, H)}{\text{Length}(R)}$)
   - **Secondary Metrics:** Word Error Rate (WER) and Character Accuracy ($\max(0, 1 - \text{CER})$).
4. **Translation (`translate`):**
   - **Primary Metric:** Sentence-level BLEU-4 with brevity penalty.
   - **Secondary Metric:** Character n-gram F-score (chrF++).

### 5.2 Uncertainty Reporting

- **Non-Parametric Bootstrap:** For every metric, 95% confidence intervals are computed via $B=1000$ bootstrap resamples.
- **Paired Comparisons:** When comparing two models or contrasting zero-shot against few-shot performance on identical item sets, the paired delta ($\Delta = \text{Score}_B - \text{Score}_A$) and its 95% bootstrap confidence interval are reported.

---

## 6. CLI Usage Guide

The CLI tool (`tools/vlm_baselines.py`) provides controlled operations:

### Validate Suite Configuration
```bash
python -m tools.vlm_baselines validate-suite
```

### Validate Demonstration Bank Quarantine
```bash
python -m tools.vlm_baselines validate-demonstrations
```

### Execute Evaluation Run
```bash
python -m tools.vlm_baselines run \
  --model mock-vision-v1 \
  --shot-mode both \
  --output artifacts/vlm_manifest.json
```

### Audit Completed Run Manifest
```bash
python -m tools.vlm_baselines audit-manifest \
  --manifest artifacts/vlm_manifest.json
```

### Score Run Manifest
```bash
python -m tools.vlm_baselines score \
  --manifest artifacts/vlm_manifest.json \
  --output artifacts/vlm_score_report.json
```

### Paired Comparison
```bash
python -m tools.vlm_baselines paired-compare \
  --manifest-a artifacts/vlm_manifest_zero.json \
  --manifest-b artifacts/vlm_manifest_few.json \
  --output artifacts/vlm_comparison.json
```

---

## 7. Hardware Boundaries & Disclosure

1. **Certified Harness:** This task delivers the complete, audited evaluation harness, schemas, adapters, quarantined few-shot bank, synthetic benchmarks, and CI.
2. **Hardware Gating for Live Models:** Real inference over large open-weight models (`Qwen2.5-VL-7B`, `Pixtral-12B`, `Llama-3.2-11B`) requires dedicated local GPU hardware (NVIDIA CUDA with $\ge 16$ GB VRAM) and downloaded model weights.
3. **Zero Falsified Evidence:** In standard developer environments or CI lacking dedicated GPUs, `OpenWeightVLMAdapter` cleanly reports the hardware barrier without generating falsified synthetic model scores or attempting unapproved paid network calls.
