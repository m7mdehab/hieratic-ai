# Verified Prior Art & Data Registry

**Task:** FND-004  
**Status:** Completed and overseer-validated  
**Date:** 2026-10-07  
**Scope:** Hieratic-specific computational work, benchmarks, visual corpora, palaeographic resources, and linguistic resources with direct relevance to machine reading.

## 1. Evidence standard

A resource enters the verified registry only when its material claims were checked against one of:

- the original project/repository;
- the original dataset record;
- the original institutional database;
- the original academic publication/repository;
- an official project page maintained by the responsible institution.

Secondary articles may be useful for discovery, but they are not sufficient for a **VERIFIED-PRIMARY** status.

License labels below are descriptive observations, **not final legal clearance**. FND-005 converts this research into an enforceable provenance/licensing policy.

### Status vocabulary

- **VERIFIED-PRIMARY** — material facts checked against the original source.
- **RIGHTS-PER-ITEM** — reuse depends on the license attached to each record/image.
- **RESTRICTED** — source explicitly limits reuse relevant to our intended pipeline.
- **RIGHTS-REVIEW** — a repository/publication is licensed, but the training-data rights are not yet cleanly separable.
- **EVALUATION-ONLY** — project policy reserves the material for evaluation to reduce contamination risk.
- **CANDIDATE-TRAINING** — technically useful, but actual ingestion still requires FND-005/DATA-001 approval.

---

# 2. Prior computational work

## PA-001 — Bermeitinger, Gülden & Konrad — CNN character OCR (2021)

**Evidence:** VERIFIED-PRIMARY  
**Primary source:** JGU Mainz Open Science, DOI 10.25358/openscience-6757  
**Title:** *How to Compute a Shape: Optical Character Recognition for Hieratic*  
**Publication:** *Handbook of Digital Egyptology: Texts* (2021)

### Verified contribution

The paper explicitly describes an OCR experiment for Hieratic in which a **convolutional neural network classifies individual Hieratic characters**. The authors frame it as the final stage of an OCR pipeline and conclude that automatic Hieratic character classification is possible in principle while identifying substantial room for improvement.

### Rights / availability

- publication: open access;
- repository rights statement: **InC-1.0**;
- no independent broadly licensed training corpus was verified from this record.

### Relevance to Hieratic AI

This is a direct pre-2026 AI/computer-vision attempt on Hieratic. It is an important baseline/prior-art reference for isolated-sign recognition.

**Consequence:** a literal statement that "nobody attempted AI/OCR on Hieratic before HieraticBench" is not supported by the evidence.

Primary URL: https://openscience.ub.uni-mainz.de/items/d5ad09ee-3411-4197-a3f5-330b7752dac1

---

## PA-002 — Julius A. Tabin / PaPYrus — Image Deformation Model OCR (2022–2023)

**Evidence:** VERIFIED-PRIMARY  
**Primary publication:** JGU Mainz Open Science, DOI 10.25358/openscience-9590  
**Earlier thesis record:** University of Chicago, DOI 10.6082/uchicago.3695  
**Code/data repository:** https://github.com/jtabin/PaPYrus

### Verified contribution

Tabin created a dataset of **13,134 individual Hieratic signs** from existing and new facsimiles and developed OCR based on an **Image Deformation Model (IDM)**. The work covers individual-sign identification and larger-scale palaeographic comparisons.

The 2023 publication states that the tool and dataset are free/open source. The GitHub repository contains the data and OCR notebooks and is marked **GPL-3.0**.

### Granularity

- individual signs;
- sign labels/metrics;
- facsimile-derived sign images;
- comparative palaeography rather than line-level end-to-end HTR.

### Rights / availability

- 2023 publication: **CC BY 4.0**;
- PaPYrus repository: **GPL-3.0**;
- the exact legal treatment of all source facsimiles/data as training material still requires FND-005 review.

### Relevance

Very high for:
- sign-level baselines;
- metric/retrieval learning;
- palaeographic similarity;
- comparison against learned visual embeddings.

