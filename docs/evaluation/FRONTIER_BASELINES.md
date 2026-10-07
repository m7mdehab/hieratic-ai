# Untuned Frontier VLM Baselines — Pre-registered Protocol and Evidence Contract

**Task:** EVAL-003 (active, not validated)  
**Protocol:** HIERATIC-FRONTIER-UNTUNED-V1  
**Date:** 2026-10-08  
**Authoritative machine suite:** `eval/baselines/suite.yaml`  
**Official benchmark revision:** `alymoursy/hieraticbench@d587dc990013f18007f1e7a8f56f96ff2f7127e2`  
**Research state:** Zero newly run project baselines, zero validated model experiments, zero trained models.

## 1. Scientific question and guardrails

How well do contemporary untuned multimodal frontier models recognize Egyptian writing as a script **versus actually identify isolated Hieratic signs** on a held-out, evaluation-only benchmark?

These are distinct tasks. No image-to-hieroglyphic sequence, meaningful transliteration or translation success can be inferred from successful script identification alone.

The published HieraticBench results reproduced under EVAL-002 are **historical upstream measurements**. They are not fresh provider calls conducted by this project, and EVAL-003 must not double count them as newly validated capability. The two commissioned sealed images have no publicly scored reading gold; the current baseline excludes them completely.

## 2. Frozen evaluation surface

The initial independent external track is confined to:

| Rung | Permitted public items | Interpretation |
|---|---:|---|
| Script identification | 116 | Public-document/control script categorization |
| Public isolated signs | 150 | Gardiner-code single-sign recognition |
| Sealed sentence images | 0 | Explicit exclusion from this local run |
| Public sentence transliteration/translation | 0 | No publicly scored gold in the current upstream snapshot |

The actual item IDs/rung combinations must be extracted from the **pinned external checkout**, frozen in an immutable public-only JSONL manifest and hashed before model inference. Never fabricate 116/150 data records from counts. The run preflight must compare candidate item IDs against the pinned upstream item metadata. No benchmark image or gold code is to be committed to Hieratic AI or used in training/dev.

The official upstream `bench/src/prompts.ts` supplies separate cold script-identification and sign-level tasks. Keep the exact text, required labels, absence of system prompt/examples/tools, and raw-output parser. Do not replace the upstream scorer/normalizer with the EVAL-001 profile. The prompt text/implementation bundle must be hashed and frozen before results.

## 3. Model selection and provider-route control

The initial **candidate provider lanes**, not yet verified deployable model IDs:

- OpenAI multimodal frontier model;
- Anthropic multimodal frontier model;
- Google multimodal frontier model.

Before execution, freeze for each:
- exact provider model identifier/version (avoid changing aliases where immutable IDs are available);
- API route (direct provider, proxy/OpenRouter, etc.);
- reasoning-effort configuration and provider limits;
- image input parameters/preprocessing and output limits;
- pricing/quotas and estimated total spend;
- retries/timeouts and error handling;
- provider terms and retention/research-compliance review.

Research models and execution agents are **not synonymous**. Sonnet/Gemini working on the dashboard are not thereby automatically model evaluations; the model under test must make image-input calls under a logged and approved protocol.

Use a paired eligible-item subset and comparable inference budget wherever possible. If one provider cannot process an image or lacks equivalent effort control, document and retain the failure rather than silently substituting a better model or narrowing its denominator.

## 4. Untuned baseline rules

All baseline candidates start from vendor-provided multimodal checkpoints without Hieratic fine-tuning, retrieval access, added OCR tools, additional examples or learned task-specific prompts.

Official identify rung is cold. The official isolated-sign rung tells the model the image contains Egyptian Hieratic. Report both rungs separately and do not conflate this sign prompting with cold recognition.

- No test-set prompt engineering after scores are seen.
- No iterative API calls to the sealed set.
- No selective exclusion of refusals, errors, unparseable answers or low-confidence predictions.
- No manual correction of raw responses.
- Record vendor nondeterminism even when a seed is unsupported.
- Preserve retries under explicit attempt identifiers; fixed planned attempts form the primary denominator.
- Report effort/cost/latency transparently without equating effort labels across vendors.

## 5. Reproducibility and security architecture

The project exposes only **metadata/code** in Git. Raw model responses and provider receipt IDs must go into a private external artifact directory or store and remain immutable for audit. It is forbidden to put those responses or test gold into a source training directory.

The companion CLI `eval/baselines/baselinectl.py` has three read-only modes:

```bash
# Verify that the proposal schema and fixed scientific restrictions are valid.
python -m eval.baselines.baselinectl validate-suite

# Will fail, intentionally, while provider IDs, budget and other gates are unresolved.
python -m eval.baselines.baselinectl preflight

# After approved inference, audit a local raw-capture archive without printing it:
python -m eval.baselines.baselinectl audit-capture \
  --suite /path/to/frozen-suite.yaml \
  --items /private/public-items.jsonl \
  --capture /private/raw-responses.jsonl \
  --receipt /private/capture-receipt.json \
  --upstream-checkout /private/pinned-hieraticbench
```

`audit-capture` checks:
- suite and model identity;
- frozen public-item and exact-prompt SHA-256 refs;
- item/rung/attempt uniqueness;
- full planned item×sample coverage, including failed calls;
- per-response provider ID and prompt consistency;
- content SHA-256 of raw response archive;
- optional exact pinned upstream membership validation through EVAL-002's metadata-only adapter.

It **does not** call a provider, read images, compute official scores, evaluate translation quality or claim that human review took place. It emits counts and integrity status, never raw response text.

A `captured` receipt is neither a `scored` run nor a validated scientific experiment.

