"""Freeze/verify PUBLIC HieraticBench item IDs and official prompt source bytes.

Does not import data/images/gold, copy model outputs, call model providers, or
change training data. Output must be outside the project checkout and is
read-only after creation; upstream checkout must be at the EVAL-002 pinned SHA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from eval.benchmarks.hieraticbench.adapter import (
    BenchmarkAuditError, assert_pinned_checkout, inspect_items, load_manifest
)

ROOT = Path(__file__).resolve().parents[2]
PROMPT_FILE = "bench/src/prompts.ts"
PUBLIC_RUNGS = ("identify", "signs")
EXPECTED_COUNTS = {"identify": 116, "signs": 150}


class PublicFreezeError(ValueError):
    pass


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_public_pairs(items: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    """Produce only item ID, rung, public split. No predictions/gold/images."""
    if len(items) != 268:
        raise PublicFreezeError(f"Unexpected pinned inventory count: {len(items)}")
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, str]] = []
    for item_id, entry in sorted(items.items()):
        if entry["split"] != "public":
            continue
        if not isinstance(item_id, str) or not item_id:
            raise PublicFreezeError("Invalid public item ID")
        for rung in PUBLIC_RUNGS:
            if rung in entry["rungs"]:
                key = item_id,rung
                if key in seen:
                    raise PublicFreezeError(f"Duplicate item/rung {key}")
                seen.add(key)
                out.append({"item_id":item_id,"rung":rung,"split":"public"})
    counts = {rung:sum(x["rung"]==rung for x in out) for rung in PUBLIC_RUNGS}
    if counts != EXPECTED_COUNTS or len(out) != 266:
        raise PublicFreezeError(f"Pinned public item/rung count mismatch: {counts}; expected {EXPECTED_COUNTS}")
    return out


def manifest_bytes(items: dict[str, dict[str, Any]]) -> bytes:
    return "".join(json.dumps(x,sort_keys=True,separators=(",",":"))+"\n" for x in safe_public_pairs(items)).encode("utf-8")


def build_snapshot(checkout: Path) -> tuple[bytes,dict[str,Any]]:
    benchmark=load_manifest()
    assert_pinned_checkout(checkout,benchmark)
    items=inspect_items(checkout,benchmark)
    prompt_path=checkout/PROMPT_FILE
    if not prompt_path.is_file() or prompt_path.is_symlink():
        raise PublicFreezeError("Pinned prompt source missing or symlinked")
    raw=prompt_path.read_bytes()
    if not raw or len(raw)>200_000:
        raise PublicFreezeError("Missing/oversized upstream prompt source")
    content=manifest_bytes(items)
    return content,{
        "schema_version":"1.0.0",
        "purpose":"evaluation_metadata_freeze_not_model_results",
        "benchmark_revision":benchmark["benchmark"]["pinned_commit"],
        "official_prompt_path":PROMPT_FILE,
        "official_prompt_source_sha256":content_hash(raw),
        "manifest_sha256":content_hash(content),
        "public_item_rung_count":266,
        "rung_counts":EXPECTED_COUNTS,
        "sealed_item_count_excluded":2,
        "contains_images":False,
        "contains_gold_answers":False,
        "contains_model_outputs":False,
        "training_or_dev_use":False,
    }


def _validate_dest(output_dir: Path) -> Path:
    out=output_dir.resolve()
    if out==ROOT.resolve() or out.is_relative_to(ROOT.resolve()):
        raise PublicFreezeError("Public benchmark freeze artifacts must be outside this repository")
    if not out.is_dir():
        raise PublicFreezeError("Existing external output directory is required")
    if output_dir.is_symlink():
        raise PublicFreezeError("Symlink destination is not permitted")
    return out


def freeze(checkout: Path, output_dir: Path) -> dict[str,Any]:
    out=_validate_dest(output_dir)
    content,receipt=build_snapshot(checkout)
    manifest_path=out/"public-item-rungs.jsonl"
    receipt_path=out/"public-freeze-receipt.json"
    if manifest_path.exists() or receipt_path.exists():
        raise PublicFreezeError("Existing freeze files: do not overwrite immutable artifacts")
    with manifest_path.open("xb") as handle:
        handle.write(content)
    try:
        with receipt_path.open("x",encoding="utf-8") as handle:
            json.dump(receipt,handle,sort_keys=True,indent=2)
            handle.write("\n")
    except Exception:
        manifest_path.unlink(missing_ok=True)
        raise
    return receipt


def verify(checkout: Path, output_dir: Path) -> dict[str,Any]:
    out=_validate_dest(output_dir)
    content,expected_receipt=build_snapshot(checkout)
    path=out/"public-item-rungs.jsonl"
    receipt_path=out/"public-freeze-receipt.json"
    try:
        stored=path.read_bytes()
        actual=json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc:
        raise PublicFreezeError(f"Frozen public metadata missing/corrupt: {exc}") from exc
    if stored != content or actual != expected_receipt:
        raise PublicFreezeError("Frozen public manifest, pinned prompt or receipt differs from current verified upstream metadata")
    return expected_receipt


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="Freeze/verify only public benchmark item identifiers and official prompt-source hash")
    parser.add_argument("action",choices=["freeze","verify"])
    parser.add_argument("--checkout",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        rec=freeze(args.checkout,args.output_dir) if args.action=="freeze" else verify(args.checkout,args.output_dir)
        print(f"PASS: {args.action} only public item/rung metadata; no images, gold, sealed predictions or inference")
        print(json.dumps(rec,indent=2,sort_keys=True))
        return 0
    except (PublicFreezeError,BenchmarkAuditError,OSError,ValueError,TypeError,KeyError) as exc:
        print(f"FAIL: {exc}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
