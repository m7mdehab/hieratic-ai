# HieraticBench Reproduction and External-Evaluation Boundary

**Project task:** EVAL-002  
**Upstream benchmark:** [alymoursy/hieraticbench](https://github.com/alymoursy/hieraticbench)  
**Pinned upstream commit:** `d587dc990013f18007f1e7a8f56f96ff2f7127e2`  
**Upstream harness:** `0.1.0`  
**Published leaderboard snapshot:** `2026-10-05T21:11:18.620Z`  
**Review date:** 2026-10-08  
**Evidence level:** original source code, original repository README/Method page, published scoreboard, item schema; no third-party secondary report substituted for source evidence.

## 1. What was and was not reproduced

EVAL-002 intentionally separates four different meanings of "reproduction":

| Layer | What is available | Reproduction status |
|---|---|---|
| Item inventory | Metadata JSON files in public upstream repository | Source-verified; local metadata-only audit tool provided |
| Official scoring algorithm | `bench/src/score.ts`, `bench/src/prompts.ts`, upstream unit tests | Source-verified; runnable via upstream `npm test`; **not reimplemented as a different official scorer** |
| Public results aggregation | Public `results/runs/*.jsonl` and `results/leaderboard.json` | Read-only independent reconstruction of numeric per-item/per-rung means and coverage |
| Provider-model inference | Proprietary/third-party remote model calls | **Not rerun** by EVAL-002; published scores are historical upstream results |
| Sealed sentence reading | No publicly stored answer key | **Not reproducible as an automatically scored reading task**; no score invented |

Our adapter `eval/benchmarks/hieraticbench/adapter.py` checks the upstream Git SHA, item counts, benchmark/public-run privacy invariant, and full published per-item/rung aggregates. It reads upstream files **in place** but emits only counts. It does not open images or private inboxes, does not call models, and does not write any upstream data into this repository.

This reproduces the public *aggregation mechanics* and supplies a defensible path to running upstream scoring tests. It does not represent an independent rerun of all model outputs or an expert adjudication of the secret sentences.

## 2. Pinned dataset structure

The published upstream inventory contains **268 item records**:

| Source prefix | Number of items | Meaning |
|---|---:|---|
| `aku` | 150 | AKU-PAL single-sign items |
| `cbl` | 16 | Chester Beatty collection documents |
| `hb` | 2 | Commissioned sealed sentence images |
| `met` | 37 | Metropolitan Museum of Art |
| `wm` | 61 | Wikimedia Commons |
| `ypm` | 2 | Yale Peabody Museum |
| **Total** | **268** | |

There are **266 public** and **2 sealed** items. The two sealed items (`hb-0001`, `hb-0002`) show the *same sentence* in two different hands, not two independent linguistic sentences.

The upstream leaderboard reports task/rung eligibility as:

| Rung | Eligible items | Publicly scored content |
|---|---:|---|
| Identify | 118 | 116 public document/control images + 2 sealed identification scores |
| Signs | 152 | 150 public single-sign items; sealed-sentence signs have no public gold |
| Transliterate | 2 | Sealed sentences only; no public answer key |
| Translate | 2 | Sealed sentences only; no public answer key |

These counts are **task eligibility**, not numbers of scored model outputs; models were not run across every eligible rung.

Gold script-label distribution (includes the 150 single-sign items):

- Hieratic: 238;
- hieroglyphic: 5;
- Demotic: 17;
- abnormal Hieratic: 1;
- cursive hieroglyphic: 7.

The 116 public identify items contain real documents and neighboring-script controls. The controls make script identification harder to game by always answering "Hieratic."

**Caution:** The label distribution above covers the full inventory. It must not be described as the class composition of the 118-item identify subset without computing that subset separately.

Primary evidence: upstream `data/SCHEMA.md`, `data/items/*.json`, `results/leaderboard.json`, `bench/src/leaderboard.ts`, and Method page, all at the pinned commit.

## 3. Prompting protocol

The original benchmark uses four independent rungs:

1. **Identify**, asked cold: "Can you identify and translate this script?" Requires a final `SCRIPT:` line.
2. **Signs**: explicitly says the image is Egyptian Hieratic; single signs request one Gardiner code, while sentence images request a Gardiner-code sequence. Requires `SIGNS:`.
3. **Transliterate**: explicitly says the image is Hieratic; requests standard Egyptological transliteration. Requires `TRANSLITERATION:`.
4. **Translate**: explicitly says the image is Hieratic; requests an English translation. Requires `TRANSLATION:`.

One image + one user message is used for each request; the Method page says no system prompts, no examples, and no tools. Provider defaults are used except the specified reasoning-effort level; model routing can be direct-provider or OpenRouter.

The official extractor finds the **last nonempty labeled answer line**; absent or malformed required lines generally receive zero. The signs and transliteration rungs being told the script prevents a cold script-ID failure from automatically failing later tasks.

**Methodological limitation:** Rungs are separate queries rather than a single continuously reasoned image→reading→translation chain. A hypothetical strong translate response cannot by itself establish a correct sign sequence.

## 4. Exact official scoring semantics

Official scoring is defined in upstream `bench/src/score.ts` and `bench/src/prompts.ts`, not by our proposed EVAL-001 normalization.

### Identify

- Score **1** when the classified script matches the gold script or belongs to the explicitly mapped equivalent pair (abnormal-Hieratic ↔ Hieratic; cursive-hieroglyphic ↔ hieroglyphic).
- Score **0.5** for another script within upstream's defined Egyptian-script group.
- Score **0** for others, UNKNOWN, or no valid `SCRIPT:` line.
- Upstream's Egyptian partial-credit set includes Hieratic, abnormal Hieratic, hieroglyphic, cursive hieroglyphic, Demotic, and generic "Egyptian"; Coptic is parsed but **not** included in that set.

The extractor and classifier are heuristic textual parsers. They should be evaluated as written, not retroactively "fixed" to improve particular model answers.

### Public single signs

- Parse Gardiner codes from `SIGNS:` text, canonicalizing capitalization/leading zeros.
- Score **1** only if the **first parsed predicted code** appears in the source's accepted Gardiner-code list.
- A correct second/third proposed code does **not** rescue an incorrect first code.

### Multi-sign sequences

Given a predicted Gardiner-code sequence and one or more reference sequences, upstream takes the maximum:

`max(0, 1 - edit_distance(prediction, reference) / number_of_reference_signs)`.

That is a **bounded accuracy-like score**, not the project GER itself. It is currently not publicly computable for the two sealed sentences, because the references are not published.

### Transliteration

Upstream canonicalizes transliteration toward a consonantal skeleton, including certain orthographic/conventional symbol merges and ignoring spaces/morpheme separators. It then uses bounded `1 - character_edit_distance/reference_length`, taking the best permitted reference.

**Important:** EVAL-001's own `TR_CER` may preserve distinctions that the official HieraticBench canonicalizer collapses. We cannot present them as numerically interchangeable.

### Translation

Upstream's present function computes **chrF**, using character n-grams through order 6, β=2, lowercasing and ignoring whitespace, taking the best available reference.

That algorithm is present as infrastructure for future gold-backed material. **No published machine-scored translation result exists for the two secret sentences.**

### Aggregation

The official leaderboard performs:

1. mean across repeated samples for the same model/item/rung;
2. mean of those item means within a rung;
3. coverage = scored distinct items / all eligible items for that rung;
4. model + reasoning-effort combination = separate leaderboard row.

`overall` is computed only if **all four rungs have scored results**. In the pinned leaderboard every entry has `overall: null`.

The adapter independently implements **only this numeric aggregation**. It compares every computed item-level mean and rung mean/count/coverage against the published leaderboard. The official TypeScript code remains authoritative for scoring a raw model answer.

## 5. Published upstream baselines (not newly run by this project)

Published leaderboard snapshot: **5 October 2026**. Values below are the **official aggregate rung scores** in `results/leaderboard.json`, not new measurements.

| Model/effort | Identify (all 118 eligible, when covered) | Public single signs |
|---|---:|---:|
| Claude Fable 5.1 (high) | 93.64% / 118 items | 8.67% / 150 |
| Claude Opus 5.5 (high) | 91.10% / 118 | 13.33% / 150 |
| Claude Sonnet 5.5 (high) | 88.98% / 118 | 10.67% / 150 |
| Claude Haiku 4.5 | 41.95% / 118 | 0.67% / 150 |
| GPT-6.1 Sol (high) | 73.31% / 118 | Not run |
| Kimi K3 (high) | 79.24% / 118 | Not run |
| Qwen3.8 Max (high) | 75.71% / **70** items | Not run |
| Gemini 3.8 Flash (high) | **0% / 2 sealed items only** | Not run |

**Do not treat these percentages as equivalent accuracy on real Hieratic documents.** They are partial-credit averages including Egyptian-script controls and sealed identification where included. The README's rounded "95% on real documents" figures refer to a different subset/description and are not the same as the full 118-item identify rung. The 2-item-only Gemini/GPT-6 Astra entries are **not comparable** to full-coverage identify rows.

The 150 publicly scored signs are a narrow **isolated-sign** reading task, not end-to-end HTR. The best published score in these reported runs is 13.33% for the Opus sign set; this establishes the motivating gap without claiming no prior Hieratic OCR/ML research exists.

All 13 model rows at this snapshot lack scored public transliteration/translation rungs. Some runs were intentionally partial due cost. Source: pinned `results/leaderboard.json` and README.

## 6. Sealed material: exact boundary

The commissioned material is **one sentence in two hands**, not a statistically large held-out corpus.

The benchmark creator states that the answer has not been published and is not stored in the repository. The upstream loader contains a *potential* optional `data/private/answers.json` interface, but the public project does not provide such a file or a verified reference transcript.

The official harness:

- scores **script identification** on the sealed images with public label "Hieratic";
- writes the **full response text** for sealed identify prompts to a local ignored private inbox, because the prompt also invites translation;
- publishes only the redacted/withheld identify record and numeric score;
- routes sealed signs/transliteration/translation responses to ignored private storage;
- leaves their score `null` without a key.

The presence of a local `score` command/API does **not** establish that a secret gold reading is available for us. No synthetic/hypothesized answer is acceptable.

The project must never upload or vendor:
- full sealed responses;
- answer-bearing speculative transliterations;
- gold sign sequences;
- commissioned image derivatives for training.

## 7. Data rights and contamination protection

The official upstream license distinguishes:

- code in `bench/` and `site/`: MIT;
- public result files: CC BY 4.0;
- public images: per-item licenses in `data/items/`;
- commissioned images: © Aly Moursy, evaluation permission only.

Our stricter FND-005 policy treats **all exact HieraticBench material as evaluation-only**, independent of otherwise permissible individual public-image licenses.

It is therefore forbidden to place benchmark image/crop/near-duplicates, public sign gold, sealed responses, or model outputs into training/dev.

A future acquisition from AKU-PAL, museum databases, or Wikimedia must check:
- stable source/item and museum object IDs;
- SHA-256 and derived-file hashes;
- perceptual similarity/near-duplicates;
- document/page lineage;
- source-specific rights.

This is particularly important because **150 benchmark sign examples come from AKU-PAL**. Training on the same benchmark images, even when individually licensed, would invalidate independent evaluation claims.

## 8. Mapping HieraticBench to Hieratic AI EVAL-001

| Official rung | EVAL-001 analogous metrics | Compatibility warning |
|---|---|---|
| Identify | SCRIPT_ACC; SCRIPT_MACRO_F1 | Official 0/0.5/1 partial credit is not plain accuracy/F1 |
| Public single signs | SIGN_TOP1 | Gold-code equivalence/canonicalization must match |
| Sentence signs | HTR_GER / HGR_SER | Official bounded 1−SER score; sealed reference unavailable |
| Transliteration | TR_CER | Upstream consonantal skeleton folds distinctions; not equivalent to our transliteration profile |
| Translation | TRANS_CHRF plus human adequacy/faithfulness | Upstream chrF alone does not establish source-faithful reading |

Official scores must be reported **unchanged**. If derived project metrics are calculated later, they receive a distinct name, scorer version, data-eligibility note, and denominator.

HieraticBench is one external benchmark, not the final system's only success criterion.

## 9. Exact reproduction procedure

A fresh upstream checkout should be pinned to the SHA above. Run the original benchmark's unit suite to verify parsing/scoring, then run our independent adapter from the Hieratic AI repository.

```bash
git clone https://github.com/alymoursy/hieraticbench.git /tmp/hieraticbench-eval
git -C /tmp/hieraticbench-eval checkout --detach d587dc990013f18007f1e7a8f56f96ff2f7127e2

# From Hieratic AI root
python -m pip install -r requirements-projectctl.txt
python -m unittest discover -s tests/evaluation -v
python -m eval.benchmarks.hieraticbench.adapter inventory --checkout /tmp/hieraticbench-eval
python -m eval.benchmarks.hieraticbench.adapter verify-leaderboard --checkout /tmp/hieraticbench-eval

# From external checkout, Node >=22
cd /tmp/hieraticbench-eval
npm ci
npm test
```

No API credentials are needed for these metadata, aggregate, and official scorer unit tests.

The upstream harness additionally offers `npm run bench -- validate` and full model execution with provider API keys. This task intentionally does not call models or rewrite stored results.

## 10. Reproduction audit criteria

A passing pinned audit establishes:

- actual upstream checkout revision is the expected SHA;
- all 268 source item records and inventory breakdowns match the manifest;
- public run records do not expose a private-copy payload or full sealed response;
- all present non-null numeric run scores are bounded [0,1] and refer to valid items/rungs;
- numeric per-item sample aggregation matches published `perItem` exactly within declared floating-point tolerance;
- model/effort/rung score, item count, sample count and coverage agree with the published leaderboard.

It **does not establish** that a model read the underlying manuscripts correctly, and does not independently re-score text against Gardiner labels. Such scoring remains the responsibility of the upstream harness and its documented tests.

## 11. Limitations, discrepancies and open questions

1. **No sealed reading gold:** The secret sentence cannot be scored automatically by an independent researcher without the author's private adjudication or an authorized later release; do not imply that a score exists.
2. **One sentence, two hands:** Not sufficient for a generalization claim.
3. **Many famous documents:** Familiar source images can have been present in pretrained corpora.
4. **Only 150 public sign-level supervised tests:** Does not measure full line HTR, transliteration or translation.
5. **Rung gap:** Script ID is assessed across public documents; signs on isolated AKU-PAL items; sentence decoding is sealed. These are not an aligned end-to-end public corpus.
6. **Published runs are incomplete:** Some model rows have only 2 sealed identify items, others partial document coverage; do not rank them as if matched.
7. **Public numeric score vs original response:** The adapter reconstructs published aggregates from existing `score` fields; it does not duplicate upstream raw-response scoring or pay for provider reruns.
8. **Scorer parsing heuristics:** Gardiner-code and script-name parsing can fail on some model formats; the official benchmark's definitions are left unchanged.
9. **Snapshot may change:** This report is pinned. Future upstream updates require a new manifest/review, not a silent moving-target baseline.
10. **Potential privacy boundary:** The benchmark's public run files may contain response text for *public* documents. The adapter deliberately reads only the numeric/identity fields necessary to audit aggregation and does not export response text.
11. **No claim of first-ever Hieratic AI:** Earlier computational work is documented in `docs/research/PRIOR_ART_AND_DATA_REGISTRY.md`.

## 12. Acceptance evidence and scientific conclusion

The source-code inspection and pinned metadata demonstrate that HieraticBench can be meaningfully integrated as an **external, independently reported challenge**, but not as a sufficient single-number measure of the Hieratic AI mission.

EVAL-002 provides a version-pinned manifest, a read-only aggregation/metadata verifier, synthetic tests, an official TypeScript scoring-test route, and a precise boundary between actual reproducibility and unscorable secrets.

No benchmark images, gold codes, response text or sealed answers are committed by this task.

## Primary references

All upstream links below point to the **pinned commit** rather than the moving main branch:

- [README](https://github.com/alymoursy/hieraticbench/blob/d587dc990013f18007f1e7a8f56f96ff2f7127e2/README.md)
- [Dataset schema](https://github.com/alymoursy/hieraticbench/blob/d587dc990013f18007f1e7a8f56f96ff2f7127e2/data/SCHEMA.md)
- [Official scoring logic](https://github.com/alymoursy/hieraticbench/blob/d587dc990013f18007f1e7a8f56f96ff2f7127e2/bench/src/score.ts)
- [Prompts and answer parsing](https://github.com/alymoursy/hieraticbench/blob/d587dc990013f18007f1e7a8f56f96ff2f7127e2/bench/src/prompts.ts)
- [Leaderboard aggregation](https://github.com/alymoursy/hieraticbench/blob/d587dc990013f18007f1e7a8f56f96ff2f7127e2/bench/src/leaderboard.ts)
- [Run secrecy/storage](https://github.com/alymoursy/hieraticbench/blob/d587dc990013f18007f1e7a8f56f96ff2f7127e2/bench/src/cli.ts)
- [Official scoring unit tests](https://github.com/alymoursy/hieraticbench/blob/d587dc990013f18007f1e7a8f56f96ff2f7127e2/bench/test/score.test.ts)
- [Published leaderboard](https://github.com/alymoursy/hieraticbench/blob/d587dc990013f18007f1e7a8f56f96ff2f7127e2/results/leaderboard.json)
- [Methodology page source](https://github.com/alymoursy/hieraticbench/blob/d587dc990013f18007f1e7a8f56f96ff2f7127e2/site/src/app/method/page.tsx)
- [License](https://github.com/alymoursy/hieraticbench/blob/d587dc990013f18007f1e7a8f56f96ff2f7127e2/LICENSE)
