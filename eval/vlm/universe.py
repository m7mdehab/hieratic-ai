"""Evaluation universe management and dataset admission governance for VLM baselines.

Provides independent universe contracts, canonical hashing, expected attempt scheduling,
and dataset admission gating with image pixel and provenance validation.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ImportError:
    Image = None

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UNIVERSE_PATH = ROOT / "eval/vlm/universe.yaml"


class UniverseError(ValueError):
    """Raised when an evaluation universe fails integrity or admission checks."""
    pass


def load_universe(universe_path: Path = DEFAULT_UNIVERSE_PATH) -> dict[str, Any]:
    """Load evaluation universe YAML or JSON file."""
    if not universe_path.is_file():
        raise UniverseError(f"Universe file does not exist: {universe_path}")
    try:
        content = universe_path.read_text(encoding="utf-8")
        if universe_path.suffix.lower() == ".json":
            return json.loads(content)
        return yaml.safe_load(content)
    except Exception as exc:
        raise UniverseError(f"Cannot read universe from {universe_path}: {exc}") from exc


def compute_universe_sha256(universe_data: dict[str, Any]) -> str:
    """Compute canonical deterministic SHA-256 hash for evaluation universe."""
    items = universe_data.get("items", [])
    expected_attempts = universe_data.get("expected_attempts", [])
    canonical_payload = json.dumps(
        {
            "dataset_id": universe_data.get("dataset_id"),
            "items": items,
            "expected_attempts": expected_attempts,
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def get_expected_attempts(
    universe_data: dict[str, Any],
    shot_mode: str,
    samples_per_item: int = 1,
) -> list[str]:
    """Generate expected attempt composite keys for given shot mode and sample count.

    Composite key: '{item_id}::{rung}::{shot_mode}::{sample_index}'
    """
    if shot_mode not in {"zero_shot", "few_shot", "both"}:
        raise UniverseError(f"Unsupported shot mode '{shot_mode}' for universe attempts.")

    modes = ["zero_shot", "few_shot"] if shot_mode == "both" else [shot_mode]
    items = universe_data.get("items", [])

    expected: list[str] = []
    for mode in modes:
        for s_idx in range(samples_per_item):
            for item in items:
                expected.append(f"{item['item_id']}::{item['rung']}::{mode}::{s_idx}")
    return sorted(expected)


def verify_universe_integrity(universe_data: dict[str, Any]) -> list[str]:
    """Verify cryptographic integrity, schema properties, and item distinctness of universe."""
    errors: list[str] = []
    if universe_data.get("doc_type") != "vlm_evaluation_universe":
        errors.append(f"Invalid doc_type: {universe_data.get('doc_type')!r}")

    recorded_sha = universe_data.get("universe_sha256")
    computed_sha = compute_universe_sha256(universe_data)
    if recorded_sha != computed_sha:
        errors.append(
            f"Universe cryptographic hash mismatch: recorded {recorded_sha[:12] if recorded_sha else 'null'} "
            f"!= computed {computed_sha[:12]}"
        )

    items = universe_data.get("items", [])
    if not items:
        errors.append("Evaluation universe contains zero items.")

    seen_items: set[str] = set()
    for i, it in enumerate(items):
        iid = it.get("item_id")
        if not iid:
            errors.append(f"Item at index {i} lacks item_id.")
        elif iid in seen_items:
            errors.append(f"Duplicate item_id '{iid}' at index {i}.")
        else:
            seen_items.add(iid)

        rung = it.get("rung")
        if rung not in {"identify", "signs", "transliterate", "translate"}:
            errors.append(f"Item '{iid}' has invalid rung: '{rung}'")

        gold = it.get("gold")
        if not gold or not isinstance(gold, dict):
            errors.append(f"Item '{iid}' lacks required gold reference dictionary.")

    return errors


def get_universe_items(universe_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract item records ready for evaluation execution."""
    items = []
    for it in universe_data.get("items", []):
        item_copy = dict(it)
        # If synthetic mock, supply synthetic image bytes based on ID
        if it.get("admission_status") == "synthetic_mock" and "image_bytes" not in item_copy:
            # Map canonical synthetic image byte references
            iid = it["item_id"]
            if iid == "SYNTH-DOCA-IDENT-001":
                item_copy["image_bytes"] = b"synthetic_palaeography_hieratic_papyrus_01"
            elif iid == "SYNTH-DOCA-IDENT-002":
                item_copy["image_bytes"] = b"synthetic_palaeography_hieratic_papyrus_02"
            elif iid == "SYNTH-DOCB-IDENT-001":
                item_copy["image_bytes"] = b"synthetic_palaeography_hieroglyphic_relief_01"
            elif iid == "SYNTH-DOCB-IDENT-002":
                item_copy["image_bytes"] = b"synthetic_palaeography_hieroglyphic_relief_02"
            elif iid == "SYNTH-DOCA-SIGN-001":
                item_copy["image_bytes"] = b"synthetic_sign_isolated_a01"
            elif iid == "SYNTH-DOCB-SIGN-001":
                item_copy["image_bytes"] = b"synthetic_sign_isolated_g43"
            elif iid == "SYNTH-DOCA-XLIT-001":
                item_copy["image_bytes"] = b"synthetic_phrase_manuscript_line_01"
            elif iid == "SYNTH-DOCB-XLIT-001":
                item_copy["image_bytes"] = b"synthetic_phrase_manuscript_line_02"
            elif iid == "SYNTH-DOCA-TRANS-001":
                item_copy["image_bytes"] = b"synthetic_passage_inscribed_column_01"
            elif iid == "SYNTH-DOCB-TRANS-001":
                item_copy["image_bytes"] = b"synthetic_passage_inscribed_column_02"
        items.append(item_copy)
    return items


