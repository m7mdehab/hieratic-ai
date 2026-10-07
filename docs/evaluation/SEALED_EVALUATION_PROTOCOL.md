# Sealed Hieratic Evaluation: Freeze, Blind Custody, Contamination and Release

**Protocol:** EVAL-006, version 1.0.0  
**Policy state:** `frozen_policy` — methodology frozen, **no sealed dataset/model run exists**  
**Created:** 2026-10-08  
**Dependencies:** Accepted EVAL-001, EVAL-004 and EVAL-005; FND-005 rights policy; DATA-001 registry.  
**Machine contract:** `eval/sealed/protocol.yaml`, `schemas/sealed_eval.schema.json`, `eval/sealed/protocolctl.py`.

## 1. What is and is not frozen

This document fixes the **rules of blind evaluation** before Hieratic AI trains any candidate model on licensed source data or requests access to an independent sealed holdout. It does *not* freeze a nonexistent dataset, certify document/scribe novelty, score any prediction, or assert that actual expert gold exists.

Distinguish these artifacts:
1. **Policy freeze:** accepted version of this protocol and its SHA-256. Validates allowed research behavior.
2. **Run preregistration freeze:** a later separate sealed-evaluation record with hashes for the actual checkpoint, exact eligible item set, rights decisions, split, overlap reviews, gold manifest, inference code/config/prompt, scorer, metric/normalization contract, analysis plan, full attempt schedule and environment. Must be completed *before* any sealed access.
3. **Score archive:** independently scored attempts after blind prediction collection.
4. **Release decision:** signed reviewer decision allowing *aggregated* evidence to be published.

Any change to a materially frozen item after exposure to sealed gold or scores invalidates the original confirmatory inference. The model cannot get infinite chances by renaming version numbers: a revised method requires an independently fresh holdout and a transparent lineage/withdrawal history.

## 2. Evaluation set eligibility and contamination barriers

The future sealed set must comprise independent documents/scribes and controls with material/date/source provenance suitable for legitimate generalization testing, not random crops of a document observed in training.

Preflight eligibility:
- Source asset: item-specific usage rights and attribution reviewed; sealed custody rights may differ from model-training licenses.
- Source origin: stable institution/item/document/page identifiers, original and normalized SHA-256. Preserve original bytes and transformation records without committing raw restricted assets.
- Disjointness: no overlap across train/dev/sealed by document, page, source object, exact image bytes, normalized content, or verified visual near-duplicates. Reused manuscript editions and translations need human source-lineage review.
- HieraticBench: all 268 benchmark items and all likely source near-duplicates remain quarantined from training/dev. Its two commissioned sealed sentence items have **no public readable gold**; their purported gold must never be manufactured.
- The accepted EVAL-004 high-risk source roster currently reports aggregate counts, not an exhaustive public item image registry. Therefore a declaration `overlap_review.status: clear` is **an auditable claim, not automated evidence of full 268-item comparison**. Independently inspect evidence and coverage before approving actual data.
- Blind gold: authoritative expert references, plausible alternatives, uncertainty and lacunae, and reviewer disagreements recorded. Cases with unscorable or missing gold excluded from specific metric denominators and explicitly counted.

No tool in this task downloads source manuscripts or hidden answer gold.

## 3. Roles, firewalls, and identity

Maintain separate access-controlled actors:
- **Training operator:** can inspect train/dev, freeze model and submit batch predictions; cannot see sealed targets or outcomes before model lock.
- **Sealed custodian:** maintains blind metadata/labels, source rights, access logs and item-selection seed; cannot authorize a release unilaterally.
- **Blind scorer:** receives final prediction archive and adjudicated sealed gold from custodian only after the run freeze; cannot train or adapt the model.
- **Expert adjudicator:** decides scholarly ambiguity masked to model branding and candidate scores wherever possible.
- **Release authorities:** at least two independent people, distinct from training operator, custodian, scorer and adjudicator, inspect the evidence, contamination report and risk caveats.

If staff limitations prevent these role separations, a confirmatory sealed result is **not publishable** as independently blinded evidence; report a development/pilot-only result or obtain independent external reviewers.

## 4. Immutable pre-registration record

Before any sealed query, write a private record with:
- `protocol_sha256`, `freeze_sha256`, timestamp including UTC offset;
- approved corpus manifest, EVAL-004 split and EVAL-002 overlap roster decisions;
- rights and item-level overlap review hashes and reviewer identities;
- adjudicated gold-set manifest hash (without giving model developer gold);
- model checkpoint and configuration hash;
- immutable inference code commit, exact prompt bytes/hash and environment/dependency lock;
- frozen scorer executable hash and EVAL-001 metric/normalization contract hash;
- selected stage-specific metric IDs, denominators, aggregation (document macro), confidence intervals (document-group bootstrap, ≥2,000 resamples), abstention/failure treatment, subgroup analysis and full attempted item list.

The hidden gold must remain inaccessible to the training operator. The preregistration package can be publicly referenced **only by hashes and permitted metadata**, never by labels or copyrighted images. A frozen checksum does not prove the underlying private file exists; reviewer must verify external storage immutability and access logs.

