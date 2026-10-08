# Acquisition manifests

Acquisition manifests describe one source item and the evidence needed to reproduce its acquisition decision. The source registry remains the authority for source rights, allowed uses, quarantine, and attribution. Manifest rights fields are snapshots checked against that registry; they do not grant permission.

## Dry-run commands

From the repository root:

```bash
python -m tools.acquisition plan data/acquisition/examples/hieraticbench-evaluation.yaml
python -m tools.acquisition validate data/acquisition/examples/hpdb-reference.yaml
```

`plan` is offline and never fetches data. It prints a planning result separately from an admission result, plus missing conditions, target path, provenance requirements, and logical fingerprint. The planner never admits an asset to a corpus. A refused request returns a nonzero status. `validate` has the same checks and is suitable for automation.

The opt-in `metadata-fetch-met` command retrieves one allowlisted public object record from The Met's documented per-object API. It is never run by `plan`, `validate`, or CI. It accepts no URL, only the nine dispatched object IDs, refuses redirects, pins a public DNS result for TLS, caps response size, validates object ID/accession and image-reference hosts, and writes one packet with exclusive-create semantics under `data/acquisition/`. It never requests image URLs. Packet publication is supported only on POSIX systems with secure `dir_fd` and `O_NOFOLLOW` operations; the command fails closed on Windows and unsupported filesystems rather than trusting a symlink-swappable parent path. Use a controlled Linux environment to acquire immutable metadata packets. For example:

```bash
python -m tools.acquisition metadata-fetch-met data/acquisition/met/objects/561345.json --object-id 561345
```

The evidence packet records the raw API body SHA-256, response size, timestamp and observed metadata. The raw API body itself and all image bytes are not stored. Existing output files are never overwritten. A failed request emits a stable error code in the packet and exits nonzero.

## W6 Met and Turin evidence

- `met/objects/<objectID>.json` contains one captured Met object API response summary per allowlisted ID, including accession, public-domain flag, canonical object page, original/small/additional image URL metadata and SHA-256 of the exact JSON response body. `original_image_sha256` remains null because no image bytes were requested.
- `met/metadata_packet.schema.json` constrains the packet and hard-codes the metadata-only rights boundary.
- `met/r017_reconciliation.json` screens all 15 R-016 candidates against the pinned 266-row R-017 public metadata snapshot. It preserves every candidate as blocked. A zero literal accession match means only no string hit in this snapshot; it does not prove source independence. All image URLs for one Met object remain grouped as views of that same candidate; no pixel comparison is claimed.
- `met/w6_candidate_evidence.json` records the nine Met candidates and two Turin editorial-access candidates (Cat.1896 and Cat.1971). Turin metadata is carried forward from R-020; no TPOP API/export was assumed or invoked, and no editorial text was copied.
- The source registry currently has no Met entry. These packets are source investigation evidence only; they are not registered acquisition manifests, a rights approval, benchmark clearance, DATA-008 release, or training admission.

## Rights and evidence boundary

The Met API's `isPublicDomain` value and the museum's Open Access statement are separately recorded. Public-domain artwork identity and a general image policy do not by themselves verify the exact image bytes, exact exposure/view, scholarly transcription rights, independent expert gold, or absence of benchmark/edition/pretraining overlap. Current packets show public-domain flags for all nine IDs, but leave exact-photo use determination, image hashes, text permission, and independence unresolved. The runbook remains: (1) independently confirm support, accession aliases, face and writing; (2) obtain the exact original image through an authorized channel; (3) hash and inspect those bytes and map each view/side; (4) establish use-specific image rights and attribution; (5) secure separately licensed editorial text or commission expert-authored diplomatic readings; (6) conduct independent scholarly and rights review; (7) adjudicate benchmark, edition, alias, and perceptual image overlaps; (8) use DATA-008 only after protected authority onboarding and every required review. No outreach or actual image acquisition is performed by this command.

## Policy and conditions

- Each item names a `source_id`; decisions are read from `data/sources/registry.yaml` at runtime. An unknown ID fails closed.
- A manifest's rights class, requested-use decision, quarantine, overlap risk, and attribution must match the registry snapshot.
- `allowed`, `prohibited`, `not_approved`, and `metadata_only` are honored directly. `conditional` use requires an explicit `review_conditions` entry for each access constraint and project review marker in the source record. Every entry must be marked satisfied and include evidence URLs and notes. Placeholder domains cannot satisfy real review evidence. Conditional redistribution uses the same condition set.
- Conditional PER-ITEM training/development plans require item URL, item-specific license, rightsholder, accountable reviewer approval, review evidence/date, and a clear benchmark-overlap assessment with reviewer, evidence, version, and date. A URL by itself never clears an item. High-risk overlap review is also required for other training/development sources marked high-risk by the registry.
- `is_synthetic_fixture: true` permits synthetic references in repository tests only. It cannot produce admission; the output explicitly reports `NOT ADMITTED — synthetic fixture only`.
- Conditional results are labeled `CONDITIONAL PLAN READY` when their review fields are complete. That label records planning metadata only and does not grant use rights or admit an asset.
- `reference` is metadata-only. It cannot declare an acquisition complete.
- A complete direct-download, IIIF, or API acquisition requires the original-byte SHA-256 and retrieval timestamp. Retrieval events preserve repeated retrieval history.
- The logical fingerprint hashes `source_id`, `source_object_id`, and `canonical_object_url` using canonical JSON. Retrieval-event details do not change logical item identity.

All examples are repository-authored metadata. They include no copied corpus records or binaries. The blocked AKU-PAL example deliberately omits item-rights and benchmark-overlap clearance; placeholder domains never count as real evidence.
# W8 local image evidence

`commons/w8_candidate_matrix.json` records the W8 candidate and quarantine decisions. Only the exact Cat.2044/013 p01 original is enabled for a single private local inspection fetch. The Commons file page and Museo Egizio collection policies identify the photograph as CC0; that grants reuse of the photograph and does not grant rights to transcriptions, editions, or annotations.

After reviewing the exact file record, the bounded command is:

```powershell
python -m tools.acquisition commons-image-fetch data/acquisition/commons/CAT2044.json --candidate-id CAT2044
```

The command pins the Commons title, original upload path, file SHA1, dimensions, MIME, timestamp, CC0 license and museum credit. It does not follow redirects, accepts only the two hard-coded public HTTPS hosts, caps the response, rejects an existing vault target, and publishes the bytes with a no-clobber hard link. The unmodified image is stored under `%LOCALAPPDATA%\HieraticAI\private-artifacts\W8`; the tracked JSON output contains hashes and source evidence only, never image bytes or the local path.

The current source registry does not contain a Museo Egizio source record. For that reason the W8 record is private-inspection evidence only, says `NOT_REGISTERED`, and explicitly blocks training and development while benchmark overlap remains unresolved and evaluation is unauthorized. It is not a validated DATA-002 admission or a DATA-008 release item. No detected region or processed derivative is transcription gold. Cat.1880 stays deferred because its edition/benchmark overlap is high risk; p01/p02 and alternate versions are one physical-support group. Met object 561392 remains metadata-only in this W8 work.

The local vault should inherit the user's restrictive LocalAppData ACL. Do not move its image into Git, a public CI artifact, an issue, or an unapproved data store. For support/security review, disclose only the tracked redacted record and exact source links. This process does not fetch institutional correspondence, editorial content, benchmark material, or credentials.
