"""Fail-closed checks for completely synthetic official-scorer CI aggregates.

Does not read gold labels, original manuscript images or provider results.
Asserts aggregate-only redaction and complete failure-preserving denominators.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

def audit(directory: Path) -> None:
    f=directory/"original-scores-FRONTIER-SYNTHETIC-SCORER-QA.json"
    content=f.read_text(encoding="utf-8")
    report=json.loads(content)
    expected=set(("schema_version","report_type","evaluation_id","upstream_commit",
      "official_scorer_sha256","public_item_manifest_sha256","raw_capture_sha256",
      "model_key","provider_model_id","rung_aggregates","note",
      "original_provider_calls_authenticated","independently_accepted_result"))
    if set(report)!=expected or report["original_provider_calls_authenticated"] or report["independently_accepted_result"]:
        raise ValueError("Report has invalid scope or false experimental authentication")
    if report["provider_model_id"]!="synthetic-test-only" or set(report["rung_aggregates"])!={"identify","signs"}:
        raise ValueError("Report copied historical scored data or unexpected tasks")
    for rung,n in (("identify",116),("signs",150)):
        r=report["rung_aggregates"][rung]
        if r["scheduled_items"]!=n or r["scheduled_attempts"]!=n or sum(r["statuses"].values())!=n:
            raise ValueError("Rung item/attempt populations or failures are incomplete")
        if r["official_scored_samples"]!=r["statuses"]["ok"]:
            raise ValueError("Official denominator does not align with successful attempts")
        if not 0<=r["intention_to_test_zero_for_failed_macro"]<=1:
            raise ValueError("Missing intention-to-test statistics")
    forbidden=('"response_text"','"gardiner"','"parsed"','"script"','"image_path"','"gold"','"per_item"','"provider_response_id"','"privateCopy"')
    if any(word in content for word in forbidden):
        raise ValueError("Report includes answer-bearing, image, item-level or private response content")
    if len(content)>5000:
        raise ValueError("Public aggregates unexpectedly large; possible confidential payload")
    print("PASS: pinned original scorer replayed 266 synthetic attempted items, aggregate only, no real model experiment")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--directory",type=Path,required=True)
    args=p.parse_args()
    audit(args.directory)

if __name__=="__main__":
    main()
