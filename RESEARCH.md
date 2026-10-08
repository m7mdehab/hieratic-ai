# Research Registry

This file tracks the compact research state. Detailed notes may later live under `docs/research/`.

## Evidence labels

- **VERIFIED-PRIMARY** — checked against the original paper/repository/dataset/site or other primary source.
- **VERIFIED-SECONDARY** — supported by a reliable secondary source but primary source not yet inspected.
- **CANDIDATE** — discovered during reconnaissance and awaiting verification.
- **REJECTED** — investigated and found irrelevant, inaccurate, inaccessible, or otherwise unsuitable.

## Current research conclusions

### R-001 — Overall feasibility

**Status:** preliminary, to be strengthened with primary-source citations.

The problem is best treated as a sequence of capabilities rather than a single classifier: script/document understanding, visual recognition/HTR, transliteration/normalization, linguistic interpretation, and translation.

The current program assumes that partial computational work on Hieratic exists while robust, general-purpose reading across unseen documents/scribes remains unsolved enough to justify research. This must be documented rigorously in FND-004.

### R-002 — HieraticBench

**Status:** CANDIDATE / external benchmark.

HieraticBench is treated as an external evaluation resource, not the definition of project success. Its exact composition, methodology, model results, source repository, leakage risks, and licensing must be verified from primary sources before being encoded into evaluation claims.

### R-003 — Data landscape

**Status:** CANDIDATE.

Initial reconnaissance identified candidate Hieratic sign/image resources, computational prior art, palaeographic databases, and at least one recent dataset direction. No candidate is considered cleared for training or redistribution until provenance, labels, access method, and license are verified.

### R-004 — Hieratic writing-system and machine-reading problem map

**Status:** VERIFIED-PRIMARY / completed as FND-003.

A source-grounded problem map is now available at `docs/research/HIERATIC_WRITING_SYSTEM_PROBLEM_MAP.md`.

Key validated implications:
- Hieratic varies strongly across period, register, scribe, material, and layout.
- Allography, abbreviation, and ligatures prevent a simple fixed-font classification framing.
- visually ambiguous signs can require phonetic/classifier and sequence context;
- image-to-translation must be decomposed into auditable recognition, standardized rendering, Egyptological transliteration, linguistic analysis, and translation layers;
- evaluation must eventually include provenance-aware held-out splits rather than random crop splits.

FND-003 is validated. It unblocks EVAL-001.

### R-005 — Verified prior art and data registry

**Status:** VERIFIED-PRIMARY / completed as FND-004.

The project now has a source-verified registry at `docs/research/PRIOR_ART_AND_DATA_REGISTRY.md`.

Key findings:
- Hieratic-specific computational/OCR work predates HieraticBench, including a 2021 CNN experiment, Tabin's 13,134-sign OCR corpus/tool, Isut, and the 2025 HieraticAI prototype.
- HieraticBench contains 268 repository item records and is now formally reserved for external evaluation rather than training.
- DDD (June 2026) is a high-value modern dataset candidate: 159 images, 50 papyri, 504 character/group categories, polygon annotations, and supplied closed/open-set split families.
- HPDB and AKU-PAL are strong palaeographic/sign-retrieval resources.
- TLA is strategically valuable for transliteration/linguistic modeling, but its live website terms do not allow bulk corpus extraction.
- Several resources require rights clarification at the data/image level even when their software repository is open source.

FND-004 is validated. It unblocks FND-005, EVAL-002, and (together with FND-003) EVAL-004.

## Active research questions

1. What are the strongest primary-source prior-art examples specifically involving Hieratic, distinct from hieroglyphic/Demotic/Coptic OCR?
2. What legally usable image/transliteration pairs exist at sign, line, page, and document level?
3. Which variation axes must be isolated in train/dev/test splits: document, scribe, period, material, collection, edition?
4. What constitutes a defensible transliteration target when multiple scholarly readings are valid?
5. Which external benchmark items may have appeared in foundation-model pretraining or public digital editions?
6. How should expert uncertainty and alternative readings be represented?
7. What is the best first specialist baseline that provides information useful to later VLM work?