Primary URLs:
- https://openscience.ub.uni-mainz.de/items/7aef8525-734c-4ab5-a5c3-4fbf312e1397
- https://knowledge.uchicago.edu/records/2s822-v5p67
- https://github.com/jtabin/PaPYrus

---

## PA-003 — Isut — collaborative annotation and computational analysis (2023–)

**Evidence:** VERIFIED-PRIMARY  
**Official application:** https://isut.uliege.be/  
**Repository:** https://github.com/nederhof/isut  
**Publication:** Tabin, Nederhof & Casey, *Collaborative Annotation and Computational Analysis of Hieratic*, ICDAR 2023 Workshops.

### Verified contribution

Isut builds on Tabin's OCR work. Its stated goals are to digitize facsimiles, annotate glyph shapes, apply **automatic segmentation and OCR classification**, compare manuscripts, and model variation across periods, provenances, and genres.

### Rights / availability

- source repository: **GPL-3.0**;
- repository includes annotated-text backups;
- exact rights for every facsimile/text backup must be audited separately before reuse as training data.

### Relevance

High for:
- annotation UX;
- segmentation;
- glyph-shape representation;
- human-in-the-loop workflows;
- palaeographic analysis.

Primary URLs:
- https://isut.uliege.be/admin/about
- https://github.com/nederhof/isut

---

## PA-004 — HieraticAI — Westcar Faster R-CNN prototype (2025)

**Evidence:** VERIFIED-PRIMARY  
**Repository:** https://github.com/MargotBelot/HieraticAI  
**Context:** Freie Universität Berlin, Ancient Language Processing seminar (Summer 2025)

### Verified contribution

The project is a Hieratic-specific computer-vision prototype centered on the **Westcar Papyrus**. Its repository reports:

- Faster R-CNN with ResNet-50-FPN;
- **95 active Gardiner-code classes**;
- **605 manually annotated signs**;
- patching to **1,269 instances**;
- spatial train/validation/test strategy;
- reported **30.9% mAP** standard;
- reported **36.4% mAP with TTA** and **59.7% AP50**;
- a Streamlit human-validation interface.

### Rights / availability

- code repository: **MIT**;
- a pretrained model is referenced through Git LFS;
- MIT on the repository must **not** be assumed to relicense Westcar manuscript imagery, annotations derived from third-party material, TLA content, or AKU-PAL content.

### Relevance

High as a modern detection/classification baseline and human-in-the-loop reference. It is narrow in document scope and does not demonstrate general Hieratic reading/transliteration.

Primary URL: https://github.com/MargotBelot/HieraticAI

---

## PA-005 — Automated Segmentation of Hieratic on Papyri (2021)

**Evidence:** VERIFIED-PRIMARY for existence/title/authors only  
**Official evidence:** AKU project publication list.

The AKU project lists Bartosz Bogacz, Tobias Konrad, Svenja A. Gülden, and Hubert Mara, *Automated Segmentation of Hieratic on Papyri*, presented at CAA 2021.

### Verification boundary

The official project bibliography verifies that the work existed and addressed automated segmentation. Detailed method/results and reusable artifacts were **not** verified from a primary paper during FND-004, so no performance claim is recorded.

Primary URL: https://en.aku.uni-mainz.de/project-publications/

---

## PA-006 — HieraticBench — frontier multimodal benchmark (2026)

**Evidence:** VERIFIED-PRIMARY  
**Repository:** https://github.com/alymoursy/hieraticbench  
**Live site:** https://hieraticbench.vercel.app/

### Verified contribution

HieraticBench is a Hieratic-specific multimodal benchmark organized as a reading ladder:

1. identify the script;
2. identify signs;
3. transliterate;
4. translate.

The repository contains **268 item JSON records**, verified directly from `data/items/`.

Current composition:

| Prefix/source | Items |
|---|---:|
| AKU-PAL sign items | 150 |
| Chester Beatty | 16 |
| commissioned/sealed | 2 |
| Metropolitan Museum of Art | 37 |
| Wikimedia Commons | 61 |
| Yale Peabody Museum | 2 |
| **Total** | **268** |

