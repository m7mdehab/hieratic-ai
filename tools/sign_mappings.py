"""Validate and deterministically query layered palaeographic mapping records."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any
import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT=Path(__file__).resolve().parents[1]
SCHEMA=ROOT/"schemas/sign_mappings.schema.json"
class MappingError(ValueError): pass

def load(path: Path)->Any:
    try: return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,yaml.YAMLError) as exc: raise MappingError(f"{path}: {exc}") from exc

def validate(payload: Any, schema: dict[str,Any]|None=None)->list[str]:
    schema=schema or json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors=[f"{'.'.join(map(str,e.absolute_path)) or '<root>'}: {e.message}" for e in sorted(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(payload),key=lambda e:str(e.absolute_path))]
    if errors:return errors
    records={}; ids=set(); citation_ids=set(); variants=set()
    def unique(value,label):
        if value in ids:errors.append(f"duplicate {label} ID: {value}")
        ids.add(value)
    for rec in payload["records"]:
        unique(rec["identity_id"],"identity");records[rec["identity_id"]]=rec
        for var in rec["variants"]:
            unique(var["variant_id"],"variant");variants.add(var["variant_id"])
        all_claims=[rec["observed_hieratic"],rec["hieroglyphic_correspondence"],rec["transliteration_value"]]
        citations=list(rec["provenance"])
        for claim in all_claims:
            citations.extend(claim["citations"])
            if claim["status"]=="supported":
                if claim["value"] is None or not claim["citations"]:
                    errors.append(f"{rec['identity_id']}: supported claim requires a value and citation")
                elif not any(citation.get("verified_metadata") is True for citation in claim["citations"]):
                    errors.append(f"{rec['identity_id']}: supported claim requires verified citation metadata")
            if claim["status"] in {"unresolved","not_applicable"} and claim["value"] is not None:errors.append(f"{rec['identity_id']}: {claim['status']} claim must not assert a value")
        for var in rec["variants"]:
            citations.extend(var["provenance"])
            if var["variant_status"]=="accepted_variant" and not any(ref.get("verified_metadata") is True for ref in var["provenance"]):
                errors.append(f"{var['variant_id']}: accepted variant requires verified provenance")
        for cite in citations:
            cid=cite["citation_id"]
            if cid in citation_ids: errors.append(f"duplicate citation_id: {cid}")
            citation_ids.add(cid)
            if not cite["reference"].strip(): errors.append(f"{cid}: empty reference")
    edges=set(); graph={key:[] for key in records}; relation_ids=set()
    for rel in payload["relations"]:
        rid=rel["relation_id"]
        if rid in relation_ids:errors.append(f"duplicate relation_id: {rid}")
        relation_ids.add(rid)
        pair=(rel["from_identity_id"],rel["to_identity_id"],rel["relation_type"])
        if pair in edges:errors.append(f"duplicate relation edge: {pair}")
        edges.add(pair)
        for key in pair[:2]:
            if key not in records:errors.append(f"relation {rid}: unknown identity {key}")
        if rel["status"]=="supported" and not any(ref.get("verified_metadata") is True for ref in rel["provenance"]):
            errors.append(f"relation {rid}: supported relation requires verified provenance")
        if rel["relation_type"] in {"variant_of","subclass_of"} and pair[0] in records and pair[1] in records:graph[pair[0]].append(pair[1])
    visiting=set(); visited=set()
    def visit(node):
        if node in visiting:errors.append(f"hierarchical relation cycle includes {node}");return
        if node in visited:return
        visiting.add(node)
        for child in graph[node]:visit(child)
        visiting.remove(node);visited.add(node)
    for node in graph:visit(node)
    return errors

def canonical(payload:Any)->str:return json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":"))

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest="cmd",required=True)
    for cmd in ("validate","export"):
        q=s.add_parser(cmd);q.add_argument("input",type=Path)
        if cmd=="export":q.add_argument("--format",choices=("json","yaml"),default="json")
    q=s.add_parser("lookup");q.add_argument("input",type=Path);q.add_argument("identity_id")
    a=p.parse_args(argv)
    try:
        payload=load(a.input); errors=validate(payload)
        if errors:raise MappingError("\n".join(errors))
        payload["records"].sort(key=lambda r:r["identity_id"]);payload["relations"].sort(key=lambda r:(r["from_identity_id"],r["to_identity_id"],r["relation_type"],r["relation_id"]))
        if a.cmd=="validate":print(f"PASS: {len(payload['records'])} sign identities, {len(payload['relations'])} relations")
        elif a.cmd=="lookup":
            rec=next((r for r in payload["records"] if r["identity_id"]==a.identity_id),None)
            if rec is None:raise MappingError(f"unknown identity_id: {a.identity_id}")
            print(json.dumps(rec,sort_keys=True,indent=2,ensure_ascii=False))
        elif a.format=="json":print(json.dumps(payload,sort_keys=True,indent=2,ensure_ascii=False))
        else:print(yaml.safe_dump(payload,sort_keys=True,allow_unicode=True),end="")
        return 0
    except (MappingError,OSError,TypeError,KeyError,ValueError) as exc:print(f"FAIL: {exc}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