## Immediate overseer research outputs

FND-003:
- **completed** — see `docs/research/HIERATIC_WRITING_SYSTEM_PROBLEM_MAP.md`.

FND-004:
- **completed** — see `docs/research/PRIOR_ART_AND_DATA_REGISTRY.md`.

FND-005:
- enforceable licensing/provenance policy.


### R-006 — Layered evaluation contract

**Status:** VERIFIED / completed as EVAL-001.

The project now evaluates reading as a layered capability chain rather than as one end-to-end score.

Key decisions:
- visual recognition, transliteration, linguistic interpretation, translation, and uncertainty remain separately measurable;
- multiple acceptable scholarly readings and illegible spans are supported;
- document-macro aggregation is required where micro averaging could be dominated by large/easy documents;
- translation uses source-faithfulness plus adequacy, with automated MT metrics treated as supporting diagnostics;
- calibration and selective-risk reporting are part of the reading objective rather than optional polish;
- no primary composite score is used in evaluation v1.

See `docs/evaluation/METRICS_SPEC.md` and `eval/metric_contract.yaml`.


### R-007 — Pinned HieraticBench external reproduction (EVAL-002)

**Status:** VERIFIED-PRIMARY, source-code inspected and CI reproduced public aggregates.

Pinned benchmark commit: `d587dc990013f18007f1e7a8f56f96ff2f7127e2`; harness `0.1.0`.

Official structure: 268 items, 266 public + two sealed images of the same commissioned sentence; 150 public AKU-PAL single signs; 118 identify-eligible items; 13 published model/effort rows in the Oct 5 snapshot.

The benchmark's 0/0.5/1 script-ID credit, first-code sign scoring, bounded 1-minus-edit-distance sign/transliteration scoring and chrF translation function are **official benchmark rules**, not interchangeable with Hieratic AI's EVAL-001 metrics.

Reproducibility:
- successful independent GitHub Actions audit of pinned upstream public run data;
- 1,892 run records inspected, 1,738 item/model/rung means and 17 aggregate model/rung values verified against official leaderboard;
- 13 synthetic Python tests and eight original upstream scorer tests passed;
- model provider calls **not** rerun;
- no public machine-scored readings/translations for the sealed sentences; no answer key inferred.

