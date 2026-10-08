# R-020 — Fifteen-item real Hieratic first-pair acquisition and rights feasibility

**Date:** 2026-10-08. **Status:** completed *public primary-source and methodological* investigation; first real image + expert diplomatic line pair remains **NOT ACQUIRED / NOT AUTHORIZED FOR CORPUS ADMISSION**.
**Program:** Hieratic-AI overseer, separate from Luna DATA-008 and Gemini VLM-001 PR remediation.
**Outputs:** [Machine-readable 15-object dossiers](R020_OBJECT_SPECIFIC_FIRST_PAIR_EVIDENCE.json), [unsent outreach packets](R020_OWNER_READY_INQUIRIES_UNSENT.md), [G0–G8 acquisition decision and evidence protocol](R020_ACQUISITION_GATE_CHECKLIST.md).
**Predecessors:** R-016 initial 15 catalogue candidates, R-017 266-public benchmark metadata census, R-018 institutional review, R-019 rigorous real-pilot protocol.
**Research boundaries:** no user account or institutional registration used; no original image, scan, full transcription or sealed benchmark answer downloaded; no contact sent; no institutional rights signature, legal advice or independent source clearance purported.

## Executive decision

For the **first legitimate image–diplomatic-reading line pair**, use **two parallel authorization pathways**—not one merged “open dataset” claim:

**A: Turin Papyrus Online Platform (TPOP), item Cat.1896:** seek a rights-holder/editor-approved, side+writing+line-addressable **existing scholarly diplomatic transliteration** with its exact matching TPOP CC0 original image/exposure. This route maximizes potential specialist expertise already associated with the document, but the platform's **image licence does not license the editors' database content**. A short administrative verso writing may make a reasonable first *inquiry*, but actual complete line legibility, alignment, transcription export and scholarly textual permissions are **unverified**.

**B: Metropolitan Museum object 561345 / accession 09.184.703, and reserve 561392 / 09.184.751:** use eligible Met **CC0 original image** if its exact file and public-domain status are independently verified, then commission **original, reviewer-authored** diplomatic transcription and image-line alignment under a separate written, purpose-specific licence. The object text descriptions mention an official visit or torches; these are **catalogue summaries**, not gold.

**Defer TPOP Cat.1966 joined “Turin Love Songs”, Cat.2083/178 multi-fragment complex and famous Cat.1880 Strike Papyrus** from first-pair claims, for complex manuscript/writing joins and/or elevated contamination. Maintain catalogued options for later properly isolated research.

**No first-pair GO is possible from public pages alone.** The current project still needs the exact image bytes/hashes, approved annotations/edition reuse, physical support and source independence, and a qualified Egyptologist review. For science, **one** genuine pair demonstrates **data engineering continuity only**, not a train/dev/test corpus or VLM skill.

## 1. New verified institutional and access facts

### TPOP: precise boundary between photos and scholarly text

Official [access/use policy](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/Policy-on-access-and-publication-of-papyri/) explicitly says photos **provided by the TPOP database** can be used under **CC0**, while cooperation-partner PDF publications are **CC BY-NC** (registered additional PDFs may differ). Textual information is authored by **named editors at the writing level**; some research is from ongoing theses. TPOP's request that editors be credited is a **citation requirement**, **not a broad machine-learning sublicence or CC0 grant to their editorial content**. Authentication is personal and must never be shared, scraped or reused through someone else's credentials.

The official [accessibility guide](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/What-is-accessible-for-whom-/), updated **27 June 2026**, says nonregistered visitors see approximately **130 papyri** including **80 Hieratic manuscripts**, with descriptions and *sometimes* transliteration, translation or hieroglyphs. A registered workspace covers **more than 12,050 entries** (fragments and assembled documents), not >12,050 independently rights-cleared gold pairs. Additional photos/editorial fields may require approved personal registration. A different official [access explanation](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/What-are-you-looking-for/) mentions individual private image-position comments and extra registered transcriptions, but does **not** promise bulk machine-readable image-line coordinates, export rights, or a reproducible research-licence contract.

