"""Combine the W20 source audits into a fail-closed DATA-008 receipt manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "data/releases/w20_source_evidence.schema.json"
MAX_INPUT_BYTES = 64 * 1024 * 1024


class ManifestError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def read_receipt(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ManifestError("receipt input must be a regular non-symlink file")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ManifestError("receipt input exceeds 64 MiB")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"invalid receipt input: {type(exc).__name__}") from exc
    if not isinstance(obj, dict):
        raise ManifestError("receipt input root must be an object")
    return obj


def validate_input(receipt: dict[str, Any]) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise ManifestError("jsonschema is required to validate W20 receipts") from exc
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = [error.message for error in Draft202012Validator(schema).iter_errors(receipt)]
    return errors


def content_digest(receipt: dict[str, Any]) -> str | None:
    value = receipt.get("evidence_sha256")
    material = {key: item for key, item in receipt.items() if key not in {"retrieved_at_utc", "evidence_sha256"}}
    expected = hashlib.sha256(canonical(material)).hexdigest()
    return expected if value == expected else None


def build_manifest(census: dict[str, Any], photos: dict[str, Any], independent_receipt: dict[str, Any] | None = None,
                   w19_receipt: dict[str, Any] | None = None, w19_raw_sha256: str | None = None) -> dict[str, Any]:
    for receipt in (census, photos):
        errors = validate_input(receipt)
        if errors:
            raise ManifestError("input schema rejection: " + "; ".join(errors[:6]))
        if content_digest(receipt) is None:
            raise ManifestError("input receipt evidence digest mismatch")
    sign_rows = census["items"]
    photo_rows = photos["items"]
    r026_digest = None
    cat1880_p01_match = False
    if independent_receipt is not None:
        if independent_receipt.get("schema_version") != "r026-exact-public-originals/1.0.0":
            raise ManifestError("unexpected independent R-026 source receipt version")
        expected = next((row for row in independent_receipt.get("verified_originals", []) if row.get("source") == "MuseoEgizio:Cat.1880" and row.get("item") == "new p01"), None)
        p01 = next((row for row in photo_rows if row.get("candidate_id") == "TURIN-CAT1880-P01"), None)
        if not expected or not p01 or expected.get("sha256") != p01.get("original_sha256") or expected.get("bytes") != p01.get("byte_count"):
            raise ManifestError("W20 Cat.1880 p01 bytes do not match accepted R-026 receipt")
        r026_digest = digest(independent_receipt)
        cat1880_p01_match = True
    if w19_receipt is not None and w19_raw_sha256 != census.get("benchmark_screen", {}).get("w19_receipt_sha256"):
        raise ManifestError("W19 media receipt hash differs from source audit's pinned registry")
    sign_ids = [row.get("sign_id") for row in sign_rows]
    if len(set(sign_ids)) != len(sign_ids):
        raise ManifestError("duplicate AKU-PAL sign identity in receipt")
    if census["summary"]["distinct_sign_ids_screened"] != len(sign_rows):
        raise ManifestError("AKU-PAL source count does not match item receipt")
    items: list[dict[str, Any]] = []
    for row in sign_rows:
        items.append({
            "candidate_id": f"AKU-PAL-HT-{row['sign_id']}", "cohort": "licensed_publisher_sign_record",
            "source_identity": {"stable_sign_id": row["sign_id"], "record_url": row["record_url"], "record_sha256": row["record_sha256"],
                "source_text_record_id": row.get("source_text_record_id"), "source_inventory_label": row.get("source_inventory_label"),
                "side": row.get("side"), "line_locator": row.get("line_locator"), "script_type": row.get("script_type")},
            "rights_evidence": {"license_id": row.get("license_id"), "license_url": row.get("license_url"), "status": row.get("rights_status"),
                "independent_rights_determination": False},
            "media": [{key: media.get(key) for key in ("url", "asset_role", "publisher_image_type", "status", "sha256", "byte_size", "content_type", "dimensions", "safe_svg")}
                      for media in row.get("media", [])],
            "benchmark_screen": row.get("benchmark_screen", {"state": "NOT_SCREENED", "matches": []}),
            "disposition": {"benchmark_overlap": "unknown_quarantined", "training_admission": False, "gold_admission": False,
                "production_admission": False, "expert_review": "none"},
        })
    for row in photo_rows:
        metadata = row.get("metadata", {})
        items.append({
            "candidate_id": row["candidate_id"], "cohort": "cc0_museum_manuscript_photo",
            "source_identity": {"accession": row["accession"], "physical_support_group": row["group_id"], "commons_title": metadata.get("commons_title"),
                "file_page_revision_id": metadata.get("page_revision_id"), "file_revision_timestamp": metadata.get("file_revision_timestamp"),
                "publisher_sha1": metadata.get("file_sha1_publisher_claim"), "original_sha256": row.get("original_sha256"),
                "byte_count": row.get("byte_count"), "dimensions": row.get("actual_dimensions"), "decode_status": row.get("decode_status"),
                "object_reference": row.get("object_url"), "identity_evidence": row.get("identity_evidence")},
            "rights_evidence": {"image_license": metadata.get("license_short_name"), "license_url": metadata.get("license_url"),
                "license_metadata_source": metadata.get("license_metadata_source"), "image_file_page_status": row.get("rights_status"),
                "text_rights": row.get("text_rights"), "independent_rights_determination": False},
            "media": [{"sha256": row.get("original_sha256"), "status": row.get("bytes_status"), "byte_size": row.get("byte_count"),
                "mime": metadata.get("mime"), "dimensions": row.get("actual_dimensions"), "publisher_sha1_verified": row.get("publisher_sha1_verified")}],
            "benchmark_screen": row.get("benchmark_screen", {"result": "UNKNOWN", "disposition": "QUARANTINED", "matches": []}),
            "disposition": {"benchmark_overlap": "unknown_quarantined", "training_admission": False, "gold_admission": False,
                "production_admission": False, "data002_acquisition": False, "intended_role": row.get("intended_role")},
        })
    media_hashes = [entry["sha256"] for item in items for entry in item["media"] if isinstance(entry.get("sha256"), str)]
    w19_hash_count = 0
    if w19_receipt is not None:
        for item in w19_receipt.get("items", []):
            for media in item.get("publisher_media", []):
                if isinstance(media.get("image_sha256"), str) and re.fullmatch(r"[a-f0-9]{64}", media["image_sha256"]):
                    media_hashes.append(media["image_sha256"])
                    w19_hash_count += 1
    hash_counts: dict[str, int] = {}
    for sha in media_hashes:
        hash_counts[sha] = hash_counts.get(sha, 0) + 1
    sign_supports = {row.get("source_inventory_label") for row in sign_rows if row.get("source_inventory_label")}
    accepted_sign_supports = {row.get("source_inventory_label") for row in sign_rows if row.get("source_inventory_label") and row.get("rights_status") == "per_item_license_and_public_provenance_screened_not_institutionally_admitted"}
    benchmark_states: dict[str, int] = {}
    for item in items:
        state = item["benchmark_screen"].get("state") or item["benchmark_screen"].get("result") or "UNKNOWN"
        benchmark_states[state] = benchmark_states.get(state, 0) + 1
    manifest = {
        "schema_version": "w20-data008-receipt-manifest/1.0.0", "classification": "SOURCE_EVIDENCE_ONLY_NO_DATASET_ADMISSION",
        "source_receipts": {"akupal_evidence_sha256": census["evidence_sha256"], "museum_photo_evidence_sha256": photos["evidence_sha256"],
            "r017_public_metadata_sha256": census["benchmark_screen"]["public_r017_sha256"], "w19_source_receipt_sha256": census["benchmark_screen"]["w19_receipt_sha256"],
            **({"r026_accepted_source_receipt_sha256": r026_digest} if r026_digest else {})},
        "summary": {"akupal_sign_ids_screened": len(sign_rows), "sign_records_with_exact_item_license_identity_and_verified_media": census["summary"]["exact_item_permissive_license_and_provenance_screened"],
            "sign_original_media_files_verified": census["summary"]["verified_sign_media_files"], "sign_unique_media_sha256": census["summary"]["unique_media_byte_hashes"],
            "sign_duplicate_media_hash_groups": census["summary"]["duplicate_media_hash_groups"], "source_inventory_labels_all_sign_records_lower_bound": len(sign_supports),
            "source_inventory_labels_screened_sign_records_lower_bound": len(accepted_sign_supports),
            "museum_photo_files_screened": len(photo_rows), "museum_original_photo_files_sha256_verified": photos["bytes_hashed"],
            "museum_physical_support_groups": photos["distinct_physical_support_groups"], "unique_media_sha256_across_receipts": len(hash_counts),
            "duplicate_sha256_groups_across_receipts": sum(count > 1 for count in hash_counts.values()),
            "w19_media_hashes_in_dedup_screen": w19_hash_count,
            "cat1880_p01_r026_byte_crossmatch": cat1880_p01_match,
            "benchmark_screen_results": benchmark_states, "gold_labels": 0, "training_admissions": 0, "production_admissions": 0,
            "sealed_benchmark_records_read": 0, "raw_media_files_committed": 0},
        "items": items,
        "blocked_release_assessment": {"production_authorization": "HARD_DISABLED_PENDING_INDEPENDENT_TRUST_ROOT_AND_AUTHORITY_ONBOARDING",
            "real_corpus_v1_release": False, "unresolved_benchmark_overlap": True, "rights_for_scholarly_editions": "NOT_VERIFIED",
            "expert_reviewed_gold": False, "leakage_safe_train_dev_test": False, "capability_points_claimed": 0},
    }
    manifest["evidence_sha256"] = digest(manifest)
    errors = validate_input(manifest)
    if errors:
        raise ManifestError("combined manifest schema rejection: " + "; ".join(errors[:6]))
    return manifest


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors = []
    if manifest.get("schema_version") != "w20-data008-receipt-manifest/1.0.0":
        errors.append("wrong manifest version")
    items = manifest.get("items", [])
    if len({item.get("candidate_id") for item in items}) != len(items):
        errors.append("candidate IDs are not unique")
    if manifest.get("blocked_release_assessment", {}).get("production_authorization") != "HARD_DISABLED_PENDING_INDEPENDENT_TRUST_ROOT_AND_AUTHORITY_ONBOARDING":
        errors.append("production hard-disable was changed")
    for item in items:
        disposition = item.get("disposition", {})
        if any(disposition.get(key) is not False for key in ("training_admission", "gold_admission", "production_admission")):
            errors.append(f"{item.get('candidate_id')}: promotion flag must remain false")
        if disposition.get("benchmark_overlap") != "unknown_quarantined":
            errors.append(f"{item.get('candidate_id')}: benchmark state must remain quarantined")
    material = {key: value for key, value in manifest.items() if key != "evidence_sha256"}
    if manifest.get("evidence_sha256") != digest(material):
        errors.append("manifest evidence digest mismatch")
    return errors


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.parent.is_symlink():
        raise ManifestError("manifest output or parent must not be a symlink")
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--census", type=Path, default=ROOT / "data/releases/w20_aku_pal_sign_census.json")
    parser.add_argument("--photos", type=Path, default=ROOT / "data/releases/w20_museum_photo_intake.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/releases/w20_item_receipt_manifest.json")
    args = parser.parse_args(argv)
    r026_path = ROOT / "docs/research/R026_ORIGINAL_SOURCE_BYTE_RECEIPTS.json"
    r026 = read_receipt(r026_path) if r026_path.is_file() else None
    w19_path = ROOT / "data/releases/w19_aku_pal_original_image_receipts.json"
    from data.releases.w20_aku_pal_source_audit import repository_evidence_bytes
    w19_raw = repository_evidence_bytes(w19_path, root=ROOT)
    w19 = read_receipt(w19_path)
    manifest = build_manifest(read_receipt(args.census), read_receipt(args.photos), r026, w19, hashlib.sha256(w19_raw).hexdigest())
    errors = validate_manifest(manifest)
    if errors:
        raise ManifestError("manifest validation failed: " + "; ".join(errors))
    write_json_atomic(args.output, manifest)
    print(json.dumps(manifest["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
