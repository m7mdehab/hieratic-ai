"""Public HieraticBench physical-object accession lineage guard.

Only the previously published R017 266 PUBLIC metadata-only rows are read.
No images, answers, signs, prompts, or sealed two items. Exact institution +
inventory matches cause quarantine. All nonmatches mean UNKNOWN, never CLEAR.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
from hashlib import sha1
import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
PUBLIC_METADATA=ROOT/"docs/research/R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl"
FROZEN_REGISTER_GIT_BLOB="974c959651d86eaa6dda6097dc8912972cafc8d1"
OFFICIAL_REVISION="d587dc990013f18007f1e7a8f56f96ff2f7127e2"
EXPECTED_PUBLIC={"aku":150,"cbl":16,"met":37,"wm":61,"ypm":2}
LIMIT_BYTES=500000

class LineageError(ValueError):
    pass

def git_blob_sha(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _institution(text:str)->str|None:
    name=text.casefold()
    if re.search(r"metropolitan museum|\bthe met\b|\bmet museum\b|\bmet\b",name):
        return "MET"
    if "brooklyn" in name:
        return "BROOKLYN"
    if "museo egizio" in name or re.search(r"\bturin\b|\btorino\b",name):
        return "TURIN"
    if "louvre" in name:
        return "LOUVRE"
    if re.search(r"berlin|ägyptisches museum und papyrussammlung",name):
        return "BERLIN"
    if "chester beatty" in name:
        return "CHESTER_BEATTY"
    if re.search(r"british museum|\blondon\b.*\bea\b",name):
        return "BRITISH_MUSEUM"
    if re.search(r"\bkairo\b|\bcairo\b",name):
        return "CAIRO"
    return None

def physical_key(institution:str|None,inventory:str|None)->str|None:
    """Require recognized institution and typed inventory; no bare number matches."""
    if not isinstance(inventory,str) or not inventory.strip():
        return None
    ins=_institution((institution or "")+" "+inventory)
    if ins is None:
        return None
    source=inventory.casefold().replace("\u00a0"," ")
    if ins in {"MET","BROOKLYN"}:
        m=re.search(r"(?<![\w.])([0-9]{1,3})\s*\.\s*([0-9]{1,3})\s*\.\s*([0-9]{1,5})(?![\w.])",source)
        if m:
            return f"{ins}:NUM:{int(m[1])}.{int(m[2])}.{int(m[3])}"
    if ins=="TURIN":
        for label,pat in (
            ("CGT",r"(?<!\w)cgt[.\s-]*(\d{3,7})(?!\w)"),
            ("CAT",r"(?<!\w)cat(?:\.|alog(?:ue)?)[.\s-]*(\d{2,7})(?!\w)"),
            ("S",r"(?<!\w)s[.\s-]+(\d{2,7}(?:/\d{1,4})?)(?!\w)")
        ):
            m=re.search(pat,source)
            if m:
                return f"TURIN:{label}:{m[1].lstrip('0') or '0'}"
    if ins=="BERLIN":
        m=re.search(r"(?<!\w)p[.\s-]+(\d{2,7})(?!\w)",source)
        if m: return f"BERLIN:P:{int(m[1])}"
    if ins=="LOUVRE":
        m=re.search(r"(?<!\w)e[.\s-]+(\d{2,7})(?!\w)",source)
        if m: return f"LOUVRE:E:{int(m[1])}"
    if ins=="BRITISH_MUSEUM":
        m=re.search(r"(?<!\w)ea[.\s-]+(\d{2,7})(?!\w)",source)
        if m: return f"BRITISH_MUSEUM:EA:{int(m[1])}"
    if ins=="CAIRO":
        m=re.search(r"(?<!\w)cg(?!t)[.\s-]+(\d{3,7})(?!\w)",source)
        if m: return f"CAIRO:CG:{int(m[1])}"
    if ins=="CHESTER_BEATTY":
        m=re.search(r"\bpap(?:yrus)?[.\s-]*([mdclxvi]{1,10})(?!\w)",source)
        if m: return f"CHESTER_BEATTY:PAP:{m[1].upper()}"
    return None

def parse_public_bytes(raw:bytes,*,require_frozen:bool=True)->list[dict[str,Any]]:
    if not raw or len(raw)>LIMIT_BYTES:
        raise LineageError("Public metadata register missing or too large")
    if require_frozen and git_blob_sha(raw)!=FROZEN_REGISTER_GIT_BLOB:
        raise LineageError("Pinned R017 public source metadata identity drift")
    try:
        values=[json.loads(line) for line in raw.decode("utf-8").splitlines()]
    except (UnicodeError,json.JSONDecodeError) as exc:
        raise LineageError("Malformed public metadata-only JSONL") from exc
    if len(values)!=266 or not all(isinstance(x,dict) for x in values):
        raise LineageError("Frozen public source census must contain 266 rows")
    expected={"id","upstream_path","object_name","object_holder",
              "source_url","source_file_url","license_claim","source_group",
              "provenance_review","corpus_status"}
    counts=Counter();ids=set()
    for row in values:
        if set(row)!=expected:
            raise LineageError("Unexpected source fields, possibly benchmark gold")
        ident,group=row["id"],row["source_group"]
        if (not isinstance(ident,str) or not isinstance(group,str) or
                not ident.startswith(group+"-") or ident in ids):
            raise LineageError("Duplicate or inconsistent public item")
        if row["provenance_review"]!="metadata_only" or row["corpus_status"]!="QUARANTINE_EVAL_ONLY":
            raise LineageError("Public record not quarantined")
        ids.add(ident);counts[group]+=1
    if dict(counts)!=EXPECTED_PUBLIC:
        raise LineageError("Frozen public family census mismatch")
    return values

@lru_cache(maxsize=1)
def load_public()->tuple[dict[str,Any],...]:
    if PUBLIC_METADATA.is_symlink() or not PUBLIC_METADATA.is_file():
        raise LineageError("No safe pinned public source register")
    return tuple(parse_public_bytes(PUBLIC_METADATA.read_bytes()))

@lru_cache(maxsize=1)
def public_index()->dict[str,tuple[str,...]]:
    indexed:dict[str,list[str]]=defaultdict(list)
    for row in load_public():
        key=physical_key(row["object_holder"],row["object_name"])
        if key: indexed[key].append(row["id"])
    return {k:tuple(sorted(v)) for k,v in sorted(indexed.items())}

def match_item(item:dict[str,Any])->dict[str,Any]:
    key=physical_key(item.get("institution"),item.get("source_object_id"))
    matched=public_index().get(key,()) if key else ()
    return {"status":"PUBLIC_PHYSICAL_SOURCE_MATCH_QUARANTINE" if matched else "UNKNOWN_NOT_CLEARED",
            "physical_key":key,"public_item_ids":list(matched),
            "public_count":len(matched),"benchmark_revision":OFFICIAL_REVISION,
            "independent_no_overlap_proven":False,"rights_clearance_granted":False,
            "sealed_test_items_inspected":False}

def audit_public()->dict[str,Any]:
    rows=load_public();idx=public_index()
    source_family={x["id"]:x["source_group"] for x in rows}
    across=[{"physical_key":k,"public_item_ids":list(v),
             "families":sorted({source_family[i] for i in v})}
            for k,v in idx.items()
            if len({source_family[i] for i in v})>1]
    groups=Counter(len(v) for v in idx.values())
    return {"classification":"PUBLIC_EXACT_INVENTORY_GROUPING_NOT_EXPERT_GOLD",
            "source_revision":OFFICIAL_REVISION,
            "source_metadata_git_blob":FROZEN_REGISTER_GIT_BLOB,
            "public_records":len(rows),
            "family_counts":dict(sorted(Counter(x["source_group"] for x in rows).items())),
            "recognized_public_item_count":sum(map(len,idx.values())),
            "recognized_physical_inventory_groups":len(idx),
            "repeated_public_groups":sum(len(v)>1 for v in idx.values()),
            "group_sizes":dict(sorted(groups.items())),
            "cross_family_public_groups":across,
            "unrecognized_public_rows":len(rows)-sum(len(v) for v in idx.values()),
            "original_image_hash_comparison_performed":False,
            "unseen_sealed_records_inspected":0,
            "physical_independence_established":False,
            "metadata_nonmatch_is_clearance":False}

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("audit-public","screen"))
    p.add_argument("--institution",default="")
    p.add_argument("--accession",default="")
    args=p.parse_args()
    try:
        result=(audit_public() if args.command=="audit-public" else
                match_item({"institution":args.institution,"source_object_id":args.accession}))
        print(json.dumps(result,sort_keys=True,indent=2))
        return 0
    except LineageError as exc:
        print(f"REFUSED: {exc}",file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
