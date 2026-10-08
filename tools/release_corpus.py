"""Validate and assemble DATA-008 corpus release packets from accepted contracts.

The command is metadata-first: it never downloads source material. It publishes a
canonical index and audit packet that references immutable preprocessing outputs.
"""
from __future__ import annotations

import argparse
import copy
import ctypes
import errno
import hashlib
import json
import os
import secrets
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from tools import acquisition, alignment, annotation_review, annotation_validation
from tools import preprocessing, sign_mappings, split_system, source_registry

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/dataset_release.schema.json"
ACQ_SCHEMA = ROOT / "schemas/acquisition_manifest.schema.json"
ANNOTATION_SCHEMA = ROOT / "schemas/annotation.schema.json"
ALIGN_SCHEMA = ROOT / "schemas/alignment_manifest.schema.json"
REVIEW_SCHEMA = ROOT / "schemas/annotation_review.schema.json"
MAPPING_SCHEMA = ROOT / "schemas/sign_mappings.schema.json"
SPLIT_SCHEMA = ROOT / "schemas/split_manifest.schema.json"
SPLIT_PROFILES = ROOT / "eval/splits/profiles.yaml"
REGISTRY = ROOT / "data/sources/registry.yaml"
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_ARTIFACT_BYTES = 256 * 1024 * 1024
MAX_RELEASE_BYTES = 512 * 1024 * 1024
GENERATOR = "hieratic-corpus-release/1.0.0"


