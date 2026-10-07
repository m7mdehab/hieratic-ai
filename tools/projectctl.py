"""Validate canonical project state and generate bounded context packets."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
COMPATIBLE_STATE_GROUPS = ("ready_tasks", "active_tasks", "review_tasks")


class ProjectCtlError(Exception):
    """A user-facing input or validation error."""


def _load_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as stream:
            return yaml.safe_load(stream)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ProjectCtlError(f"{path.name}: cannot read valid YAML: {exc}") from exc


def _validate_schema(data: Any, schema_path: Path, label: str) -> list[str]:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProjectCtlError(f"Cannot read schema {schema_path}: {exc}") from exc
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(map(str, error.absolute_path)))
    return [f"{label}{''.join(f'[{part!r}]' for part in error.absolute_path)}: {error.message}" for error in errors]


def _decimal(value: Any, where: str, errors: list[str]) -> Decimal | None:
    if isinstance(value, bool):
        errors.append(f"{where}: expected a number")
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        errors.append(f"{where}: expected a number")
        return None
    if not result.is_finite():
        errors.append(f"{where}: expected a finite number")
        return None
    return result


def validate_data(project_state: Any, tasks_data: Any, *, root: Path = ROOT) -> list[str]:
    """Return every detectable canonical-state validation error."""
    errors: list[str] = []
    errors += _validate_schema(project_state, root / "schemas" / "project_state.schema.json", "PROJECT_STATE.yaml")
    errors += _validate_schema(tasks_data, root / "schemas" / "tasks.schema.json", "TASKS.yaml")
    if errors:
        return errors

    task_rows = tasks_data["tasks"]
    task_by_id: dict[str, dict[str, Any]] = {}
    for task in task_rows:
        task_id = task["id"]
        if task_id in task_by_id:
            errors.append(f"TASKS.yaml: duplicate task ID {task_id}")
        else:
            task_by_id[task_id] = task

    known_statuses = set(tasks_data["status_values"])
    for task in task_rows:
        task_id = task["id"]
        if task["status"] not in known_statuses:
            errors.append(f"Task {task_id}: unknown status {task['status']!r}")
        for dependency in task["depends_on"]:
            if dependency not in task_by_id:
                errors.append(f"Task {task_id}: missing dependency ID {dependency}")

        weight = _decimal(task["weight"], f"Task {task_id} weight", errors)
        if weight is not None:
            if weight < 0:
                errors.append(f"Task {task_id}: negative weight {weight}")
            phase = tasks_data["phases"].get(task["phase"], {})
            if (task["phase"].startswith("P0_") or phase.get("mandatory_gate") is True) and weight != 0:
                errors.append(f"Task {task_id}: control-plane tasks must have zero capability weight")
        if task["phase"] not in tasks_data["phases"]:
            errors.append(f"Task {task_id}: unknown phase {task['phase']!r}")

    for key, phase in tasks_data["phases"].items():
        weight = _decimal(phase["weight"], f"Phase {key} weight", errors)
        if weight is not None and weight < 0:
            errors.append(f"Phase {key}: negative weight {weight}")

    p1_p8_weights: list[Decimal] = []
    for number in range(1, 9):
        matching = [value for key, value in tasks_data["phases"].items() if key.startswith(f"P{number}_")]
        if len(matching) != 1:
            errors.append(f"TASKS.yaml: expected exactly one P{number} phase, found {len(matching)}")
        elif (value := _decimal(matching[0]["weight"], f"P{number} phase weight", errors)) is not None:
            p1_p8_weights.append(value)
    if len(p1_p8_weights) == 8 and sum(p1_p8_weights, Decimal("0")) != Decimal("100"):
        errors.append(f"P1-P8 phase weights total {sum(p1_p8_weights, Decimal('0'))}, expected 100")

    weights_by_phase: dict[str, Decimal] = defaultdict(Decimal)
    for task in task_rows:
        weight = _decimal(task["weight"], f"Task {task['id']} weight", errors)
        if weight is not None:
            weights_by_phase[task["phase"]] += weight
    for phase_id, phase in tasks_data["phases"].items():
        declared = _decimal(phase["weight"], f"Phase {phase_id} weight", errors)
        if declared is not None and weights_by_phase[phase_id] != declared:
            errors.append(
                f"Phase {phase_id}: task weights total {weights_by_phase[phase_id]}, declared phase weight is {declared}"
            )

    # A three-color DFS reports a concrete cycle path while visiting the full graph.
    colors: dict[str, int] = {}
    stack: list[str] = []
    cycles: set[tuple[str, ...]] = set()

    def visit(task_id: str) -> None:
        colors[task_id] = 1
        stack.append(task_id)
        for dependency in task_by_id[task_id]["depends_on"]:
            if dependency not in task_by_id:
                continue
            if colors.get(dependency, 0) == 0:
                visit(dependency)
            elif colors.get(dependency) == 1:
                start = stack.index(dependency)
                cycle = tuple(stack[start:] + [dependency])
                cycles.add(cycle)
        stack.pop()
        colors[task_id] = 2

    for task_id in task_by_id:
        if colors.get(task_id, 0) == 0:
            visit(task_id)
    for cycle in sorted(cycles):
        errors.append("Dependency cycle: " + " -> ".join(cycle))

    for task in task_rows:
        if task["status"] in {"ready", "active", "under_review"}:
            for dependency in task["depends_on"]:
                dependency_task = task_by_id.get(dependency)
                if dependency_task and dependency_task["status"] != "validated":
                    errors.append(
                        f"Task {task['id']}: status {task['status']} requires validated dependency {dependency} "
                        f"(currently {dependency_task['status']})"
                    )

    state = project_state["state"]
    for group in COMPATIBLE_STATE_GROUPS:
        for task_id in state[group]:
            if task_id not in task_by_id:
                errors.append(f"PROJECT_STATE.yaml state.{group}: unknown task ID {task_id}")
    memberships: dict[str, list[str]] = defaultdict(list)
    for group in COMPATIBLE_STATE_GROUPS:
        for task_id in state[group]:
            memberships[task_id].append(group)
    for task_id, groups in memberships.items():
        if len(groups) > 1:
            errors.append(f"PROJECT_STATE.yaml: task {task_id} appears in incompatible state arrays: {', '.join(groups)}")

    validated_weight = Decimal("0")
    for task in task_rows:
        if task["status"] == "validated":
            weight = _decimal(task["weight"], f"Task {task['id']} weight", errors)
            if weight is not None:
                validated_weight += weight
    goal_progress = _decimal(project_state["progress"]["goal_progress"], "PROJECT_STATE.yaml goal_progress", errors)
    expected = _decimal(
        tasks_data["rules"]["progress"]["validated_weighted_tasks_expected"],
        "TASKS.yaml validated_weighted_tasks_expected",
        errors,
    )
    if goal_progress is not None and validated_weight != goal_progress:
        errors.append(f"Validated weighted task sum {validated_weight} does not equal goal_progress {goal_progress}")
    if expected is not None and validated_weight != expected:
        errors.append(f"Validated weighted task sum {validated_weight} does not equal rules.progress.validated_weighted_tasks_expected {expected}")
    return errors


def validate_repository(root: Path = ROOT) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    project_state = _load_yaml(root / "PROJECT_STATE.yaml")
    tasks_data = _load_yaml(root / "TASKS.yaml")
    # Fixture and alternate roots carry their own schema copies.
    errors = validate_data(project_state, tasks_data, root=root)
    return errors, project_state, tasks_data


def _section(text: str, heading: str, *, max_chars: int = 1200) -> str:
    match = re.search(rf"^## (?:\d+\. )?{re.escape(heading)}\s*$", text, re.MULTILINE)
    if not match:
        return ""
    tail = text[match.end():]
    next_heading = re.search(r"^## ", tail, re.MULTILINE)
    body = tail[:next_heading.start()] if next_heading else tail
    body = body.strip()
    if len(body) > max_chars:
        boundary = body.rfind("\n", 0, max_chars)
        if boundary < max_chars * 0.6:
            boundary = body.rfind(" ", 0, max_chars)
        body = body[:boundary].rstrip() + "..."
    return body


def _markdown_list(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "- None"


def _portable_punctuation(text: str) -> str:
    """Keep packets readable in shells that do not default to UTF-8 output."""
    return text.replace("—", "-").replace("–", "-")


def overseer_context(root: Path, project_state: dict[str, Any], tasks_data: dict[str, Any]) -> str:
    state = project_state["state"]
    progress = project_state["progress"]
    handoff = (root / "OVERSEER_HANDOFF.md").read_text(encoding="utf-8")
    decisions = (root / "DECISIONS.md").read_text(encoding="utf-8")
    start = (root / "START_HERE.md").read_text(encoding="utf-8")
    open_decisions = []
    for block in re.split(r"(?m)(?=^## ADR-)", decisions):
        title = re.match(r"^## (ADR-\d+[^\n]*)", block)
        if title and re.search(r"(?m)^\*\*Status:\*\*\s*(?:Open|Pending)(?:\s|$)", block):
            open_decisions.append(title.group(1))
    if not open_decisions:
        open_decisions = ["No open decisions are listed in DECISIONS.md."]
    gate_lines = []
    for gate in project_state["critical_gates"]:
        remainder = ", ".join(gate.get("remaining", [])) or "none"
        gate_lines.append(f"{gate['id']} - {gate['name']}: {gate['status']} (remaining: {remainder})")
    authority = _section(start, "Canonical authority order")
    read_order = _section(start, "Read only what you need")
    latest_handoff = "\n\n".join(filter(None, [
        _section(handoff, "Current verified state", max_chars=500),
        _section(handoff, "What was just completed", max_chars=380),
    ]))
    return _portable_punctuation(f"""# Overseer Context Packet

