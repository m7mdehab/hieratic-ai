# DATA-008 — ML-ready corpus v1 assembly and release

- **Task ID:** DATA-008
- **Weight:** 3.0 capability points, awarded only by independent overseer acceptance
- **Branch:** `task/DATA-008-ml-ready-corpus`
- **Depends on:** DATA-003, DATA-005, DATA-006, DATA-007, and EVAL-004 — validated infrastructure contracts
- **Write scope:** `tasks/DATA-008.md`, `data/releases/**`, `schemas/dataset_release.schema.json`, `tools/release_corpus.py`, `tests/data/test_corpus_release.py`, and `docs/data/CORPUS_V1_RELEASE.md`
- **Canonical status/progress:** maintained only in `TASKS.yaml` and `PROJECT_STATE.yaml` by the overseer

## Objective

Assemble immutable, reproducible dataset releases from the accepted acquisition, preprocessing, annotation, sign-mapping, alignment, expert-review, and split contracts. Refuse inputs that lack item-level identity, provenance, compatible rights, intended-use evidence, benchmark-overlap clearance, or leakage-safe split membership. Preserve uncertainty, alternative readings, missing gold, and reviewer disagreement.

This task separates two milestones:

1. **Release infrastructure:** executable validators/builders, schemas, reproducible synthetic fixtures, security and integrity gates, and a blocked-production assessment. Passing infrastructure tests demonstrates software behavior only.
2. **A real `corpus_v1_release`:** actual rights-cleared source images and annotations/mappings, reviewed scholarly gold, complete acquisitions and transformations, and independently checked train/dev/test partitions. This is a separate evidence-bearing corpus milestone. Synthetic fixtures, synthetic rights attestations, empty or illustrative splits, or this task brief do not satisfy it.

## Dependencies and interfaces

- DATA-001 source registry and licensing policy define source identities, rights classes, intended uses, attribution, and benchmark quarantine.
- DATA-002 acquisition manifests define item/source-object identity, retrieval provenance, rights snapshots, hashes, and overlap decisions.
- DATA-003 preprocessing requests and artifacts define transformation lineage and original/preprocessed hashes.
- DATA-004 annotations preserve document/page/line/sign/token identity and layer-specific readings, alternatives, and missingness.
- DATA-005 mappings preserve sign identity and scholarly provenance separately from transliteration.
- DATA-006 alignments connect image regions to annotation targets and identify score-eligible gold conservatively.
- DATA-007 review records preserve independent decisions, disagreements, adjudication, and review state.
- EVAL-004 split metadata/manifests define deterministic train/dev/test membership, exclusions, overlap checks, and leakage groups.

The release tool consumes those contracts. It does not download assets, grant rights, decide scholarly readings, resolve disputed overlap by assertion, score a model, or redefine split policy.

## Required deliverables

- Versioned input-bundle and output-manifest schemas.
- Deterministic CLI validation and release construction with stable dataset version IDs, input hashes, lineage, partition summaries, exclusions, and audit evidence.
- Five-file immutable publication contract: `release-manifest.json`, `export.jsonl`, `dataset-card.md`, `rejection-report.json`, and `audit-trail.json`.
- Fail-closed checks for source/object identity, rights and attribution for images/annotations/mappings, item permissions and intended use, benchmark quarantine/overlap, hashes, score eligibility, and source-object/document/page/image/near-duplicate leakage across partitions.
- Safe input-size and output-size limits, bundle-relative path containment, symlink rejection, and atomic no-clobber publication. Concurrent publishers must not replace each other's outputs; a final destination must be absent before a complete staged release becomes visible.
- Synthetic positive, negative, mutation, integration, concurrency, and reproducibility tests. Fixtures must be repository-authored and contain no restricted images or benchmark answers.
- A metadata-only rights-readiness inventory and blocked-production assessment that never imply permission.

## Acceptance criteria

### Release infrastructure evidence

- [ ] Accepted upstream contracts are connected with stable identities, hashes, permissions, lineage, and split membership.
- [ ] Unlicensed, unknown-rights, evaluation-only, quarantined, unresolved-overlap, inconsistent, hash-mismatched, oversized, path-escaping, and leakage-contaminated inputs fail closed.
- [ ] Uncertainty, alternatives, missing readings, and reviewer disagreements survive deterministic exports.
- [ ] Release identity and all five output artifacts reproduce deterministically from identical inputs.
- [ ] Publication is atomic and no-clobber under concurrent writers, including when an empty destination or symlink appears immediately before finalization; failures clean private staging output.
- [ ] `synthetic_test_release` cannot be relabeled as `corpus_v1_release`.
- [ ] Full governance, data, linguistic, evaluation, and state/source-registry validation pass locally and required hosted CI passes on the exact reviewed commit.
- [ ] No third-party raw assets, benchmark answers, canonical progress/status changes, or self-awarded points are added.

### Real corpus evidence required before claiming DATA-008 complete or awarding 3.0 points

- [ ] Genuine source objects have independently verified per-item rights for the actual training/development and redistribution uses, with attribution and transformation obligations.
- [ ] Real DATA-002 acquisitions and DATA-003 artifacts match the admitted original objects and content hashes.
- [ ] DATA-004 annotations, DATA-005 mappings, DATA-006 alignments, and DATA-007 expert review provide independently audited, appropriately licensed gold while retaining uncertainty and missingness.
- [ ] A real EVAL-004 release split passes source-object, document, page, original/normalized image, benchmark, and reviewed near-duplicate separation.
- [ ] Independent overseer review confirms dataset adequacy, subgroup coverage, legal/provenance evidence, export terms, and that the release is actually suitable for the claimed ML use.

No minimum scientifically adequate sample size is specified by this task. The overseer must assess adequacy separately; a non-empty or structurally valid synthetic split is insufficient.

## Scientific, rights, and security limitations

- Dataset assembly is data plumbing; it establishes no model capability, performance score, or validated experiment.
- Rights fields in manifests are evidence references and snapshots, not legal determinations or grants of permission. Unknown rights mean no admission.
- HieraticBench assets, answers, and exact/near duplicates remain evaluation-only and excluded from training/development.
- The checked-in fixture is synthetic. It is never an independently licensed training corpus.
- No third-party materials may be downloaded or committed under this task without separate explicit authorization and verified rights.

## Evidence required for overseer review

Return the exact branch/head SHA and PR, changed-file list, CLI validation and deterministic build identities, complete relevant suite results, exact-head hosted workflow URL/conclusion, scope validation, concurrency/no-clobber regression evidence, rights-readiness/blocker summary, limitations, and the criterion-by-criterion checklist above. A passed synthetic test suite is evidence for release infrastructure only. Do not edit canonical task state or claim the real-corpus milestone without the independent evidence above.
