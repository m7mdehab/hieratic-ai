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
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("hpdb-verify", "hpdb-search"):
        return _hpdb_cli(argv)
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


# R-024/DATA-005: real publisher-pinned HPDB concordance reference.
# This is a separate metadata lookup API, NOT an assertion of observed manuscript
# identity, image rights, transliteration, or independent expert-gold validation.
HPDB_CONCORDANCE_BLOB = "9de1829304fcb2c3b5ee054fd7bd0e6f1dea964b"
HPDB_INDEX_BLOB = "6efc36471b47255cfc03f6ba8cf9c887a293bb89"
HPDB_EXPECTED_DISCREPANCIES = frozenset({
    "122001", "145001", "163007", "165017", "169010", "170006",
    "174007", "321001", "323008", "339009", "339010", "365004",
})
HPDB_CONCORDANCE_FIELDS = frozenset({
    "moller_no", "gardiner_no", "unicode_cp", "unicode_char", "jsesh",
    "mdc", "hieroglyphica", "ifao", "desc", "match_type", "wikidata_id",
    "wikidata_label", "wikidata_image", "tsl_id", "aku_id", "phrp_id",
    "isut_id", "dpdp_id",
})
HPDB_QUERY_FIELDS = frozenset({
    "moller_no", "gardiner_no", "unicode_cp", "unicode_char",
    "jsesh", "mdc", "hieroglyphica", "match_type",
    "tsl_id", "aku_id", "phrp_id", "isut_id", "dpdp_id",
})


def _pinned_hpdb_json(path: Path, *, max_bytes: int, blob_sha1: str) -> Any:
    """Pin exact Git blob bytes, including whitespace, against published Git SHA-1."""
    import hashlib
    try:
        size = path.stat().st_size
        if not 1 <= size <= max_bytes or not path.is_file() or path.is_symlink():
            raise MappingError(f"HPDB input is missing, symlinked or outside size cap: {path}")
        raw = path.read_bytes()
        if len(raw) != size:
            raise MappingError(f"HPDB input changed during read: {path}")
        observed = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()
        if observed != blob_sha1:
            raise MappingError(f"HPDB published Git blob drift/tampering: {path}")
        return json.loads(raw)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        if isinstance(exc, MappingError):
            raise
        raise MappingError(f"HPDB invalid source {path}: {exc}") from exc