The 150 AKU-PAL items are single-sign scoring items. The museum/Wikimedia material forms the public document/script-identification set and controls. Two commissioned modern sentences are sealed.

The repository reports October 2026 model runs in which frontier models can identify Hieratic on many public real-document images but perform much worse on isolated-sign reading; the exact results remain benchmark results, not a claim that the reading problem is solved.

### Rights / availability

- benchmark code (`bench/`, `site/`): **MIT**;
- public results: **CC BY 4.0**;
- public images: retain their source-specific licenses, recorded per item;
- commissioned `hb-0001` and `hb-0002`: © Aly Moursy, permitted for model evaluation; other use needs permission.

### Project policy

**EVALUATION-ONLY.** Exact HieraticBench images and gold labels must not enter our training corpus. This is stricter than the individual image licenses because benchmark independence matters scientifically.

Primary URL: https://github.com/alymoursy/hieraticbench

---

# 3. Verified data and knowledge resources

## DATA-R001 — DDD: Diagnostic Deir el-Medina Dataset (2026)

**Evidence:** VERIFIED-PRIMARY  
**Zenodo DOI:** 10.5281/zenodo.20553713  
**Published:** 2026-06-26

### Verified size and structure

The dataset record states:

- **159 images**;
- **50 papyrus documents**;
- **504 categories** of characters or character groups;
- polygon annotations produced in LabelMe;
- JSON and YOLO annotation formats;
- rectangular and polygonal sign crops;
- publishable full-papyrus and masked-papyrus image subsets;
- dataset files listed by Zenodo total approximately **5.3 GB**.

It explicitly says the annotations are **selective rather than complete character annotation**.

### Proposed split families supplied by the dataset

- closed-set recognition, document-aware;
- closed-set recognition, cross-document;
- character detection;
- open-set recognition;
- variants restricted to publishable documents.

The dataset does not provide the all-document detection case because not all source files can be redistributed.

### Rights

Zenodo describes the dataset license verbatim as **"CC 4.0 BY-SA-NC"** and says per-image copyright information is stored in `papyri.json`; full papyrus images are courtesy of Museo Egizio.

Because of the non-commercial condition and per-image rights complexity, status is:

**CANDIDATE-TRAINING / RESTRICTED — requires FND-005 policy before download or model training.**

### ML usefulness

Extremely high for:
- character classification;
- detection;
- open-set recognition;
- cross-document generalization;
- testing data schemas against real expert annotations.

It is a strong candidate for the "new dataset" mentioned in the motivating conversation because it was released in June 2026; this is an **inference, not a verified identification of what Aly Moursy meant**.

Primary URL: https://zenodo.org/records/20553713

---

## DATA-R002 — Tabin / PaPYrus sign corpus

**Evidence:** VERIFIED-PRIMARY  
**Size:** **13,134 individual signs**  
**Granularity:** isolated/facsimile-derived sign images with sign metadata/metrics.

### Rights

- publication describing it: CC BY 4.0;
- code/data repository: GPL-3.0;
- source-facsimile provenance and whether GPL is sufficient for every image/data component require FND-005 review.

**Status:** CANDIDATE-TRAINING / RIGHTS-REVIEW.

### ML usefulness

High for sign embeddings, retrieval, few-shot classification, palaeographic comparison, and baseline replication.

Primary URLs:
- https://github.com/jtabin/PaPYrus
- https://openscience.ub.uni-mainz.de/items/7aef8525-734c-4ab5-a5c3-4fbf312e1397

---

## DATA-R003 — Hieratische Paläographie Database (HPDB)

**Evidence:** VERIFIED-PRIMARY  
**Provider:** University of Tsukuba / University of Tokyo

### Verified datasets

The official dataset page exposes:

- **2,065** Hieratic sign-item records;
- item index JSON (about 3.3 MB);
- **937-record** ID concordance table;
- IIIF curation linking sign items to image regions;
- IIIF manifests for Möller's three palaeography volumes;
- JSON, JSON-LD, RDF/Turtle, and CSV data.

