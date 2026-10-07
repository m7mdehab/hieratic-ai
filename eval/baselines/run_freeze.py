"""Offline EVAL-003 per-model preregistration and rendered-prompt provenance gate.

Checks exact permitted public item/rung universe, *actual* rendered prompt
and image bytes kept in an external evaluation-only vault, frozen hashes,
suite's approval declarations, provider/config identities, and official scorer
source. Does not run models, compute scores, access gold, or prove a human
reviewer actually granted rights/spend approval.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from eval.baselines import baselinectl as base
from eval.baselines import public_freeze
from eval.benchmarks.hieraticbench import adapter

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "eval/baselines/run_freeze.schema.json"
DRAFT = ROOT / "eval/baselines/examples/run-freeze.draft.synthetic.json"
PINNED = base.PINNED_BENCHMARK_SHA
PROMPTS = "bench/src/prompts.ts"
SCORER = "bench/src/score.ts"
REQUIRED_ROW = {
    "item_id", "rung", "sample_index", "model_key",
    "prompt_path", "prompt_sha256", "image_path", "image_sha256",
}
REQUIRED_COUNTS = {"identify": 116, "signs": 150}
HASH_FIELDS = (
    "official_prompt_source_sha256", "public_item_manifest_sha256",
    "prompt_attempts_manifest_sha256", "model_settings_sha256",
    "inference_runtime_sha256", "scorer_source_sha256",
    "metric_contract_sha256",
)


class FreezeError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    """Stream hashes so large originals do not exhaust CI/runtime memory."""
    dig = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            dig.update(chunk)
    return dig.hexdigest()


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.suffix.lower()==".json" else yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError, yaml.YAMLError) as exc:
        raise FreezeError(f"Cannot open structured metadata {path}: {exc}") from exc


def _external_directory(path: Path, label: str) -> Path:
    resolved=path.resolve()
    if path.is_symlink() or not resolved.is_dir() or resolved==ROOT.resolve() or resolved.is_relative_to(ROOT.resolve()):
        raise FreezeError(f"{label} must be a real private directory outside the public project")
    return resolved


def _external_file(path: Path, label: str) -> Path:
    resolved=path.resolve()
    if not resolved.is_file() or resolved.is_relative_to(ROOT.resolve()):
        raise FreezeError(f"{label} must be a real file outside the public project")
    return resolved


def _vault_file(vault: Path, value: str, label: str, *, max_bytes: int) -> Path:
    rel=Path(value)
    if rel.is_absolute() or not value or ".." in rel.parts:
        raise FreezeError(f"{label}: path escapes external evidence vault")
    target=(vault / rel).resolve()
    if not target.is_relative_to(vault) or not target.is_file():
        raise FreezeError(f"{label}: missing, escaped or symlinked outside vault")
    if target.stat().st_size<1 or target.stat().st_size>max_bytes:
        raise FreezeError(f"{label}: unexpectedly empty/oversized evidence blob")
    return target


def validate_draft(freeze: Any) -> list[str]:
    schema=_read(SCHEMA)
    errors=[f"{'.'.join(map(str,e.absolute_path)) or '<root>'}: {e.message}"
            for e in Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(freeze)]
    if errors:
        return sorted(errors)
    if freeze["official_benchmark_commit"]!=PINNED:
        errors.append("benchmark revision differs from EVAL-002 pinned commit")
    if freeze["state"]=="draft":
        if freeze["approval"]["approved"]:
            errors.append("draft may not claim approved or execution-ready")
        if freeze["budget_cap_usd"] is not None:
            errors.append("draft cannot assign an unapproved budget cap")
    return errors


def _clock(value: str) -> datetime:
    d=datetime.fromisoformat(value.replace("Z","+00:00"))
    if not d.tzinfo:
        raise ValueError("timezone missing")
    return d


def validate_locked(
    freeze: dict[str,Any], suite: dict[str,Any], *,
    items_path: Path, attempts_path: Path, vault_path: Path,
    upstream_checkout: Path, actual_approval_confirmed: bool = False,
) -> dict[str,Any]:
    errors=validate_draft(freeze)
    if errors:
        raise FreezeError("; ".join(errors))
    if freeze["state"]!="locked":
        raise FreezeError("Not a locked run: draft metadata cannot authorize inference")
    if suite["status"]!="execution_ready":
        raise FreezeError("Suite must have separately approved execution_ready state")
    suite_schema=_read(base.SUITE_SCHEMA)
    errors=base.validate_suite(suite,suite_schema)
    if errors:
        raise FreezeError("Suite is not executable: "+"; ".join(errors))
    if not actual_approval_confirmed:
        raise FreezeError("Separate human user authorization must be checked externally; metadata booleans are not consent")
    # Every declared config must remain tethered to the run's exact frozen suite.
    if freeze["suite_id"]!=suite["suite_id"]:
        raise FreezeError("Run targets a different suite ID")
    model=next((x for x in suite["models"] if x["key"]==freeze["model_key"]),None)
    if model is None:
        raise FreezeError("Frozen model key not present in approved suite")
    if freeze["provider_model_id"]!=model["provider_model_id"] or freeze["provider_route"]!=model["api_route"] or not freeze["model_checkpoint_or_version"]:
        raise FreezeError("Provider model/version or route mismatch")
    if freeze["samples_per_item"]!=suite["protocol"]["samples_per_item"]:
        raise FreezeError("Frozen sampling plan disagrees with suite")
    if freeze["budget_cap_usd"] is None or freeze["budget_cap_usd"]>suite["execution_gate"]["max_total_spend_usd"]:
        raise FreezeError("Run budget exceeds independently authorized suite cap")
    approval=freeze["approval"]
    if not (approval["approved"] and approval["approved_by"] and approval["approved_at"] and approval["evidence_ref"]):
        raise FreezeError("Missing named independent spend/terms approval and evidence")
    try:
        _clock(approval["approved_at"])
    except ValueError as exc:
        raise FreezeError("Spend approval lacks timezone-aware timestamp") from exc
    rights=freeze["benchmark_rights"]
    if not (rights["image_rights_reviewed"] and rights["item_overlap_reviewed"] and
            rights["rights_review_ref"] and rights["overlap_review_ref"]):
        raise FreezeError("Unreviewed item-level benchmark use/overlap must block inference")
    archive=freeze["archive"]
    if not (archive["external_private_store"] and archive["access_restricted"] and
            archive["append_only"] and archive["encryption_at_rest"] and
            archive["raw_response_retention"]=="private"):
        raise FreezeError("Unsecured private raw-output archive")
    if any(freeze[name] is None for name in HASH_FIELDS) or not freeze["inference_code_commit"]:
        raise FreezeError("Missing immutable model/config/prompt/scorer/inference hashes")
    _external_file(items_path,"item manifest")
    _external_file(attempts_path,"rendered-attempt manifest")
    vault=_external_directory(vault_path,"input vault")
    _external_directory(upstream_checkout,"pinned benchmark checkout")
    if sha256_file(items_path)!=freeze["public_item_manifest_sha256"] or sha256_file(items_path)!=suite["official_benchmark"]["item_manifest_sha256"]:
        raise FreezeError("Public item inventory bytes do not match frozen suite and run")
    if sha256_file(attempts_path)!=freeze["prompt_attempts_manifest_sha256"]:
        raise FreezeError("Rendered prompt/attempt receipt bytes changed since freeze")
    if sha256_file(base.ROOT/"eval/metric_contract.yaml")!=freeze["metric_contract_sha256"]:
        raise FreezeError("Metric contract differs from accepted EVAL-001")
    upstream=adapter.load_manifest()
    adapter.assert_pinned_checkout(upstream_checkout,upstream)
    upstream_items=adapter.inspect_items(upstream_checkout,upstream)
    rows=public_freeze.safe_public_pairs(upstream_items)
    expected_bytes=public_freeze.manifest_bytes(upstream_items)
    if items_path.read_bytes()!=expected_bytes:
        raise FreezeError("Public item/rung IDs differ from frozen upstream EVAL-002 inventory")
    if sha256_file(upstream_checkout/PROMPTS)!=freeze["official_prompt_source_sha256"]:
        raise FreezeError("Official prompt-source content differs from preregistered version")
    if sha256_file(upstream_checkout/SCORER)!=freeze["scorer_source_sha256"]:
        raise FreezeError("Official scoring-source content differs from preregistered version")
    expected={(row["item_id"],row["rung"],sample) for row in rows
              for sample in range(freeze["samples_per_item"])}
    if freeze["attempts_planned"]!=len(expected):
        raise FreezeError("Frozen attempt count is incomplete or mismatched")
    found=set()
    images={}
    per_rung=Counter()
    with attempts_path.open(encoding="utf-8") as handle:
        for n,line in enumerate(handle,1):
            if not line.strip():
                raise FreezeError(f"Attempt manifest line {n}: blank lines forbidden")
            try:
                row=json.loads(line)
            except json.JSONDecodeError as exc:
                raise FreezeError(f"Attempt manifest line {n}: invalid JSON") from exc
            if not isinstance(row,dict) or set(row)!=REQUIRED_ROW:
                raise FreezeError(f"Attempt manifest line {n}: expected exactly the 8 metadata fields, never gold/responses")
            key=(row["item_id"],row["rung"],row["sample_index"])
            if type(row["sample_index"]) is not int or key not in expected or key in found:
                raise FreezeError(f"Attempt manifest line {n}: duplicate/unrequested/missing sample key")
            if row["model_key"]!=freeze["model_key"]:
                raise FreezeError(f"Attempt manifest line {n}: wrong provider/model key")
            for label in ("prompt_sha256","image_sha256"):
                val=row[label]
                if not isinstance(val,str) or len(val)!=64 or any(c not in "0123456789abcdef" for c in val):
                    raise FreezeError(f"Attempt manifest line {n}: invalid {label}")
            p=_vault_file(vault,row["prompt_path"],"rendered prompt",max_bytes=131072)
            img=_vault_file(vault,row["image_path"],"evaluation-only image",max_bytes=200_000_000)
            if sha256_file(p)!=row["prompt_sha256"] or sha256_file(img)!=row["image_sha256"]:
                raise FreezeError(f"Attempt manifest line {n}: actual prompt/image bytes mismatch frozen digests")
            image_key=(row["item_id"],row["rung"])
            if image_key in images and images[image_key]!=row["image_sha256"]:
                raise FreezeError(f"Attempt manifest line {n}: image changes across repeated attempts")
            images[image_key]=row["image_sha256"]
            found.add(key)
            per_rung[row["rung"]]+=1
    if found!=expected:
        raise FreezeError(f"Unrecorded attempts in frozen prompt schedule: {len(found)} of {len(expected)}")
    return {
        "scope":"metadata_and_bytes_integrity_only_no_model_calls",
        "run_id":freeze["run_id"],
        "model_key":freeze["model_key"],
        "public_item_rungs":len(rows),
        "planned_attempts":len(found),
        "attempts_by_rung":dict(sorted(per_rung.items())),
        "rights_status":"requires_independent_human_evidence_inspection",
        "official_score_reproduced":False,
        "fresh_model_result":False,
        "trained_model":False,
    }


def main(argv: list[str]|None=None) -> int:
    p=argparse.ArgumentParser(description="EVAL-003: metadata-only preregistration / rendered-input audit")
    sub=p.add_subparsers(dest="command",required=True)
    d=sub.add_parser("validate-draft")
    d.add_argument("--record",type=Path,default=DRAFT)
    l=sub.add_parser("verify-locked")
    l.add_argument("--record",type=Path,required=True)
    l.add_argument("--suite",type=Path,required=True)
    l.add_argument("--items",type=Path,required=True)
    l.add_argument("--attempts",type=Path,required=True)
    l.add_argument("--vault",type=Path,required=True)
    l.add_argument("--upstream-checkout",type=Path,required=True)
    # Must pass via separate human authorization; intentionally no toggle to bypass
    # real-world approval within a repo script. Future operator uses imported
    # validate_locked(... actual_approval_confirmed=True) only after signed review.
    args=p.parse_args(argv)
    try:
        record=_read(args.record)
        if args.command=="validate-draft":
            errors=validate_draft(record)
            if errors:
                raise FreezeError("; ".join(errors))
            print("PASS: draft is non-executable metadata; zero provider inference")
            return 0
        validate_locked(record,_read(args.suite),items_path=args.items,attempts_path=args.attempts,
                        vault_path=args.vault,upstream_checkout=args.upstream_checkout)
        return 0
    except (FreezeError,OSError,ValueError,KeyError,TypeError,
            adapter.BenchmarkAuditError) as exc:
        print(f"REFUSED: {exc}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
