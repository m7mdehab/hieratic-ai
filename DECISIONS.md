# Decision Log

Accepted decisions are append-only in substance. Later decisions may supersede earlier ones, but the historical decision remains visible.

## ADR-0001 — Repository is the canonical project memory

**Status:** Accepted  
**Date:** 2026-10-07

Long-running continuity must not depend on a single AI conversation or provider. Canonical state lives in the public repository. Chats and agent memories are transient views.

## ADR-0002 — Measure capability, not elapsed time

**Status:** Accepted  
**Date:** 2026-10-07

The primary roadmap is a 100-point capability program. Elapsed time may be logged retrospectively but does not define progress.

Only accepted weighted milestones earn goal-progress points. Research coverage is tracked separately.

## ADR-0003 — Overseer/executor separation

**Status:** Accepted  
**Date:** 2026-10-07

The overseer owns research, architecture, decomposition, acceptance criteria, review, and state transitions. Heterogeneous AI agents are primarily execution workers operating from bounded briefs.

This separation is intended to reduce duplicated reasoning, drift, and inconsistent project assumptions.

## ADR-0004 — Parallelism is default when dependency-safe

**Status:** Accepted  
**Date:** 2026-10-07

Independent tasks should run in parallel. Concurrency is restricted when tasks share mutable files, benchmark/test material, canonical schemas, or incompatible interfaces.

Branch/write-scope isolation is preferred over ad-hoc coordination.

## ADR-0005 — Control plane is mandatory but unweighted

**Status:** Accepted  
**Date:** 2026-10-07

The dashboard, context tooling, task graph, and governance automation are essential infrastructure but do not themselves improve Hieratic-reading capability. They are a mandatory Phase-0 gate worth 0 goal-progress points.

## ADR-0006 — Dashboard derives from repository state

**Status:** Accepted  
**Date:** 2026-10-07

The public website/control plane must consume canonical repository state. It must not maintain an independent manually edited project-status database.

## ADR-0007 — Code license does not relicense external research assets

**Status:** Accepted  
**Date:** 2026-10-07

Apache-2.0 covers repository-authored software/documentation unless otherwise stated. External images, datasets, editions, fonts, and model artifacts retain their own terms. Provenance and redistribution rights must be recorded separately.

## ADR-0008 — Every agent review ends with a complete status report

**Status:** Accepted  
**Date:** 2026-10-07

Whenever Mohammed brings back execution-agent feedback or implementation evidence, the overseer must review the actual work and then provide a standardized project status report.

The report must include:
- review verdict;
- verified completed items;
- pending/revision items;
- checked/unchecked acceptance checklist;
- task evidence completion;
- verified goal progress and remaining percentage;
- research coverage;
- current phase progress;
- relevant operational gate progress;
- next dependency-aware checklist;
- explicit statement of which percentages changed.

Operational/task percentages must remain distinct from the 0–100 verified capability score.

The canonical format is `docs/governance/REVIEW_REPORTING_PROTOCOL.md`.


## ADR-0009 — Third-party data is deny-by-default

**Status:** Accepted  
**Date:** 2026-10-07

Public availability is not permission to train, redistribute, or relicense.

Every third-party asset must pass the repository's data-admission gate before it enters a training/dev corpus. The project records provenance, license/rightsholder, allowed uses, redistribution status, attribution, source identity, cryptographic hash, transformation history, and benchmark-overlap status.

Unknown or ambiguous rights default to **metadata-only / do not ingest**.

Training permission, dataset redistribution permission, and model-weight release permission are treated as separate questions.

HieraticBench is quarantined for external evaluation even when an individual public benchmark image would otherwise have a permissive source license.

The canonical policy is `docs/governance/DATA_LICENSING_AND_PROVENANCE_POLICY.md`.


## ADR-0010 — Every dispatch wave includes approved overseer work when safe

**Status:** Accepted  
**Date:** 2026-10-08

The project should maximize safe parallel throughput across Luna, Sonnet, Gemini/other execution agents, and the overseer.

Whenever at least one substantial dependency-ready task is suitable for the overseer's strengths, the overseer must include that task in the same wave plan rather than waiting idly for execution agents.

Before starting, the overseer presents the complete wave assignment to Mohammed, including:
- each execution agent's task;
- the overseer's own task;
- why each task is assigned that way;
- dependencies and collision risks;
- expected capability or infrastructure effect.

