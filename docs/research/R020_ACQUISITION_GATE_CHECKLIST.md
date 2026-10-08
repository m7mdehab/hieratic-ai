# R-020 — First real manuscript-image + licensed scholarly line: acquisition control checklist

**State: no actual image–gold pair acquired. No scientific experiment.**  
The template in [R020_FIRST_PAIR_INTAKE_TEMPLATE.json](R020_FIRST_PAIR_INTAKE_TEMPLATE.json) is deliberately filled with **unknown/null, hard-blocking** values. It is not a signature or authorization receipt and must never be accepted as evidence merely because it exists.

## Decision algorithm: no inferred permissions

An item may move only in the following order; every individual gate has its own authorized human or system verifier.

| Gate | Input evidence | Verifier | Allow / refuse rule |
|---|---|---|---|
| **G0: exact museum object** | real institutional URL, actual accession and alternative IDs, support/fragment/writing identity | independent metadata reviewer | catalogue is reproducible and aliases adjudicated; else **candidate-only** |
| **G1: original photo** | official original file/IIIF exposure, pixel bytes, SHA-256, image dimensions, side, image licence and exact use terms | institutional policy + independent digital asset reviewer | image actually exists and permission covers its source; else **no image admission** |
| **G2: rights over edited content** | identified editor/text/version/rights holder, licence for diplomatic readings, translations and maps separately; required attribution | authorized rights holder + independent legal/rights reviewer | source photo CC0 is insufficient; all use-specific requested permissions explicitly granted; else **no text reuse** |
| **G3: original scholarly gold** | exact image-linked line transcription with ambiguity, restoration and geometry, independent expert decisions and version | qualified Egyptologists and adjudicator | a catalogue synopsis, model output or historical hieroglyph transcription is not automatically visual diplomatic gold; else **no scoring gold** |
| **G4: source overlap** | R-017 266-public source metadata + manually adjudicated aliases, textual witness/edition, exact/perceptual image checks | independent benchmark auditor | unknown or potential overlap **quarantine**, no silent training/few-shot promotion |
| **G5: signed admission trust** | accepted rights and Egyptology evidence, protected external trust anchor, authenticated reviewer-specific roles and signed decision bound to original bytes | independent externally authorized authority; overseer governance | a task-writable YAML key or self-declared reviewer identity **never** creates authority; until bootstrap secure **production disabled** |
| **G6: data continuity** | immutable DATA-002–008 source, preprocessing, annotation, gold review, split and release audit | independent technical reviewer | one pair establishes only **source→gold continuity**; no ML-ready set from one line |
| **G7: frozen independent evaluation** | multiple group-independent validated supports, versioned holdout, model inputs, expected universe, image hashes and true inference | VLM evaluator and independent reviewer | no current self-declared receipt or score may be “scientifically certified” |
| **G8: accepted empirical claim** | full attempted denominator, native/official correctly separated metrics, document-clustered uncertainty, leakage reports | scientific overseer | no capability milestone unless an actual scientifically valid model experiment/data acceptance exists |

### Minimum first-pair intake (not a grant)

1. Name an exact institutional **physical support** and each related accession/fragment.
2. Select one specific face/writing/line **only after qualified legibility inspection**.
3. Verify image pixel bytes/hashes, source image file ID, origin, public/permission terms, applicable jurisdiction and intended uses; preserve original media bytes securely.
4. Independently validate original editorial text licence **or** secure new author-owned expert annotations and written licence; treat translation as separate.
5. Store two independent readings and adjudication if available; retain source disagreement, damage and unscorable results, never wash alternatives away.
6. Record sign polygons or line region with coordinate/orientation to a specific image version, plus annotation hash and corrected source linkage.
7. Confirm complete manuscript+edition+image/facsimile exclusions, not just the absent literal item-name string in public benchmark metadata.
8. Produce one read-only, externally reviewed evidence packet, without embedding private agreements in public release artifacts.
9. Run accepted DATA-008 proof **only once actual source rights and an independent protected trust root exist**.
10. Write experiment stage `data_continuity_only`; reject “real training corpus”, “validated language understanding” and “VLM accuracy” claims.

### Independent authority root requirement from W5 review

