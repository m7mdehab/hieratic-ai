# Capability Roadmap v0.1

The roadmap is a **capability-weighted DAG**, not a calendar plan. The high-level destination is stable; implementations beneath it may change as evidence changes.

The eight capability phases sum to exactly **100 points**. A separate unweighted control-plane gate enables execution but does not itself make the model better at reading Hieratic.

## Phase 0 — Project control plane — mandatory gate, 0 points

Outcome: the repo can coordinate heterogeneous agents, validate state, preserve continuity across chats, and expose live project progress through a web interface.

This gate includes:
- canonical project-state schemas;
- task graph and dependency validation;
- agent rules;
- context/handoff generation;
- CI checks;
- dashboard/control-plane shell;
- safe branch/PR conventions.

No capability points are awarded merely for project-management infrastructure.

## Phase 1 — Research foundation — 5 points

Outcome: the project precisely understands the problem it is solving and the evidence constraints.

| ID | Capability milestone | Points |
|---|---|---:|
| FND-001 | Ultimate goal and scope are explicitly defined | 1.0 |
| FND-002 | Preliminary feasibility/prior-art/data reconnaissance is complete enough to justify the program | 1.5 |
| FND-003 | Writing-system and task-decomposition problem map is validated | 0.75 |
| FND-004 | Primary-source prior-art/data/source registry is verified | 0.75 |
| FND-005 | Licensing, provenance, and redistribution policy is enforceable | 0.50 |
| FND-006 | Reproducibility and agent-governance contract is operational | 0.50 |

Current accepted: FND-001, FND-002 = **2.5 / 5**.

## Phase 2 — Evaluation system — 10 points

Outcome: the project can objectively determine whether a system actually reads Hieratic.

| Capability milestone | Points |
|---|---:|
| Metric specification across script ID, recognition, transliteration, and translation | 1.5 |
| External benchmark ingestion/reproduction | 2.0 |
| Untuned frontier-model baseline suite | 1.5 |
| Leakage-resistant split/test construction | 2.0 |
| Error taxonomy and analysis tooling | 1.0 |
| Sealed evaluation protocol | 2.0 |

## Phase 3 — Data engine — 20 points

Outcome: a legal, versioned, ML-ready Hieratic corpus and annotation pipeline exists.

| Capability milestone | Points |
|---|---:|
| Verified source registry | 2.0 |
| Reproducible acquisition manifests/tools | 2.0 |
| Preprocessing and dataset versioning | 3.0 |
| Canonical annotation schema | 3.0 |
| Sign/palaeography mapping | 2.0 |
| Transliteration/image alignment | 3.0 |
| Ambiguity and expert-QA representation | 2.0 |
| Train/dev/test corpus v1 | 3.0 |

## Phase 4 — Specialist reading system — 20 points

Outcome: purpose-built CV/HTR systems demonstrate real recognition capability on unseen Hieratic.

| Capability milestone | Points |
|---|---:|
| Script-identification sanity control | 1.0 |
| Visual embedding/retrieval capability | 3.0 |
| Sign-level recognition/localization capability | 3.0 |
| Line/sequence recognition capability | 5.0 |
| Linguistically constrained decoding capability | 2.0 |
| Controlled model comparison/ablations | 2.0 |
| Integrated specialist reading system | 2.0 |
| Held-out generalization gate | 2.0 |

Specific algorithms are not fixed by the roadmap.

## Phase 5 — Teach a VLM Hieratic — 20 points

Outcome: a multimodal foundation model demonstrably learns to read Hieratic images rather than only identify the script.

| Capability milestone | Points |
|---|---:|
| Zero/few-shot VLM baseline suite | 2.0 |
| Structured image-to-language supervision pipeline | 3.0 |
| Successful VLM capability adaptation | 5.0 |
| Retrieval-augmented VLM capability | 3.0 |
| Specialist-tool/encoder augmentation | 2.0 |
| Controlled VLM ablations | 2.0 |
| Unseen-Hieratic VLM gate | 3.0 |

Methods may include fine-tuning, adapters, retrieval, specialist tools, curriculum learning, or future techniques.

## Phase 6 — Reading to decipherment/translation — 10 points

Outcome: recognized Hieratic is converted into defensible linguistic interpretation.

| Capability milestone | Points |
|---|---:|
| Transliteration normalization | 2.0 |
| Lexical/morphological interpretation | 2.0 |
| Translation layer | 2.0 |
| Confidence, uncertainty, and alternatives | 2.0 |
| End-to-end vs modular/hybrid comparison | 2.0 |

## Phase 7 — Generalization and expert validation — 10 points

Outcome: capability survives genuinely difficult out-of-distribution and contamination-resistant tests.

| Capability milestone | Points |
|---|---:|
| Cross-document/scribe generalization | 2.0 |
| Cross-period/media/damage robustness | 2.0 |
| Contamination/leakage audit | 2.0 |
| Blind expert evaluation | 3.0 |
| Explicit failure-boundary statement | 1.0 |

## Phase 8 — Public research release — 5 points

Outcome: the work is reproducible, inspectable, and professionally released.

| Capability milestone | Points |
|---|---:|
| Reproducibility package | 1.25 |
| Model/data cards and licensing documentation | 0.75 |
| Public interactive demo | 1.0 |
| Technical report / paper-quality write-up | 1.25 |
| Release and external benchmark submission where applicable | 0.75 |

## Change policy

Weights represent contribution to the final capability, not estimated effort.

If research invalidates a milestone or makes it obsolete:
1. record the reason in `DECISIONS.md`;
2. issue a new roadmap version;
3. redistribute points transparently within the affected phase;
4. never change weights merely to inflate progress;
5. preserve historical versions in Git.

Critical gates may block a release even when their point value is small or zero.
