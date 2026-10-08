"""Normalize text encodings and declared formatting while preserving readings."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from tools.annotation_validation import validate_data as validate_annotation
from tools.source_registry import load_yaml as load_registry

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/linguistic_normalization.schema.json"
ANNOTATION_SCHEMA = ROOT / "schemas/annotation.schema.json"
REGISTRY = ROOT / "data/sources/registry.yaml"
PROFILES = ROOT / "ling/normalization/profiles.yaml"
MAX_BYTES = 16 * 1024 * 1024
GENERATOR = "hieratic-linguistic-normalization/1.0.0"


class NormalizationError(ValueError):
    """Malformed input or unsupported normalization request."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path) -> tuple[Any, bytes]:
    try:
        raw = path.read_bytes()
        if len(raw) > MAX_BYTES:
            raise NormalizationError(f"input exceeds {MAX_BYTES} byte limit: {path}")
        if path.suffix.lower() == ".json":
            return json.loads(raw.decode("utf-8")), raw
        return yaml.safe_load(raw.decode("utf-8")), raw
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise NormalizationError(f"cannot read {path}: {exc}") from exc


def _schema_errors(value: Any, schema: dict[str, Any], label: str) -> list[str]:
    found = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value), key=lambda e: str(e.absolute_path))
    return [f"{label}{''.join(f'[{part!r}]' for part in error.absolute_path)}: {error.message}" for error in found]


def normalize_text(text: str, profile_id: str, version: str, whitespace_semantics: str, line_break_semantics: str) -> tuple[str, dict[str, Any]]:
    profiles, _ = read(PROFILES)
    profile = profiles.get("profiles", {}).get(profile_id)
    if profile is None or profile.get("version") != version:
        raise NormalizationError(f"unsupported profile/version: {profile_id}/{version}")
    value = text
    applied: list[str] = []
    if profile_id == "identity":
        return value, {"applied_rules": [], "reversible": True, "non_reversible_operations": []}
    if profile_id == "unicode-nfc":
        value = unicodedata.normalize("NFC", value)
        applied.append("unicode_nfc")
    elif profile_id in {"translit_diplomatic_v1", "translit_compare_v1"}:
        value = unicodedata.normalize("NFC", value)
        applied.append("unicode_nfc")
        value = value.replace("\r\n", "\n").replace("\r", "\n")
        applied.append("normalize_line_endings_to_lf")
        if profile_id == "translit_diplomatic_v1":
            value = value.rstrip(" \t\f\v\n")
            applied.append("trim_terminal_whitespace")
        else:
            value = value.strip()
            applied.append("trim_outer_whitespace")
            if line_break_semantics == "formatting_only":
                value = value.replace("\n", " ")
                applied.append("normalize_formatting_line_breaks_to_spaces")
            if whitespace_semantics == "token_separator":
                value = re.sub(r" {2,}", " ", value)
                applied.append("collapse_repeated_token_separator_spaces")
            elif whitespace_semantics == "formatting_only":
                if line_break_semantics == "formatting_only":
                    value = re.sub(r"\s+", " ", value)
                else:
                    value = re.sub(r"[ \t\f\v]{2,}", " ", value)
                applied.append("collapse_declared_formatting_whitespace")
            elif whitespace_semantics not in {"significant", "unknown"}:
                raise NormalizationError(f"unsupported whitespace semantics: {whitespace_semantics}")
            if line_break_semantics not in {"formatting_only", "significant", "unknown"}:
                raise NormalizationError(f"unsupported line-break semantics: {line_break_semantics}")
    else:
        raise NormalizationError(f"profile implementation is missing: {profile_id}/{version}")
    changed = value != text
    return value, {"applied_rules": applied, "reversible": bool(profile.get("reversible")) or not changed,
                   "non_reversible_operations": list(profile.get("non_reversible_operations", [])) if changed else []}


