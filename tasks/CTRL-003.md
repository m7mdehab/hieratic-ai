# CTRL-003 — Live Dashboard / Control-Plane Shell

- **Task ID:** CTRL-003
- **Branch:** `task/CTRL-003-dashboard-shell`
- **Owner:** execution agent
- **Depends on:** CTRL-001 — validated
- **Status at dispatch:** ready
- **Primary write scope:** `dashboard/`
- **Do not edit:** canonical progress/task weights, research conclusions, evaluation data, unrelated root governance files

## Context

The project needs a public-facing research control plane from the beginning, eventually hosted on a subdomain of Mohammed Ehab's personal website.

It serves two audiences:
1. Mohammed: live operational visibility into progress, tasks, experiments, and decisions.
2. Public visitors/recruiters/researchers: a credible, understandable view of an active open research program.

This is **not** a generic SaaS admin dashboard.

The established personal-site design direction is:
- professional, minimal, clean, visual, typography-led, naturally flowy;
- generous whitespace and strong visual rhythm;
- controlled asymmetry;
- short high-impact copy;
- restrained motion concentrated around meaningful state change;
- clarity, accessibility, mobile usability, SEO, and performance over spectacle.

Avoid:
- generic bento-dashboard composition;
- neon developer styling;
- random gradients/glowing orbs;
- excessive glassmorphism;
- identical cards everywhere;
- giant terminal aesthetics;
- gratuitous 3D;
- continuous ambient motion;
- fake metrics.

## Objective

Build the first deployable dashboard shell under `dashboard/` that reads project state from canonical repository files at build/server time and renders an elegant, responsive Hieratic AI home/control page.

The shell should be architected for later expansion without pretending future features already exist.

## Technical baseline

Use:
- Next.js;
- React;
- TypeScript;
- Tailwind CSS or the repository's equivalent tokenized CSS approach.

Keep dependencies lean. Add a motion library only if a specific subtle interaction justifies it.

The dashboard is currently a sub-application in this repo. Do not couple it to an unknown personal-site implementation. Instead use clean design tokens/components so it can later be visually mapped and deployed to a subdomain.

## Canonical data flow

The page must derive current values from repository data, primarily:
- `PROJECT_STATE.yaml`;
- `TASKS.yaml`;
- `ROADMAP.md` only for human-facing descriptive copy where needed;
- `DECISIONS.md`, `EXPERIMENTS.md`, `RESEARCH.md` only for lightweight preview/count/link surfaces if implemented.

No second manually edited dashboard-state JSON file.

It is acceptable to copy canonical files into the dashboard build context through a documented loader, but the copies must be generated and non-authoritative.

## Required homepage information architecture

### 1. Identity / research header

Communicate succinctly:
- Hieratic AI;
- open research program;
- mission: teach multimodal AI to read ancient Egyptian Hieratic;
- link to GitHub.

Avoid marketing hyperbole.

### 2. Primary state

Make these immediately legible:
- **2.5% verified goal progress**;
- **14% research coverage**;
- current capability phase;
- current control-plane wave;
- validated experiment count.

The values must come from canonical state, not literals in the rendered component.

### 3. Capability roadmap

Show P1-P8 with:
- phase name;
- weight;
- verified earned points;
- current/locked state.

Do not show fake completion for planned work.

### 4. Task operations view

At minimum provide useful grouping for:
- ready;
- active;
- under review;
- blocked;
- validated.

Initial data should reveal CTRL-002 and CTRL-003 as ready at the corresponding repository state.

A full interactive DAG is **not required in this task**; architecture should leave room for it.

### 5. Research activity

Compact previews/links for:
- latest decision(s);
- research registry;
- experiment count/state;
- latest accepted task / next overseer action.

### 6. Methodology / credibility note

Explain briefly that:
- progress is capability-based, not time-based;
- execution agents work from bounded tasks;
- only overseer-validated evidence earns progress.

This is scientifically important public context, not project-management decoration.

## Visual direction

Translate the personal-site system into a research-console context:
- strong typography;
- calm neutral canvas;
- one restrained accent system;
- generous spacing;
- precise dividers/rules;
- large meaningful numerals;
- light structural/data motifs only if they support comprehension;
- different visual treatments for roadmap, task state, and research evidence rather than a wall of identical cards.

Motion should be limited to useful state transitions, progress reveals, or hover/focus affordances. Support `prefers-reduced-motion`.

## Accessibility / responsive baseline

Required:
- semantic headings/landmarks;
- keyboard-accessible controls/links;
- visible focus states;
- sufficient contrast;
- no horizontal overflow at common mobile widths;
- meaningful screen-reader labels for progress;
- reduced-motion behavior.

## Data robustness

- missing optional fields should degrade gracefully;
- malformed required canonical state should fail visibly during build/runtime rather than silently invent defaults;
- do not hard-code task counts;
- do not parse Markdown tables when machine-readable task metadata is available.

If CTRL-002 tooling is not yet merged because both tasks run in parallel, write the loader behind a small interface so validation can be integrated later without redesigning the page.

## Tests / QA

At minimum:
- production build succeeds;
- lint/typecheck succeeds;
- unit/component tests for derived progress/task grouping where practical;
- mobile + desktop screenshots;
- verify no source value for goal progress/research coverage is duplicated as a UI constant;
- verify canonical file changes propagate to rendered data through a test/fixture.

## Deliverables

- complete `dashboard/` app;
- README inside `dashboard/` with local run/build instructions and data-flow explanation;
- screenshots or preview URL;
- test/build outputs.

## Prohibited shortcuts

- manually typing current metrics into JSX;
- creating `dashboard/data/project.json` as a second hand-maintained truth source;
- presenting a static mockup instead of a runnable application;
- using generic dashboard templates that visually conflict with the personal-site direction;
- inventing experiment results, task activity, dates, or model performance;
- editing canonical state to make the interface look richer.

## Evidence package on return

Return:
- task ID;
- branch;
- commit SHA;
- files changed;
- install/build/test commands + outputs;
- screenshot/preview;
- short architecture/data-flow explanation;
- acceptance checklist;
- deviations/risks;
- new dependencies and licenses.

Do **not** self-mark the task validated.
