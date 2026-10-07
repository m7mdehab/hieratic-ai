# Hieratic AI dashboard (CTRL-003)

Public research control-plane shell. Next.js (App Router) + React + TypeScript, tokenized plain CSS (no Tailwind, no motion library).

> Status: CTRL-003 deliverable under overseer review. Not self-validated.

## Run

```bash
cd dashboard
npm install
npm run dev          # http://localhost:3000
npm run build && npm start
npm run lint
npm run typecheck
npm test
npm run screenshots  # needs: npx playwright install chromium; run after build
```

## Data flow

There is no dashboard-owned state. At build/server time, `src/lib/state.ts` reads the canonical files from the repository root (the parent of `dashboard/`, or `DASHBOARD_REPO_ROOT`):

| File | Used for |
|---|---|
| `PROJECT_STATE.yaml` | goal progress, research coverage, phase, wave, experiments, gates, next action |
| `TASKS.yaml` | tasks, statuses, dependencies, phase weights, per-phase earned points |
| `ROADMAP.md` | phase display names only (falls back to ids) |
| `DECISIONS.md`, `RESEARCH.md`, `EXPERIMENTS.md` | lightweight previews/counts |

- Per-phase earned points are derived from validated task weights. The loader fails the build if they disagree with `progress.goal_progress`, if phase weights do not sum to `goal_total`, or if a required field is missing/malformed. Optional fields degrade gracefully.
- `StateSource` is the integration seam for CTRL-002's validator.
- Nothing is copied or cached; no `data/project.json` exists. Tests enforce this.

## Tests

`tests/state.test.ts`: derivation, fixture propagation of canonical changes, failure modes, and a scan asserting that current progress/coverage values and task ids are not literals in `src/`.

## Dependencies and licenses

### Direct dependencies

All direct dependencies use permissive, commercial-friendly open source licenses compatible with Apache-2.0 (ADR-0007).

| Package | Type | Version | License | Purpose |
|---|---|---|---|---|
| `next` | Production | ^16.4.0 | MIT | Core framework (App Router, static rendering) |
| `react` | Production | ^19.3.0 | MIT | UI library |
| `react-dom` | Production | ^19.3.0 | MIT | DOM renderer |
| `yaml` | Production | ^2.9.1 | ISC | YAML parser for canonical repo state |
| `typescript` | Dev | ^6.0.3 | Apache-2.0 | Type checking (`tsc --noEmit`) |
| `@types/node` | Dev | ^26.6.4 | MIT | Node.js typings |
| `@types/react` | Dev | ^19.3.0 | MIT | React typings |
| `@types/react-dom` | Dev | ^19.3.0 | MIT | React DOM typings |
| `eslint` | Dev | ^9.39.5 | MIT | Linter |
| `eslint-config-next` | Dev | ^16.4.0 | MIT | Next.js ESLint rules |
| `vitest` | Dev | ^5.0.3 | MIT | Fast unit and fixture testing |
| `playwright` | Dev | ^1.63.0 | Apache-2.0 | Automated responsive QA and screenshot capture |

### Transitive dependency & licensing audit

- **Production runtime:** All production dependencies (`next`, `react`, `react-dom`, `yaml`) and their runtime transitive graph are licensed under MIT or ISC.
- **Optional native bindings:** `package-lock.json` contains 14 optional `@img/sharp-libvips-*` packages (`LGPL-3.0-or-later` and combined `Apache-2.0 AND LGPL-3.0-or-later`) declared as optional platform dependencies by Next.js for image optimization (`sharp`). The dashboard shell does not invoke `next/image` or native Sharp processing. In environments where `@img/sharp-libvips` binaries are installed, they exist as dynamically linked shared libraries; under Section 4 of LGPL v3, dynamically linking an LGPL library does not relicense the calling application or repository code (ADR-0007).
- **Copyleft isolation:** No GPL, AGPL, or restrictive copyleft code is incorporated into the repository or client bundles.

### Security audit breakdown

- **Production vulnerabilities (`npm audit --omit=dev --json`):** Exactly **0** vulnerabilities across all 19 production dependencies.
- **Development vulnerabilities (`npm audit --json`):** 5 high-severity alerts reported, representing a single propagation chain in the dev linter:
  ```text
  braces (<=3.0.3, GHSA-vfj7-8cjw-p6xm)
    └── micromatch (>=0.2.0)
         └── fast-glob (*)
              └── @next/eslint-plugin-next (>=14.3.0-canary.0)
                   └── eslint-config-next (>=14.3.0-canary.0) [devDependency]
  ```
  - **Impact:** Strictly development/build-time (`eslint .`). Does not execute in production runtime or client browsers.
  - **Remediation:** The package on disk is `braces@3.0.3` (the latest release addressing stack exhaustion), reinforced via `"overrides": { "braces": "^3.0.3" }` in `package.json`. npm's automated suggestion (`npm audit fix --force`) proposes downgrading to `eslint-config-next@14.2.35`, which is incompatible with Next.js 16 and React 19.

## Accessibility and responsive QA

- **Responsive layout verified:** Automated headless tests via Playwright at 320px, 390px, and 1440px widths verify:
  - `document.documentElement.scrollWidth <= clientWidth` (0px document overflow across all breakpoints).
  - `document.body.scrollWidth <= clientWidth` (0px body overflow; blind masking `overflow-x: hidden` removed).
  - Every rendered element satisfies `rect.right <= clientWidth + 1` and `rect.left >= -1` (`clippedCount = 0`).
  - Mobile facts layout stacks neatly into label/value pairs below 34rem, eliminating horizontal collisions.
  - Roadmap ledger names wrap naturally without awkward character splitting.
- **Reduced motion:** `@media (prefers-reduced-motion: reduce)` disables progress bar animations and smooth scrolling.
- **Color contrast:** Neutral canvas `#f6f4ef` with `#191816` ink (>16:1, WCAG AAA), muted text `#5e5a52` (>6:1, exceeding WCAG AA 4.5:1), and accent `#1d4b66` (>8.5:1, WCAG AAA).
- **Semantics & landmarks:** `<header>`, `<main id="main">`, `<section>`, `<footer>`, skip navigation link, semantic headings `<h1>`..`<h3>`, and screen-reader progressbar attributes (`role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-valuetext`).

## Known limitations

- No interactive task DAG (out of scope for CTRL-003; architecture leaves room for later extension).
- System font stacks only (no third-party webfont dependencies).