def validate_request(request: Any, annotation: Any, annotation_bytes: bytes, registry: Any,
                     schema: dict[str, Any] | None = None, profiles: Any | None = None) -> tuple[list[str], dict[str, Any]]:
    schema = schema or json.loads(SCHEMA.read_text(encoding="utf-8"))
    profiles = profiles or read(PROFILES)[0]
    errors = _schema_errors(request, schema, "request")
    errors.extend(_schema_errors(annotation, json.loads(ANNOTATION_SCHEMA.read_text(encoding="utf-8")), "annotation"))
    if errors:
        return errors, {}
    errors.extend(validate_annotation(annotation, json.loads(ANNOTATION_SCHEMA.read_text(encoding="utf-8")), registry))
    if request["annotation_id"] != annotation["annotation_id"]:
        errors.append("annotation_id does not match DATA-004 annotation")
    actual_hash = sha256(annotation_bytes)
    if request["annotation_sha256"].lower() != actual_hash:
        errors.append("annotation_sha256 does not match exact DATA-004 input bytes")
    profile = profiles.get("profiles", {}).get(request["profile_id"])
    if profile is None or profile.get("version") != request["profile_version"]:
        errors.append(f"unsupported profile/version: {request['profile_id']}/{request['profile_version']}")
    lines = {line["line_id"]: line for line in annotation.get("lines", [])}
    tokens = {token["token_id"]: (line, token) for line in annotation.get("lines", []) for token in line.get("normalized_representation", {}).get("tokens", [])}
    unit_ids: set[str] = set()
    target_keys: set[tuple[str, str, str | None]] = set()
    group_ids: set[str] = set()
    for item in request["items"]:
        uid = item["unit_id"]
        if uid in unit_ids:
            errors.append(f"duplicate unit_id: {uid}")
        unit_ids.add(uid)
        line = lines.get(item["line_id"])
        if line is None:
            errors.append(f"{uid}: unknown DATA-004 line_id {item['line_id']}")
            continue
        target = (item["line_id"], item["source_layer"], item["token_id"])
        if target in target_keys:
            errors.append(f"{uid}: duplicate reading group target")
        target_keys.add(target)
        if item["reading_group_id"] in group_ids:
            errors.append(f"duplicate reading_group_id: {item['reading_group_id']}")
        group_ids.add(item["reading_group_id"])
        layer: dict[str, Any] | None
        if item["source_layer"] == "diplomatic_transliteration":
            layer = line.get("transliteration")
            if layer is None:
                layer = {"gold_status": "missing_annotation", "values": [], "selected_value_id": None, "explanation": "DATA-004 transliteration layer is absent."}
            if item["token_id"] is not None:
                errors.append(f"{uid}: diplomatic line transliteration must not name a token")
        else:
            pair = tokens.get(item["token_id"])
            if pair is None:
                errors.append(f"{uid}: unknown DATA-004 token_id {item['token_id']}")
                continue
            if pair[0]["line_id"] != item["line_id"]:
                errors.append(f"{uid}: token_id belongs to a different DATA-004 line")
                continue
            layer = pair[1]["value"]
        if layer is None:
            errors.append(f"{uid}: source layer is absent from DATA-004")
            continue
        expected_ids = [candidate["value_id"] for candidate in layer["values"]]
        if item["source_value_ids"] != expected_ids:
            errors.append(f"{uid}: source_value_ids must preserve every DATA-004 alternative in canonical order")
        for candidate in layer["values"]:
            if candidate["value_id"] in item["source_value_ids"] and not isinstance(candidate["value"], str):
                errors.append(f"{uid}: source candidate {candidate['value_id']} must be a string in this text profile")
    return errors, profile or {}


