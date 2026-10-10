"""W25 genuine CC0 full-photo visual processing, with SHA/rights and provenance gates.

No Hieratic reading/transcription accuracy claims. Uses one single museum physical support.
Original image bytes stay in memory, no original pixels committed/uploaded.
"""
from __future__ import annotations
import argparse,hashlib,json,math,os,re,urllib.request,urllib.error
from io import BytesIO
from pathlib import Path
from PIL import Image,ImageFilter,ImageOps
import numpy as np

ORIGINAL_URL="https://upload.wikimedia.org/wikipedia/commons/b/b1/The_so-called_%27Strike_Papyrus%27_written_by_Amunnakht_-_Museo_Egizio_Turin_C_1880_p01.jpg"
ORIGINAL_SHA256="2f637e7d59785cce7308e478f6a59fb5c54e0ba9c694621e4072c8b2f2594ee5"
ORIGINAL_BYTES=30364719
SOURCE_RECORD="https://commons.wikimedia.org/wiki/File:The_so-called_%27Strike_Papyrus%27_written_by_Amunnakht_-_Museo_Egizio_Turin_C_1880_p01.jpg"
EXPECTED_WH=(17704,7983)
MAX_DOWNLOAD_BYTES=32_000_000
MAX_PIXELS=18000*9000

def original(raw:bytes)->Image.Image:
    if len(raw)!=ORIGINAL_BYTES or hashlib.sha256(raw).hexdigest()!=ORIGINAL_SHA256:
        raise ValueError("source original bytes do not match W21 independently verified image")
    if not raw.startswith(b"\xff\xd8"):raise ValueError("no JPEG source signature")
    Image.MAX_IMAGE_PIXELS=MAX_PIXELS
    picture=Image.open(BytesIO(raw))
    if picture.size!=EXPECTED_WH:raise ValueError("W21 original source pixel geometry mismatch")
    return picture

def otsu(arr:np.ndarray)->int:
    hist=np.bincount(arr.ravel(),minlength=256).astype(np.float64)
    total=hist.sum()
    if total==0:raise ValueError("empty image")
    probabilities=hist/total
    omega=np.cumsum(probabilities)
    means=np.cumsum(probabilities*np.arange(256))
    numerator=(means[-1]*omega-means)**2
    denom=omega*(1-omega)
    score=np.zeros(256,dtype=np.float64)
    np.divide(numerator,denom,out=score,where=(denom>1e-12))
    return int(np.argmax(score))

def metrics(gray:Image.Image)->dict:
    a=np.asarray(gray,dtype=np.uint8)
    threshold=otsu(a)
    if a.size<100:raise ValueError("invalid metric image")
    candidate=(a<=threshold) if threshold>0 else (a<0)
    # Mask is *dark pixels*, not reliably classified Egyptian ink.
    h,w=a.shape
    byrow=np.mean(candidate,axis=1)
    bycol=np.mean(candidate,axis=0)
    dx=np.abs(np.diff(a.astype(np.int16),axis=1)).astype(np.float64)
    dy=np.abs(np.diff(a.astype(np.int16),axis=0)).astype(np.float64)
    return {"gray_sha256":hashlib.sha256(a.tobytes()).hexdigest(),
        "width":int(w),"height":int(h),"gray_mean":round(float(a.mean()),6),
        "gray_std":round(float(a.std()),6),
        "otsu_threshold":int(threshold),
        "dark_pixel_fraction":round(float(candidate.mean()),8),
        "row_density_max":round(float(byrow.max()),8),
        "row_density_p95":round(float(np.percentile(byrow,95)),8),
        "column_density_max":round(float(bycol.max()),8),
        "horizontal_abs_gradient_mean":round(float(dx.mean()),6),
        "vertical_abs_gradient_mean":round(float(dy.mean()),6)}