Mohammed approves the wave before the overseer begins its own task.

The overseer-owned task should normally be a high-leverage research, architecture, evaluation, scientific-method, or integration task. Filler work is prohibited.

If no safe overseer task is available, the overseer must explicitly state the blocking dependency instead of inventing work.

The detailed protocol is `docs/governance/PARALLEL_WAVE_PROTOCOL.md`.


## ADR-0011 — Sonnet and Gemini share one Anti-Gravity execution lane

**Status:** Accepted  
**Date:** 2026-10-08

The normal parallel topology is three lanes:

1. Luna;
2. one Anti-Gravity lane occupied by either Sonnet or Gemini 3.8 Flash;
3. the overseer.

Sonnet and Gemini are not planned as simultaneous independent lanes. Mohammed switches the Anti-Gravity lane between them according to model limits and availability.

A provider/model switch does not create a new project or task. The incoming model resumes from canonical repository state and the relevant task brief/handoff. Repository state remains authoritative over model memory or prior chat summaries.

Wave plans must therefore assign work to the **Anti-Gravity lane**, while naming the currently active model in parentheses.


## ADR-0012 — Evaluation v1 has no primary composite score

**Status:** Accepted  
**Date:** 2026-10-08

Hieratic AI evaluation v1 reports layer-specific metrics rather than one primary composite score.

Reason:
- script identification, visual recognition, transliteration, linguistic analysis, translation, and uncertainty are different capabilities;
- a single weighted average can hide catastrophic failure at an earlier reading layer;
- fluent translation must not compensate for incorrect visual reading.

A future public composite may be introduced only through a versioned decision with fixed predeclared weights, visible component metrics, and hard capability floors.

The canonical metric contract is `docs/evaluation/METRICS_SPEC.md` plus `eval/metric_contract.yaml`.


## ADR-0013 — Luna receives larger independent-task work packages

**Status:** Accepted  
**Date:** 2026-10-08

Luna completes bounded engineering tasks faster than the overseer lane, so one-small-task-per-wave creates avoidable idle time.

When several tasks are independently ready, the default Luna assignment is therefore a **2–3 task work package**.

Constraints:
- all package tasks must already have validated dependencies at dispatch;
- each task keeps separate acceptance criteria, evidence, and progress accounting;
- preferably one branch/PR per canonical task;
- write scopes must be disjoint or explicitly partitioned;
- Luna may return only after completing the full package;
- no dependent task may start solely because its prerequisite was locally completed inside the package; overseer validation is still required.

This changes throughput, not scientific or quality standards.


## ADR-0014 — Pin external HieraticBench; preserve its official scoring and quarantine

**Status:** Accepted  
**Date:** 2026-10-08

HieraticBench reproduction is pinned to upstream commit
`d587dc990013f18007f1e7a8f56f96ff2f7127e2`
and harness `0.1.0`.

- Reproduce item inventory and public numeric score aggregation with a read-only external adapter.
- Use the benchmark's own TypeScript scoring implementation/tests as the authoritative raw-answer scorer.
- Never silently substitute Hieratic AI's different normalization or metrics for official benchmark scores.
- Do not claim fresh model-inference reproduction merely because historical numeric aggregates were reproduced.
- Never fabricate gold labels/scores for the undisclosed sentence.
- Keep images, crops, exact/near-duplicate source items, benchmark answer gold, and model outputs out of the training/development pipeline.
- Any future upstream benchmark version requires a new reviewed manifest, scorer comparison and benchmark-integrity decision.

References: `docs/evaluation/HIERATICBENCH_REPRODUCTION.md` and `eval/benchmarks/hieraticbench/manifest.yaml`.


## ADR-0015 — Error-review events are not performance denominators

**Status:** Accepted  
**Date:** 2026-10-08

EVAL-005 formalizes an evidence-linked taxonomy with one primary failure code, optional secondary codes, adjudication status, gold eligibility, contamination status, causal references, and subgroup metadata.

Error-review counts must **not** be interpreted as rates, model accuracy or reading proficiency without a separately frozen EVAL-001 scored-item universe and documented sampling design. Public summaries exclude sealed-aggregate records before computing any statistics. Disputed/uncertain/contaminated events may be logged diagnostically but do not enter confirmed clean-error distributions.

