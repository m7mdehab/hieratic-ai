"""Ephemeral private-only synthetic replay fixture for pinned official scorer CI.

No model calls, no real predictions, no source images, no benchmark gold
copied to repo; only ephemeral external manifest/receipts in runner tempdir.
The pinned upstream scorer reads public gold only transiently at score time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from eval.baselines.public_freeze import build_snapshot
from eval.baselines.run_freeze import sha256_file

def blob(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--checkout",type=Path,required=True)
    p.add_argument("--outside",type=Path,required=True)
    a=p.parse_args()
    out=a.outside.resolve()
    repo=Path(__file__).resolve().parents[2]
    if not out.is_dir() or out.is_relative_to(repo):
        raise SystemExit("Fixtures must be written to existing external scratch directory")
    content,public_receipt=build_snapshot(a.checkout)
    (out/"public-items.jsonl").write_bytes(content)
    rows=[json.loads(line) for line in content.decode().splitlines()]
    # Statuses chosen for structural/denominator validation, not historical accuracy.
    status_cycle=("ok","failed","abstained","timeout","refused")
    frozen=[]
    capture=[]
    for idx,row in enumerate(rows):
        rung=row["rung"]
        token=row["item_id"]
        prompt_hash=blob(("SYNTHETIC PROMPT "+token+rung).encode())
        frozen.append({
            "item_id":token,"rung":rung,"sample_index":0,
            "model_key":"synthetic-score-bridge","prompt_path":"synthetic-no-real-prompt.txt",
            "prompt_sha256":prompt_hash,"image_path":"synthetic-no-image.ppm",
            "image_sha256":blob(b"SYNTHETIC IMAGE NEVER SOURCE IMAGE"),
        })
        status=status_cycle[idx%len(status_cycle)]
        capture.append({
            "item_id":token,"rung":rung,"sample_index":0,
            "provider_model_id":"synthetic-test-only","prompt_sha256":prompt_hash,
            "status":status,
            # A canned test string, never obtained from a model or inferred from gold.
            "response_text":("SCRIPT: UNKNOWN" if rung=="identify" else "SIGNS: Z999") if status=="ok" else "",
            "provider_response_id":f"SYNTHETIC-RECEIPT-{idx}" if status=="ok" else None,
            "timestamp":"2026-10-08T00:00:00Z",
        })
    def write(path: Path,obj: object) -> None:
        path.write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    (out/"attempts.jsonl").write_text(
        "".join(json.dumps(r,sort_keys=True)+"\n" for r in frozen),encoding="utf-8"
    )
    (out/"capture.jsonl").write_text(
        "".join(json.dumps(r,sort_keys=True)+"\n" for r in capture),encoding="utf-8"
    )
    freeze={
        "state":"locked","run_id":"FRONTIER-SYNTHETIC-SCORER-QA",
        "model_key":"synthetic-score-bridge",
        "provider_model_id":"synthetic-test-only",
        "official_benchmark_commit":public_receipt["benchmark_revision"],
        "scorer_source_sha256":sha256_file(a.checkout/"bench/src/score.ts"),
        "official_prompt_source_sha256":sha256_file(a.checkout/"bench/src/prompts.ts"),
        "public_item_manifest_sha256":sha256_file(out/"public-items.jsonl"),
        "prompt_attempts_manifest_sha256":sha256_file(out/"attempts.jsonl"),
        "samples_per_item":1,
        "attempts_planned":len(rows),
    }
    receipt={
        "schema_version":"1.0.0","state":"captured","run_id":freeze["run_id"],
        "model_key":freeze["model_key"],"provider_model_id":freeze["provider_model_id"],
        "capture_sha256":sha256_file(out/"capture.jsonl"),
        "rendered_attempts_sha256":sha256_file(out/"attempts.jsonl"),
        "records_expected":len(rows),
    }
    write(out/"freeze.json",freeze)
    write(out/"receipt.json",receipt)
    print(f"PASS: created only synthetic private test payload for {len(rows)} attempts, not provider results")

if __name__=="__main__":
    main()
