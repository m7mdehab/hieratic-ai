# Sign identities and palaeographic mappings

`schemas/sign_mappings.schema.json` keeps three distinct claims: observed Hieratic form, hieroglyphic correspondence, and transliteration value. Null/unresolved values are valid and preferred to fabricated equivalence. Context and historical qualifiers are attached to candidate claims. Relations are many-to-many and each mapping/variant carries provenance citations with a claim scope and optional locator; status and confidence do not replace evidence.

Run `python -m tools.sign_mappings validate FILE`, `lookup FILE ID`, or `export FILE [--format json|yaml]`. The validator checks schema, unique record/variant/relation/citation IDs, citation presence for supported claims, references, duplicate edges and cycles in `variant_of`/`subclass_of`. Citation URLs are not treated as proof: `verified_metadata` records that reference metadata was checked, while scholars still review the cited content and claim. No source metadata or historical mapping is included in the synthetic example.

To add a real mapping, cite a verifiable scholarly source and a precise locator, state which representational layer it supports, preserve competing readings as disputed candidates, and review conflicts independently. Never infer transliteration from a hieroglyphic glyph or use a hieroglyphic rendering as the observed Hieratic shape.
