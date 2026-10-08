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


## Wave 8 real-evidence acceptance package (2026-10-09)

**Substantive task implementation:** PR #88. Prerequisite verified independent scholarly text-layer rights records were accepted in DATA-001 source-registration PR #85. This package is not credited for synthetic fixtures or another already accepted task.

- **Authentic primary scholarly resources:** AED-TEI original CC BY-SA dictionary contains **35,052** distinct Egyptological lemma entries with actual historical orthographies, grammatical type labels and optional root/English gloss; AES contains **445** edited sentences from **311** distinct text record groups, **2,526** tokens, **2,305** editor-provided lemma IDs and genuine morphological tags.
- **Source-bound identity and rights:** Upstream Git revisions, AED original dictionary.xml Git blob, AES original JSON Git blob, eight byte-identical-pinned *derived* dictionary partitions, publisher citations, share-alike license and real source registry identities. Both resources are official separate open scholarly data releases, not a scrape of the restricted live TLA interface. No underlying manuscript photograph acquired.
- **Executable lexical layer:** Real Egyptian input forms resolve multiple exact scholarly lemma/POS/root/gloss candidates from AED; other-source textual attestations add real alternative morphology bundles rather than guessing inflection. All alternatives and unknown/unattested cases preserved. Normalization and source text claims are kept distinct.
- **Real controlled experiment:** Exhaustive text-ID-level holdout for all **311** AES text groups (**309** scoreable, two without any labelled lemma). Each target text's AES labels are removed from its candidate-generation index. Shared AED public dictionary remains openly visible and thus not a sealed independent test. Evaluated on genuine editor-provided metadata only, not images.
- **Exact-head hosted evaluation measured 2026-10-09:** 1,621/2,305 (70.3254%) have correct published lemma among candidates; 1,062/1,102 (96.3702%) single-candidate cases correct; 449/753 (59.6282%) published morphology bundles appear among candidate bundles; overall candidate coverage 1,709/2,305 (74.1432%). **Conditional single-case correctness must never be misreported as full recall.**
- **Frozen full-report digest:** 26ad977c29fdd8659157cb02bec04323b6b544dc8ca9425a13825ea629acedee. Generated deterministically by the real code; exact digest verified in unit tests.
- **Hosted QA:** project-governance, source registry, full data, full linguistics and evaluation suites plus scoped-file contract passed; no non-scoped files, no secrets or third-party image bytes, zero provider spend.
- **Legitimate scientific limitations:** AED and AES historically share editorial dictionary sources; different AED/AES text IDs are not independently proven distinct physical witnesses and possible pretraining exposure is unknown. Their published labels are *authentic philological references*, not two-reader blind gold. Metrics describe lexical/morphological **scholarly-text diagnostic**, not image recognition/generalization or translation. DATA-008 and VLM-001 scientific production gates remain disabled.

**Independent overseer review required for task status and any 2.0 weighted capability credit.** No automated self-promotion from source ingestion, project file editing, or the publisher's accessible data.

### Reproduce

~~~bash
python -m tools.lexical_interpretation scholarly-aes verify
python -m tools.lexical_interpretation scholarly-aes lookup --form ꜣ
python -m tools.lexical_interpretation scholarly-aes evaluate
python -m unittest tests.linguistics.test_lexical_interpretation -v
~~~