class ReleaseError(ValueError):
    """Input failed a DATA-008 release gate."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_document(path: Path) -> Any:
    try:
        raw = path.read_bytes()
        if len(raw) > MAX_INPUT_BYTES:
            raise ReleaseError(f"input exceeds {MAX_INPUT_BYTES} byte limit: {path}")
        if path.suffix.lower() == ".json":
            return json.loads(raw.decode("utf-8"))
        return yaml.safe_load(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ReleaseError(f"cannot read {path}: {exc}") from exc


def safe_path(base: Path, relative: str, *, must_exist: bool = True) -> Path:
    """Resolve a bundle-relative path while refusing symlinks and root escape."""
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ReleaseError(f"absolute input path is forbidden: {relative}")
    root = base.resolve(strict=True)
    current = root
    for part in candidate.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            current = current.parent
            if not current.is_relative_to(root):
                raise ReleaseError(f"input path escapes bundle directory: {relative}")
            continue
        current = current / part
        if current.is_symlink():
            raise ReleaseError(f"symlink input path is forbidden: {relative}")
    result = current.resolve(strict=must_exist)
    if not result.is_relative_to(root):
        raise ReleaseError(f"input path escapes bundle directory: {relative}")
    if must_exist and not result.is_file() and not result.is_dir():
        raise ReleaseError(f"input path is not a file or directory: {relative}")
    return result


def _schema_errors(value: Any, path: Path, label: str) -> list[str]:
    schema = read_document(path)
    found = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value), key=lambda e: str(e.absolute_path))
    return [f"{label}{''.join(f'[{part!r}]' for part in err.absolute_path)}: {err.message}" for err in found]


def _read_checked(base: Path, relative: str, audit: list[dict[str, str]]) -> tuple[Any, Path]:
    path = safe_path(base, relative)
    if not path.is_file():
        raise ReleaseError(f"expected a manifest file: {relative}")
    raw = path.read_bytes()
    if len(raw) > MAX_INPUT_BYTES:
        raise ReleaseError(f"input exceeds {MAX_INPUT_BYTES} byte limit: {relative}")
    audit.append({"path": relative.replace("\\", "/"), "sha256": digest(raw), "size_bytes": len(raw)})
    return read_document(path), path


def _map_by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {row[key]: row for row in items}


def _target_annotation(annotation: dict[str, Any], target_type: str, target_id: str) -> dict[str, Any] | None:
    if target_type == "line":
        value = next((x for x in annotation.get("lines", []) if x.get("line_id") == target_id), None)
        if value is None:
            return None
        fields = ("region_id", "parent_line_id", "reading_order", "reading_direction", "geometry", "sequence_id", "grapheme_sequence", "hieroglyphic_rendering", "transliteration", "normalized_representation", "lemma_analysis", "morphology", "syntax", "translations")
        return {"line_id": target_id, "page_id": value.get("page_id"), **{field: copy.deepcopy(value.get(field)) for field in fields}}
    if target_type == "sign":
        value = next((x for x in annotation.get("signs", []) if x.get("sign_id") == target_id), None)
        return copy.deepcopy(value) if value else None
    if target_type == "token":
        for line in annotation.get("lines", []):
            for value in line.get("normalized_representation", {}).get("tokens", []):
                if value.get("token_id") == target_id:
                    return {"token": copy.deepcopy(value), "line_id": line.get("line_id"), "page_id": line.get("page_id")}
    return None


def _validate_source(bundle: dict[str, Any], row: dict[str, Any], base: Path, registry: dict[str, Any],
                     split_metadata: dict[str, Any], split_manifest: dict[str, Any], profile_set: dict[str, Any],
                     audit: list[dict[str, str]], release_kind: str) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    iid = row["item_id"]
    try:
        acq, _ = _read_checked(base, row["acquisition_path"], audit)
        request, request_path = _read_checked(base, row["preprocessing_request_path"], audit)
        artifact_manifest, _ = _read_checked(base, row["preprocessing_artifact_manifest_path"], audit)
        annotation, _ = _read_checked(base, row["annotation_path"], audit)
        mappings, _ = _read_checked(base, row["mapping_path"], audit)
        alignments, _ = _read_checked(base, row["alignment_path"], audit)
        reviews, _ = _read_checked(base, row["review_path"], audit)
    except ReleaseError as exc:
        return {}, [f"{iid}: {exc}"]

    errors += [f"{iid}: {e}" for e in _schema_errors(acq, ACQ_SCHEMA, "DATA-002")]
    acquisition_errors, _ = acquisition.validate_data(acq, registry, read_document(ACQ_SCHEMA))
    if all(item.get("is_synthetic_fixture") is True for item in acq.get("items", [])):
        # Structural fixtures are not permission requests. Preserve every identity,
        # registry, quarantine, and schema error while ignoring only conditional
        # approval completeness that cannot be satisfied by a synthetic fixture.
        acquisition_errors = [e for e in acquisition_errors if "conditional use or redistribution lacks explicit conditions" not in e]
    errors += [f"{iid}: {e}" for e in acquisition_errors]
    errors += [f"{iid}: {e}" for e in annotation_validation.validate_data(annotation, read_document(ANNOTATION_SCHEMA), registry)]
    errors += [f"{iid}: {e}" for e in sign_mappings.validate(mappings, read_document(MAPPING_SCHEMA))]
    alignment_errors, eligibility = alignment.validate(alignments, acq, annotation, registry)
    errors += [f"{iid}: {e}" for e in alignment_errors]
    review_errors, review_report = annotation_review.validate(reviews, annotation, registry)
    errors += [f"{iid}: {e}" for e in review_errors]
    errors += [f"{iid}: {e}" for e in preprocessing.validate_request(request, registry, request_path.parent, acq)]
    if (artifact_manifest.get("generator") != "hieratic-preprocessing/1.0.0"
            or not isinstance(artifact_manifest.get("dataset_version_id"), str)
            or not isinstance(artifact_manifest.get("items"), list)):
        errors.append(f"{iid}: malformed DATA-003 artifact manifest")

    acq_matches = [x for x in acq.get("items", []) if x.get("source_object_id") == annotation.get("provenance", {}).get("source_object_id")]
    if len(acq_matches) != 1:
        errors.append(f"{iid}: annotation source object must match exactly one acquisition item")
        acquired = {}
    else:
        acquired = acq_matches[0]
    source_id = annotation.get("provenance", {}).get("source_registry_id")
    if acquired and source_id != acquired.get("source_id"):
        errors.append(f"{iid}: annotation/acquisition source identity differs")
    source_map = _map_by(registry.get("sources", []), "source_id")
    source = source_map.get(source_id, {})
    if not source:
        errors.append(f"{iid}: unknown DATA-001 source identity {source_id}")
    if acquired and (acquired.get("benchmark_quarantine") or source.get("benchmark_quarantine") or source.get("rights_class") == "EVALUATION-ONLY"):
        errors.append(f"{iid}: benchmark-quarantined or evaluation-only source is excluded")
    if acquired and acquired.get("benchmark_overlap_review", {}).get("status") != "clear" and not acquired.get("is_synthetic_fixture"):
        errors.append(f"{iid}: unresolved DATA-002 benchmark overlap review")

    if artifact_manifest.get("acquisition_manifest_id") != request.get("acquisition_manifest_id"):
        errors.append(f"{iid}: preprocessing artifact manifest/request acquisition identity differs")
    request_bytes_total = 0
    for request_item in request.get("items", []):
        try:
            input_asset = safe_path(request_path.parent, request_item.get("asset_path", ""))
            if not input_asset.is_file():
                errors.append(f"{iid}: DATA-003 input asset is not a file")
                continue
            asset_size = input_asset.stat().st_size
            request_bytes_total += asset_size
            if asset_size > MAX_ARTIFACT_BYTES:
                errors.append(f"{iid}: DATA-003 input asset exceeds {MAX_ARTIFACT_BYTES} byte limit")
        except ReleaseError as exc:
            errors.append(f"{iid}: {exc}")
    if request_bytes_total > MAX_RELEASE_BYTES:
        errors.append(f"{iid}: combined DATA-003 inputs exceed {MAX_RELEASE_BYTES} byte limit")
    req_items = _map_by(request.get("items", []), "item_id")
    art_items = _map_by(artifact_manifest.get("items", []), "item_id")
    pre_item = req_items.get(row["preprocessing_item_id"])
    art_item = art_items.get(row["preprocessing_item_id"])
    if pre_item is None or art_item is None:
        errors.append(f"{iid}: preprocessing request/artifact item reference is broken")
    elif (pre_item.get("source_id"), pre_item.get("source_object_id")) != (source_id, acquired.get("source_object_id")) and not acquired.get("is_synthetic_fixture"):
        errors.append(f"{iid}: preprocessing provenance identity differs from acquisition/annotation")

    artifact_root = safe_path(base, row["preprocessing_artifact_root"])
    if not artifact_root.is_dir():
        errors.append(f"{iid}: preprocessing_artifact_root must name a directory")
    if art_item:
        rel = art_item.get("output_path", "")
        try:
            artifact_path = safe_path(artifact_root, rel)
            if not artifact_path.is_file():
                errors.append(f"{iid}: preprocessed artifact is missing")
            else:
                size = artifact_path.stat().st_size
                if size > MAX_ARTIFACT_BYTES:
                    errors.append(f"{iid}: artifact exceeds {MAX_ARTIFACT_BYTES} byte limit")
                blob = artifact_path.read_bytes()
                if digest(blob) != art_item.get("output_sha256"):
                    errors.append(f"{iid}: preprocessed output hash mismatch")
        except ReleaseError as exc:
            errors.append(f"{iid}: {exc}")

    page = next((p for p in annotation.get("pages", []) if p.get("page_id") == row["page_id"]), None)
    if page is None:
        errors.append(f"{iid}: page_id does not resolve in DATA-004 annotation")
    if annotation.get("document", {}).get("metadata", {}).get("document_id") not in {None, row["document_id"]}:
        errors.append(f"{iid}: document identity differs from DATA-004 metadata")
    if annotation.get("provenance", {}).get("source_object_id") != acquired.get("source_object_id"):
        errors.append(f"{iid}: annotation source object differs from acquisition")

    mapping_ids = {record.get("identity_id") for record in mappings.get("records", [])}
    for sign in annotation.get("signs", []):
        ref = sign.get("allograph_ref")
        if ref and ref not in mapping_ids:
            errors.append(f"{iid}: DATA-004 allograph reference {ref} is absent from DATA-005")

    alignment_map = _map_by(alignments.get("alignments", []), "alignment_id")
    if not set(row["alignment_ids"]) <= alignment_map.keys():
        errors.append(f"{iid}: DATA-006 alignment ID reference is broken")
    selected_alignments = [alignment_map[x] for x in row["alignment_ids"] if x in alignment_map]
    if any(x.get("page_id") != row["page_id"] for x in selected_alignments):
        errors.append(f"{iid}: selected DATA-006 alignment belongs to another page")
    gold_alignments = [x for x in selected_alignments if eligibility.get(x["alignment_id"], False)]
    if not gold_alignments and release_kind == "corpus_v1_release":
        errors.append(f"{iid}: no expert-reviewed, unambiguous, scoring-eligible gold alignment")

    review_map = _map_by(reviews.get("cases", []), "case_id")
    if not set(row["review_case_ids"]) <= review_map.keys():
        errors.append(f"{iid}: DATA-007 review case reference is broken")
    selected_cases = [review_map[x] for x in row["review_case_ids"] if x in review_map]
    if any(case.get("target_id") not in {t["target_id"] for a in selected_alignments for t in a.get("targets", [])} for case in selected_cases):
        errors.append(f"{iid}: DATA-007 review case target is inconsistent with selected alignment targets")
    if release_kind == "corpus_v1_release" and any(case.get("case_state") not in {"consensus", "adjudicated", "closed"} for case in selected_cases):
        errors.append(f"{iid}: unresolved DATA-007 disagreement is excluded from production gold")
    if release_kind == "corpus_v1_release":
        scored_targets = {target["target_id"] for item in gold_alignments for target in item.get("targets", [])}
        reviewed_targets = {case.get("target_id") for case in selected_cases if case.get("case_state") in {"consensus", "adjudicated", "closed"}}
        if not scored_targets <= reviewed_targets:
            errors.append(f"{iid}: expert-review coverage is insufficient for scoring-eligible gold targets")

    split_rows = _map_by(split_manifest.get("assignments", []), "item_id")
    split_row = split_rows.get(row["split_item_id"])
    metadata_rows = _map_by(split_metadata.get("items", []), "item_id")
    metadata_row = metadata_rows.get(row["split_item_id"])
    if split_row is None or metadata_row is None:
        errors.append(f"{iid}: EVAL-004 split assignment or metadata item is missing")
    else:
        if split_row.get("partition") not in {"train", "dev", "test"}:
            errors.append(f"{iid}: EVAL-004 item is not assigned to train/dev/test")
        if split_row.get("document_id") != row["document_id"] or split_row.get("page_id") != row["page_id"]:
            errors.append(f"{iid}: document/page identity disagrees with EVAL-004")
        if (split_row.get("source_id"), split_row.get("source_object_id")) != (source_id, acquired.get("source_object_id")):
            errors.append(f"{iid}: source identity disagrees with EVAL-004")
        if split_row.get("benchmark_quarantine") or metadata_row.get("benchmark_quarantine"):
            errors.append(f"{iid}: EVAL-004 benchmark-quarantined item cannot be released")
        if release_kind == "corpus_v1_release":
            for field in ("document_id", "page_id", "source_object_id", "image_sha256", "normalized_sha256"):
                if not metadata_row.get(field):
                    errors.append(f"{iid}: production split metadata lacks required leakage identity {field}")
            if metadata_row.get("benchmark_overlap_review", {}).get("status") != "clear":
                errors.append(f"{iid}: production split metadata requires reviewed clear benchmark overlap")
            if acquired.get("redistribution_requested") is not True or source.get("redistribution_use") != "allowed":
                errors.append(f"{iid}: production release lacks independently allowed redistribution rights")
            if source.get(f"{acquired.get('intended_use')}_use") != "allowed" or acquired.get("source_rights_snapshot", {}).get("use_decision") != "allowed":
                errors.append(f"{iid}: production training use is not independently allowed")
            if acquired.get("acquisition_status") != "complete":
                errors.append(f"{iid}: production input is not a completed DATA-002 acquisition")
            for label, permission, evidence in (
                ("annotation training", row["annotation_training_permission"], row["annotation_rights_evidence_ref"]),
                ("annotation redistribution", row["annotation_redistribution_permission"], row["annotation_rights_evidence_ref"]),
                ("mapping training", row["mapping_training_permission"], row["mapping_rights_evidence_ref"]),
                ("mapping redistribution", row["mapping_redistribution_permission"], row["mapping_rights_evidence_ref"]),
            ):
                if permission != "allowed" or evidence.startswith(("synthetic:", "synthetic://")):
                    errors.append(f"{iid}: {label} permission lacks independent allowed status and rights evidence")

    if split_row and art_item:
        if split_row.get("image_sha256") and acquired.get("actual_sha256") and split_row["image_sha256"].lower() != acquired["actual_sha256"].lower():
            errors.append(f"{iid}: EVAL-004 original image hash differs from DATA-002")
        if split_row.get("normalized_sha256") and art_item.get("output_sha256") and split_row["normalized_sha256"].lower() != art_item["output_sha256"].lower():
            errors.append(f"{iid}: EVAL-004 normalized hash differs from DATA-003")

    if acquired.get("is_synthetic_fixture") and release_kind != "synthetic_test_release":
        errors.append(f"{iid}: synthetic fixture cannot be labeled a production corpus_v1_release")
    if not acquired.get("is_synthetic_fixture") and release_kind == "synthetic_test_release":
        errors.append(f"{iid}: synthetic_test_release cannot disguise real source assets")

    target_annotations = []
    for alignment_record in selected_alignments:
        target_rows = []
        for target in alignment_record.get("targets", []):
            data = _target_annotation(annotation, target["target_type"], target["target_id"])
            if data is None:
                errors.append(f"{iid}: unable to export annotation target {target['target_type']}:{target['target_id']}")
            target_rows.append({**target, "annotation": data})
        target_annotations.append({"alignment": copy.deepcopy(alignment_record), "targets": target_rows})
    artifact_hash = art_item.get("output_sha256") if art_item else None
    record = {
        "item_id": iid,
        "document_id": row["document_id"],
        "page_id": row["page_id"],
        "partition": split_row.get("partition") if split_row else None,
        "source_id": source_id,
        "source_object_id": acquired.get("source_object_id"),
        "rights_class": source.get("rights_class"),
        "training_permission": source.get("training_use"),
        "redistribution_permission": source.get("redistribution_use"),
        "intended_use": acquired.get("intended_use"),
        "required_attribution": source.get("attribution_requirements"),
        "source_rights_evidence_urls": source.get("rights_evidence_urls", []),
        "rights_provenance": {"source_registry_record": copy.deepcopy(source), "acquisition_record": copy.deepcopy(acquired)},
        "annotation_training_permission": row["annotation_training_permission"],
        "annotation_redistribution_permission": row["annotation_redistribution_permission"],
        "annotation_rights_evidence_ref": row["annotation_rights_evidence_ref"],
        "mapping_training_permission": row["mapping_training_permission"],
        "mapping_redistribution_permission": row["mapping_redistribution_permission"],
        "mapping_rights_evidence_ref": row["mapping_rights_evidence_ref"],
        "original_sha256": acquired.get("actual_sha256"),
        "preprocessed_sha256": artifact_hash,
        "preprocessed_artifact_ref": {"artifact_manifest": row["preprocessing_artifact_manifest_path"],
                                      "dataset_version_id": artifact_manifest.get("dataset_version_id"),
                                      "path": art_item.get("output_path") if art_item else None,
                                      "sha256": artifact_hash},
        "annotation_id": annotation.get("annotation_id"),
        "annotation_provenance": {"provenance": copy.deepcopy(annotation.get("provenance")), "document": copy.deepcopy(annotation.get("document"))},
        "mapping_set_id": mappings.get("mapping_set_id"),
        "mapping_records": copy.deepcopy(mappings.get("records", [])),
        "mapping_relations": copy.deepcopy(mappings.get("relations", [])),
        "alignment_set_id": alignments.get("alignment_set_id"),
        "review_set_id": reviews.get("review_set_id"),
        "gold_alignment_ids": sorted(x["alignment_id"] for x in gold_alignments),
        "target_annotations": target_annotations,
        "review_case_ids": sorted(row["review_case_ids"]),
        "review_cases": copy.deepcopy(selected_cases),
        "split_assignment": copy.deepcopy(split_row),
        "gold_statuses": sorted({
            target.get("gold_status", "unknown")
            for target in annotation.get("lines", []) if target.get("line_id") in {t.get("target_id") for a in selected_alignments for t in a.get("targets", [])}
        }),
        "review_disagreement_count": sum(bool(case.get("disagreement")) for case in review_report.get("cases", [])) if isinstance(review_report, dict) else 0,
        "synthetic": bool(acquired.get("is_synthetic_fixture")),
    }
    return record, errors


def validate_bundle(bundle: Any, bundle_path: Path) -> tuple[dict[str, Any], list[str]]:
    errors = _schema_errors(bundle, SCHEMA, "bundle")
    if errors:
        return {}, errors
    base = bundle_path.resolve(strict=True).parent
    registry = source_registry.load_yaml(REGISTRY)
    registry_errors = source_registry.validate_registry_data(registry, read_document(ROOT / "schemas/data_sources.schema.json"))
    errors.extend(f"DATA-001 registry: {e}" for e in registry_errors)
    audit: list[dict[str, str]] = []
    try:
        metadata, _ = _read_checked(base, bundle["split_metadata_path"], audit)
        split_manifest, _ = _read_checked(base, bundle["split_manifest_path"], audit)
    except ReleaseError as exc:
        return {}, [str(exc)]
    profiles = read_document(SPLIT_PROFILES)
    errors.extend(f"EVAL-004 metadata: {e}" for e in split_system._validate_metadata(metadata, registry, profiles))
    errors.extend(f"EVAL-004 split: {e}" for e in split_system.validate_manifest(split_manifest, metadata, profiles, read_document(SPLIT_SCHEMA), registry))
    seen: set[str] = set()
    records = []
    for row in bundle["items"]:
        if row["item_id"] in seen:
            errors.append(f"duplicate release item_id: {row['item_id']}")
        seen.add(row["item_id"])
        record, row_errors = _validate_source(bundle, row, base, registry, metadata, split_manifest, profiles, audit, bundle["release_kind"])
        if record:
            records.append(record)
        errors.extend(row_errors)

    included_ids = {record["item_id"] for record in records}
    split_map = _map_by(split_manifest.get("assignments", []), "item_id")
    for partition in ("train", "dev", "test"):
        split_ids = {iid for iid, row in split_map.items() if row.get("partition") == partition}
        if not split_ids <= included_ids:
            errors.append(f"release omits EVAL-004 {partition} assignments: {', '.join(sorted(split_ids - included_ids))}")
        if bundle["release_kind"] == "corpus_v1_release" and not any(row.get("partition") == partition for row in records):
            errors.append(f"production release has an empty {partition} partition")
    if bundle["release_kind"] == "corpus_v1_release" and any(record.get("synthetic") for record in records):
        errors.append("synthetic input cannot be represented as a real corpus_v1_release")
    if bundle["release_kind"] == "corpus_v1_release" and not records:
        errors.append("production corpus has no independently rights-cleared items")

    # Leakage checks are repeated at release time, including reviewed near duplicates.
    active = [r for r in records if r.get("partition") in {"train", "dev", "test"}]
    for field in ("source_object_id", "document_id", "page_id", "original_sha256", "preprocessed_sha256"):
        places: dict[str, set[str]] = {}
        for record in active:
            value = record.get(field)
            if value:
                places.setdefault(str(value).lower(), set()).add(record["partition"])
        for value, partitions in places.items():
            if len(partitions) > 1:
                errors.append(f"release leakage: {field} {value} crosses partitions {sorted(partitions)}")
    queue = split_manifest.get("near_duplicate_review_queue", [])
    for pair in queue:
        if pair.get("review_status") == "pending":
            errors.append(f"release blocked by unresolved near-duplicate review: {pair.get('left_item_id')} / {pair.get('right_item_id')}")
        if pair.get("review_status") == "same_content":
            left, right = split_map.get(pair.get("left_item_id"), {}), split_map.get(pair.get("right_item_id"), {})
            if left.get("partition") != right.get("partition"):
                errors.append("release leakage: reviewed near-duplicate pair crosses partitions")

    unique_inputs = sorted({x["path"]: x for x in audit}.values(), key=lambda x: x["path"])
    if sum(item["size_bytes"] for item in unique_inputs) > MAX_RELEASE_BYTES:
        errors.append(f"combined unique release inputs exceed {MAX_RELEASE_BYTES} byte limit")
    excluded_items = sorted(({"item_id": row["item_id"], "reason": row.get("exclusion_reason")} for row in split_manifest.get("assignments", []) if row.get("partition") == "excluded"), key=lambda x: x["item_id"])
    identity = {"release_id": bundle["release_id"], "release_kind": bundle["release_kind"], "generator": GENERATOR,
                "inputs": unique_inputs, "items": sorted(records, key=lambda x: x["item_id"]), "excluded_items": excluded_items,
                "split_statistics": copy.deepcopy(split_manifest.get("statistics", {})), "split_warnings": sorted(split_manifest.get("warnings", [])),
                "split_version": split_manifest.get("split_version"), "split_profile_id": split_manifest.get("profile_id")}
    release = {"schema_version": "1.0.0", **identity,
               "dataset_version_id": "corpus-" + digest(canonical(identity)),
               "partition_counts": {p: sum(r.get("partition") == p for r in records) for p in ("train", "dev", "test")}
               | {"excluded": len(excluded_items)}}
    output_schema = read_document(SCHEMA)["$defs"]["releaseManifest"]
    output_errors = sorted(Draft202012Validator(output_schema, format_checker=FormatChecker()).iter_errors(release), key=lambda e: str(e.absolute_path))
    errors.extend(f"release{''.join(f'[{part!r}]' for part in err.absolute_path)}: {err.message}" for err in output_errors)
    errors = sorted(set(errors))
    if errors:
        return {}, errors
    return {"release": release, "errors": [], "audit": unique_inputs}, []


def _dataset_card(release: dict[str, Any]) -> str:
    synthetic = release["release_kind"] == "synthetic_test_release"
    return "\n".join([
        "# Hieratic AI corpus release card", "", f"- Release ID: `{release['release_id']}`",
        f"- Dataset version: `{release['dataset_version_id']}`", f"- Release kind: `{release['release_kind']}`",
        f"- Items indexed: {len(release['items'])}", f"- Partitions: train {release['partition_counts']['train']}, dev {release['partition_counts']['dev']}, test {release['partition_counts']['test']}, excluded {release['partition_counts']['excluded']}",
        f"- Data status: {'synthetic structural fixture only; not a licensed production corpus' if synthetic else 'production release; each item has passed release-time rights and leakage checks'}",
        "- Included source bytes: none; artifacts are referenced by immutable hash and remain in their DATA-003 artifact store.",
        "- Gold: only reviewed, unambiguous DATA-006 alignments are included in the gold ID index; missing, uncertain, disputed, damaged, restored, or unreviewed readings remain metadata and are not coerced.",
        "- Rights: item-level evidence, permissions, and required attribution are preserved in the release manifest; this card does not grant permission.",
        "- Exclusions: evaluation-only, quarantined, unknown-rights, unresolved-overlap, and unresolved near-duplicate items are refused.",
        "- Limitations: no model training or performance claim is made by corpus assembly.", ""
    ])


def _write_staging_file(staging: Path, staging_fd: int | None, name: str, content: bytes) -> None:
    """Write one exclusive staging file, refusing symlink or pre-existing entries."""
    if staging_fd is None:
        # Windows has no dir_fd support in Python's os.open. The staging name is
        # private and newly-created; os.rename below supplies the no-clobber commit.
        with (staging / name).open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        return
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(name, flags, 0o600, dir_fd=staging_fd)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _open_linux_directory_without_symlinks(path: Path) -> int:
    """Open each absolute path component without following symlinks (Linux)."""
    absolute = Path(os.path.abspath(path))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    current_fd = os.open(absolute.anchor, flags)
    try:
        for component in absolute.parts[1:]:
            try:
                next_fd = os.open(component, flags, dir_fd=current_fd)
            except OSError as exc:
                try:
                    mode = os.stat(component, dir_fd=current_fd, follow_symlinks=False).st_mode
                except OSError:
                    raise exc
                if stat.S_ISLNK(mode):
                    raise ReleaseError("release output cannot traverse a symlink") from exc
                raise
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def _rename_linux_noreplace(parent_fd: int, staging_name: str, output_name: str) -> None:
    """Atomically rename a complete directory only if the name is still absent."""
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise ReleaseError("Linux renameat2(RENAME_NOREPLACE) is required for safe release publication")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    # Linux UAPI: include/uapi/linux/fs.h
    rename_noreplace = 1
    result = renameat2(parent_fd, os.fsencode(staging_name), parent_fd, os.fsencode(output_name), rename_noreplace)
    if result == 0:
        return
    error = ctypes.get_errno()
    if error in (errno.EEXIST, errno.ENOTEMPTY):
        raise ReleaseError("release destination already exists; immutable releases are never replaced")
    if error in (errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP):
        raise ReleaseError("filesystem does not support atomic no-replace directory publication")
    raise OSError(error, os.strerror(error), output_name)


def _verify_linux_parent_path(path: Path, parent_fd: int) -> None:
    """Fail if the caller's parent path was replaced after its fd was pinned."""
    opened = os.fstat(parent_fd)
    try:
        named = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise ReleaseError("release output parent path changed during publication") from exc
    if not stat.S_ISDIR(named.st_mode) or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
        raise ReleaseError("release output parent path changed during publication")


