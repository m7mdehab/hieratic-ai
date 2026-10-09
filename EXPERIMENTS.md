# Experiment Registry

No validated model experiments have been run yet.

## Rules

Every experiment receives a stable ID, e.g. `EXP-HTR-001`.

Minimum record:
- hypothesis;
- linked task;
- Git commit;
- dataset/manifests and split version;
- model/checkpoint;
- configuration and seed(s);
- execution environment;
- command/entry point;
- metrics;
- artifacts;
- result;
- interpretation;
- decision caused by the result;
- known caveats.

A failed experiment remains in the registry. Negative results may increase research coverage but do not automatically earn capability points.

## Template

```yaml
id: EXP-...
task_id: ...
status: planned
hypothesis: ...
code_commit: ...
data_version: ...
split_version: ...
model: ...
config: ...
seeds: []
metrics: {}
artifacts: []
result: ...
decision: ...
caveats: []
```


## EXP-LING-002-AED-AES-001 — Genuine published-text lexical/morphology diagnostic

- **Task:** LING-002 (accepted source-grounded linguistic interpretation; not an image OCR or model-experiment certification)
- **Classification:** completed_development_grade_scholarly_text_diagnostic; **not independently validated real model experiment**
- **Execution:** PR #88 exact-head GitHub Linux CI 37856429995; verified source registry PR #85
- **Hypothesis:** exact original Egyptian written-form lookup into scholarly AED dictionary and independent-other-text AES editorial annotations can recover useful lemma identities, grammatical alternatives and attested inflection bundles, without fabricating unseen-text gold.
- **Inputs:** AED-TEI 35,052 publisher lexemes, Git dictionary.xml original blob 078f2f7b83bd642b6530ed000dbc68f9aa79c06e; AES Felsinschriften 445 sentences, 311 text groups and 2,526 original editor tokens, source Git blob 7bfcba9678b64c3526a1123996a0714b5f76812f. See immutable source manifests and CC BY-SA 4.0 contributor attribution at ling/lexical/data/scholarly_source_manifest.json.
- **Splitter:** exhaustive leave-one-AES-source-text-ID-out. Every queried text ID excluded from AES candidate generation. Common AED published dictionary remains visible. Two text IDs had no scoreable lemma.
- **Prediction method:** deterministic exact form candidate union over AED's dictionary orthography and other-text AES form attestations; no trained weights, statistical model or hidden parameter tuning, seed not applicable. Source-native morphology is only transferred when another text attests the same form and lemma; alternatives preserved.
- **Measured real diagnostic:** of 2,305 tokens with published lemma labels, 1,709 (74.14%) have any lookup candidate and 1,621 (70.33%) have the editorial lemma among candidates. Exactly 1,102 produce a single candidate, with 1,062 matching the published lemma (96.37% among the single-candidate subset only). Of 753 tokens with publisher morphology bundles, 449 (59.63%) match some permitted cross-text candidate bundle. These are *candidate recall* and conditional source-lookup accuracy, not blind OCR accuracy.
- **Immutable report SHA-256:** 26ad977c29fdd8659157cb02bec04323b6b544dc8ca9425a13825ea629acedee. Script: python -m tools.lexical_interpretation scholarly-aes evaluate.
- **CI:** complete governance, data, linguistic and evaluation suites passed, LING-002 15-path scope check passed on exact source head.
- **Decision:** Accept LING-002 2.0-point *linguistic analysis capability only*; unblock the downstream LING-003 translation-engine task. Mark no genuine image-reading, no held-out independent manuscript or VLM result, no trained model, no independently validated model experiments. Input editor labels are genuine published scholarship, not newly blind reviewer-certified gold, and AED/AES publication overlap and unknown pretraining exposure remain substantive limitations.


