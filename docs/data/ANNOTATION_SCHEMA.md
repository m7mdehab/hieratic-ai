# Canonical annotation schema

The annotation model follows the validated FND-003 layered reading model and EVAL-001's metric gold fields. Its hierarchy is source asset and registry record → document/object → page/surface → region → line/sequence → sign/group → linguistic layers → review and uncertainty. Fields can be omitted when a dataset does not provide that layer; signs, geometry, and linguistic analysis are not mandatory for every line.

## Identity and provenance

`annotation_id`, page, region, line, sequence, sign, group, token, layer-value, and review IDs are stable identifiers, not array positions. `provenance.source_registry_id` links to DATA-001. Source object ID, URL, asset references, optional SHA-256 and acquisition-manifest references preserve provenance. `rights_provenance_ref` points to the relevant source/item decision; legal prose is not copied into annotations.

Document metadata carries period/date range, geographic provenance, material/support, genre/register, and scribe group when known. Unknown values may be null.

## Layout and graphemes

Every page declares `pixel_origin_top_left` or `normalized_0_1` coordinates. Dimensions can be null if unknown. Region hierarchy and page reading order are explicit; reading-order entries are unique and parent-region cycles are rejected. Line geometry is optional. `rectangle`, `polyline`, and `polygon` geometries retain non-rectilinear shapes.

Lines have a sequence ID and required `grapheme_sequence` layer, which permits a line-level sequence with no sign segmentation. Optional sign records support identity alternatives, allograph references, group membership, abbreviation, visual confidence, and damage state. `sign_groups` represent ligatures and other multi-sign units through constituent sign IDs.

## Distinct reading layers and uncertainty

The schema keeps separate fields for Hieratic grapheme sequence, standardized hieroglyphic rendering, Egyptological transliteration, normalized representation/tokenization, lemma analysis, morphology, syntax, and translations. Each layer uses EVAL-001 gold status values. A layer can retain multiple candidate values, confidence, a selected value, and an explanation. `certain` requires an existing selected value; if it has multiple candidates, the selected value anchors the layer and every other candidate must be explicitly equivalent to it. `uncertain_with_alternatives` retains at least two candidates; illegible and missing values remain explicit rather than becoming guessed text. A token's `sequence_ref` must identify its owning line or that line's sequence, so tokens cannot borrow a reference from another line.

## Review

Review records retain annotator, timestamp, version, reviewer/adjudicator, status, comments, evidence, supersession linkage, and a status-transition history. The validator enforces legal transitions: draft→in_review or revision_requested; in_review→reviewed or revision_requested; reviewed→adjudicated or revision_requested; revision_requested→draft or in_review; adjudicated is terminal. A reviewed record needs a reviewer; an adjudicated record needs reviewer and distinct adjudicator.

## EVAL-001 metric gold-field mapping

| EVAL-001 gold field | Annotation representation |
| --- | --- |
| `script_label` | `/script_label` values and `gold_status` |
| `regions` | `/pages/*/regions` and geometry |
| `reading_order` | `/pages/*/reading_order`; `/lines/*/reading_order` |
| `sign_regions`, `sign_grouping_policy` | `/signs/*/geometry`; `/sign_groups`; group types/constituents |
| `acceptable_grapheme_ids`, `grapheme_reference` | sign identity alternatives and `/lines/*/grapheme_sequence` candidate values |
| `hieroglyphic_reference` | `/lines/*/hieroglyphic_rendering` |
| `transliteration_reference` | `/lines/*/transliteration` |
| `tokenization_profile`, `normalized_tokens` | `/lines/*/normalized_representation` profile and tokens |
| `acceptable_lemmas` | normalized tokens' `acceptable_lemmas` |
| `acceptable_morphology_bundles`, `morphology_features` | token bundles and line `/morphology` layer |
| `translation_references`, `source_reading_for_review` | line `/translations/*/references` plus upstream grapheme/transliteration layers |
| `group_metadata` | document period, source, scribe, material, genre, geographic provenance |
| `expert_review_packet` | annotation provenance, alternatives, uncertainty, review records and evidence |

The mapping exposes concepts, not a requirement that every source populate every metric field. Partial gold is explicit and downstream scoring must respect layer status and coverage.

## Validate an annotation

From the repository root, with `requirements-projectctl.txt` installed:

```bash
python -m tools.annotation_validation validate data/examples/annotation_minimal.yaml
python -m tools.annotation_validation validate data/examples/annotation_ambiguous.yaml
```

Validation checks the JSON Schema, stable IDs, parent/child references, page and line links, geometry coordinates, layer status/value consistency, ligature constituents, token sequence references, review transitions, and DATA-001 source IDs. It does not inspect or acquire source assets.
