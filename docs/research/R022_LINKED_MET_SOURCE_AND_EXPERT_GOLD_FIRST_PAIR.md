# R-022 — W7 independent first-pair accession identity and Egyptologist acquisition decision

**Completed:** 2026-10-09. **Evidence:** [Structured audit](R022_MET_LINKED_OBJECT_PILOT_DECISION.json), [R-021](R021_IMAGE_TEXT_PAIRING_RIGHTS_AND_LEAKAGE.md), Met exact source-page links below. **Scientific result:** ZERO authentic source-aligned, licensed, independently reviewed image/line pairs; this is source research only. No source image or copyrighted scholarly transcription downloaded or uploaded. No institutional outreach or money spent.

## 1. Met 561345 filename ambiguity now has *primary-catalogue* evidence

Prior [DATA-002 object 561345 response](../../data/acquisition/met/objects/561345.json) contains two official original-photo URLs, both named `09.184.728-09.184.703_EGDP017620/21.jpg`. This was previously classified as a suspicious *multi-accession-looking photo filename*. It now has a verified catalogue counterpart:

- **[561345 / 09.184.703](https://www.metmuseum.org/art/collection/search/561345)** — official Met Hieratic ostracon, Ramesside, accession **09.184.703**, about high-authority visit to the royal necropolis; object size **18.8 × 12.8 × 4.5 cm**; publicly marked **Public Domain**.
- **[561369 / 09.184.728](https://www.metmuseum.org/art/collection/search/561369)** — **separate** Met collection-object ID and accession **09.184.728**, directly titled **“Hieratic Ostracon- see 09.184.703”**; object size **10 × 18.5 cm**; publicly marked **Public Domain** and not on view.
- [Wikimedia Commons object-linked archive](https://commons.wikimedia.org/wiki/File:Hieratic_Ostracon-_see_09.184.703_MET_09.184.728-acc.jpg) independently repeats source attribution to Met **561369**, accession **09.184.728**, with a Met-donated CC0 description. Commons metadata are corroborative, **not original institutional proof of physical joins**.

**Established:** two museum catalogue objects explicitly refer to one another; one candidate's Met API photo filenames include **both** accession numbers. **Not established:** whether they are joined fragments of one original support, companion ostraca, distinct text witnesses, or separately numbered objects co-photographed in the exact full-resolution frames. No original photo pixels were downloaded/inspected. This source relationship must not be converted into *false physical-join certainty*.

**Scientific control:** until independently resolved, use one conservative **linked holdout/leakage group** `MET-09.184.703__09.184.728_LINKED_UNRESOLVED` for both objects, all faces/views, editions and crops. Never allow one accession in training and the other in test; never count their images as two independent documents. Also search both aliases in historical publications and source support lineage, even though the pinned R-017 266-public metadata census has **zero literal accession/object-ID hits** (not proof of unseen data).

## 2. Changed first-pair priority: Met 561392 ahead of 561345

- **Preferred first core-period pilot: [Met 561392 / 09.184.751](https://www.metmuseum.org/art/collection/search/561392).** Official Met: Ramesside Hieratic ostracon, **notes on lamps/torches, one written face**, 10 × 10.1 × 1.9 cm, Public Domain. Its [W6 API packet](../../data/acquisition/met/objects/561392.json) has two image references with one `09_184_751` accession and a recorded original API response-body SHA-256 `6b9499da2e3f704ba949899a15465f90775f9eaf84bfd081452c6da5f60df424`. No original JPEG bytes, exact view/frame pixel SHA, approved Egyptologist reading or benchmark alias review yet. Two photos are **two views of one candidate**, not two independent manuscript supports.
- **Fallback/special-case group:** Met **561345 ↔ 561369**, only after original-object/fragment/photographic link adjudication. This does *not* mean the pair is unsuitable forever: resolving the linkage itself can become a source-provenance test case.
- **Alternative text-first core route:** Museo Egizio [Cat.1896](https://collezionepapiri.museoegizio.it/en-GB/document/259/) has TPOP-provided image CC0 scope distinct from credited scholarly editor rights; a specific writing/side/line still needs independently licensed text and spatial mapping.
- **Possible annotation-linked but script-stratum-specific route:** Louvre/Leiden E 7852 through [AHGP](https://lab.library.universiteitleiden.nl/abnormalhieratic/papyri/p-louvre-e-7852/) requires **Louvre photographic** and **Leiden CC BY-NC-SA 3.0 NL editorial** permissions and is **Abnormal Hieratic Dyn.25–26**, not interchangeably evidence for Ramesside reading.

**Reason for ranking:** 561392 avoids the *known* Met 561345 ↔ 561369 catalogue/source association. This is a comparative workflow preference, **not a clearance verdict** or proof 561392 cannot overlap a published edition/foundation-model pretraining.

## 3. Real specialist route: expertise verified, not capacity or agreement

The official [Museo Egizio research team page](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Collection/Our-projects/Research-projects/) identifies **Susanne Töpfer** as curator of its papyrus collection since 2017, coordinator of TPOP, and researcher of Hieratic, papyrology and ancient Egyptian texts. The [Crossing Boundaries project](https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Collection/Our-projects/Crossing-Boundaries/) documents partner institutions **Museo Egizio, University of Basel and University of Liège**, with specialist expertise in Ramesside Deir el-Medina scribal practices. The museum publishes **collezione.papiri@museoegizio.it** as its official [papyri/ostraca inquiry route](https://collezionepapiri.museoegizio.it/en-GB/contacts/).

**Limits:** This confirms a **credible specialist research community/contact channel**, not that anyone has agreed to work for this project, is qualified to transcribe this specific Met ostracon sight unseen, will release derivative IP on permissive terms, or has quoted a fee. **Fee: unknown**. **Availability: unknown**. **Named first reader: unengaged; second reader: unengaged.** An institutional curator need not personally perform the annotation. The Met's Egyptian Art curatorial team is an appropriate provenance clarification route, **not a presumed transcription bureau**.

### Exact owner-ready inquiry packet — UNSENT

**Inquiry A: Met collections/photography source linkage.** Identify Met 561345 (09.184.703) and 561369 (09.184.728), their formal relationship (same physical original/join/associated text vs different supports), photograph `EGDP017620/21` contents (one object vs multiple fragments in frame), which original exact pixels illustrate which object and face, any stable API exposure/canvas ID, and published facsimile/edition aliases. For 561392 (09.184.751), confirm which of its two views is the inscribed face and whether its current Download Image images are covered by its listed Public Domain/Open Access status. No demand that museum create bespoke rights where open CC0 policy already grants image reuse.

**Inquiry B: specialist independent first reading.** For a single selected 561392 original photo and named inscribed line: who can produce *original* diplomatic Hieratic sign reading / hieroglyphic rendering / standard Egyptological transliteration with uncertainty and a documented polygon or precise ROI? Can a **second independent qualified Egyptologist** adjudicate disagreements? What original author's rights cover keeping, publishing, using for ML training/evaluation and distributing derived data/model weights? How will text, editor attribution, metadata and uncertainty be cited? Ask for indicative turnaround and quote **only if the user approves outreach**; do not invent an hourly fee.

**Inquiry C: editorial existing-text alternative.** For Turin Cat.1896 specifically distinguish recto decree vs address verso vs ration note verso, request one authorized editor's diplomatic line with explicit writing ID, source photo/canvas and publication/edition licence. Images CC0 are **not** editor copyright clearance.

**An internally produced request is not a real grant of rights or expert certification.** Store signed replies privately under protected authority, not in public Git. No requests have been sent.

## 4. Practical first-pair gate: exactly one line, then evaluate eligibility

1. **Owner decision:** decide unrestricted/commercial-compatible corpus versus a legally segregated NC research subset. Default for main project is unrestricted-compatible; AHGP's CC BY-NC-SA cannot silently satisfy it.
2. **Photo:** explicit agreed Met 561392 inscribed view with provenance from the source API packet, exact original photo bytes in restricted vault, SHA-256, dimensions, MIME, source page and acquisition date; distinguish CC0 policy observation from exact file and institution metadata.
3. **Source group:** physical support/cross-accession/fragment and edition/source-witness review; ignore zero literal benchmark matches as proof. No training/test mixture.
4. **Text:** original Egyptian diplomatic line reading separate from catalogue English prose, first Egyptologist authorship, timestamp, edition/line ID, all alternatives/damage and uncertainty, signed use/derivatives licence.
5. **Geometry:** same exact image ROI/line polygon or trace with coordinate convention, orientation, and auditable source image SHA binding.
6. **Second reader:** blinded independent review or explicit adjudication; preserve both alternatives, not just majority.
7. **Protected authority:** DATA-008 independent trust root/rights-holder approvals and reviewer authentication must be established *outside task-writable Git*. Production currently hard-disabled.
8. **Scientific boundary:** one legal line demonstrates end-to-end authenticity/continuity only. A real *held-out* performance score requires an independently frozen cohort, actual image-conditioned predictions, disjoint source splits and properly audited EVAL-001 + official scorer for any official rung.

## 5. Outcome

**R-022 scientific status:** 0 real eligible pairs, no new model evaluations, no source admission. **Action now possible without institutional approval:** carry the documented Met cross-accession link into the source-lineage acceptance checklist; prioritize 561392 and record expert-gold inquiry contents. **External blocker:** explicit source-pixel procurement/owner authorization and actual qualified annotators, not lack of a further web search. No user approval for museum correspondence, external expert payment, image acquisition or inference billing has been granted in this lane.