## Mission
{project_state['project']['ultimate_goal'].strip()}

## Progress
- Verified goal progress: {progress['goal_progress']} / {progress['goal_total']}
- Research coverage: {progress['research_coverage']}%
- Current phase: {state['current_phase']}
- Current wave: {state['current_wave']}
- Validated experiments: {state['validated_experiments']}
- Trained models: {state['trained_models']}

## Gates
{_markdown_list(gate_lines)}

## Last accepted task
{state['last_accepted_task']}

## Task operations
- Ready: {', '.join(state['ready_tasks']) or 'none'}
- Active: {', '.join(state['active_tasks']) or 'none'}
- Under review: {', '.join(state['review_tasks']) or 'none'}
- Blockers: {', '.join(state['blockers']) or 'none'}

## Latest handoff
{latest_handoff or 'No handoff summary is available.'}

## Canonical authority and read order
{authority}

{read_order}

## Open decisions
{_markdown_list(open_decisions)}

## Next overseer action
{project_state['next_overseer_action'].strip()}
""".strip())


def task_context(root: Path, task_id: str, project_state: dict[str, Any], tasks_data: dict[str, Any]) -> str:
    task = next((entry for entry in tasks_data["tasks"] if entry["id"] == task_id), None)
    if task is None:
        raise ProjectCtlError(f"Unknown task ID: {task_id}")
    agent_contract = (root / "AGENTS.md").read_text(encoding="utf-8")
    brief_path = root / "tasks" / f"{task_id}.md"
    if not brief_path.exists():
        raise ProjectCtlError(f"Task brief not found: tasks/{task_id}.md")
    brief = brief_path.read_text(encoding="utf-8")
    dependencies = []
    by_id = {entry["id"]: entry for entry in tasks_data["tasks"]}
    for dependency in task["depends_on"]:
        dep_task = by_id.get(dependency)
        dependencies.append(f"{dependency}: {dep_task['status'] if dep_task else 'missing'}")
    contract_summary = "Execution agents implement bounded briefs and do not redefine project goals or canonical state. See AGENTS.md."
    acceptance = task["acceptance_summary"]
    objective = _section(brief, "Objective", max_chars=700)
    requirements = _section(brief, "Required implementation", max_chars=1800)
    brief_acceptance = _section(brief, "Acceptance criteria", max_chars=900)
    brief_tests = _section(brief, "Tests", max_chars=900)
    write_scope = re.search(r"(?m)^- \*\*(?:Primary write scope|Allowed write scope):\*\*\s*(.+)$", brief)
    scope = write_scope.group(1).strip() if write_scope else "Not specified."
    return _portable_punctuation(f"""# Execution Context Packet - {task_id}

