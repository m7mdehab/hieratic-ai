"""W27: bounded, authentic Tokyo IIIF printed-palaeography visual diagnostic.

Source: publisher HPDB metadata already committed and pinned (R023).
Rights: U-Tokyo Asian Research Library digital-archive use terms; printed
Möller book IIIF scans, not original manuscript photos or blind gold.
This experiment is QUARANTINED and cannot enter DATA-008 production or
official HieraticBench claims. Source images never enter public Git.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import io
import json
from pathlib import Path
import time
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data" / "references" / "hpdb"
LABELS = ("A1", "A2", "D1", "D2", "G1", "M12", "V1", "Z1")  # frozen before pixels
ITEMS_PER_LABEL_PER_VOLUME = 1
VOLUMES_TRAIN = (1, 2)
VOLUME_TEST = 3
SOURCE_HOST = "iiif.dl.itc.u-tokyo.ac.jp"
MAX_IMAGE_BYTES = 500_000
MAX_PIXEL_AREA = 1_000_000
SOURCE_POLICY = "https://www.lib.u-tokyo.ac.jp/ja/library/contents/archives-top/reuse"
SOURCE_COLLECTION = "https://da.dl.itc.u-tokyo.ac.jp/portal/en/assets/4a1fbed0-f2a2-4cf5-8a0a-fa310c62ca50"
SOURCE_INDEX = "https://moeller.jinsha.tsukuba.ac.jp/en/datasets/"
PROTOCOL = "W27_HPDB_PRINTED_FACSIMILE_RESEARCH_ONLY/1"
USER_AGENT = "HieraticAI-W27-original-IIIF-exploratory-research/1.0 (bounded)"
ALLOWED_SOURCE_PREFIX = "/iiif/asia/hp/"


class SourceError(ValueError):
    """Fail closed for any original-source or cohort inconsistency."""


class ExactHostRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        verify_iiif_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def verify_iiif_url(url: str) -> None:
    u = urlsplit(url)
    if (u.scheme != "https" or u.hostname != SOURCE_HOST or u.port is not None
            or u.username or u.password or u.query or u.fragment
            or not u.path.startswith(ALLOWED_SOURCE_PREFIX)
            or not u.path.endswith("/default.jpg")
            or ".." in u.path or "%2f" in u.path.lower()):
        raise SourceError("IIIF URL violates exact source host/path restrictions")


def read_catalog() -> list[dict]:
    manifest = json.loads((META / "metadata_manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("total_sign_records") != 2065
            or manifest.get("unambiguous_single_gardiner") != 1439
            or manifest.get("pinned_repository_commit") != "a8cfcf52632487cf1d61a5793d84c9b2f7192d5a"):
        raise SourceError("HPDB publisher-index identity changed")
    rows = []
    for vol in (1, 2, 3):
        f = META / f"moller_v{vol}_ccby4_metadata.jsonl"
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row["vol"] != vol:
                    raise SourceError("Unexpected volume in source metadata")
                rows.append(row)
    if len(rows) != 2065 or len({r["id"] for r in rows}) != 2065:
        raise SourceError("Unverified HPDB catalog population")
    return rows


def frozen_cohort(rows: list[dict]) -> list[dict]:
    cohort = []
    for label in LABELS:
        for volume in (1, 2, 3):
            eligible = sorted(
                (r for r in rows if r.get("single_sign") == label
                 and r.get("vol") == volume and r.get("iiif_ref")
                 and r.get("kind") == "Main"),
                key=lambda r: str(r["id"]),
            )
            if len(eligible) < ITEMS_PER_LABEL_PER_VOLUME:
                raise SourceError(f"Source cohort is insufficient: {label} volume {volume}")
            for r in eligible[:ITEMS_PER_LABEL_PER_VOLUME]:
                verify_iiif_url(r["iiif_ref"])
                cohort.append({
                    "item_id": str(r["id"]), "label": label, "volume": volume,
                    "printed_page": int(r["page"]), "url": r["iiif_ref"],
                    "role": "test" if volume == VOLUME_TEST else "train",
                    "source_proxy": f"MOLLER-V{volume}-P{int(r['page']):03d}",
                })
    if len(cohort) != 24 or len({i["item_id"] for i in cohort}) != 24:
        raise SourceError("Frozen cohort/attempt population differs from 24")
    train = {r["source_proxy"] for r in cohort if r["role"] == "train"}
    test = {r["source_proxy"] for r in cohort if r["role"] == "test"}
    if train & test:
        raise SourceError("Printed-page source proxy leaked across partitions")
    return cohort


def fetch_original(url: str, opener=None) -> bytes:
    verify_iiif_url(url)
    client = opener or build_opener(ExactHostRedirect())
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "image/jpeg"})
    try:
        with client.open(request, timeout=25) as reply:
            verify_iiif_url(reply.geturl())
            if reply.status != 200 or reply.headers.get_content_type() != "image/jpeg":
                raise SourceError("Source HTTP status or image content type incorrect")
            data = reply.read(MAX_IMAGE_BYTES + 1)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise SourceError(f"Authentic IIIF retrieval blocked: {type(exc).__name__} {str(exc)[:120]}") from exc
    if not 128 <= len(data) <= MAX_IMAGE_BYTES or not data.startswith(bytes((255, 216))):
        raise SourceError("Original image bytes missing, oversized or not JPEG")
    return data


def image_features(data: bytes) -> tuple[tuple[float, ...], dict]:
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise SourceError("Pillow is required; no procedural image substitution") from exc
    with Image.open(io.BytesIO(data)) as im:
        if im.format != "JPEG" or im.width * im.height > MAX_PIXEL_AREA:
            raise SourceError("JPEG source format/geometry not accepted")
        dims = [im.width, im.height]
        gray = ImageOps.autocontrast(im.convert("L")).resize((16, 8), Image.Resampling.LANCZOS)
        f = tuple(float(v) / 255.0 for v in gray.getdata())
    if len(f) != 128:
        raise SourceError("Invalid real-pixel feature vector")
    return f, {"original_dimensions": dims, "stimulus_sha256": sha256(data).hexdigest()}


def squared_distance(x: tuple[float, ...], y: tuple[float, ...]) -> float:
    if len(x) != 128 or len(y) != 128:
        raise SourceError("Unexpected original-pixel vector dimension")
    return sum((a - b) ** 2 for a, b in zip(x, y))


def evaluate(samples: list[dict]) -> dict:
    """1NN on decoded original JPG pixels, print-VOLUME holdout only."""
    train = [x for x in samples if x["role"] == "train"]
    test = [x for x in samples if x["role"] == "test"]
    if len(train) != 16 or len(test) != 8:
        raise SourceError("Real-pixel denominator not equal frozen 16/8")
    prior = Counter(s["label"] for s in train)
    majority = sorted(prior, key=lambda label: (-prior[label], label))[0]
    predictions = []
    for row in test:
        best = min(train, key=lambda x: (squared_distance(x["features"], row["features"]), x["item_id"]))
        predictions.append({
            "item_id": row["item_id"], "label": row["label"], "predicted": best["label"],
            "nearest_training_id": best["item_id"], "correct": best["label"] == row["label"],
            "prior_correct": majority == row["label"], "printed_page_proxy": row["source_proxy"],
        })
    counts = Counter(y["label"] for y in predictions)
    return {
        "training_samples": len(train), "test_samples": len(test),
        "class_counts_test": dict(sorted(counts.items())),
        "majority_training_class": majority,
        "nonvisual_prior_correct": sum(x["prior_correct"] for x in predictions),
        "visual_1nn_correct": sum(x["correct"] for x in predictions),
        "visual_1nn_accuracy": sum(x["correct"] for x in predictions) / len(test),
        "nonvisual_prior_accuracy": sum(x["prior_correct"] for x in predictions) / len(test),
        "predictions": predictions,
    }


def run() -> dict:
    rows = frozen_cohort(read_catalog())
    samples = []
    for idx, row in enumerate(rows):
        if idx:
            time.sleep(0.8)  # polite, sequential bounded host access
        raw = fetch_original(row["url"])
        features, meta = image_features(raw)
        samples.append({**row, **meta, "features": features})
    result = evaluate(samples)
    receipts = [{k: v for k, v in s.items() if k != "features"} for s in samples]
    return {
        "protocol": PROTOCOL,
        "classification": "QUARANTINED_PRINTED_PALEOGRAPHY_ORIGINAL_PIXEL_DIAGNOSTIC_ONLY",
        "source_policy": SOURCE_POLICY,
        "source_collection": SOURCE_COLLECTION,
        "metadata_index": SOURCE_INDEX,
        "publisher_original_pixels_used": True,
        "original_papyrus_photographs_used": False,
        "physical_manuscript_group_holdout_proven": False,
        "benchmark_independence_proven": False,
        "dataset_training_admitted": False,
        "production_corpus_v1": False,
        "sign_reading_certified": False,
        "capability_points": 0,
        "cohort": receipts,
        "result": result,
    }


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():
        p.error("output exists; refusing overwrite")
    report = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + chr(10), encoding="utf-8")
    print(json.dumps({k: report["result"][k] for k in ("training_samples", "test_samples", "visual_1nn_correct", "nonvisual_prior_correct")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