def load_hpdb_concordance(*, root: Path = ROOT) -> dict[str, Any]:
    """Validate exact publisher snapshot and deterministic index associations.

    A Möller printed number is not a physical manuscript ID; index links are
    explicitly typed 'published_printed_reference_only'. Differing Gardiner
    notations from official datasets are preserved, not auto-corrected.
    """
    from collections import Counter

    base = root / "data/mappings/hpdb"
    manifest_path = base / "concordance_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise MappingError(f"HPDB manifest unreadable: {exc}") from exc
    expected_manifest = {
        "source_revision": "a8cfcf52632487cf1d61a5793d84c9b2f7192d5a",
        "source_git_blob_sha1": HPDB_CONCORDANCE_BLOB,
        "source_license": "CC-BY-4.0",
        "expected_concordance_count": 937,
        "linked_index_count": 2065,
        "exact_printed_notation_matches": 2053,
        "printed_notation_discrepancies": 12,
        "training_admission": "BLOCKED_REFERENCE_METADATA_ONLY",
        "scientific_evaluation_admission": "BLOCKED_REFERENCE_METADATA_ONLY",
    }
    for key, expected in expected_manifest.items():
        if manifest.get(key) != expected:
            raise MappingError(f"HPDB manifest unexpectedly changed {key}")
    if set(manifest.get("discrepancy_item_ids", [])) != HPDB_EXPECTED_DISCREPANCIES:
        raise MappingError("HPDB discrepancy manifest has drifted")
    raw = _pinned_hpdb_json(
        base / "id_correspondence_ccby4.json", max_bytes=1_000_000,
        blob_sha1=HPDB_CONCORDANCE_BLOB,
    )
    if not isinstance(raw, list) or len(raw) != 937:
        raise MappingError("Expected exactly 937 source-published concordance rows")
    by_number: dict[str, dict[str, str]] = {}
    for row in raw:
        if (not isinstance(row, dict) or set(row) != HPDB_CONCORDANCE_FIELDS
                or any(not isinstance(v, str) for v in row.values())):
            raise MappingError("Unexpected source concordance field structure")
        moller = row["moller_no"]
        if (not moller or moller != moller.strip() or len(moller) > 64
                or not row["gardiner_no"] or moller in by_number):
            raise MappingError(f"Invalid or duplicate Möller identity: {moller!r}")
        if row["match_type"] not in {"matched", "compound", "unmatched", "unknown"}:
            raise MappingError("Unrecognized publisher concordance match type")
        by_number[moller] = row
    if dict(Counter(x["match_type"] for x in raw)) != manifest.get("match_type_counts"):
        raise MappingError("HPDB concordance match-type census mismatch")

    index_root = root / "data/references/hpdb"
    try:
        index_manifest = json.loads(
            (index_root / "metadata_manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise MappingError(f"HPDB sign index manifest unreadable: {exc}") from exc
    if (index_manifest.get("source_git_blob_sha1") != HPDB_INDEX_BLOB
            or index_manifest.get("total_sign_records") != 2065
            or index_manifest.get("underlying_scans_downloaded") is not False
            or index_manifest.get("corpus_training_admission") != "BLOCKED_REFERENCE_METADATA_ONLY"):
        raise MappingError("Sign index source provenance or admission state changed")

    by_printed: dict[str, list[dict[str, Any]]] = {}
    seen: set[str] = set()
    for volume in (1, 2, 3):
        path = index_root / f"moller_v{volume}_ccby4_metadata.jsonl"
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 1_000_000:
                raise MappingError(f"Unsafe sign index file: {path}")
            with path.open("r", encoding="utf-8") as fd:
                for line in fd:
                    item = json.loads(line)
                    if not isinstance(item, dict):
                        raise MappingError("Malformed sign index record")
                    uid, printed, gardiner = item.get("id"), item.get("hieratic"), item.get("gardiner_printed")
                    if (not isinstance(uid, str) or not isinstance(printed, str)
                            or not isinstance(gardiner, str) or uid in seen or item.get("vol") != volume):
                        raise MappingError("Malformed or duplicate sign index identity")
                    seen.add(uid)
                    by_printed.setdefault(printed, []).append(item)
        except (OSError, ValueError, UnicodeError, TypeError) as exc:
            if isinstance(exc, MappingError):
                raise
            raise MappingError(f"HPDB sign index read failure: {path}: {exc}") from exc
    if len(seen) != 2065:
        raise MappingError(f"Expected 2065 unique sign records, got {len(seen)}")
    # Every published index record has a referenced concordance Möller key in
    # this pinned publisher revision. No fuzzy or inferred label equivalence.
    if set(by_printed) != set(by_number):
        raise MappingError("Published sign-index Möller keys do not match concordance")
    discrepancies = []
    exact = 0
    for number, items in by_printed.items():
        expected = by_number[number]["gardiner_no"]
        for item in items:
            if item["gardiner_printed"] == expected:
                exact += 1
            else:
                discrepancies.append({
                    "item_id": item["id"],
                    "volume": item["vol"],
                    "moller_no": number,
                    "index_gardiner": item["gardiner_printed"],
                    "concordance_gardiner": expected,
                    "status": "PUBLISHED_METADATA_DISAGREEMENT_NOT_RESOLVED",
                })
    if exact != 2053 or len(discrepancies) != 12 or {
        x["item_id"] for x in discrepancies
    } != HPDB_EXPECTED_DISCREPANCIES:
        raise MappingError("Concordance-to-index consistency audit changed")
    discrepancies.sort(key=lambda x: x["item_id"])
    for group in by_printed.values():
        group.sort(key=lambda x: x["id"])
    return {
        "manifest": manifest, "rows": raw, "by_printed": by_printed,
        "counts": {
            "concordance_rows": len(raw), "sign_index_rows": len(seen),
            "literal_exact_matches": exact, "literal_disagreements": len(discrepancies),
            "match_types": dict(sorted(Counter(x["match_type"] for x in raw).items())),
            "physical_original_manuscripts_verified": 0,
            "expert_gold_lines": 0,
        }, "discrepancies": discrepancies,
    }


def hpdb_query(snapshot: dict[str, Any], field: str, exact_value: str, *,
               limit: int = 20) -> dict[str, Any]:
    """Pure exact-field lookup; never silently aliases approximate or compound signs."""
    if field not in HPDB_QUERY_FIELDS or not exact_value or not isinstance(exact_value, str):
        raise MappingError("Unsupported or empty exact HPDB lookup")
    if not isinstance(limit, int) or not 1 <= limit <= 100:
        raise MappingError("HPDB lookup limit must be from 1 to 100")
    matching = sorted(
        (r for r in snapshot["rows"] if r[field] == exact_value),
        key=lambda r: r["moller_no"],
    )
    results = []
    for row in matching[:limit]:
        items = snapshot["by_printed"][row["moller_no"]]
        results.append({
            "concordance": row,
            "publisher_index_candidates": [{
                "item_id": item["id"], "volume": item["vol"], "printed_page": item["page"],
                "printed_moller": item["hieratic"], "printed_gardiner": item["gardiner_printed"],
                "publisher_item_url": item["item_url"],
                "printed_notation_agrees": item["gardiner_printed"] == row["gardiner_no"],
            } for item in items],
            "link_status": "PUBLISHED_PRINTED_NOTATION_LINK_ONLY_NOT_ORIGINAL_WITNESS",
        })
    return {
        "query": {"field": field, "exact_value": exact_value},
        "total_concordance_matches": len(matching),
        "returned_matches": len(results), "truncated": len(results) < len(matching),
        "results": results,
        "rights": "CC-BY-4.0_METADATA_ONLY_TOKYO_SCAN_RIGHTS_UNVERIFIED",
        "not_gold_or_scientific_result": True,
    }


def _hpdb_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Offline verified HPDB metadata concordance")
    sub = parser.add_subparsers(dest="action", required=True)
    check = sub.add_parser("hpdb-verify")
    check.add_argument("--disagreements", action="store_true")
    lookup = sub.add_parser("hpdb-search")
    lookup.add_argument("--field", choices=sorted(HPDB_QUERY_FIELDS), required=True)
    lookup.add_argument("--exact", required=True)
    lookup.add_argument("--limit", type=int, default=20)
    try:
        opts = parser.parse_args(argv)
        snapshot = load_hpdb_concordance()
        if opts.action == "hpdb-verify":
            data = {
                "counts": snapshot["counts"],
                "source_revision": snapshot["manifest"]["source_revision"],
                "source_blob_sha1": HPDB_CONCORDANCE_BLOB,
                "classification": "REFERENCE_METADATA_ONLY",
                "validated": True,
            }
            if opts.disagreements:
                data["disagreements"] = snapshot["discrepancies"]
        else:
            data = hpdb_query(snapshot, opts.field, opts.exact, limit=opts.limit)
        print(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (MappingError, OSError, ValueError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__=="__main__":raise SystemExit(main())
