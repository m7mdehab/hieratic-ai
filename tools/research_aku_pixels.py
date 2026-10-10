"""W25 original publisher sign-scan image pixels (5 verified WebP specimens).

All actual source media are explicitly CC BY 4.0 at exact AKU-PAL item IDs.
Source witnesses must be grouped, and existing public benchmark source collision is
UNKNOWN; this is research morphology ONLY. Never source lines or model accuracy.
"""
from __future__ import annotations
import hashlib,io,json,sys,urllib.error,urllib.parse,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
from tools.research_cat1880_pixels import metrics
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"data/releases/w19_aku_pal_original_image_receipts.json"
USER_AGENT="HieraticAI-W25-licensed-original-publisher-scan-research/1.0"
def allowed(url,id):
    p=urllib.parse.urlsplit(url)
    return (p.scheme=="https" and p.hostname=="aku-pal.uni-mainz.de" and not p.query and
        not p.fragment and not p.username and not p.password and p.port is None and
        p.path==f"/img/data/ht/scan/ht_{id}_2.webp")
def inspect(raw,sha,bytes_expected):
    if len(raw)!=bytes_expected or hashlib.sha256(raw).hexdigest()!=sha:
        raise ValueError("W19 original publisher WebP bytes mismatch")
    im=Image.open(io.BytesIO(raw))
    if im.format!="WEBP":raise ValueError("original media not a WebP scan")
    if im.width>5000 or im.height>5000:raise ValueError("publisher scan unexpectedly huge")
    g=ImageOps.exif_transpose(im).convert("L").resize((256,256),Image.Resampling.LANCZOS)
    result=metrics(g)
    result["original_width"]=im.width
    result["original_height"]=im.height
    return result
def scan_records(manifest):
    if manifest["record_count"]!=8 or manifest["verified_distinct_media_file_count"]!=15:
        raise ValueError("original source cohort drift")
    results=[]
    for item in manifest["items"]:
        if item["individually_displayed_license"]!="CC BY 4.0":
            raise ValueError("per-item original rights changed")
        for media in item["publisher_media"]:
            if media["image_classification"]!="publication_scan_reproduction":continue
            if not allowed(media["publisher_media_url"],item["id"]):
                raise ValueError("wrong host/item/image role")
            results.append((item,media))
    if len(results)!=5:raise ValueError("W19 five original WebP source scan roles missing")
    return results
def run():
    manifest=json.loads(MANIFEST.read_text("utf8"))
    cohort=scan_records(manifest)
    items=[]
    for item,media in cohort:
        u=media["publisher_media_url"]
        req=urllib.request.Request(u,headers={"User-Agent":USER_AGENT,"Accept":"image/webp"})
        try:
            with urllib.request.urlopen(req,timeout=40) as response:
                if response.status!=200 or response.geturl()!=u:
                    raise ValueError("unexpected source redirect")
                if response.headers.get("Content-Type","").split(";")[0].lower() not in ("image/webp","application/octet-stream"):
                    raise ValueError("invalid original source MIME")
                raw=response.read(4_000_001)
            m=inspect(raw,media["image_sha256"],media["original_response_bytes"])
            items.append({"sign_id":item["id"],"witness":item["physical_witness"],
                "publisher_source_sha256":media["image_sha256"],
                "publisher_original_bytes":len(raw),
                "metrics":m,"image_role":"ORIGINAL_PUBLISHED_HISTORICAL_SCAN",
                "training":False,"benchmark_overlap":"UNKNOWN_QUARANTINED"})
        except (OSError,ValueError,urllib.error.URLError) as exc:
            items.append({"sign_id":item["id"],"witness":item["physical_witness"],
                "status":"BLOCKED","error":str(exc)[:160]})
    ok=sum("metrics" in x for x in items)
    return {"schema_version":"w25-real-akupal-original-scan-pixel-diagnostic/1.0",
        "source_original_scan_targets":5,"source_original_scans_verified":ok,
        "source_physical_support_count":len(set(x["witness"] for x in items)),
        "source_rights":"INDIVIDUAL_CC_BY_4_0_PUBLISHER_METADATA",
        "benchmark":"UNRESOLVED_QUARANTINED",
        "scientific_status":"VERIFIED_REAL_PUBLISHER_SCAN_PIXELS_NOT_READING" if ok==5 else "PARTIAL_OR_BLOCKED",
        "trained_models":0,"image_based_script_recognition_accuracy":None,
        "training_corpus_admitted":False,"independent_gold":False,
        "source_binaries_committed":False,"per_sign":items}
def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    out=run()
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print(json.dumps(out,indent=2,sort_keys=True))
    if out["scientific_status"]!="VERIFIED_REAL_PUBLISHER_SCAN_PIXELS_NOT_READING":
        raise SystemExit("Source originals not completely verified; no claim")
if __name__=="__main__":main()
