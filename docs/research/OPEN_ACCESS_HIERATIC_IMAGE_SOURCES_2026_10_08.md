# Open-access Hieratic image-source leads — primary-source audit

**Audit date:** 2026-10-08  
**Owner/lane:** Overseer — independent source-rights and acquisition strategy research  
**Evidence state:** PRIMARY SOURCE VERIFIED for institutional statements linked below; **NO INDIVIDUAL ASSET ADMITTED**  
**Scope:** Public, metadata-only reconnaissance. This is **not** rights clearance, permission to bulk scrape, creation of a training dataset, scholarly gold review, a scientific experiment, or progress credit. It complements rather than supersedes `eval/baselines/SOURCE_RIGHTS_READINESS.md` and `docs/governance/DATA_LICENSING_AND_PROVENANCE_POLICY.md`.

## Executive finding

The original DATA-001/FND-004 shortlist is not the only route to an *image-rights-compatible* Hieratic corpus. Two additional institutionally published CC0 programs merit a dedicated item-by-item pilot:

1. **Museo Egizio, Turin — Turin Papyrus Online Platform (TPOP) / collections:** public CC0 image-policy statement, a publicly searchable Hieratic collection and thousands of registered catalog entries. **Priority A for authentic papyrus imagery and potential image-to-transliteration research partnership**, subject to independent source/annotation rights, benchmark novelty and access permission.
2. **The Metropolitan Museum of Art Open Access:** CC0 public-domain image program and numerous **named, inspectable Hieratic ostraca**. **Priority B for manuscript/ostracon image diversity and eventual independent image pilot**, subject to `isPublicDomain` + actual image availability + quarantine verification for each object.

This resolves **part of the source-discovery problem**, not the production DATA-008 blocker: a full corpus still requires reviewed real image/text alignment, rights for labels and interpretations, clean document-separated train/dev/test partitions, full 268-item HieraticBench source/near-duplicate checks, and scholarly gold. In particular, **the benchmark already includes 37 Met items and 61 Wikimedia items** according to the accepted FND-004 registry. All candidate objects remain `candidate_only` until an independently checked exclusion list is available.

## 1. Museo Egizio: Turin Papyrus Online Platform

### Primary evidence

- Institutional reuse policy: https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/Policy-on-access-and-publication-of-papyri/
  - Site says images provided in the Turin Papyrus Online Database can be used under **CC0**.
  - **Partner-provided PDF files** are separately designated **CC BY-NC** (including Griffith Institute / Berlin-Brandenburg Academy materials). Do not generalize the image policy to these PDFs.
  - Additional PDFs for registered users can be CC0, but establish **per-file provenance/type** before any use.
  - Contributed text has named editors at the **writing** level; the policy asks users to credit those editors and exercise scientific respect. **It does not state that all digitized transliterations, transcriptions and translations are independently CC0 for bulk training/redistribution.** Label rights must be investigated separately.
  - The site states login credentials must not be shared.
- Collection scope and access: https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/What-is-accessible-for-whom-/
  - The museum states **about 130 publicly visible papyri**, of which **80 are Hieratic**; some public records include images and partial transliteration/hieroglyph/translation information.
  - The registered TPOP catalog states **more than 12,050 Hieratic papyri** (fragments and assembled documents). This is **not** the number of training-ready image/text pairs, unique complete documents, rights-reviewed records, or independently transcribed items.
  - Registration provides deeper access including unpublished images and ongoing Egyptological transliterations. Restricted access is a setup dependency; **do not bypass registration, use another person's credentials, or assume automated bulk ingestion is permitted**.
- Search guidance: https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/What-are-you-looking-for/
  - Museum describes searching by **script = hieratic**, provenance, inventory number and text type.
  - Registered access exposes more transcriptions/transliterations, but this is a discovery promise, **not a grant for extraction and model training**.
- Example identified from the *actual institution*, not invented:
  - **Turin Strike Papyrus, Cat.1880**, https://collezionepapiri.museoegizio.it/en-GB/document/131 — a named Hieratic manuscript with writing recto/verso, repeated writing/editor attributions, hieroglyph-rendering references, and bibliographic identifiers.
  - Its English translation is labelled **in preparation**; do not manufacture translation gold from the explanatory museum narrative or infer an aligned transcription from an image icon.
  - This well-known manuscript is a high benchmark/source-lineage overlap *risk*: do not admit it to training or few-shot demos without explicit independent non-overlap review.
- Museum's general collection site separately affirms that its collection images are CC0: https://collezioni.museoegizio.it/en-GB
- Museum's photo-archive policy releases its own eligible photographic-archive reproductions as CC0; **third-party/state archive images may differ**: https://archiviofotografico.museoegizio.it/en/section/How-to-use-the-Archive/Policy-on-access-and-use
- Institutional papyrus contact on the official policy/access pages: **collezione.papiri@museoegizio.it**. No inquiry has been sent by the project.

### Scope separation and proposed treatment