See `docs/evaluation/ERROR_TAXONOMY_AND_ANALYSIS.md` and `eval/analysis/error_taxonomy.yaml`.


## ADR-0016 — Evidence validity and capability acceptance are separate gates

**Status:** Accepted  
**Date:** 2026-10-08

FND-006 made project governance executable via evidence/experiment schemas, task write-scope registration, CI checking of actual PR file diffs, full cross-domain tests, and operational reproducibility documentation.

- A syntactically valid agent evidence bundle or experiment record is not proof that its underlying commands/results/rights were independently verified.
- Only the overseer, after inspecting actual PR/CI/evaluation evidence, may mark weighted tasks validated.
- An experiment may be labeled `validated` only after frozen data/splits, code/config/model/run outputs and actual reviewed metrics exist; schema completeness alone is insufficient.
- Unregistered execution-agent task branches fail CI write-scope checks; novel tasks must register a reviewed allowed scope.
- FND-006 closes foundation P1 at 5/5; CTRL-003 remains an independent, unresolved control-plane gate item.

Reference: `docs/governance/REPRODUCIBILITY_GATES.md`.


## ADR-0017 — Reviewable acquisition and split plans do not constitute dataset clearance

**Status:** Accepted  
**Date:** 2026-10-08

DATA-002, DATA-004 and EVAL-004 infrastructure was accepted after code, CI and negative-test review, but **only the mechanisms** have been validated:

- Acquisition manifests plan source handling without downloading, licensing, granting rights or admitting assets into a training/dev corpus; real per-item license/rightsholder/reviewer and independent overlap evidence must exist.
- A syntactically reviewed `benchmark_overlap_review.status: clear` is an attestation that must be independently checked; it does not prove the item was compared with all 268 pinned HieraticBench examples. The aggregate-only roster is explicitly insufficient to automate exhaustive overlap clearance.
- Any real/production split must pass item-level provenance and exact/near-duplicate comparison before downstream training or blind-evaluation claims; unreviewed high-risk items remain excluded.
- Annotation examples are synthetic. EVAL-001 scoring against actual expert gold still needs reviewed real annotations with permission.
- Downstream tasks `EVAL-006`, `DATA-003`, `DATA-005`, `DATA-006`, `DATA-007` become **dependency-ready only**; ready is not automatically active or validated.

The accepted implementation PRs are #20, #23 and #24, with W1 acceptance recorded in canonical state. The limitation protects the difference between validated engineering guardrails and scientific or licensing evidence.


## ADR-0018 — A frozen evaluation policy is not a scored blind experiment

**Status:** Accepted  
**Date:** 2026-10-08

EVAL-006's versioned sealed evaluation protocol, custody separation, machine-readable pre-registration, contamination-response rules and staged publication gates are accepted research infrastructure. A human-verified, hash-frozen real dataset/model run remains a separate future scientific milestone.

- Freeze item/split/model/config/prompts/metric identities and planned attempts **before** developer exposure to sealed item gold/scores; revisions after exposure require a genuinely fresh independent holdout.
- Keep training operator, sealed custodian, blind scorer/adjudicator and release authorities separated and evidence-linked; no unilateral scoring/publication.
- Test asset rights, source/near-duplicate overlap and original document lineage; a submitted `clear` boolean is not independent rights/novelty proof.
- Score EVAL-001 layers individually, preserve all failures/abstentions/unscorable gold counts, and use document-clustered confidence limits. A fluent translation or script label is insufficient evidence of genuine Hieratic reading.
- Suspected/confirmed contamination blocks affected public claims until recorded independent review and, as necessary, withdrawal or genuinely new blind test.
- EVAL-003 public benchmark manifest/prompt-source freeze is separate from execution authority; upstream historical scores cannot be laundered into newly run baseline claims.

Evidence: `docs/evaluation/SEALED_EVALUATION_PROTOCOL.md`, PRs #35/#40; `docs/evaluation/FRONTIER_BASELINES.md`, PR #38.


## ADR-0019 — Accept build-time canonical dashboard with independently verified CI

**Status:** Accepted  
**Date:** 2026-10-08

