# EVAL-006 — Freeze Sealed Evaluation and Contamination-Response Protocol

**Owner:** Overseer (approved W2)  
**Dependency status:** EVAL-004 and EVAL-005 validated  
**Weight:** 2.0 capability points upon independent acceptance  
**Status:** Accepted by overseer after independently passing governance, sealed and evaluation CI (PRs #35/#40; canonical state acceptance separate).  

## Objective

Freeze a concrete, independently checkable process for unseen Hieratic evaluation. Prevent access to sealed gold before a model/configuration freeze, test-driven prompt/model adaptation, leaked or overlapping training items, post-hoc metric cherry picking, and unsupported public research claims.

## Acceptance requirements

1. Immutable, versioned sealed evaluation protocol grounded in EVAL-001/004/005, external HieraticBench quarantine and expert-review integrity.
2. Sealed dataset rights and benchmark-overlap clearance rules separate from training permissions; no public raw images, references, gold or model outputs.
3. Pre-registration/freeze records capturing model/config/data/splits/metrics/corpus eligibility/analysis plan hashes, roles, timestamps and conflicts.
4. Strict blind scoring: separate training/developer, sealed custodian, scorer/adjudicator, and release authority.
5. Executable negative controls for contaminated items, insufficient blind separation, unreviewed gold, incomplete attempts, metric drift, after-the-fact protocol changes, lack of document-group uncertainty, and unsupported score publication.
6. Versioned machine-readable release record schema, validator, synthetic example(s) and CI.
7. A contamination incident taxonomy, triage workflow, quarantine and re-evaluation rules, and scientifically explicit withdrawal/correction policy.
8. Boundary: a frozen *evaluation protocol* does not mean a real blind dataset/model run exists. Zero experiments and trained models remain until actual accepted evidence.

## Write scope

`tasks/EVAL-006.md`, `eval/sealed/**`, `schemas/sealed_eval.schema.json`, `tests/evaluation/test_sealed_eval.py`, `docs/evaluation/SEALED_EVALUATION_PROTOCOL.md`, `.github/workflows/sealed-eval.yml`.

No edits to Luna's DATA-003/005/006/007 branches, Antigravity dashboard, or current canonical task state.