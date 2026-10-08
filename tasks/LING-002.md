# LING-002 — Lexical and Morphological Interpretation

**Status:** ready for implementation review; this document does not validate the task or award capability points.

## Objective and dependency

LING-002 consumes immutable LING-001 normalization manifests (which retain exact DATA-004 annotation provenance) and produces a separately versioned layer of lexical candidates and morphological analyses. Its declared dependency is accepted LING-001. DATA-004 source identities and EVAL-001 evaluation contracts are inherited as provenance/metric boundaries; this task does not alter either contract.

The layer must never rewrite diplomatic transliteration, normalized forms, source annotations, alternatives, uncertainty, or prior linguistic fields. Lexical and morphological output is additive and source-linked.

## Deliverables

- Versioned lexical interpretation schema for entries, lemmas, roots, part of speech, feature bundles, inflection, attestations, historical period, citation, source identity/content hash, confidence, ambiguity and rights.
- Deterministic validation and interpretation CLI, with immutable output identity derived from exact normalization manifest and lexicon content.
- Explicit `interpreted`, `ambiguous`, `unattested`, and `unknown` outcomes; all candidate analyses and source alternatives are retained.
- Fail-closed scholarly citation, registry identity, content hash, rights and intended-use checks.
- Synthetic fixtures and adversarial integration tests; protocol document defining evidentiary boundaries.

## Scientific boundary

The checked-in lexicon fixture is fabricated contract data. It does not claim to represent Egyptian lexical forms, lemmas, roots, grammatical categories, period attestations, or expert consensus. Synthetic entries cannot produce scholarly gold, evaluation results, metric values, task validation, or capability credit. The engine is infrastructure; a real lexical interpretation milestone requires licensed and source-verified lexical material, item-level citation and rights review, domain-expert review, documented morphology and uncertainty, and an independent evaluation design.

The interpreter performs exact normalized-form lookup only. It does not infer lexical equivalence, derive roots, generate paradigms, disambiguate alternatives by frequency, or make unsupported morphological claims. Missing/illegible/pending source readings produce `unknown`; no lexicon match produces `unattested`; source or analysis alternatives produce `ambiguous`.

## Acceptance checklist

- [ ] Schema is versioned and validates lexical, morphological, attestation, citation, source-identity, confidence, uncertainty and rights fields.
- [ ] CLI validates LING-001 manifest content identity and each normalized/diplomatic value hash; source-hash or content drift is rejected.
- [ ] CLI validates lexicon content, exact Unicode form hashes, entry identities, source references, citation verification fields, compatible rights and explicit intended use.
- [ ] Unknown source rights, unverified citations, benchmark-only sources, invalid source IDs and unsupported feature structures fail closed.
- [ ] Multiple lexical candidates and multiple normalized source readings remain separately represented; no candidate is silently selected.
- [ ] `unknown`, `unattested`, `ambiguous`, and single-candidate `interpreted` states have deterministic definitions.
- [ ] Diplomatic text, normalized alternatives, existing annotation analysis and Unicode distinctions remain preserved, including collisions.
- [ ] Repeated build over identical bytes yields identical JSON and release ID; output publication refuses overwrite.
- [ ] Tests cover Unicode/transliteration, source/hash drift, unknown and missing forms, ambiguous and conflicting analyses, unsupported morphology, invalid references/citations, rights failure, collisions and reproducibility.
- [ ] EVAL-001 metric IDs are not reported as scores unless an actual gold/prediction scoring implementation and eligible gold set exist. This CLI computes no metrics.
- [ ] Project state, task statuses, weights, DATA-004, LING-001 and EVAL-001 contracts remain unchanged; actual branch changes pass the registered LING-002 scope.
- [ ] Synthetic-only evidence is clearly labeled non-scientific. Real-source lexical interpretation and independent expert review remain pending.

## Rights and limits

Unknown, restricted, noncommercial, evaluation-only and unverified source material cannot be admitted by a lexicon declaration alone. Scholarly candidate entries require a registry source with verified primary status, compatible project rights, citation locator plus verification evidence, stable source-object ID, source content hash and independent rights review. The engine does not itself verify a remote citation or grant rights; its data must already have passed that review. No external lexical source, TLA extraction, benchmark answer, or third-party material is included in this infrastructure task.
