# R-017 — Complete public HieraticBench source-lineage screen (pinned revision)

**Audit date:** 2026-10-08 · **Research status:** completed public *metadata* census; scientific source independence NOT established.  
**Upstream:** [alymoursy/hieraticbench at `d587dc990013f18007f1e7a8f56f96ff2f7127e2`](https://github.com/alymoursy/hieraticbench/tree/d587dc990013f18007f1e7a8f56f96ff2f7127e2/data/items)  
**Outputs:** [266-source metadata register](R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl), [15-candidate crosswalk](R017_R016_CANDIDATE_SOURCE_CROSSWALK.json), earlier [R-016 candidate roster](R016_PRELIMINARY_CANDIDATE_ROSTER.yaml).

## 1. Scope, method, and deliberately excluded fields

This is an item-by-item census **of all 266 public files** at the pinned revision. We fetched each public `data/items/aku-*.json` (150), `cbl-*.json` (16), `met-*.json` (37), `wm-*.json` (61), and `ypm-*.json` (2) through the GitHub connector and **projected only** item/source metadata. We did **not** copy benchmark gold, labels, `rungs`, `gardiner`, `notes`, prompts, image payloads or answer content into our registry. We explicitly excluded both sealed `hb-*` files. The registry is produced without duplicates or fetch errors: **266 rows, 266 distinct item IDs**.

The JSONL fields are `id`, `upstream_path`, `object_name`, `object_holder`, `source_url`, `source_file_url` (URL string only; **not downloaded**), `license_claim` (upstream self-declaration, **not** independently rights-audited), `source_group`, `provenance_review=metadata_only`, `corpus_status=QUARANTINE_EVAL_ONLY`. No benchmark materials are admitted for training or exemplars.

The 15 R-016 candidate accessions were screened against the 266 records' concatenated `object_name`, `source_url` and `source_file_url` using conservative literal inventory/accession comparison (not a sophisticated alias resolver). The crosswalk retains zero direct literal matches while preserving a **BLOCKED** admission status for all fifteen. This negative is **not** a proof against alternative catalog IDs, fragment joins, different scans, transcribed editions, image similarity, textual reuse, or contamination in pretrained foundation models.

A future upstream commit, changed item set or altered rights statement invalidates this snapshot's completeness for that newer revision.

## 2. Audited source families

| Family | Public item IDs | Distinct `object.name` strings *within family* | Principal source and confounders |
|---|---:|---:|---|
| AKU-PAL (`aku`) | 150 | **82** | Single hieratograms; 150 unique sign-page source URLs but many signs **from the same original physical support**. Many sources are SVG facsimiles rather than original-camera photos. Never split by hieratogram item ID. [Official AKU-PAL FAQ](https://aku-pal.uni-mainz.de/faq). |
| Chester Beatty (`cbl`) | 16 | 15 | Papyrus-page scans across museum collections. `Pap XXII` appears as both `cbl-0004` and `cbl-0009` with identical object-name and source URL. [Museum copyright](https://chesterbeatty.ie/about/copyright-2/). |
| Met (`met`) | 37 | 37 | Museum-identified objects; some are related accessions / Heqanakht papyri; additional AKU-PAL records show Met objects, so the prefix alone does **not** define provenance. [Met OA](https://www.metmuseum.org/hubs/open-access). |
| Wikimedia Commons (`wm`) | 61 | 55 | Cross-archival image reproductions and famous texts; original institutional source and per-file licence may vary. Includes Met photos, Turin images, Papyrus Berlin and Chester Beatty textual witnesses. |
| Yale Peabody (`ypm`) | 2 | 2 | Public museum records, Yale Peabody CC0 policy subject to individual item terms. [Yale Peabody Information Science](https://peabody.yale.edu/explore/information-science). |
| **Total** | **266** | **Not additive as physical documents** | Sources and items must be linked at museum-inventory/physical-manuscript level. |

Across **all** 266 rows, there are only **191 distinct raw `object.name` strings**; this number is **not** a count of 191 unique original manuscripts. Names differ across museums/transliterations/recto-verso, and some string-identical titles may describe distinct material witnesses.

`license_claim` summary as asserted by benchmark JSON metadata (not independently verified from each original photo or website): CC BY 4.0 168; Met CC0 37; CC0 21; Yale CC0 2; public domain 14; CC BY-SA 4.0 11; CC BY-SA 3.0 9; CC BY-SA 2.0 2; CC BY 3.0 2. The sum is 266. **Never infer a global training clearance from these metadata claims.**

## 3. Concrete multi-item lineage clusters

This is new, directly checked evidence that public benchmark items are not synonymous with independent manuscript witnesses:

| Original-support name as recorded upstream | Benchmark IDs | Immediate protocol consequence |
|---|---|---|
| Brooklyn Museum **47.218.84** | aku-0006, 0031, 0063, 0086, 0130 | One source support, five sign examples |
| D. **Hatnub 25** | aku-0008, 0026, 0110, 0119, 0121 | Five hieratograms from one named inscription |
| Louvre **E 25416** | aku-0017, 0054, 0069, 0090, 0116 | Five sign examples, not five manuscripts |
| Brooklyn Museum **47.218.3** | aku-0025, 0099, 0113, 0133, 0149 | Five examples, same named accession |
| Bancroft/P. Hearst **1282** | aku-0032, 0039, 0112, 0139, 0144 | Five sign instances, one physical-source candidate |
| Berlin Papyrussammlung **P 3057** | aku-0034, 0047, 0061, 0066, 0147 | Five examples from same inventory |
| Met **22.3.517** | aku-0013, 0041, 0118, 0125 | Source family crosses benchmark institutional prefixes |
| Met **22.3.516** | aku-0019, 0082, 0135, 0141 | Same Met collection in AKU-PAL facsimile form |
| Turin **CGT 54050** | aku-0023, 0083, 0128 | Three sign records, one title identity |
| Turin **CGT 54051** | aku-0132, 0150 | Two sign records, one title identity |
| Turin King List **Cat.1874** | wm-0019 and wm-0020 | Two distinct photo files of the same named manuscript |
| Chester Beatty Pap **XXII** | cbl-0004 and cbl-0009 | Same external papyrus collection page in two records |

These are *named-support* relationships, not verified pixel-hash equivalences. Repeated `source_url` occurred for Chester Beatty XXII; most AKU sign URLs are distinct even while their `object.name` identifies a shared source.

## 4. Turin and Met family-level exclusion watchlists

**18 public benchmark items carry explicitly Turin/Museo Egizio names:** AKU `0023,0083,0128` (CGT 54050), `0129` (CGT 57036), `0132,0150` (CGT 54051), `0136` (S.17507/2); WM `0019,0020` (King List), `0032` (S.9598), `0033` (Cat.2164), `0034` (S.9754), `0035` (S.6619), `0036` (Cat.6238), `0037` (S.8618), `0046` (Cat.1986), `0049` (S.6074; Demotic), `0050` (G.5; Demotic). Disambiguate **CGT**, **Cat.**, and **S.** inventory schemes and institutional joins before rejecting or admitting any nearby Turin manuscript.

**11 more AKU-PAL items explicitly cite Met objects** 22.3.516/.517/.518/.520. These are additional to the 37 `met` records; they show why provider-prefix exclusion alone cannot guarantee source independence. Distinct `22.3.*` versus candidate `09.184.*` does not prove absence of shared scribal/textual witness or gallery-photo duplication.

**R-016 candidate comparison:** None of the six TPOP inventory identities or nine Met exact accession identities appears as an **exact literal accession/name match** in any of the 266 screened source fields. This expands R-016's partial 98-record check to all 266 **but does not clear one image**. The Met 09.184.* candidates lie in a Ramesside ostracon accession/excavation family with other 09.184.* Met benchmark objects, and the TPOP candidates remain susceptible to other inventory schemes and known published editions. Every crosswalk entry therefore remains `training_admission=BLOCKED`.

## 5. Required actual contamination audit before any first real corpus

**Identity ledger:** Build an institutional accession canonicalizer with human-adjudicated alias links, external text/reconstruction IDs (Trismegistos where available), writing/face/fragment lineage, edition references and exact provenance source, not auto-merge based on vague titles.

**File identity:** Acquire only approved photos, record original SHA-256 and dimensions, all exposure/side/reproduction relationships, and compute derived image SHA-256 and a perceptual near-duplicate score. Similarity thresholds must be validated against false-positive/false-negative review exemplars; no arbitrary universal threshold as proof.

**Text/edition identity:** Compare scholarly editions, standard text titles and transliteration sequence fingerprints. An edited/transliterated edition of a benchmark witness can leak the answers even if the benchmark image differs completely.

**Scientific independence:** Quarantine entire physical manuscripts and joining fragments across splits; record author/scribe/provenance when known, avoid silently converting unknown scribe identity to “independent”. AKU-PAL drawn sign snippets from the same object must move together. For performance claims on genuinely unseen writing, implement collection/period/scribe/dating subgroup audits where sample sizes permit.

**Version freezing:** Freeze official benchmark commit, exact public item inventory (the metadata register), original source URLs and institutional accession crosswalk. Future benchmark updates require a new ledger version.

**Human review:** An independent reviewer must approve every `not_same_witness` determination with source evidence, dates, and explicit uncertainty; when unresolved, training/few-shot remains blocked. A metadata-only negative means **candidate**, not **independently_cleared**.

**Distinct withheld benchmark:** The sealed two-file family was not inspected; preserve the sealed-answer boundary. No validation of those unseen source identities is claimed. Existing frontier-model pretraining can be contaminated independently and cannot be disproved with local source comparison alone.

## 6. Adversarial contamination scenarios to add to admission testing

1. Same object, AKU sign SVG vs museum high-res image; block despite distinct file hashes.
2. Same manuscript, recto image in evaluation vs verso image in training; treat as one leakage group unless a stronger explicit scientific design justifies separation.
3. Same reconstructed TPOP papyrus under separate fragment inventory numbers; merge as one group.
4. Same named text in historical edition and new museum photograph; require manuscript witness identity, not just text title.
5. Two different source objects accidentally sharing a generic name “Hieratic ostracon”; **do not** automatically collapse without accession proof.
6. Altered cropped/recolored/resized benchmark image; perform perceptual review and source provenance check.
7. Unrelated objects from same Met `09.184` acquisition lot; **do not** automatically equate one acquisition series with the same manuscript, but demand explicit accession-level disambiguation and expert review for suspicious groupings.
8. One CBL Pap XXII view recorded twice; must deduplicate document group even when each item key is unique.
9. False “independently cleared” claim derived only from zero literal accession matches; block.
10. New HieraticBench version introducing a previously proposed training image; require revisioned embargo/quarantine policy before any performance claim.

## 7. Remaining and user-facing truth

**Completed:** all 266 pinned **public** source metadata rows; 15 candidate exact-name crosswalk; practical repeated-source examples; explicit provenance and leakage-risk specifications.

**NOT completed:** original 266 source images, full institutional object alias reconciliation, Met/TPOP item pixels, verified rights per benchmark source, near-duplicate comparison, scholarly alignment, sealed-source audit, downstream foundation pretraining exposure, genuinely independent held-out corpus, or expert approval.

**Decision:** This research substantially improves exclusion evidence, but **0 model capability points** are earned. DATA-008's required genuine rights-cleared, expert-reviewed corpus remains blocked.