def analyze(raw:bytes,size:tuple[int,int]=(1280,576))->dict:
    src=original(raw)
    # Bound processing resolution and avoid interpreting crop orientation as historical recto/verso.
    frame=ImageOps.exif_transpose(src).convert("L").resize(size,Image.Resampling.LANCZOS)
    base=metrics(frame)
    blank=Image.new("L",size,230)
    # Domain matched deterministic brightness inversion and morphology-destroying tile permutation.
    inverted=ImageOps.invert(frame)
    block=32
    arr=np.asarray(frame).copy()
    h,w=arr.shape
    if w%block or h%block:raise ValueError("tile dimension not divisible by block")
    tiles=arr.reshape(h//block,block,w//block,block).transpose(0,2,1,3).reshape(-1,block,block)
    rng=np.random.default_rng(20261010)
    shuffled=tiles[rng.permutation(len(tiles))].reshape(h//block,w//block,block,block).transpose(0,2,1,3).reshape(h,w)
    # Deterministic pseudo-paper texture control; cannot be called a negative language truth label.
    noise=np.clip(np.random.default_rng(20261011).normal(225,12,(h,w)),0,255).astype(np.uint8)
    comparison={
      "original_authentic_museum_full_photo":base,
      "blank_uniform_no_strokes":metrics(blank),
      "photometric_inversion_same_source":metrics(inverted),
      "tile_scramble_preserves_some_local_strokes":metrics(Image.fromarray(shuffled,"L")),
      "procedural_synthetic_texture_no_original_script":metrics(Image.fromarray(noise,"L"))}
    for key,v in comparison.items():
        if v["width"]!=w or v["height"]!=h:raise AssertionError("mis-sized control")
    if comparison["original_authentic_museum_full_photo"]["gray_sha256"]==comparison["blank_uniform_no_strokes"]["gray_sha256"]:
        raise AssertionError("source accidentally replaced with blank")
    return {"schema_version":"w25-cc0-real-photo-visual-feature-diagnostic/1.0",
      "source_original_CC0_file_page":SOURCE_RECORD,
      "source_sha256":ORIGINAL_SHA256,"source_bytes":ORIGINAL_BYTES,
      "source_dimensions":list(EXPECTED_WH),
      "one_physical_support":"MuseoEgizio:Cat.1880",
      "read_original_full_photo":True,
      "original_raw_image_uploaded":False,"hieratic_transliteration_evaluated":False,
      "script_recognition_accuracy":None,"morphology_is_not_reading":True,
      "benchmark_overlap":"UNKNOWN_QUARANTINED","admit_to_training":False,
      "model_trained":False,"independent_blind_gold":False,
      "diagnostic_pixel_conditions":comparison,
      "scientific_status":"REAL_PIXEL_FEATURES_NOT_READING_MODEL"}

def fetch()->bytes:
    import urllib.parse
    parsed=urllib.parse.urlsplit(ORIGINAL_URL)
    if parsed.scheme!="https" or parsed.hostname!="upload.wikimedia.org":
        raise ValueError("unexpected source host")
    req=urllib.request.Request(ORIGINAL_URL,headers={"User-Agent":"HieraticAI-public-CC0-one-original-readonly-evidence/1.0","Accept":"image/jpeg"})
    with urllib.request.urlopen(req,timeout=65) as rsp:
        if rsp.status!=200 or urllib.parse.urlsplit(rsp.geturl()).hostname!="upload.wikimedia.org":
            raise ValueError("unexpected redirect")
        if rsp.headers.get("Content-Type","").split(";")[0]!="image/jpeg":
            raise ValueError("source mime drift")
        result=rsp.read(MAX_DOWNLOAD_BYTES+1)
    if len(result)>MAX_DOWNLOAD_BYTES:raise ValueError("source exceeds bound")
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    try:
        evidence=analyze(fetch())
    except (urllib.error.URLError,ValueError,OSError) as exc:
        evidence={"schema_version":"w25-cc0-real-photo-visual-feature-diagnostic/1.0",
            "scientific_status":"BLOCKED_ORIGINAL_PIXEL_SOURCE_OR_PREPROCESSING",
            "error_type":type(exc).__name__,"error":str(exc)[:160],
            "source_sha256_expected":ORIGINAL_SHA256,
            "source_verified_in_prior_w21":True,
            "real_image_inference_performed":False,
            "training_admission":False}
    args.output.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print(json.dumps(evidence,indent=2,sort_keys=True))
    if evidence["scientific_status"]!="REAL_PIXEL_FEATURES_NOT_READING_MODEL":
        raise SystemExit("W25 ORIGINAL IMAGE UNAVAILABLE: research fails closed")
if __name__=="__main__":main()