**High-value R-020 finding:** the [Cat.1896 museum entry](https://collezionepapiri.museoegizio.it/en-GB/document/259/) separately describes a **recto royal decree**, **verso text I (address)**, **verso text II (bread ration administrative record)** and **non-text drawings**. Editors/contributors differ by writing: Jill Raimondo, Danja Zimmermann, Vera Allen and Juan José Archidona Ramírez are credited. Recto points to Ramses Online **ID 1066**; the two verso writings explicitly say the text is not previously known in literature. Some partial translations appear, not an exposed independently authorized diplomatic full-line data release.

**Technical request:** for **one selected actual verso or recto line**, ask for exact support/accession → side → writing ID → line number → source exposure/file/IIIF ID → original pixel version → diplomatic readings and uncertainty → editor identity → edition revision; a separate evidence-backed licence to train, validate and distribute (and where required permit commercial use, derivatives and future checkpoint release). No “exposed translation” should stand in for diplomatic transliteration.

### Met: real unrestricted eligible image policy, but no ready gold

The [official Open Access policy](https://www.metmuseum.org/hubs/open-access) states eligible public-domain original artwork images and basic data are **CC0, reusable without permission**; the [official API documentation](https://metmuseum.github.io/) defines `GET /public/collection/v1/objects/{objectID}` fields including `isPublicDomain`, `primaryImage`, `primaryImageSmall` and `additionalImages`, and says API keys are not required. It notes **new paginated search v1.1 introduced 4 September 2026** and v1 search deprecated for **1 October 2026**; object-detail endpoint remains v1. One must query **object details**, not rely on old search v1 pagination.

The nine candidate museum pages individually display **Public Domain** with accession/medium, and many provide “Download Image”. The research browser **could not retrieve raw object-detail JSON** from `collectionapi.metmuseum.org` for the four attempted candidate URLs (561345/561392/561410/561413): this is an access/tool limitation, **not** evidence that the API or images are unavailable generally. **No `isPublicDomain=true` JSON response, `primaryImage` URL, high-res original JPEG, original hash, pixel dimensions, orientation or image-rights receipt was actually validated here**. No museum original photos were downloaded into the repository.

The [Met 561345 / 09.184.703 page](https://www.metmuseum.org/art/collection/search/561345) documents an inscription mentioning an official visit to the royal necropolis; [561392 / 09.184.751](https://www.metmuseum.org/art/collection/search/561392) describes lamp/torch notes and displays **two image views**; [561361 / 09.184.720](https://www.metmuseum.org/art/collection/search/561361) describes a list of workmen's names. These are **subject annotations**, not readable line-level text, sign sequences or transliterations, and **cannot be copied into gold annotations as substitute answers**.

The Met original-image path potentially requires no additional CC0 permission if confirmed for the exact file, but **source-image equivalence, original text attribution, an independent scientific gold licence and source-lineage isolation still do require evidence**. An inquiry to `openaccess@metmuseum.org` is for accession/photography metadata and item-image terms, not an invented requirement that Met must license CC0 anew.

## 2. Source-specific first-pair dossiers and ordered admission queue

The machine-readable [R-020 object matrix](R020_OBJECT_SPECIFIC_FIRST_PAIR_EVIDENCE.json) contains a **separate record for each of all 15 R-016 candidates**. In all fifteen, actual image hash is null, editorial copyright/annotation use unverified, image alignment unverified, public benchmark string match count zero but real contamination unresolved, and **corpus admission BLOCKED**.

| Candidate | Confirmed source details | First-pair decision / extra question |
|---|---|---|
| **TPOP-1896** Cat.1896 | [Museum object 259](https://collezionepapiri.museoegizio.it/en-GB/document/259/): royal decree, distinct verso address and bread record; four named scholarly contributors | **A1 permission inquiry** for one exact writing/line, image file ID, side, editor-authorized diplomatic transcription and rights |
| **TPOP-1971** Cat.1971 | [Museum object 216](https://collezionepapiri.museoegizio.it/en-GB/document/216/): Butehamun letter; Ramses **ID 112**; related source Cat.2026 | **A2 editorial route**; prove textual witness, editorial rightsholder, related-letter distinction and recto/verso alignment |
| **TPOP-1966** Cat.1966 joined CP124/001–008 | [Museum object 250](https://collezionepapiri.museoegizio.it/en-GB/document/250/): literary + administrative writings, at least nine named joined pieces; Ramses **ID 859** | **Later only**; treat joined physical fragments as one source, writing contexts separately, published editions/licences separately |
| **TPOP-2021** Cat.2021 | [Museum object 511](https://collezionepapiri.museoegizio.it/en-GB/document/511): priest's legal statement and verso letter; multiple published editions | **Later**; independently verify attribution, edition reuse and versioned target writing |
| **TPOP-NECROPOLIS-5** Cat.2083/178 and others | [Museum object 5](https://collezionepapiri.museoegizio.it/en-GB/document/5/): **16 accession fragments joined** with many Martina Landrino-authored writings | **Defer** until joined fragments have a single source support ID and written scholarly permission |
| **TPOP-1880** Cat.1880 | [Museum object 131](https://collezionepapiri.museoegizio.it/en-GB/document/131): publicized Strike Papyrus; Ramses **ID 453** | **High-prior-exposure defer**. Famous text and extensive edition/prompt contamination remain a serious confound |
| **MET-561345** 09.184.703 | [Met object](https://www.metmuseum.org/art/collection/search/561345): Hieratic official visit, limestone ink, Public Domain | **B1 first new-gold fallback**; acquire eligible exact CC0 image via official API and commission blinded original reading |
| **MET-561392** 09.184.751 | [Met object](https://www.metmuseum.org/art/collection/search/561392): torch/lamp notes, two views, limestone ink/paint | **B1 two-view reserve**; source image view/side identity must be retained |
| **MET-561361** 09.184.720 | [Met object](https://www.metmuseum.org/art/collection/search/561361): workmen's names, limestone | **B2**; proper-name palaeography and normalization error risks |
| **MET-561391** 09.184.750 | [Met object](https://www.metmuseum.org/art/collection/search/561391): incomplete lines | **B2 damage/uncertainty stress test**, not an easy reference gold candidate |
| **MET-561407** 09.184.766 | [Met object](https://www.metmuseum.org/art/collection/search/561407): smaller limestone | **B2**; inspect original legibility and exact transcription viability first |
| **MET-561409** 09.184.768 | [Met object](https://www.metmuseum.org/art/collection/search/561409): small limestone | **B2**; exact image legibility and scholarly reading unknown |
| **MET-561410** 09.184.769 | [Met object](https://www.metmuseum.org/art/collection/search/561410): pottery ink/paint | **B1 medium diversification** after first limestone pair; source orientation needed |
| **MET-561413** 09.184.772 | [Met object](https://www.metmuseum.org/art/collection/search/561413): pottery, two image views | **B1 reserve**, exact views and image-copy IDs separately hashed |
| **MET-561621** 14.1.453 | [Met object](https://www.metmuseum.org/art/collection/search/561621): “literary text?” including museum question mark | **B3**; no assumption of literary genre or correctly identified text |

**Important caveats on counting:** The 9 Met ostraca share some `09.184.*` excavation/accession prefix, but this **does not make them the same manuscript**. Conversely, different accession prefixes or image files do **not** prove independence. Check original supports, textual witness and source aliases. Turin Cat.1966 and joined Necropolis Journals must never inflate document count by counting fragments as separate manuscripts.

## 3. Rights and evidence packet for *one actual chosen line*

A usable submission must bind the following **distinct components**, each with documented evidence status:

| Layer | Required record | Actual R-020 state |
|---|---|---|
| Museum original photo | Specific institution inventory + image file/IIIF/exposure/side, exact pixel hash, original file bytes, applicable item policy | **MISSING** |
| Copyright / rightsholder | TPOP-provided CC0 image or Met eligible OA original plus captured policy and possible item-level exceptions | **Policy known; exact item-file proof not complete** |
| Diplomatic Egyptian reading | Source-linked written sign/word/line reading; independent scholarly editor version and retained ambiguities | **MISSING** |
| Editorial text reuse | Distinct author/editor grant if reusing edited source; purpose-specific ML, redistribution and model derivation rights | **MISSING** |
| Independently authored gold | Qualified Egyptologist original annotation, explicit IP agreement, second independent review/adjudication | **MISSING** |
| Spatial alignment | Original image coordinate space and line/polygon ID, orientation and page/recto-verso mapping | **MISSING** |
| Corpus contamination review | Pinned 266-public source register, alias+edition+same-support+actual image perceptual checks, controlled holdout | **Only public accession-string negative, not clearance** |
| Scientific readiness | Multiple independent documents with held-out groups, reproducible actual VLM inference, appropriate uncertainty | **NOT STARTED** |

**Caution:** externally published descriptions of texts, existing hieroglyphic representations and English/French translations do not establish diplomatic line readings. Licensed images are not automatically licensed scholarly text. “CC0 image from museum” is a strong image starting point, not total corpus admission.

## 4. Proposed evidence-bound acquisition sequence

**Pre-outreach / metadata-only phase (completed R-020):** freeze the 15 records and their exact public URLs; record 266 public benchmark accession/URL exclusions; identify museums, writers and known published references; classify the state of each legal/data layer as **observed policy**, **catalogue assertion**, **inference** or **unverified**. No invented original image URLs.

**Owner-authorized institutional inquiry (NOT SENT):** use [four tailored requests](R020_OWNER_READY_INQUIRIES_UNSENT.md)—TPOP photos and editorial export together, Met photography identity, Egyptologist collaboration, and optional Ramses/TLA scholarly text—as distinct ownership/permission threads. A policy already declaring CC0 images does not require contacting a museum just to ask to reproduce its CC0 photographs; institutional contacts can clarify original-asset identities, side mapping or off-platform annotations.

**First permitted acquisition (NOT EXECUTED):** obtain **one** source-specific file only through a permitted official route (TPOP public published CC0 display or verified Met OA eligible original), check actual source, format/dimensions/image SHA-256, accession and side, record date/policy snapshot. Keep bytes out of public Git until actual policy and storage decisions are independently checked. No bulk downloads or registered-user scraping.

**Expert gold (NOT EXECUTED):** either receive versioned/editor-cleared original diplomatic line text with editorial rights and attribution (TPOP), **or** have qualified Egyptologists independently transcribe the actual Met visual strokes and sign the contribution licence. Blind independent review must track disagreements/alternatives, damaged marks, signs and geometry; a single editor or visually plausible AI answer is insufficient.

**Integrity-only release proof (NOT EXECUTED):** feed one pair through validated DATA-008 once the externally authenticated trust root is established, and label it **data continuity only**, not model accuracy or ML-ready corpus. Current Luna PR #63 correctly keeps empty production trust anchors but requires stronger protected trust-root and separate scholarly attestation before any release.

**Scientific experiment (NOT EXECUTED):** recruit more source-disjoint licensed expert gold, preregister train/dev/test by physical support/manuscript, construct real image-conditioned zero-shot VLM evaluation and complete externally anchored denominator audit. Gemini PR #52 still requires externally verifiable cohort admission and scientific certification; synthetic green CI is irrelevant to real model skill.

## 5. Source overlap and scientific contamination boundaries

R-017 read **266/266 public item source identities** at `alymoursy/hieraticbench@d587dc990013f18007f1e7a8f56f96ff2f7127e2`, excluding two sealed records and never copying gold or benchmark images. The [15-candidate crosswalk](R017_R016_CANDIDATE_SOURCE_CROSSWALK.json) finds **zero literal exact public source match**. This only supports “no matching accession string found,” not “unique unseen handwriting”: image/photo reproduction, renumbered accession, edition, source text, other sign facsimiles, scribe, model pretraining exposure and hidden benchmark examples remain unresolved. All **15/15** require **BLOCKED** release/training/few-shot gates.

**Specific falsification cases** for the future independent reviewer:
1. A Cat.1896 image shares publication facsimile with a different accession or AKU sign support; no literal match yet same manuscript.
2. Met original image 561345 is mirrored/rescaled/cropped on another public site; different bytes yet same source.
3. TPOP Cat.1966 joined CP124 fragments get assigned different partitions.
4. Same published line gold copied from an edition already exposed to VLM prompt/few-shot.
5. The Met 09.184 acquisition-prefix family erroneously collapsed as “same manuscript” without true object joins; do not overblock merely for acquisition context.
6. A benchmark update adds an original acquired during this pilot; maintain versioned quarantine and retroactive report of conflict.
7. A famous Strike Papyrus text is easy for a foundation VLM because it memorized a published edition; cannot claim unseen visual reading without image-conditioned controls and truly independent holdout.

## 6. Owner-actionable decision package

**Request 1 to authorize later:** Identify whether Hieratic-AI public code, eventual training corpus **and model weights** must all be distributable for commercial use, or if a strictly isolated noncommercial scholarly track is acceptable. Until resolved, *do not mix NC materials into an unrestricted model-training corpus*.

**Request 2:** Approve or decline sending the exact unsent museum/editor requests. No outreach has been initiated. Museum recipient and rights-holder decision must be recognized; contacting one custodian does not waive the editor's separate rights.

**Request 3:** Confirm qualified independent Egyptologist(s), reviewer/adjudicator and legal terms for newly authored readings; staffing and funding are unknown.

**Request 4:** Establish independently controlled authority bootstrap for corpus admissions (outside the candidate/applicant writable trust store), approved protected original asset storage, and versioned evidence custody.

**Request 5:** Permit item-specific technical acquisition of original CC0 images only after the above governance and purpose-specific intended-use decisions; verify actual bytes and hashes without publishing them prematurely.

### No-go conditions and precise next milestone

**Current state = METADATA-ONLY BLOCKED.** No item-specific image bytes, fully licensed editorial line text, independently authored/approved gold, confirmed spatial alignment, external trust root or source-disjoint holdout exists. **No first pair** has been achieved. The next legitimate advancement is **an authorized, exact-museum-image-and-expert-diplomatic-line pair with independently verifiable rights and lineage**, not a claimed amount of corpus or accuracy.

### Evidence and reproducibility limits

Every object claim above is linked to an official institution catalogue entry; every general policy claim links to its institution's official policy/API. Object API raw responses were not retrieved, and no actual photography/transcription byte hashes were computed. R-020 does not cite external article text as a legal opinion or silently extend CC0 to edited scholarly content.

**Capability:** 32.5/100, research coverage 14% as last canonically recorded, 0 trained models and 0 validated real model experiments; no new points awarded for this investigation.