def build(request: Any, annotation: Any, annotation_bytes: bytes, registry: Any) -> dict[str, Any]:
    errors, profile = validate_request(request, annotation, annotation_bytes, registry)
    if errors:
        raise NormalizationError("\n".join(errors))
    lines = {line["line_id"]: line for line in annotation["lines"]}
    tokens = {token["token_id"]: (line, token) for line in annotation["lines"] for token in line.get("normalized_representation", {}).get("tokens", [])}
    output_items = []
    collisions = []
    for item in sorted(request["items"], key=lambda x: x["unit_id"]):
        line = lines[item["line_id"]]
        if item["source_layer"] == "diplomatic_transliteration":
            layer = line.get("transliteration")
            if layer is None:
                layer = {"gold_status": "missing_annotation", "values": [], "selected_value_id": None, "explanation": "DATA-004 transliteration layer is absent."}
        else:
            layer = tokens[item["token_id"]][1]["value"]
        values = []
        normalized_buckets: dict[str, list[str]] = {}
        for candidate in layer["values"]:
            normalized, reversibility = normalize_text(candidate["value"], request["profile_id"], request["profile_version"], item["whitespace_semantics"], item["line_break_semantics"])
            values.append({"source_value_id": candidate["value_id"], "diplomatic_text": candidate["value"], "normalized_text": normalized,
                           "source_sha256": sha256(candidate["value"].encode("utf-8")), "normalized_sha256": sha256(normalized.encode("utf-8")),
                           "confidence": candidate["confidence"], "equivalent_to_selected": candidate["equivalent_to_selected"],
                           "evidence_ref": candidate.get("evidence_ref"), "reversibility": reversibility})
            normalized_buckets.setdefault(normalized, []).append(candidate["value_id"])
        for normalized, ids in sorted(normalized_buckets.items()):
            if len(ids) > 1:
                collisions.append({"reading_group_id": item["reading_group_id"], "unit_id": item["unit_id"], "normalized_sha256": sha256(normalized.encode("utf-8")),
                                   "source_value_ids": ids, "collapsed": False, "reason": "distinct DATA-004 alternatives normalize to the same text; both are retained"})
        analysis_fields = {key: copy.deepcopy(line[key]) for key in ("lemma_analysis", "morphology", "syntax") if key in line}
        diplomatic = line.get("transliteration") or {"gold_status": "missing_annotation", "values": [], "selected_value_id": None,
                                                     "explanation": "DATA-004 transliteration layer is absent."}
        output_items.append({"unit_id": item["unit_id"], "line_id": item["line_id"], "token_id": item["token_id"],
                             "source_layer": item["source_layer"], "reading_group_id": item["reading_group_id"],
                             "gold_status": layer["gold_status"], "selected_value_id": layer["selected_value_id"],
                             "explanation": layer["explanation"], "acceptable_reading_ids": [x["value_id"] for x in layer["values"]],
                             "values": values, "input_layer": item["source_layer"],
                             "normalization_configuration": {"whitespace_semantics": item["whitespace_semantics"], "line_break_semantics": item["line_break_semantics"]},
                             "diplomatic_transliteration": {"gold_status": diplomatic["gold_status"], "selected_value_id": diplomatic["selected_value_id"],
                                                             "explanation": diplomatic["explanation"], "values": copy.deepcopy(diplomatic["values"])},
                             "normalized_representation": {"profile_id": request["profile_id"], "profile_version": request["profile_version"], "values": [{"source_value_id": x["source_value_id"], "text": x["normalized_text"]} for x in values]},
                             "linguistic_analysis": {"annotation_id": annotation["annotation_id"], "line_id": line["line_id"], "fields": analysis_fields, "transformed": False}})
    identity = {"normalization_id": request["normalization_id"], "generator": GENERATOR,
                "annotation": {"annotation_id": annotation["annotation_id"], "sha256": sha256(annotation_bytes),
                               "source_registry_id": annotation["provenance"]["source_registry_id"], "source_object_id": annotation["provenance"]["source_object_id"],
                               "source_url": annotation["provenance"]["source_url"], "rights_provenance_ref": annotation["provenance"]["rights_provenance_ref"]},
                "profile": {"profile_id": request["profile_id"], "profile_version": request["profile_version"], **copy.deepcopy(profile)},
                "items": output_items, "collisions": sorted(collisions, key=lambda x: (x["unit_id"], x["normalized_sha256"]))}
    return {"schema_version": "1.0.0", **identity, "normalization_version_id": "ling-" + sha256(canonical(identity))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "normalize"):
        command = sub.add_parser(name)
        command.add_argument("request", type=Path)
        command.add_argument("--annotation", type=Path, required=True)
        if name == "normalize":
            command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        request, _ = read(args.request)
        annotation, annotation_bytes = read(args.annotation)
        registry = load_registry(REGISTRY)
        errors, profile = validate_request(request, annotation, annotation_bytes, registry)
        if errors:
            raise NormalizationError("\n".join(errors))
        if args.command == "validate":
            print(f"PASS: {request['normalization_id']} validates against DATA-004 and {request['profile_id']}/{request['profile_version']}; no output written")
            return 0
        result = build(request, annotation, annotation_bytes, registry)
        output_schema = json.loads(SCHEMA.read_text(encoding="utf-8"))["$defs"]["normalizationManifest"]
        output_errors = _schema_errors(result, output_schema, "output")
        if output_errors:
            raise NormalizationError("\n".join(output_errors))
        output = args.output.absolute()
        parent_path = output.parent
        while parent_path != parent_path.parent:
            if parent_path.is_symlink():
                raise NormalizationError("output path cannot traverse a symlink")
            parent_path = parent_path.parent
        if output.exists() or output.is_symlink():
            raise NormalizationError("output path already exists; versioned normalization outputs are immutable")
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary_name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False) as temporary:
                temporary_name = temporary.name
                temporary.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            # Linking creates the destination *only if absent*. os.replace would
            # overwrite another process's file after our check (TOCTOU race).
            # The temp file is in the same directory/filesystem.
            try:
                os.link(temporary_name, output)
            except FileExistsError as exc:
                raise NormalizationError("output appeared during write; refusing overwrite") from exc
            Path(temporary_name).unlink()
            temporary_name = None
        except Exception:
            if temporary_name and Path(temporary_name).exists():
                Path(temporary_name).unlink()
            raise
        print(f"PASS: wrote {result['normalization_version_id']} ({len(result['items'])} groups; {len(result['collisions'])} preserved collisions)")
        return 0
    except (NormalizationError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
