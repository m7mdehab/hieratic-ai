"""Dry-run policy planner and validator for data acquisition manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "sources" / "registry.yaml"
SCHEMA_PATH = ROOT / "schemas" / "acquisition_manifest.schema.json"


class AcquisitionError(Exception):
    """Input or schema error suitable for the CLI."""


def _load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise AcquisitionError(f"{path}: cannot read valid YAML: {exc}") from exc


def _validate_https_urls(item: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    synthetic = item.get("is_synthetic_fixture", False)

    def valid_evidence_url(url: str) -> bool:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        placeholder = host in {"example.com", "example.org", "example.net"} or host.endswith((".invalid", ".example", ".test"))
        return parts.scheme == "https" and bool(parts.netloc) and not parts.username and not parts.password and (synthetic or not placeholder)

    for field in ("canonical_object_url", "exact_access_url"):
        url = item.get(field)
        if url is None:
            continue
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
            errors.append(f"items[{index}].{field}: expected an absolute HTTPS URL")
    for field in ("provenance_urls", "evidence_urls"):
        for url_index, url in enumerate(item.get(field, [])):
            if not valid_evidence_url(url):
                errors.append(f"items[{index}].{field}[{url_index}]: expected an absolute HTTPS URL with non-placeholder evidence")
    return errors


def _review_reference_is_valid(reference: str | None, synthetic: bool) -> bool:
    if not reference or not reference.strip():
        return False
    if synthetic:
        return reference.startswith("synthetic:")
    parts = urlsplit(reference)
    host = (parts.hostname or "").lower()
    placeholder = host in {"example.com", "example.org", "example.net"} or host.endswith(
        (".invalid", ".example", ".test")
    )
    return (
        parts.scheme == "https"
        and bool(host)
        and not parts.username
        and not parts.password
        and parts.path not in {"", "/"}
        and not placeholder
    )


def _review_value_is_known(value: str | None) -> bool:
    return bool(value and value.strip() and value.strip().lower() not in {"unknown", "unresolved", "n/a", "none"})


def logical_fingerprint(item: dict[str, Any]) -> str:
    """Hash stable identity fields; retrieval-event data intentionally does not affect it."""
    identity = {
        "source_id": item["source_id"],
        "source_object_id": item["source_object_id"],
        "canonical_object_url": item["canonical_object_url"],
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_data(manifest: Any, registry: Any, schema: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    schema_errors = sorted(validator.iter_errors(manifest), key=lambda error: list(map(str, error.absolute_path)))
    errors = [f"manifest{''.join(f'[{part!r}]' for part in error.absolute_path)}: {error.message}" for error in schema_errors]
    if errors:
        return errors, []

    source_by_id = {source["source_id"]: source for source in registry["sources"]}
    plans: list[dict[str, Any]] = []
    seen_fingerprints: set[str] = set()
    for index, item in enumerate(manifest["items"]):
        item_errors = _validate_https_urls(item, index)
        source_id = item["source_id"]
        source = source_by_id.get(source_id)
        if source is None:
            errors.append(f"items[{index}].source_id: unknown source_id {source_id}")
            plans.append({
                "item": item,
                "decision": "REFUSED",
                "planning_status": "REFUSED",
                "admission_status": "NOT ADMITTED — planner performs no acquisition or corpus admission",
                "reasons": ["unknown source_id"],
            })
            continue

        use = item["intended_use"]
        if item["source_rights_snapshot"]["rights_class"] != source["rights_class"]:
            item_errors.append("rights_class snapshot does not match the source registry")
        if source["benchmark_quarantine"] != item["benchmark_quarantine"]:
            item_errors.append("benchmark_quarantine snapshot does not match the source registry")
        if source["benchmark_overlap_risk"] != item["benchmark_overlap_risk"]:
            item_errors.append("benchmark_overlap_risk snapshot does not match the source registry")
        if item["required_attribution"] != source["attribution_requirements"]:
            item_errors.append("required_attribution must preserve the source registry requirement")

        if use == "reference":
            if item["acquisition_mode"] != "metadata_only":
                item_errors.append("reference use must use metadata_only mode")
            if item["acquisition_status"] == "complete":
                item_errors.append("reference-only metadata records cannot declare acquisition complete")
            if item["source_rights_snapshot"]["use_decision"] != "metadata_only":
                item_errors.append("reference use snapshot must be metadata_only")
            decision = "ALLOWED"
            reasons = ["metadata-only reference; no source content is acquired"]
        else:
            decision = source[f"{use}_use"].upper()
            reasons = []
            if item["source_rights_snapshot"]["use_decision"] != source[f"{use}_use"]:
                item_errors.append("use_decision snapshot does not match the source registry")
            if source["rights_class"] == "EVALUATION-ONLY" and use in {"training", "development"}:
                item_errors.append("EVALUATION-ONLY sources cannot be used for training or development")
            if source["benchmark_quarantine"] and use in {"training", "development"}:
                item_errors.append("benchmark-quarantined sources cannot be used for training or development")
            if source[f"{use}_use"] in {"prohibited", "not_approved", "metadata_only"}:
                item_errors.append(f"source registry decision {source[f'{use}_use']} refuses {use} use")
        conditions_required = (
            use != "reference" and source[f"{use}_use"] == "conditional"
        ) or (
            item["redistribution_requested"] and source["redistribution_use"] == "conditional"
        )
        if conditions_required:
            required_conditions = set(source["automated_access_constraints"]) | set(source["project_review_markers"])
            condition_map = {condition["condition_id"]: condition for condition in item["review_conditions"]}
            missing_conditions = sorted(required_conditions - condition_map.keys())
            if missing_conditions:
                item_errors.append(f"conditional use or redistribution lacks explicit conditions: {', '.join(missing_conditions)}")
            for condition_id in sorted(required_conditions & condition_map.keys()):
                condition = condition_map[condition_id]
                if not condition["satisfied"]:
                    item_errors.append(f"condition {condition_id} is not satisfied")
                if not condition["evidence_urls"]:
                    item_errors.append(f"condition {condition_id} lacks evidence URLs")
                elif not item["is_synthetic_fixture"] and any(
                    not _review_reference_is_valid(url, False) for url in condition["evidence_urls"]
                ):
                    item_errors.append(f"condition {condition_id} uses placeholder evidence")
            reasons.append("conditional registry use; all registry conditions must be evidenced")

        item_rights_required = (
            use in {"training", "development"}
            and source["rights_class"] == "PER-ITEM"
            and source[f"{use}_use"] == "conditional"
        )
        overlap_review_required = use in {"training", "development"} and source["benchmark_overlap_risk"] == "high"
        if item_rights_required:
            review = item["item_rights_review"]
            synthetic = item["is_synthetic_fixture"]
            if not _review_value_is_known(review["license_identifier"]):
                item_errors.append("item rights review requires a known item-specific license identifier")
            if not _review_value_is_known(review["rightsholder"]):
                item_errors.append("item rights review requires an identified rightsholder")
            if review["approval_status"] != "approved":
                item_errors.append("item rights review lacks reviewer approval")
            if not _review_value_is_known(review["reviewer_id"]):
                item_errors.append("item rights review requires an accountable reviewer")
            if not _review_reference_is_valid(review["evidence_ref"], synthetic):
                item_errors.append("item rights review requires non-placeholder evidence reference")
            if not review["reviewed_at"]:
                item_errors.append("item rights review requires a review date")
            item_url = review["item_url"]
            if synthetic:
                if not item_url or not item_url.startswith("synthetic://"):
                    item_errors.append("synthetic fixture item rights review requires a synthetic:// item URL")
            else:
                item_host = (urlsplit(item_url or "").hostname or "").lower()
                source_host = (urlsplit(source["canonical_url"]).hostname or "").lower()
                if not item_url or urlsplit(item_url).scheme != "https" or item_host != source_host or urlsplit(item_url).path in {"", "/"}:
                    item_errors.append("item rights review requires an item-specific HTTPS URL on the registered source host")

        if overlap_review_required:
            review = item["benchmark_overlap_review"]
            synthetic = item["is_synthetic_fixture"]
            if review["status"] != "clear":
                item_errors.append("high-risk training/development use requires a clear benchmark-overlap assessment")
            if not _review_value_is_known(review["reviewer_id"]):
                item_errors.append("benchmark-overlap assessment requires an accountable reviewer")
            if not _review_reference_is_valid(review["evidence_ref"], synthetic):
                item_errors.append("benchmark-overlap assessment requires non-placeholder evidence reference")
            if not _review_value_is_known(review["overlap_check_version"]):
                item_errors.append("benchmark-overlap assessment requires a versioned check")
            if not review["reviewed_at"]:
                item_errors.append("benchmark-overlap assessment requires a review date")
        if item["redistribution_requested"] and source["redistribution_use"] not in {"allowed", "conditional"}:
            item_errors.append(f"source registry decision {source['redistribution_use']} refuses redistribution")
        if item["redistribution_requested"]:
            rights_evidence = set(source["rights_evidence_urls"])
            if not rights_evidence:
                item_errors.append("source registry has no rights evidence for requested redistribution")
            if not rights_evidence <= set(item["evidence_urls"]):
                item_errors.append("manifest evidence_urls must include source rights_evidence_urls for redistribution")
        if use != "reference":
            reasons.append(f"source registry {use} decision: {source[f'{use}_use']}")

        if item["acquisition_status"] == "complete" and item["acquisition_mode"] in {"direct_download", "iiif", "api"}:
            if not item["actual_sha256"]:
                item_errors.append("complete downloaded artifact requires actual_sha256")
            if not item["retrieval_timestamp"]:
                item_errors.append("complete downloaded artifact requires retrieval_timestamp")
        fingerprint = logical_fingerprint(item)
        if fingerprint in seen_fingerprints:
            item_errors.append(f"duplicate logical acquisition fingerprint {fingerprint}")
        seen_fingerprints.add(fingerprint)
        if item_errors:
            decision = "REFUSED"
            reasons.extend(item_errors)
            errors.extend(f"items[{index}]: {message}" for message in item_errors)
        elif decision == "CONDITIONAL":
            decision = "CONDITIONAL PLAN READY"
        admission_status = "NOT ADMITTED — planner performs no acquisition or corpus admission"
        if item["is_synthetic_fixture"]:
            admission_status = "NOT ADMITTED — synthetic fixture only"
        plans.append({
            "item": item,
            "decision": decision,
            "planning_status": decision,
            "admission_status": admission_status,
            "reasons": reasons,
            "fingerprint": fingerprint,
        })
    return errors, plans


def load_and_validate(manifest_path: Path, registry_path: Path = REGISTRY_PATH, schema_path: Path = SCHEMA_PATH):
    manifest = _load_yaml(manifest_path)
    registry = _load_yaml(registry_path)
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcquisitionError(f"{schema_path}: cannot read valid JSON Schema: {exc}") from exc
    return validate_data(manifest, registry, schema)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.acquisition")
    parser.add_argument("command", choices=["plan", "validate"])
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    args = parser.parse_args(argv)
    try:
        errors, plans = load_and_validate(args.manifest, args.registry, args.schema)
    except AcquisitionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for plan in plans:
        item = plan["item"]
        print(f"PLAN: {plan['planning_status']} — {item['source_id']} / {item['source_object_id']} ({item['intended_use']})")
        print(f"ADMISSION: {plan['admission_status']}")
        print(f"  target: {item['expected_path']}")
        print(f"  fingerprint: {plan.get('fingerprint', 'unavailable')}")
        for reason in plan["reasons"]:
            print(f"  - {reason}")
    if errors:
        print("Acquisition manifest validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"PASS: {len(plans)} acquisition manifest item(s) validated; no network calls made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
