"""W26 DDD visual-experiment readiness and fail-closed manuscript-split gate.

Research-only *metadata* inspection by default. Never downloads a manuscript
image, trains a model, certifies third-party image rights or marks DATA-008 as
admitted. Publisher annotations are noncommercial and not expert-blind gold.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

from tools.research_ddd_public_metadata import PublicSourceError, fetch_exact
from tools.research_ddd_prior_baseline import (
    EXPECTED_CLASSES, EXPECTED_GROUPS, EXPECTED_PAPYRI,
    EXPECTED_SAMPLES, stable_rank,
)

SOURCE = "https://zenodo.org/records/20553713"
SOURCE_SHA256 = {
    "papyri.json": "33265df94656e79a27c1c158756f0a2479173d00184c5212159ec1bb8414eb62",
    "samples.json": "763944b29e06643131fa9fdbd14a2b169afe5961df80394fecfd152203584e46",
    "classes.json": "5ff0181de57e1018058ba53e8e436e6e67a19fca290568ed0f9ea341af7afe18",
}
PARTITIONS = ("train", "dev", "test")
REASONS = (
    "per_image_training_rights_unverified",
    "image_pixel_and_crop_hash_absent",
    "benchmark_lineage_and_near_duplicate_review_unverified",
    "scholarly_label_not_independent_blind_gold",
)


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def verified_source(raw: dict[str, bytes]) -> tuple[dict, dict, dict]:
    """Verify original publisher bytes, invariants, and sample-to-document joins."""
    for name, expected in SOURCE_SHA256.items():
        if name not in raw or sha256_bytes(raw[name]) != expected:
            raise PublicSourceError(f"missing/drifted exact DDD publisher bytes: {name}")
    papyri, samples, classes = (json.loads(raw[n]) for n in
                                  ("papyri.json", "samples.json", "classes.json"))
    if not (isinstance(papyri, dict) and len(papyri) == EXPECTED_PAPYRI and
            isinstance(samples, dict) and len(samples) == EXPECTED_SAMPLES and
            isinstance(classes, dict) and len(classes) == EXPECTED_CLASSES):
        raise PublicSourceError("DDD original publisher cohort shape drift")
    return papyri, samples, classes


def build_preflight(papyri: dict, samples: dict, classes: dict) -> dict:
    """Research inventory only. A copyright assertion never upgrades an image."""
    if (len(papyri), len(samples), len(classes)) != (
            EXPECTED_PAPYRI, EXPECTED_SAMPLES, EXPECTED_CLASSES):
        raise PublicSourceError("publisher universe count drift")
    clusters: dict[str, str] = {}
    support_images: dict[str, list[str]] = collections.defaultdict(list)
    claim_distribution: collections.Counter[str] = collections.Counter()
    has_tpop_ref = 0
    unknown_copyright = 0
    for image_id, item in papyri.items():
        if not isinstance(image_id, str) or not re.fullmatch(r"\d{3}", image_id):
            raise PublicSourceError("image identity is not an original three-digit ID")
        if (not isinstance(item, dict) or type(item.get("doc_cluster")) is not int or
                not isinstance(item.get("copyright"), str)):
            raise PublicSourceError("missing publisher physical identity/copyright")
        claim = item["copyright"].strip()
        if not claim:
            raise PublicSourceError("empty item-specific image copyright")
        cluster = str(item["doc_cluster"])
        clusters[image_id] = cluster
        support_images[cluster].append(image_id)
        claim_distribution[claim] += 1
        if isinstance(item.get("TPOP_ref"), dict) and item["TPOP_ref"].get("document") is not None:
            has_tpop_ref += 1
        if claim.strip(" ?-").lower() in ("", "unknown", "none", "n/a"):
            unknown_copyright += 1
    if len(support_images) != EXPECTED_GROUPS:
        raise PublicSourceError("50-physical-manuscript identity drift")
    cat1880 = [i for i,v in papyri.items() if "C1880" in str(v.get("name", ""))]
    if len(cat1880) < 2 or len({clusters[i] for i in cat1880}) != 1:
        raise PublicSourceError("Cat1880 rotated/source sibling split integrity failed")
    original_labels = {x["class_label"] for x in classes.values()
                       if isinstance(x,dict) and isinstance(x.get("class_label"),str)}
    annotated_images: collections.Counter[str] = collections.Counter()
    source_labels: dict[str, set[str]] = collections.defaultdict(set)
    for sid, row in samples.items():
        if not isinstance(row, dict) or str(row.get("sample_number")) != sid:
            raise PublicSourceError("publisher sample identity mismatch")
        image_id = str(row.get("document_number", ""))
        label = row.get("class_label")
        if image_id not in clusters or not isinstance(label, str) or label not in original_labels:
            raise PublicSourceError("publisher label or source image not recognized")
        annotated_images[image_id] += 1
        source_labels[clusters[image_id]].add(label)
    if len(annotated_images) != EXPECTED_PAPYRI:
        raise PublicSourceError("one or more publisher images have no original samples")
    groups = sorted(support_images, key=stable_rank)
    membership = {g: ("train" if i < 35 else "dev" if i < 42 else "test")
                  for i,g in enumerate(groups)}
    cluster_counts = collections.Counter(membership.values())
    if dict(cluster_counts) != {"train": 35, "dev": 7, "test": 8}:
        raise PublicSourceError("W24 project diagnostic source split drift")
    # This is NOT the publisher's official C-B split: the official split ZIP is not acquired.
    ledger = []
    for image_id in sorted(papyri):
        cluster = clusters[image_id]
        ledger.append({
            "image_id": image_id,
            "physical_witness_group": cluster,
            "research_diagnostic_partition": membership[cluster],
            "publisher_annotations": annotated_images[image_id],
            "item_copyright_text": papyri[image_id]["copyright"],
            "source_license": "CC_BY_NC_SA_4_0_NONCOMMERCIAL",
            "image_training_admitted": False,
            "image_evaluation_admitted": False,
            "blocked_reasons": list(REASONS),
        })
    return {
        "protocol": "R033_W26_DDD_PER_IMAGE_VISUAL_ADMISSION_PREFLIGHT_V1",
        "source": SOURCE,
        "input_universe": {"images": len(papyri),"samples": len(samples),
                           "classes": len(classes),"physical_supports": len(support_images)},
        "metadata_observations": {
            "item_copyright_claim_categories": len(claim_distribution),
            "images_with_tpop_document_metadata": has_tpop_ref,
            "images_with_placeholder_copyright_claim": unknown_copyright,
            "groups_with_scholarly_labels": len(source_labels),
            "cat1880_source_variants": sorted(cat1880),
            "cat1880_supports": 1,
        },
        "split": {
            "status": "PROJECT_R029_35_7_8_DIAGNOSTIC_NOT_PUBLISHER_C_B",
            "groups": {x: cluster_counts[x] for x in PARTITIONS},
            "source_group_overlap": 0,
        },
        "per_image_ledger": ledger,
        "rights_approved_image_count": 0,
        "benchmark_cleared_image_count": 0,
        "training_admitted_image_count": 0,
        "scientifically_scoreable_independent_gold_count": 0,
        "image_pixels_retrieved": 0,
        "model_trained": False,
        "heldout_visual_accuracy": None,
        "weighted_capability_points_awarded": 0,
        "production_corpus_status": "HARD_BLOCKED",
        "readiness_status": "NO_RIGHTS_AND_BENCHMARK_CLEARED_COHORT",
        "required_external_independent_evidence": [
            "item-level image training/evaluation rights tied to exact source bytes",
            "exact downloaded image or crop SHA256 with parent archive provenance",
            "physical document/alias near-duplicate screen against public benchmark sources",
            "frozen publisher C-B original split manifest or explicitly new diagnostic split",
            "independent evaluation of scientific labels and intended performance claims",
        ],
    }


def validate_positive_clearance(preflight: dict, claims: dict) -> dict:
    """Fail-closed evidence validator; never itself authenticates a claimed reviewer.

    Returns only provisional candidates. Even full syntactic receipts cannot
    authorize DATA-008, benchmark exposure, scientific score or training.
    """
    if claims.get("protocol") != "R033_IMAGE_RIGHTS_CLAIM_PACKET_V1":
        raise PublicSourceError("unknown independent-clearance packet type")
    rows = claims.get("images")
    if not isinstance(rows, list) or not rows:
        raise PublicSourceError("clearance requires at least one explicit item")
    original = {x["image_id"]: x for x in preflight["per_image_ledger"]}
    seen = set()
    provisionals=[]
    for row in rows:
        if not isinstance(row,dict) or row.get("image_id") not in original:
            raise PublicSourceError("unknown publisher image ID")
        image_id=row["image_id"]
        if image_id in seen:raise PublicSourceError("duplicate clearance identity")
        seen.add(image_id)
        # A written claim is not institutional authority. These exact bindings
        # merely ensure the next reviewer can check a plausible evidence packet.
        for key in ("image_sha256", "original_archive_sha256", "permission_url",
                    "permission_reviewed_by", "benchmark_screen_url", "benchmark_reviewed_by"):
            if not isinstance(row.get(key),str) or not row[key].strip():
                raise PublicSourceError(f"missing clearance reference: {key}")
        for key in ("image_sha256", "original_archive_sha256"):
            if not re.fullmatch(r"[0-9a-f]{64}",row[key]):
                raise PublicSourceError("invalid source byte SHA256")
        for key in ("permission_url", "benchmark_screen_url"):
            if not row[key].startswith("https://"):
                raise PublicSourceError("evidence links must be HTTPS")
        if row.get("intended_track") != "NONCOMMERCIAL_RESEARCH_ONLY":
            raise PublicSourceError("DDD cannot silently enter commercial release")
        if row.get("benchmark_decision") != "INDEPENDENTLY_CLEARED_NO_OVERLAP":
            raise PublicSourceError("benchmark independence not cleared")
        if row.get("permission_decision") != "ITEM_REVIEWED_RESEARCH_USE_ONLY":
            raise PublicSourceError("original image rights not cleared")
        provisionals.append({"image_id":image_id,"source_group":original[image_id]["physical_witness_group"],
                             "status":"EVIDENCE_REFERENCES_PRESENT_REQUIRES_INDEPENDENT_VERIFICATION"})
    return {"provisional_evidence_packets":provisionals,
            "training_admission":False,"scientific_certification":False,
            "production_admission":False,"reason":"asserted refs are not authenticated reviewer/permission evidence"}


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--clearance",type=Path,help="Optional independently supplied review references; never self-approves")
    p.add_argument("--summary-output",type=Path,help="Aggregate-only replay receipt suitable for CI artifacts")
    args=p.parse_args()
    source = {name: fetch_exact(name)[0] for name in SOURCE_SHA256}
    report = build_preflight(*verified_source(source))
    report["source_sha256"] = dict(SOURCE_SHA256)
    if args.clearance:
        report["provisional_clearance_check"] = validate_positive_clearance(
            report, json.loads(args.clearance.read_text("utf8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    compact={k:v for k,v in report.items() if k!="per_image_ledger"}
    compact["private_ledger_sha256"] = sha256_bytes(json.dumps(report["per_image_ledger"],
        sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf8"))
    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True,exist_ok=True)
        args.summary_output.write_text(json.dumps(compact,sort_keys=True,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print(json.dumps(compact,sort_keys=True,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
