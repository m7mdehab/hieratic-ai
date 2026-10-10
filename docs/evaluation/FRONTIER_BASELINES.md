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


## 11. W3: byte-verified model attempt freeze and external rights evidence (PR candidate)

The `eval/baselines/run_freeze.py` validator and `eval/baselines/run_freeze.schema.json` add **per-model** preregistration independent of EVAL-006's future truly sealed corpus releases. The frozen metadata records one exact provider model/version, route, benchmark revision, original scorer and prompt source SHA-256, accepted EVAL-001 metric contract, configuration, run environment, inference commit, budget cap, and identity of the human authorizing use/spending.

The private `prompt-attempts.jsonl` must enumerate every `(item_id, rung, sample_index)` in the actual pinned public set. Each row points to *external, restricted* rendered prompt bytes and evaluation-only image bytes and includes independent SHA-256 checksums. The preflight reads those bytes only to confirm hashes; it never publishes their content, scores, or answers. It refuses inconsistent prompt/image copies, changed official scorer source, incomplete 116/150 public coverage, missing attempts, extra sealed IDs, unknown aliases, path traversal or evidence inside the public Git repository.

**Difference from earlier `public_freeze.py`:** that prior tool hashes upstream **prompt source code** and permitted item IDs; it does not prove what item-specific rendered text or image was actually supplied to a provider. The new audit binds each planned attempt to real private bytes and the exact official scorer. This is *necessary* before honest paid inference but is still only preregistration. It does not validate that a provider later used the approved prompt bytes or faithfully returned an output; that requires separate immutable provider request/response receipts and scorer replay.

```bash
# Public, intentionally incomplete and non-executable synthetic draft:
python -m eval.baselines.run_freeze validate-draft

# A run that claims to be locked must not pass without separate human
# authorization, immutable evidence and externally reviewed rights.
# This read-only CLI intentionally refuses user approval via a fake toggle.
python -m eval.baselines.run_freeze verify-locked \
  --record /private/run-freeze.json \
  --suite /private/suite.yaml \
  --items /private/public-item-rungs.jsonl \
  --attempts /private/prompt-attempts.jsonl \
  --vault /private/evaluation-vault \
  --upstream-checkout /private/hieraticbench
```

### Preserve per-attempt prompt and response identity

The older `baselinectl.audit-capture` checks a single suite-level prompt-bundle digest and is **not sufficient for an original run with item-specific rendered prompts**. It can remain as a preliminary legacy integrity check, but it cannot certify W3 model runs.

The new `run_freeze.audit_original_capture(...)` pairs every private raw-response record with its unique frozen item/rung/sample prompt SHA-256 and its actual input image bytes. It separately checks the capture archive hash, exact model identity and complete attempt universe. Successful answers must retain original provider response IDs; failures, abstentions, timeouts and refusals must all remain in the denominator. It emits only status tallies, never model outputs or hidden answer keys.

This audit must still be accompanied by authenticated provider request logs, independently verified permission receipts, source rights and replay of the pinned upstream official scorer before EVAL-003 can earn capability points. The code deliberately makes `scoring_reproduced=False` and `scientific_experiment_validated=False` for any metadata audit result.

**Authorization control:** No automation, chat response or Boolean in the record substitutes for explicit user budget approval. A qualified operator can invoke `validate_locked(... actual_approval_confirmed=True)` programmatically only after checking the genuine human authorization and item rights outside the repo. This intentionally avoids any runnable paid inference in GitHub CI.

**A synthetic "passing locked record" in unit tests is not actual authorized execution or rights clearance**. The tests mock an upstream audit and use harmless fake bytes outside the checkout to verify fail-closed logic. Do not cite their success as evidence of real model coverage or official scores.

## 12. Primary-source rights audit and corpus/evaluation interfaces

See `eval/baselines/SOURCE_RIGHTS_READINESS.md` for the 2026-10-08 evidence audit, including current HPDB, AKU-PAL, DDD, TLA, PaPYrus, HieraticAI, Isut and HieraticBench policy distinctions. No source was newly cleared for unrestricted training, no external item downloaded or inserted into an ML corpus, and no real expert gold found.