## EXP-LING-003-W9-EXTERNAL — Publisher source-memory test, negative
- **Task:** LING-003 (active 0/2); **classification:** REAL_PUBLISHER_TEXT_NONCERTIFIABLE_DIAGNOSTIC.
- **Inputs:** Pinned CC BY-SA 4.0 AES published text: 1,156 source sentences, 1,151 German references, 418 AES source text IDs. 904 internal translated training/development sentences; source-ID-heldout Tübingen (247 references/21 text IDs) was used only once for external testing and is NOW EXPOSED.
- **Method:** 5 text-ID-grouped dev folds with train-only lexical German glosses and TF-IDF German sentence retrieval, original frozen threshold 0.0. No original Hieratic image reading.
- **Result:** Internal micro German word F1 gloss 0.15368591 versus sentence memory 0.24261684, but on harder reserved Tübingen publisher text **fell** from 0.15275625 gloss to 0.14259102 contextual memory. 40 copied German sentences came from NONIDENTICAL original Egyptian token sequences.
- **Artifact:** `ling/translation/experiments/W9_CONTEXTUAL_TRANSLATION_EXTERNAL_TEST.md`; deterministic report SHA-256 `3e8b42915d0a5cfce9a1a8cde78d503b319c18cbd3ed3ec28cafa745167402aa`. **Decision:** No fluent translation claim; Tübingen never used again as unseen benchmark; no capability credit.

## EXP-LING-003-W10-ARCHIVE — Preregistered new archive publisher cohort, negative
- **Task:** LING-003, PR #102 (merged `2004abf6175a33f40a1d76822f9baaaab73114cf`); **classification:** new AES editorial-text-domain external diagnostic, NOT original manuscript or independent blind semantic test.
- **Source lock/chronology:** Source/method preregistration commit `7bd1d01c1d9d6242625a1dcd3363e6aaac15ffba` PRECEDED viewing new archive references. AES original archive Git blob `014cccf04235d9e093fca24ed48c62630d235852` and frozen hash selection of 32 NEW complete text-ID groups, 47 original German publisher reference sentences, derived blob `d3d7b57aef7bd10a48df6b1be340be8ff5b36e32`.
- **Methods/results:** Identical 904 earlier W9 train reference sentences; plain gloss word F1 0.02312139, W9 German sentence memory 0.02136752, W10 train-only context-gloss local-composer 0.02285714; **107/162 Egyptian source tokens lack supported word glosses, 0 independently supported word-order inversions**, 5 retrieved publisher sentences copied from nonidentical Egyptian token sequences in W9 memory. Source IDs are not independently verified physical witnesses.
- **Artifact:** `ling/translation/experiments/W10_COMPOSITIONAL_ARCHIVE_EXTERNAL_REPORT.md`, report SHA-256 `da1d4275c9f78e4ad229ab1681de58a3374497df6a150e78cffc03c8f3c1b04c`. No tune-after-test, no reward; archive now EXPOSED.

## EXP-LING-003-W11-BIOGRAPHIES — Preregistered training expansion, qualified lexical gain
- **Task:** LING-003, PR #105, merged `96a9779dca04e5594a1e6413c28fccdac4a88999`; **classification:** first-use AES source-blocked original scholarly text, not expert adjudication.
- **Predeclared source and split:** Git preregistration `c3f88e9274ce1f088619f45aef5ea74be21dcedb` before opening new historical biography reference translations. Additional archive train-only published CC BY-SA 4.0 3,021 usable sentences/1,130 distinct original text IDs, permanently excluding all 32 W10 archive heldout source IDs and previously exposed Tübingen. Total train=3,925. New biographies original publisher blob `6f26021ee4243e87657ff8afd59847f126d6ca65`, hashed top 32 complete original biography source IDs among ALL 141 source IDs, producing 180 source sentences, **178 with German publisher references across 31 scoreable text groups**. Zero source-text-ID overlap; physical witness genealogy independent status unresolved.
- **Methods:** Frozen original 904 gloss/composer, expanded 3,925 gloss/composer with exactly the W10 context and swap parameters unchanged; expanded W9 nearest-neighbor memory threshold 0.0 only as risky copying comparator. No test references in training.
- **Full first-use results (micro German word F1):** 904 gloss **0.09434764**, 904 composer **0.09667330**, expanded gloss **0.10736754**, expanded composer **0.10791969**, expanded whole-sentence memory **0.11088737**. German word-overlap is not percentage of semantically correct Egyptian translation.
- **Other denominators:** 2,264 Egyptian source tokens: unknown cotext gloss abstentions **949 → 846** (103 recovered), expanded contextual unit selections 355, local word-order inversions **0**. Expanded memory copied **50** whole German sentences from nonidentical Egyptian source sequences.
- **Evidence:** Exact-head Project Governance `37918269880` passed; postmerge main governance `37918395022` passed. Report `ling/translation/experiments/W11_EXPANDED_TRAIN_BIOGRAPHY_EXTERNAL_REPORT.md`; diagnostic SHA-256 `c5b3d40e87bae24cf9574e5a6ee48e89acc0348b8e9346cdacc28b2fbf6aa48c`. Test source exact group selection independently audits all 141 original text IDs.
- **Decision:** Accept honest **lexical coverage** expansion, NOT learned grammar, independently reviewed semantics, manuscript OCR or gold. The W11 biographies are now EXPOSED. LING-003 remains active 0/2 and overall verified score 34.5/100. No neural model was trained.