The contents include main characters, numerals, and ligatures from Georg Möller's *Hieratische Paläographie*.

### Rights

Official dataset license: **CC BY 4.0**.

**Status:** CANDIDATE-TRAINING, subject to FND-005 attribution/provenance implementation and image-layer confirmation.

### ML usefulness

High for:
- palaeographic retrieval;
- sign-ID concordances;
- Gardiner/Möller/Unicode/JSesh/AKU crosswalks;
- region-level historical sign exemplars.

It is less suited by itself to line-level HTR because the core asset is palaeographic sign/table data, not fully aligned continuous manuscript lines.

Primary URL: https://moeller.jinsha.tsukuba.ac.jp/en/datasets/

---

## DATA-R004 — AKU-PAL

**Evidence:** VERIFIED-PRIMARY  
**Provider:** Academy of Sciences and Literature Mainz / Altägyptische Kursivschriften project  
**Public database:** https://aku-pal.uni-mainz.de/

### Verified content

AKU-PAL presents Hieratic and cursive-hieroglyphic graphemes across approximately three millennia. Individual hieratograms are primarily facsimiles, sometimes image crops, with annotations covering writing characteristics, carriers/materials, dating, and other palaeographic metadata.

The official FAQ states that **individual images may be used and redistributed under the license stated for that specific image**.

### Rights

**RIGHTS-PER-ITEM.** There is no basis in FND-004 for treating the entire database as a single uniformly licensed bulk training corpus.

Therefore ingestion must record the license and attribution of **every acquired image**.

### ML usefulness

Very high for:
- exemplar retrieval;
- sign/allograph representation;
- period-aware metric learning;
- palaeographic crosswalks;
- building positive/negative visual pairs.

AKU-PAL is already a major source for HieraticBench sign items, so any training acquisition must also maintain image hashes/source IDs to prevent benchmark overlap.

Primary URLs:
- https://aku-pal.uni-mainz.de/
- https://aku-pal.uni-mainz.de/faq

---

## DATA-R005 — Thesaurus Linguae Aegyptiae (TLA)

**Evidence:** VERIFIED-PRIMARY  
**Provider:** Berlin-Brandenburg and Saxon Academies projects  
**Corpus edition:** 20 / web app 2.5.2 (2026)

### Verified linguistic content

The official TLA documentation reports:

- about **1.69 million lemma tokens** overall;
- about **1.355 million hieroglyphic/hieratic lemma tokens**;
- **49,037 entries** in the hieroglyphic/hieratic lemma list;
- Egyptological transliteration as the basic text level;
- growing digital hieroglyphic transcription in JSesh-specific Manuel de Codage and, where possible, Unicode;
- translations, mostly German with some English/French;
- lemma/POS information and grammatical annotation for many texts.

### Rights

The official license page permits copying/quoting **individual data sets for academic research**, but explicitly not entire subcorpora or larger sets (**>10 website pages**). It says separately licensed raw-data releases are being prepared.

**Status:** RESTRICTED for bulk extraction from the live website.

No scraping or bulk training ingestion is authorized by this registry.

### ML usefulness

Potentially central for:
- transliteration language modeling;
- lexical/morphological constraints;
- normalization;
- translation supervision;
- constrained decoding;
- linguistic retrieval.

Use requires an allowed raw release, explicit permission, or another legally valid route established in FND-005.

Primary URLs:
- https://thesaurus-linguae-aegyptiae.de/info/text-corpus?lang=en
- https://thesaurus-linguae-aegyptiae.de/info/lemma-lists?lang=en
- https://thesaurus-linguae-aegyptiae.de/info/licenses

---

## DATA-R006 — Isut annotated Hieratic texts

**Evidence:** VERIFIED-PRIMARY  
**Application:** University of Liège-hosted Isut  
**Repository:** GPL-3.0

The project stores annotated text backups and supports automatic segmentation/classification, sign-shape annotation, manuscript comparison, and OCR preparation.

**Status:** CANDIDATE / RIGHTS-REVIEW.

The software license is clear; rights for each underlying facsimile/text backup are not assumed from the software license. Do not bulk-import until FND-005 resolves provenance requirements.

