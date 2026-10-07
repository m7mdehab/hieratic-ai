# DATA-004 — Canonical Hieratic Annotation Schema

- **Task ID:** DATA-004
- **Branch:** `task/DATA-004-annotation-schema`
- **Owner:** execution agent
- **Depends on:** FND-003, DATA-001 — validated
- **Status at dispatch:** ready
- **Primary write scope:** `schemas/`, `docs/data/`, `tests/data/`, small repository-authored fixtures
- **Do not edit:** project progress/weights, external source rights, benchmark gold data, raw third-party assets

## Objective

Define the canonical machine-readable annotation model that every later Hieratic dataset, alignment tool, expert-review workflow, specialist model, and VLM training pipeline can use.

The schema must preserve the layered structure established by FND-003 and the gold/evaluation requirements established by EVAL-001.

Do not flatten the problem into one text string.

## Required conceptual hierarchy

The schema must be capable of representing:

`source asset -> document/object -> page/surface -> region -> line/sequence -> sign/group -> linguistic layers -> review/uncertainty`

Not every dataset must populate every layer, but the canonical model must support them.

## Required entities/fields

### Provenance / document

Support at least:
- annotation/document ID;
- source registry ID;
- source object ID;
- source URL;
- asset/provenance/hash references;
- collection/institution;
- period/date range;
- geographic provenance;
- material/support;
- genre/register;
- scribe/writer ID/group where known;
- rights/provenance reference, not duplicated legal prose.

### Page/surface and layout

Support:
- page/surface ID;
- dimensions/orientation where known;
- regions;
- line/column geometry;
- reading direction/order;
- parent/child relations;
- irregular/non-rectilinear geometry where polygons are available.

Coordinates must declare the coordinate system.

### Sign / grapheme layer

Support:
- sign/group ID;
- geometry;
- grapheme identity;
- alternative identities;
- allograph/palaeographic references;
- ligature/group membership;
- constituent signs where known;
- abbreviation flags;
- visual confidence;
- damage/legibility state.

### Textual layers

Support distinct fields for:
- Hieratic grapheme sequence;
- standardized hieroglyphic rendering;
- Egyptological transliteration;
- normalized linguistic representation/tokenization;
- lemma;
- morphology;
- optional syntactic/structural information;
- modern-language translation(s).

These must not be collapsed into one field.

### Ambiguity and uncertainty

Align with EVAL-001 gold statuses:
- `certain`;
- `uncertain_with_alternatives`;
- `illegible_unscorable`;
- `missing_annotation`;
- `adjudication_pending`.

Support:
- multiple acceptable readings;
- localized uncertain spans;
- alternative sign/transliteration/lemma/morphology/translation values;
- confidence where meaningful;
- explicit abstention/unknown rather than fabricated certainty.

### Review / annotation provenance

Support:
- annotator ID or pseudonymous reviewer ID;
- annotation timestamp/version;
- reviewer/adjudicator;
- review status;
- comments/notes;
- source citation/evidence;
- change/revision linkage where practical.

## EVAL-001 compatibility

The schema should expose, directly or through well-defined mappings, the gold fields needed for the metric contract, including:

- script label;
- regions;
- reading order;
- sign regions;
- acceptable grapheme identities;
- grapheme references;
- hieroglyphic references;
- transliteration references;
- tokenization profile;
- normalized tokens;
- acceptable lemmas;
- morphology bundles/features;
- translation references;
- group/generalization metadata;
- expert review packets.

The annotation schema is allowed to use richer internal names, but document the mapping.

## Deliverables

At minimum:

1. `schemas/annotation.schema.json` — canonical JSON Schema.
2. `docs/data/ANNOTATION_SCHEMA.md` — human-readable semantics.
3. `data/examples/annotation_minimal.yaml` — repository-authored minimal valid example.
4. `data/examples/annotation_ambiguous.yaml` — example with alternatives/uncertain span/ligature.
5. `tests/data/test_annotation_schema.py` — validation and negative tests.
6. Optional small validator/helper only if it materially improves maintainability.

No third-party manuscript content is required; examples must be synthetic placeholders.

## Validation invariants

Tests/schema must reject at minimum:

- duplicate IDs within the relevant annotation scope;
- child pointing to nonexistent parent;
- invalid coordinate system/geometry shape;
- invalid gold status;
- `certain` item containing contradictory unresolved alternatives unless explicitly represented as equivalent;
- `illegible_unscorable` item presented as a single certain reading without explanation;
- ligature constituent IDs that do not exist;
- normalized/linguistic token references to nonexistent line/sequence IDs;
- invalid reviewer state transitions where encoded;
- external source reference not matching a DATA-001 `source_id` when registry-aware validation is implemented.

## Design requirements

- Schema must be extensible without being permissive garbage.
- Use stable IDs rather than array position as identity.
- Preserve provenance and layer boundaries.
- Do not force sign segmentation for every line; sequence-only annotation must remain representable.
- Do not require linguistic annotation for purely visual datasets.
- Do not require geometry for sources that provide only sequence/text data.
- Permit partial annotation while making missingness explicit.
- Avoid dataset-specific field names unless isolated in an extension block.

## Acceptance criteria

- [ ] Full semantic hierarchy is represented.
- [ ] Sign/allograph/ligature concepts are represented.
- [ ] Layout and reading order are represented.
- [ ] Transliteration, normalization, linguistic analysis, and translation are distinct.
- [ ] Multiple valid readings and uncertainty are first-class.
- [ ] Expert/reviewer provenance exists.
- [ ] DATA-001 provenance linkage exists.
- [ ] EVAL-001 required gold concepts have a documented mapping.
- [ ] Synthetic minimal and ambiguous fixtures validate.
- [ ] Negative tests reject broken references/states.
- [ ] No external raw assets are added.
- [ ] No canonical progress/status is self-modified.

## Prohibited shortcuts

- one `text` field representing every layer;
- mandatory per-sign segmentation for all examples;
- silently choosing one reading from an ambiguous gold set;
- embedding copied source-license prose in every annotation;
- inventing Hieratic sign mappings not present in canonical research;
- using real benchmark sealed answers as examples;
- making the schema so dataset-specific that another source cannot use it.

## Evidence package

Return:
- branch/commit and PR;
- exact files changed;
- schema/entity summary;
- validation/test commands and output;
- mapping to EVAL-001 metric gold fields;
- acceptance checklist;
- unresolved design questions;
- confirmation fixtures are synthetic and no third-party assets were added.

Do not self-mark DATA-004 validated.
