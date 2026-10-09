"""W21 original CC0/photo and historic PDM plate volume read-only byte receipts.

Source files exist only inside the short-lived GitHub runner; NEVER publish,
train, embed or write original source content to repository or artifact.
This is an original-byte *research inspection*, NOT DATA-008 admission or gold.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,subprocess,sys,tempfile,urllib.parse,urllib.request
from pathlib import Path

TITLE_PHOTO="File:The so-called 'Strike Papyrus' written by Amunnakht - Museo Egizio Turin C 1880 p01.jpg"
TITLE_PLATES="File:Papyrus de Turin. (IA papyrusdeturin02muse).pdf"
SOURCES=(
 {"key":"cat1880_new_p01","title":TITLE_PHOTO,"mime":"image/jpeg",
  "max_bytes":43_000_000,"source":"MuseoEgizio:Cat.1880","license":"CC0"},
 {"key":"pleyte_rossi_historical_vol2","title":TITLE_PLATES,"mime":"application/pdf",
  "max_bytes":24_000_000,"source":"PleyteRossi:1869-1876:vol2","license":"PDM"},
)
API="https://commons.wikimedia.org/w/api.php"
USER_AGENT="HieraticAI-R026-original-publicdomain-source-research/1.0 (8-bit-identity-receipt)"
MAX_API=800_000

def url_ok(url:str,media=False)->bool:
    u=urllib.parse.urlsplit(url)
    if u.scheme!="https" or u.username or u.password or u.port or u.fragment:return False
    if media:return u.hostname=="upload.wikimedia.org"
    return u.hostname=="commons.wikimedia.org" and u.path=="/w/api.php"

def http_bytes(url:str,max_bytes:int,*,media=False)->tuple[bytes,str]:
    if not url_ok(url,media):raise ValueError("URL outside approved Wikimedia API/media origin")
    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,
        "Accept":"image/jpeg,application/pdf" if media else "application/json"})
    with urllib.request.urlopen(req,timeout=65) as response:
        if response.status!=200 or not url_ok(response.geturl(),media):
            raise ValueError("unexpected HTTP status or cross-origin redirect")
        content_type=response.headers.get("Content-Type","").split(";")[0].lower().strip()
        body=response.read(max_bytes+1)
    if not 1<=len(body)<=max_bytes:raise ValueError("source response outside bounded size")
    return body,content_type

def first_image_info(title):
    url=API+"?"+urllib.parse.urlencode({"action":"query","format":"json","formatversion":"2",
        "prop":"imageinfo","iiprop":"url|size|sha1|mime|extmetadata","titles":title})
    raw,ctype=http_bytes(url,MAX_API)
    if ctype not in ("application/json","text/json"):
        raise ValueError("metadata response not JSON")
    d=json.loads(raw)
    pages=d["query"]["pages"]
    if len(pages)!=1 or "missing" in pages[0] or pages[0].get("title")!=title:
        raise ValueError("Commons source identity mismatch")
    info=pages[0]["imageinfo"]
    if len(info)!=1:raise ValueError("ambiguous imageinfo")
    src=info[0]
    if src["mime"] not in ("image/jpeg","application/pdf"):raise ValueError("source file MIME unsupported")
    if not url_ok(src["url"],media=True):raise ValueError("unsafe media URL")
    return src,hashlib.sha256(raw).hexdigest()

def license_evidence(item, info):
    fields=info.get("extmetadata",{})
    values={str(k):str(v.get("value") or "") for k,v in fields.items() if isinstance(v,dict)}
    # Distinguish explicitly attributed CC0 from PDM; lexical source licenses
    # alone are NOT proof of approved dataset/annotations or image-to-line gold.
    evidence=" ".join(values.get(k,"") for k in ("LicenseShortName","LicenseUrl","UsageTerms"))
    if item["license"]=="CC0":
        ok=bool(re.search(r"CC0|creativecommons\.org/publicdomain/zero",evidence,re.I))
    else:
        ok=bool(re.search(r"Public domain|publicdomain/mark|PDM",evidence,re.I))
    return ok,values

def inspect(item)->dict:
    out={"key":item["key"],"status":"UNVERIFIED","rights":"UNVERIFIED",
         "admitted_training":False,"matched_physical_line":False,
         "original_sha256":None,"original_bytes":None,
         "rights_and_bytes_are_separate":True,"source_media_original_downloaded":False}
    try:
        meta,api_sha=first_image_info(item["title"])
        rights,rights_fields=license_evidence(item,meta)
        out.update({"title":item["title"],"source":item["source"],
           "api_response_sha256":api_sha,"publisher_sha1":meta.get("sha1"),
           "publisher_size":meta.get("size"),"publisher_mime":meta.get("mime"),
           "media_url":meta["url"],"source_evidence_licence":item["license"],
           "rights_metadata":{k:rights_fields.get(k) for k in
               ("LicenseShortName","LicenseUrl","UsageTerms","AttributionRequired")}})
        if not rights:
            out["status"]="BLOCKED_NO_ITEM_LICENSE_IN_PUBLISHER_RECORD"
            return out
        out["rights"]="INDIVIDUAL_FILE_LICENSE_CONFIRMED_FOR_RESEARCH_INSPECTION"
        if meta["mime"]!=item["mime"]:raise ValueError("original file MIME changed")
        if not (0<meta.get("size",0)<=item["max_bytes"]):raise ValueError("source size metadata outside original limits")
        body,content_type=http_bytes(meta["url"],item["max_bytes"],media=True)
        if content_type!=item["mime"]:raise ValueError("response MIME mismatch")
        if len(body)!=meta["size"]:raise ValueError("publisher byte length mismatch")
        if hashlib.sha1(body).hexdigest()!=meta["sha1"]:raise ValueError("publisher original SHA1 mismatch")
        if item["mime"]=="image/jpeg" and not body.startswith(b"\xff\xd8"):
            raise ValueError("JPEG content signature absent")
        if item["mime"]=="application/pdf" and not body.startswith(b"%PDF-"):
            raise ValueError("PDF content signature absent")
        out.update({"status":"ORIGINAL_FILE_BYTES_SHA256_VERIFIED",
           "source_media_original_downloaded":True,
           "original_sha256":hashlib.sha256(body).hexdigest(),
           "original_bytes":len(body),"original_magic_verified":True})
        with tempfile.TemporaryDirectory(prefix="hieratic_r026_ephemeral_") as folder:
            path=Path(folder)/("photo.jpg" if item["mime"]=="image/jpeg" else "plates.pdf")
            path.write_bytes(body)
            if item["mime"]=="image/jpeg":
                # Original SOF without OCR, imaging model, or source reuse.
                p=2;dims=None
                while p+10<len(body):
                    if body[p]!=0xff:p+=1;continue
                    marker=body[p+1];p+=2
                    if marker in (0xd8,0xd9,0x01) or 0xd0<=marker<=0xd7:continue
                    if p+2>len(body):break
                    seg=int.from_bytes(body[p:p+2],"big")
                    if seg<2 or p+seg>len(body):break
                    if marker in (0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf):
                        dims=[int.from_bytes(body[p+5:p+7],"big"),int.from_bytes(body[p+3:p+5],"big")]
                        break
                    p+=seg
                out["original_pixel_dimensions"]=dims
                if dims is None:raise ValueError("JPEG original pixel geometry unavailable")
            else:
                import fitz
                pdf=fitz.open(str(path))
                out["original_pdf_page_count"]=len(pdf)
                if len(pdf)<150:raise ValueError("Historical 158-plate book PDF unusually short")
                # Derivative contact sheets are low resolution PDM facsimile
                # examination materials, not original source pages/benchmark gold.
                directory=os.environ.get("R026_CONTACT_DIR")
                if directory:
                    from PIL import Image,ImageDraw
                    destination=Path(directory)
                    destination.mkdir(parents=True,exist_ok=True)
                    # Sparse diagnostic plate locator: avoid expensive 240-page
                    # full original book image decompression on hosted CI.
                    for begin in (0,40,80,120):
                        sheet=Image.new("RGB",(8*235,5*305),"white")
                        draw=ImageDraw.Draw(sheet)
                        for offset in range(0,40,4):
                            number=begin+offset
                            if number>=len(pdf):break
                            page=pdf[number]
                            # 0.20 scale is thumbnail-only; no content transcription
                            pix=page.get_pixmap(matrix=fitz.Matrix(0.20,0.20),alpha=False)
                            image=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
                            image.thumbnail((225,275))
                            slot=offset//4
                            x=(slot%8)*235+int((235-image.width)/2)
                            y=(slot//8)*305+22
                            sheet.paste(image,(x,y))
                            draw.text((slot%8*235+8,slot//8*305+4),f"PDF page index: {number}",fill="black")
                        sheet.save(destination/f"historical_pdm_pdf_pages_{begin:03d}_{min(begin+39,len(pdf)-1):03d}.jpg",quality=77,optimize=True)
                    out["research_only_thumbnail_grids_generated"]=len(list(destination.glob("*.jpg")))
                pdf.close()
        out["source_pixels_not_exported"]=True
    except (ValueError,KeyError,TypeError,TimeoutError,urllib.error.URLError,json.JSONDecodeError) as exc:
        out["status"]="BLOCKED_ORIGINAL_SOURCE_EVIDENCE"
        out["error"]=type(exc).__name__+":"+str(exc)[:220]
        out["admitted_training"]=False
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    items=[inspect(s) for s in SOURCES]
    out={"protocol":"r026-original-pixel-and-pdm-book-byte-evidence/1.0",
         "original_targets":len(SOURCES),
         "source_files_verified":sum(z["status"]=="ORIGINAL_FILE_BYTES_SHA256_VERIFIED" for z in items),
         "original_image_line_correspondences_certified":0,
         "independent_egyptologist_reviewers":0,
         "data008_production_admission":False,
         "benchmark_overlap":"UNRESOLVED_QUARANTINED",
         "asset_storage":"EPHEMERAL_RUNNER_DISCARDED",
         "source_original_media_bytes_published":0,"sources":items}
    s=json.dumps(out,sort_keys=True,indent=2,ensure_ascii=False)+"\n"
    if args.output:args.output.write_text(s,encoding="utf8")
    print(s)
    if out["source_files_verified"]!=2:
        raise SystemExit("SOURCE_BOUNDARY_NOT_MET: one or both original source assets not verified")
if __name__=="__main__":main()
