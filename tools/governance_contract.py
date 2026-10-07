"""Independent operational governance checks; does not mutate canonical project state.

Schema validity and scoped-file membership are necessary checks, not proof that
an agent executed a command or that an external license is genuinely approved.
"""
from __future__ import annotations

import argparse
from fnmatch import fnmatchcase
import json
from pathlib import Path
import sys
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_SCHEMA = ROOT / "schemas/agent_evidence.schema.json"
EXPERIMENT_SCHEMA = ROOT / "schemas/experiment_record.schema.json"
SCOPES = ROOT / "docs/governance/TASK_WRITE_SCOPES.yaml"


class ContractError(ValueError):
    pass


def read_payload(path: Path) -> Any:
    try:
        if path.suffix.lower() == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ContractError(f"{path}: cannot read structured data: {exc}") from exc


def validate_schema(payload: Any, schema_path: Path) -> list[str]:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ContractError(f"Invalid schema {schema_path}: {exc}") from exc
    errors = Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(payload)
    return [f"{'.'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in sorted(errors, key=lambda e: str(list(e.absolute_path)))]


def check_scope(task_id: str, changed_files: list[str], policy: Any) -> list[str]:
    if not isinstance(policy, dict) or not isinstance(policy.get("task_scopes"), dict):
        return ["Missing or malformed canonical task write-scope policy"]
    allowed = policy["task_scopes"].get(task_id)
    if not isinstance(allowed, list) or not allowed:
        return [f"{task_id} has no approved registered write scope; fail closed"]
    errors: list[str] = []
    if not changed_files:
        errors.append("changed-file list is empty; cannot establish actual branch scope")
    if len(set(changed_files)) != len(changed_files):
        errors.append("duplicate changed file paths")
    for path in changed_files:
        if not isinstance(path, str) or not path or path.startswith("/") or "\\" in path or ".." in path.split("/"):
            errors.append(f"invalid or unsafe changed-file path: {path!r}")
        elif not any(fnmatchcase(path, pattern) for pattern in allowed):
            errors.append(f"{task_id} does not authorize changed file: {path}")
    return errors


def validate_evidence(payload: Any, schema: Path = EVIDENCE_SCHEMA, scopes: Path = SCOPES) -> list[str]:
    errors = validate_schema(payload, schema)
    if errors:
        return errors
    if payload["branch"].split("/")[1].split("-")[:2] != payload["task_id"].split("-"):
        errors.append("Task ID in branch name does not match evidence task_id")
    policy = read_payload(scopes)
    errors.extend(check_scope(payload["task_id"], payload["changed_files"], policy))
    if payload["licensing_provenance"]["third_party_assets_added"] and payload["licensing_provenance"]["rights_review_status"] != "approved_with_evidence":
        errors.append("Third-party additions require an approved rights review with independent evidence")
    for item in payload["acceptance"]:
        if item["met"] and not item["evidence_ref"]:
            errors.append(f"Claimed acceptance criterion has no evidence reference: {item['criterion']}")
    return errors


def validate_experiment(payload: Any, schema: Path = EXPERIMENT_SCHEMA) -> list[str]:
    errors = validate_schema(payload, schema)
    if errors:
        return errors
    if payload["status"] == "validated":
        roles = {item["role"] for item in payload["artifacts"]}
        if not {"raw_predictions", "scores", "config"} <= roles:
            errors.append("Validated experiment must reference immutable predictions, scores, and config artifacts")
        if any(not item["uri"].startswith(("artifact:", "sha256:", "https://")) for item in payload["artifacts"]):
            errors.append("Experiment artifacts must use auditable immutable-reference URI schemes")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate agent scope, evidence and experiment reproducibility")
    subparsers = parser.add_subparsers(dest="command", required=True)
    e = subparsers.add_parser("evidence")
    e.add_argument("--input", required=True, type=Path)
    x = subparsers.add_parser("experiment")
    x.add_argument("--input", required=True, type=Path)
    s = subparsers.add_parser("scope")
    s.add_argument("--task-id", required=True)
    s.add_argument("--file", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        if args.command == "evidence":
            errors = validate_evidence(read_payload(args.input))
        elif args.command == "experiment":
            errors = validate_experiment(read_payload(args.input))
        else:
            errors = check_scope(args.task_id, args.file, read_payload(SCOPES))
    except (ContractError, TypeError, KeyError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if errors:
        for message in errors:
            print(f"FAIL: {message}", file=sys.stderr)
        return 1
    print(f"PASS: {args.command} governance contract (no canonical state changed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