Evidence: `docs/evaluation/HIERATICBENCH_REPRODUCTION.md`,
`eval/benchmarks/hieraticbench/`,
[Actions audit run 37693626552](https://github.com/m7mdehab/hieratic-ai/actions/runs/37693626552).

Methodological constraint: external item content, source near-duplicates, and benchmark gold stay out of training/dev, regardless of source-license permissiveness.


### R-008 — Error taxonomy and reproducible review workflow (EVAL-005)

**Status:** ACCEPTED methodology and software contract, not a reported model result.

Defines 48 failure codes across 16 visual, linguistic, uncertainty, generalization and evaluation-integrity layers. Review events are typed, evidence-linked, may express upstream causal relationships, and track adjudication, gold missingness, contamination, stratum metadata and publication scope. Public summary logic suppresses sealed-record aggregates. Error counts are not performance rates without frozen scored denominators.

Evidence: `docs/evaluation/ERROR_TAXONOMY_AND_ANALYSIS.md`, `eval/analysis/`, dedicated passing GitHub Actions error-analysis workflow, 23 new synthetic tests.


### R-009 — Untuned frontier model baseline preregistration

**Status:** PROTOCOL-STAGED / no experimental evidence.

A versioned, fail-closed untuned frontier VLM evaluation protocol has been implemented for public HieraticBench script-ID and isolated-sign rungs. Candidate provider lanes are OpenAI, Anthropic and Google; exact provider IDs/configurations remain unresolved. Prompt source and dataset commit are pinned to accepted EVAL-002, but frozen item manifest and exact prompt hashes still require verification.

Read-only tooling validates planned capture completeness, hashes and provider/prompt consistency using synthetic offline tests. No API calls, new model predictions, official new scores, or trained models have been produced. This is **not** a verified EVAL-003 baseline and does **not** change research coverage.

See `docs/evaluation/FRONTIER_BASELINES.md`, `eval/baselines/` and PR #31.


### R-010 — W1 acquisition, annotation and evaluation-split infrastructure (validated)

**Status:** REVIEWED TOOLING / NO CLAIM OF CORPUS ADMISSION OR GENERALIZATION.

The corrected W1 package passed live GitHub CI and was merged in independent PRs:
- **DATA-002 (#20):** acquisition-manifest rights/provenance planner, with item-level reviewer and licence evidence, benchmark-overlap review, SHA-256 lineage and fail-closed synthetic/placeholder checks. A conditional plan is not asset acquisition or admission.
- **DATA-004 (#23):** layered Hieratic annotation schema with strict certain-gold anchoring, acceptable alternatives, document/line/region/sign relations, coordinates, reviewer provenance, unique reading order and parent-region cycle checks.
- **EVAL-004 (#24):** deterministic document/scribe/period/source split planning and quarantine of unreviewed high-risk benchmark overlaps. Upstream benchmark public item roster is aggregate-only and production image overlap must receive independent item-level review.

Observed CI: DATA-002 final 34 governance/51 data/78 evaluation tests; DATA-004 34/32/57; EVAL-004 34/13/78, all passed with approved task-branch scopes. **No rights-controlled images, trained models, model experiments or unseen-scribe performance were produced.**

Capability points **+7.0** (11.5 -> 18.5), phase P2 **6.5/10**, phase P3 **7/20**. Research coverage remains **14%** pending its separate operational denominator.


### R-011 — Sealed evaluation policy, metric-claim auditing and public-freeze preregistration

**Status:** VERIFIED METHODOLOGY/TOOLING — NO REPORTED MODEL PERFORMANCE.

EVAL-006 created a versioned frozen **policy** for independent blind Hieratic evaluation, contamination response and release authority. It does not certify a real sealed corpus or evaluate a real checkpoint. Its linked redacted-report contract forbids missing/altered attempts, post-hoc metrics, composite scores, unsubstantiated stage/generalization claims and confidence intervals without document groups. Scientific release must also meet item-specific rights and benchmark-overlap evidence and independent review.

PRs #35 and #40 passed CI and were accepted (+2.0 points). A total of 145 evaluation tests passed in the final audit; this includes synthetic cases, **not** model runs.

Separately, EVAL-003's pinned public metadata freeze was implemented in PR #38. Ephemeral CI examined only permitted metadata/prompt source in the EVAL-002 upstream checkout at commit `d587dc990013f18007f1e7a8f56f96ff2f7127e2` and verified 116 public script-ID + 150 sign item/rung records (2 sealed items excluded). It creates no inference results or spending authorization; EVAL-003 retains 0/1.5 points.

New goal progress: **20.5/100**, P2 evaluation **8.5/10**, research coverage 14%, 0 validated experiments and 0 trained models.


### R-012 — W2 data-engine contracts and strict provenance/ambiguity gates

**Status: REVIEWED ENGINEERING INFRASTRUCTURE — not a real corpus or experimental result.**

DATA-003 #36: deterministic image preprocessing, SHA256 lineage, coordinate transforms and dataset IDs. DATA-005 #37: versioned Hieratic identity/variant claims separated from hieroglyphic and transliteration with verified citation metadata. DATA-006 #39: rights-linked image/line/sign/token alignment and synthetic-source exclusion from gold scoring. DATA-007 #41: independent blinded reviewer decisions, append-only supersessions, adjudication and transparent paired denominators.

All four merged following independent negative-test review, targeted fixes and final green CI (34 governance/80 data/145 evaluation tests by last PR). No copyrighted manuscript images, real historical mappings, expert adjudication, trained models, model outputs, or benchmark scores were produced.

**Verified progress +10.0** to 30.5/100, P3 17/20, P2 8.5/10, coverage unchanged at 14%. DATA-008, VLM-001 and LING-001 become dependency-ready only.


### R-013 — W3 original baseline freeze and primary-source rights readiness

**Status:** MERGED RESEARCH INFRASTRUCTURE, no model results. Date: 2026-10-08.

[PR #47](https://github.com/m7mdehab/hieratic-ai/pull/47) passed complete frontier-baseline CI: 175 evaluation tests and frozen pinned public inventory/prompt-source verification. `eval/baselines/run_freeze.py` rejects unapproved/unsafely stored, altered, missing or mismatched original model prompt/image attempt evidence; per-attempt private provider responses are checked against *individual* rendered prompt hashes, not only an upstream shared prompt-source digest. The tool purposely emits no raw responses, claims no real provider calls and cannot validate rights/consent from a Boolean flag alone.

Official evidence audit `eval/baselines/SOURCE_RIGHTS_READINESS.md` (primary sources as of audit date): HPDB data CC BY with distinct underlying source imaging rights; AKU-PAL per-image; DDD noncommercial/share-alike plus individual image copyright; TLA limits mass copying; PaPYrus, HieraticAI, Isut software rights not equal to images. HieraticBench quarantined externally for evaluation only. No unrestricted corpus admission from these observations.

W3's EVAL-003 remains active and earns zero until real inference, frozen run/cost/rights record, official scores, independent reproduction and human scientific review. No change to 30.5/100 progress, 14% coverage or 0 experiment/model counts.


### R-014 — W3 linguistic normalization acceptance and official-score parity preflight

**2026-10-08.** LING-001 accepted as a versioned, deterministic Unicode/transliteration normalization **technical layer** preserving DATA-004 source alternatives and uncertainties, without fabricated Egyptian lexical interpretation. Independent regression tests include annotation hash drift, collision preservation, token provenance, and concurrent immutable-output protection. PR #51 accepted after governance CI was extended in PR #53, including all 8 linguistic tests. **+2 earned capability points**, P6 2/10.

EVAL-003 PR #50 integrated actual *pinned upstream official TypeScript scorer* into redacted private-capture replay. Native scorer parity exercised on 266 synthetic items, with failure and abstention accounting, but no model output was generated. EVAL-003 remains active, unearned +0/1.5.

Current project milestone 32.5/100. No licensed production manuscript dataset, real VLM run, actual expert annotation or training experiments have been verified. Research coverage remains 14%.


### R-015 — Institutional CC0 Hieratic image-source leads (source discovery only)

**2026-10-08. Status: VERIFIED-PRIMARY institutional access/rights statements; NO ITEM ADMISSION.**

An independent overseer audit identified a new potential path toward a rights-compatible image *source* beyond HPDB/AKU-PAL/DDD: Museo Egizio's Turin Papyrus Online Platform (TPOP) explicitly describes **CC0 images** and about **80 public Hieratic papyri**, with over **12,050 registered Hieratic papyrus entries**; Met Open Access also publishes CC0 public-domain images and identifiable Hieratic ostraca. TPOP partner PDFs and editor-authored transcriptions/translations have **different or insufficiently demonstrated** reuse rights. Met's image availability and `isPublicDomain` status require per-object verification.

**Core limit:** these are rights-policy and object-discovery leads, not a licensed paired corpus. Image-content hashes, registered access/automated extraction terms, expert text/annotation rights, benchmark source/near-duplicate disjointness, and independent train/dev/test gold remain unresolved. HieraticBench already contains Met and Wikimedia source items; neither may be mined for examples. No acquisition, rights approval, experiment, data release, capability points or research-coverage percentage change is asserted.

Detailed primary URLs, sample object IDs, explicit rights boundaries, proposed admission checks and an unsent contact inquiry:
`docs/research/OPEN_ACCESS_HIERATIC_IMAGE_SOURCES_2026_10_08.md`.


### R-016 — Primary-source shortlist for first real image-to-transliteration gold (W4 overseer)

**2026-10-08. Status: VERIFIED-PRIMARY institutional source metadata / preliminary benchmark source-name audit, NO CORPUS ADMISSION.**

Identified **15** specific public catalogue leads: **6 Turin Papyrus Online Platform (TPOP)** records with image policy CC0 but editorial text rights/open export unverified, plus **9 Met Open Access** Hieratic ostraca with institutional public-domain image labels but no verified image bytes or line-aligned gold. TPOP Cat.1896 / Cat.1971 are the first paired-corpus *permission-inquiry* priorities; Met 561345 / 561392 / 561361 are promising independently annotated image-only alternatives. Famous/fragment-assembled records are deferred or require additional group isolation.

Independently checked **37 pinned HieraticBench Met source records and 61 pinned Wikimedia source records**, using source names/URLs only (no gold or images reused). None of the 15 proposed institutional identities was directly named in those 98 source records, but this is **NOT** full benchmark, item-hash, near-duplicate or pretrained-model leakage clearance; all 15 remain in `benchmark_quarantine_pending` for training and few-shot. Notably the pinned benchmark already includes Met 545587/545588/545584 and Wikimedia Turin King List Cat.1874 and other Turin ostraca; prevent re-admission through renamed images.

R-016 defines two concrete gated tracks: obtain **written approved TPOP image+editor-text paired export**, or use individually verified **Met CC0 images plus newly commissioned, independently double-reviewed Egyptological gold**. Both require permitted access, exact image provenance, independent text/annotation rights, all-source quarantining and genuine leakage-safe splits before DATA-008 +3 can be reviewed. Two institution-specific outreach drafts are **unsent**. No acquisition, expert annotations, contacts, progress credit or research-coverage change occurred; canonical goal **32.5/100**, research coverage **14%**.

Primary-source URLs, per-record evidence, identified benchmark exclusions, admission protocol and outreach drafts: `docs/research/R016_CORPUS_GOLD_FEASIBILITY.md`. Machine-readable **candidate-only** manifest: `docs/research/R016_PRELIMINARY_CANDIDATE_ROSTER.yaml`.


### R-017–R-019 — Expanded W5 overseer institutional source, benchmark lineage and real pilot research (2026-10-08)

**W5 dispatched:** User explicitly confirmed sending expanded, substantial W5 assignments to both Luna/Codex (DATA-008 full rights/provenance/admission pipeline) and Anti-Gravity Gemini (VLM-001 scientific evaluation architecture). Independently owned overseer deliverables were completed on research branch; agent PR results will need later exact-head independent verification.

**R-017 COMPLETED: public benchmark *metadata* census of every 266 / 266 public files** at immutable upstream `alymoursy/hieraticbench@d587dc990013f18007f1e7a8f56f96ff2f7127e2`, excluding both sealed files and all answer/image/gold fields. Distribution: 150 AKU, 16 CBL, 37 Met, 61 Wikimedia, 2 Yale. All IDs unique; 191 distinct raw object-name strings **are not 191 unique manuscript groups**. AKU's 150 source items collapse to 82 raw support-name strings; repeated originals include Louvre E 25416 (5 entries), Brooklyn 47.218.84 (5), Met 22.3.517 (4), Turin CGT 54050 (3), and others. All 15 R-016 candidates have **no exact literal public source-identity match** in these 266 metadata rows, but **no alias, image, edition, perceptual or pretrained-model leakage clearance**. Every candidate remains prohibited for training/few-shot. Outputs: `docs/research/R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl` (metadata only), `R017_R016_CANDIDATE_SOURCE_CROSSWALK.json` (all 15 blocked) and `R017_PUBLIC_BENCHMARK_LINEAGE_AUDIT.md`.

**R-018 COMPLETED: twelve institutional/collection classes plus separately restricted Tsukuba HDB** compared on image policy, actual annotation access, derived text rights and training/weights reuse. Priority (A) CC0 image TPOP with independently licensed editor manuscripts; (B) Met OA images needing *new* Egyptologist gold; (C) Tsukuba/Tokyo Hieratische Paläographie DB—**2,065 CC BY 4.0 published sign-index records and 937 concordance records**, with **underlying IIIF reproduction rights a separate gate**; (D) Chester Beatty CC BY 4.0 images and Yale Peabody CC0 by object; constrained AKU per-image SVG, DDD NC/SA partial polygons, restricted TLA larger than ten pages, Ramses, BM, UCL and LMU. Rights analysis `R018_INSTITUTIONAL_RIGHTS_GOLD_FEASIBILITY.md`, 13-source all-BLOCKED `R018_INSTITUTIONAL_EVIDENCE_MATRIX.json`. Additional museum/academic contact drafts remain **UNSENT**.

**R-019 COMPLETED: preregistered end-to-end real-data and inference plan** `R019_FIRST_REAL_HIERATIC_PILOT_PROTOCOL.md`. First genuine rights-cleared image + independent scholar-adjudicated line is only an integration proof; next stage needs source-separated multi-document stratified cohort, legal/image/editorial authorization, manuscript-level heldouts, frozen independent item universe, genuine visual inference, SCRIPT_ACC/SIGN_TOP1/TR_CER/TRANS_CHRF with EVAL-006 clustered uncertainty and proper control arms. Defined annotation handbook, stop rules, 9 release/inference/gold gates, cross-agent adversarial scenarios and real human resource decisions. **Not** actual data or experiment.

**Canonical unaffected:** goal **32.5/100**, coverage **14%**, zero trained models, zero validated real experiments; DATA-008/VLM-001/LING-002 active and EVAL-003 pending. No museum data downloaded, no permission granted, no contact sent, no sealed files opened, no task credits awarded. An independently reviewed real-data source, Egyptologist gold, model image-conditioned execution and genuine held-out statistics remain gating.


### R-020 — Source-specific first image + diplomatic-line pair rights and acquisition audit (2026-10-08)

**COMPLETED researcher-owned public source feasibility work**, NOT acquisition or a model experiment. After user dispatched the W5 trust-hardening revisions to Luna/Codex DATA-008 #63 and Gemini VLM-001 #52, overseer reviewed exact original records for **all 15 R-016 institutional candidates** (six Museo Egizio Turin TPOP document groups, nine Met object records) against official current image/content reuse policies, technical API documentation and known per-object scholarly edition attribution. No original image bytes, editor text, line gold, outside email, registered-only data, or license signatures acquired. All 15 remain **BLOCKED_METADATA_ONLY**, zero corpus admissions.

**TPOP:** Official policy grants CC0 only to *TPOP-provided images*, not editors' attributed textual transcriptions, hieroglyphic renderings or partner PDFs (some CC BY-NC). [Official policy](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/Policy-on-access-and-publication-of-papyri/), [public/registered access](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/What-is-accessible-for-whom-/); nonregistered circa 130 documents (80 Hieratic), registered >12,050 entries are not verified licensed gold pairs. **Primary inquiry: Cat.1896**, writing-specific recto royal decree + separate verso address/ration note, contributor names and Ramses Online ID 1066, but no permitted original image bytes or reusable text export. **Second: Cat.1971**, Ramses ID 112 / linked incoming letter Cat.2026. Cat.1966 nine joined parts, Necropolis Journals 16 joined accession fragments, and famous Cat.1880 need enhanced leakage controls. Contact drafts only; nothing sent.

**Met:** All nine specific object pages mark artwork **Public Domain**; Met CC0 OA policy and [documented object endpoint](https://metmuseum.github.io/) support a potential authorized image+new Egyptologist gold pilot. Current research browser could not retrieve raw `collectionapi.metmuseum.org/public/collection/v1/objects/{ID}` JSON for attempted 561345/561392/561410/561413: `isPublicDomain`, image URL and original pixel hash **NOT verified**. Primary fallback original objects **561345 / 09.184.703** (official visit) and **561392 / 09.184.751** (torch/lamp notes); museum synopsis is NOT line transcription. No actual original images downloaded or professional gold produced. Met API's public September 2026 update changed **search v1.1**, but per-object remains documented v1.

**Decisions and explicit artifacts:** `docs/research/R020_FIRST_PAIR_SOURCE_DOSSIERS.md` primary links and 15 independent records; `docs/research/R020_OBJECT_SPECIFIC_FIRST_PAIR_EVIDENCE.json` individual purpose/rights/hash/no-go states; `docs/research/R020_OWNER_READY_INQUIRIES_UNSENT.md` item-scoped museum/editor/expert question packets, **unsent**; `docs/research/R020_ACQUISITION_GATE_CHECKLIST.md` G0–G8 exact support/photo/text/editor/expert/line geometry/benchmark/protected trust/eval guards; `docs/research/R020_FIRST_PAIR_INTAKE_TEMPLATE.json` **NO_GO** machine-readable dummy intake with all vital receipts null. One later genuinely lawful pair would establish only data continuity; no corpus adequacy or model capability.

**Blocking owner actions:** determine commercial-compatible vs NC scholarly track; explicitly authorize named-source inquiry and original image acquisition/storage; obtain externally authorized editor/diplomatic-text licence or independently authored qualified Egyptologist line, second review/adjudication; secure source/edition/hash lineage and external trust-root admission governance in PR #63; independent VLM cohort/model auditing in PR #52. No new earned weighted progress; canonical **32.5/100**, research coverage **14%**, 0 real experiments, 0 trained models.



### R-021 and EVAL-003 W6 — Source-matched real Hieratic line feasibility and original frontier-baseline readiness (2026-10-08)

- **R-021 complete as a primary-source feasibility investigation**: discovered Leiden/Louvre [Abnormal Hieratic Global Portal](https://lab.library.universiteitleiden.nl/abnormalhieratic/papyri-with-abnormal-hieratic-script/) **five side records from three physical Louvre papyri** (E 7851, E 7852, E 7856), with interactive word annotation, line transliterations and translations for E 7852. New potential actual source↔line correspondence, but specifically abnormal Hieratic Dyn.25–26, **not** New Kingdom Ramesside Hieratic. The [official rights page](https://lab.library.universiteitleiden.nl/abnormalhieratic/content-and-code-licenses/) explicitly reserves Louvre **original photo copyright** and Leiden **CC BY-NC-SA 3.0 Netherlands** on editor text/annotations; neither grants unrestricted commercial image+gold model-training permission. Original image bytes, ROIs/line coordinates, copyright override, expert validation and source novelty not acquired. Evidence: `docs/research/R021_IMAGE_TEXT_PAIRING_RIGHTS_AND_LEAKAGE.md`, `docs/research/R021_FIRST_PAIR_ROUTE_EVIDENCE.json` (ten tracked routes, all blocked).
- **R-017 explicit support exclusions enlarged:** pinned 266-public record literal comparison confirmed Papyrus Abbott **`wm-0021`**; Hearst Papyrus **`wm-0028`** plus **`aku-0032, aku-0039, aku-0112, aku-0139, aku-0144`**. Neither is a novel independent manuscript acquisition route. Leiden E 7851/7852/7856 absent as exact accession strings, **not alias/perceptual/edition or model-pretraining clearance**. All 15 R-016 candidate data still denied production admission. No benchmark gold/sealed material accessed.
- **R-021 next feasible routes:** (A) Leiden/Louvre dual rightsholder agreement for one E 7852 Abnormal Hieratic annotated line; (B) TPOP Cat.1896 exact CC0 original exposure plus authorized separate editor diplomatic writing/line; (C) Met OA 561345/561392 exact eligible image and **new** independently licensed qualified Egyptologist reading. No owner authorization to contact any institution or download/save protected media; draft questions only. One pair proves only data continuity.
- **EVAL-003 W6 documentary provider research** confirmed specific publicly advertised image-capable API candidates: OpenAI `gpt-6-luna` Responses, Anthropic `claude-sonnet-5-5` Messages, Google `gemini-3.8-flash` GenerateContent. All **CANDIDATE_ONLY** until account access, provider terms, cost, pinned prompt and image rights audited. `eval/baselines/w6_provider_candidates.json` holds exact official model URLs and unverified-access flags; `eval/baselines/w6_readiness.py` validates the catalogue, 266 metadata-only public source IDs split **150 signs, 116 identify**, quarantine, unchanged planning-only canonical suite, nonapproval and no model results, with thirteen adversarial tests + hosted CI step.
- **No actual baseline inference**: existing public freeze and official pinned TypeScript scorer CI operate on entirely synthetic predictions. Three providers × 266 public items × 3 scheduled samples = **2,394 hypothetical calls**, not authorized or budgeted. No API credentials or approved funds, no frozen approved live run or independent scientific results. EVAL-003 active 0/1.5, VLM-001 active 0/2, DATA-008 active 0/3; overall canonical 32.5/100, research coverage 14%, 0 real validated model experiments, 0 trained models. W6 Luna DATA-002 and Gemini VLM-001 agent work stays independent.



### R-022 / W7 EVAL-003 — museum cross-accession primary evidence + first original API run decision (2026-10-09)

- New **Met 561369 / accession 09.184.728** official catalogue entry is directly titled **“Hieratic Ostracon- see 09.184.703”**, the separately registered **Met 561345 / 09.184.703** source. The latter's official API `primaryImage` and `additionalImages` filenames contain **both** accessions. **The relationship is real and source-documented**, not merely a filename hunch, but a physical join, shared photographed support or same text remain **unverified**. Quarantine both within **one provisional source-leakage group**. The pinned R-017 266 public ID metadata has no literal ID/accession hits; this is not independence clearance. `docs/research/R022_LINKED_MET_SOURCE_AND_EXPERT_GOLD_FIRST_PAIR.md` and `R022_MET_LINKED_OBJECT_PILOT_DECISION.json` contain all source-specific evidence.
- **Preferred first core period original photo/gold path switches to Met 561392 / accession 09.184.751**, original official Met public-domain photo refs have only its own accession, 2 views of one support; still **no pixels, original SHA, independent editor/Egyptologist reading, usage-rights authenticated or source/edition independence**. Official Museo Egizio TPOP [research page](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Collection/Our-projects/Research-projects/) identifies specialist curator Susanne Töpfer, and [Crossing Boundaries](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Collection/Our-projects/Crossing-Boundaries/) demonstrates Ramesside interdisciplinary expertise; official papyrus contact exists, **but nobody was contacted/hired/quoted**, no guaranteed external annotation.
- **EVAL-003 W7:** `eval/baselines/w7_first_run_decision.json`, `w7_decision.py`, 14 adversarial tests and dedicated hosted CI audit. Current vendor published **Standard per-MTok** price anchors: Luna **$0.10/$0.50**, Sonnet 5.5 **$2/$10**, Gemini 3.8 Flash **$0.75/$3.75** through end-2026 (source links in packet). Image tokens/effort/retries/real account rates unknown so **no per-request quote/approved budget**. Protocol separates one user-owned synthetic **P0 API transport** (not Hieratic score) from one explicitly frozen official public benchmark **P1 diagnostic** (not population score), then later complete independent scientific corpus. Canonical frontier suite remains **planning**, no provider credentials, approved spend, owner requests, image bytes, actual provider calls or scientific results.
- Zero training/source admission, zero W7 scientific capability credit and no formal research-coverage promotion. DATA-008 and VLM-001 science barriers stay hard-disabled. EVAL-003 active; validated experiments/models remain 0.