## Mission summary
{project_state['project']['ultimate_goal'].strip()}

## Agent contract
{contract_summary}

## Task metadata
- ID: {task['id']}
- Title: {task['title']}
- Phase: {task['phase']}
- Status: {task['status']}
- Owner role: {task.get('owner_role', 'unspecified')}
- Acceptance summary: {acceptance}

## Objective
{objective or task['title']}

## Dependencies
{_markdown_list(dependencies)}

## Acceptance details
{requirements or acceptance}

{brief_acceptance}

## Tests and evidence
{brief_tests or 'Follow the task brief evidence package.'}

## Declared write scope
{scope}

## Required inputs and paths
- Task brief: `tasks/{task_id}.md`
- Agent contract: `AGENTS.md`
- Mission and state: `START_HERE.md`, `PROJECT_STATE.yaml`
- Task graph and acceptance summary: `TASKS.yaml`
- Dependency briefs: {', '.join(f'`tasks/{item}.md`' for item in task['depends_on']) or 'none'}

## State authority warning
Do not alter progress numbers or task weights unless the task explicitly authorizes that exact state transition.
""".strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.projectctl")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (defaults to this checkout)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="validate canonical project and task state")
    context = subparsers.add_parser("context", help="generate a compact context packet")
    group = context.add_mutually_exclusive_group(required=True)
    group.add_argument("--overseer", action="store_true", help="generate the overseer packet")
    group.add_argument("--task", metavar="ID", help="generate context for one execution task")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        errors, project_state, tasks_data = validate_repository(root)
        if errors:
            print("Project state validation failed:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        if args.command == "validate":
            print(
                "PASS: canonical project state is valid "
                f"({len(tasks_data['tasks'])} tasks; goal progress {project_state['progress']['goal_progress']}; "
                f"validated weighted sum {tasks_data['rules']['progress']['validated_weighted_tasks_expected']})."
            )
            return 0
        if args.overseer:
            print(overseer_context(root, project_state, tasks_data))
        else:
            print(task_context(root, args.task, project_state, tasks_data))
        return 0
    except ProjectCtlError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
