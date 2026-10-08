# R-016 — First real Hieratic image–transliteration gold: evidence-based acquisition feasibility

**As-of:** 2026-10-08  
**Research owner:** Overseer, parallel W4 lane (disjoint from LING-002 and VLM-001)  
**Evidence status:** Institution-level reuse policies and catalogue metadata verified against primary sources; public benchmark *source metadata* screened at pinned commit. No item-level dataset admission, no licensed gold, no model runs.  
**Associated metadata roster:** `docs/research/R016_PRELIMINARY_CANDIDATE_ROSTER.yaml`  
**Context:** R-015 `docs/research/OPEN_ACCESS_HIERATIC_IMAGE_SOURCES_2026_10_08.md`; FND-005 policy `docs/governance/DATA_LICENSING_AND_PROVENANCE_POLICY.md`; rights audit `eval/baselines/SOURCE_RIGHTS_READINESS.md`.

## Decision-ready conclusion

**Best path to authentic paired training material:** Approach **Museo Egizio / Turin Papyrus Online Platform (TPOP)** for permission to export a **small, independently benchmark-separated, line-addressable** set of its Hieratic photos **and** editor-attributed scholarly readings (transliteration/hieroglyphic transcription/uncertainty). Images have an explicit CC0 policy; **scholarly text permissions, structured alignment, access terms and exact derivative/model use are not established**. This is a concrete expert-gold *partnership* route, not a cleared dataset.

**Independent fallback:** The **Met Open Access** has attributable, museum-identified Hieratic ostraca labelled **Public Domain**, offering potential permissive **image** inputs. Their museum descriptive captions are not aligned diplomatic transcripts. Commission independent, rights-assigned Egyptological annotation under a defined agreement and avoid reusing externally licensed translations/editions. This route is scientifically credible but requires real Egyptologist availability and item-level acceptance. Neither access nor expert review has happened.

**Research-only auxiliary:** DDD at Zenodo has annotated sign polygons but is subject to **noncommercial/share-alike and per-image conditions**; it does not unblock default commercial-compatible corpus v1 or solve full-line Hieratic reading. Do not silently incorporate it.

These routes can eventually unlock DATA-008's **3** still-unearned points and the dependent specialist reading stages; this research itself **earns zero**. Acceptance will remain conditional on legitimate copyright/access provenance, real pixels, gold, and document-level leakage-proof partitions.

## 1. Institutional primary-source audit

### Museo Egizio / TPOP

- **Images:** Official [Policy on access and use](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/Policy-on-access-and-publication-of-papyri/) explicitly allows images provided by the Turin Papyrus Online Database under **CC0**. The *same policy* separately labels partner PDF files **CC BY-NC**, some registered-user PDF uploads CC0, and requires crediting editors at each **writing** level. Editor authorship and scientific credit **do not amount to blanket permission** to machine-extract, redistribute, commercially train on, or sublicense every editorial transcription/translation.
- **Scale—not aligned-pair count:** Official [public vs registered access page](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/What-is-accessible-for-whom-/) reports ~**80 public Hieratic papyri** and **more than 12,050 registered Hieratic entries**, including fragments and reconstructed documents. The higher number is not images ready for public redistribution, unique complete manuscripts, transcribed pages, available line pairs, or permission to bulk crawl. Nonregistered pages may have high-resolution photos and *sometimes* transliteration, translation or hieroglyphic rendering.
- **Registered content:** Registration is required for many entries; credentials cannot be shared. Do not programmatically scrape restricted records or assume research access permits collection/model training. Site changes over time.
- **Stable object/writing structures:** Public catalogue pages expose inventory numbers, recto/verso and often per-text editorial provenance. **Writing, physical fragment, assembled manuscript, photo exposure and textual witness are distinct identities** that must be kept separate.
- **Permission contact (not contacted):** `collezione.papiri@museoegizio.it` (on official policy page).

### Met Open Access

