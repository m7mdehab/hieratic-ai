"""W19 exact-API individual AKU-PAL artwork acquisition screening.

All public requests constrained to individual Mainz publisher host and verified
item-level CC BY 4.0. Images are hashed in memory only and never exported.
No automatic label gold, ML training, image-text line alignment or release.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ORIGIN="https://aku-pal.uni-mainz.de"
IDS=(6036,2448,23466,6066,32833,56377,5862,5447)
MAX_JSON=160_000
MAX_IMAGE=4_000_000
MAX_LINKS_PER_SIGN=5
USER_AGENT="HieraticAI-W19-original-licensed-publisher-image-evidence/1.0"
ASSET_KEY=re.compile(r"(image|svg|scan|photo|graph|facsim|file|media|drawing|picture|bild|abbild|datei|url|path|uri|src)",re.I)
LICENSE_KEY=re.compile(r"(licen[cs]|lizenz|copyright|rechte|rights)",re.I)
IMAGE_EXT=re.compile(r"\.(?:svg|png|jpg|jpeg|webp|tiff?|gif)(?:\?.*)?$",re.I)


def same_origin(url: str)->bool:
    u=urlparse(url)
    return u.scheme=="https" and u.hostname=="aku-pal.uni-mainz.de" and u.port is None and not u.username and not u.password


def bounded_get(url:str, limit:int, content_types:tuple[str,...])->tuple[bytes,str]:
    if not same_origin(url):raise ValueError("non-publisher host refused")
    if urlparse(url).query or urlparse(url).fragment:raise ValueError("query/fragment rejected")
    req=Request(url,headers={"User-Agent":USER_AGENT,"Accept":"application/json,image/*,image/svg+xml;q=0.8"})
    with urlopen(req,timeout=20) as response:
        if response.status!=200:raise ValueError("non-200 source")
        if not same_origin(response.geturl()):raise ValueError("redirect outside publisher")
        ctype=response.headers.get("content-type","").split(";")[0].strip().lower()
        if not any(ctype==c for c in content_types):
            raise ValueError("unexpected content type: "+ctype)
        body=response.read(limit+1)
    if not 1<=len(body)<=limit:raise ValueError("empty or oversized publisher resource")
    return body,ctype


def surface_keys(obj, prefix="", depth=0)->list[dict]:
    if depth>7:return []
    if isinstance(obj,dict):
        leaves=[]
        for key,val in obj.items():
            p=(prefix+"."+str(key)) if prefix else str(key)
            leaves.extend(surface_keys(val,p,depth+1))
        return leaves
    if isinstance(obj,list):
        a=[]
        for i,val in enumerate(obj[:12]):a.extend(surface_keys(val,prefix+f"[{i}]",depth+1))
        return a
    if isinstance(obj,(str,int,float,bool)) or obj is None:
        v=str(obj) if obj is not None else ""
        return [{"key":prefix,"type":type(obj).__name__,"chars":len(v),
          "safe_metadata_value":v[:180] if (len(v)<220 and (
               LICENSE_KEY.search(prefix) or ASSET_KEY.search(prefix) or
               (prefix.endswith((".id","id")) and len(v)<50))) else None}]
    return []


def candidates_from_metadata(leaves:list[dict])->list[dict]:
    unique=set()
    result=[]
    for leaf in leaves:
        key=leaf["key"]; val=leaf.get("safe_metadata_value")
        if not isinstance(val,str):continue
        if not (ASSET_KEY.search(key) or IMAGE_EXT.search(val)):continue
        if not (val.startswith("/") or val.startswith("https://")):continue
        url=urljoin(ORIGIN,val)
        if urlparse(url).query or urlparse(url).fragment or not same_origin(url):continue
        if url in unique:continue
        unique.add(url)
        result.append({"field":key,"url":url})
    return result[:MAX_LINKS_PER_SIGN]


def inspect_one(rid:int)->dict:
    if rid not in IDS:raise ValueError("not an audited item ID")
    url=ORIGIN+"/api/signs/"+str(rid)
    out={"id":rid,"record_url":url,"record":"UNAVAILABLE",
      "license_per_item_confirmed":False,"source_record_sha256":None,
      "source_binary_images_verified":0,"source_binary_sha256":[],
      "training_admission":False,"gold_admission":False}
    try:
        raw,_=bounded_get(url,MAX_JSON,("application/json",))
        data=json.loads(raw)
        if isinstance(data,list):
            # Publisher may wrap a single complete sign in a JSON array.
            if len(data)==1 and isinstance(data[0],dict):
                data=data[0]
            else:
                matching=[x for x in data if isinstance(x,dict) and
                    str(x.get("id"))==str(rid)]
                if len(matching)==1:
                    data=matching[0]
                else:
                    raise ValueError("unrecognized publisher list schema: "+str(len(data))+
                        " first keys="+str(sorted(data[0].keys())[:14]
                          if data and isinstance(data[0],dict) else
                          (type(data[0]).__name__ if data else "empty")))
        if not isinstance(data,dict):raise ValueError(
            "bad original JSON shape: "+type(data).__name__)
        leaves=surface_keys(data)
        text=raw.decode("utf-8")
        if not re.search(r"(?:\b|_)"+str(rid)+r"(?:\b|_)",text):raise ValueError("item ID not identified")
        rights=[x for x in leaves if LICENSE_KEY.search(x["key"])]
        exact_license=any(re.search(r"\bCC[\s\u00a0-]*BY[\s\u00a0-]*4(?:\.0)?\b",str(x.get("safe_metadata_value") or ""),re.I) for x in rights)
        # Exact publisher-record license, not coincidental external/example license.
        out.update({"record":"VERIFIED_PUBLISHER_JSON","source_record_sha256":hashlib.sha256(raw).hexdigest(),
                    "record_bytes":len(raw),"license_per_item_confirmed":bool(exact_license),
                    "field_keys":[x["key"] for x in leaves][:100],
                    "rights_fields":rights[:20]})
        links=candidates_from_metadata(leaves)
        out["publisher_asset_candidates"]=links
        if not exact_license:
            out["media_status"]="BLOCKED_NOT_CONFIRMED_EXACT_RECORD_RIGHTS"
            return out
        if not links:
            out["media_status"]="NO_EXPLICIT_BINARIES_LINKED_IN_RECORD_JSON"
            return out
        for link in links:
            entry={"field":link["field"],"url":link["url"],"status":"UNVERIFIED"}
            try:
                body,ctype=bounded_get(link["url"],MAX_IMAGE,(
                   "image/svg+xml","image/png","image/jpeg","image/webp",
                   "image/tiff","image/gif"))
                entry.update({"status":"ORIGINAL_PUBLISHER_IMAGE_VERIFIED",
                     "image_sha256":hashlib.sha256(body).hexdigest(),
                     "image_byte_size":len(body),"content_type":ctype,
                     "file_magic_ok": (
                        (ctype=="image/png" and body.startswith(b"\x89PNG\r\n\x1a\n")) or
                        (ctype=="image/jpeg" and body.startswith(b"\xff\xd8")) or
                        (ctype=="image/svg+xml" and b"<svg" in body[:2000]) or
                        (ctype=="image/webp" and body[:4]==b"RIFF") or
                        (ctype=="image/tiff" and body[:4] in (b"II*\x00",b"MM\x00*")) or
                        (ctype=="image/gif" and body[:3]==b"GIF"))})
                if not entry["file_magic_ok"]:entry["status"]="IMAGE_SIGNATURE_MISMATCH"
                if entry["status"]=="ORIGINAL_PUBLISHER_IMAGE_VERIFIED":
                    out["source_binary_images_verified"]+=1
                    out["source_binary_sha256"].append(entry["image_sha256"])
            except (ValueError,HTTPError,URLError,TimeoutError) as e:
                entry["error"]=type(e).__name__+":"+str(e)[:130]
            link["verification"]=entry
        out["media_status"]="BINARY_EVIDENCE_RECORDED" if out["source_binary_images_verified"] else "BINARIES_UNRESOLVED"
    except (ValueError,HTTPError,URLError,TimeoutError,json.JSONDecodeError) as e:
        out["error"]=type(e).__name__+":"+str(e)[:130]
    return out


def run()->dict:
    data=[inspect_one(i) for i in IDS]
    return {"schema_version":"w19-akupal-real-sign-image-evidence/1",
        "scientific_admission":"NOT_AUTHORIZED",
        "source_records_checked":len(data),
        "record_json_verified":sum(x["record"]=="VERIFIED_PUBLISHER_JSON" for x in data),
        "per_item_cc_by_confirmed":sum(x["license_per_item_confirmed"] for x in data),
        "original_image_bytes_verified":sum(x["source_binary_images_verified"] for x in data),
        "original_image_bytes_committed":0,"independent_expert_gold":0,
        "original_manuscript_line_transcriptions":0,
        "benchmark_overlap_status":"UNRESOLVED_QUARANTINED",
        "records":data}


if __name__=="__main__":
    report=run()
    if len(sys.argv)>1:
        from pathlib import Path
        Path(sys.argv[1]).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "record_json_verified":report["record_json_verified"],
        "per_item_cc_by_confirmed":report["per_item_cc_by_confirmed"],
        "original_image_bytes_verified":report["original_image_bytes_verified"],
        "signs":[{"id":x["id"],"fields":x.get("field_keys",[])[:40],
         "rights":x.get("rights_fields",[]),
         "media_status":x.get("media_status"),"asset_candidates":x.get("publisher_asset_candidates",[]),
         "error":x.get("error")}
        for x in report["records"]]},sort_keys=True,ensure_ascii=False))
    if report["record_json_verified"]!=len(IDS):
        raise SystemExit("SOURCE_AUDIT_BLOCKED: not all eight source-specific records verified")

