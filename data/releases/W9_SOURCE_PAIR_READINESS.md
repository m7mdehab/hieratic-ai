# W9 real source and image–reading readiness assessment

Assessment date: 2026-10-09. This is a W9 evidence supplement for the existing DATA-008 readiness assessment. It does not modify canonical state or authorize use.

## Results

| Evidence level | Count | Status |
|---|---:|---|
| Actual source photo files acquired into the restricted user-local vault | 2 | Cat.2044/013 W8 Commons original JPEG; Cat.1883 + Cat.2095 RIME Fig. 6 article-hosted TIFF |
| Distinct physical supports represented | 2 | Cat.2044/013 and the single joined Cat.1883 + Cat.2095 support |
| Complete public line readings with verified reuse terms suitable for this release | 0 | No textual license permitting this project's training/redistribution use has been independently verified |
| Line-level image/text alignments with independent review | 0 | The W9 RIME evidence reaches only unreviewed column-envelope geometry; Cat.2044 face/writing-unit correspondence remains unresolved |
| DATA-008 production items admitted | 0 | Production authorization remains hard-disabled; rights, benchmark, gold, review and split gates remain incomplete |

The RIME TIFF is 6,585 × 4,718, 36,023,444 bytes, SHA-256 `c4b878ca5b6b6c22d0b4b1574d4f8e95072d651c38cb03d49f3cf73c5f6052b9`. It is the RIME Fig. 6 scan credited to Museo Egizio and digitally processed by Martina Landrino, not claimed as the first-generation museum master. The figure image is supported as CC BY 2.0 by the RIME author guidelines and exact figure caption. This does not establish a license for the article transcription/translation. The text content has not been copied into this repository, training data, or labels.

The RIME edition is a viable *bibliographic reading candidate* for this witness: it identifies the five adjoining fragments, the recto's three columns and line counts, and section/line references. The lineage is one physical support, not two independent manuscripts. The article itself notes uncertainty in line assignment at an adjacent-column boundary and reports difficulty identifying some signs. Our geometry packet maps approximate column envelopes only and explicitly keeps that dispute unresolved; it is not a verified image-to-line alignment or gold.

## Candidate-by-candidate disposition

| Candidate | Image / exact identity | Reading evidence | W9 decision |
|---|---|---|---|
| Cat.1883 + Cat.2095, RIME 6 (2022), Fig. 6 | Exact 6,585 × 4,718 TIFF acquired privately; article figure credits Museo Egizio scan, digitally processed by Landrino; CC BY 2.0 image evidence | Scholarly edition available online with col./line pointers. Article text license not verified. No line text copied. One five-fragment support; boundary ordering and some readings remain disputed. | Best first-pair research lead. Photo allowed for attributed private geometry work; no line-level match, source registration, training, evaluation or release. D2/D3/D6 evidence is separately proposed on PRs #96–#98 and is not merged/accepted here. |
| Cat.2044/013 | W8 authentic 7,063 × 3,947 Commons original JPEG, CC0, SHA-256 `569e8e5bb446588481481bfea823fc95383bb7076270363c666f868b7fa5b912`; one support | Official TPOP public record describes multiple recto and verso writings and identifies an editor, but no independent text-reuse license or exact photograph-to-writing-unit mapping was verified. Commons title's Ramesses VI conflicts with TPOP's Ramesses V metadata. | Image usable for local inspection; line matching, attribution, text rights and benchmark overlap remain unresolved. Keep blocked; do not select a king/period. |
| Cat.1880 / Strike Papyrus | Commons file metadata indicates CC0 image and multiple views of the same support; no W9 download | Multiple historical and modern editions increase overlap risk; exact text license and image-to-line correspondence not established in this review. | Rejected for first pair: famous-work/edition/benchmark leakage risk remains high and unresolved. No download. |
| TPOP-1896, TPOP-1971, TPOP-1966, TPOP-2021, TPOP-NECROPOLIS-5 | Existing R-016 metadata-only candidates; no W9 image bytes acquired | Exact licensed line readings and image/side links not established in W9 | Blocked by the current pinned R-017 overlap screen and item-rights/identity gaps. Preserve prior readiness dispositions. |
| MET-561345, MET-561392, MET-561361, MET-561391, MET-561407, MET-561409, MET-561410, MET-561413, MET-561621 | Existing W6/W7 public API metadata candidates; no W9 image bytes acquired | No matched, reuse-cleared reading identified in this search | Metadata only; exact item/view, textual witness, rights, benchmark/edition independence and alignment remain unproven. |
| Pleyte and Rossi, *Papyrus de Turin* (1869–1876), plate XXIX | Public historical facsimile bibliographic lead cited by later scholarship for Cat.1883+2095; it is a facsimile, not a current original photograph | Old edition may be public domain, but exact digital page, line correspondence, transcription accuracy and source lineage were not verified enough for inclusion. | Further research lead only; no text or plate bytes copied. It cannot substitute for exact current-photo alignment or expert-reviewed gold. |
| Tabin/PaPYrus, Isut, HieraticAI Westcar, HPDB, AKU-PAL, TLA, DDD | Existing DATA-001 rights inventory | No W9 per-item image + reading pair with cleared training/redistribution rights was independently established | Retain the existing source-registry dispositions. DDD/HPDB/AKU-PAL conditional terms need per-item permissions and benchmark/lineage review; Papyrus/Isut/Westcar unknown; TLA bulk use prohibited; no data fetched. |

