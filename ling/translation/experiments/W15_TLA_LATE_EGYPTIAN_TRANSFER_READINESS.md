# W15 — TLA Late Egyptian real publisher source, AES-train-only transfer readiness

## Status and original-source finding (2026-10-09)

**Result:** New **published Late Egyptian → German sentence target** independently identified with a rights-clear raw-data publication, separate from the Old Egyptian Egyptian-PC grammatical source. The publisher offers **3,606 Late Egyptian original editorial sentences with German translations**, in an exact \`train.jsonl\` release. It does **not** include original manuscript, papyrus, scribe, text-group or physical-witness IDs among its eight row columns. Data publication is CC BY-SA 4.0; images and unreleased live TLA corpus are **not** implied licensed.

**Publisher authority and license**
- Academy's 2025 raw release listing: https://aaew.bbaw.de/daten-veroeffentlichungen
- Exact Hugging Face dataset revision: https://huggingface.co/datasets/thesaurus-linguae-aegyptiae/tla-late_egyptian-v19-premium/tree/8af85941783ba575d5a8985c80c688f948c50040
- Direct object identity: \`train.jsonl\`, original Git HTTP ETag \`74a058b192314b165bec33278fb882ba1333b172\`; **to be confirmed as a Git blob by checking downloaded original bytes**. SHA-256 unknown until entire original asset has been downloaded and hashed. Do not pass a fabricated placeholder as authentic.
- Citation: *Thesaurus Linguae Aegyptiae, Late Egyptian sentences, corpus v19, premium*, version 1.0, January 19, 2025, editors Tonio Sebastian Richter and Daniel A. Werning, Berlin-Brandenburg Academy and Saxon Academy. Attribute scholarly collaborators per publisher card. CC BY-SA 4.0 text data; publisher explicitly says translated text may be used for Late Egyptian transliteration→German model training, **but release terms remain share-alike**.
- Published eight fields: \`hieroglyphs\`, \`transliteration\`, \`lemmatization\`, \`UPOS\`, \`glossing\`, \`translation\`, \`dateNotBefore\`, \`dateNotAfter\`. Missing \`witness_id\`, \`original_source_id\`, \`manuscript_id\`, \`scribe\`, line and image coordinate fields. Do not manufacture manuscript independence from row index or date range.

## Controlled new empirical question

Preregistration committed **before accessing the full raw target JSONL**:
\`ling/translation/experiments/W15_PREREG_TLA_LATE_EGYPTIAN_TRANSFER.md\`
(commit \`319f7baf3bf15df0b29c9d79053f311648bc9a19\`).

The implementation \`ling/translation/w15_tla_transfer.py\` creates an original source-locked lexical memory solely from **3,021 previously published and indexed AES W11 training-donor sentences across 1,130 source text groups**. The TLA corpus will be treated only as targets. The predictor API accepts **one string, publisher Egyptian transliteration**, never TLA \`translation\`, \`UPOS\`, \`glossing\`, \`hieroglyphs\`, \`lemmatization\` or witness dates. Predict exact-form previously attested contextual German word glosses; unknowns explicitly abstain with \`[?]\`; entire identical ordered forms may retrieve a complete German sentence only from the already frozen donor. Similarity/threshold/hyperparameters are not reselected on TLA data.

The assessment then compares all source predictions to the actual publisher's German reference **only after all predictions were generated**, using deterministic multiset word F1 (the same limitations as W8–W13) with complete source/input denominator, abstention and rare/unknown statistics, exact ordered-sentence repeats and source hashes. These measures **do not establish semantic adequacy, fluent translation or a valid Hieratic image-reading model**.

### Source acquisition blocker

At this review, the full original TLA JSONL could be viewed as a public web page but **could not be transferred into the repository work environment as trustworthy original bytes**. The direct URL and publisher digest identity are recorded, but a verified local SHA-256 is not available. Therefore:

- **No real W15 scores have been generated.**
- **No TLA row data, copyrighted image, raw photograph, manuscript transcript or German reference has been committed to the repository.**
- Production \`verify-target\` and \`evaluate\` are expected to **refuse** until the authentic 3,606-row, exact-Git-blob source is supplied locally through approved acquisition, without modifying the source identity. Synthetic malformed-row tests are only software validation.
- Prior W13 official Egyptian-PC TEST remains unopened. TLA published data have no physical-source grouping and share editorial ancestry with previously exposed AED/AES. Even successful 3,606-row scoring would only be a published **cross-corpus text diagnostic** and could not earn LING-003 2.0 capability points without independent semantic adequacy and image→line source proof.

### Reproduction after lawful exact-byte acquisition

\`\`\`bash
python -m ling.translation.w15_tla_transfer verify-train
python -m ling.translation.w15_tla_transfer predict --text 'nꜣy ⸗f'
python -m ling.translation.w15_tla_transfer verify-target --target-path /LOCAL/PUBLISHER/train.jsonl
python -m ling.translation.w15_tla_transfer evaluate --target-path /LOCAL/PUBLISHER/train.jsonl
python -m unittest tests.linguistics.test_translation_layer -v
\`\`\`

The exact raw target is separately available at:
\`https://huggingface.co/datasets/thesaurus-linguae-aegyptiae/tla-late_egyptian-v19-premium/resolve/8af85941783ba575d5a8985c80c688f948c50040/train.jsonl\`.
A local copy with any other original Git object identity must fail the loader. No network access, paid model API or protected benchmark is needed for the code path.

## Experiment gate checklist

- [x] Primary publisher raw dataset + card + CC BY-SA verified and scholarly citation captured.
- [x] Missing physical-witness identifiers found and recorded as a hard boundary.
- [x] Method frozen before full target acquisition.
- [x] Authentic prior AES training donor pinned to hash, 3021/1130 source census.
- [x] Deterministic FORM-only prediction/abstention/translation-memory, conditional gold-only scoring and negative tests implemented.
- [ ] Original TLA \`train.jsonl\` independently acquired and byte-verified in a permitted local environment.
- [ ] 3,606-row evaluation completed with all-denominator source hashes, true score and error breakdown.
- [ ] Independent manuscript and editorial genealogy crosswalk (not available in published 8-field extract).
- [ ] Expert-reviewed image/line and semantic-quality validation.
- [ ] LING-003 scientific acceptance **0/2** until all original gates met.

**Capability:** 34.5/100 verified; historic coverage 14%; zero independently validated real Hieratic model benchmarks; zero newly trained neural models. No status or score change permitted for this engineering readiness result.