## EXP-VLM-001-W10-CPU-CONTROLS — Agent-reported authentic Hieratic control diagnostics
- **Task:** VLM-001, PR #104 merged `dbc65cadee4466d45910669e2d1cd8454254b188`; **classification:** versioned fail-closed experiment software plus reported private-host execution, NOT a jointly independently rerun scientific result.
- **Input/weights:** Original Cat.2044/013 CC0 p01 JPEG SHA-256 `569e8e5bb446588481481bfea823fc95383bb7076270363c666f868b7fa5b912`; pinned SmolVLM-256M-Instruct revision `7e3e67edbbed1bf9888184d9df282b700a323964`, exact safetensors SHA-256 `74dea5904032e5ae99a2e0eef5179e6ac0f1dedc3ab0c7c2a5d4d387c843203e`. Agent reports **23 local AMD Ryzen CPU forward passes** over full authentic source, three unlabelled candidate crops and blank, inverse and scrambled-tile controls. Real private image/weights/receipt not committed.
- **Negative results:** Blank and scrambled controls produced descriptions of script despite absent/disrupted source structure, prompt-prior hallucination; Grade E visual sensitivity **NOT_VERIFIED**, Grade F authentic scholarly manuscript gold **STRICTLY_NO**, 0/2 VLM capability points. Scrambled tiles preserve within-tile stroke texture, cannot serve as proven complete sign-destruction gold; old W9 unqualified A-E claim is superseded by PR #100 reviewer corrections.
- **Hosted tests:** VLM Baselines Preflight `37919061764`, Project Governance `37919061772`, Error Analysis Integrity `37919061835` all passed exact-reviewed head. **No independently certified Hieratic transcription, translation, or benchmark accuracy.**


## EXP-LING-003-W12B-AMARNA-POS — Preregistered original Egyptian publisher grammar-tag evidence

- **Task and PR:** LING-003 #107 merged `e321b82031b4e2eec7ec493162f9c2aaffdad5e1`. Research engineering accepted, **no weighted points**.
- **W12 FAIL-CLOSED:** Original AES `bbawtempelbib` corpus was preregistered before inspection, but contains only **11** original source IDs versus the specified 24. This experiment is **BLOCKED**, not rescued by lowering its threshold or moving source labels into training. Evidence: `ling/translation/experiments/W12_TEMPLE_COHORT_BLOCKED.md`.
- **Independent W12B registration:** `ling/translation/experiments/W12B_PREREG_AMARNA_GRAMMAR.md` at Git commit `d9e7bcb6b51742f527ae60830143b31cc67d6cde`, recorded before viewing the separate original AES `bbawamarna` source records and annotations. Publisher CC BY-SA 4.0, pinned original Git blob `5e512681dc0d1ac7177a62531582b3473a0a11f2` (14,683,204 bytes). Full original source 399 source IDs / 2,634 sentences; fixed SHA-256 rank selected first **24 complete unique source-text groups**, comprising **163 sentences, 1,691 Egyptian token written forms, 1,649 original published POS tags**. No source ID shared with any W9–W11 pool or exposed W12 temple.
- **Training and methods:** Source-validated original publisher POS/morph features from **3,925** W9+W11 eligible train sentences / **1,526 original source-text groups**. Baseline majority `pos` by exact Egyptian written form, one vote per independent training text ID; contextual model chooses only an already-observed POS with `>=2` independent matching immediate-neighbor training texts, then exact-form fallback. Noninvented morphological candidates `genus`, `numerus`, `status`, `inflection`, `voice`, `verbalClass`; contextual bigrams are descriptive, **NOT grammar dependencies or semantic roles**. Target original editor labels are held in a separate file only read after predictions.
- **Complete-denominator first-use POS accuracy:** **form baseline 773/1,649 = 0.46876895; contextual 780/1,649 = 0.47301395**, a **net 7 token / ~0.4245 percentage point gain**. POS coverage 954/1,649 (0.57853244); conditional context accuracy 780/954 (0.81761006), which must never replace the complete-denominator headline. POS candidate recall 905/1649 (0.54881747), macro group accuracy 0.36066520 baseline vs 0.36289471 context, 37 POS changes, 279 context-supported assignments, 436 multi-POS tokens, 570 training-attested token-adjacent POS pair occurrences.
- **Morphology reference-label recall denominators**: genus 168/412, numerus 267/605, status 158/413, inflection 43/246, voice 48/146, verbalClass 98/287. Coverage/ambiguity still severe; POS evidence is not inflection synthesis.
- **Host exact-head workflow:** Project Governance `37923609501`, **34 governance, 182 data, 84 linguistic, 299 evaluation tests** passed and LING-003 actual changed-file scope passed. First-use full report `ling/translation/experiments/W12B_AMARNA_GRAMMAR_RESULT.md`; canonical SHA-256 `a339e434a29f735330151d31115d3d91828aa836b47b00e1f8b185907272f3a6`.
- **Scientific adjudication:** All source inputs are original publisher-attested **Egyptian editorial transliteration**, not photographs; original source-text IDs are not independently verified papyrus/work/scribe or blind-review partitions. W12B Amarna target now exposed after first use; never retune and claim it is new heldout. No source-exact manuscript line, blind semantic quality, independent grammatical role/dependency gold, fluent German translation or VLM inference was produced. **No LING-003 points, canonical 34.5/100; validated real Hieratic model experiments 0.**


