# W28 — genuinely new original-publisher AES BBAW letters transfer experiment

**Independent hosted source execution:** [GitHub Actions run 38085816438](https://github.com/m7mdehab/hieratic-ai/actions/runs/38085816438), **SUCCESS**, exact evaluated repository commit `58837395abbafe862fdcf971f686c69461fcb6dd`, with main workflow `.github/workflows/w28-original-aes-letters.yml` and exact source-locked code `ling/translation/w28_letters_first_use.py`. All initial W28 feature tests and governance passed before original target fetch.

## True prospective chronology

1. Independent publisher Git **TREE metadata only** was examined to select previously unused BBAW letters source file, `files/aes/_aes_bbawbriefe.json`, byte size 19,946,763, immutable Git blob SHA-1 `2c8db01616a37c75a3566e3b64d94a75fdf194c2` at upstream AES revision `35276d2527cca1a055e31ed5f6683e777717170f`. No contents or German references read before freeze.
2. Prospectively frozen `ling/translation/experiments/W28_PREREG_LETTERS_MEANING_TRANSFER.md` **initial Git commit `46c2efb818aaac0834ad6c853bbc4c18ff6c8fd1`**, preserved in repository by true non-squash merge PR #161 `793b3746ea3bb36090b5c7810db26280e03f5b50`. Selection: lowest salted SHA256 of original **32 source text IDs**, not labels; no look at target publisher German references. Fixed train only: accepted 904 W9 developer sentences + 3,021 W11 archive donor (3,925 sentences total), per-source-group disjoint. Prior W9 Tübingen, W10 external archive, W11 biographies, W12B Amarna and W16 TLA remain exposed and never recycled as virgin external targets.
3. The first hosted workflow run [38085651938](https://github.com/m7mdehab/hieratic-ai/actions/runs/38085651938) stopped **BEFORE original source access** because a `workflow_dispatch`-only SHA variable was empty during a push event; PR #165 corrected CI environment and reran after hosted exact-head governance. No target German answer was accessed in the failed attempt.
4. Actual heldout run [38085816438](https://github.com/m7mdehab/hieratic-ai/actions/runs/38085816438) then genuinely fetched exact original AES publisher bytes, verified both original Git blob SHA-1 and raw SHA256, partitioned private source-token-only input vs separate German target references, executed **different predictor process** with no reference file input, SHA-anchored frozen private predictions, and opened references only afterward in scorer stage. Private original and predictions destroyed at job end; aggregate SHA/metrics only were printed, no source/labels deposited as public artifacts.

## Original byte and archive receipts

| Original receipt | Value |
|---|---|
| Source repository | https://github.com/simondschweitzer/aes |
| Immutable original publisher revision | `35276d2527cca1a055e31ed5f6683e777717170f` |
| File | `files/aes/_aes_bbawbriefe.json` |
| Exact source Git blob SHA-1 | `2c8db01616a37c75a3566e3b64d94a75fdf194c2` |
| Actual original file SHA-256 | `97929b4fb89f8336bbd5c87f98b1ae781e406d1b27b38475d0375760d91a75b0` |
| Private source-only predictor input SHA-256 | `e188aad7c2802e81e107beb50428d1eb055f5e609b032b964f63df7bcc2e41fc` |
| Private reference-only archival SHA-256 | `4a2aa0d9b79914fd53dc799807280ffed547bd85a6d19fc86294e33c267e53e0` |
| Predictions frozen before reference scoring SHA-256 | `26d1a61b57a4e9675d0f71cd7a3df4c9b62501935c7e91747d57a2d732013041` |
| License | Publisher CC BY-SA 4.0, Egyptian scholarly transcription/editorial German text only; original photography NOT implied |

## Complete genuine heldout original publisher diagnostic (no omitted cases)

| Criterion | Genuine observed |
|---|---:|
| Frozen distinct original publisher text IDs | **32** |
| Frozen total source sentences | **285** |
| Published nonempty German references | **284** |
| Missing reference | **1** (remains in complete denominator) |
| Original Egyptian token count | **3,835** |
| W28 unknown/abstained source tokens | **1,660** |
| New W28 supported 3-token phrase reversals | **0** |
| German published reference tokens | **5,109** |
| All methods emitted German tokens | **5,683** |
| Gloss-only overlap | **355** |
| W10 baseline overlap | **357** |
| W28 grammar extension overlap | **357** |

Scores were **German word-multiset full-denominator micro-F1**, *not* fluent or semantically adjudicated translation:

- **Frozen gloss-only:** `0.06578947`
- **W10 existing constrained composition:** `0.06616012`
- **W28 new three-token source-voting composer:** `0.06616012`
- **W28 vs W10 effect:** **0.00000000**; 2,000 document-text-ID clustered bootstrap resamples 95% empirical difference interval **[0.0, 0.0]**. Structural rule abstained from reordering any triple, so model output equaled W10 source-constrained fallback.

**Negative scientific result:** the proposed train-voted three-token grammar change did **not** improve authentic heldout source-editorial German word-match performance. The 32 original text IDs do **not** prove independent manuscript physical supports; AES original reference translations share AED/TLA editorial genealogy; current outputs are not independently adjudicated fluent semantics. No Hieratic photo input or certified source-to-line correspondence, no model weights fine-tuned, no new approved corpus v1. This source and its editorial German references are now **EXPOSED**: future changes cannot be tuned on it and called unseen.

## Independent scoring and scope review

- Actual source fetch from immutable publisher **genuine**: YES, sha verified.
- Separate source-only predictor process before opening private target reference file: YES, hosted.
- Correct 32-group/285-sentence planned denominator: YES, no missing output.
- Local/repository-hosted unit fixture tests: YES (source right/target gold injection, malformed groups, no false image claim, train/source-voted unit rules).
- External Egyptologist qualified independent semantic quality reading: **NO**.
- Original papyrus image, physical-scribe grouping, benchmark independence: **NO**.
- No leaked private publisher original data: YES; only aggregate results/digests.
- Capability milestone LING-003: **0/2**, task **ACTIVE**.
- Canonical weighted goal: **34.5/100 unchanged**; research coverage **18/100 unchanged**, new subset of already explored AES transfer family, no added distinct research axis.

## Immediate next technical decision

Do **not** just increase retriever memory size or retune on exposed letters. The cohort contains **1,660/3,835** unrecognized source tokens, and the new grammar rule found **zero independently source-voted triples**; a next *prospectively frozen different* corpus should prioritize source-form/semantic bilingual coverage and genuine predicate/negation/role supervision. To reach the originally weighted LING-003 gate, independently verify complete semantic/predicate accuracy with a qualified blinded expert and an appropriately licensed source-level text/translation pair, and ultimately integrate with a real independently gold Hieratic manuscript input without benchmark contamination. No user payment/API permission was needed or used in this W28 experiment.
