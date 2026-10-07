"""Schema and referential validation for layered Hieratic annotations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "annotation.schema.json"
REGISTRY_PATH = ROOT / "data" / "sources" / "registry.yaml"
EXAMPLE_DIR = ROOT / "data" / "examples"
GOLD_STATUSES = {"certain", "uncertain_with_alternatives", "illegible_unscorable", "missing_annotation", "adjudication_pending"}
ALLOWED_TRANSITIONS = {
    "draft": {"in_review", "revision_requested"},
    "in_review": {"reviewed", "revision_requested"},
    "reviewed": {"adjudicated", "revision_requested"},
    "revision_requested": {"draft", "in_review"},
    "adjudicated": set(),
}


class AnnotationInputError(Exception):
    """Input or schema error suitable for the CLI."""


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise AnnotationInputError(f"{path}: cannot read valid YAML: {exc}") from exc


def _unique_ids(values: list[str], label: str, errors: list[str]) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            errors.append(f"duplicate {label} ID: {value}")
        seen.add(value)


def _validate_layer(layer: dict[str, Any], path: str, errors: list[str]) -> None:
    status = layer["gold_status"]
    values = layer["values"]
    value_ids = [value["value_id"] for value in values]
    _unique_ids(value_ids, f"{path} value", errors)
    selected = layer["selected_value_id"]
    if selected is not None and selected not in value_ids:
        errors.append(f"{path}: selected_value_id {selected} does not exist in this layer")
    if status == "certain":
        if not values:
            errors.append(f"{path}: certain layer requires a value")
        if selected is None or selected not in value_ids:
            errors.append(f"{path}: certain layer requires a selected value that exists in this layer")
        else:
            selected_value = next(value for value in values if value["value_id"] == selected)
            if selected_value["equivalent_to_selected"]:
                errors.append(f"{path}: selected certain value cannot be marked equivalent to itself")
            if len(values) > 1 and not all(
                value["equivalent_to_selected"]
                for value in values
                if value["value_id"] != selected
            ):
                errors.append(f"{path}: certain layer has unresolved alternative values")
    elif status == "uncertain_with_alternatives" and len(values) < 2:
        errors.append(f"{path}: uncertain_with_alternatives requires at least two values")
    elif status == "illegible_unscorable":
        if selected is not None:
            errors.append(f"{path}: illegible_unscorable cannot select a reading")
        if not layer["explanation"]:
            errors.append(f"{path}: illegible_unscorable requires an explanation")
    elif status == "missing_annotation" and (values or selected is not None):
        errors.append(f"{path}: missing_annotation cannot contain values or a selected value")


def _layers_in(annotation: dict[str, Any]):
    if "script_label" in annotation:
        yield "script_label", annotation["script_label"]
    for line in annotation["lines"]:
        line_id = line["line_id"]
        for field in ("grapheme_sequence", "hieroglyphic_rendering", "transliteration", "lemma_analysis", "morphology", "syntax"):
            if field in line:
                yield f"lines[{line_id}].{field}", line[field]
        normalized = line.get("normalized_representation")
        if normalized:
            yield f"lines[{line_id}].normalized_representation.layer", normalized["layer"]
            for token in normalized["tokens"]:
                yield f"tokens[{token['token_id']}].value", token["value"]
        for translation in line.get("translations", []):
            yield f"lines[{line_id}].translation[{translation['language']}]", translation["references"]
    for sign in annotation["signs"]:
        yield f"signs[{sign['sign_id']}].grapheme_identity", sign["grapheme_identity"]
    for group in annotation["sign_groups"]:
        yield f"sign_groups[{group['group_id']}].grapheme_identity", group["grapheme_identity"]


def _check_geometry(geometry: dict[str, Any] | None, coordinate_system: str, dimensions: dict[str, Any] | None, path: str, errors: list[str]) -> None:
    if geometry is None:
        return
    points = geometry["vertices"]
    kind = geometry["kind"]
    minimum = {"rectangle": 4, "polyline": 2, "polygon": 3}[kind]
    maximum = {"rectangle": 4}.get(kind)
    if len(points) < minimum or (maximum is not None and len(points) != maximum):
        errors.append(f"{path}: {kind} geometry has invalid vertex count {len(points)}")
    for point_index, (x, y) in enumerate(points):
        if x < 0 or y < 0:
            errors.append(f"{path}.vertices[{point_index}]: coordinates must be non-negative")
        if coordinate_system == "normalized_0_1" and (x > 1 or y > 1):
            errors.append(f"{path}.vertices[{point_index}]: normalized coordinates must be within 0..1")
        if coordinate_system == "pixel_origin_top_left" and dimensions:
            if x > dimensions["width"] or y > dimensions["height"]:
                errors.append(f"{path}.vertices[{point_index}]: pixel coordinate exceeds page dimensions")


def validate_data(annotation: Any, schema: dict[str, Any], registry: Any | None = None) -> list[str]:
    schema_validator = Draft202012Validator(schema, format_checker=FormatChecker())
    schema_errors = sorted(schema_validator.iter_errors(annotation), key=lambda error: list(map(str, error.absolute_path)))
    errors = [f"annotation{''.join(f'[{part!r}]' for part in error.absolute_path)}: {error.message}" for error in schema_errors]
    if errors:
        return errors

    page_ids = [page["page_id"] for page in annotation["pages"]]
    line_ids = [line["line_id"] for line in annotation["lines"]]
    sequence_ids = [line["sequence_id"] for line in annotation["lines"]]
    sign_ids = [sign["sign_id"] for sign in annotation["signs"]]
    group_ids = [group["group_id"] for group in annotation["sign_groups"]]
    region_ids = [region["region_id"] for page in annotation["pages"] for region in page["regions"]]
    for values, label in ((page_ids, "page"), (line_ids, "line"), (sequence_ids, "sequence"), (sign_ids, "sign"), (group_ids, "sign group"), (region_ids, "region")):
        _unique_ids(values, label, errors)
    token_ids = [token["token_id"] for line in annotation["lines"] for token in line.get("normalized_representation", {}).get("tokens", [])]
    asset_ids = [asset["asset_id"] for asset in annotation["provenance"]["asset_refs"]]
    value_ids = [value["value_id"] for _, layer in _layers_in(annotation) for value in layer["values"]]
    value_ids.extend(
        value["value_id"]
        for line in annotation["lines"]
        for token in line.get("normalized_representation", {}).get("tokens", [])
        for field in ("acceptable_lemmas", "morphology_bundles")
        for value in token[field]
    )
    value_ids.extend(value["value_id"] for sign in annotation["signs"] for value in sign["alternative_identities"])
    _unique_ids(token_ids, "token", errors)
    _unique_ids(asset_ids, "asset", errors)
    _unique_ids(value_ids, "layer value", errors)
    if registry is not None:
        known_source_ids = {record["source_id"] for record in registry["sources"]}
        source_id = annotation["provenance"]["source_registry_id"]
        if source_id not in known_source_ids:
            errors.append(f"provenance.source_registry_id does not match DATA-001: {source_id}")

    all_regions = {region["region_id"]: (page, region) for page in annotation["pages"] for region in page["regions"]}
    pages = {page["page_id"]: page for page in annotation["pages"]}
    lines = {line["line_id"]: line for line in annotation["lines"]}
    signs = {sign["sign_id"]: sign for sign in annotation["signs"]}
    groups = {group["group_id"]: group for group in annotation["sign_groups"]}

    for path, layer in _layers_in(annotation):
        _validate_layer(layer, path, errors)
    for page in annotation["pages"]:
        page_id = page["page_id"]
        local_regions = {region["region_id"]: region for region in page["regions"]}
        for region in page["regions"]:
            region_id = region["region_id"]
            if region["parent_region_id"] is not None:
                parent = local_regions.get(region["parent_region_id"])
                if parent is None:
                    errors.append(f"region {region_id}: parent region {region['parent_region_id']} does not exist on page {page_id}")
                elif region_id not in parent["child_region_ids"]:
                    errors.append(f"region {region_id}: parent/child relation is not reciprocal")
            for child_id in region["child_region_ids"]:
                child = local_regions.get(child_id)
                if child is None:
                    errors.append(f"region {region_id}: child region {child_id} does not exist on page {page_id}")
                elif child["parent_region_id"] != region_id:
                    errors.append(f"region {region_id}: child/parent relation is not reciprocal for {child_id}")
            _check_geometry(region["geometry"], page["coordinate_system"], page["dimensions"], f"region {region_id}", errors)
        for region_id in page["reading_order"]:
            if region_id not in local_regions:
                errors.append(f"page {page_id}: reading_order references nonexistent region {region_id}")

        reported_cycles: set[tuple[str, ...]] = set()
        for start_region_id in local_regions:
            trail: list[str] = []
            current_region_id: str | None = start_region_id
            while current_region_id is not None and current_region_id in local_regions:
                if current_region_id in trail:
                    cycle = tuple(sorted(trail[trail.index(current_region_id):]))
                    if cycle not in reported_cycles:
                        errors.append(f"page {page_id}: parent-region cycle detected: {', '.join(cycle)}")
                        reported_cycles.add(cycle)
                    break
                trail.append(current_region_id)
                current_region_id = local_regions[current_region_id]["parent_region_id"]

    for line in annotation["lines"]:
        line_id = line["line_id"]
        page = pages.get(line["page_id"])
        if page is None:
            errors.append(f"line {line_id}: page {line['page_id']} does not exist")
            continue
        if line["region_id"] is not None:
            region_pair = all_regions.get(line["region_id"])
            if region_pair is None:
                errors.append(f"line {line_id}: region {line['region_id']} does not exist")
            elif region_pair[0]["page_id"] != line["page_id"]:
                errors.append(f"line {line_id}: region {line['region_id']} belongs to a different page")
        if line["parent_line_id"] is not None:
            parent = lines.get(line["parent_line_id"])
            if parent is None:
                errors.append(f"line {line_id}: parent line {line['parent_line_id']} does not exist")
            elif parent["page_id"] != line["page_id"]:
                errors.append(f"line {line_id}: parent line belongs to a different page")
        peer_orders = [peer["reading_order"] for peer in annotation["lines"] if peer["page_id"] == line["page_id"]]
        if peer_orders.count(line["reading_order"]) > 1:
            errors.append(f"line {line_id}: reading_order {line['reading_order']} is duplicated on page {line['page_id']}")
        _check_geometry(line["geometry"], page["coordinate_system"], page["dimensions"], f"line {line_id}", errors)
        normalized = line.get("normalized_representation")
        if normalized:
            for token in normalized["tokens"]:
                if token["sequence_ref"] not in {line_id, line["sequence_id"]}:
                    if token["sequence_ref"] in set(sequence_ids) | set(line_ids):
                        errors.append(f"token {token['token_id']}: sequence_ref {token['sequence_ref']} belongs to a different line")
                    else:
                        errors.append(f"token {token['token_id']}: sequence_ref {token['sequence_ref']} does not exist")
                if token["gold_status"] != token["value"]["gold_status"]:
                    errors.append(f"token {token['token_id']}: gold_status does not match value layer status")

    for sign in annotation["signs"]:
        line = lines.get(sign["line_id"])
        if line is None:
            errors.append(f"sign {sign['sign_id']}: line {sign['line_id']} does not exist")
            continue
        page = pages[line["page_id"]]
        _check_geometry(sign["geometry"], page["coordinate_system"], page["dimensions"], f"sign {sign['sign_id']}", errors)
        for group_id in sign["group_ids"]:
            group = groups.get(group_id)
            if group is None:
                errors.append(f"sign {sign['sign_id']}: group {group_id} does not exist")
            elif sign["sign_id"] not in group["constituent_sign_ids"]:
                errors.append(f"sign {sign['sign_id']}: group membership is not reciprocal for {group_id}")
    for group in annotation["sign_groups"]:
        line = lines.get(group["line_id"])
        if line is None:
            errors.append(f"sign group {group['group_id']}: line {group['line_id']} does not exist")
        for sign_id in group["constituent_sign_ids"]:
            sign = signs.get(sign_id)
            if sign is None:
                errors.append(f"sign group {group['group_id']}: constituent sign {sign_id} does not exist")
            else:
                if sign["line_id"] != group["line_id"]:
                    errors.append(f"sign group {group['group_id']}: constituent {sign_id} belongs to another line")
                if group["group_id"] not in sign["group_ids"]:
                    errors.append(f"sign group {group['group_id']}: membership is not reciprocal for sign {sign_id}")
        if line is not None:
            page = pages[line["page_id"]]
            _check_geometry(group["geometry"], page["coordinate_system"], page["dimensions"], f"sign group {group['group_id']}", errors)

    review_ids = [review["review_id"] for review in annotation["reviews"]]
    _unique_ids(review_ids, "review", errors)
    reviews = {review["review_id"]: review for review in annotation["reviews"]}
    for review in annotation["reviews"]:
        if review["supersedes_review_id"] is not None and review["supersedes_review_id"] not in reviews:
            errors.append(f"review {review['review_id']}: superseded review {review['supersedes_review_id']} does not exist")
        if review["review_status"] in {"reviewed", "adjudicated"} and not review["reviewer_id"]:
            errors.append(f"review {review['review_id']}: {review['review_status']} requires reviewer_id")
        if review["review_status"] == "adjudicated" and (not review["adjudicator_id"] or review["adjudicator_id"] == review["reviewer_id"]):
            errors.append(f"review {review['review_id']}: adjudicated status requires a distinct adjudicator")
        previous = "draft"
        for transition in review["status_history"]:
            if transition["from"] != previous:
                errors.append(f"review {review['review_id']}: status history starts or continues from unexpected state {transition['from']}")
            if transition["to"] not in ALLOWED_TRANSITIONS[transition["from"]]:
                errors.append(f"review {review['review_id']}: invalid status transition {transition['from']} -> {transition['to']}")
            previous = transition["to"]
        if review["status_history"] and previous != review["review_status"]:
            errors.append(f"review {review['review_id']}: status history ends at {previous}, not review_status {review['review_status']}")
        if not review["status_history"] and review["review_status"] != "draft":
            errors.append(f"review {review['review_id']}: non-draft state requires status_history")
    return errors


def validate_file(annotation_path: Path, schema_path: Path = SCHEMA_PATH, registry_path: Path = REGISTRY_PATH) -> list[str]:
    annotation = load_yaml(annotation_path)
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AnnotationInputError(f"{schema_path}: cannot read valid JSON Schema: {exc}") from exc
    registry = load_yaml(registry_path)
    return validate_data(annotation, schema, registry)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.annotation_validation")
    parser.add_argument("validate", choices=["validate"])
    parser.add_argument("annotation", type=Path)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    args = parser.parse_args(argv)
    try:
        errors = validate_file(args.annotation, args.schema, args.registry)
    except AnnotationInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("Annotation validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"PASS: {args.annotation} is a valid layered annotation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
