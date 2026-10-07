"""EVAL-006: static sealed-evaluation preregistration and publication gate.

Reads *metadata only*. Never reads hidden gold, manuscript images, model
responses or publicizes private result values. This is necessary contract
validation, not proof that external evidence is genuine or research accepted.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = ROOT / "eval/sealed/protocol.yaml"
SCHEMA_PATH = ROOT / "schemas/sealed_eval.schema.json"
METRICS_PATH = ROOT / "eval/metric_contract.yaml"
TAXONOMY_PATH = ROOT / "eval/analysis/error_taxonomy.yaml"
SPLITS_PATH = ROOT / "eval/splits/profiles.yaml"
BENCHMARK_PATH = ROOT / "eval/benchmarks/hieraticbench/manifest.yaml"
REQUIRED_HASHES = (
    "dataset_manifest_sha256", "split_manifest_sha256", "overlap_review_sha256",
    "rights_review_sha256", "accepted_gold_manifest_sha256", "model_checkpoint_sha256",
    "model_config_sha256", "inference_code_commit", "prompt_bundle_sha256",
    "metric_contract_sha256", "normalization_profiles_sha256", "scorer_sha256",
    "analysis_plan_sha256", "attempt_manifest_sha256", "environment_lock_sha256",
)
FREEZE_STATES = {"frozen", "scored", "adjudicated", "publishable"}
SCORED_STATES = {"scored", "adjudicated", "publishable"}
PUBLIC_ARTIFACTS = {
    "protocol_freeze", "training_exclusion_report", "rights_clearance",
    "overlap_clearance", "prediction_receipt", "score_reproduction",
    "group_uncertainty", "blinded_adjudication", "contamination_check",
    "public_report",
}


class SealError(ValueError):
    pass


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.suffix.lower() == ".json" else yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
        raise SealError(f"{path}: cannot load structured metadata: {exc}") from exc


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def time_of(value: str) -> datetime:
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("time zone missing")
    return d


def validate_protocol(protocol: Any, *, metrics: Any = None,
                      taxonomy: Any = None, splits: Any = None,
                      benchmark: Any = None) -> list[str]:
    errs: list[str] = []
    if not isinstance(protocol, dict):
        return ["sealed policy must be a mapping"]
    if protocol.get("protocol_version") != "1.0.0" or protocol.get("protocol_state") != "frozen_policy":
        errs.append("protocol must be frozen policy version 1.0.0")
    metrics = load(METRICS_PATH) if metrics is None else metrics
    taxonomy = load(TAXONOMY_PATH) if taxonomy is None else taxonomy
    splits = load(SPLITS_PATH) if splits is None else splits
    benchmark = load(BENCHMARK_PATH) if benchmark is None else benchmark
    expected_versions = {
        "metric_contract_version": metrics.get("contract_version"),
        "error_taxonomy_version": taxonomy.get("taxonomy_version"),
        "split_profiles_version": splits.get("profiles_version"),
        "external_benchmark_commit": benchmark.get("benchmark", {}).get("pinned_commit"),
    }
    for k, expected in expected_versions.items():
        if protocol.get("source_authorities", {}).get(k) != expected:
            errs.append(f"source authority mismatch: {k} expected {expected}")
    freeze = protocol.get("freeze_requirements", {})
    if not freeze.get("pre_result_freeze") or not set(REQUIRED_HASHES) <= set(freeze.get("immutable_fields", [])):
        errs.append("policy fails to require every immutable preregistration field")
    roles = protocol.get("roles", {}).get("separation_rules", [])
    for rule in ("training_operator != sealed_custodian","training_operator != blind_scorer","training_operator != release_authority","sealed_custodian != release_authority"):
        if rule not in roles:
            errs.append(f"missing independence rule: {rule}")
    scoring = protocol.get("scoring", {})
    if scoring.get("no_composite_primary") is not True or scoring.get("no_adaptive_normalization") is not True:
        errs.append("policy must prohibit composite-primary/adaptive normalization")
    if scoring.get("bootstrap_resamples", 0) < 2000 or scoring.get("uncertainty_group") != "document":
        errs.append("policy must prescribe document-clustered uncertainty")
    if protocol.get("release", {}).get("minimum_independent_approvers", 0) < 2:
        errs.append("policy must demand independent release approvals")
    return errs


def validate_release(record: Any, schema: dict[str, Any],
                     protocol: dict[str, Any], *, check_local_hashes: bool = True) -> list[str]:
    errs = [f"{'.'.join(map(str,e.absolute_path)) or '<root>'}: {e.message}" for e in Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(record)]
    if errs:
        return sorted(errs)
    state = record["state"]
    if record["protocol_version"] != protocol["protocol_version"]:
        errs.append("unregistered protocol version")
    if record["protocol_sha256"] is not None and check_local_hashes and record["protocol_sha256"] != sha256(PROTOCOL_PATH):
        errs.append("protocol SHA-256 mismatch: version or content changed after preregistration")
    roles = record["roles"]
    operator, custodian, scorer = roles["training_operator"],roles["sealed_custodian"],roles["blind_scorer"]
    approvals = roles["release_authorities"]
    if len(approvals) != len(set(approvals)):
        errs.append("duplicate release authority")
    if state in FREEZE_STATES | {"blocked","withdrawn"}:
        if not operator or not custodian or not scorer or operator == custodian or operator == scorer:
            errs.append("training operator, sealed custodian and blind scorer must be distinct named people")
        if operator in approvals or custodian in approvals:
            errs.append("release authorities cannot be training operator or sealed custodian")
    if state in FREEZE_STATES:
        if record["protocol_sha256"] is None or record["freeze_sha256"] is None or not record["freeze_created_at"]:
            errs.append("frozen evaluation missing immutable policy/freeze hashes or timestamp")
        if any(not record["frozen_inputs"][k] for k in REQUIRED_HASHES):
            errs.append("frozen evaluation missing required immutable input hashes")
        if not record["metric_ids"]:
            errs.append("frozen evaluation requires preregistered metric IDs")
        if check_local_hashes and record["frozen_inputs"]["metric_contract_sha256"] != sha256(METRICS_PATH):
            errs.append("metric contract SHA-256 differs from approved frozen version")
        allowed_metrics = {m["id"] for m in load(METRICS_PATH)["metrics"]}
        if not set(record["metric_ids"]) <= allowed_metrics:
            errs.append("frozen evaluation includes unknown metric IDs")
        if record["rights"]["status"] != "cleared" or not record["rights"]["reviewer_id"] or not record["rights"]["evidence_ref"]:
            errs.append("sealed corpus rights clearance absent or unreviewed")
        if record["overlap"]["status"] != "cleared" or not record["overlap"]["roster_sha256"] or record["overlap"]["unresolved_candidates"] != 0 or not record["overlap"]["reviewer_id"] or not record["overlap"]["evidence_ref"]:
            errs.append("benchmark/document overlap review incomplete")
        if record["first_sealed_access_at"] and record["freeze_created_at"]:
            try:
                if time_of(record["freeze_created_at"]) > time_of(record["first_sealed_access_at"]):
                    errs.append("protocol frozen after first sealed access (adaptive-test leakage)")
            except ValueError:
                errs.append("invalid or timezone-naive freeze/first-access time")
        elif not record["freeze_created_at"]:
            errs.append("frozen evaluation missing freeze event")
    if state in SCORED_STATES:
        a=record["attempts"]
        if a["expected"] <= 0 or a["received"] != a["expected"]:
            errs.append("incomplete predictions/attempts or zero denominator; failures must not be dropped")
        if a["failed"]+a["abstained"]+a["excluded_unscorable"]>a["received"]:
            errs.append("failure/abstention/unscorable counts exceed attempts")
        scoring=record["scoring"]
        if scoring["status"] not in {"scored","independently_reproduced"}:
            errs.append("evaluation has no scored prediction archive")
        for key in ("scorer_sha256","prediction_archive_sha256","score_archive_sha256"):
            if scoring[key] is None:
                errs.append(f"missing immutable scoring artifact {key}")
        if scoring["scorer_sha256"]!=record["frozen_inputs"]["scorer_sha256"]:
            errs.append("scoring implementation differs from preregistered scorer")
        if not set(scoring["attempted_metric_ids"]) <= set(record["metric_ids"]):
            errs.append("post-hoc metric addition is forbidden")
        if not scoring["official_external_metric_separate"]:
            errs.append("upstream official and project metrics must not be conflated")
        if record["contamination"]["status"]!="none_detected":
            errs.append("contamination uncertain or confirmed; scores must be blocked pending adjudication")
        if not record["first_sealed_access_at"]:
            errs.append("scored evaluation missing first sealed access timestamp")
    if state in {"adjudicated","publishable"}:
        adjud=record["adjudication"]
        if adjud["status"]!="complete" or not adjud["blinded_to_model"] or not adjud["reviewer_id"] or not adjud["evidence_ref"] or adjud["unresolved_gold_count"]!=0:
            errs.append("gold/expert adjudication incomplete or not blind")
        if adjud["reviewer_id"] in {operator,custodian}:
            errs.append("expert adjudicator must not be training operator or sealed custodian")
    if state=="publishable":
        scoring=record["scoring"]
        if scoring["status"]!="independently_reproduced" or not scoring["document_macro_report_sha256"] or not scoring["bootstrap_report_sha256"]:
            errs.append("publishable results require independent scoring, document macro and clustered uncertainty")
        if len(approvals)<2:
            errs.append("at least two separate independent release authorities required")
        approved={a["reviewer_id"] for a in record["approvals"] if a["approved"]}
        if len(approved & set(approvals))<2 or any(a in {operator,custodian,scorer,record["adjudication"]["reviewer_id"]} for a in approved):
            errs.append("missing independent release approval or reviewer role conflict")
        artifact_roles={a["role"] for a in record["release_artifacts"]}
        if not PUBLIC_ARTIFACTS<=artifact_roles:
            errs.append("incomplete provenance/report artifacts for release")
        if record["contamination"]["incidents"]:
            errs.append("contamination incidents require public resolution and a new independent sealed release decision")
    if record["contamination"]["status"] in {"confirmed","suspected"} and state not in {"blocked","withdrawn","draft"}:
        errs.append("suspected/confirmed contamination cannot proceed through evaluation or release")
    return errs


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="Validate metadata-only sealed evaluation policy/release gates")
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("validate-protocol")
    r=sub.add_parser("validate-release")
    r.add_argument("--input",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        p=load(PROTOCOL_PATH)
        errors=validate_protocol(p)
        if args.command=="validate-release" and not errors:
            schema=load(SCHEMA_PATH)
            errors=validate_release(load(args.input),schema,p)
        if errors:
            for e in errors:print(f"FAIL: {e}",file=sys.stderr)
            return 1
        print(f"PASS: {args.command} integrity constraints; no raw sealed data accessed")
        return 0
    except (SealError,OSError,KeyError,TypeError,ValueError) as exc:
        print(f"FAIL: {exc}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
