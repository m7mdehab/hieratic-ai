# R-018 — Institutional Hieratic image, palaeography and expert-transcription feasibility

**As of:** 2026-10-08 · **Mode:** primary-source public policy/catalogue research; no assets downloaded, login attempted, scholarly text copied, correspondence sent or licences acquired.  
**Predecessors:** R-015 open image source discovery; R-016 15-object shortlisted catalogue; R-017 all-266 public benchmark-source metadata census.  
**Objective:** distinguish **(a) rights to use specific pixels**, **(b) rights to scholarly transcription/translation/annotation**, **(c) actual image–line spatial alignment**, and **(d) absence of evaluation contamination**.

## 1. Practical decision: deploy a *two-track* real gold-acquisition strategy, plus a complementary sign track

- **Route A — Museo Egizio TPOP image plus authorized edited text:** The museum explicitly permits using TPOP-provided **images under CC0**, publishes some images and editor-attributed hieroglyph renderings/translations, and exposes structured document/writing/side identities. However, **the textual editorial copyright/contract/export and line-pair mapping are separate**. A rights-holder/editor agreement plus structured, traceable line-level extraction is necessary before turning catalogue scholarship into training gold. First inquire on **Cat.1896**, then **Cat.1971**, **Cat.1966** and **Cat.2021**. Do not presume unrestricted reuse of textual editions embedded in the site.
- **Route B — Met Open Access original image plus newly produced licensed Egyptologist gold:** Official Met object pages label the nine R-016 Hieratic ostraca public domain, and the museum uses CC0 for eligible Open Access images. But the descriptive text is **not** a diplomatic line-by-line Hieratic transcription. Commission independent original expert readings and connect them to actual approved image bytes and object/side IDs; all sources remain benchmark quarantine pending full alias/duplicate checks.
- **Complementary Route C — CC BY palaeography-sign metadata:** University of Tsukuba / University of Tokyo **Hieratische Paläographie DB (HPDB)** provides **2,065 open sign index entries**, **937 cross-notation concordance entries**, IIIF curated regions and CC BY 4.0 project datasets. This is a materially stronger, potentially usable *metadata and sign mapping* source than relying on uncited invented signs; the underlying IIIF page-image and prior-edition reproduction rights must **separately** be established. These cropped historic palaeographic signs are **not equivalent** to a broad corpus of modern photographic handwritten manuscript lines, and cannot by themselves establish contextual transcription ability.

These are complementary inputs, not interchangeable datasets. The third track can strengthen DATA-005 and sign recognition only if its imaging/editorial provenance and evaluation isolation are cleared.

## 2. Primary-source institutional comparison