CTRL-003's Next.js public control-plane shell is accepted only after independent `npm ci`, production-security, lint/typecheck/Vitest, build and Playwright QA on the updated canonical state. The dashboard is derived from `PROJECT_STATE.yaml` and `TASKS.yaml` during build/server rendering, without an independent status database. New canonical commits require rebuild/redeployment to refresh a static deployment. Dashboard CI was introduced via PR #43; implementation PR #27 and its scope were independently reviewed.

The dependency `braces@3.0.3` is still vulnerable under **GHSA-vfj7-8cjw-p6xm** (all versions through 3.0.3 affected; no patched release as of this decision). Five high alerts remain in a development-only ESLint transitive chain. Acceptance is conditioned on zero production high alerts and not processing untrusted glob/brace expressions in that tooling; the risk is documented, **not represented as remediated**.

CTRL-003's zero-point status remains unchanged; the control-plane gate becomes **5/5 complete**. No deployment, model experiment or Hieratic reading performance is inferred from dashboard acceptance.


## ADR-0020 — Accepted synthetic-only data engine contracts do not license assets or prove reading competence

**Status:** Accepted  
**Date:** 2026-10-08

After independent source inspection, CI and critical hardening, DATA-003/005/006/007 were accepted as deterministic preprocessing, sign/palaeography schema, image-to-text alignment, and expert-review *infrastructure*. They earn +10 verified engineering roadmap points but no real inference or expert gold.

Required boundaries: input usage and manifest-local asset containment; verified scholarly citation metadata for supported sign assertions; no gold-score eligibility for synthetic even if superficially resolved/reviewed; real source item rights/admission and benchmark novelty independently validated; reviewer consensus only after two independent decisions with dated evidence. The source registry and admission rules remain conservative: a declared approval is not independent rights proof.

Remaining real-world limitations include missing JPEG/TIFF/EXIF support, absent licensed manuscript datasets and real scholarly sign mappings, and absent external expert adjudication. W3 candidates DATA-008, VLM-001 and LING-001 are dependency-ready only.


## ADR-0021 — Normalization infrastructure accepted with immutable source preservation

**Status:** Accepted  
**Date:** 2026-10-08

LING-001 PR #51 receives its 2.0 roadmap points following source review and independent hosted testing. EVAL-001-aligned technical normalization may adjust declared Unicode/formatting distinctions but cannot invent linguistic equivalences, displace source readings, or coerce uncertain alternatives to certainty. Exact DATA-004 annotation bytes are pinned in the request by SHA-256; stale fixture hashes fail closed. Output publishing must not overwrite another writer's file even under a concurrent creation race. The final tested implementation uses atomic same-directory hard-link creation and rejects existing targets.

The governance test suite now includes tests/linguistics, PR #53. DATA-008's right to 3 points requires a real source-cleared training/dev/test corpus, not only a synthetic assembly engine. VLM-001 requires actual scientific VLM runs, verified demonstrations and pinned correct scoring, not only mock tests. Canonical capability 30.5→32.5, P6 interpretation 2/10; model training/validated experiments remain 0.


## ADR-0022 — A delivered execution prompt is authorization to start, without redundant approval gates

**Status:** Accepted  
**Date:** 2026-10-08  
**Authority:** Mohammed's explicit instruction on 2026-10-08; supersedes the approval/waiting clauses of ADR-0010 and the earlier parallel-wave protocol.

Once Mohammed sends a concrete continuation/task prompt to Luna (Codex), the selected Anti-Gravity agent (Gemini/Sonnet), or any future execution agent, **receipt of that prompt is the authorization to begin the bounded assigned task immediately**. Agents must not request a second "may I start?" permission, wait for a later wave sign-off, or return a planning-only response when the task is executable.

The overseer publishes a dependency-safe wave assignment and copy-ready dispatch prompts, and may begin its own independent safe work without an artificial repeated approval checkpoint. Mohammed retains final authority to change or stop work. Sending a prompt does not waive the governance contract or authorize scope creep.

**Separate explicit authorization is still required** for paid inference or nontrivial third-party spend, restricted data access/rights changes, revealing secrets, irreversible destructive operations, scientific release/unblinding, or any action explicitly held behind an external/security/legal gate. An ordinary task prompt does not implicitly approve those actions. Execute all safe, independent work and record blockers precisely.

PR acceptance, capability points, protected state transitions, and promotion of claims remain exclusively overseer-reviewed. This decision alters dispatch latency, not integrity or review standards.


