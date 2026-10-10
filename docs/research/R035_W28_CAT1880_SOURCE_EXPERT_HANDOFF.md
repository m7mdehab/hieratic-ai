# R035 / Wave 28 — Cat.1880 original photo-to-plate line and expert gold packet

**Status:** Prepared and original institutional sources independently rechecked 2026-10-10; **no new image binary downloaded**, **no same-line pixel match**, **no independent qualified readings**, **no outreach sent**, **no benchmark/trust clearance**. Public redacted [machine matrix](R035_W28_CAT1880_FIRST_LINE_REVIEW_MATRIX.json). Owns research only; no DATA-008 release rights decision, protected benchmark material, editorial transcript reuse or scientific point claims.

## New W28 primary-source recheck

1. [Museo Egizio original catalogue](https://collezioni.museoegizio.it/en-GB/material/Cat_1880) explicitly identifies the Strike Papyrus, accession **Cat.1880**, genuine **hieratic** administrative work written by Amunnakht, Ramesses III / 20th Dynasty. Museum catalogue bibliographic context associates this original with **Pleyte & Rossi, *Papyrus de Turin*, text volume pp.50–65 and plate volume 2 printed plates XXXV–XLVIII**. This is **same-object bibliography**, *not* a specific plate/photo/physical-line assertion.
2. [TPOP official document 131](https://collezionepapiri.museoegizio.it/en-GB/document/131) has **Writing Recto** and **Writing Verso** and displays **12 selected “Text 1” to “Text 12” document units**. They are NOT 12 consecutive physical papyrus lines, nor 12 independently gold-standard transcripts. Editor roles include Matthias Müller and Anne-Claude Honnay, with Kathrin Gabler contributing. Public page explicitly says English translation *in preparation*, and German/French translation requires login or external source. Never scrape login, infer missing editorial license or treat page's modern English summary as an exact original diplomatic line.
3. [Institutional TPOP policy](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/Policy-on-access-and-publication-of-papyri/) (last updated 27 June 2026) says images provided by TPOP may be used under **CC0**; partner PDF files may be **CC BY-NC**; some registered-user PDF files have separate public-domain terms. Editorial authorship is separately credited at the “writing” level, and login data may not be shared. The **CC0 image statement alone is not proof** that a modern editor's original German/English translation or diplomatic sentence can be reused as a training target.
4. The accepted original binary bytes in [R026](R026_ORIGINAL_SOURCE_BYTE_RECEIPTS.json) were genuinely read/hashed on hosted GitHub and then destroyed, not downloaded again this wave:
   - **Exact Commons *new* p01 file** https://commons.wikimedia.org/wiki/File:The_so-called_%27Strike_Papyrus%27_written_by_Amunnakht_-_Museo_Egizio_Turin_C_1880_p01.jpg, JPEG **30,364,719 bytes**, **17,704×7,983** pixels, SHA-1 `c6cf2123a26547c3f9f20e7fab31e1e5b8265ef3`, SHA-256 `2f637e7d59785cce7308e478f6a59fb5c54e0ba9c694621e4072c8b2f2594ee5` (verified in prior W21 source CI 38000390567). A similarly titled **older Commons file including “papyurs” in its filename** has a different original size/dimensions; do not substitute it based solely on “Cat1880 p01” text. Its object is the same, its exact pixels are NOT the R026 original.
   - Original Pleyte–Rossi nineteenth-century **volume 2** https://commons.wikimedia.org/wiki/File:Papyrus_de_Turin._(IA_papyrusdeturin02muse).pdf, **400 PDF pages**, **16,926,761 bytes**, SHA-256 `deec087699eafa5ceee87a2d7e2887590e09b4d2308e40ac6c57b0757c5e43b0` (PDM original source; prior source CI exact match). **Do not infer printed plate XXXV = PDF page 35 or PDF zero-based page 34.** Roman plate folios and PDF pages have different pagination, blanks and image faces.
5. Prior public benchmark [R017](R017_PUBLIC_BENCHMARK_LINEAGE_AUDIT.md) only screened 266 **public metadata** records; zero exact Cat1880 accession strings and 19 broad Turin-family hits do **not** prove that the sealed physical source, edition or visual derivatives are absent. Entire Cat1880 accession remains **one physical witness / quarantine group** regardless of p01/p02/p03 views and resized/rotated variants. No sealed benchmark introspection is authorized.

## Genuine image/line correspondence decision, fixed explicit nulls

The [machine matrix](R035_W28_CAT1880_FIRST_LINE_REVIEW_MATRIX.json) lists TPOP Text1/Text2/Text3 as **candidate selector units only**; none was claimed a photographed physical line. Each exact original-photo coordinate polygon, recto/verso mapping, printed Roman plate, PDF zero-based page and 3 discriminating shared stroke anchors is **NULL/[]**. No automated claim of photograph-to-plate registration, target transliteration, writer stylistics, damage agreement, line continuity or published re-segmentation.

An eligible “first Cat1880 gold line” requires, in this order:

1. A dedicated independent primary-source reviewer inspects the exact R026 photograph revision and the original 400-page historical volume under their respective permissions and annotates the **specific printed plate label actually on that PDF image face** and its zero-based PDF index. Log image version/hash and side, not an inferred pagination equation.
2. Select a fully visible photo physical line by an explicit source-attached pixel polygon (integer coordinates bounded to 17,704×7,983, origin/rotation disclosed) and the historical edition crop polygon in the independently verified plate raster. Account for mounted fragments, lost ink, damage and orientation.
3. Show **at least three distinct numbered, discriminating shared groups of strokes** observable in both the genuine mounted photographed original and the historical plate. Attach point/polygon, human reviewer confidence and contradiction notes. Run independent source/edition lineage check to confirm whether facsimile is diplomatic or restoratively normalized. If correspondence is inconclusive, record **NO_MATCH_UNRESOLVED**, not a guessed line number.
4. Two independently authenticated qualified Egyptologists each examine the **original cropped photo** and render separate diplomatic sign sequence/transliteration with uncertainty, alternatives, lacunae and abstentions. The two reviewers **cannot see each other's draft, the source editorial answer or system output** before locking their reads. A third independent adjudicator subsequently records agreement/disagreement and decisions; do not force consensus where evidence is absent.
5. Rights officer independently secures permission/licenses for the original source image, *each editor-created and reviewer-created reading*, annotation geometry, training/development/evaluation and permitted derivative distribution. A qualifying license for a photo is not enough for separately copyrightable annotation work; institutional trust root and reviewer credentials kept outside public Git and verified by independent authority.
6. Independent benchmark custodian evaluates the accession/edition/source pedigree and perceptual near duplicate relation **without making sealed benchmark data available to the model developer**. Unknown overlap stays quarantined and cannot be used for blind-scoring gold.
7. EVAL-004 source-witness-group split, original SHA and image transform audit, DATA-002/003 acquisitions, DATA-004/005/006/007 gold chain and DATA-008 release authority all pass. One expert line alone is not a scientifically adequate corpus v1; adequacy/stratification must be reviewed independently.

## Independent review receipt fields

A private signed/onboarded reviewer ledger must bind:
- original museum object ID and original raw SHA/size/file page;
- original photo side and exact polygon, resize orientation transform/histogram diagnostic;
- historical work volume source SHA, printed plate Roman numeral, exact PDF zero-based page and selected image crop;
- ≥3 diagnostic numbered matched strokes with original vs plate coordinates plus direction/uncertainty;
- blind reader #1 and #2 authenticated Egyptological qualifications, affiliation/authority, role separation, lock timestamps, original independent readings and license terms;
- third independently qualified adjudicator ID, decision, alternatives/lacunae and any continuing dispute;
- signed authorization covering editor/reviewer-produced transcription/translation and transformations, institution authority and expiry/revocation;
- benchmark lineage/overlap custodian disposition and source release adequacy, all immutable and independently revocable.

Only externally verified redacted evidence digests and aggregate statuses may be committed publicly. Merely adding a YAML signature/role key in repository code is *not* external institutional authority.

## Source/publisher matrix for authorized reviewer

| Candidate | What is genuinely known | What remains unresolved | Decision |
|---|---|---|---|
| Cat1880 exact R026 p01 photo | Exact image CC0, bytes/SHA/dimensions from prior independent hosted run; object catalogue confirmed | Current private custody, which mounted face/line, licensed reading source | Image can be investigated; no text gold |
| Pleyte/Rossi vol2 | Historical original PDM source 400 pages, physical-document bibliography plates XXXV–XLVIII | Printed Roman plate↔PDF page, photo line↔plate line, modern editorial correction | Source research only |
| TPOP Text 1 | One of 12 editorial text selector records on Cat1880 document 131; named editors | Physical-line ordinal, original photo polygon, transcript reuse rights | Not a physical-line label |
| TPOP Text 2 | Same publication document/context | Same unknowns | Not a physical-line label |
| TPOP Text 3 | Same publication document/context | Same unknowns | Not a physical-line label |
| Published modern English overview | Institution gives object history; text describes strikes | No exact diplomatic line pairing; rights distinct | Context only |
| R017 public overlap metadata | 266 public source records, Turin family hints | Official sealed provenance and original/derivative image lineage | UNKNOWN → quarantine |

## First research outreach request — WRITTEN, NOT SENT

**Potential recipient:** Official Museo Egizio Papyrus Collection research contact `collezione.papiri@museoegizio.it`, as listed on the museum's TPOP policy and contacts page. This is a public institutional research address, not private third-party user information.

**Subject:** Research clarification request — Cat.1880 original photograph, Pleyte/Rossi plate/line alignment and licensed diplomatic reading

> Dear Museo Egizio Papyrus Collection Team,
>
> I am preparing a small reproducible research pilot on Hieratic manuscript reading, centered on Cat.1880 (Turin Strike Papyrus). I have verified the public collection catalogue and the exact original Commons CC0 image file for Cat.1880, and the historical Pleyte–Rossi *Papyrus de Turin* volume-2 plate publication referenced in your catalogue. I have **not** established correspondence between an individual photographed line and a specific historic plate/line, and do not wish to infer it from the publication index.
>
> Could your team advise (a) the confirmed recto/verso and exact source-view identity of the original Commons Cat1880 photograph, (b) the exact printed Pleyte/Rossi plate and line corresponding to one short, intact photographed source line (or a route to scholarly verification), (c) whether there is a correctly licensed diplomatic modern transliteration for that precise line, and (d) who may authorize a separately reviewer-created diplomatic line annotation for noncommercial research, model training/evaluation and possible later open release?
>
> We would also welcome advice on qualified independent Egyptologist reviewers who could perform **two blinded readings and independent adjudication**, without exposing existing editorial or machine outputs before review. We will not assume the image's CC0 status extends to modern TPOP editorial translations or reuse restricted material without consent. If this requires a formal collaboration, permission request, registration or paid specialist engagement, please describe that process before any work begins.
>
> We can share exact source hashes and a small redacted provenance checklist, without sharing credentials, private user data, benchmark answers or unlicensed content.
>
> Thank you for considering this source-identification and research-permission inquiry.
>
> Sincerely,
> Hieratic-AI research project

**Outreach state:** UNSENT. Requires the user's explicit authorization to contact the museum or qualified researchers; no fees or contractual acceptance authorized. The code and issues do not send email.

## Consequence for scientific gates

- Cat1880 original photo↔historical plate **document identity**: verified.
- Exact **same physical original line**: 0 verified pairs.
- Independently reviewed **gold diplomatic lines**: 0.
- New modern text/translation reuse rights: not verified.
- Source-independent heldout benchmark provenance: not cleared.
- REAL DATA-008 original-photo corpus training/evaluation admission: 0.
- Weighted task points: **0 added**; canonical 34.5/100 and research 18, no new empirical experiment.

**Next decisive external action if authorized:** submit unsent scholarly inquiry; until then all purely independent online research/actionable protocols are complete. Source-verified title/index alone cannot replace a specialist reading.