Primary URLs:
- https://isut.uliege.be/admin/about
- https://github.com/nederhof/isut

---

## DATA-R007 — HieraticAI Westcar annotations/model

**Evidence:** VERIFIED-PRIMARY  
**Repository license:** MIT for repository software.

The repository reports manual annotation of **605 signs**, transformed into **1,269 patch instances**, with **95 active classes**, alongside a trained Faster R-CNN checkpoint.

**Status:** useful baseline artifact; **RIGHTS-REVIEW** for training-data reuse.

The fact that the code repository is MIT does not establish that third-party Westcar facsimile imagery or imported reference data are MIT-licensed.

Primary URL: https://github.com/MargotBelot/HieraticAI

---

# 4. Benchmark-source image pools

HieraticBench already curated open/public-document images from sources such as Wikimedia Commons, the Metropolitan Museum of Art, Chester Beatty, Yale Peabody, and AKU-PAL, with source and license metadata per item.

These collections may contain additional useful Hieratic material outside the benchmark. However:

> **No exact image, crop, or derived near-duplicate used by HieraticBench may be admitted into our training/dev corpus.**

If we later acquire from the same museums or repositories, DATA-001/DATA-008 must maintain:

- canonical source URL/object ID;
- original file hash;
- normalized image hash;
- perceptual hash;
- object/document identity;
- overlap checks against all HieraticBench sources/crops.

This allows us to benefit from open museum collections without destroying the credibility of external evaluation.

---

# 5. What the prior-art record changes

## 5.1 The literal "no prior AI attempts on Hieratic" claim is false

Verified evidence predating HieraticBench includes:

- a 2021 CNN experiment classifying individual Hieratic characters;
- Tabin's 2022/2023 13,134-sign OCR/IDM system and dataset;
- Isut's collaborative segmentation/OCR environment;
- a 2025 Faster R-CNN Hieratic detector/classifier.

Therefore our public writing must not repeat the stronger novelty claim.

## 5.2 The open research gap remains substantial

The verified prior art is concentrated around:

- isolated signs;
- palaeographic comparison;
- document-specific detection/classification;
- annotation/validation tooling.

FND-004 found no verified prior system in this registry demonstrating the full target we have defined:

> genuinely unseen Hieratic image → robust reading → defensible transliteration/normalization → linguistic interpretation/translation with calibrated uncertainty and cross-document/scribe generalization.

Absence from this registry is **not proof that no such work exists anywhere**. It is the current source-verified state and remains open to correction.

## 5.3 Stronger novelty framing

Our defensible research framing is:

- integrate specialist Hieratic vision/HTR with modern multimodal foundation models;
- measure reading at multiple auditable layers rather than only script ID or sign classification;
- test genuinely unseen documents/scribes and leakage;
- preserve uncertainty from visual recognition through translation;
- publish reproducible baselines, negative results, and a public control plane.

---

# 6. Resource suitability matrix

| Resource | Image data | Sign labels | Line/text alignment | Transliteration | Translation/lexicon | Rights status | Recommended role |
|---|---|---|---|---|---|---|---|
| HieraticBench | yes | yes (sign subset) | limited | framework/sealed | framework/sealed | mixed per item | external evaluation only |
| DDD | yes | yes, 504 categories/groups | partial/selective | limited by dataset labels | no core translation layer | NC + per-image details | research training candidate, rights-gated |
| PaPYrus | yes | yes, 13,134 signs | no core line HTR | sign metadata | no | GPL repo / source audit needed | sign baseline/retrieval candidate |
| HPDB | IIIF regions | sign/concordance | no | mapping metadata | no | CC BY 4.0 datasets | retrieval/concordance |
| AKU-PAL | yes | grapheme/MdC metadata | not primary line corpus | sign mapping | limited | per-image licenses | exemplar retrieval / palaeography |
| TLA | not primarily image corpus | linguistic signs/transcription in parts | text/sentence structure | extensive | extensive | bulk website restricted | language/lexicon layer with permission/raw release |
| Isut | facsimile-backed | glyph shapes | annotated texts | project-dependent | limited | GPL software; image rights audit | annotation/segmentation baseline |
| HieraticAI | Westcar images/patches | 95 classes | detection regions | not full target | linked reference tools | MIT code; data rights audit | detector baseline/HITL reference |