| Priority | Institution/collection and public primary evidence | Image rights/access state | Text/transliteration and alignment state | Feasibility for desired corpus |
|---|---|---|---|---|
| **A1** | **Museo Egizio TPOP**: [official rights/authorship](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/Policy-on-access-and-publication-of-papyri/), [public access](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/What-is-accessible-for-whom-/), [Cat.1896](https://collezionepapiri.museoegizio.it/en-GB/document/259/) | TPOP-provided **images CC0** per platform policy; external partner PDFs **CC BY-NC**; many documents require personal registration, not transferable credentials | Multiple editor-attributed writing levels and partial translated/hieroglyph material; no verified freely licensed bulk diplomatic transliteration with image-line coordinates | Strongest **paired-source permission-inquiry** prospect. Do not infer that image CC0 licenses editor-authored text |
| **A2** | **Met**: [OA policy](https://www.metmuseum.org/hubs/open-access), [561345](https://www.metmuseum.org/art/collection/search/561345), [561392](https://www.metmuseum.org/art/collection/search/561392), [561410](https://www.metmuseum.org/art/collection/search/561410), [561413](https://www.metmuseum.org/art/collection/search/561413) | Individual pages show “Public Domain”; Open Access CC0; verify each asset via per-object API and actual pixels | Catalog synopses and object details, not verifiable scholarly line/sign gold; original annotation work required | Best **image+new expert gold** fallback; moderate cost/personnel dependency |
| **A3** | **HPDB (Tsukuba/Tokyo)**: [datasets](https://moeller.jinsha.tsukuba.ac.jp/en/datasets/), [project and methods](https://moeller.jinsha.tsukuba.ac.jp/en/) | 2,065 sign-index metadata records, 937-ID concordance, IIIF curation, metadata dataset CC BY 4.0; University of Tokyo's original scanned Möller publication IIIF images need separately confirmed rights and access conditions | Sign IDs, palaeographic variants, mappings, IIIF rectangular regions. No multi-line original photo-to-diplomatic text pairs | High-value **sign/mapping integration pilot** after rights/lineage separation; weaker for line recognition |
| **B1** | **Chester Beatty**: [official copyright](https://chesterbeatty.ie/about/copyright-2/) | Default object image licence **CC BY 4.0**, except items with other copyright attribution; institute credits required | Papyrus collection scans; corresponding editions/transliterations not covered by CC BY photo statement | Strong additional original-photo donor subject to item-specific validation. **16 public CBL benchmark IDs already evaluation-only** |
| **B2** | **Yale Peabody**: [Open Access IT statement](https://peabody.yale.edu/explore/information-science), [terms](https://peabody.yale.edu/about/terms-of-use) | Site generally releases data/images CC0 but *terms explicitly warn not all content is unrestricted*, check each object | Peabody Hieratic papyrus catalog metadata but no demonstrated paired text gold | Secondary CC0 image candidate; **two Yale objects already in public benchmark** |
| **B3** | **AKU-PAL (Mainz)**: [English project](https://en.aku.uni-mainz.de/project/), [sign copyright FAQ](https://aku-pal.uni-mainz.de/faq) | Digital **SVG sign facsimiles**, occasional photographs; copyright is **per image / per item**, cross-partner material varies; **not blanket** open-rights claim | Rich grapheme, support, dating and manuscript metadata with stable entry URLs; strongest sign/palaeography lexicon linkage, not long-line aligned ground truth | Collaboration possibility; 150 AKU sign items in benchmark must be excluded by **physical object** and image lineage, not sign entry number |
| **B4-restricted** | **DDD: Diagnostic Deir el-Medina Dataset**: [Zenodo record and licence](https://zenodo.org/records/20553713) | 159 images of 50 papyrus documents, with per-image rights, general CC BY-NC-SA 4.0; some full images subject to publishability, partner rights | 504 selected character/group classes, polygon annotations; authors explicitly say **not complete character annotation** | Scientifically useful external evaluation/research inspiration and potential collaboration, **not default commercial-compatible line corpus** |
| **B5-permission only** | **Ramses Online / Liège**: [project overview](https://www.egypto.ulg.ac.be/Ramses.htm), [TPOP Cat.1971](https://collezionepapiri.museoegizio.it/en-GB/document/216/) | Image provenance is external to many Ramses references; no institution-level blanket image licence established | Late Egyptian textual corpus with annotated transliteration, hierarchical transcription and envisioned TEI/XML export; no confirmed permissive bulk text/ML licence | Potential authoritative **textual edition**, especially Cat.1896/1971 pointers. Seek owner-led written licence and line identifiers; no scraping |
| **B6-permission only** | **LMU Deir el-Medine Online**: [official LMU project description](https://www.aegyptologie.uni-muenchen.de/forschung/projekte/deir_el-medine/index.html) | No blanket unrestricted original image right verified | Published nonliterary Hieratic ostraca catalogue with text and support metadata | Relevant corpus expertise; ask about available transcriptions/rights and record joins |
| **C-no-bulk** | **Thesaurus Linguae Aegyptiae**: [corpus format](https://thesaurus-linguae-aegyptiae.de/info/text-corpus?lang=en), [licence](https://thesaurus-linguae-aegyptiae.de/info/licenses) | Original photographs not necessarily served or rights-linked to each textual witness | Major Egyptological transliteration+translation+lemmatized corpus, some hieroglyph transcriptions, stable text/object IDs. Explicitly permits individual academic quotations but **forbids copying whole subcorpora or more than ten pages** absent separate raw-data permission | **Do not bulk extract**; source for citation/discovery, targeted authorized licensed raw-data inquiry to project |
| **C-noncommercial** | **British Museum**: [image permissions](https://www.britishmuseum.org/terms-use/copyright-and-permissions/images-and-photography) | Most website images CC BY-NC-SA 4.0; commercial use requires separate image license; others third-party | Relevant original Hieratic manuscript holdings, but image and text licenses differ | Restricted to approved use / explicit commercial rights; separate research branch |
| **C-noncommercial** | **UCL Petrie**: [collection site](https://collections.ucl.ac.uk/home), [curatorial image licensing](https://www.ucl.ac.uk/engage/museums-collections/petrie-museum-egyptian-and-sudanese-archaeology/collections-and-research) | Collection online image/text CC BY-NC-SA 3.0; commercial rights require inquiry; curated higher-resolution photos on request | Catalogue and some associated scholarly studies, no blanket full transcription licence | Good relevant materials but default rights **not** aligned with broadly reusable/commercial-compatible corpus |
| **C-authorization required** | **Tsukuba Hieratic Database (HDB)**: [project About](https://wdb.jinsha.tsukuba.ac.jp/en/wdb/hdb/about) | Historical Papyrus Abbott collaboration images from British Museum; online database restricted to authorized academic users | Hieratic text/database alignment potentially valuable | **Do not conflate** with Tsukuba's separately CC BY **HPDB datasets**; no HDB access or use without explicit permission |

### Key factual distinctions

**Open access ≠ open training pair.** An open image might have no text; public hieroglyph rendering might have a separate editor/edition copyright; a CC BY sign metadata concordance might cite a photographed manuscript under a different rightsholder. Historical provenance and representation rights must be determined for every layer.

**Text edition ≠ observed sign truth.** Normalized hieroglyphic rendering is editorial interpretation, not equivalent to preserved Hieratic ink strokes. Ensure distinct diplomatic / palaeographic / normalized / lexical / translated layers.

**Fragments ≠ independent pages.** Joined papyri, alternate sides, alternative exposures, editions and named literary works require grouping and disambiguation before sampling or splitting.

**Benchmark exclusions:** The 266-source metadata census identifies known AKU/CBL/Met/Wikimedia/Yale evaluation witnesses. Even candidate object IDs absent as direct strings may overlap via institutional aliases. No candidate is now marked independently cleared.

## 3. Source-by-source expected output contracts

| Data field | TPOP | Met | HPDB | Chester Beatty / Yale |
|---|---|---|---|---|
| Institution/source identifier | Inventory, document, writing | Met objectID, accession | HPDB item ID, original support + Möller ref | Institution accession and viewer ID |
| Authoritative image | Museum photo/exposure/side under stated CC0 platform policy | OA original `primaryImage`/additional views | IIIF book/plate exposure; **underlying page-image terms** | Image viewer file/version |
| Textual label | Editor-authorized separate text or newly created expert gold | Newly created expert gold | Sign identity/glyph correspondence, not aligned line gold | Licensed published edition or new expert gold |
| Image licence evidence | TPOP policy + exact image provenance | per-object OA flag + exact pixel URL | CC BY index metadata + source-image agreement | explicit per-item rights and file provenance |
| Editorial rights evidence | **MUST OBTAIN** | independent author agreement | license to editorial metadata and mappings | **MUST OBTAIN** or annotate independently |
| Model/sublicensing rights | written answer needed for text | independently authored labels licensed for intended model use | test per content layer | case by case |
| First usable scientific output | reviewed paired line and exact image hash | reviewed paired line and exact image hash | verified sign crop+notation match | verified image and approved new/existing reading |

## 4. Candidate priority and evidence-gated funnel

### Tier 1 — institution-ready, still BLOCKED
1. **TPOP Cat.1896:** multiple physically identifiable writings, explicit editors, mixed administrative text; highest prospect of nontrivial writing-addressable gold, but multilingual translations are incomplete and editorial access uncertain.
2. **TPOP Cat.1971:** letter with recto/verso, external Ramses Online/TLA pointers; paired-source mapping would require separate text edition licence.
3. **Met 561345 / 561392:** two distinct administratively described ostraca with OA-labelled catalog pages; needs original pixel and newly authored expert transliteration.
4. **Met 561410 / 561413:** pottery examples diversify beyond limestone, subject to visual legibility and actual image bytes.

### Tier 2 — complementary
5. **HPDB 2,065 item sign-index / 937 concordance:** prepare a legal and source-overlap review for explicitly permitted metadata + IIIF crops; test annotation ontology and mapping, not unseen-page transcription.
6. **Chester Beatty nonbenchmark objects:** seek object-specific rights, line editions and manuscript exclusion against benchmark's 16 CBL entries; *do not nominate a specific unexamined object*.
7. **Yale Peabody nonbenchmark objects:** similar CC0+expert gold route; first identify actual nonbenchmark Hieratic entries.

### Tier 3 — educational / external validation / owner-negotiated license only
8. **DDD**, **AKU-PAL**, **TLA**, **Ramses**, **LMU**, **British Museum**, **UCL**: excellent scholarly resources but missing one or more decisive rights, item or alignment gates for the current commercial-compatible objective. Remain research-only until explicitly resolved.

## 5. Institutional engagement question sets — all UNSENT

**Museum permissions**: confirm each image's source rights and exact original image file/IIIF ID; whether machine-learning development, public dataset transformation, public redistribution and model weights are permitted; image metadata and attribution; high-resolution and automated or bulk access without prohibited credential sharing.

**Editors and rights holders**: identify the legally authorized licensor of diplomatic transcription, transliteration, translations, hieroglyph conversion, annotations and line mapping; permissions for machine learning/derived datasets and publication; stable edition/version; editor citation requirements; availability of normalized versus diplomatic variants and revisions.

**Scientific collaborator**: request a small blind pilot with two independently qualified Egyptologists, documented annotation conventions, line/polygon identity, missing/alternative readings, disagreement adjudication, estimated reviewer capacity and remuneration or institutional collaboration terms. No presumed staff, cost or institutional acceptance.

### Additional draft — Chester Beatty

**To (not sent):** photographicservices@cbl.ie (listed on official museum copyright page)  
**Subject:** Authorized Hieratic papyrus image/transcription research pilot

> We are evaluating a small source-traceable Hieratic reading pilot. We understand that Chester Beatty collection object images generally use CC BY 4.0 except where third-party rights are indicated. We would appreciate guidance about obtaining original resolution images for suitable **nonbenchmark** Hieratic papyri with precise object/page/side IDs, and whether a scholarly diplomatic transcription or transliteration is available under a separately authorized compatible licence. We will independently screen accession and image lineage against public HieraticBench sources, retain curator/editor credit, and request specific permission before collecting text or registered assets. Could the museum suggest which images, manuscript identifications and reuse terms might support a small reproducible pilot?

### Additional draft — Hieratische Paläographie DB

**To (not sent):** mnagai@slis.tsukuba.ac.jp (official HPDB homepage)  
**Subject:** HPDB open palaeography corpus — confirmation of IIIF image rights and derived sign uses

> We have examined the HPDB's 2,065-record index, 937-record concordance and CC BY 4.0 published datasets. May we clarify whether the underlying IIIF plate images and their derived sign crops can be incorporated into an attributed computational sign-recognition benchmark or training corpus, whether additional University of Tokyo/edition permission is required, and how the original plate, grapheme and support identifiers should be cited? We would not assume that the metadata licence alone grants rights over underlying digitized images or unpublished scholarly annotations.

### Additional draft — AKU-PAL

**To (not sent):** aku@uni-mainz.de (official FAQ)  
**Subject:** Hieratogram source mapping and image-specific reuse for independent research

> We are compiling a source-identity exclusion ledger for Hieratic computer vision. AKU-PAL's stable sign, text and object pages are very useful, and we recognize that the license varies by individual image and collaborator. Could you advise the correct stable physical-support IDs/aliases for source names, any bulk metadata licence or API, and the procedure to request rights for genuinely nonbenchmark sign-image exemplars and palaeographic annotations? We will exclude all benchmark-linked source supports and do not seek unrestricted access to collaborator-owned images.

**No draft is sent.** TPOP and Met drafts are already in R-016. Sending, accepting licences or hiring specialists requires owner authorization and designated contact identity.

## 6. Falsifiable go/no-go after inquiries

- **TPOP GO** only with explicit text/edition licence + image-source receipt + line/writing-level identifier + benchmark quarantine clearance + independently accepted expert gold. If text permissions unavailable, route imagery into independent expert annotation instead.
- **Met GO** only when a real OA image file is securely acquired, source/object/side/pixel hash verified, rights independently checked, expert gold produced under a compatible licence and held-out leakage audit passed. Catalogue synopsis never becomes gold.
- **HPDB sign GO** only when underlying IIIF image/crop rights and edition provenance are established, source support not used by evaluation witnesses, sign label identity validated and specialist review passed.
- **Commercial-compatible release NO-GO** for image/text assets restricted by NC terms until an explicit additional authorization or a deliberately separately isolated noncommercial research license is approved; no silent mixing.
- **Science acceptance NO-GO** until genuine image–gold pairs from multiple independent document groups and correct blind held-out evaluation are achieved.

No corpus acquisition, expert annotations, reproducible ML result or scientific capability claim is implied by this source inventory.
