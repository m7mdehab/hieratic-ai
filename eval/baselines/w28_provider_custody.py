"""W28 EVAL-003 provider-event reconciliation and paired-coverage preflight.

The prior run_freeze.audit_original_capture checks private response byte
integrity, NOT whether a commercial provider executed the calls. This module
adds independent event-key reconciliation without falsely promoting log
consistency into provider-authenticated evidence.

All inputs are PRIVATE JSONL/JSON files outside the repository. No network,
provider keys, gold answers, or commercial inference are used.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from typing import Any

from eval.baselines import baselinectl

ROOT = Path(__file__).resolve().parents[2]
VERSION = "eval003-w28-private-provider-custody/1.0.0"
HEX64 = re.compile(r"^[a-f0-9]{64}$")
MAX_FILE_BYTES = 24_000_000
MAX_EVENTS = 3000

class CustodyError(ValueError):
    pass

def _priv(path: Path) -> Path:
    if path.is_symlink() or not path.is_file() or path.resolve().is_relative_to(ROOT.resolve()):
        raise CustodyError("Provider custody file must exist outside public repository and not be a symlink")
    if not 1 <= path.stat().st_size <= MAX_FILE_BYTES:
        raise CustodyError("Provider custody byte cap exceeded")
    return path

def _digest(path: Path) -> str:
    return sha256(_priv(path).read_bytes()).hexdigest()

def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(_priv(path).read_text("utf-8"))
    except (ValueError, UnicodeError, OSError) as exc:
        raise CustodyError("Private structured record unreadable") from exc
    if not isinstance(value, dict):
        raise CustodyError("Structured record must be object")
    return value

def _jsonl(path: Path, required: set[str]) -> list[dict[str, Any]]:
    rows = []
    try:
        with _priv(path).open("r", encoding="utf-8") as source:
            for n, line in enumerate(source,1):
                if not line.strip():
                    raise CustodyError("Blank event row not permitted")
                row=json.loads(line)
                if not isinstance(row,dict) or set(row)!=required:
                    raise CustodyError(f"Private event {n} has unknown or missing fields")
                rows.append(row)
                if len(rows)>MAX_EVENTS:
                    raise CustodyError("Event limit exceeded")
    except (UnicodeError,OSError,json.JSONDecodeError) as exc:
        raise CustodyError("Malformed event JSONL") from exc
    if not rows:
        raise CustodyError("No source event attempts")
    return rows

def _utc(value: str) -> datetime:
    if not isinstance(value,str) or not value.endswith("Z"):
        raise CustodyError("Timestamps require explicit UTC Z")
    try:
        return datetime.fromisoformat(value.replace("Z","+00:00"))
    except (ValueError,TypeError) as exc:
        raise CustodyError("Malformed UTC timestamp") from exc

def _key(row: dict[str,Any]) -> tuple[str,str,int]:
    idx=row["sample_index"]
    if type(idx) is not int or idx<0:
        raise CustodyError("Invalid sample index")
    for field in ("item_id","rung"):
        if not isinstance(row[field],str) or not row[field] or len(row[field])>256:
            raise CustodyError(f"Missing {field}")
    if row["rung"] not in ("identify","signs","transliterate","translate"):
        raise CustodyError("Unregistered evaluation rung")
    return row["item_id"],row["rung"],idx

def audit_private_provider_events(
    attempts_path: Path,
    responses_path: Path,
    export_path: Path,
    attestation_path: Path,
) -> dict[str, Any]:
    """Reconcile all attempts to responses and purported provider account events.

    Provider account export comes from a *different claimed custody source*,
    but hashes and matching IDs do not independently authenticate it. A real
    authorized reviewer must verify account/provider origin and legal scope.
    """
    required_attempt={"item_id","rung","sample_index","prompt_sha256","image_sha256",
                      "model_id","request_config_sha256","requested_at","max_usd"}
    required_response={"item_id","rung","sample_index","model_id","prompt_sha256",
                       "image_sha256","request_config_sha256","status","response_id",
                       "responded_at","response_text","response_sha256"}
    required_event={"provider_event_id","response_id","model_id","created_at",
                    "request_config_sha256","provider_cost_usd","event_status"}
    attempts=_jsonl(attempts_path,required_attempt)
    outputs=_jsonl(responses_path,required_response)
    events=_jsonl(export_path,required_event)
    attest=_read_json(attestation_path)
    fields={"schema_version","run_id","provider","model_id","frozen_source_sha256",
            "attempts_sha256","responses_sha256","account_export_sha256",
            "authorization_state","spend_approved_usd","claimed_export_origin"}
    if set(attest)!=fields or attest["schema_version"]!="1.0.0":
        raise CustodyError("Custody manifest invalid/unrecognized")
    if (attest["authorization_state"] not in ("UNAPPROVED","APPROVED_EXTERNALLY")
            or type(attest["spend_approved_usd"]) not in (int,float)
            or attest["spend_approved_usd"]<0):
        raise CustodyError("Missing bounded financial authorization")
    if not isinstance(attest["run_id"],str) or not attest["run_id"]:
        raise CustodyError("Missing frozen run ID")
    if attest["provider"] not in ("openai","anthropic","google"):
        raise CustodyError("Unknown provider")
    if not isinstance(attest["model_id"],str) or not attest["model_id"]:
        raise CustodyError("Missing declared model")
    for field,path in (("attempts_sha256",attempts_path),("responses_sha256",responses_path),
                       ("account_export_sha256",export_path)):
        if not HEX64.fullmatch(attest[field]) or _digest(path)!=attest[field]:
            raise CustodyError(f"{field}: source bytes drifted")
    if not HEX64.fullmatch(attest["frozen_source_sha256"]):
        raise CustodyError("Missing prior immutable freeze source hash")
    if not isinstance(attest["claimed_export_origin"],str) or not attest["claimed_export_origin"]:
        raise CustodyError("No source statement about provider event export")
    actual:dict[tuple[str,str,int],dict[str,Any]]={}
    for row in attempts:
        key=_key(row)
        if key in actual:
            raise CustodyError("Duplicate planned attempt keys")
        if row["model_id"]!=attest["model_id"]:
            raise CustodyError("Frozen original provider model changed")
        for digest in ("prompt_sha256","image_sha256","request_config_sha256"):
            if not HEX64.fullmatch(str(row[digest])):
                raise CustodyError("Missing exact raw prompt/image/config SHA256")
        if type(row["max_usd"]) not in (int,float) or row["max_usd"]<0:
            raise CustodyError("Bad per-call cap")
        _utc(row["requested_at"])
        actual[key]=row
    if sum(row["max_usd"] for row in attempts) > attest["spend_approved_usd"] + 1e-9:
        raise CustodyError("Planned maximum provider cost exceeds externally claimed cap")
    if attest["authorization_state"]=="UNAPPROVED":
        if attempts:
            raise CustodyError("Provider calls cannot occur under unapproved plan")
    mapped:dict[tuple[str,str,int],dict[str,Any]]={}
    response_ids=set()
    for row in outputs:
        key=_key(row)
        if key not in actual or key in mapped:
            raise CustodyError("Unplanned or duplicate provider response attempt")
        frozen=actual[key]
        if any(row[field]!=frozen[field] for field in (
                "model_id","prompt_sha256","image_sha256","request_config_sha256")):
            raise CustodyError("Provider answer differs from original input/model identity")
        status=row["status"]
        if status not in ("ok","failed","refused","timeout","abstained"):
            raise CustodyError("Invalid response outcome")
        if not isinstance(row["response_text"],str):
            raise CustodyError("Response text absent or invalid")
        if not HEX64.fullmatch(str(row["response_sha256"])) or sha256(
                row["response_text"].encode()).hexdigest()!=row["response_sha256"]:
            raise CustodyError("Private raw response text SHA does not match")
        if status=="ok" and (not row["response_text"] or not row["response_id"]):
            raise CustodyError("Successful attempt missing original provider response ID")
        if status!="ok" and row["response_text"] and not row["response_id"]:
            raise CustodyError("Failed attempt has text but no linked response ID")
        if row["response_id"]:
            if not isinstance(row["response_id"],str) or row["response_id"] in response_ids:
                raise CustodyError("Missing/duplicate provider response ID")
            response_ids.add(row["response_id"])
        if _utc(row["responded_at"]) < _utc(frozen["requested_at"]):
            raise CustodyError("Provider response before request")
        mapped[key]=row
    if set(mapped)!=set(actual):
        raise CustodyError("Incomplete attempt denominator including failures")
    exported={}
    eventids=set()
    for row in events:
        if row["provider_event_id"] in eventids or not row["provider_event_id"]:
            raise CustodyError("Duplicate/missing claimed external account event ID")
        eventids.add(row["provider_event_id"])
        eid=row["response_id"]
        if eid not in response_ids or eid in exported:
            raise CustodyError("Export event missing/duplicate matching response ID")
        if row["model_id"]!=attest["model_id"]:
            raise CustodyError("Provider export uses different model")
        if row["event_status"] not in ("ok","refused","failed"):
            raise CustodyError("Unknown external provider event type")
        if type(row["provider_cost_usd"]) not in (int,float) or row["provider_cost_usd"]<0:
            raise CustodyError("Invalid claimed real provider cost")
        _utc(row["created_at"])
        exported[eid]=row
    linked=[r for r in outputs if r["response_id"]]
    if len(exported)!=len(linked):
        raise CustodyError("Missing provider export event for response ID")
    for row in linked:
        ev=exported[row["response_id"]]
        if ev["request_config_sha256"]!=row["request_config_sha256"]:
            raise CustodyError("Provider export/config provenance mismatch")
        if abs((_utc(ev["created_at"])-_utc(row["responded_at"])).total_seconds()) > 300:
            raise CustodyError("Provider export timestamp differs >5min")
    claimed_cost=sum(v["provider_cost_usd"] for v in events)
    if claimed_cost>attest["spend_approved_usd"]+1e-9:
        raise CustodyError("Reported provider cost exceeds max approved spend")
    counts=Counter(r["status"] for r in outputs)
    return {"audit":"INTEGRITY_AND_SELF_REPORTED_PROVIDER_EXPORT_CONSISTENT",
            "schema_version":VERSION,"run_id":attest["run_id"],
            "planned_attempts":len(attempts),"recorded_attempts":len(outputs),
            "outcomes":dict(sorted(counts.items())),"provider_events":len(events),
            "unique_response_ids":len(response_ids),
            "claimed_cost_usd":round(claimed_cost,6),
            "approved_budget_cryptographically_authenticated":False,
            "export_independently_authenticated_by_provider":False,
            "model_forward_pass_proven":False,
            "official_scorer_replayed":False,
            "permission_verified_by_authorized_review":False,
            "scientific_grade":"D0_STRUCTURE_ONLY",
            "eval003_milestone_points":0.0}


def paired_coverage(left: list[dict[str,Any]],right: list[dict[str,Any]]) -> dict[str,Any]:
    """Coverage-only paired comparison: no benchmark gold or arbitrary scores."""
    indexes=[]
    for rows in (left,right):
        keys={}
        for row in rows:
            if set(row)!={"item_id","rung","sample_index","status"}:
                raise CustodyError("Coverage-only rows require exact fields")
            key=_key(row)
            if key in keys or row["status"] not in ("ok","failed","refused","timeout","abstained"):
                raise CustodyError("Duplicate/malformed result in one model")
            keys[key]=row["status"]
        indexes.append(keys)
    if set(indexes[0])!=set(indexes[1]):
        raise CustodyError("Cannot compare dissimilar item/rung/sample populations")
    both=sum(indexes[0][k]=="ok" and indexes[1][k]=="ok" for k in indexes[0])
    return {"paired_attempts":len(indexes[0]),"both_successes":both,
            "left_successes":sum(v=="ok" for v in indexes[0].values()),
            "right_successes":sum(v=="ok" for v in indexes[1].values()),
            "model_ranking_or_accuracy":None,
            "official_scorer_replayed":False}


def main(argv: list[str]|None=None)->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("command",choices=("audit-private","paired-coverage"))
    ap.add_argument("--attempts",type=Path)
    ap.add_argument("--responses",type=Path)
    ap.add_argument("--account-export",type=Path)
    ap.add_argument("--attestation",type=Path)
    ap.add_argument("--left",type=Path)
    ap.add_argument("--right",type=Path)
    args=ap.parse_args(argv)
    try:
        if args.command=="audit-private":
            if not all((args.attempts,args.responses,args.account_export,args.attestation)):
                raise CustodyError("Private audit requires all 4 source files")
            out=audit_private_provider_events(args.attempts,args.responses,args.account_export,args.attestation)
        else:
            if not args.left or not args.right:
                raise CustodyError("Pairing requires both model receipts")
            req={"item_id","rung","sample_index","status"}
            out=paired_coverage(_jsonl(args.left,req),_jsonl(args.right,req))
        print(json.dumps(out,sort_keys=True,indent=2))
        return 0
    except (CustodyError, ValueError, OSError, TypeError, KeyError) as exc:
        print(f"REFUSED: {exc}",file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
