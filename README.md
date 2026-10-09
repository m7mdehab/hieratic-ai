# Hieratic AI

Open research project for teaching multimodal AI systems to **read, transliterate, normalize, and ultimately interpret ancient Egyptian Hieratic handwriting**.

## Project status

- **Verified goal progress:** 34.5 / 100
- **Research coverage:** ~14%
- **Current stage:** P2 Evaluation; W10 data/VLM diagnostics and W11 publisher-text external generalization research integrated; original Hieratic line gold, semantic translation and independent reading accuracy remain blocked
- **Validated experiments:** 0

Progress is capability-based, not time-based. Work only earns goal-progress points after predefined acceptance criteria are met and the evidence is reviewed.

## Ultimate goal

Build and publicly demonstrate a reproducible multimodal AI system that can take genuinely unseen Hieratic handwriting, recognize what is written, produce a defensible transliteration/normalization, and derive meaning/translation with calibrated uncertainty, while generalizing beyond memorized documents or scribes and improving over untuned frontier VLMs and appropriate specialist baselines.

## Start here

Humans and AI agents should begin with [START_HERE.md](START_HERE.md).

The repository itself is the source of truth for project state. Individual chat histories, agent memories, and local notes are not authoritative unless reconciled into the canonical project files.

## Governance

Key files:

- `PROJECT_STATE.yaml` — live machine-readable state
- `ROADMAP.md` — capability roadmap and weights
- `TASKS.yaml` — canonical task graph
- `AGENTS.md` — execution rules for any AI agent
- `OVERSEER_HANDOFF.md` — compact continuity packet for a new overseer chat
- `DECISIONS.md` — architectural/research decision log
- `EXPERIMENTS.md` — experiment registry
- `RESEARCH.md` — research registry and unresolved questions
- `REPO_MAP.md` — navigation map

## Licensing

Repository-authored software and documentation are licensed under Apache-2.0 unless a file states otherwise.

**Third-party datasets, museum images, scholarly editions, model weights, fonts, and other external assets are not automatically covered by the repository license.** Their original licenses, provenance, and redistribution restrictions must be recorded before inclusion or redistribution.
