# Data Licensing & Provenance Policy

**Policy version:** 1.0  
**Status:** Active / mandatory  
**Effective:** 2026-10-07  
**Owner:** Hieratic AI overseer  
**Task:** FND-005

## 1. Purpose

Hieratic AI depends on museum images, facsimiles, scholarly annotations, historical editions, lexical corpora, benchmarks, and model artifacts originating outside this repository.

The project therefore separates four questions that are often incorrectly collapsed:

1. **May we access/copy the source?**
2. **May we use it for model training or evaluation?**
3. **May we redistribute the source or derived dataset?**
4. **May we release model weights/artifacts produced using it?**

A "yes" to one question is not automatically a "yes" to the others.

This policy is intentionally conservative. If permission is unclear, the default action is **do not ingest the asset**.

This document is project governance, not legal advice.

---

## 2. Scope

This policy applies to:

- manuscript/facsimile photographs and scans;
- sign crops, line crops, pages, and document images;
- annotations, bounding boxes, polygons, labels, transliterations, translations;
- museum/API metadata;
- scholarly editions;
- lexical/morphological corpora;
- benchmark material;
- fonts/sign drawings where used as ML data;
- third-party code only when it bundles or generates data assets;
- pretrained model weights and embeddings;
- synthetic derivatives made from third-party assets.

Repository-authored code/documentation remain under the repository's Apache-2.0 license unless a file states otherwise. That license does **not** relicense third-party assets.

---

## 3. Rights classes

Every external source/item must receive one project rights class before use.

### OPEN-PD

Public domain / CC0.

Default project treatment:
- training: allowed;
- evaluation: allowed;
- redistribution: allowed, subject to source metadata/ethical attribution;
- derivatives: allowed;
- attribution: preserve source/provenance even when legally optional.

### OPEN-BY

CC BY or comparable attribution license.

Default:
- training: allowed;
- evaluation: allowed;
- redistribution: allowed with required attribution/license notice;
- modifications: record transformation history;
- model release: normally eligible, subject to dataset/model-specific review.

### OPEN-SA

CC BY-SA or other share-alike content license.

Default:
- training: potentially allowed;
- raw/derived-data redistribution: must satisfy attribution/share-alike obligations;
- model-weight release: **requires explicit project review** rather than assuming whether share-alike reaches weights.

Do not combine OPEN-SA data into an unrestricted dataset release without a compatibility decision.

### NONCOMMERCIAL

CC BY-NC, CC BY-NC-SA, or equivalent non-commercial restriction.

Default:
- research experimentation: only if consistent with source terms;
- unrestricted/commercial training corpus: **not allowed**;
- public raw-data redistribution: only under source terms;
- released model weights: **rights review required**;
- commercial-compatible release track: excluded unless permission is obtained.

### PER-ITEM

A collection/database has item-level rights rather than one blanket license.

Default:
- every asset requires its own recorded rights fields;
- an asset lacking explicit compatible rights is rejected;
- collection-level public access is insufficient.

### EVALUATION-ONLY

Permission or project policy restricts material to evaluation.

Default:
- training/dev: prohibited;
- model-selection feedback: only according to the sealed evaluation protocol;
- redistribution: according to source terms;
- no augmentations/near-duplicates may be moved into training.

HieraticBench is EVALUATION-ONLY by project decision.

### RESTRICTED

Source terms permit only narrow use, prohibit bulk extraction, require permission, or otherwise conflict with intended ingestion.

Default:
- metadata/source link may be recorded;
- no bulk copying/scraping;
- no training ingestion unless explicit permission or a separately licensed release is found.

### UNKNOWN

No reliable rights statement has been verified.

Default:
- metadata-only;
- do not download into managed corpus;
- do not train;
- do not redistribute;
- escalate or seek permission.

---

## 4. Mandatory source-level provenance

Before any source becomes an approved candidate, its source record must capture:

- stable `source_id`;
- source/project name;
- responsible institution/person;
- canonical source URL;
- access/API/download URL if different;
- date accessed;
- source type;
- scope/granularity;
- stated license/rights text **verbatim**;
- normalized rights class;
- license URL when available;
- rightsholder/provider;
- attribution requirements;
- training permission status;
- evaluation permission status;
- redistribution permission status;
- commercial-use status;
- modification/share-alike obligations;
- known terms-of-use restrictions;
- evidence URL for the rights claim;
- verification status and verifier;
- notes/unknowns.

DATA-001 will make this machine-readable.

---

## 5. Mandatory item-level provenance

Every downloaded external asset must be traceable to one source record and carry, directly or through a manifest:

