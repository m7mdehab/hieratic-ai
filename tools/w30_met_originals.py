"""W30: real museum-original papyrus CPU denoiser, train W29 known originals,
test new Met accession IDs only. Prospective rights, full source byte receipt.
"""
from __future__ import annotations
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import argparse,json,urllib.request,urllib.parse
import numpy as np
from PIL import Image,ImageOps,ImageFilter
from tools import w29_cc0_original_vision as w

FREEZE=[
 (546511,"Nine fragments of hieratic text","15.3.1136","train"),
 (554654,"Letter with hieratic inscription","27.3.561a, b","train"),
 (544847,"Letter written in hieratic script on papyrus","27.3.560","test"),
 (555779,"Papyrus fragments inscribed in hieratic","34.1.215a","test"),
]
SOURCE_API="https://collectionapi.metmuseum.org/public/collection/v1/objects/"
IMAGE_PREFIX="/CRDImages/eg/original/"
SIGMAS=(8,16,24)
ALPHAS=(0.001,.01,.1,1.)
MAX_BYTES=36_000_000


def fetch(record):
    object_id,title,accession,role=record
    url=SOURCE_API+str(object_id)
    req=urllib.request.Request(url,headers={"User-Agent":"HieraticAI-W30-public-original-photo-experiment/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=45) as rsp:
        meta=json.loads(rsp.read(200_000))
    if (meta.get("objectID")!=object_id or meta.get("title")!=title
       or str(meta.get("accessionNumber")).strip()!=accession
       or meta.get("isPublicDomain") is not True
       or meta.get("department")!="Egyptian Art"
       or "papyrus" not in str(meta.get("medium","")).casefold()):
        raise ValueError("Original papyrus title/inventory/license failed closed")
    url=meta.get("primaryImage")
    if not isinstance(url,str) or not url:raise ValueError("Public domain museum photo missing")
    parsed=urllib.parse.urlsplit(url)
    if (parsed.scheme!="https" or parsed.hostname!="images.metmuseum.org"
        or not parsed.path.startswith(IMAGE_PREFIX) or parsed.query or parsed.fragment
        or parsed.username or parsed.password or not parsed.path.lower().endswith((".jpg",".jpeg"))):
        raise ValueError("Untrusted museum original JPEG URL")
    safe=parsed._replace(path=urllib.parse.quote(parsed.path,safe="/%-._~")).geturl()
    req=urllib.request.Request(safe,headers={"User-Agent":"HieraticAI-W30-public-original-photo-experiment/1.0"})
    with urllib.request.urlopen(req,timeout=70) as rsp:
        raw=rsp.read(MAX_BYTES+1)
    if not 1000<len(raw)<=MAX_BYTES or raw[:2]!=bytes((255,216)):
        raise ValueError("Missing genuine bounded JPEG source")
    Image.MAX_IMAGE_PIXELS=150_000_000
    with Image.open(BytesIO(raw)) as picture:
        if picture.format!="JPEG" or picture.width*picture.height>150_000_000:
            raise ValueError("Cannot decode bounded original JPEG")
        wh=[picture.width,picture.height]
        im=ImageOps.exif_transpose(picture).convert("L")
        # Aspect preserving resize and no letterbox padding in scoring region.
        scale=1024/max(im.size)
        size=(max(3,round(im.width*scale)),max(3,round(im.height*scale)))
        im=im.resize(size,Image.Resampling.LANCZOS)
        pixels=np.asarray(im,dtype=np.uint8).copy()
    return pixels,{"object_id":object_id,"accession":accession,"title":title,"role":role,
      "public_domain_via_original_museum_API":True,"source_sha256":sha256(raw).hexdigest(),
      "source_bytes":len(raw),"source_geometry_wh":wh,
      "aspect_preserving_working_wh":list(size),"original_api_url":SOURCE_API+str(object_id)}


def samples(pixel,seed):
    clean=pixel.astype(np.float32)/255
    rng=np.random.default_rng(seed)
    yy=rng.integers(1,clean.shape[0]-1,size=18000)
    xx=rng.integers(1,clean.shape[1]-1,size=18000)
    all_x=[];all_y=[]
    for sigma in SIGMAS:
        noisy=w.noise(clean,sigma,seed+sigma)
        all_x.append(w.patch_features(noisy,yy,xx))
        all_y.append(clean[yy,xx])
    return np.concatenate(all_x),np.concatenate(all_y)


def fit_on_sources(train):
    chunks=[samples(a,3000+i) for i,a in enumerate(train)]
    # A fixed 20% of training pairs from development images alone chooses alpha.
    X=np.concatenate([p[0] for p in chunks]);y=np.concatenate([p[1] for p in chunks])
    rng=np.random.default_rng(3007)
    order=rng.permutation(len(y));cut=len(y)//5;dev=order[:cut];fit=order[cut:]
    vals=[]
    for alpha in ALPHAS:
        weights=w.fit(X[fit],y[fit],alpha)
        loss=float(np.mean(abs(np.clip(X[dev]@weights,0,1)-y[dev])))
        vals.append({"alpha":alpha,"dev_mae":round(loss,8)})
    best=min(vals,key=lambda q:(q["dev_mae"],q["alpha"]))["alpha"]
    return w.fit(X,y,best),{"train_pairs":len(y),"alpha":best,"internal_dev":vals}


def eval_image(original,weights,object_id):
    clean=original.astype(np.float32)/255
    yy,xx=np.mgrid[1:clean.shape[0]-1,1:clean.shape[1]-1]
    yy=yy.ravel();xx=xx.ravel()
    truth=clean[yy,xx]
    threshold=float(np.percentile(clean,33))
    out={}
    for sigma in SIGMAS:
        noisy=w.noise(clean,sigma,3000+object_id%10000+sigma)
        X=w.patch_features(noisy,yy,xx)
        pred=np.clip(X@weights,0,1)
        baselines={"noisy":X[:,4],"3x3_mean":X[:,:9].mean(axis=1),"trained_ridge":pred}
        out[str(sigma)]={method:w.report(value,truth,threshold) for method,value in baselines.items()}
        out[str(sigma)]["trained_beats_mean_psnr"]=out[str(sigma)]["trained_ridge"]["psnr_db"]>out[str(sigma)]["3x3_mean"]["psnr_db"]
    return {"object_id":object_id,"valid_unpadded_evaluation_pixels":len(truth),
       "noise_controls":out,"source_is_train_disjoint":True}


def run():
    train=[];test=[];receipts=[]
    for record in FREEZE:
        pixels,receipt=fetch(record)
        receipts.append(receipt)
        (train if record[3]=="train" else test).append((record[0],pixels))
    if len({r["accession"] for r in receipts})!=len(FREEZE) or len(test)!=2:
        raise ValueError("Fewer than two independent new physical supports")
    if len({r["source_sha256"] for r in receipts})!=4:raise ValueError("Duplicate pixels across alleged witnesses")
    weights,trained=fit_on_sources([i for _,i in train])
    result=[eval_image(a,weights,obj) for obj,a in test]
    return {"version":"w30-met-original-physical-holdout-v1","original_museum_pixel_source":True,
       "original_source_rights_public_domain":True,"frozen_original_supports":receipts,
       "train_physical_support_count":2,"test_physical_support_count":2,
       "model":"trained 3x3 Gaussian-corruption ridge restoration",
       "actual_cpu_training":trained,
       "weight_sha256":sha256(weights.astype("<f8").tobytes()).hexdigest(),
       "untouched_new_source_test_results":result,
       "actual_hieratic_transcription_accuracy":None,"expert_sign_gold":False,
       "separate_manuscript_rightholder_free_evaluation":True,
       "publisher_original_pixels_not_committed":True,
       "official_sealed_benchmark_clear":False,"weighted_points_awarded":0}


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path);args=p.parse_args()
    data=run();out=json.dumps(data,indent=2,sort_keys=True)
    if args.output:args.output.write_text(out+"\n")
    print(out)

if __name__=="__main__":main()
