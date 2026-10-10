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

The first CI pre-results cohort was revised before any pixels or model outputs were observed: using two entries per label inadvertently required mixing Main sign records with Number-use variants. To prevent type confounding, the frozen population was changed to eight Main classes with one item per publisher volume, retaining 24 source requests and 16/8 train/test denominators. This correction is recorded transparently in the Git commit history.\n\nThe pilot is deliberately about **published-palaeography row-image classification**, not photographed manuscript transcription. HPDB's IIIF region URL can contain a multi-exemplar printed-sign row: do not describe one cropped publication strip as a single isolated handwritten sign.

- Original source metadata pinned previously: repository `data/references/hpdb/metadata_manifest.json`, upstream published HPDB `public/data/index.json` at commit `a8cfcf52632487cf1d61a5793d84c9b2f7192d5a`, original source Git blob `6efc36471b47255cfc03f6ba8cf9c887a293bb89`. Verified overall universe: **2,065** items, **1,439** unambiguous single Gardiner mappings, 214 source *printed-book page* groups, NOT 214 physical manuscripts.
- Prospectively fixed printed-sign label classes, alphabetically: **A1, A2, D1, D2, G1, M12, V1, Z1**.
- Prospectively fixed design: **first Main-type item ID for each label in each printed volume** with a valid exact original HPDB IIIF path, 8 labels × 3 printed volumes × 1 item = **24** original-pixel stimuli.
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

## Accepted original-pixel research result — exact hosted evidence

The independently hosted research execution at **https://github.com/m7mdehab/hieratic-ai/actions/runs/38073081844** passed on original implementation head **`3a2324cf27e0034a7a280d48d80e42a5cd2fd113`**. Governance at **https://github.com/m7mdehab/hieratic-ai/actions/runs/38073081862** also passed on exactly that head. Implementation PR **#146** merged as **`61d4bba5746b3d1855a50b5258e3143ecf365d36`**. The workflow ran **13 adversarial tests PASS**, then accessed and decoded **24 actual Tokyo IIIF original digitizations**, retained 24 SHA256 input identities without distributing the images, calculated original image features and evaluated a frozen 1NN against a training-label-only majority control.

- Fixed class set: `A1,A2,D1,D2,G1,M12,V1,Z1` (eight original publisher **Main** rows/volume).
- **16 source strips** in printed volumes I–II gallery; **8 source strips** in printed volume III comparison set; no original print-page group overlap. No manuscript-level holdout assertion.
- Original-pixel 1NN: **2/8 = 25.00%** diagnostic correctness against catalogue sign labels.
- Nonvisual training label-prior baseline: **1/8 = 12.50%**.
- Both denominators are tiny; the +1 sample differential has no accepted statistical claim, expert adjudication, or valid physical support generalization.
- Artifact ID **11677406912**, original run artifact https://github.com/m7mdehab/hieratic-ai/actions/runs/38073081844/artifacts/11677406912, ZIP SHA256 **`d97142f41ef3ede69436e69692a074e5a8870b779b7bb04a7fba109a7ecd9e74`**, retention 14 days. Source image bytes and independently restricted museum materials remain uncommitted.
- The original rights-bearing individual University of Tokyo portal records are **Band 1** https://da.dl.itc.u-tokyo.ac.jp/portal/en/assets/4a1fbed0-f2a2-4cf5-8a0a-fa310c62ca50, **Band 2** https://da.dl.itc.u-tokyo.ac.jp/portal/en/assets/56653a59-0d55-4d1a-a7e3-2242e02859a1, and **Band 3** https://da.dl.itc.u-tokyo.ac.jp/portal/assets/8aaa203c-1c5a-4fef-973b-4fb174d60d37. Each links the same original collection image-use policy; these publisher records—not the HPDB metadata-only CC BY claim—ground the original image reuse route.

### Independent scoring conclusion

This is a distinct third quantitative original-source research axis beyond W23 publisher annotation inspection, W24 nonvisual label priors and W25 mere original image brightness/gradient features. It is the **first observed actual image-conditioned label-matching classifier** on genuinely downloaded, original legally reusable historical Hieratic publication image strips in the project. A **+1.0 qualitative research coverage** increase is independently appropriate (**17 → 18**) to reflect this genuinely new empirical modality and explicit source-rights unlock. **No weighted capability points** are earned (**34.5/100**) because the tiny set is only Möller print-volume-disjoint, benchmark ancestry remains unknown, independent palaeographer-adjudicated gold is absent, and this does not meet DATA-008, SPEC or VLM acceptance. Archive metadata alone and toy 1NN accuracy must never be represented as manuscript reading. This source remains **research-only/quarantined** for official benchmark and corpus-admission purposes.

Next actual advance must use independent **physical-manuscript** image+annotation identity, rights/adjudication, explicit benchmark source exclusion and a larger honest heldout denominator. Do not reuse the Tokyo reference-gallery images for any claimed official benchmark evaluation.
