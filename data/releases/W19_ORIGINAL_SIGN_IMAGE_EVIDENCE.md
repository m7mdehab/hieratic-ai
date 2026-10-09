# W19: Original licensed Hieratic signs — exact binary gate

Aim: turn W17's eight genuine publisher original **AKU-PAL sign metadata** records on six physical manuscript supports into verifiable per-item image file digests. Original public Mainz source [image reuse FAQ](https://aku-pal.uni-mainz.de/faq) states that individual imagery may be reused under each original **record's own license**. This W19 execution is bounded to the eight item IDs already inspected in W17.

- Fetch each source-specific JSON and prove stable source ID, response status, content type and original JSON SHA256.
- Determine item-level license from license fields (never from unrelated page text, or from another record) and admit media probing ONLY when the exact item's license is **CC BY 4.0**.
- Extract actual asset links from original metadata, same publisher host HTTPS only. Fetch a maximum of five asset files per eligible item in a bounded 4MB memory-only stream, inspect content type and image magic, hash the original bytes. **Original media binaries are never written to Git or uploaded as artifacts.**
- Publish a source-hash/rights/URL-only receipt for independent retrieval. Unknown formats, absent image endpoints, asset mismatches and rights failures remain blocked.
- The source's grapheme/identifier fields are **publisher annotations** not a second independent gold review. Training and gold admission remain false. Metadata and sign fragments are not source-linked manuscript **whole lines**. Benchmark overlap, manuscript source isolation and independently authenticated reviewer authority remain mandatory.
- Any result is W19 SOURCE IMAGE EVIDENCE only; DATA-008 full `corpus_v1_release`, training, inference scores and project capability progress unchanged unless separately independently certified.