| Asset layer | What the institution explicitly says | Project handling now |
|---|---|---|
| TPOP images identified as museum-supplied images | CC0 reuse declaration | **OPEN-PD candidate at policy level**; item ID, actual original image bytes and license/source confirmation still necessary |
| Partner PDFs (including facsimile notebooks) | CC BY-NC | **NONCOMMERCIAL / separate-source review**; do not mix into unrestricted corpus |
| Other PDFs supplied to registered users | Some designated CC0 | **PER-FILE review**; no blanket assumption |
| Transliterations, transcriptions, translations and editorial annotations | Editor credit and scholarly attribution specified; blanket commercial ML/redistribution rights not demonstrated | **TEXT RIGHTS UNKNOWN**; metadata-only until specific permission/terms established |
| Nonpublic registered content | Researcher registration needed; catalog access varies | **ACCESS-DEPENDENT**; do not bypass login or automate extraction without allowed terms |
| Full manuscript gold and sentence alignment | May be partial or absent for a given writing; example Cat.1880 lacks English translation | **GOLD NOT VERIFIED**, needs expert review and exact spans |

**High-value next inquiry:** Can TPOP offer a permitted *structured* export of selected Hieratic document/write-layer IDs, approved page images, line-level transliteration/hieroglyphic representations and author attributions for research, model training, public dataset publication and possible weight release? Are there terms/API limitations distinct from CC0 image reuse? Prefer a small rights-reviewed subset to a speculative 12k-item bulk download.

## 2. Metropolitan Museum of Art — Open Access and Egyptian ostraca

### Primary evidence

- Institutional CC0 program announcement: https://www.metmuseum.org/press-releases/open-access-2017-news
- Technical API specification: https://metmuseum.github.io/
  - The Met provides CC0 collection metadata and public-domain images. The item endpoint is `GET /public/collection/v1/objects/{objectID}`.
  - Records expose `isPublicDomain`, `primaryImage`, `primaryImageSmall`, `additionalImages`, `accessionNumber`, `objectURL`, provenance fields, etc.
  - A CC0 metadata record is **not proof of a downloadable cleared image**; require `isPublicDomain == true` **and** a real nonempty image URL, then inspect the image's provenance/terms.
  - Direct endpoint JSON for the examples below was *not* successfully fetched in this web research pass; their **museum HTML catalog pages**, where marked Public Domain, are the available item evidence. The eventual item-reviewer must cross-verify actual API JSON and bytes.
- Named candidate museum pages:
  - **19.3.31**, image explicitly labelled **Public Domain**, catalogue object 545594: https://www.metmuseum.org/art/collection/search/545594
  - **09.184.703**, image explicitly labelled **Public Domain**, catalogue object 561345: https://www.metmuseum.org/art/collection/search/561345
  - **09.184.751**, image explicitly labelled **Public Domain**, catalogue object 561392: https://www.metmuseum.org/art/collection/search/561392
  - **09.184.750**, image explicitly labelled **Public Domain**, catalogue object 561391: https://www.metmuseum.org/art/collection/search/561391
  - **09.184.710**, Hieratic ostracon with recorded workmen absences, catalogue object 561351: https://www.metmuseum.org/art/collection/search/561351 — **image/public-domain flag not independently checked on the page excerpt; not cleared.**
  - **09.184.744**, single incomplete, described as unintelligible Hieratic line, catalogue object 561385: https://www.metmuseum.org/art/collection/search/561385 — **not suitable for invented transcription gold**.

### Model/data relevance and limitations

- Strong **real handwriting diversity** across limestone ostraca; partial/faded lines are useful for future detection, illegibility and abstention studies, **provided** independent line labels exist.
- Museum catalog descriptions often paraphrase contents ("notes about lamps", "visits by officials") but they **are not** verbatim diplomatic transliteration, sign annotation or alignments. Do not turn a descriptive sentence into ground truth.
- Met object identity, image hash, accession, original image license and rights history must be preserved before any derivative crop generation.
- Since HieraticBench contains **37 Met object items**, an accession/object-ID comparison alone is necessary but **not sufficient**. Check exact bytes and near-duplicates, different museum photos of the same object, other published reproductions and overlapping pages.
- A sample of six named item pages is **not a sampled count of eligible training images**, and no claim of a production-sized public-domain Hieratic corpus follows.

## 3. Commons derivatives — lower-priority, high-overlap source

- Discovery entry: https://commons.wikimedia.org/wiki/Category:Hieratic
- Hieratic items have **file-specific licenses** ranging from CC0 to CC BY-SA and others; category membership is not a license grant.
- Museum-provided CC0 examples of Turin manuscript images appear on Commons, e.g. a strike-papyrus image (museum attribution and original object still must be pinned):
  https://commons.wikimedia.org/wiki/File:The_so-called_%27Strike_Papyrus%27_written_by_Amunnakht_-_Museo_Egizio_Turin_C_1880_p01.jpg
- An unrelated Petrie Museum Hieratic ostracon file uses **CC BY-SA 3.0**, not CC0:
  https://commons.wikimedia.org/wiki/File:Petrie_Museum_hieratic_ostracon.jpg
