"""W17 read-only bounded AKU-PAL 8-item source endpoint probe.

No image downloads or training admission. This is source-page byte verification
and API discovery only, never scholarly sign-gold certification.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

RECORDS = (6036,2448,23466,6066,32833,56377,5862,5447)
ORIGIN = "https://aku-pal.uni-mainz.de"
MAX_PAGE = 900_000
MAX_API = 200_000


def page_probe(url: str, max_bytes: int = MAX_PAGE) -> dict:
    if urlparse(url).scheme != "https" or urlparse(url).netloc != "aku-pal.uni-mainz.de":
        raise ValueError("External source origin refused")
    request = urllib.request.Request(url, headers={
        "User-Agent": "HieraticAI-Original-Source-Evidence-W17/1.0 (8-item scholarly metadata screening)",
        "Accept": "text/html,application/json;q=0.9",
    })
    result = {"url": url, "status": "UNAVAILABLE", "original_bytes": 0,
              "original_sha256": None, "contains_ccby": False,
              "contains_record_id": False, "original_file_type": None,
              "html_preview_has_license": False,
              "image_reference_count": None, "original_image_bytes_acquired": 0}
    try:
        with urllib.request.urlopen(request,timeout=18) as response:
            if response.geturl().split("?")[0].rstrip("/") != url.rstrip("/"):
                raise ValueError("Unexpected redirect/source identity")
            if response.status != 200:
                raise ValueError("Source status not 200")
            raw = response.read(max_bytes+1)
            if len(raw)>max_bytes or not raw:
                raise ValueError("Source response size outside bounded protocol")
            typ = response.headers.get("content-type", "").split(";")[0]
        text = raw.decode("utf-8","replace")
        result.update({
            "status":"HTTP_200_SOURCE_BYTES_VERIFIED",
            "original_bytes":len(raw),
            "original_sha256":hashlib.sha256(raw).hexdigest(),
            "original_file_type":typ,
            "contains_ccby":bool(re.search(r"CC[ \u00a0-]*BY[ \u00a0-]*4(?:\.0)?",text,re.I)),
            "contains_record_id":str(url.rsplit("/",1)[-1]) in text,
            "html_preview_has_license":"Lizenz" in text or "license" in text.lower(),
            "image_reference_count":len(re.findall(r"<img\b",text,re.I)),
        })
    except (ValueError,TimeoutError,urllib.error.URLError,UnicodeError) as exc:
        result["error"]=type(exc).__name__+":"+str(exc)[:170]
    return result


def run() -> dict:
    result={"schema_version":"w17-akupal-probe/1.0.0",
            "classification":"NONADMISSIBLE_EVIDENCE_DISCOVERY_ONLY",
            "source_host":"aku-pal.uni-mainz.de",
            "disclosure":"No image bytes, no target sign labels, no external model use",
            "individual_pages":[page_probe(ORIGIN+"/signs/"+str(i)) for i in RECORDS],
            "official_sign_api_records":[page_probe(ORIGIN+"/api/signs/"+str(i),MAX_API)
                                         for i in RECORDS],
            "sample_api_endpoints":[
              page_probe(ORIGIN+"/api/graphemes/291",MAX_API),
              page_probe(ORIGIN+"/api/hieratograms/6036",MAX_API),
            ]}
    result["spa_shell_is_not_sign_metadata"]=(len({r["original_sha256"] for r in result["individual_pages"]}) == 1 and not any(r["contains_record_id"] for r in result["individual_pages"]))
    result["official_per_item_source_json_verified"]=sum(r["status"]=="HTTP_200_SOURCE_BYTES_VERIFIED" and r["contains_ccby"] and r["contains_record_id"] for r in result["official_sign_api_records"])
    result["source_pages_verified"]=sum(x["status"]=="HTTP_200_SOURCE_BYTES_VERIFIED"
                                      for x in result["individual_pages"])
    result["no_source_images_acquired"]=True
    result["no_trainable_gold_admitted"]=True
    return result


if __name__=="__main__":
    x=run()
    out=json.dumps(x,indent=2,sort_keys=True)+"\n"
    if len(sys.argv)>1:
        from pathlib import Path
        Path(sys.argv[1]).write_text(out,encoding="utf-8")
    print(out)
