"""Deterministic leakage-aware evaluation split generator and validator."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
PROFILES_PATH = ROOT / "eval" / "splits" / "profiles.yaml"
MANIFEST_SCHEMA_PATH = ROOT / "schemas" / "split_manifest.schema.json"
GENERATOR_VERSION = "split-system/1.0.0"
HASH_FIELDS = ("image_sha256", "normalized_sha256")
COPIED_FIELDS = (
    "document_id", "page_id", "source_id", "source_object_id", "institution", "scribe_group", "period",
    "material_support", "genre_register", "image_sha256", "normalized_sha256", "perceptual_hash", "benchmark_quarantine",
)


class SplitInputError(Exception):
    """Invalid split metadata, profile, or manifest."""


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise SplitInputError(f"{path}: cannot read valid YAML: {exc}") from exc


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def metadata_digest(metadata: dict[str, Any]) -> str:
    normalized = _json_value(metadata)
    if isinstance(normalized.get("items"), list):
        normalized["items"] = sorted(normalized["items"], key=lambda item: item["item_id"])
    if isinstance(normalized.get("near_duplicate_candidates"), list):
        normalized["near_duplicate_candidates"] = sorted(
            normalized["near_duplicate_candidates"],
            key=lambda pair: (pair["left_item_id"], pair["right_item_id"], pair["method"]),
        )
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_metadata(metadata: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(metadata, dict) or not isinstance(metadata.get("metadata_version"), str) or not metadata["metadata_version"]:
        return ["source metadata requires a non-empty metadata_version"]
    if not isinstance(metadata.get("items"), list) or not metadata["items"]:
        return ["source metadata requires a non-empty items list"]
    seen: set[str] = set()
    required = {"item_id", "source_id", "source_object_id", "document_id", "page_id", "institution", "scribe_group", "period", "material_support", "genre_register", "image_sha256", "normalized_sha256", "perceptual_hash", "benchmark_quarantine"}
    for index, item in enumerate(metadata["items"]):
        if not isinstance(item, dict):
            errors.append(f"items[{index}] must be an object")
            continue
        missing = sorted(required - item.keys())
        if missing:
            errors.append(f"items[{index}] missing fields: {', '.join(missing)}")
            continue
        item_id = item["item_id"]
        if not isinstance(item_id, str) or not item_id:
            errors.append(f"items[{index}].item_id must be a non-empty string")
        elif item_id in seen:
            errors.append(f"duplicate item_id: {item_id}")
        else:
            seen.add(item_id)
        for field in ("source_id", "document_id"):
            if not isinstance(item[field], str) or not item[field]:
                errors.append(f"items[{index}].{field} must be a non-empty string")
        for field in ("source_object_id", "page_id", "institution", "scribe_group", "period", "material_support", "genre_register", "perceptual_hash"):
            if item[field] is not None and not isinstance(item[field], str):
                errors.append(f"items[{index}].{field} must be a string or null")
        for field in HASH_FIELDS:
            value = item[field]
            if value is not None and (not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdefABCDEF" for char in value)):
                errors.append(f"items[{index}].{field} must be a 64-character SHA-256 or null")
        if not isinstance(item["benchmark_quarantine"], bool):
            errors.append(f"items[{index}].benchmark_quarantine must be boolean")
    item_ids = {item.get("item_id") for item in metadata["items"] if isinstance(item, dict)}
    candidate_pairs: set[tuple[str, str]] = set()
    for index, pair in enumerate(metadata.get("near_duplicate_candidates", [])):
        required_pair_fields = {"left_item_id", "right_item_id", "method", "similarity", "review_status", "reviewer_id", "evidence_ref"}
        if not isinstance(pair, dict) or required_pair_fields - pair.keys():
            errors.append(f"near_duplicate_candidates[{index}] is missing required review fields")
            continue
        left, right = pair["left_item_id"], pair["right_item_id"]
        if left not in item_ids or right not in item_ids or left == right:
            errors.append(f"near_duplicate_candidates[{index}] must reference two different known item IDs")
        pair_key = tuple(sorted((left, right)))
        if pair_key in candidate_pairs:
            errors.append(f"duplicate near-duplicate candidate pair: {pair_key}")
        candidate_pairs.add(pair_key)
        if pair["review_status"] not in {"pending", "same_content", "distinct_content"}:
            errors.append(f"near_duplicate_candidates[{index}].review_status is invalid")
        if pair["method"] not in {"perceptual_hash", "embedding_similarity", "manual", "other"}:
            errors.append(f"near_duplicate_candidates[{index}].method is invalid")
        if pair["review_status"] != "pending" and (not pair["reviewer_id"] or not pair["evidence_ref"]):
            errors.append(f"near_duplicate_candidates[{index}] resolved status requires reviewer_id and evidence_ref")
    return errors


class _UnionFind:
    def __init__(self, values: list[str]) -> None:
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        if self.parent[value] != value:
            self.parent[value] = self.find(self.parent[value])
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            first, second = sorted((a, b))
            self.parent[second] = first


def _atomic_components(metadata: dict[str, Any]) -> list[list[dict[str, Any]]]:
    items = metadata["items"]
    ids = [item["item_id"] for item in items]
    union = _UnionFind(ids)
    keyed: dict[tuple[Any, ...], str] = {}
    for item in items:
        keys = [("document", item["document_id"])]
        if item["page_id"] is not None:
            keys.append(("page", item["page_id"]))
        if item["source_object_id"] is not None:
            keys.append(("source_object", item["source_id"], item["source_object_id"]))
        for field in HASH_FIELDS:
            if item[field]:
                keys.append((field, item[field].lower()))
        for key in keys:
            if key in keyed:
                union.union(item["item_id"], keyed[key])
            else:
                keyed[key] = item["item_id"]
    by_id = {item["item_id"]: item for item in items}
    for pair in metadata.get("near_duplicate_candidates", []):
        if pair.get("review_status") == "same_content" and pair.get("left_item_id") in by_id and pair.get("right_item_id") in by_id:
            union.union(pair["left_item_id"], pair["right_item_id"])
    components: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        components[union.find(item["item_id"])].append(item)
    return [sorted(component, key=lambda item: item["item_id"]) for _, component in sorted(components.items())]


def _component_id(component: list[dict[str, Any]]) -> str:
    return hashlib.sha256("\n".join(item["item_id"] for item in component).encode("utf-8")).hexdigest()[:16]


def _allocate(components: list[list[dict[str, Any]]], ratios: dict[str, float], seed: int, profile_id: str, stratify_by: list[str]) -> tuple[dict[str, str], list[str]]:
    total_ratio = sum(ratios.values())
    if not ratios or any(value <= 0 for value in ratios.values()) or abs(total_ratio - 1.0) > 1e-9:
        raise SplitInputError("partition ratios must be positive and sum to 1")
    strata: dict[tuple[str, ...], list[list[dict[str, Any]]]] = defaultdict(list)
    for component in components:
        stratum_values: list[str] = []
        for field in stratify_by:
            values = sorted({str(item.get(field) or "UNKNOWN") for item in component})
            stratum_values.append("|".join(values))
        strata[tuple(stratum_values)].append(component)
    assignments: dict[str, str] = {}
    warnings: list[str] = []
    minimum = len(ratios)
    for stratum, members in sorted(strata.items()):
        ranked = sorted(members, key=lambda component: hashlib.sha256(f"{seed}|{profile_id}|{stratum}|{_component_id(component)}".encode()).hexdigest())
        raw_counts = {part: len(ranked) * ratio for part, ratio in ratios.items()}
        counts = {part: int(raw) for part, raw in raw_counts.items()}
        remainder = len(ranked) - sum(counts.values())
        partition_order = list(ratios)
        for part in sorted(partition_order, key=lambda name: (-(raw_counts[name] - counts[name]), partition_order.index(name)))[:remainder]:
            counts[part] += 1
        cursor = 0
        for part in partition_order:
            for component in ranked[cursor:cursor + counts[part]]:
                for item in component:
                    assignments[item["item_id"]] = part
            cursor += counts[part]
        if len(ranked) < minimum or any(count == 0 for count in counts.values()):
            warnings.append(f"low_sample_stratum {stratum!r}: {len(ranked)} atomic groups for {len(ratios)} requested partitions; one or more partitions may be empty")
    return assignments, warnings


def _profile_config(profile_id: str, profile_set: dict[str, Any]) -> dict[str, Any]:
    try:
        profile = profile_set["profiles"][profile_id]
    except KeyError as exc:
        raise SplitInputError(f"unknown split profile: {profile_id}") from exc
    if profile.get("kind") == "policy_only" or profile.get("instantiable") is False:
        raise SplitInputError(f"{profile_id} is a policy profile and cannot generate a production split")
    return profile


def _near_duplicate_queue(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {item["item_id"]: item for item in metadata["items"]}
    queue = [dict(pair) for pair in metadata.get("near_duplicate_candidates", [])]
    phashes: dict[str, list[str]] = defaultdict(list)
    for item in metadata["items"]:
        value = item.get("perceptual_hash")
        if value:
            phashes[value].append(item["item_id"])
    existing = {(pair["left_item_id"], pair["right_item_id"]) for pair in queue}
    for value, item_ids in phashes.items():
        if len(item_ids) < 2:
            continue
        for index, left in enumerate(sorted(item_ids)):
            for right in sorted(item_ids)[index + 1:]:
                pair = (left, right)
                if pair not in existing and by_id[left]["image_sha256"] != by_id[right]["image_sha256"]:
                    queue.append({"left_item_id": left, "right_item_id": right, "method": "perceptual_hash", "similarity": 1.0, "review_status": "pending", "reviewer_id": None, "evidence_ref": f"same perceptual_hash={value}"})
    return sorted(queue, key=lambda pair: (pair["left_item_id"], pair["right_item_id"], pair["method"]))


def _stats(assignments: list[dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "item_counts": {part: sum(row["partition"] == part for row in assignments) for part in ("train", "dev", "test", "excluded")},
        "document_counts": {part: len({row["document_id"] for row in assignments if row["partition"] == part}) for part in ("train", "dev", "test", "excluded")},
        "dimension_counts": {},
        "warning_count": len(warnings),
    }
    for field in ("source_id", "institution", "scribe_group", "period", "material_support", "genre_register"):
        by_value: dict[str, dict[str, int]] = {}
        for row in assignments:
            value = row[field] or "UNKNOWN"
            tally = by_value.setdefault(value, {part: 0 for part in ("train", "dev", "test", "excluded")})
            tally[row["partition"]] += 1
        stats["dimension_counts"][field] = by_value
    stats["known_scribe_counts"] = {part: len({row["scribe_group"] for row in assignments if row["partition"] == part and row["scribe_group"]}) for part in ("train", "dev", "test", "excluded")}
    stats["excluded_or_quarantined_count"] = stats["item_counts"]["excluded"]
    return stats


def generate_manifest(metadata: dict[str, Any], profile_set: dict[str, Any], profile_id: str, seed: int, holdout_values: list[str] | None = None, generated_at: str | None = None) -> dict[str, Any]:
    metadata_errors = _validate_metadata(metadata)
    if metadata_errors:
        raise SplitInputError("; ".join(metadata_errors))
    profile = _profile_config(profile_id, profile_set)
    holdout_values = sorted(set(holdout_values or []))
    if profile["kind"] == "metadata_holdout" and not holdout_values:
        raise SplitInputError(f"{profile_id} requires at least one --holdout-value")
    if profile["kind"] == "group_holdout":
        ratios = profile["ratios"]
        stratify_by = profile.get("stratify_by", [])
    else:
        ratios = profile["remaining_ratios"]
        stratify_by = profile.get("stratify_by", ["source_id"])

    items = metadata["items"]
    by_id = {item["item_id"]: item for item in items}
    components = _atomic_components(metadata)
    quarantine_sources = set(profile_set.get("benchmark_quarantine_source_ids", [])) | set(metadata.get("quarantined_source_ids", []))
    quarantine_objects = set(profile_set.get("known_benchmark_item_ids", [])) | set(metadata.get("quarantined_object_ids", []))
    assigned: dict[str, str] = {}
    reasons: dict[str, str | None] = {}
    eligible_components: list[list[dict[str, Any]]] = []
    for component in components:
        quarantined = any(item["benchmark_quarantine"] or item["source_id"] in quarantine_sources or item["item_id"] in quarantine_objects or item["source_object_id"] in quarantine_objects for item in component)
        if quarantined:
            bench_ids = sorted(item["item_id"] for item in component if item["benchmark_quarantine"] or item["source_id"] in quarantine_sources or item["item_id"] in quarantine_objects or item["source_object_id"] in quarantine_objects)
            reason = "benchmark_quarantine" if len(bench_ids) == len(component) else f"linked_to_quarantined_benchmark:{','.join(bench_ids)}"
            for item in component:
                assigned[item["item_id"]] = "excluded"
                reasons[item["item_id"]] = reason
        else:
            eligible_components.append(component)
            for item in component:
                reasons[item["item_id"]] = None

    warnings: list[str] = []
    if profile["kind"] == "group_holdout":
        allocated, allocation_warnings = _allocate(eligible_components, ratios, seed, profile_id, stratify_by)
        assigned.update(allocated)
        warnings.extend(allocation_warnings)
    else:
        field = profile["holdout_dimension"]
        remaining: list[list[dict[str, Any]]] = []
        held_values_present: set[str] = set()
        for component in eligible_components:
            values = {str(item[field]) for item in component if item.get(field) is not None}
            if values & set(holdout_values):
                for item in component:
                    assigned[item["item_id"]] = profile["held_partition"]
            elif field == "scribe_group" and any(item.get(field) is None for item in component):
                unknown_policy = profile["unknown_value_policy"]
                part = {"train_only": "train", "exclude": "excluded"}.get(unknown_policy)
                if part is None:
                    raise SplitInputError(f"unsupported unknown scribe policy: {unknown_policy}")
                for item in component:
                    assigned[item["item_id"]] = part
                    reasons[item["item_id"]] = "unknown_scribe_policy" if part == "excluded" else None
            else:
                remaining.append(component)
            held_values_present.update(values & set(holdout_values))
        missing_holdouts = sorted(set(holdout_values) - held_values_present)
        if missing_holdouts:
            warnings.append(f"requested holdout values absent from metadata: {', '.join(missing_holdouts)}")
        remaining_assignments, allocation_warnings = _allocate(remaining, ratios, seed, profile_id, stratify_by)
        assigned.update(remaining_assignments)
        warnings.extend(allocation_warnings)

    queue = _near_duplicate_queue(metadata)
    assignments: list[dict[str, Any]] = []
    component_ids = {item["item_id"]: _component_id(component) for component in components for item in component}
    for item in sorted(items, key=lambda row: row["item_id"]):
        row = {field: item[field] for field in COPIED_FIELDS}
        row.update({"item_id": item["item_id"], "partition": assigned[item["item_id"]], "exclusion_reason": reasons[item["item_id"]], "atomic_group_id": component_ids[item["item_id"]]})
        assignments.append(row)
    for pair in queue:
        left, right = pair["left_item_id"], pair["right_item_id"]
        if left not in by_id or right not in by_id:
            raise SplitInputError(f"near-duplicate pair references unknown item: {left}, {right}")
        if pair["review_status"] == "same_content" and assigned[left] != assigned[right]:
            raise SplitInputError(f"confirmed near-duplicate pair crosses partitions: {left}, {right}")
        if pair["review_status"] == "pending" and assigned[left] != assigned[right]:
            raise SplitInputError(f"pending near-duplicate review must be resolved before pair crosses partitions: {left}, {right}")
        if pair["review_status"] == "pending":
            warnings.append(f"near_duplicate_review_pending: {left} / {right}; same partition retained pending review")

    grouping_keys = ["document_id", "page_id", "source_id", "source_object_id", "image_sha256", "normalized_sha256"]
    if profile["kind"] == "metadata_holdout":
        if profile["holdout_dimension"] not in grouping_keys:
            grouping_keys.append(profile["holdout_dimension"])
    if any(item["perceptual_hash"] for item in items) or metadata.get("near_duplicate_candidates"):
        grouping_keys.append("perceptual_hash_review_hook")
    return {
        "split_version": "1.0.0",
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "profile_id": profile_id,
        "source_metadata_version": metadata["metadata_version"],
        "source_metadata_sha256": metadata_digest(metadata),
        "generation_timestamp": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "grouping_keys_used": grouping_keys,
        "holdout_values": holdout_values,
        "assignments": assignments,
        "near_duplicate_review_queue": queue,
        "statistics": _stats(assignments, warnings),
        "warnings": warnings,
        "sealed_test_policy": None,
    }


def validate_manifest(manifest: Any, metadata: dict[str, Any], profile_set: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    schema_errors = sorted(validator.iter_errors(manifest), key=lambda error: list(map(str, error.absolute_path)))
    errors = [f"manifest{''.join(f'[{part!r}]' for part in error.absolute_path)}: {error.message}" for error in schema_errors]
    if errors:
        return errors
    errors.extend(_validate_metadata(metadata))
    if errors:
        return errors
    try:
        profile = _profile_config(manifest["profile_id"], profile_set)
    except SplitInputError as exc:
        return [str(exc)]
    if manifest["source_metadata_version"] != metadata["metadata_version"]:
        errors.append("source_metadata_version does not match input metadata")
    if manifest["source_metadata_sha256"] != metadata_digest(metadata):
        errors.append("source_metadata_sha256 does not match input metadata")
    items = {item["item_id"]: item for item in metadata["items"]}
    rows = manifest["assignments"]
    ids = [row["item_id"] for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("duplicate item IDs in split assignments")
    if set(ids) != set(items):
        errors.append("split assignment item IDs do not exactly match input metadata")
    by_id = {row["item_id"]: row for row in rows}
    for item_id in set(items) & set(by_id):
        source_item, row = items[item_id], by_id[item_id]
        for field in COPIED_FIELDS:
            if row[field] != source_item[field]:
                errors.append(f"{item_id}: assignment {field} differs from source metadata")
        if row["partition"] == "excluded" and not row["exclusion_reason"]:
            errors.append(f"{item_id}: excluded item requires an exclusion reason")
        is_quarantined = source_item["benchmark_quarantine"] or source_item["source_id"] in set(profile_set.get("benchmark_quarantine_source_ids", [])) | set(metadata.get("quarantined_source_ids", [])) or item_id in set(profile_set.get("known_benchmark_item_ids", [])) | set(metadata.get("quarantined_object_ids", [])) or source_item["source_object_id"] in set(profile_set.get("known_benchmark_item_ids", [])) | set(metadata.get("quarantined_object_ids", []))
        if is_quarantined and (row["partition"] in {"train", "dev"} or row["partition"] != "excluded"):
            errors.append(f"{item_id}: benchmark-quarantined item must be excluded with a reason")

    active = [row for row in rows if row["partition"] != "excluded"]
    dimensions = ("document_id", "source_object_id", "image_sha256", "normalized_sha256")
    for field in dimensions:
        buckets: dict[str, set[str]] = defaultdict(set)
        for row in active:
            value = row[field]
            if value is not None:
                if field == "source_object_id":
                    value = f"{row['source_id']}::{value}"
                buckets[str(value).lower() if field.endswith("sha256") else str(value)].add(row["partition"])
        for value, partitions in buckets.items():
            if len(partitions) > 1:
                label = "exact hash" if field.endswith("sha256") else field
                errors.append(f"{label} {value} overlaps partitions: {', '.join(sorted(partitions))}")
    page_buckets: dict[str, set[str]] = defaultdict(set)
    for row in active:
        if row["page_id"] is not None:
            page_buckets[row["page_id"]].add(row["partition"])
    for key, partitions in page_buckets.items():
        if len(partitions) > 1:
            errors.append(f"page {key} overlaps partitions: {', '.join(sorted(partitions))}")

    if profile["kind"] == "metadata_holdout" and not manifest["holdout_values"]:
        errors.append(f"{manifest['profile_id']} requires one or more holdout_values")
    if manifest["profile_id"] == "PROFILE-SCRIBE-HOLDOUT":
        held = set(manifest["holdout_values"])
        for row in rows:
            if row["partition"] == "train" and row["scribe_group"] in held:
                errors.append(f"held-out scribe {row['scribe_group']} appears in train")
    if manifest["profile_id"] == "PROFILE-SOURCE-HOLDOUT":
        for row in rows:
            if row["source_id"] in set(manifest["holdout_values"]) and row["partition"] not in {"test", "excluded"}:
                errors.append(f"held-out source {row['source_id']} appears outside test/excluded")
    if manifest["profile_id"] == "PROFILE-PERIOD-HOLDOUT":
        for row in rows:
            if row["period"] in set(manifest["holdout_values"]) and row["partition"] not in {"test", "excluded"}:
                errors.append(f"held-out period {row['period']} appears outside test/excluded")

    queue = manifest["near_duplicate_review_queue"]
    queue_pairs = set()
    for pair in queue:
        left, right = pair["left_item_id"], pair["right_item_id"]
        if left not in by_id or right not in by_id:
            errors.append(f"near-duplicate review pair references missing item: {left}, {right}")
            continue
        pair_key = tuple(sorted((left, right)))
        queue_pairs.add(pair_key)
        if pair["review_status"] in {"same_content", "pending"} and by_id[left]["partition"] != by_id[right]["partition"]:
            errors.append(f"near-duplicate pair crosses partitions: {left}, {right} ({pair['review_status']})")
    for pair in metadata.get("near_duplicate_candidates", []):
        if tuple(sorted((pair["left_item_id"], pair["right_item_id"]))) not in queue_pairs:
            errors.append(f"manifest omits near-duplicate review pair: {pair['left_item_id']}, {pair['right_item_id']}")

    if manifest["profile_id"] == "PROFILE-SEALED-TEST":
        errors.append("PROFILE-SEALED-TEST is policy-only; production membership is not generated here")
    expected_keys = ["document_id", "page_id", "source_id", "source_object_id", "image_sha256", "normalized_sha256"]
    if profile["kind"] == "metadata_holdout":
        if profile["holdout_dimension"] not in expected_keys:
            expected_keys.append(profile["holdout_dimension"])
    if any(item["perceptual_hash"] for item in metadata["items"]) or metadata.get("near_duplicate_candidates"):
        expected_keys.append("perceptual_hash_review_hook")
    if manifest["grouping_keys_used"] != expected_keys:
        errors.append("grouping_keys_used does not match the selected profile and available overlap hooks")
    try:
        reproducible = generate_manifest(metadata, profile_set, manifest["profile_id"], manifest["seed"], manifest["holdout_values"], manifest["generation_timestamp"])
    except SplitInputError as exc:
        errors.append(f"split cannot be reproduced: {exc}")
    else:
        expected_partitions = {row["item_id"]: row["partition"] for row in reproducible["assignments"]}
        actual_partitions = {row["item_id"]: row["partition"] for row in rows}
        if actual_partitions != expected_partitions:
            errors.append("partition membership does not reproduce from input metadata, profile, and seed")
        if manifest["statistics"] != reproducible["statistics"]:
            errors.append("split statistics do not match assignments")
    return errors


def _dump_yaml(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.split_system")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate")
    generate.add_argument("--metadata", type=Path, required=True)
    generate.add_argument("--profile", required=True)
    generate.add_argument("--seed", type=int, required=True)
    generate.add_argument("--holdout-value", action="append", default=[])
    generate.add_argument("--output", type=Path, required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--metadata", type=Path, required=True)
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--profiles", type=Path, default=PROFILES_PATH)
    validate.add_argument("--schema", type=Path, default=MANIFEST_SCHEMA_PATH)
    args = parser.parse_args(argv)
    try:
        profile_set = load_yaml(args.profiles) if hasattr(args, "profiles") else load_yaml(PROFILES_PATH)
        metadata = load_yaml(args.metadata)
        if args.command == "generate":
            manifest = generate_manifest(metadata, profile_set, args.profile, args.seed, args.holdout_value)
            schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
            errors = validate_manifest(manifest, metadata, profile_set, schema)
            if errors:
                print("Split generation refused:", file=sys.stderr)
                for error in errors:
                    print(f"- {error}", file=sys.stderr)
                return 1
            _dump_yaml(args.output, manifest)
            print(f"PASS: generated {args.profile} for {len(manifest['assignments'])} synthetic/metadata items at {args.output}")
            print(json.dumps(manifest["statistics"], sort_keys=True))
            for warning in manifest["warnings"]:
                print(f"WARNING: {warning}")
            return 0
        manifest = load_yaml(args.manifest)
        schema = json.loads(args.schema.read_text(encoding="utf-8"))
        errors = validate_manifest(manifest, metadata, profile_set, schema)
    except (SplitInputError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("Split validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"PASS: {manifest['profile_id']} split manifest is valid for {len(manifest['assignments'])} items.")
    print(json.dumps(manifest["statistics"], sort_keys=True))
    for warning in manifest["warnings"]:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