## 5. Run execution, scoring and adjudication

1. Custodian verifies eligibility and approves blind run packet *before* model receives sealed inputs.
2. Training operator freezes model checkpoint, tools/config, prompts, and all scheduled item/attempt IDs. No retrieval from evaluation sources or adaptive test-prompt improvement.
3. Execute inference under controlled logging; preserve even errors, refusals and abstentions. Incomplete attempts cannot vanish to improve denominators.
4. Blind scorer scores each task with the predeclared versioned metric. **Script ID, visual sign recognition, hieroglyphic rendering, grapheme sequence, transliteration, normalization and translation are separate**. Avoid the "fluent wrong reading" failure mode.
5. Expert adjudication handles multiple legitimate readings and disputed gold without changing reference targets to flatter a model. Missing/illegible/pending gold remains unscorable.
6. Independently reproduce raw and normalized scores and per-task denominators, with document-level macro and group-bootstrap uncertainty; report weak sample/subgroup support explicitly. Include independent EVAL-005 failure taxonomy and calibration risk/coverage as **secondary diagnostics**, never a hidden composite primary score.
7. Run signed exposure/contamination checks; do not treat a matching model answer as automatic evidence of either mastery or contamination.

**External HieraticBench:** its official scoring algorithm and leaderboard are authoritative for its published track; project metrics must never silently replace its scoring contract. Original frontier model baselines remain EVAL-003 and require separately approved provider runs.

## 6. Suspected, confirmed, and unresolved contamination

Incident categories include exact/near-duplicate document reuse, benchmark public examples in training, gold/reference exposure, post-hoc metric or prompt adjustment, training on previous sealed outputs, hidden-set access by developer, source-rights conflict, or misleading data lineage.

- **Suspected / unknown:** freeze affected result; quarantine all scientific claims linked to it, log incident ID, evidence, review owner and impact scope. No publishable status.
- **Confirmed:** invalidate affected blinded evaluation; disclose what was compromised and whether prior public claims require correction or withdrawal. A new independent sealed set and new preregistration are required for a fresh confirmatory claim.
- **Dismissed after evidence:** retain incident and adjudication history; a clean release must still go through independent reviewers. The current strict automatic release checker intentionally blocks records with any incident—even dismissed—until a new independent release decision is assembled.
- **Data rights breach:** do not publish or redistribute affected assets; notify custodian/rightsholder according to applicable legal and institutional policy.

The incident log references evidence hashes/URLs; raw gold and proprietary source images never enter public GitHub issues or release bundles.

## 7. Programmatic integrity gate

Run:
```bash
python -m eval.sealed.protocolctl validate-protocol
python -m eval.sealed.protocolctl validate-release \
  --input eval/sealed/examples/draft.synthetic.json
python -m unittest discover -s tests/evaluation -v
```

The sample release record is synthetic, *draft* and deliberately incomplete for execution; it is not a scored experiment.

A future private run record moves across states:
`draft → frozen → scored → adjudicated → publishable`, or becomes `blocked`/`withdrawn`.
The validator checks the declared state's required evidence. In particular:
- freezes must precede sealed access and contain all 15 versioned immutable input fields;
- all roles and rights/overlap evidence are present and non-conflicted;
- score artifacts and completed attempts match the frozen input plan;
- scorer identity has not silently changed;
- published results have independently reproduced scores and document-clustered uncertainty;
- expert gold is blind-adjudicated;
- contamination is reviewed clean;
- minimum two independent release authorities and the full provenance/evaluation artifacts exist.

This is a **necessary but not sufficient** set of controls. It does not cryptographically sign human identities, validate actual provider payments, independently prove rights grants or guarantee that external references exist. A real release needs human scientific and compliance inspection of those hashes, recorded run logs, actual metrics, training exclusions and rights.

## 8. Publication and claim boundary

Allowed public release after passing all checks:
- protocol/metric versions, dataset summary and item eligibility/rights caveats;
- full attempted versus scored denominators, exclusions and abstention count;
- per-layer scores and document-clustered intervals;
- comparison to matched independent baselines when both were actually run;
- source/scribe/period and material strata with small-sample caveats;
- negative findings and known failure categories;
- versioned limitations, contamination and reviewer decision record.

Not allowed:
- privately held gold readings, sealed images, confidential provider raw responses, or unlicensed reproduction;
- a headline "deciphers Hieratic" based on script labels or fluent but unsupported translations;
- claims of superiority without paired matched baselines and independent held-out results;
- silent post-hoc prompt tuning, reference changes or omission of failed attempts.

## 9. Task acceptance

EVAL-006 acceptance validates that the **sealed protocol and its audit software** are frozen and testable. It earns 2.0 roadmap points when the overseer independently reviews and accepts the implementation CI, test fixtures, rights conditions, and published policy. It does **not** imply a sealed run has occurred or that EVAL-003's 1.5 baseline points have been earned. Future data/model benchmarks must separately pass real scientific validation.