PR #63 (Luna DATA-008) already introduces Ed25519 verification but must not allow task-writable `data/releases/trust_anchors.yaml` to promote attacker-generated signers. The signed receipt proves integrity relative to a key, **not independently authorized reviewer identity or documentary truth**. Review comment [DATA-008 #63](https://github.com/m7mdehab/hieratic-ai/pull/63#issuecomment-6066703730) requires protected bootstrap / production hard-disable pending real trust. An untrusted researcher cannot self-issue the institutional authorization. The empty trust store is correct.

PR #52 (Gemini VLM-001) likewise must reject local four-string `approved_evaluation_cohort` requests and self-asserted `certified` success. See [VLM #52](https://github.com/m7mdehab/hieratic-ai/pull/52#issuecomment-6066715731). An external DATA-008 receipt must be **independently verified** for the exact source, image, intended purpose and reviewer, not copied as an opaque path. Until external authority exists, model reports are `diagnostic_only`, no science acceptance.

### First-pair binary accept/reject examples

| Intake scenario | Verdict | Specific reason |
|---|---|---|
| TPOP Cat.1896 page with policy saying published photos CC0 and exposed translations | **BLOCK** | no exact image bytes; no independently authorized editor diplomatic line |
| Authorized TPOP photo and edited text without editor ML reuse licence | **BLOCK** | original image and textual-editor rights differ |
| Met 561345 marked Public Domain, no locally verified original pixel/hash and no expert reading | **BLOCK** | catalog description is not gold; no photo hash |
| Met official image with verified CC0 hash and a single unsourced AI transliteration | **BLOCK** | generated reading not independent scholarly gold |
| Independent professional reads a line but annotation is copied from nonlicensed published edition | **BLOCK** | editorial-derived rights unresolved |
| 2 images from Met 561392 in train and test with differing JPEG hashes | **BLOCK** | same physical support across partitions |
| One qualified image-line scholarly pair with verified rights, source and review, no other documents | **ALLOW ONLY DATA CONTINUITY ONCE AUTHORITY VALID** | no population or held-out cross-source ML conclusions |
| Many metadata accession matches absent in R-017, no perceptual/edition audit | **BLOCK TRAIN/FEWSHOT** | a negative string check is not independence |
| Attacker rewrites local signing key and invents three reviewer names | **BLOCK PRODUCTION** | authority provenance untrusted even with valid mathematical signature |
| Frozen genuine cohort independently admitted and actually vision-inferred with auditable heldout gold | **ELIGIBLE FOR INDEPENDENT SCIENTIFIC REVIEW**, not automatic points | all gates still need verification |

### Rights-decision questions for owner

- Is the research intended to distribute a permissively licensed *dataset* or also trained weights with commercial-compatible reuse? Never mix CC BY-NC/CC BY-NC-SA into unrestricted training, regardless of openness of unrelated museum photographs.
- May original CC0 images be obtained from official OA channels and stored in a restricted project custody? Owner must authorize the actual acquisition workflow; no images were downloaded in R-020.
- Is there an authorized identity for museum inquiries? No outreach sent.
- Who may hold protected trust anchors/reviewer qualifications and audit private licence letters? Not the applicant or ordinary task branch.
- Is a two-reader plus adjudicator scholarly annotation arrangement available and lawful? No expert engaged or cost commitment made.

### Technical accession and image validation recipe for future authorized work

Use documented Met object endpoint `GET https://collectionapi.metmuseum.org/public/collection/v1/objects/{ID}` with the chosen existing object ID; expect the exact `objectID`, `accessionNumber`, `isPublicDomain`, `primaryImage` and `additionalImages` keys. **Do not mistake API documentation for a successful object JSON response.** Record the retrieval timestamp, response hash and authoritative image URL; separately retrieve the exact CC0 original photo when authorized; verify format/pixels, SHA-256, dimensions, original vs additional view and accession. Do **not** scrape public search snippets to invent those fields. Met search API moved to paginated v1.1 in September 2026; the documented per-object v1 endpoint remains distinct.

For TPOP, do **not** assume a public bulk API, undocumented image endpoint, anonymous direct file URL or export/registered rights exists. Request approved image-export method and separate editorial-text export/permission at exact writing/line granularity.

### Final fail-closed decision

**Current R-020 = all 15 candidate objects BLOCKED, 0 actual image bytes, 0 matched diplomatic line gold, 0 text/annotation rights approvals, 0 source-cleared heldout sets, 0 authorized model runs.** Advance only upon institution/independent expert evidence; no artificial calendar, citation or signature creates this missing proof.
