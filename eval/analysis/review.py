"""EVAL-005: deterministic, evidence-linked Hieratic reading error-analysis CLI.

Only consumes redacted structured review metadata. It never opens images, raw
model responses, benchmark gold, or model training inputs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TAXONOMY = PROJECT_ROOT / "eval/analysis/error_taxonomy.yaml"
DEFAULT_SCHEMA = PROJECT_ROOT / "eval/analysis/review_record.schema.json"
DEFAULT_METRICS = PROJECT_ROOT / "eval/metric_contract.yaml"


class ReviewError(ValueError):
    pass


def load_contracts(taxonomy_path: Path = DEFAULT_TAXONOMY,
                   schema_path: Path = DEFAULT_SCHEMA,
                   metrics_path: Path = DEFAULT_METRICS) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    taxonomy = yaml.safe_load(taxonomy_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    metrics = yaml.safe_load(metrics_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    if not isinstance(taxonomy, dict) or not isinstance(metrics, dict):
        raise ReviewError("Taxonomy and metric contract must be mappings")
    required = {"code", "layer", "definition", "requires_evidence"}
    codes: set[str] = set()
    layers = {m["layer"] for m in metrics["metrics"]}
    layers.update({"evaluation_integrity"})
    for idx, entry in enumerate(taxonomy.get("error_codes", []), 1):
        if not isinstance(entry, dict) or not required.issubset(entry):
            raise ReviewError(f"Invalid taxonomy entry {idx}")
        if entry["code"] in codes:
            raise ReviewError(f"Duplicate taxonomy error code {entry['code']}")
        if entry["layer"] not in layers:
            raise ReviewError(f"Unknown metric layer for error code {entry['code']}: {entry['layer']}")
        codes.add(entry["code"])
    if not codes:
        raise ReviewError("Error taxonomy must contain at least one code")
    return taxonomy, schema, metrics


def read_reviews(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ReviewError(f"Invalid JSON on line {index}: {exc.msg}") from exc
        if not isinstance(entry, dict):
            raise ReviewError(f"Review on line {index} must be an object")
        rows.append(entry)
    return rows


def validate_reviews(rows: list[dict[str, Any]], taxonomy: dict[str, Any],
                     schema: dict[str, Any], metrics: dict[str, Any]) -> None:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    codebook = {c["code"]: c for c in taxonomy["error_codes"]}
    metric_ids = {m["id"] for m in metrics["metrics"]}
    known: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows, 1):
        problems = list(validator.iter_errors(row))
        if problems:
            err = sorted(problems, key=lambda x: str(list(x.path)))[0]
            raise ReviewError(f"Record {index} schema error: {err.message}")
        rid = row["record_id"]
        if rid in known:
            raise ReviewError(f"Duplicate record_id: {rid}")
        known[rid] = row
        if row["taxonomy_version"] != taxonomy["taxonomy_version"]:
            raise ReviewError(f"{rid}: taxonomy_version mismatch")
        if row["metric_contract_version"] != metrics["contract_version"]:
            raise ReviewError(f"{rid}: metric_contract_version mismatch")
        codes = row["error_codes"]
        if row["primary_error"] not in codes:
            raise ReviewError(f"{rid}: primary_error must appear in error_codes")
        unknown = set(codes) - set(codebook)
        if unknown:
            raise ReviewError(f"{rid}: unknown taxonomy code(s) {sorted(unknown)}")
        metric_id = row["metric_id"]
        if metric_id is not None and metric_id not in metric_ids:
            raise ReviewError(f"{rid}: unknown EVAL-001 metric_id {metric_id}")
        if row["gold_status"] in {"missing_annotation", "illegible_unscorable", "adjudication_pending"}:
            allowed_layers = {"evaluation_integrity", "uncertainty", "expert_evaluation"}
            if any(codebook[k]["layer"] not in allowed_layers for k in codes):
                raise ReviewError(f"{rid}: content-reading error cannot be confirmed without scorable gold")
        if row["sample_scope"] == "sealed_aggregate" and row["score_status"] == "scored":
            # A sanctioned sealed scorer might later exist, but not under EVAL-005.
            raise ReviewError(f"{rid}: sealed items cannot claim independently scored reading")
        if row["attribution_status"] == "adjudicated" and row["exposure_status"] == "unknown":
            raise ReviewError(f"{rid}: adjudicated error must record exposure assessment")
        if any(not row["evidence_refs"] for code in codes if codebook[code]["requires_evidence"] and row["attribution_status"] == "adjudicated"):
            raise ReviewError(f"{rid}: adjudicated error requires evidence")
        if rid in row.get("upstream_record_ids", []):
            raise ReviewError(f"{rid}: record cannot be its own upstream cause")

    edges: dict[str, list[str]] = {}
    for rid, row in known.items():
        edges[rid] = row.get("upstream_record_ids", [])
        for parent_id in edges[rid]:
            parent = known.get(parent_id)
            if parent is None:
                raise ReviewError(f"{rid}: unknown upstream_record_id {parent_id}")
            identity = ("run_id", "model_id", "dataset_version", "split_id", "document_id")
            if any(parent[field] != row[field] for field in identity):
                raise ReviewError(f"{rid}: cross-run/document causal relationship is prohibited")
    visited: set[str] = set()
    active: set[str] = set()
    def visit(rid: str) -> None:
        if rid in active:
            raise ReviewError(f"Cyclic error-propagation links involving {rid}")
        if rid in visited:
            return
        active.add(rid)
        for parent_id in edges[rid]:
            visit(parent_id)
        active.remove(rid)
        visited.add(rid)
    for rid in known:
        visit(rid)


def summarize(rows: list[dict[str, Any]], taxonomy: dict[str, Any],
              *, publication: str = "public") -> dict[str, Any]:
    if publication not in {"public", "internal"}:
        raise ReviewError("Publication must be public or internal")
    codes = {x["code"]: x for x in taxonomy["error_codes"]}
    # Public summaries never contain even aggregate statistics from sealed material.
    visible = [r for r in rows if publication == "internal" or r["sample_scope"] != "sealed_aggregate"]
    confirmed = [r for r in visible
                 if r["attribution_status"] == "adjudicated"
                 and r["score_status"] == "scored"
                 and r["exposure_status"] == "clean"]
    count_primary = Counter(r["primary_error"] for r in confirmed)
    count_secondary = Counter(code for r in confirmed for code in r["error_codes"])
    stage_count = Counter(codes[r["primary_error"]]["layer"] for r in confirmed)
    severity_count = Counter(r["severity"] for r in confirmed)
    strata_docs: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for r in confirmed:
        for field in ("source", "scribe", "period", "material", "genre", "damage"):
            value = r["strata"].get(field)
            if value:
                strata_docs[field][value].add(r["document_id"])
    by_stratum = {
        field: {value: len(doc_ids) for value, doc_ids in sorted(groups.items())}
        for field, groups in sorted(strata_docs.items())
    }
    def sorted_counts(counter: Counter[str]) -> dict[str, int]:
        return {key: counter[key] for key in sorted(counter)}
    return {
        "taxonomy_version": taxonomy["taxonomy_version"],
        "publication": publication,
        "review_records": len(visible),
        "adjudicated_clean_scored_errors": len(confirmed),
        "affected_document_count": len({r["document_id"] for r in confirmed}),
        "review_status_counts": sorted_counts(Counter(r["attribution_status"] for r in visible)),
        "scoring_status_counts": sorted_counts(Counter(r["score_status"] for r in visible)),
        "exposure_status_counts": sorted_counts(Counter(r["exposure_status"] for r in visible)),
        "gold_status_counts": sorted_counts(Counter(r["gold_status"] for r in visible)),
        "primary_error_counts": sorted_counts(count_primary),
        "all_code_occurrence_counts": sorted_counts(count_secondary),
        "primary_layer_counts": sorted_counts(stage_count),
        "severity_counts": sorted_counts(severity_count),
        "affected_document_counts_by_stratum": by_stratum,
        "rates_computable": False,
        "denominator_warning": "Error-review events alone are not a denominator for error rates, accuracy, or model rankings. Join a frozen scored-item/metric universe before computing any rate.",
        "metric_warning": "Counts are diagnostic observations, not EVAL-001 metric scores or a composite reading-capability score.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and summarize structured Hieratic error-review events")
    parser.add_argument("command", choices=["validate", "summarize"])
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--publication", choices=["public", "internal"], default="public")
    args = parser.parse_args(argv)
    try:
        taxonomy, schema, metrics = load_contracts()
        rows = read_reviews(args.input)
        validate_reviews(rows, taxonomy, schema, metrics)
        if args.command == "summarize":
            print(json.dumps(summarize(rows, taxonomy, publication=args.publication), indent=2, sort_keys=True))
        else:
            print(f"PASS: {len(rows)} structured review records valid; taxonomy {taxonomy['taxonomy_version']}")
        return 0
    except (ReviewError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