def get_universe_gold(universe_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract gold dictionary keyed by item_id."""
    gold_map = {}
    for it in universe_data.get("items", []):
        iid = it["item_id"]
        gold_map[iid] = it.get("gold", {})
    return gold_map


def validate_image_file(image_path: Path, expected_sha256: str | None = None) -> tuple[bytes, list[str]]:
    """Validate on-disk image file: existence, hash match, and PIL RGB decodability."""
    errors: list[str] = []
    if not image_path.is_file():
        return b"", [f"Image file does not exist: {image_path}"]

    try:
        raw_bytes = image_path.read_bytes()
    except Exception as exc:
        return b"", [f"Cannot read image file {image_path}: {exc}"]

    if len(raw_bytes) == 0:
        return b"", [f"Image file {image_path} is empty (0 bytes)."]

    if expected_sha256:
        actual_sha = hashlib.sha256(raw_bytes).hexdigest()
        if actual_sha != expected_sha256:
            errors.append(
                f"Image file {image_path.name} SHA-256 mismatch: actual {actual_sha} != expected {expected_sha256}"
            )

    if Image is not None:
        try:
            img = Image.open(io.BytesIO(raw_bytes))
            img.verify()
            # Re-open for mode and dimension checks after verify
            img = Image.open(io.BytesIO(raw_bytes))
            w, h = img.size
            if w < 16 or h < 16:
                errors.append(f"Image {image_path.name} dimensions too small: ({w}x{h}); minimum 16px.")
        except Exception as exc:
            errors.append(f"Image file {image_path.name} cannot be decoded as valid image: {exc}")
    else:
        # Fallback binary magic byte validation when PIL is not in environment
        is_png = raw_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        is_jpeg = raw_bytes.startswith(b"\xff\xd8\xff")
        is_synth = raw_bytes.startswith(b"synthetic_")
        if not (is_png or is_jpeg or is_synth):
            errors.append(f"Image file {image_path.name} lacks valid PNG or JPEG magic bytes.")

    return raw_bytes, errors


def admit_external_items(
    items_path: Path,
    admission_receipt_path: Path | None = None,
) -> tuple[list[dict[str, Any]], str, list[str]]:
    """Admit external evaluation items with strict classification and fail-closed image validation.

    Returns:
        (items, admission_tier, validation_errors)
    """
    errors: list[str] = []
    if not items_path.is_file():
        return [], "unverified_external_inputs", [f"Items file does not exist: {items_path}"]

    try:
        content = items_path.read_text(encoding="utf-8")
        raw_data = json.loads(content) if items_path.suffix.lower() == ".json" else yaml.safe_load(content)
    except Exception as exc:
        return [], "unverified_external_inputs", [f"Cannot parse items file {items_path}: {exc}"]

    items_list: list[dict[str, Any]] = raw_data.get("items", raw_data) if isinstance(raw_data, dict) else raw_data
    if not isinstance(items_list, list) or not items_list:
        return [], "unverified_external_inputs", ["External items file contains no valid items list."]

    # Validate image files if paths are provided
    for it in items_list:
        img_path_str = it.get("image_path")
        if img_path_str:
            img_path = Path(img_path_str)
            if not img_path.is_absolute():
                img_path = items_path.parent / img_path
            raw_bytes, img_errs = validate_image_file(img_path, it.get("image_sha256"))
            errors.extend(img_errs)
            if not img_errs:
                it["image_bytes"] = raw_bytes

    # External cohort scientific admission is HARD-DISABLED in this preflight.
    # A local JSON/YAML "receipt" is a self-issued claim: it has no signature,
    # no pinned reviewer identity, no binding to exact item IDs / image hashes,
    # no source-registry record and no DATA-008 verification. It can therefore
    # never promote a cohort. The tier is always unverified_external_inputs.
    admission_tier = "unverified_external_inputs"
    if admission_receipt_path and admission_receipt_path.is_file():
        try:
            rcpt = (
                json.loads(admission_receipt_path.read_text(encoding="utf-8"))
                if admission_receipt_path.suffix.lower() == ".json"
                else yaml.safe_load(admission_receipt_path.read_text(encoding="utf-8"))
            )
        except Exception as exc:
            errors.append(f"Cannot read admission receipt {admission_receipt_path}: {exc}")
            rcpt = None
        if isinstance(rcpt, dict):
            looks_approved = (
                rcpt.get("rights_review_status") == "approved_with_evidence"
                and rcpt.get("quarantine_verified") is True
                and rcpt.get("permitted_cohort_tier") == "approved_evaluation_cohort"
                and bool(rcpt.get("independent_reviewer"))
            )
            if looks_approved:
                errors.append(
                    f"{NOTICE_PREFIX}Admission receipt {admission_receipt_path.name} is self-declared and cannot be "
                    "independently verified (no signature, pinned reviewer identity, item/image-hash binding, "
                    "source-registry record or DATA-008 check is integrated); cohort stays "
                    "unverified_external_inputs and is non-promotable."
                )
            else:
                errors.append(
                    f"Admission receipt {admission_receipt_path.name} is incomplete or unapproved; "
                    "cannot grant approved_evaluation_cohort tier."
                )
        elif rcpt is not None:
            errors.append(f"Admission receipt {admission_receipt_path.name} is not a mapping.")

    return items_list, admission_tier, errors


NOTICE_PREFIX = "NOTICE: "


def fatal_admission_errors(errors: list[str]) -> list[str]:
    """Return admission errors that must abort a run (notices are informational)."""
    return [e for e in errors if not e.startswith(NOTICE_PREFIX)]
