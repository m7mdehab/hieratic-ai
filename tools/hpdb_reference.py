"""Offline HPDB sign-index importer, preserving source and rights boundaries.

Only parses locally supplied CC BY 4.0 *metadata*. The University of Tokyo
IIIF page images are separately hosted and NEVER downloaded by this module.
No input can authorize benchmark independence or scientific training.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlsplit

INDEX_URL = "https://moeller.jinsha.tsukuba.ac.jp/data/index.json"
LICENSE_URL = "https://moeller.jinsha.tsukuba.ac.jp/en/datasets/"
IMAGE_HOST = "iiif.dl.itc.u-tokyo.ac.jp"
IMAGE_PATH_PREFIX = "/iiif/asia/hp/"
EXPECTED_COMPLETE_ROWS = 2065
MAX_JSON_BYTES = 10 * 1024 * 1024
MAX_ROWS = 3000
GARDINER_TOKEN = re.compile(r"^[A-Za-z]{1,2}\d{1,3}[a-zA-Z]?$")


class HPDBReferenceError(ValueError):
    """Reject incomplete or forged reference-only metadata."""


def _one_string(item: dict[str, Any], field: str) -> str:
    value = item.get(field)
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], str):
        raise HPDBReferenceError(f"{field}: expected exactly one text value")
    text = value[0].strip()
    if not text or len(text) > 256:
        raise HPDBReferenceError(f"{field}: empty/oversized source field")
    return text


def _safe_image_reference(url: Any) -> bool:
    """Check shape of an untrusted IIIF reference; do not fetch any bytes."""
    if not isinstance(url, str) or len(url) > 1024:
        return False
    try:
        parts = urlsplit(url)
        safe_port = parts.port in (None, 443)
    except ValueError:
        return False
    if (parts.scheme != "https" or parts.hostname != IMAGE_HOST or not safe_port
            or parts.username or parts.password or parts.query or parts.fragment
            or not parts.path.startswith(IMAGE_PATH_PREFIX)):
        return False
    path = parts.path[len(IMAGE_PATH_PREFIX):]
    # This is a IIIF image URI, never an authorization to download it.
    return "/default." in path and ".tif/" in path and ".." not in path and "\x00" not in path


def normalize_item(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise HPDBReferenceError("HPDB item must be a mapping")
    item_id = item.get("_id")
    if not isinstance(item_id, str) or not re.fullmatch(r"\d{6}", item_id):
        raise HPDBReferenceError("Invalid HPDB six-digit item ID")
    volume = _one_string(item, "Vol")
    page = _one_string(item, "Page")
    if volume not in {"1", "2", "3"} or not page.isdigit() or not 1 <= int(page) <= 250:
        raise HPDBReferenceError("Missing/invalid palaeographic volume or page")
    source_image = item.get("_image")
    if not _safe_image_reference(source_image):
        raise HPDBReferenceError("IIIF image reference is not on exact source host/path")
    persistent_uri = item.get("_url")
    if persistent_uri != f"https://w3id.org/hpdb/item/{item_id}":
        raise HPDBReferenceError("HPDB persistent ID mismatch")
    group = _one_string(item, "Item Type")
    if group not in {"Main", "Number", "Ligature"}:
        raise HPDBReferenceError("Unknown palaeographic item type")
    gardiner = _one_string(item, "Hieroglyph No")
    # Gardiner combinations and uncertainty are preserved as source notation,
    # but only unambiguous single-token signs are machine-labelled.
    canonical = gardiner if GARDINER_TOKEN.fullmatch(gardiner) and "?" not in gardiner else None
    ref = {
        "item_id": item_id,
        "source_item_url": persistent_uri,
        "volume": int(volume),
        "page": int(page),
        "source_page_group": f"MOLLER-V{volume}-P{int(page):03d}",
        "item_type": group,
        "hieratic_no_as_printed": _one_string(item, "Hieratic No"),
        "hieroglyph_no_as_printed": gardiner,
        "unambiguous_single_gardiner_label": canonical,
        "facsimile_iiif_reference": source_image,
        "source_type": "printed_hieratic_palaeography_facsimile_not_original_manuscript",
        "metadata_license": "CC-BY-4.0",
        "underlying_scan_image_license": "not_independently_verified",
        "original_manuscript_source_identity": None,
        "expert_gold_status": "not_attested_for_this_image",
        "training_admission": "BLOCKED_REFERENCE_METADATA_ONLY",
        "scientific_evaluation_admission": "BLOCKED_REFERENCE_METADATA_ONLY",
    }
    return ref


def assemble_index(items: Any, *, require_complete: bool = True) -> dict[str, Any]:
    if not isinstance(items, list) or len(items) > MAX_ROWS:
        raise HPDBReferenceError("HPDB index must be a bounded array")
    if require_complete and len(items) != EXPECTED_COMPLETE_ROWS:
        raise HPDBReferenceError(f"Expected {EXPECTED_COMPLETE_ROWS} published metadata rows, got {len(items)}")
    seen: set[str] = set()
    records = []
    for ix, item in enumerate(items):
        try:
            normalized = normalize_item(item)
        except HPDBReferenceError as exc:
            raise HPDBReferenceError(f"HPDB item {ix}: {exc}") from exc
        if normalized["item_id"] in seen:
            raise HPDBReferenceError(f"Duplicate HPDB item ID {normalized['item_id']}")
        seen.add(normalized["item_id"])
        records.append(normalized)
    groups = Counter(x["source_page_group"] for x in records)
    labels = Counter("known_single_sign" if x["unambiguous_single_gardiner_label"] else "ambiguous_or_compound" for x in records)
    volumes = Counter(str(x["volume"]) for x in records)
    return {
        "schema_version": "1.0.0",
        "classification": "cc_by_reference_metadata_only_no_original_images",
        "public_index_url": INDEX_URL,
        "license_evidence_url": LICENSE_URL,
        "declared_source_rows": len(records),
        "source_page_groups": len(groups),
        "volume_counts": dict(sorted(volumes.items())),
        "label_counts": dict(sorted(labels.items())),
        "original_image_bytes_obtained": False,
        "rights_cleared_original_manuscripts": 0,
        "scientific_results": 0,
        "source_identity_cleared": False,
        "source_rows": records,
    }


def read_local_index(path: Path, *, require_complete: bool = True) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
        raise HPDBReferenceError("Source JSON missing or over byte cap")
    raw = path.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HPDBReferenceError("Invalid UTF-8 JSON index") from exc
    result = assemble_index(parsed, require_complete=require_complete)
    result["locally_supplied_bytes_sha256"] = hashlib.sha256(raw).hexdigest()
    result["source_file_trust"] = "local_unattested_bytes_not_publisher_signed"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True, help="Locally supplied publisher index.json")
    parser.add_argument("--output", type=Path, help="Create a new metadata-only JSON summary; never overwrite")
    parser.add_argument("--fixture-small", action="store_true", help="Allow small synthetic test indices only")
    args = parser.parse_args(argv)
    try:
        data = read_local_index(args.index, require_complete=not args.fixture_small)
        if args.output:
            # Non-sensitive metadata only. Refuse existing files; callers should
            # choose an existing private working directory without symlinks.
            if args.output.is_symlink() or args.output.exists():
                raise HPDBReferenceError("Refusing to overwrite existing output")
            with args.output.open("x", encoding="utf-8") as fd:
                json.dump(data, fd, ensure_ascii=False, sort_keys=True, indent=2)
                fd.write("\n")
        print(json.dumps({k: v for k, v in data.items() if k != "source_rows"}, indent=2))
        return 0
    except (HPDBReferenceError, OSError) as exc:
        print(f"HPDB REFERENCE IMPORT REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
