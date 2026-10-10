# R034 / W27 — Original Tokyo library IIIF pixel rights and image-conditioned diagnostic

**Overseer research scope (2026-10-10):** Resolve a genuinely new original-image rights route and execute a bounded real-pixel experiment using source-linked historical printed Hieratic sign facsimiles. This is **not original photographed papyrus**, **not an independently verified physical-manuscript holdout**, **not an official HieraticBench score**, **not an authorized DATA-008 production corpus**, and not independently adjudicated sign gold.

## New material source-rights discovery

The already-pinned Hieratische Paläographie Database (HPDB) project originally provided *metadata only*. It indexes **2,065** printed sign-item records, including **1,439** simple single-Gardiner catalog mappings, sourced from Georg Möller's *Hieratische Paläographie* volumes I–III.

Independent original-source legal chain, not merely an HPDB catalogue metadata license:

1. HPDB itself attributes the underlying IIIF images of Möller's historical 1909–1912 publication to the **Asian Research Library, University of Tokyo**: https://moeller.jinsha.tsukuba.ac.jp/en/ and https://moeller.jinsha.tsukuba.ac.jp/en/manual/search/.
2. Tokyo's original archive object **Möller, Hieratische Paläographie Band 1**, metadata rights and provider are documented at https://da.dl.itc.u-tokyo.ac.jp/portal/en/assets/4a1fbed0-f2a2-4cf5-8a0a-fa310c62ca50 ; provider **U-PARL University of Tokyo Library System**.
3. The **actual provider's public image-reuse policy** explicitly covers the Asian Research Library digital collection, permits downloads, copying, modification, noncommercial AND commercial secondary reuse without applications, and describes conditions equivalent to CC BY 4.0: https://www.lib.u-tokyo.ac.jp/ja/library/contents/archives-top/reuse . Attribution must name the holding library, and transformations must be clearly identified. The legal notice applies to out-of-copyright original materials in the listed archive, and item-level exceptions still control. Our acquisition route must fail on an exception.
4. HPDB's separately licensed **CC BY 4.0 original item metadata** are listed at https://moeller.jinsha.tsukuba.ac.jp/en/datasets/ . HPDB sign-item labels are catalogue equivalences, not independent hieratic blind adjudication; original photographic papyrus source and exact scribal hand often remain undetermined.
5. As an alternative, **Tabin's PaPYrus** contains three publicly downloadable sign-image ZIP datasets, specifically the categorized (~27 MB) source folders and 13,134 individual facsimile sign images; see https://github.com/jtabin/PaPYrus at commit `3a45a030e5b1a2bc185d1a723e9a4ebfecdfe7ae`. The authors describe the data as free and request open contributions, while GitHub distributes the GPL-3.0 license file. This **does not independently establish sublicensing rights for each included facsimile source image**, so no PaPYrus images are used in this wave.

### Rights disposition

**Tokyo HPDB publication-page crops: evidence supports limited original-source research inspection, transforms and the proposed permitted-use study**, with mandatory provenance/attribution and item-exception rechecks. This does **not** license or certify unseen *underlying ancient papyrus photographs* or modern protected editions, and cannot self-authorize a redistributable composite commercial ML corpus. **No museum photographs, rights-holder letters, third-party image bytes or raw scans are committed.**

Benchmark independence remains **UNKNOWN/QUARANTINED**. HPDB scans Möller's published facsimile, which may have publication ancestry shared with AKU-PAL facsimiles and the public AKU portions of HieraticBench. A difference in exact byte hash or published object-name spelling is not proof that it is a new physical source.

## Pre-results frozen original-pixel pilot

The pilot is deliberately about **published-palaeography row-image classification**, not photographed manuscript transcription. HPDB's IIIF region URL can contain a multi-exemplar printed-sign row: do not describe one cropped publication strip as a single isolated handwritten sign.

- Original source metadata pinned previously: repository `data/references/hpdb/metadata_manifest.json`, upstream published HPDB `public/data/index.json` at commit `a8cfcf52632487cf1d61a5793d84c9b2f7192d5a`, original source Git blob `6efc36471b47255cfc03f6ba8cf9c887a293bb89`. Verified overall universe: **2,065** items, **1,439** unambiguous single Gardiner mappings, 214 source *printed-book page* groups, NOT 214 physical manuscripts.
- Prospectively fixed printed-sign label classes, alphabetically: **D50, M12, V1, Z1**.
- Prospectively fixed design: **first two item IDs of each label from each printed volume** with a valid exact original HPDB IIIF path, 4 labels × 3 printed volumes × 2 items = **24** original-pixel stimuli.
- Train on printed **volumes I and II**: 16 original pixels. Test on printed **volume III**: 8 original pixels. Print-volume proxy partition membership is disjoint, but **physical original papyrus/scribe independence is unknown**.
- Source only `https://iiif.dl.itc.u-tokyo.ac.jp/iiif/asia/hp/...` with strict HTTPS same-domain final URL, maximum JPEG size 500 KB and <=1 million decoded pixels. No large archive download, credentials or bypass; 800 ms sequential delay between requests, abort cleanly on HTTP429 or errors.
- Actual RGB/JPEG converted to autocontrasted grayscale and **16×8 pixel** feature vector. Frozen Euclidean 1-nearest-neighbor classification, deterministic item-ID tie break. True learned/reference visual data from 16 original image strips; no VLM or fake synthetic fixture.
- Separately score the no-image prior: majority class of training labels, with lexical stable tie break.
- Report all 24 raw-image SHA256, original dimensions, source IIIF identifiers, genuine test image predictions, numerator/denominator 8 and genuine failure. Outbound artifacts contain metadata/predictions only, never source images.
- Do not interpret accuracy at n=8 as an accepted generalization result. Printed-volume grouping does not substitute manuscript-level split; class labels are catalogued labels, not independently blind original-manuscript sign gold; this corpus may overlap the benchmark.

**Execution:** `python -m tools.research_hpdb_original_pixels --output /tmp/r034-real-original-pixels.json`. Hosted workflow `.github/workflows/w27-utokyo-iiif-original-pixels.yml` runs 12 adversarial/local tests followed by live original IIIF sources on the GitHub runner. A blocked retrieval is a real negative result, not a synthetic pass.

## Acceptance boundary

A successfully executed original-source sample and 1NN result establish a new, reproducible **authentic historical publication pixel classification diagnostic**. They **do not** satisfy DATA-008, SPEC-002/003, VLM-001, EVAL-003 or the independently reviewed Cat.1880 first physical line issue #136. No capability milestone, original papyrus reader, VLM, held-out blind accuracy or source-disjoint physical handwriting claim is awarded.

To progress beyond this work, independently resolve printed-facsimile versus underlying papyrus accession equivalence, HieraticBench/source-history overlap, production item-specific rights/annotations, at least one suitable authenticated original manuscript photograph with matched scholarly labels, and strict physical-support train/dev/test eligibility. Do not use this quarantined evaluation cohort as training/development material in a future claimed official benchmark.

## Citation/credit for original materials

'Hieratische Paläographie' by Georg Möller, original volume scans courtesy Asian Research Library, University of Tokyo (U-PARL). Derived/region-cropped and resized for W27 research; original images not republished. HPDB project by Masakatsu Nagai, Toshihito Waki, Yona Takahashi and Satoru Nakamura. Use both source and provider attribution in any publication.
