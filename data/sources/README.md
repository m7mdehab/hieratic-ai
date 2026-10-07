# Machine-readable source registry

`registry.yaml` is the canonical metadata registry for external resources considered by Hieratic AI. It records source identity, granularity, evidence, rights class, project-use decisions, access constraints, benchmark overlap risk, and unresolved questions. It contains no source images, annotations, model weights, or copied corpus data.

## Validate

From the repository root, with the dependencies in `requirements-projectctl.txt` installed:

```bash
python -m tools.source_registry validate
```

The validator checks the JSON Schema and cross-record rules. It does not repair records or grant rights.

## Field semantics

- `rights_class` uses only the canonical classes in `DATA_LICENSING_AND_PROVENANCE_POLICY.md`. `project_review_markers` carry additional project checks such as per-item review; they do not replace the rights class.
- `rights_text_verbatim` contains exact source wording when the research record preserves it. `null` means no single uniform rights statement applies or the exact wording was not captured. `provenance_notes` explain the boundary; paraphrases must not be put in the verbatim field.
- `evidence_urls` link to the primary records supporting the source facts. `rights_evidence_urls` identify the evidence consulted for the recorded rights decision. A conditional or allowed redistribution decision requires rights evidence.
- Use decisions are `allowed`, `prohibited`, `conditional`, `not_approved`, or `metadata_only`. `conditional` means the stated item-level, attribution, access, or project review must pass before use. `not_approved` is not permission. `metadata_only` permits recording source metadata and links only.
- `development_use` is separate from training and evaluation so benchmark isolation can be enforced explicitly.
- `accessed_at` records the latest source inspection represented by this registry entry. For TLA, the rights summary remains the FND-004 verification; the live license page presented an automated verification gate during the latest spot check, so refresh it before any acquisition.

## Update procedure

1. Read the licensing/provenance policy and the source's accepted research entry before editing.
2. Use an authoritative source URL already supported by project research. Preserve exact rights wording only when it was actually captured; otherwise use `null` and retain the open question.
3. Keep raw external assets out of this directory. Record metadata and links only; DATA-001 does not authorize downloads.
4. Update a registry record and schema together when a field or controlled value must change.
5. Run the validator and `python -m unittest discover -s tests/data -v`. Review changes to use decisions and rights evidence before merging.