- stable internal `asset_id`;
- source ID;
- source object/document identifier;
- canonical object/record URL;
- exact file URL when applicable;
- original filename;
- source license/rights class;
- rightsholder/creator/attribution;
- retrieval date;
- SHA-256 of original bytes;
- normalized/processed artifact hashes where produced;
- processing/transformation history;
- document/page/region relationship;
- benchmark-overlap status;
- allowed-use flags;
- release/redistribution flag;
- provenance reviewer/status.

If an image is cropped, converted, masked, normalized, or rendered from SVG, the derived record must retain a pointer to the original asset and the transformation recipe.

---

## 6. Data-admission gate

An asset may enter a **training/dev corpus** only when all checks pass:

- [ ] source identity is verified;
- [ ] exact item provenance is recorded;
- [ ] license/rightsholder is known;
- [ ] training use is allowed under project policy;
- [ ] any attribution/share-alike obligations are captured;
- [ ] source terms do not prohibit the acquisition method;
- [ ] original SHA-256 is recorded;
- [ ] object/document identity is recorded where available;
- [ ] benchmark exact-overlap check passes;
- [ ] benchmark perceptual/near-duplicate check passes when images are involved;
- [ ] asset is not sealed/evaluation-only material;
- [ ] proposed redistribution/release status is recorded;
- [ ] unresolved rights questions are empty or explicitly approved by the overseer.

Failure of any mandatory item means **do not admit**.

No agent may "temporarily" train on unapproved assets with the promise of cleaning provenance later.

---

## 7. Benchmark quarantine

### HieraticBench

All exact HieraticBench items, source crops, gold labels, commissioned sentence images, and derived near-duplicates are excluded from training/dev.

This applies even when:
- the original museum/Wikimedia image is CC0/CC BY;
- a sign is available independently in AKU-PAL;
- a model could legally train on that source outside this project.

The restriction is methodological: an external benchmark is only useful if we preserve independence.

### Same-source acquisition

The project may later use other material from a museum/database also represented in HieraticBench, but it must prove separation using:

- stable museum/object IDs;
- source URLs;
- original SHA-256;
- normalized SHA-256;
- perceptual hashes;
- document/page IDs;
- manual review for suspicious near-duplicates.

If uncertainty remains, quarantine the sample.

---

## 8. Current resource decisions

These decisions implement FND-004 findings and may be superseded only through a logged decision.

### HieraticBench

Class: **EVALUATION-ONLY**

- never training/dev;
- commissioned images respect their explicit evaluation-only permission;
- public images retain source licenses;
- raw model answers that could leak a sealed reading must remain private according to benchmark protocol.

### DDD

Class: **NONCOMMERCIAL + PER-ITEM complexity**

Zenodo states "CC 4.0 BY-SA-NC" and per-image copyright details exist in `papyri.json`.

Policy:
- do not place DDD in the default commercial-compatible training track;
- do not redistribute source imagery outside its terms;
- a research-only experiment may be proposed later after item-level manifest review;
- released weights trained on DDD require a separate rights decision.

### HPDB

Class: **OPEN-BY for the official datasets**, with image-layer provenance preserved.

Policy:
- metadata/concordance datasets may be used with CC BY 4.0 attribution;
- image/IIIF derivatives must preserve source and attribution;
- modification history must be recorded.

### AKU-PAL

Class: **PER-ITEM**

Official FAQ says individual images may be used under the license displayed for each image.

Policy:
- acquire only items whose explicit license satisfies the intended use;
- record the exact hieratogram stable ID and license;
- no assumption of one database-wide blanket image license;
- check against HieraticBench overlap before training.

### PaPYrus

Class: **RIGHTS-REVIEW**

- repository is GPL-3.0 and publication describes the dataset as free/open source;
- source facsimile provenance still matters;
- do not copy the corpus into the default training set until DATA-001 item/source manifests confirm compatibility.

### Isut

Class: **RIGHTS-REVIEW**

- software repository GPL-3.0;
- annotated backups may contain third-party facsimiles;
- do not infer image/data rights from software license.

### HieraticAI

Class: **RIGHTS-REVIEW**

- code MIT;
- Westcar/facsimile-derived dataset rights are not assumed to be MIT;
- model/code can be studied as prior art; dataset ingestion requires independent provenance clearance.

### TLA live website

Class: **RESTRICTED**

Official TLA terms allow individual academic quotation but prohibit copying entire subcorpora/larger sets (>10 pages) from the website.

Policy:
- no bulk scraping;
- no model-training corpus built by crawling the live site;
- use only a separately licensed raw-data release or explicit permission for bulk data;
- individual scholarly references/queries may still inform research within stated terms.

---

## 9. Repository storage policy

### Git-tracked by default