## ADR-0023 — The user synchronizes the parallel start: prompts first, overseer work after user returns

**Status:** Accepted  
**Date:** 2026-10-08  
**Authority:** Mohammed's newer explicit workflow correction; supersedes only the overseer-start timing in ADR-0022 and the corresponding parallel-wave protocol.

A new parallel wave has **two separate visible steps**:

1. **Dispatch response first:** the overseer gives Mohammed (a) complete ready-to-send prompts for Luna and the single Anti-Gravity lane, and (b) a concise statement of the substantial overseer-owned parallel task, scope, and noncollision rationale. The overseer does **not** finish or silently begin that work before presenting the prompts. The user gets the opportunity to forward them to the execution agents.
2. **Synchronized execution after handoff:** Mohammed sends the prompts to the agents (which authorize them to begin immediately under ADR-0022) and then returns to the overseer chat to say dispatch is complete / to continue. At that point the overseer begins and performs the assigned independent work while execution agents are running.

No second agent approval or redundant confirmation is needed **inside Codex or Anti-Gravity**. The overseer must not demand a separate formal wave approval once Mohammed has returned to continue. The user may explicitly authorize another timing arrangement for a given wave.

This handoff is **a synchronization cue, not a scientific or financial waiver**. Rights, spending, sealed data, irreversible actions, unblinding, agent scope, independent PR acceptance and progress gates remain intact. The overseer must not promise background work while the user is away: the work runs only during the resumed interactive turn.

**Exception at adoption:** after the user explicitly asked the overseer to pick up different work while the agents were already executing, the overseer completed primary-source research R-015 in PR #56. That completed work is not undone by this future-wave sequencing rule.


## ADR-0024 — Accept genuinely source-grounded LING-002 interpretation; keep script-reading evidence separate

**Status:** Accepted · **Date:** 2026-10-09 · **Authority:** Independent overseer review of full publisher source licensing, original-source Git blob identity, exact-head PR #88 code/tests and hosted governance CI 37856429995.

The project owner's explicit preference is to exhaust viable public licensed free resources rather than idle while awaiting hired Egyptologists or paid infrastructure. An agent should **not** call a substep exhaustively blocked until lawful and materially different online alternatives have been investigated, tested where accessible and documented. Actual legal/security authorization gates remain real and must not be fabricated away.

**Accepted LING-002 accomplishment (2.0 weighted roadmap points):** Real scholarly Egyptian dictionary/grammar and corpus from AED-TEI and AES (publisher CC BY-SA 4.0, independently registered via PR #85) now power deterministic token-to-lemma/POS/root/gloss and genuine alternative inflection analyses. The runtime validates the source data and licensed text-layer custody. A genuine full-corpus developmental diagnostic holds out each AES text ID's token gold from its AES candidate-generation set and compares model-free exact-form retrieval to published editor lemmas/morphology. The analysis is source-grounded and neither synthetic-only nor inferred from HPDB. It meets LING-002's limited P6 task scope and unblocks LING-003.

**Measured and qualified:** 1,621 of 2,305 published lemma tokens have the correct lemma in returned candidate sets (70.33%); 1,062 of 1,102 uniquely predicted cases match published lemma (96.37% **conditional on unique prediction**); 449/753 morphological bundles match other-text source candidates (59.63%). Report SHA-256 is 26ad977c29fdd8659157cb02bec04323b6b544dc8ca9425a13825ea629acedee; full provenance and evidence in tasks/LING-002.md and EXPERIMENTS.md. Exact-head CI and canonical 15-file write-scope check passed.

**Explicit limits:** AED and AES derive from overlapping published scholarship. Original AES text IDs do not prove independent physical papyri or scribes. No licensed original image, OCR, hand-written recognition, second blind Egyptologist reading, model tuning, sealed benchmark or statistically independent real-model performance was demonstrated. The 2 points acknowledge the **linguistic interpretation milestone only** and do not change DATA-008 production, VLM scientific certification, real-model experiment count, independent gold/benchmark or P4/P5 capability status.

Canonical score: **32.5 → 34.5/100**, P6 **2 → 4/10**; LING-002 status **validated** and LING-003 becomes dependency-ready. Research coverage retains its historic 14% uncalibrated value, validated real model experiments **0**, trained models **0**. Neither publisher source licensing nor a task-oriented weight award is independent of original-image use rights.