- Since 61 Wikimedia images are already in HieraticBench, Commons is **high-risk for contamination**. Prefer museum-original sources, immutable archive IDs, evidence of license, and independent near-duplicate screening. Reuploading/renaming an evaluation image does not make it independent.

## 4. Proposed pre-admission algorithm (documentation, not an authorized data import)

1. **Discovery only:** enumerate museum identifiers/search results and evidence URLs without downloading source image bytes or copyrighted labels. Distinguish full manuscript, face, writing, crop, photo exposure and annotated witness identities.
2. **Rights ledger:** for each candidate, preserve institution/source URL, immutable accession/inventory/writing ID, license URL/text, copyright holder, creator, access limits, image permissions, annotation/transcription/translation rights, intended commercial/noncommercial model use, derivatives, redistribution and weight-release review.
3. **Access method:** confirm allowed API/record-fetch paths and rate/registration terms. Do not assume CC0 copyright status automatically authorizes unrestricted automated bulk access or website terms bypass.
4. **Item review:** review each real asset's license/metadata, not only the collection header. Keep the official rights text snapshot hash in an independent external evidence store if permitted.
5. **Quarantine first:** check all candidate IDs, accession aliases, source editions and manuscript/page lineage against the pinned HieraticBench **268-item** roster and its known near-duplicates, plus EVAL-004 split/review data. If any source object is a benchmark match or overlap cannot be cleared, exclude from training and few-shot demonstrations.
6. **Only then** acquire approved images into external, permission-compliant, immutable storage with SHA-256 and acquisition logs; do not commit raw rights-controlled assets to Git.
7. **Separate gold:** expert-validated diplomatic transcript, sign IDs, hieroglyphic rendering, transliteration, normalized text, translation, uncertainty and editor permissions must be documented separately; a catalog synopsis is not model gold.
8. **Split by document/source/scribe**, not by random crops; require nonempty genuine train/dev/test sets and independent near-duplicate review per EVAL-004.
9. **Admission requires overseer/expert evidence review** of licenses, benchmark isolation and gold; use DATA-008's release machinery afterward. No release gate is overridden by this note.

### Recommended staged target

- **A. Image-only discovery:** prepare a 10–20 item candidate **metadata** roster (not an acquired dataset) sampling Turin public access and Met distinct object IDs; score image availability, public CC0 status, possible paired text, period and overlap risk. One well-reviewed document beats dozens of unverified links.
- **B. Scholarly contact:** prepare an institutional request to TPOP about rights/structured text export and approved automatic access, **without sending it or accessing registered content** until authorized and credentials are present.
- **C. Pilot annotation:** for first independently cleared, non-benchmark images, have qualified Egyptologists establish line/sign/transliteration gold with ambiguity and provenance. This will be new scholarly work, not copied unlicensed text.
- **D. Production dataset:** proceed only after rights-cleared multi-document, expert-reviewed gold and leakage-free splits; accept DATA-008's remaining three points only when its canonical task acceptance is genuinely met.

## 5. Proposed TPOP research inquiry — not sent

**To:** collezione.papiri@museoegizio.it  
**Subject:** Research collaboration and licensing clarification — Hieratic image/transliteration alignment

We are developing an evidence-driven, reproducible Hieratic handwriting research project. We have read TPOP's CC0 image reuse policy and its separate treatment of partner PDFs and scholar-authored text layers. We would appreciate clarification on whether any selected Hieratic manuscript images and editor-attributed transliterations/transcriptions can be supplied through an authorized structured export for machine-learning research.

In particular, could you advise on (1) allowed automated access/registration; (2) permissions and required attribution for editor-authored text, line alignment and potential publication of annotated derivatives; (3) suitability of research/commercial-compatible model training and public model-weight release; (4) stable inventory/writing/image identifiers; and (5) whether an appropriately licensed, small research subset or partnership is possible? We would keep benchmark content separate, preserve all item/editor provenance and avoid redistribution outside agreed terms.

This is an **unsent draft** only; no permission request, rights decision or data collection has occurred.

## 6. Nonclaims / acceptance boundary

- **No** CC0 label has been converted into blanket permission for external annotations or full catalog exports.
- **No** per-item image, model datum, gold label, data split, GPU model run or benchmark score has been created or checked into the repository.
- **No** real-corpus/data-release, LING-002, VLM-001 or EVAL-003 capability milestone is accepted by this research.
- **No** `PROJECT_STATE.yaml`, `TASKS.yaml`, `data/sources/registry.yaml`, `RESEARCH.md` research-coverage percentage or progress weight has been altered.
- **Research coverage remains 14.0%** until an explicitly reviewed denominator-based update.

**Source context:** Compare existing rights notes in `eval/baselines/SOURCE_RIGHTS_READINESS.md` and existing research registry `docs/research/PRIOR_ART_AND_DATA_REGISTRY.md` before treating any candidate as novel.
