# Task Brief Template

Every dispatched implementation task should be self-contained enough that an execution agent spends most of its effort executing rather than rediscovering project intent.

## Header

- **Task ID:**
- **Title:**
- **Branch:** `task/<TASK-ID>-<slug>`
- **Owner type:** execution agent / overseer
- **Dependencies:**
- **Allowed write scope:**
- **Forbidden write scope:**

## Context

Only the project context necessary to understand this task.

## Objective

One concrete outcome stated in observable terms.

## Inputs

Exact files, schemas, APIs, datasets, or prior task artifacts to use.

## Required implementation

Detailed behavior and interfaces. Distinguish mandatory requirements from implementation freedom.

## Constraints

Scientific, licensing, security, compatibility, performance, and architectural constraints.

## Acceptance criteria

Binary or measurable conditions the overseer can audit.

## Tests / evaluation

Exact tests, commands, fixtures, benchmarks, or manual checks required.

## Deliverables

Paths/artifacts that must exist when the task returns.

## Evidence package

The agent must return:
- branch + commit SHA;
- files changed;
- commands/tests;
- results;
- acceptance checklist;
- deviations;
- risks;
- licensing/provenance impact.

## Prohibited shortcuts

Task-specific ways an agent could appear to satisfy the task without actually satisfying it.

## Escalation conditions

Questions the agent must return to the overseer rather than decide locally.