---

# 7. Immediate project decisions from FND-004

1. **HieraticBench remains quarantined as an external benchmark.**
2. **DDD is the highest-priority modern ML dataset candidate**, but FND-005 must settle NC/per-image policy before use.
3. **HPDB and AKU-PAL are highest-value palaeographic retrieval/sign-mapping resources.**
4. **PaPYrus/Isut are important baselines and possible sign-data sources, but data provenance/license handling needs explicit review.**
5. **TLA is strategically central for the linguistic layer but must not be bulk-scraped from the website under current stated terms.**
6. **The project must cite prior Hieratic OCR/AI work rather than claim a blank research history.**
7. **All future data acquisition needs overlap protection against benchmark objects/images, not merely filename separation.**

---

# 8. Known verification debt

The following are intentionally not presented as settled facts:

- Whether DDD is definitely the unnamed "new dataset" referenced by Aly Moursy — **likely, not verified**.
- Whether every PaPYrus/Isut facsimile can legally be redistributed or used to train released model weights — **FND-005 required**.
- Whether HieraticAI's bundled Westcar-derived data can be redistributed independently of the code — **not established by MIT code license**.
- Whether bulk AKU-PAL acquisition is acceptable even when individual selected images are licensed — **per-item rights are verified; bulk policy still needs conservative handling**.
- Whether a separately licensed TLA raw-data release already contains every linguistic field we would want — **must be checked before acquisition**.
- Whether the research literature contains additional unpublished/local Hieratic ML experiments — **possible**.

Preserving these unknowns is part of the acceptance criterion; they are not silently resolved.

---

# 9. FND-004 acceptance decision

### Criterion 1
> Every material prior-art/dataset claim has a primary or high-authority source.

**Satisfied.** Core claims are tied to original repositories, institutional dataset records, institutional databases, or original scholarly repository records.

### Criterion 2
> License, size, granularity, labels, provenance, accessibility, and ML usefulness are recorded where knowable.

**Satisfied.** The registry records those dimensions for the material resources and explicitly distinguishes software/publication licenses from data/image rights.

### Criterion 3
> Unverified claims remain visibly marked as such.

**Satisfied.** The verification-debt section records unresolved rights and factual questions rather than inferring answers.

**Verdict: FND-004 VALIDATED.**

---

# 10. Primary sources

- HieraticBench repository: https://github.com/alymoursy/hieraticbench
- DDD Zenodo record: https://zenodo.org/records/20553713
- Bermeitinger, Gülden & Konrad (2021): https://openscience.ub.uni-mainz.de/items/d5ad09ee-3411-4197-a3f5-330b7752dac1
- Tabin (2023): https://openscience.ub.uni-mainz.de/items/7aef8525-734c-4ab5-a5c3-4fbf312e1397
- Tabin thesis record: https://knowledge.uchicago.edu/records/2s822-v5p67
- PaPYrus: https://github.com/jtabin/PaPYrus
- Isut: https://isut.uliege.be/admin/about and https://github.com/nederhof/isut
- HieraticAI: https://github.com/MargotBelot/HieraticAI
- AKU-PAL: https://aku-pal.uni-mainz.de/
- AKU-PAL FAQ/rights: https://aku-pal.uni-mainz.de/faq
- AKU project publications: https://en.aku.uni-mainz.de/project-publications/
- HPDB datasets: https://moeller.jinsha.tsukuba.ac.jp/en/datasets/
- TLA corpus: https://thesaurus-linguae-aegyptiae.de/info/text-corpus?lang=en
- TLA lemma lists: https://thesaurus-linguae-aegyptiae.de/info/lemma-lists?lang=en
- TLA licenses: https://thesaurus-linguae-aegyptiae.de/info/licenses

Accessed/verified 2026-10-07.
