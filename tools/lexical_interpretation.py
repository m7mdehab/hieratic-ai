"""Validate LING-001 manifests and add conservative lexical candidate analyses."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from tools.source_registry import validate_registry_data

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/lexical_interpretation.schema.json"
REGISTRY_PATH = ROOT / "data/sources/registry.yaml"
GENERATOR = "hieratic-lexical-interpretation/1.0.0"
MAX_BYTES = 16 * 1024 * 1024


class InterpretationError(ValueError):
    """Invalid or unsupported lexical interpretation input."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_data(path: Path) -> tuple[Any, bytes]:
    try:
        raw = path.read_bytes()
        if len(raw) > MAX_BYTES:
            raise InterpretationError(f"input exceeds {MAX_BYTES} byte limit: {path}")
        data = json.loads(raw.decode("utf-8")) if path.suffix.lower() == ".json" else yaml.safe_load(raw.decode("utf-8"))
        return data, raw
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise InterpretationError(f"cannot read {path}: {exc}") from exc


def schema_errors(value: Any, schema: dict[str, Any], label: str) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    found = sorted(validator.iter_errors(value), key=lambda e: list(map(str, e.absolute_path)))
    return [f"{label}{''.join(f'[{part!r}]' for part in e.absolute_path)}: {e.message}" for e in found]


def definition_errors(value: Any, schema: dict[str, Any], definition: str, label: str) -> list[str]:
    # Keep the original $defs root so nested local references resolve correctly.
    fragment = {"$schema": schema["$schema"], "$defs": schema["$defs"], **schema["$defs"][definition]}
    return schema_errors(value, fragment, label)


