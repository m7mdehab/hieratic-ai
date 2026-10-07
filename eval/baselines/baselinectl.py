"""Untuned frontier baseline suite: no network or model inference.

Provides a strict *preflight* and read-only audit of private raw-response archives.
The upstream HieraticBench TypeScript scorer remains authoritative for official
scores. This module never opens image files, benchmark gold or API credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = ROOT / "eval/baselines/suite.yaml"
SUITE_SCHEMA = ROOT / "eval/baselines/suite.schema.json"
PINNED_BENCHMARK_SHA = "d587dc990013f18007f1e7a8f56f96ff2f7127e2"


class BaselineError(ValueError):
    pass


def load_data(path: Path) -> Any:
    try:
        if path.suffix.lower() == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise BaselineError(f"{path}: invalid or missing structured file: {exc}") from exc


def digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise BaselineError(f"Cannot read artifact for SHA-256 verification: {path}") from exc


def validate_suite(suite: Any, schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = [f"{'.'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
              for e in sorted(validator.iter_errors(suite), key=lambda e: str(list(e.absolute_path)))]
    if errors:
        return errors
    bench = suite["official_benchmark"]
    prompts = suite["official_prompts"]
    if bench["commit"] != PINNED_BENCHMARK_SHA or prompts["commit"] != PINNED_BENCHMARK_SHA:
        errors.append("Benchmark and prompt revisions must use the accepted EVAL-002 pinned commit")
    keys = [m["key"] for m in suite["models"]]
    if len(set(keys)) != len(keys):
        errors.append("Model candidate keys must be unique")
    if suite["status"] in {"execution_ready", "completed"}:
        for key, value in suite["execution_gate"].items():
            if key == "max_total_spend_usd":
                if value is None:
                    errors.append("No approved positive spending cap exists")
            elif value is not True:
                errors.append(f"Execution gate not met: {key}")
        if bench["item_manifest_sha256"] is None:
            errors.append("Official public-only item manifest must be frozen before execution")
        if prompts["exact_prompt_bundle_sha256"] is None:
            errors.append("Exact official prompt bundle SHA-256 must be pinned before execution")
        for model in suite["models"]:
            if not model["provider_model_id"] or not model["api_route"] or model["effort"] == "verify_provider_support":
                errors.append(f"Model {model['key']} needs exact provider ID, API route and validated effort")
    return errors


def parse_item_manifest(path: Path, suite: dict[str, Any],
                        upstream_items: dict[str, dict[str, Any]] | None = None) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    records: list[tuple[str, str]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise BaselineError(f"Cannot read item manifest: {exc}") from exc
    for line_no, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BaselineError(f"Item manifest line {line_no}: invalid JSON: {exc}") from exc
        if not isinstance(record, dict) or set(record) != {"item_id", "rung", "split"}:
            raise BaselineError(f"Item manifest line {line_no}: expected item_id, rung and split only")
        item_id, rung, split = record["item_id"], record["rung"], record["split"]
        if not isinstance(item_id, str) or not item_id or not isinstance(rung, str):
            raise BaselineError(f"Item manifest line {line_no}: invalid item_id/rung")
        if split != "public" or rung not in suite["official_benchmark"]["permitted_rungs"]:
            raise BaselineError(f"Item manifest line {line_no}: sealed or out-of-contract item")
        key = (item_id, rung)
        if key in seen:
            raise BaselineError(f"Item manifest line {line_no}: repeated item/rung {key}")
        if upstream_items is not None:
            official = upstream_items.get(item_id)
            if official is None or official["split"] != "public" or rung not in official["rungs"]:
                raise BaselineError(f"Item manifest line {line_no}: not an eligible public item at pinned upstream revision")
        seen.add(key)
        records.append(key)
    if not records:
        raise BaselineError("A baseline item manifest must contain at least one eligible public item")
    return records


def verify_capture(suite: dict[str, Any], item_manifest: Path, capture: Path,
                   receipt: dict[str, Any], upstream_items: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """Check raw-response capture integrity; does NOT compute model scores."""
    # Prevent accidental tracking or exposure of raw responses, including sealed
    # response text that is not safe in the public repository.
    if capture.resolve().is_relative_to(ROOT.resolve()):
        raise BaselineError("Raw model response archive must live outside the public repository")
    if suite["status"] not in {"execution_ready", "completed"}:
        raise BaselineError("Suite execution gate must be satisfied before captures can be audited")
    models = {x["key"]: x for x in suite["models"]}
    expected_keys = {"schema_version","suite_id","model_key","provider_model_id",
                     "raw_capture_sha256","item_manifest_sha256","prompt_sha256","records_expected","status"}
    if not isinstance(receipt, dict) or set(receipt) != expected_keys:
        raise BaselineError("Capture receipt is missing required version/provenance fields")
    if receipt["schema_version"] != "1.0.0" or receipt["status"] != "captured":
        raise BaselineError("Invalid capture receipt status/version; this stage never certifies scores")
    key = receipt["model_key"]
    model = models.get(key)
    if not model or receipt["provider_model_id"] != model["provider_model_id"]:
        raise BaselineError("Receipt model/provider identity differs from frozen suite")
    if receipt["suite_id"] != suite["suite_id"]:
        raise BaselineError("Capture receipt belongs to another suite")
    if receipt["item_manifest_sha256"] != digest(item_manifest) or receipt["item_manifest_sha256"] != suite["official_benchmark"]["item_manifest_sha256"]:
        raise BaselineError("Item manifest hash differs from frozen suite or receipt")
    if receipt["prompt_sha256"] != suite["official_prompts"]["exact_prompt_bundle_sha256"]:
        raise BaselineError("Response prompt SHA differs from accepted frozen prompt bundle")
    if receipt["raw_capture_sha256"] != digest(capture):
        raise BaselineError("Raw response capture SHA-256 does not match receipt")

    item_keys = parse_item_manifest(item_manifest, suite, upstream_items)
    expected = {(item,rung,n) for item,rung in item_keys for n in range(suite["protocol"]["samples_per_item"])}
    if receipt["records_expected"] != len(expected):
        raise BaselineError("Receipt number of attempts does not cover frozen item/rung/sampling universe")
    found: set[tuple[str,str,int]] = set()
    errors = 0
    for line_no, line in enumerate(capture.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BaselineError(f"Raw capture line {line_no}: invalid JSON") from exc
        required = {"item_id","rung","sample_index","provider_model_id","prompt_sha256",
                    "status","response_text","provider_response_id","timestamp"}
        if not isinstance(record, dict) or set(record) != required:
            raise BaselineError(f"Raw capture line {line_no}: unexpected/missing fields")
        if type(record["sample_index"]) is not int:
            raise BaselineError(f"Raw capture line {line_no}: sample index must be integer")
        token = record["item_id"], record["rung"], record["sample_index"]
        if token not in expected or token in found:
            raise BaselineError(f"Raw capture line {line_no}: duplicate or unrequested item/rung/attempt")
        if record["provider_model_id"] != model["provider_model_id"] or record["prompt_sha256"] != receipt["prompt_sha256"]:
            raise BaselineError(f"Raw capture line {line_no}: provider/prompt integrity mismatch")
        if record["status"] not in {"ok","failed"}:
            raise BaselineError(f"Raw capture line {line_no}: unknown outcome status")
        if not isinstance(record["response_text"], str) or not isinstance(record["timestamp"], str) or not record["timestamp"]:
            raise BaselineError(f"Raw capture line {line_no}: missing raw response/timestamp")
        if record["status"] == "ok":
            if not record["response_text"] or not record["provider_response_id"]:
                raise BaselineError(f"Raw capture line {line_no}: successful response missing raw text/receipt")
        else:
            errors += 1
        found.add(token)
    if found != expected:
        raise BaselineError(f"Incomplete capture: {len(found)} of {len(expected)} attempts preserved; no failed calls may be dropped")
    return {
        "scope": "raw_capture_integrity_only_not_scoring",
        "model_key": key, "captured_attempts": len(found),
        "failed_attempts_preserved": errors,
        "item_rung_count": len(item_keys),
        "scoring_reproduced": False,
        "fresh_model_results_validated": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only frontier baseline preflight and capture-integrity audit")
    sub = parser.add_subparsers(dest="command", required=True)
    v=sub.add_parser("validate-suite")
    v.add_argument("--suite",type=Path,default=DEFAULT_SUITE)
    p=sub.add_parser("preflight")
    p.add_argument("--suite",type=Path,default=DEFAULT_SUITE)
    for name in ("audit-capture",):
        a=sub.add_parser(name)
        a.add_argument("--suite",type=Path,default=DEFAULT_SUITE)
        a.add_argument("--items",type=Path,required=True)
        a.add_argument("--capture",type=Path,required=True)
        a.add_argument("--receipt",type=Path,required=True)
        a.add_argument("--upstream-checkout",type=Path)
    args=parser.parse_args(argv)
    try:
        suite=load_data(args.suite)
        schema=json.loads(SUITE_SCHEMA.read_text(encoding="utf-8"))
        errors=validate_suite(suite,schema)
        if errors:
            raise BaselineError("; ".join(errors))
        if args.command=="validate-suite":
            print(f"PASS: suite schema valid; status={suite['status']} (NOT evidence of model inference)")
            return 0
        if args.command=="preflight":
            if suite["status"]=="planning":
                raise BaselineError("Execution blocked: suite is planning-only; provider IDs, frozen public item set, prompt hash, approved budget, external artifact store and credentials required")
            print("PASS: declared preflight fields complete; independently verify permissions/credentials before spending")
            return 0
        upstream=None
        if args.upstream_checkout:
            from eval.benchmarks.hieraticbench.adapter import assert_pinned_checkout,inspect_items,load_manifest
            upstream_manifest=load_manifest()
            assert_pinned_checkout(args.upstream_checkout,upstream_manifest)
            upstream=inspect_items(args.upstream_checkout,upstream_manifest)
        report=verify_capture(suite,args.items,args.capture,load_data(args.receipt),upstream)
        print("PASS: raw archive integrity only, no scoring, no model calls and no raw text exported")
        print(json.dumps(report,indent=2,sort_keys=True))
        return 0
    except (BaselineError,OSError,ValueError,KeyError,TypeError) as exc:
        print(f"FAIL: {exc}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