def _remove_published_linux_directory(parent_fd: int, name: str, published_fd: int) -> None:
    """Remove only our just-published inode, never a replacement at its name."""
    try:
        entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        inode = os.fstat(published_fd)
        if not stat.S_ISDIR(entry.st_mode) or (entry.st_dev, entry.st_ino) != (inode.st_dev, inode.st_ino):
            return
        for child in os.listdir(published_fd):
            os.unlink(child, dir_fd=published_fd)
        os.rmdir(name, dir_fd=parent_fd)
    except OSError:
        # A concurrent replacement is not ours to remove.
        return


def _publish_linux(files: dict[str, bytes], output: Path) -> None:
    """Stage through a pinned parent fd, then atomically publish without clobbering."""
    output_name = output.name
    if output_name in ("", ".", "..") or os.sep in output_name:
        raise ReleaseError("release output must name a new directory")
    parent_fd = _open_linux_directory_without_symlinks(output.parent)
    staging_name = f".{output_name}.staging-{secrets.token_hex(12)}"
    staging_fd: int | None = None
    staging_exists = False
    try:
        os.mkdir(staging_name, mode=0o700, dir_fd=parent_fd)
        staging_exists = True
        staging_fd = os.open(staging_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
        staging_path = output.parent / staging_name
        for name, content in files.items():
            _write_staging_file(staging_path, staging_fd, name, content)
        os.fsync(staging_fd)
        _verify_linux_parent_path(output.parent, parent_fd)
        # This is the single commit point. It is atomic, rejects every existing
        # entry (including an empty directory or symlink), and exposes only a
        # complete five-file release.
        _rename_linux_noreplace(parent_fd, staging_name, output_name)
        staging_exists = False
        try:
            _verify_linux_parent_path(output.parent, parent_fd)
        except ReleaseError:
            _remove_published_linux_directory(parent_fd, output_name, staging_fd)
            raise
        os.fsync(parent_fd)
    finally:
        if staging_fd is not None:
            if staging_exists:
                for name in os.listdir(staging_fd):
                    try:
                        os.unlink(name, dir_fd=staging_fd)
                    except OSError:
                        pass
            os.close(staging_fd)
        if staging_exists:
            try:
                os.rmdir(staging_name, dir_fd=parent_fd)
            except OSError:
                # Never follow or recursively remove a path that may have been
                # swapped by another process. A leftover private staging dir is
                # safer than touching an untrusted destination.
                pass
        os.close(parent_fd)


def _publish_windows(files: dict[str, bytes], output: Path) -> None:
    """Windows rename fails if the destination exists; stage beside the target."""
    parent = output.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ReleaseError("release output parent must already exist")
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=parent))
    try:
        for name, content in files.items():
            _write_staging_file(staging, None, name, content)
        # Unlike POSIX rename, Windows MoveFile semantics do not replace an
        # existing destination. This remains a no-clobber atomic directory move.
        os.rename(staging, parent / output.name)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def publish(result: dict[str, Any], output: Path, bundle_path: Path) -> None:
    if result["errors"]:
        raise ReleaseError("release validation failed:\n" + "\n".join(result["errors"]))
    output = Path(os.path.abspath(output))
    if output.name in ("", ".", ".."):
        raise ReleaseError("release output must name a new directory")
    if not output.parent.exists() or not output.parent.is_dir():
        raise ReleaseError("release output parent must already exist")
    if sys.platform.startswith("linux"):
        # A preflight check gives a fast, clear error; renameat2 is the actual
        # no-clobber guarantee and closes the check/commit race.
        if output.exists() or output.is_symlink():
            raise ReleaseError("release destination already exists; immutable releases are never replaced")
    elif os.name == "nt":
        probe = output.parent
        while probe != probe.parent:
            if probe.is_symlink():
                raise ReleaseError("release output cannot traverse a symlink")
            probe = probe.parent
        if output.exists() or output.is_symlink():
            raise ReleaseError("release destination already exists; immutable releases are never replaced")
    else:
        raise ReleaseError("safe no-clobber directory publication is unsupported on this platform")
    total = 0
    encoded_records = []
    for record in result["release"]["items"]:
        encoded_records.append(canonical(record) + b"\n")
    files = {
        "release-manifest.json": json.dumps(result["release"], ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n",
        "export.jsonl": b"".join(encoded_records),
        "dataset-card.md": _dataset_card(result["release"]).encode("utf-8"),
        "rejection-report.json": json.dumps({"excluded_split_items": result["release"]["excluded_items"], "reason": "excluded items retain EVAL-004 exclusion reasons and are absent from train/dev/test exports"}, sort_keys=True, indent=2).encode("utf-8") + b"\n",
        "audit-trail.json": json.dumps({"generator": GENERATOR, "bundle_sha256": digest(bundle_path.read_bytes()), "inputs": result["audit"], "release_sha256": digest(canonical(result["release"]))}, sort_keys=True, indent=2).encode("utf-8") + b"\n",
    }
    for content in files.values():
        total += len(content)
    if total > MAX_RELEASE_BYTES:
        raise ReleaseError(f"release output exceeds {MAX_RELEASE_BYTES} byte limit")
    if sys.platform.startswith("linux"):
        _publish_linux(files, output)
    else:
        _publish_windows(files, output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate"); check.add_argument("bundle", type=Path)
    run = sub.add_parser("build"); run.add_argument("bundle", type=Path); run.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        bundle_path = args.bundle.resolve(strict=True)
        bundle = read_document(bundle_path)
        result, errors = validate_bundle(bundle, bundle_path)
        if errors:
            raise ReleaseError("\n".join(errors))
        release = result["release"]
        if args.command == "validate":
            print(f"PASS: {release['release_kind']} {release['dataset_version_id']} ({len(release['items'])} items); no files written")
        else:
            publish(result, args.output, bundle_path)
            print(f"PASS: published {release['dataset_version_id']} to {args.output}")
        return 0
    except (ReleaseError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