The W3 task boundaries are deliberate:
- DATA-008 releases a train/dev/test corpus **only when actual item rights and expert adjudication exist**; otherwise only a synthetic demonstration and a blocked-release report are honest outputs.
- VLM-001 measures an actual zero/few-shot image-conditioned baseline only after approved runtime/model access and non-benchmark, licensed few-shot examples; benchmark public items never become training/dev prompts.
- EVAL-003 focuses on untuned vendor frontier models with identical, predeclared official public item/rung surface and no image-based prompt tuning.

No accepted scientific capability points accrue from this W3 methodology work alone. The canonical goal remains **30.5/100** pending actual independently accepted weighted tasks.


## 13. Original native HieraticBench public scorer replay, no reimplementation

`eval/baselines/official_replay.mjs` imports **the actual pinned upstream TypeScript `bench/src/score.ts`** through Node/tsx from the frozen checkout (`d587dc990013f18007f1e7a8f56f96ff2f7127e2`). It reads authorized public metadata/gold from upstream *in memory*, combines them with a private externally stored response JSONL archive, and writes only a redacted aggregate JSON report to an external directory. It will not import anything from `data/private` or the commissioned sealed pair.

This is necessary to complete EVAL-003's requirement that **official scoring be executed**, not reimplemented or inferred from published leaderboard numerics.

**Preconditions for actual original-run scoring:**
1. User explicitly approves provider spend/rights separately; authenticated actual provider raw capture and immutable provider receipts exist.
2. `eval.baselines.run_freeze.validate_locked` confirms the real per-attempt rendered prompt/image hash and complete pinned 266 item-rung universe; `audit_original_capture` verifies every original response including errors/refusals.
3. Native replay `--checkout` must point to the exact external pinned HieraticBench Git revision and must have Node 22/tsx dependencies installed from its committed lockfile.
4. Private `--freeze`, `--receipt`, `--items`, `--attempts`, `--capture` and `--output-dir` paths must be outside this public repository. The replay checks byte-level hashes of pinned scorer/prompt source, item/attempt/archive records and provider/model identity.
5. Independent research reviewer must verify the underlying provider logs, rights grants, complete attempted denominators and downstream statistics before stating any externally meaningful model score.

**Reporting:** Results are separate for script identification (116 public items) and isolated single signs (150 public items). The tool reports the upstream's native *successfully scored sample → per-item mean → rung macro mean* convention **and** a second conservative `intention_to_test_zero_for_failed_macro`, counting failures, timeouts, refusals and abstentions as zero. The first is comparable to the benchmark's public leaderboard scoring convention only for equivalent coverage and prompt protocol; the second makes incomplete model calls transparent. It reports scoring coverage and attempt statuses, never a composite score or claim about sentence transcription/translation.

**Important privacy safeguard:** The original benchmark's publicly scored sign labels are present only in the ephemeral upstream checkout; no gold, per-item results, parsed sign guesses, provider raw answers or source images are copied into the project's Git history or aggregate report.

**CI:** The `frontier-baselines.yml` workflow runs a built-in fake-script/fake-sign parity test against *the real pinned official TypeScript source*, then creates a **synthetic 266-attempt full public-manifest fixture** in `runner.temp`. It replays placeholder text/failures through the real scorer and audits the resulting aggregate for exact count and absence of answer-bearing fields. **This is not new frontier-model inference and awards zero EVAL-003 points.** A real provider call and independently accepted scored archive remain required.


## W6 — Verified current provider identifiers and actual baseline execution readiness (2026-10-08)

**Additional auditable artifacts:** [W6 candidate catalogue](../../eval/baselines/w6_provider_candidates.json) and [deterministic offline readiness audit](../../eval/baselines/w6_readiness.py). **Preflight status: NOT AUTHORIZED; zero provider API calls/actual Hieratic inference.**

### Three *documentary-verified* image-capable model candidates