- The [Met Open Access hub](https://www.metmuseum.org/hubs/open-access) and [Met terms](https://www.metmuseum.org/policies/terms-and-conditions) identify eligible OA images as **CC0**, including commercial and noncommercial uses, with source attribution encouraged and trademark/endoresement rights separate.
- The [official API documentation](https://metmuseum.github.io/) defines `objectID`, `accessionNumber`, `isPublicDomain`, `primaryImage`, `additionalImages`, `objectURL` and related provenance. An image is **not established usable just because an object appears in a CC0 metadata database**: confirm OA/public-domain status on the *specific object* and a nonempty image URL/actual pixels, including additional images for recto/verso.
- **Verification limit:** The Met individual JSON API endpoint returned inaccessible from the public research browser during this audit. Individual museum **catalogue HTML pages** listed below displayed “Public Domain”; this research **did not independently verify actual API JSON, source-image bytes, cryptographic checksums, or download terms per image**.
- Museum metadata often provides historical *synopses* (e.g. workmen's names, torches, official visits) but these **are not literal line-level diplomatic transcriptions, sign bounding boxes or transliterated gold**.
- **Contact (not contacted):** `openaccess@metmuseum.org` (museum's official Open Access hub/API docs).

## 2. Exactly 15 externally grounded candidate records

These entries are **metadata discovery candidates only**, not authorizations to acquire and train, scientifically representative samples, or confirmed benchmark-disjoint data.

**A — Turin partnership / potential editorial pairing** (script verified as Hieratic on the individual pages):

| ID | Stable institutional record | What makes it useful | Pair-readiness / risk |
|---|---|---|---|
| TPOP-1896 | [Cat. 1896, royal decree, recto + multiple verso writings](https://collezionepapiri.museoegizio.it/en-GB/document/259/) | Hieratic royal letter, verso administrative ration notes, writing-level editors, illustrated hieroglyph rendering and fragments of *English translation* | **A1** rich multi-layer candidate, but editorial text rights, exact written-sign alignment and photograph bytes unverified; public English translation is *partial*, not complete gold |
| TPOP-1971 | [Cat. 1971, Butehamun's letter to Djehutymes](https://collezionepapiri.museoegizio.it/en-GB/document/216/) | Two writing faces; script, editor credits, bibliographic / Ramses Online / TLA pointers; potentially addressable letter lines | **A2** potential independently citable transcription route. TLA/Ramses Online text terms are separately restricted/unverified; English translation marked in preparation |
| TPOP-1966 | [Cat. 1966 + CP124 fragments, Turin Love Songs](https://collezionepapiri.museoegizio.it/en-GB/document/250/) | Literary verses plus verso administrative texts; many writing segments and an editorially identified hieroglyph layer | **A3** useful diversity but joined-fragment lineage/genre mix raises alignment and split problems; English translation marked in preparation |
| TPOP-2021 | [Cat. 2021, priest's legal statement and court session](https://collezionepapiri.museoegizio.it/en-GB/document/511) | Administrative / legal text and different verso writing; editor names, substantive scholarly bibliography | **A4** interesting legal register, but no confirmed machine-readable aligned transcription and page evidence partially older |
| TPOP-NECROPOLIS-5 | [Necropolis Journals, assembled multi-fragment Cat.2083/178 et al.](https://collezionepapiri.museoegizio.it/en-GB/document/5/) | Repeated administrative accounts, explicit writing segmentation, editor Martina Landrino and multiple joining inventory IDs | **B1** high visual/text volume opportunity but **complex manuscript join/group identity**: cannot split fragments/faces of same reconstructed document between train/test |
| TPOP-1880 | [Cat.1880, Turin Strike Papyrus](https://collezionepapiri.museoegizio.it/en-GB/document/131) | Multiple independent writings and citations, editor-named, readily identifiable real Hieratic | **C / defer** famous, extensively published, probable prior exposure; no independent leakage proof; public English translation in preparation. Not the first training choice |

**B — Met's OA/public-domain Hieratic object records** (all individual HTML catalogues explicitly describe a Hieratic ostracon and display “Public Domain”; standalone digital transcriptions not established):

| ID | Museum object and accession | Distinctive information | Initial rank |
|---|---|---|---|
| MET-561345 | [561345 / 09.184.703](https://www.metmuseum.org/art/collection/search/561345) | Official visit mentioned in museum description, Ramesside limestone ostracon | **B1** image-only + independently authored gold |
| MET-561392 | [561392 / 09.184.751](https://www.metmuseum.org/art/collection/search/561392) | Lamps/torches accounts, ink/paint on limestone | **B1** independent administrative annotation candidate |
| MET-561361 | [561361 / 09.184.720](https://www.metmuseum.org/art/collection/search/561361) | Names of workmen, likely shorter nomenclature/onomastics context | **B1** specialized proper-name gold; do not infer literal names from synopsis |
| MET-561391 | [561391 / 09.184.750](https://www.metmuseum.org/art/collection/search/561391) | Several incomplete lines, limestone | **B2** good for uncertainty/illegibility, poor as a sole clean-gold benchmark |
| MET-561407 | [561407 / 09.184.766](https://www.metmuseum.org/art/collection/search/561407) | Small Ramesside ostracon, limestone | **B2** examine readable lines and image resolution |
| MET-561409 | [561409 / 09.184.768](https://www.metmuseum.org/art/collection/search/561409) | Very small ink/paint limestone ostracon | **B2** short, fragile text: potential sign/abstention annotation |
| MET-561410 | [561410 / 09.184.769](https://www.metmuseum.org/art/collection/search/561410) | **Pottery**, ink and paint, distinct from limestone set | **B1** useful writing-surface variation, provided image and reading are usable |
| MET-561413 | [561413 / 09.184.772](https://www.metmuseum.org/art/collection/search/561413) | Another **pottery** ostracon; museum page shows two views | **B1** evaluate photo-face identity and possible paired sides |
| MET-561621 | [561621 / 14.1.453](https://www.metmuseum.org/art/collection/search/561621) | Possible literary text; Deir el-Medina provenance uncertain | **B2** literary genre candidate; scholarly “?” in title means content/reading cannot be asserted |

**Caveats:** Availability of a “Download Image” control or OA/public-domain label is not a preserved image hash; date/dynasty labels have broad ranges. TPOP's image block and editorial attribution are not proof that full paired transliteration can be exported under a commercial-compatible licence. TPOP-NECROPOLIS-5 represents **one reconstructed document group**, not 16 independent samples. MET items from the same excavation are not necessarily different scribes.

## 3. Reproducible preliminary public-benchmark source check — important new evidence

**Pinned upstream revision:** `alymoursy/hieraticbench@d587dc990013f18007f1e7a8f56f96ff2f7127e2`, the project's accepted EVAL-002 benchmark reference.

**Method (performed):** Read the *public metadata* of exactly **37 `data/items/met-*.json`** and **61 `data/items/wm-*.json`** files at that pinned Git revision using the GitHub connector, considering only the item ID, `source.url`, and `object.name`. The content includes score-bearing data in the original file, but **none of that content was copied, displayed, included here, or used as corpus data**. No sealed `hb-*.json` or images were opened. Compare the institutional Met **numeric object IDs** and Turin **catalogue inventory names** in these 98 public-source records against the 15 institutional candidates.

**Observed result:** None of the **nine selected Met object-page IDs** is a direct `met-*` source object in the pinned benchmark's 37 Met records. None of the six selected TPOP source inventory IDs / document identifications was a *directly named match* within the 61 Wikimedia `wm-*` source titles/links. These are **exact metadata lookup negatives**, not proof of dataset eligibility or perceptual-image disjointness.

**Directly observed benchmark-owned examples to exclude from train/few-shot:**
- Met [545587 / 19.3.24](https://www.metmuseum.org/art/collection/search/545587): `met-0007`.
- Met [545588 / 19.3.25](https://www.metmuseum.org/art/collection/search/545588): `met-0008`.
- Met [545584 / 19.3.21](https://www.metmuseum.org/art/collection/search/545584): `met-0036`.
- Met [558590 / 09.184.183](https://www.metmuseum.org/art/collection/search/558590): `met-0015`.
- Wikimedia [Turin King List, Cat.1874](https://commons.wikimedia.org/wiki/File:Turin_King_List,_papyrus_-_Museo_Egizio_Turin_C_1874_p02.jpg): `wm-0019` (also `wm-0020` separate image).
- Wikimedia Turin [S.9598](https://commons.wikimedia.org/wiki/File:Hieratic_ostracon_with_a_section_of_the_%27Instruction_of_Amennakht%27,_limestone_-_Museo_Egizio,_Turin_S_9598_p01.jpg): `wm-0032`; [Cat.2164](https://commons.wikimedia.org/wiki/File:Hieratic_ostracon_inscribed_with_a_hymn_written_by_Amunnakht,_son_of_Ipuy,_on_both_sides,_limestone_-_Museo_Egizio_(Turin)_C_2164_p01.jpg): `wm-0033`; [Cat.1986](https://commons.wikimedia.org/wiki/File:Book_of_Breathing_written_in_hieratic,_papyurs_-_Museo_Egizio,_Turin_C_1986_p01.jpg): `wm-0046`.

**Not yet cleared:** Full `aku-*` 150-sign source lineages, 16 `cbl-*`, 2 Yale museum sources, future benchmark revisions, same physical object across different exposures/archives, aliases and accession joins, photographs embedded in prior papers, transformed facsimiles, perceptual/embedding duplicates, text leakage, foundation pretraining exposure, and true trained-model independent holdouts. **All 15 candidates therefore remain `benchmark_quarantine_pending` for training and few-shot.** Do not describe an absence from 98 source *names* as a completed EVAL-004 provenance/near-duplicate audit.

## 4. Source-safe first pilot: two concrete tracks

| Gate | TPOP curated source+gold track | Met OA+newly authored expert gold track | Pass condition |
|---|---|---|---|
| G0 Metadata | Inventory + writing/face IDs + editor + citations | ObjectID + accession + object URL + page view | 10–20 entries discovered, all traceable |
| G1 Legal and access | Museum clarifies image selection, registered data-export permission, editor text licence/credit and derived-model/weight/publication rights **in writing** | Per-object OA status and actual image URL confirmed; qualified expert gold generated under explicit project-owned or compatible annotation licence | Image AND text independently cleared |
| G2 Evaluation quarantine | Match inventory, fragment joins, editions and writing to *all* pinned benchmark sources | Match Met object/collection aliases, Commons reproductions, alternative exposures and hashes | Source/document/perceptual review; uncertain candidates rejected |
| G3 Original asset acquisition | Approved image(s), immutable original hash, dimensions, exposure/side/page ID | OA image(s), per-object `isPublicDomain`, `primaryImage`/additional image bytes, hashes | External approved acquisition receipts, not only web links |
| G4 Gold creation | Rights-checked editor readings mapped to writing/line and reviewed independently | Two qualified Egyptologists independently draft diplomatic transcription and transliteration, adjudicate disagreements | No invented gold; alternatives/missingness preserved |
| G5 Segregated splits and release | Group all joining fragments, faces, editions and scribal witnesses | Group paired faces/same object and excavation/likely lineage | Genuine EVAL-004 train/dev/test groups and DATA-008 real release checks independently accepted |

**Why two tracks:** TPOP could unlock *existing scholarship* with clear provenance if rights are granted; Met offers more straightforward institutional image policy but requires new specialist labor. These should not be conflated. Short-term initial output can be a **metadata+contact packet** even before any image is acquired. No real-data tests or conclusions are implied.

### Pilot's minimum evidence fields

Document identity: `provider`, `accession/inventory`, `document_group_id`, `join_group`, `face`, `writing_id`, `exposure_id`, `script`, `period`, `medium`, `scribe_if_documented` (never inferred).

Asset licensing: original `image_uri`, `isPublicDomain`/CC0 policy evidence, `image_sha256`, pixel dimensions, provenance/credit, acquisition timestamp and terms; **independent** `transcription_source`, `editor_id`, editorial licence/evidence, derived annotation rights, permitted redistribution, downstream model/weights decision.

Science: `benchmark_source_identity_review`, `perceptual_review`, `train/dev/test_document_group`, `annotation_layer`, diplomatic readings and uncertainty/alternative status, geometries and order, independent annotator identities, adjudication decision log, reviewer dates, and gold-eligibility flags.

**Do not place content in a training directory until G0–G4 truly pass; do not treat a nonempty structurally valid split as scientifically adequate without group-coverage review.**

## 5. Expert-gold acceptance protocol and personnel dependency

1. **Before seeing machine outputs or any held-out test examples**, freeze a short manual annotation handbook using DATA-004/005/006/007 and LING-001; specify Egyptological transliteration conventions, sign ambiguity, lacunae, damage, restoration marks, corrections, direction and reading order.
2. Prefer **two independent qualified Egyptologists** for each pilot writing/line, blinded to each other's first-pass annotation and to model predictions; unresolved conflicts go to a documented third adjudication, not forced majority labels. A specialist may be credited through an approved collaborative agreement, not impersonated by an LLM.
3. Every line has a **diplomatic reading** and an explicitly separate normalized/transliterated analysis; record alternatives and `unknown` spans. Any hieroglyph image or museum curator synopsis does **not** automatically become an aligned line transcript.
4. Audit image–line polygon/order and annotate real physical page/fragment lineage. Respect split isolation **before** expert/model feedback is used for training or prompt tuning.
5. Independently validate at least one permitted image–line–transliteration pair end to end through DATA-008 without labeling this a scientifically adequate release; then plan a diversity-aware multi-document release with genuine nonempty held-out groups and explicit expert budget/availability.
6. Rights/approval evidence needs a named authorized human and date, not test fixture booleans. Funding/staff availability, institutional response and acceptable release licences remain open blockers. Do not launch external procurement or requests without owner direction.

## 6. Institution-ready questions and unsent correspondence

### TPOP — priority: gain an explicitly authorised paired research export

**To (not sent):** collezione.papiri@museoegizio.it  
**Subject:** Hieratic research collaboration — licensed image/line-transliteration pilot (6 identified Turin manuscripts)

> We are developing a reproducible academic-quality Hieratic handwriting research system. We reviewed the Turin Papyrus Online Platform's CC0 image policy, its distinct CC BY-NC partner-PDF terms, and its writing-level editor attribution requirements. Could the museum advise whether a small selected set (starting with Cat.1896, Cat.1971, Cat.1966 and Cat.2021) can be supplied as an authorized image-plus-structured-scholarly-reading pilot?  
>  
> We would like to clarify: (1) permitted access/API/bulk methods and registration; (2) stable document/fragment/writing/line and exposure identifiers; (3) rights to Egyptologist-authored hieroglyphic rendering, diplomatic transcription, transliteration, translation, annotations and their derivatives, including required editor credit; (4) permitted public release of transformed crops/paired annotations, commercial/noncommercial model training and weights; (5) whether a letter of agreement can cover an independently reviewed small subset with no known benchmark overlap. We will maintain institutional provenance, quarantine public benchmark materials and preserve alternative readings. We are not seeking to republish unlicensed editorial content.

**Decision required before sending:** authorize external institutional outreach using an appropriate project contact address and decide whether contact represents individual independent research or an incorporated/research institution. No request has been sent.

### The Met — priority: confirm object OA pixels and availability of Egyptological line readings

**To (not sent):** openaccess@metmuseum.org  
**Subject:** Met Open Access Hieratic ostraca — image availability and scholarly transcription partners

> We are researching Hieratic optical reading with independent expert-adjudicated transcripts. Could you clarify whether the official Open Access API can provide actual public-domain image files for objects 561345 (09.184.703), 561392 (09.184.751), 561361 (09.184.720), 561410 (09.184.769), and 561413 (09.184.772), including alternate views and a stable source/credit record?  
>  
> We understand that OA/CC0 images do not confer rights to separately authored scholarly editions. Are line-level diplomatic transcripts, scholarly transcriptions, or appropriate Egyptological collaborators available for these specific objects? We would independently annotate any permitted images, maintain full provenance and separate benchmark evaluation objects and reproductions. We seek guidance on permitted API use and object-level licensing fields, not a blanket endorsement.

**Decision required before sending:** owner authorizes museum outreach. No claim of API availability, research partnership or museum replies.

## 7. Concrete next unblock sequence and falsifiable outcomes

1. **Owner decision**: permit institution contact, designate representative and intended model/data release posture (open research vs commercially compatible), and identify real expert annotation capacity. These facts change whether G1 or G4 is feasible.
2. **TPOP response**: if a small selection's **images plus editor-authored transcription/annotation rights** and structured export can be explicitly cleared, prioritize this track; if only image CC0 is confirmed, switch to independent scholarly annotation.
3. **Met API verification**: verify `isPublicDomain`, real downloadable `primaryImage`/additional views and object/rights metadata in an allowed runtime, then check against the complete frozen evaluation lineage. The research browser could not reach the JSON endpoint on 2026-10-08.
4. **Expert protocol**: secure independent reviewers, confirm agreements/attribution, create source-grounded first line gold and log alternative readings; never use LING-002 synthetic lexicon output as ground truth.
5. **Accept no more than evidenced**: even one genuine cleared pair is a material real-data proof of workflow, **not a full ML-ready corpus** or valid held-out performance claim. DATA-008 task +3 remains withheld until a genuine independently audited sufficiently diverse train/dev/test release.

### Audit status / nonclaims

- 15 item **records** verified at institution-page metadata level (6 TPOP + 9 Met); not 15 acquired images or 15 eligible real training documents.
- 98 public *Met/Wikimedia* benchmark source identities checked at one pinned upstream commit, excluding raw image extraction and benchmark gold reuse. **No near-duplicate audit performed.**
- Zero item-specific licences/annotation grants, no API image-byte acquisition, no paid inference, no independently reviewed ancient Egyptian lines, no gold, no training/test splits, no messages sent.
- No change to `PROJECT_STATE.yaml`, `TASKS.yaml`, research coverage **14%**, weighted progress **32.5/100**, training count **0**, validated experiments **0**. R-016 is **research evidence**, not scientific task validation.

**Sources beyond sample links:** [Met API and fields](https://metmuseum.github.io/), [Met OA](https://www.metmuseum.org/hubs/open-access), [Met terms](https://www.metmuseum.org/policies/terms-and-conditions), [TPOP access](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/What-is-accessible-for-whom-/), [TPOP policy](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/Policy-on-access-and-publication-of-papyri/), [pinned HieraticBench source](https://github.com/alymoursy/hieraticbench/tree/d587dc990013f18007f1e7a8f56f96ff2f7127e2/data/items).