Allowed:
- provenance/source manifests;
- URLs and identifiers;
- checksums;
- scripts that acquire permitted data;
- small repository-authored fixtures;
- openly redistributable small assets when explicitly approved;
- derived statistics that do not reproduce restricted source content.

### Not Git-tracked by default

- raw external manuscript datasets;
- large image archives;
- restricted/non-commercial source assets;
- sealed benchmark material beyond what the benchmark's own repository exposes;
- model checkpoints;
- credentials/API keys;
- local caches.

Large/permitted artifacts should use an artifact store or reproducible acquisition pipeline with immutable hashes rather than ordinary Git.

---

## 10. Dataset release gate

Before publishing a Hieratic AI dataset release:

- every included asset must have a release-compatible rights status;
- attribution files must be generated from manifests;
- share-alike requirements must be satisfied;
- restricted/non-commercial assets must be excluded unless the release itself explicitly complies;
- source/derived hashes and transformation history must be preserved;
- benchmark-overlap checks must pass;
- a dataset card must state source composition, rights, exclusions, known gaps, and version.

If a dataset mixes incompatible release terms, split it into separately licensed components or release only acquisition scripts/manifests.

---

## 11. Model-training gate

Every experiment must point to an immutable dataset manifest/version.

The training launcher or experiment record must be able to answer:

- which source/item IDs were used;
- which rights classes were present;
- whether any NONCOMMERCIAL/RESTRICTED/EVALUATION-ONLY/UNKNOWN item was present;
- which benchmark-overlap scan version passed.

Default rule:

> A training run containing EVALUATION-ONLY or UNKNOWN material is invalid and must not be used for a reported project result.

A run containing NONCOMMERCIAL material must be explicitly labeled as a research-restricted track and may not silently become the default release model.

---

## 12. Model-release gate

Model weights are not automatically licensed because the training code is Apache-2.0.

Before publishing weights, record:

- training dataset versions;
- rights-class composition;
- third-party model/base-checkpoint license;
- whether any NC/SA/restricted source was used;
- intended-use/commercial-use status;
- model license;
- attribution/notice obligations;
- unresolved legal or provenance caveats.

If compatibility is unresolved, release code/configs/evaluation results while withholding weights until resolved.

---

## 13. Attribution and modifications

Attribution must be generated from canonical manifests, not hand-maintained prose.

When a license requires indication of modifications, transformations such as:
- crop;
- resize;
- binarization;
- contrast normalization;
- masking;
- vector rendering;
- augmentation used in published examples

must be described at the appropriate dataset/asset level.

Scientific provenance should be retained even for public-domain/CC0 assets.

---

## 14. Acquisition behavior for agents

Agents may:

- record metadata and links for a candidate source;
- download assets already classified as allowed when the assigned task authorizes acquisition;
- write acquisition scripts that enforce the manifest rules.

Agents must escalate when:

- license text conflicts across source pages;
- a license covers code but source data rights are unclear;
- terms of use constrain automated access;
- an item has no stable provenance;
- a source mixes licenses;
- NC/SA material could affect release strategy;
- a benchmark overlap is possible;
- model-weight release implications are unclear.

Agents must never infer "open" from:
- no login required;
- downloadable URL;
- GitHub hosting;
- IIIF availability;
- museum/public-institution ownership;
- age of the digitized photograph;
- a citation saying "open source" without a specific rights basis for the asset.

---

## 15. Enforcement roadmap

Effective immediately:
- this policy is mandatory for human and agent work;
- AGENTS.md points to it;
- unknown-rights assets are deny-by-default;
- HieraticBench is quarantined.

Upcoming machine enforcement:
- DATA-001: machine-readable source registry;
- DATA-002: acquisition manifests/scripts;
- CTRL-004: CI governance checks where appropriate;
- DATA-008: corpus-integrity and benchmark-overlap gates.

The policy is considered **operational now** even though automation will strengthen enforcement later.

---

## 16. FND-005 acceptance decision

### Criterion 1
> Code licensing is distinguished from dataset/image/edition/model licenses.

**Satisfied.** Sections 1–3 and resource decisions explicitly separate software, publication, data/image, benchmark, and model-weight rights.

### Criterion 2
> Redistribution rules and provenance fields are enforceable.

**Satisfied.** Sections 4–15 define mandatory source/item fields, admission gates, benchmark quarantine, dataset/model release gates, and deny-by-default behavior that agents must follow.

### Criterion 3
> No ambiguous third-party assets are silently committed.

**Satisfied.** UNKNOWN/RIGHTS-REVIEW assets are metadata-only by default; raw external assets are non-Git by default; AGENTS.md now requires escalation.

**Verdict: FND-005 VALIDATED.**