| Provider | Official current model ID | Official primary model/vision evidence | Draft direct API route | Verification scope |
|---|---|---|---|---|
| OpenAI | `gpt-6-luna` | [model card](https://developers.openai.com/api/docs/models/gpt-6-luna), [image-input guide](https://developers.openai.com/api/docs/guides/images-vision) | `POST https://api.openai.com/v1/responses` | Exact ID+image input documented; user-account access, actual image encoding, context charges and final effort policy NOT tested |
| Anthropic | `claude-sonnet-5-5` | [model card](https://platform.claude.com/docs/en/models/sonnet-5-5/overview), [vision API guide](https://platform.claude.com/docs/en/build-with-claude/vision) | `POST https://api.anthropic.com/v1/messages` | Exact Claude API ID and image content block documented; user-account entitlements/permissions NOT verified |
| Google | `gemini-3.8-flash` | [model card](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash), [Gemini 3.8 official model guide](https://ai.google.dev/gemini-api/docs/latest-model) | `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent` | Stable model ID, image modality, `low/medium/high` thinking documented; actual credential/model access NOT verified |

These are **three candidates for a future owner-authorized comparison**, not default runtime selections or inferred best performers. Dates/specs are point-in-time official website observations; provider models, quota and pricing may change. The Google general model-list page appeared with different crawl snapshot versions; prefer its explicit specific 3.8 Flash model page and live authenticated `models.list` verification before any protocol lock. Claude IDs 4.6+ are version names rather than assumed ever-shifting generic aliases ([official version guidance](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions)); do not claim accessible/account-enabled from public model documentation.

**Reasoning settings are not scientifically equivalent across vendors.** Proposed effort tiers in the candidate catalogue are merely configuration ideas requiring pre-registration, not comparable compute budgets. No empirical performance ranking can be made from published model-family descriptions.

### Frozen public benchmark population and upstream-only official scorer

The independently reviewed R-017 [public-source metadata census](../research/R017_PUBLIC_BENCHMARK_LINEAGE_AUDIT.md) includes **266 unique pinned public item IDs**: **150 AKU isolated-sign items** and **116 script-ID items** (16 Chester Beatty, 37 Met, 61 Wikimedia, 2 Yale). **Two commissioned sealed items excluded.** There is no source-side `gold` or image pixel field in the W6 census. Full 266 × 3 candidate providers × **3 samples** = **2,394 pre-planned attempts**, not 2,394 results or a reasonable cost quote. Original object/support clustering is fewer than 266 (AKU 150 signs may share physical supports), so document-level intervals must not blindly treat each item as independent.

The existing `public_freeze.py` and `official_replay.mjs` already exercise pinned upstream metadata, prompt hashes and **synthetic** original TypeScript scorer parity in hosted CI; these do not mean actual provider images were sent or a new leaderboard has been produced. When genuine inference becomes authorized, preserve **exact official prompt bytes** from pinned upstream; avoid run-time model-dependent prompt improvements, examples, system additions, OCR tools and per-rung denominator selection.

### Offline readiness audit and adversarial tests

Run:

```bash
python -m eval.baselines.w6_readiness
python -m eval.baselines.baselinectl validate-suite
# This MUST fail pending specific execution permission.
python -m eval.baselines.baselinectl preflight
python -m unittest tests.evaluation.test_frontier_baselines -v
```

`w6_readiness` reads only public project-local JSON/metadata, validates official provider documentation domains and proposed exact IDs, pinned 266-source family census, mandatory quarantine, absence of sealed/gold fields, and canonical `suite.yaml` execution-state **planning**. Its output says `execution_authorized: false`, `eligible_scientific_evaluation_items: 0`, `provider_calls_observed: 0`, and no scores. These are **documentary/authorization state**, not a claim that the evaluation-only public benchmark itself could never be legally evaluated. The audit does not access the internet or API credentials, cannot award rights or certificates, and refuses mutated self-authorization flags and image/benchmark contamination.

### Owner authorization, execution and reproducibility gate

Before even one paid image request:
1. Obtain separately approved API credentials, provider account access and current provider terms for copyrighted/public-domain benchmark images and test outputs. The OpenAI/Claude/Gemini consumer-app subscriptions are **not** interchangeable with research API credentials or billing.
2. Lock **exact authenticated model IDs, image input format, reasoning effort and provider API route**, prompt bytes, preservation policy, benchmark item set, per-image licence, samples, budget in **USD**, retry rules and capped estimated image tokens. Image token costs depend on resolution/provider; no total quote inferred from text MTok alone.
3. Validate reproducible private artifact custody and immutable attempted-universe manifest with audited source support group + image hashes; source metadata only in public repository.
4. Authorize an initial deliberately scoped paired dry-run subset and only then enlarge up to 266 when actual spend and image delivery/accuracy controls pass. **Avoid picking a subset based on outcome.** Do not use official benchmark gold for development or tuning, even if public.
5. Run actual provider requests and preserve all attempt failures/refusals/timeouts and raw provider receipts; evaluate using pinned official scorer and separately labeled EVAL-001 metrics; independent observer reviews results and provenance before status changes.

**No provider credentials, image acquisition, new API inference, live images or human permission have been provided.** All W6 catalogue entries are documentary candidates, all execution gates remain blocked, `suite.yaml` is unchanged in `planning`, EVAL-003 still active and earns zero new points. This research only removes uncertainty over current *documented* model ID/routes, not experiment access.


## W7 — Owner-executable first real inference decision (2026-10-09)

**Deliverables:** [explicit unapproved two-stage decision packet](../../eval/baselines/w7_first_run_decision.json), [offline source-linked decision auditor](../../eval/baselines/w7_decision.py), [R-022 first-image expert-gold investigation](../research/R022_LINKED_MET_SOURCE_AND_EXPERT_GOLD_FIRST_PAIR.md). These are **reviewed provider documentation and planning outputs, not a real run, an authenticated approval or a model score**.

### Why the first attempted request should be one user-owned image, not a scientific benchmark

- **P0 — transport integrity:** owner-authorized **one** synthetic, locally authored image (for example a red square/blue circle; no Egyptian artefact, copyrighted work or answer gold), exact model account ID, one actual image-conditioned API request, one returned provider response preserved in a secure vault and original raw-output/usage hash. This proves successful *image transport* only. An unchanged-text image-swap visual-sensitivity check may be separately preregistered, but requires another approved attempt; no inferred Hieratic quality.
- **P1 — frozen *public-evaluation-only* sample:** after separate explicit approval of exact public source identity and image rights, freeze one preselected `HieraticBench@d587dc990013f18007f1e7a8f56f96ff2f7127e2` public item **without consulting gold**, use exact pinned `bench/src/prompts.ts` prompt, preserve every failure/response and original source hash. This is a **transport/integration diagnostic**, not a population benchmark, and cannot tune prompts or choose subsequent examples based on the answer. P1 remains blocked until vault, rights, approved item snapshot and bill cap are verified.
- **P2 — scientific evaluation:** only after P0/P1 technical transport works and an exact whole-public-universe attempt plan is independently preregistered and funded. Retain sealed exclusion, image/edition support groups, intention-to-test failure denominator, original upstream scorer and independent audit. Do **not** extrapolate one P1 result into a scored project capability milestone.

The existing `eval/baselines/suite.yaml` intentionally remains `status: planning` with all authorization flags false, unknown approved dollar cap and null immutable live item/prompt bundle IDs. The new tool must also fail closed against any attempted JSON-generated "owner approval" or fabricated API usage receipts.

### Published provider pricing: rate anchors, *not an image cost estimate*

Public official vendor rate references observed **2026-10-09** (USD per 1,000,000 billed tokens; confirm authenticated exact tier and image/thinking-token billing before execution):

| Provider / documented API model | Uncached input USD/MTok | Output USD/MTok | Rate/limitations |
|---|---:|---:|---|
| OpenAI [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) via Responses | **$0.10** | **$0.50** | [Official Standard short-context pricing](https://developers.openai.com/api/docs/pricing); different Batch/Flex, Fast, cached and long-context tiers. |
| Anthropic [Claude Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/overview) via Messages | **$2.00** | **$10.00** | Standard rate; image tokens counted as input; thinking/cache and account routes can change charges. |
| Google [Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash) via GenerateContent | **$0.75** | **$3.75** | [Official introduction pricing](https://ai.google.dev/gemini-api/docs/pricing) through **2026-12-31**; output may include thinking, and free tiers have different data-use policies; do not presume a free quota or use consumer subscription. |

No defensible **total $ figure** is possible without the actual picture resolution, provider image-token accounting, output/thinking limit, retries, verified current rate, region/mode and user-defined maximum spend. The calculator formula in the decision packet is accounting guidance, *not* a quote. Avoid any API call until the owner supplies separate approval and a concrete capped budget.

### Source-specific preflight contamination

[Met object 561345](https://www.metmuseum.org/art/collection/search/561345) accession `09.184.703` is explicitly associated in [the Met's own 561369 record](https://www.metmuseum.org/art/collection/search/561369) (accession `09.184.728`, title **“Hieratic Ostracon- see 09.184.703”**). The two official images in `data/acquisition/met/objects/561345.json` contain both accession numbers in their filenames. The original physical relationship remains unadjudicated; **group 561345 and 561369 as one provisional source leakage cluster**.

The first independently authored source-line-pair target is switched to **[Met 561392 / 09.184.751](https://www.metmuseum.org/art/collection/search/561392)**, which has documented public-domain image references mentioning just its own accession; the absence of a catalogue link is not proof of independence. This Met acquisition pilot is **not** automatically one of the frozen `HieraticBench` evaluation items. Keep genuine new training/pilot sources separate from evaluation-only public benchmark items. No original pixel bytes, specialist reading or source-independent science claim exists.

### Operator command and stop conditions

```bash
python -m eval.baselines.w7_decision
python -m eval.baselines.w6_readiness
python -m eval.baselines.baselinectl validate-suite
# Must still fail (cannot authorize provider calls):
python -m eval.baselines.baselinectl preflight
python -m unittest tests.evaluation.test_frontier_baselines -v
```

The W7 auditor cross-checks the R-022 linked object group, published model identities/rates and the prior official 266-public-only source snapshot, rejects false paid permissions/score promotion, and can only output `execution_authorized: false`. It **cannot** validate actual third-party letters, legal agreements, institutional identities, real API credentials or actual provider outputs. **No provider calls occurred** and no first scientific Hieratic prediction was scored in W7 overseer work. The entire decision remains `NOT_EXECUTED_NONCERTIFIABLE`.

**Minimum owner inputs needed for a genuine P0 run:** choice of API provider account, availability and right to use its API key, a specific USD budget ceiling, an authenticated permitted image input, a genuinely protected raw-capture store and permission to transmit one user-owned generated image under the relevant API data-use policy. External correspondence/expert fees and Met original image acquisition remain separate authorizations.


## W28: independent private provider-export reconciliation and real-inference admission boundary

**Implementation:** `eval/baselines/w28_provider_custody.py`; no provider SDK, no billed calls, no sealed cases. The independent first-party `run_freeze.audit_original_capture` already checks a frozen request/capture's private byte identity, not provider execution. W28 adds a **different check** that joins (1) originally frozen per-item requests, (2) private raw responses and failure rows, (3) independently *claimed* provider account event export and billing records, and (4) a separate private run manifest by exact request/response ID, timestamps, SHA-256 of raw prompt, original image and model config, provider ID, response text, request max-spend and final aggregate cost. No public corpus images or raw response text are committed.

To audit a valid existing prior *private* run (only with independently approved access):
```bash
python -m eval.baselines.w28_provider_custody audit-private \
  --attempts /external-private/attempts.jsonl \
  --responses /external-private/responses.jsonl \
  --account-export /external-private/provider-export.jsonl \
  --attestation /external-private/custody-manifest.json
```

The four files must exist outside this public checkout and must not be symlinked or exceed byte limits. The runner rejects unknown fields, omitted or duplicated item/rung/sample attempt IDs, broken per-input prompt/image/config hashes, malformed UTC timestamps, backwards request/response timing, contradictory model IDs, forged per-response content hashes, absent/duplicate provider response IDs or claimed account events, stale account-event timestamps, over-budget/surprise spend and non-zero attempts under UNAPPROVED authorization. Failed, refused, timeout and abstained attempts count fully.

**Crucial epistemic limit:** matching two editable local files (even if they carry plausible account event identifiers and SHA-256) is **not independent proof** that OpenAI, Google or Anthropic executed anything. Only an authenticated externally controlled account/provider report, a valid independent evidence custodian, original provider output and authorized official scoring can establish high-trust evidence. The output intentionally says `export_independently_authenticated_by_provider=false`, `model_forward_pass_proven=false`, `official_scorer_replayed=false` and `eval003_milestone_points=0` even when the synthetic fixtures reconcile. Local metadata `authorization_state=APPROVED_EXTERNALLY` is a *claim* and must not give budget permission by itself; real credentials and budget authorization are separately required.

The secondary `paired-coverage` compares only identical keys and produces success/failure population counts; it never creates accuracy, BLEU, sign top-1, ranking or semantic evidence without the independently pinned official scorer and known real item gold.

**Current W28 outcome:** no new commercial provider inference authorized/executed, no independently authenticated provider event export supplied, and no original third-party raw response archive supplied to this task. EVAL-003 remains **0/1.5** and canonical weighted progress **34.5/100** pending genuine approval, independent original-provider calls and admissible official source scoring. No published price quote/model token cost should be treated current without fresh independent provider verification; do not assume $0 website subscriptions entitle licensed API inference.