The existing R-016/R-017 assessment remains the governing benchmark screen: it compared 15 public candidates against 266 pinned public metadata records (2 sealed records excluded), but a zero literal metadata match is not proof of image, edition, or source independence. No benchmark image, answer, or sealed item was accessed or copied for W9.

## W9 artifact and transformation evidence

- The image acquisition packet, exact hash, source URL, image-use basis, and blocked-use boundary are proposed on DATA-002 PR #96.
- A private deterministic decode of the exact TIFF produced an outer photographed-content bounds overlay (`1800 × 1290`, SHA-256 `0fa9b1eff8aa5fedebc0b062272fe1619df3185ce7e2b6ab775b89cbdb6ecf97`) and private processing manifest. The box includes the photographed ruler and does not segment papyrus or text. The private artifact stays outside Git.
- A reference-only geometry packet on DATA-006 PR #98 contains three unreviewed approximate column envelopes and edition section pointers. It has no DATA-004 annotation ID, no line-level alignment, and zero scoreable targets.
- No restricted TIFF, overlay, private path, article transcription, translation, or reviewer/permission document is committed.

These PRs are independent proposals based on `main`. Until independently reviewed/merged and the source is admitted through DATA-001/002, their packets do not constitute accepted upstream inputs.

## Production decision

**Production release: BLOCKED. DATA-008 real-corpus credit: 0/3 pending independent acceptance.** Infrastructure and source discovery do not satisfy corpus admission. No eligible train/dev/test item exists from this W9 evidence. There is no independently protected trust root onboarding, independently authenticated rights-holder/reviewer authority, verified permission-letter bytes, substantive rights determination for textual readings, independent expert adjudication, line-level gold alignment, or leakage-reviewed split.

No text reading, rights grant, expert review, benchmark clearance, training experiment, model performance score, or production corpus is claimed. No canonical progress, task status, or weight was changed.

## Next lawful gates

1. Establish primary official text-use terms for the RIME article or use a separately verified public-domain reading, with exact bibliography/page and correspondence to the same Cat.1883 fragment.
2. Independently inspect line positions in the acquired image and adjudicate RIME's disputed boundary/ambiguous readings; preserve alternatives and missingness.
3. Determine exact Cat.2044 recto/verso writing units against the W8 pixels and identify an independently reusable line reading; retain its Ramesses V/VI metadata discrepancy unresolved until supported.
4. Have governance register and review each source, rights record and overlap decision; do not admit a source from this supplement alone.
5. Obtain independent expert review and protected authority onboarding, then build leakage-safe train/dev/test partitions and rerun the production release validator.
