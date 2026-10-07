"""Cross-layer EVAL-001 x EVAL-006 report audit.

Fail closed on unverifiable denominators, post-hoc score dimensions,
unsupported inference, cherry-picked models and unsupported decipherment
claims. Inputs are redacted aggregate metadata, never source images or gold.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from eval.sealed import protocolctl as seal

SCHEMA=seal.ROOT/"eval/sealed/metric_report.schema.json"


class ReportError(ValueError):
    pass


def check_report(report: Any, schema: dict[str,Any], metrics: dict[str,Any],
                 *, release_record: dict[str,Any] | None = None,
                 release_sha256: str | None = None,
                 check_hashes: bool = True) -> list[str]:
    err=[f"{'.'.join(map(str,e.absolute_path)) or '<root>'}: {e.message}" for e in Draft202012Validator(schema).iter_errors(report)]
    if err:
        return sorted(err)
    known={m["id"]:m for m in metrics["metrics"]}
    if check_hashes:
        if report["metric_contract_sha256"] is not None and report["metric_contract_sha256"]!=seal.sha256(seal.METRICS_PATH):
            err.append("metric contract snapshot SHA-256 differs from accepted EVAL-001")
        if report["sealed_protocol_sha256"] is not None and report["sealed_protocol_sha256"]!=seal.sha256(seal.PROTOCOL_PATH):
            err.append("sealed policy snapshot SHA-256 differs from accepted EVAL-006")
    used=set()
    valid_layers=set()
    for i,row in enumerate(report["metric_rows"]):
        prefix=f"metric_rows[{i}]"
        m=known.get(row["metric_id"])
        if m is None:
            err.append(f"{prefix}: unknown EVAL-001 metric ID")
            continue
        if row["metric_id"] in used:
            err.append(f"{prefix}: duplicated metric identifier risks cherry-picked denominators")
        used.add(row["metric_id"])
        for key,expected in (("layer",m["layer"]),("unit",m["unit"]),("normalization_profile",m["normalization_profile"])):
            if row[key]!=expected:
                err.append(f"{prefix}: {key} mismatches frozen EVAL-001 contract")
        if row["scheduled"] != sum(row[k] for k in ("scored","failed","abstained","excluded_unscorable")):
            err.append(f"{prefix}: category counts do not partition scheduled denominator")
        if row["documents_scored"] > row["scored"]:
            err.append(f"{prefix}: document groups cannot exceed scored observations")
        value=row["value"]
        if row["scored"] == 0 and (value is not None or row["interval"] is not None):
            err.append(f"{prefix}: no scored gold, so no metric value or confidence interval")
        if row["scored"] > 0:
            if value is None or isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
                err.append(f"{prefix}: scored result must be finite nonnegative numeric value")
            elif m["unit"] in {"proportion","reciprocal_rank"} and value>1:
                err.append(f"{prefix}: bounded metric above one")
            else:
                valid_layers.add(m["layer"])
        ci=row["interval"]
        if ci is not None:
            if row["documents_scored"]<2:
                err.append(f"{prefix}: group interval unsupported with fewer than two documents")
            if ci["method"]!="document_bootstrap" or ci["resamples"]<2000 or abs(ci["confidence"]-.95)>1e-9:
                err.append(f"{prefix}: prespecified document bootstrap 2000/95% required")
            if any(not math.isfinite(ci[k]) for k in ("lower","upper")) or ci["lower"]<0 or ci["upper"]<ci["lower"]:
                err.append(f"{prefix}: invalid confidence interval bounds")
            if value is not None and (value<ci["lower"] or value>ci["upper"]):
                err.append(f"{prefix}: point estimate outside declared confidence interval")
            if m["unit"] in {"proportion","reciprocal_rank"} and ci["upper"]>1:
                err.append(f"{prefix}: bounded metric CI above one")
    if "full_pipeline" in report["public_claim_layers"]:
        needed={"script_identification","sign_recognition","sequence_recognition","transliteration","translation"}
        e=report["end_to_end_evidence"]
        if not needed<=valid_layers or not e["trace_sha256"] or not e["expert_review_sha256"] or e["heldout_document_count"]<2:
            err.append("full-pipeline reading claim lacks complete held-out visual-to-linguistic trace and independent expert evidence")
    for claimed in report["public_claim_layers"]:
        if claimed!="full_pipeline" and claimed not in valid_layers:
            err.append(f"public claim {claimed} lacks independently measured task-layer result")
    for i,comp in enumerate(report["comparisons"]):
        if not comp["paired_items_sha256"] or comp["pair_count"]<=0 or comp["doc_groups"]<2 or not comp["uncertainty_ref"]:
            err.append(f"comparisons[{i}]: no verified paired-item universe and group uncertainty")
    if report["report_state"]=="proposed_public":
        if not report["metric_rows"]:
            err.append("cannot publish a report without measured metric rows")
        if not release_record or release_record["state"]!="publishable":
            err.append("public report requires an independently accepted publishable sealed release record")
        else:
            if report["evaluation_id"]!=release_record["evaluation_id"]:
                err.append("release record and metric report evaluation IDs mismatch")
            if report["release_record_sha256"]!=release_sha256:
                err.append("published report does not match immutable release record hash")
            if not used<=set(release_record["metric_ids"]):
                err.append("published report includes metrics not preregistered in sealed release")
            if check_hashes:
                errors=seal.validate_release(release_record,seal.load(seal.SCHEMA_PATH),seal.load(seal.PROTOCOL_PATH))
                if errors:
                    err.append("referenced sealed release record does not pass independent integrity policy")
    return err


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="Validate redacted metric denominator, stage and release claims")
    parser.add_argument("--report",type=Path,required=True)
    parser.add_argument("--release-record",type=Path)
    args=parser.parse_args(argv)
    try:
        r=seal.load(args.report)
        release=seal.load(args.release_record) if args.release_record else None
        sha=seal.sha256(args.release_record) if args.release_record else None
        errors=check_report(r,seal.load(SCHEMA),seal.load(seal.METRICS_PATH),
                            release_record=release,release_sha256=sha)
        if errors:
            for error in errors:print(f"FAIL: {error}",file=sys.stderr)
            return 1
        print("PASS: redacted metric denominators/stage claims internally consistent; scientific review remains required")
        return 0
    except (seal.SealError,ReportError,KeyError,TypeError,ValueError,OSError) as exc:
        print(f"FAIL: {exc}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