## EXP-LING-003-W13-EGYPTIAN-PC — Frozen oracle-POS Old Egyptian dependency diagnostic

- **Task/state:** LING-003 active 0/2; PR [#110](https://github.com/m7mdehab/hieratic-ai/pull/110), merged as `54c4dd8651fb65b756ed9d9b6fd80da9bd12545f`. **Engineering/research evidence only**; not a validated Hieratic model experiment.
- **Original source and rights:** University of Jaén / Universal Dependencies [Egyptian-PC](https://github.com/UniversalDependencies/UD_Egyptian-PC), Old Egyptian Pyramid Texts, CC BY-SA 4.0; source tree `fca8538287cb69fd07b811eb55dcfd25584f3006`; train original Git blob `ea262ee047943b81c0e0db8ff139ec7deb9b7b53`, official DEV `78a9749f823441633836b63a952df05d8636624c`. Official TEST original Git blob `f40982ca7dc7b67a5ed6d6bc90f4fe8dcd8085f6` identified **but deliberately not opened**.
- **Prereg and provenance:** `ling/translation/experiments/W13_PREREG_EGYPTIAN_PC_DEPENDENCIES.md` registered before viewing official development gold. Immutable derived train-statistics and dev-label Git blobs: `4bedc6cd872cc9e93339bd0fad4bba780b5cda49`, `2694c4aa14dd6712b9fb45d714caead1c8856d64`. Train 1,619 sentences / 19,486 tokens; dev 230 original sentences / 3,167 tokens, no sentence-ID intersection. Identity separation is **not** independent witness or period separation.
- **Model and privilege:** Deterministic train-only dependent-UPOS/head-UPOS/direction/DEPREL frequency + fixed 0.02 distance penalty; single root and cycle repair. Comparison is a frozen naive previous-token baseline. Both systems receive **gold official DEV UPOS** at prediction time; no DEV dependency heads or relation gold enters prediction.
- **First-use full-population result:** UAS baseline 1,390/3,167 = **43.890117%**; model 1,849/3,167 = **58.383328%** (+459 correct heads, +14.493211 pp). LAS baseline 554/3,167 = **17.492895%**; model 1,143/3,167 = **36.090938%** (+589 correct head-and-relation tokens, +18.598043 pp). Both produced zero invalid trees. Exact deterministic result SHA-256 `da5710ab3ea140f34d68fba5457ad4cf56d1d0a7e4cf2a0ec7a050086e736f70`.
- **Reproduction:** `python -m ling.translation.w13_egyptian_pc verify`; `python -m ling.translation.w13_egyptian_pc evaluate`; `python -m unittest tests.linguistics.test_translation_layer`. Exact-head Linux [Project Governance run 37929827457](https://github.com/m7mdehab/hieratic-ai/actions/runs/37929827457) passed. No independent rerun of private source-manifest preparation by this overseer.
- **Decision and safeguards:** Positive dependency learning under **oracle POS**, not a source-image OCR, German semantic translation, later-period transfer, end-to-end parsing or independent expert/witness test. Official DEV now **EXPOSED**; official TEST remains sealed/unread and must not be opened without the separate scientific authorization gate. No automatic milestone points, goal/research-coverage change, DATA-008 admissions or trained-neural-model count change.



## EXP-LING-003-W14-EGYPTIAN-PC-ORACLE-FREE-TRAIN-GROUP-001

- **Task:** LING-003; **classification:** COMPLETED_SOURCE_ORIGINAL_TRAIN_ONLY_RETROSPECTIVE_DIAGNOSTIC, NOT_INDEPENDENT_BLIND_GENERALIZATION.
- **Hypothesis:** train-group-only FORM→predicted-UPOS→dependency model can recover some genuine Old Egyptian source-original syntactic labels without supplying gold inference-time UPOS and beat the deliberately weak train-only majority-POS previous-token baseline.
- **Preregistration:** `ling/translation/experiments/W14_PREREG_ORACLE_FREE_TRAIN_GROUP.md`, independently committed BEFORE W14 group scoring as `b7424bf379616adecec7f96548cc808e3b6cde85`. Full prior W13 original TRAIN aggregate was already exposed, preventing any untouched-test claim.
- **Source:** UniversalDependencies/UD_Egyptian-PC, University of Jaén Díaz Hernández and collaborators; Original tree `fca8538287cb69fd07b811eb55dcfd25584f3006`, TRAIN Git blob `ea262ee047943b81c0e0db8ff139ec7deb9b7b53`; derived CC BY-SA 4.0 Git blob `2b42a078e6ec4277a5ab7016d6f966c3545a7894`; all 1,619 genuine source TRAIN sentences. Official DEV exposed by W13, TEST never opened.
- **Split:** Teti/Neith/Merenre 790 sentences/9,157 tokens for all training; Pepi 829/10,329 evaluation; published metadata groups, not adjudicated distinct physical handwriting witnesses. Exact complete FORM-sequence train/eval duplicates = 0, but literary/genealogical overlap unresolved.
- **Method:** deterministic train-only exact-form POS majority → unseen-form 3/2/1 char suffix thresholds 3/5/8 → train-global majority; unchanged W13 head-POS/direction/DEPREL frequency parser trained solely on W14 training groups, 0.02 distance penalty and cycle/root repair. Comparison A majority-UPOS previous-token control; comparison B true FORM-only non-oracle pipeline; comparison C separately privileged gold-UPOS upper-bound diagnostic. No new trainable neural parameters or external model API; fixed program, deterministic, no seed needed.
- **Results full heldout:** predicted POS 8060/10329 (78.0327%) and macro-F1 0.62421625; weak UAS 4259/10329 (41.2334%) and LAS 750/10329 (7.2611%); nonoracle UAS **4757/10329 (46.0548%)**, LAS **2811/10329 (27.2146%)**; oracle-only UAS 6489/10329 (62.8231%), LAS 4316/10329 (41.7853%). Every predicted tree valid; no target-reference-based tuning. Source-derived form coverage exact 8240, suffix3 829, suffix2 346, suffix1 776, train-majority 138.
- **Verification:** PR [#112](https://github.com/m7mdehab/hieratic-ai/pull/112) merged at `2a72409d6c100e6f83be038e708632bdbe5b1e8a`, exact-head full hosted Project Governance run [37974824523](https://github.com/m7mdehab/hieratic-ai/actions/runs/37974824523) SUCCESS including integer pinned result assertions, golden-free inference injection and group/byte integrity tests.
- **Artifacts:** `ling/translation/w14_oracle_free.py`, `ling/translation/experiments/W14_ORACLE_FREE_TRAIN_GROUP_RESULTS.md`, `docs/linguistics/TRANSLATION_PROTOCOL.md`; command `python -m ling.translation.w14_oracle_free evaluate`.
- **Outcome/caveats:** authentic source-grammar diagnostic, no manuscript image, independent scribe support, full fluent translation, external semantic adequacy or original blind gold. Contributes research software/evidence but **0 scientific milestone points**. Goal **34.5/100**, historic research coverage **14%**, active LING-003 **0/2**, validated real Hieratic image/model experiments **0**, trained neural models **0**.