## 6. Model evaluation, metrics and paired comparison

When external inference is eventually approved and complete:

1. Verify item/attempt coverage with this capture auditor.
2. Score raw responses using the **pinned upstream official** parsing/scoring code, not a newly improvised scoring implementation.
3. Reproduce its numeric aggregation independently using the EVAL-002 adapter where appropriate.
4. Report rung-level official scores, eligible and attempted denominators, coverage and failure reasons.
5. Report script-family error breakdown and isolated-sign confusion/error taxonomy, using EVAL-005, as separate diagnostics.
6. Distinguish accuracy-like official partial-credit script-ID score from EVAL-001 `SCRIPT_ACC` and `SCRIPT_MACRO_F1`.
7. Produce document-group paired comparisons/uncertainty intervals only on truly paired sets with suitable sample support.
8. For period/scribe/generalization claims, wait for EVAL-004 reviewed split integrity and suitable metadata.
9. Exclude all sealed-label extrapolations from this release; a hidden answer key is not assumed.

No primary composite score; never let strong script identification or fluent words mask sign recognition failure.

## 7. Execution authorization and spend

The machine suite is intentionally marked `planning`. Its execution gate requires:

- [ ] Exact current API-accessible model IDs and supported inference configurations confirmed.
- [ ] Provider credentials available in a restricted runtime; no keys in Git.
- [ ] Provider terms and model/service rights reviewed.
- [ ] Explicit user approval for paid inference and maximum USD spend.
- [ ] Frozen public item/rung manifest with SHA-256, verified against pinned upstream metadata.
- [ ] Frozen official prompt implementation/byte hash.
- [ ] Dedicated external private artifact storage configured.
- [x] EVAL-002 official scorer parity established.
- [ ] All run models compared under a predeclared protocol.

With three providers, 266 public item-rung combinations and three samples per item, a full round would plan **2,394 inference attempts** before any retries. This is a planning quantity, **not an actual call count or price estimate**. A smaller *predeclared* pilot may establish provider integration feasibility but cannot substitute for a full comparable baseline without a separately frozen coverage claim.

Do not turn `status: execution_ready` on merely to make the tool pass; the permissions, cost and artifact gates must be genuinely satisfied.

## 8. Acceptance criteria for 1.5 project points

This iteration produces the protocol/tooling foundation. EVAL-003 remains **active, not validated** until:

- [ ] Selected model IDs/settings recorded and fixed before inference.
- [ ] Comparable public item/rung sample set verified and frozen.
- [ ] Exact prompts/official scorer pinned; no adaptive test prompting.
- [ ] Approved model inference completed with complete raw outputs (including failures).
- [ ] Immutable run config, raw archive, hashes, provider receipts, cost and environment recorded.
- [ ] Official per-layer scores revalidated, with paired coverage and confidence limits.
- [ ] Artifact provenance, licensing, contamination, and access limits independently reviewed.
- [ ] At least one reproducible model-run evidence packet passes the FND-006 experiment contract.
- [ ] Findings and limitations recorded in `EXPERIMENTS.md` and technical research report.
- [ ] Overseer explicitly accepts task and awards full 1.5 points (no fractional award for a spec alone).

## 9. Proof available in this PR

- Frozen **proposal**, not finalized payable execution config: `eval/baselines/suite.yaml`.
- JSON Schema and fail-closed plan/capture audit implementation.
- Synthetic tests demonstrating incorrect sealed access, altered prompt hash, incomplete attempt capture, mismatched provider IDs and raw-repository storage are refused.
- CI with no provider API access or external images.
- No new model scores, no real benchmark gold, no copies of raw third-party assets.

This creates the technical and scientific preconditions for honest EVAL-003 baseline experiments, without claiming they already exist.


## 10. Pinned, deterministic public item and prompt-source freeze utility

New `eval/baselines/public_freeze.py` is a **non-inference artifact preparer**: it obtains the metadata-only inventory from EVAL-002's pinned HieraticBench adapter, selects exactly 116 public script-ID items and 150 public isolated-sign items, and emits a sorted JSONL of **only item_id, rung, split**. Both sealed items are excluded.

It separately hashes the exact upstream `bench/src/prompts.ts` bytes (rather than copying those prompts into our repository). Receipt includes the item-manifest SHA-256, official prompt-source SHA-256, pinned upstream Git SHA, safe item-rung counts and an explicit exclusion/no-training declaration.

Usage, with a pinned **external** checkout and an existing **external artifact directory**:

```bash
python -m eval.baselines.public_freeze freeze \
  --checkout /external/pinned-hieraticbench \
  --output-dir /private/hieratic-baseline-freeze

python -m eval.baselines.public_freeze verify \
  --checkout /external/pinned-hieraticbench \
  --output-dir /private/hieratic-baseline-freeze
```

The tool fails closed on mismatched Git commit, missing prompt-source bytes, unexpected rung inventory, sealed exposure, write locations under this repository, attempted overwrite and mutated artifact receipt/bytes.

**Important limits:**
- The receipt contains prompt-**source** byte hashes, not a cryptographic digest of every dynamically composed runtime prompt. Before actual paid inference, the EVAL-003 provider adapter must additionally freeze the exact rendered item prompt bytes and image preprocessing configuration. Neither a source hash nor receipt by itself proves executed runtime prompts matched.
- This produces benchmark evaluation metadata only; it grants no right to train on HieraticBench or related source crops.
- External checkout in CI is ephemeral and must not upload public gold, model responses or images.
- The new receipt is not automatically inserted into `suite.yaml` because the suite remains `planning` until explicit provider/budget approval.
- No model calls, metric scores or accepted EVAL-003 points are created.
