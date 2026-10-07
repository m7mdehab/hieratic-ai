"""Validate the machine-readable external source and rights registry."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "sources" / "registry.yaml"
SCHEMA_PATH = ROOT / "schemas" / "data_sources.schema.json"


class SourceRegistryError(Exception):
    """A user-facing source-registry input error."""


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise SourceRegistryError(f"{path}: cannot read valid YAML: {exc}") from exc


def validate_registry_data(registry: Any, schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validation_errors = sorted(
        validator.iter_errors(registry),
        key=lambda error: list(map(str, error.absolute_path)),
    )
    errors = [
        f"registry{''.join(f'[{part!r}]' for part in error.absolute_path)}: {error.message}"
        for error in validation_errors
    ]
    if errors:
        return errors

    sources = registry["sources"]
    counts = Counter(source["source_id"] for source in sources)
    for source_id, count in sorted(counts.items()):
        if count > 1:
            errors.append(f"Duplicate source_id {source_id} ({count} records)")

    for source in sources:
        source_id = source["source_id"]
        if source["verified_status"] == "VERIFIED-PRIMARY" and not source["evidence_urls"]:
            errors.append(f"{source_id}: VERIFIED-PRIMARY requires at least one evidence URL")

        for field in ("canonical_url", "access_url", "license_url"):
            url = source.get(field)
            if url is not None:
                parts = urlsplit(url)
                if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
                    errors.append(f"{source_id}.{field}: expected an absolute HTTPS URL")
        for field in ("evidence_urls", "rights_evidence_urls"):
            for index, url in enumerate(source[field]):
                parts = urlsplit(url)
                if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
                    errors.append(f"{source_id}.{field}[{index}]: expected an absolute HTTPS URL")

        if source["rights_class"] == "EVALUATION-ONLY":
            if source["training_use"] != "prohibited" or source["development_use"] != "prohibited":
                errors.append(f"{source_id}: EVALUATION-ONLY requires training and development use to be prohibited")
        if source["benchmark_quarantine"] and (
            source["training_use"] != "prohibited" or source["development_use"] != "prohibited"
        ):
            errors.append(f"{source_id}: benchmark quarantine requires training and development use to be prohibited")

        redistribution = source["redistribution_use"]
        if redistribution in {"allowed", "conditional"} and not source["rights_evidence_urls"]:
            errors.append(f"{source_id}: redistribution requires rights evidence URLs")

        if source_id == "SRC-HIERATICBENCH":
            if source["rights_class"] != "EVALUATION-ONLY":
                errors.append("SRC-HIERATICBENCH: rights_class must remain EVALUATION-ONLY")
            if not source["benchmark_quarantine"]:
                errors.append("SRC-HIERATICBENCH: benchmark_quarantine must be true")
            if source["benchmark_overlap_risk"] != "high":
                errors.append("SRC-HIERATICBENCH: benchmark_overlap_risk must be high")

        if source_id == "SRC-TLA":
            required_constraints = {"no_bulk_scraping", "no_bulk_corpus_construction"}
            absent = required_constraints - set(source["automated_access_constraints"])
            if absent:
                errors.append(f"SRC-TLA: missing automated access constraints: {', '.join(sorted(absent))}")
            if source["training_use"] != "prohibited":
                errors.append("SRC-TLA: live-site training use must be prohibited")

        if source_id == "SRC-DDD":
            if source["rights_class"] != "NONCOMMERCIAL":
                errors.append("SRC-DDD: rights_class must be NONCOMMERCIAL")
            if "PER-ITEM" not in source["project_review_markers"]:
                errors.append("SRC-DDD: per-image review marker is required")
            if source["commercial_use"] != "prohibited":
                errors.append("SRC-DDD: commercial use must be prohibited")

    return errors


def validate_files(registry_path: Path = REGISTRY_PATH, schema_path: Path = SCHEMA_PATH) -> tuple[list[str], Any]:
    registry = load_yaml(registry_path)
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceRegistryError(f"{schema_path}: cannot read valid JSON Schema: {exc}") from exc
    return validate_registry_data(registry, schema), registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.source_registry")
    parser.add_argument("command", choices=["validate"], help="validate the canonical source registry")
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH, help="registry YAML path")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH, help="JSON Schema path")
    args = parser.parse_args(argv)
    try:
        errors, registry = validate_files(args.registry, args.schema)
    except SourceRegistryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("Source registry validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"PASS: source registry is valid ({len(registry['sources'])} source records).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