def source_records(registry: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(registry, dict) or not isinstance(registry.get("sources"), list):
        raise InterpretationError("source registry is malformed")
    records = {r.get("source_id"): r for r in registry["sources"] if isinstance(r, dict) and isinstance(r.get("source_id"), str)}
    if len(records) != len(registry["sources"]):
        raise InterpretationError("source registry has missing or duplicate source identities")
    return records


def validate_normalization(manifest: Any, schema: dict[str, Any]) -> list[str]:
    errors = definition_errors(manifest, schema, "normalizationManifest", "normalization")
    if errors:
        return errors
    identity = {k: copy.deepcopy(v) for k, v in manifest.items() if k not in {"schema_version", "normalization_version_id"}}
    if manifest["normalization_version_id"] != "ling-" + digest(canonical(identity)):
        errors.append("normalization_version_id does not match canonical manifest content (source/hash drift)")
    if not isinstance(manifest.get("annotation", {}).get("sha256"), str) or len(manifest["annotation"]["sha256"]) != 64:
        errors.append("normalization manifest lacks a pinned DATA-004 source hash")
    unit_ids: set[str] = set()
    for item in manifest["items"]:
        uid = item.get("unit_id")
        if uid in unit_ids:
            errors.append(f"duplicate normalized unit_id: {uid}")
        unit_ids.add(uid)
        values = item.get("values", [])
        if item.get("acceptable_reading_ids", []) != [v.get("source_value_id") for v in values]:
            errors.append(f"{uid}: source alternatives are incomplete or reordered")
        if len({v.get("source_value_id") for v in values}) != len(values):
            errors.append(f"{uid}: duplicate source value identity")
        for value in values:
            text = value.get("normalized_text")
            original = value.get("diplomatic_text")
            if not isinstance(text, str) or digest(text.encode("utf-8")) != value.get("normalized_sha256"):
                errors.append(f"{uid}: normalized text/hash mismatch")
            if not isinstance(original, str) or digest(original.encode("utf-8")) != value.get("source_sha256"):
                errors.append(f"{uid}: diplomatic text/hash mismatch")
    return errors


def validate_lexicon(lexicon: Any, schema: dict[str, Any], registry: Any) -> list[str]:
    errors = definition_errors(lexicon, schema, "lexicon", "lexicon")
    if errors:
        return errors
    try:
        sources = source_records(registry)
    except InterpretationError as exc:
        return [str(exc)]
    registry_schema = json.loads((ROOT / "schemas/data_sources.schema.json").read_text(encoding="utf-8"))
    errors.extend(validate_registry_data(registry, registry_schema))
    if errors:
        return errors
    ids: set[str] = set()
    for entry in lexicon["entries"]:
        eid = entry["entry_id"]
        if eid in ids:
            errors.append(f"duplicate entry_id: {eid}")
        ids.add(eid)
        if entry["form_sha256"] != digest(entry["form"].encode("utf-8")):
            errors.append(f"{eid}: form_sha256 does not match exact Unicode form")
        if entry["scientific_status"] == "illustrative_synthetic":
            if entry["attestations"] or entry["rights"]["rights_class"] != "SYNTHETIC" or entry["rights"]["review_status"] != "not_applicable_synthetic":
                errors.append(f"{eid}: synthetic entries cannot claim citations or external rights clearance")
            continue
        if not entry["attestations"]:
            errors.append(f"{eid}: scholarly entry requires a cited attestation")
        rights = entry["rights"]
        if rights["review_status"] != "independently_verified" or rights["rights_class"] not in {"OPEN-PD", "OPEN-BY", "OPEN-SA"}:
            errors.append(f"{eid}: scholarly lexical source rights are not independently cleared")
        if rights["intended_use"] not in {"research", "development", "evaluation"}:
            errors.append(f"{eid}: scholarly entry lacks explicit intended-use clearance")
        for attestation in entry["attestations"]:
            source_id = attestation["source_identity"]["source_registry_id"]
            source = sources.get(source_id)
            if source is None:
                errors.append(f"{eid}: invalid source reference {source_id}")
                continue
            if source.get("verified_status") != "VERIFIED-PRIMARY" or source.get("rights_class") not in {"OPEN-PD", "OPEN-BY", "OPEN-SA"}:
                errors.append(f"{eid}: source {source_id} is not a verified compatible scholarly source")
            if source.get("rights_class") != entry["rights"]["rights_class"]:
                errors.append(f"{eid}: entry rights class conflicts with canonical source registry")
            permitted_field = {"research": "development_use", "development": "development_use", "evaluation": "evaluation_use"}.get(entry["rights"]["intended_use"])
            if permitted_field is None or source.get(permitted_field) != "allowed":
                errors.append(f"{eid}: source {source_id} does not explicitly allow {entry['rights']['intended_use']} use")
            if attestation["citation"].get("verification_evidence_url") is None:
                errors.append(f"{eid}: citation lacks independent verification evidence")
            if attestation["source_identity"].get("source_content_sha256") is None:
                errors.append(f"{eid}: source content hash is required")
    return errors


def build(manifest: Any, lexicon: Any, registry: Any, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    schema = schema or json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = validate_normalization(manifest, schema) + validate_lexicon(lexicon, schema, registry)
    if errors:
        raise InterpretationError("\n".join(errors))
    if any(e["scientific_status"] != lexicon["scientific_status"] for e in lexicon["entries"]):
        raise InterpretationError("mixed synthetic and scholarly entries are prohibited")
    sources = source_records(registry)
    source_id = manifest["annotation"].get("source_registry_id")
    source = sources.get(source_id)
    if source is None:
        raise InterpretationError(f"normalization references unknown source identity: {source_id}")
    source_object = str(manifest["annotation"].get("source_object_id", ""))
    rights_note = str(manifest["annotation"].get("rights_provenance_ref", "")).lower()
    is_synthetic = source_object.startswith("SYNTHETIC-") and "synthetic" in rights_note
    if is_synthetic and lexicon["scientific_status"] != "illustrative_synthetic":
        raise InterpretationError("synthetic normalization input requires an illustrative synthetic lexicon")
    if not is_synthetic:
        if lexicon["scientific_status"] == "illustrative_synthetic":
            raise InterpretationError("synthetic lexicon cannot be applied to a real-source record")
        if source.get("verified_status") != "VERIFIED-PRIMARY" or source.get("rights_class") not in {"OPEN-PD", "OPEN-BY", "OPEN-SA"} or source.get("development_use") != "allowed":
            raise InterpretationError("input source lacks independently verified compatible development-use rights")

    by_form: dict[str, list[dict[str, Any]]] = {}
    for entry in lexicon["entries"]:
        by_form.setdefault(entry["form"], []).append(entry)
    blocked = {"illegible_unscorable", "missing_annotation", "adjudication_pending"}
    outputs = []
    for item in manifest["items"]:
        readings = []
        if item.get("gold_status") in blocked or not item.get("values"):
            readings.append({"source_value_id": None, "normalized_text": None, "analyses": [], "outcome": "unknown", "reason": "source reading is missing, illegible, or pending adjudication"})
        else:
            for value in item["values"]:
                candidates = sorted(by_form.get(value["normalized_text"], []), key=lambda e: e["entry_id"])
                analyses = [{k: copy.deepcopy(e[k]) for k in ("entry_id", "lemma", "root", "part_of_speech", "grammatical_features", "inflection", "historical_period", "attestations", "confidence", "uncertainty", "scientific_status")} for e in candidates]
                outcome = "unattested" if not analyses else ("interpreted" if len(analyses) == 1 and item["gold_status"] == "certain" else "ambiguous")
                readings.append({"source_value_id": value["source_value_id"], "normalized_text": value["normalized_text"], "normalized_sha256": value["normalized_sha256"], "analyses": analyses, "outcome": outcome, "reason": "no exact lexicon entry" if not analyses else ("source alternatives or multiple candidate analyses remain" if outcome == "ambiguous" else None)})
        count = sum(len(r["analyses"]) for r in readings)
        if item.get("gold_status") in blocked:
            outcome = "unknown"
        elif item.get("gold_status") != "certain" or len(readings) != 1 or any(r["outcome"] == "ambiguous" for r in readings):
            outcome = "ambiguous" if count or len(readings) else "unknown"
        elif count == 0:
            outcome = "unattested"
        elif count > 1:
            outcome = "ambiguous"
        else:
            outcome = "interpreted"
        outputs.append({"unit_id": item["unit_id"], "line_id": item["line_id"], "token_id": item.get("token_id"), "source_layer": item["source_layer"], "source_gold_status": item["gold_status"], "source_value_ids": copy.deepcopy(item["acceptable_reading_ids"]), "diplomatic_transliteration": copy.deepcopy(item["diplomatic_transliteration"]), "normalized_representation": copy.deepcopy(item["normalized_representation"]), "readings": readings, "outcome": outcome, "source_analysis_preserved": copy.deepcopy(item.get("linguistic_analysis")), "gold_scoring_eligible": False})
    identity = {"interpretation_input": {"normalization_version_id": manifest["normalization_version_id"], "annotation_sha256": manifest["annotation"]["sha256"], "source_registry_id": source_id, "source_object_id": source_object}, "lexicon": {"lexicon_id": lexicon["lexicon_id"], "lexicon_version": lexicon["lexicon_version"], "lexicon_sha256": digest(canonical(lexicon)), "scientific_status": lexicon["scientific_status"]}, "generator": GENERATOR, "items": outputs, "metrics": {"computed": False, "reason": "No independently reviewed gold or prediction evaluation is performed."}}
    return {"schema_version": "1.0.0", **identity, "interpretation_version_id": "lex-" + digest(canonical(identity))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "interpret"):
        cmd = subs.add_parser(name)
        cmd.add_argument("normalization", type=Path)
        cmd.add_argument("--lexicon", type=Path, required=True)
        cmd.add_argument("--registry", type=Path, default=REGISTRY_PATH)
        if name == "interpret":
            cmd.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        manifest, _ = read_data(args.normalization)
        lexicon, _ = read_data(args.lexicon)
        registry, _ = read_data(args.registry)
        result = build(manifest, lexicon, registry, schema)
        if args.command == "validate":
            print(f"PASS: {manifest['normalization_version_id']} and lexicon {lexicon['lexicon_id']} validate; no output written")
            return 0
        errors = definition_errors(result, schema, "interpretationManifest", "output")
        if errors:
            raise InterpretationError("\n".join(errors))
        output = args.output.absolute()
        parent = output.parent
        while parent != parent.parent:
            if parent.is_symlink():
                raise InterpretationError("output path cannot traverse a symlink")
            parent = parent.parent
        if output.exists() or output.is_symlink():
            raise InterpretationError("output already exists; interpretation releases are immutable")
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False) as handle:
                temporary = handle.name
                handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
                handle.flush(); os.fsync(handle.fileno())
            try:
                os.link(temporary, output)
            except FileExistsError as exc:
                raise InterpretationError("output appeared during write; refusing overwrite") from exc
            Path(temporary).unlink(); temporary = None
        finally:
            if temporary and Path(temporary).exists():
                Path(temporary).unlink()
        print(f"PASS: wrote {result['interpretation_version_id']} ({len(result['items'])} units; no metrics computed)")
        return 0
    except (InterpretationError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
