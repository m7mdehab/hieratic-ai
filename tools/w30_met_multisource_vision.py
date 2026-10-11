"""W30 A actual PUBLIC-DOMAIN original Met photo CPU denoising model experiment.

New heldout original physical accessions frozen before first image access.
Resized photos retain aspect, zero original photo bytes stored or uploaded.
"""
from __future__ import annotations
import argparse,hashlib,io,json,urllib.parse,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
from tools import w29_cc0_original_vision as baseline

TRAIN={
 546511:("Nine fragments of hieratic text","15.3.1136"),
 554654:("Letter with hieratic inscription","27.3.561a, b"),
 545445:("Heqanakht Letter I","22.3.516"),
}
TEST={
 544847:("Letter written in hieratic script on papyrus","27.3.560"),
 549250:("Hieratic Papyrus fragment","O.C.3569"),
}
DIM=512
SIGMAS=(8,16,24)
ALPHAS=(0.01,0.1,1.,10.)
SOURCE_API="https://collectionapi.metmuseum.org/public/collection/v1/objects/"
ORIGINAL_PREFIX="/CRDImages/eg/original/"
VERSION="W30-MET-ORIGINAL-5-OBJECT-MASKED-NONLINEAR-RIDGE/1"

def acquire(object_id:int)->tuple[np.ndarray,np.ndarray,dict]:
    if object_id not in TRAIN and object_id not in TEST:raise ValueError("Unfrozen Met object")
    title,accession=(TRAIN|TEST)[object_id]
    with urllib.request.urlopen(urllib.request.Request(SOURCE_API+str(object_id),headers={
        "User-Agent":"HieraticAI-W30-open-met-papyrus-cpu/1.0"}),timeout=35) as rsp:
        if rsp.status!=200:raise ValueError("Official Met public API not success")
        data=json.loads(rsp.read(200_000))
    if (data.get("objectID")!=object_id or data.get("department")!="Egyptian Art" or
        data.get("isPublicDomain") is not True or data.get("title")!=title or
        str(data.get("accessionNumber","")).strip()!=accession or
        "papyrus" not in str(data.get("medium","")).casefold()):
        raise ValueError("Original Met identity/right/medium evidence missing")
    link=data.get("primaryImage")
    if not isinstance(link,str):raise ValueError("No original public photo")
    url=urllib.parse.urlsplit(link)
    if (url.scheme!="https" or url.hostname!="images.metmuseum.org" or url.port is not None
        or url.username or url.password or url.query or url.fragment
        or not url.path.startswith(ORIGINAL_PREFIX)
        or not url.path.lower().endswith((".jpg",".jpeg"))):
        raise ValueError("Untrusted original photo provider path")
    safe=url._replace(path=urllib.parse.quote(url.path,safe="/%-._~")).geturl()
    with urllib.request.urlopen(urllib.request.Request(safe,headers={
       "User-Agent":"HieraticAI-W30-open-met-papyrus-cpu/1.0","Accept":"image/jpeg"}),timeout=60) as rsp:
        if rsp.status!=200:raise ValueError("Official original JPEG not found")
        raw=rsp.read(32_000_001)
    if not 1000<len(raw)<=32_000_000 or raw[:2]!=bytes((255,216)):
        raise ValueError("Expected capped genuine JPEG original bytes")
    Image.MAX_IMAGE_PIXELS=180_000_000
    with Image.open(io.BytesIO(raw)) as im:
        if im.format!="JPEG" or im.width*im.height>180_000_000:
            raise ValueError("Invalid original JPEG geometry")
        wh=(im.width,im.height)
        photo=ImageOps.contain(ImageOps.exif_transpose(im).convert("L"),
                                (DIM-4,DIM-4),Image.Resampling.LANCZOS)
    x0=(DIM-photo.width)//2
    y0=(DIM-photo.height)//2
    frame=np.full((DIM,DIM),230,dtype=np.uint8)
    frame[y0:y0+photo.height,x0:x0+photo.width]=np.asarray(photo)
    mask=np.zeros_like(frame,dtype=bool)
    mask[y0+2:y0+photo.height-2,x0+2:x0+photo.width-2]=True
    if not np.any(mask):raise ValueError("Original photo too small for heldout interior")
    return frame,mask,{"met_object_id":object_id,"title":title,"accession":accession,
        "declared_public_domain":True,"official_source":SOURCE_API+str(object_id),
        "original_image_url":link,"original_original_dimensions":list(wh),
        "original_photo_bytes":len(raw),"original_sha256":hashlib.sha256(raw).hexdigest(),
        "working_canvas":[DIM,DIM],"working_photo_roi":[x0,y0,photo.width,photo.height],
        "valid_nonpadding_interior":int(mask.sum())}

def features(noisy:np.ndarray,y:np.ndarray,x:np.ndarray,nonlinear:bool)->np.ndarray:
    base=baseline.patch_features(noisy,y,x)
    if not nonlinear:return base
    a=base[:,:9]
    # Quadratic nonlinear intensity interactions and local variance/edge.
    center=a[:,4];mean=a.mean(axis=1)
    variance=((a-mean[:,None])**2).mean(axis=1)
    dx=(a[:,5]-a[:,3]);dy=(a[:,7]-a[:,1])
    return np.column_stack((a,a*a,variance,abs(dx),abs(dy),np.ones(len(x))))

def ridge(X:np.ndarray,target:np.ndarray,alpha:float)->np.ndarray:
    reg=np.eye(X.shape[1]);reg[-1,-1]=0
    gram=X.T@X
    return np.linalg.solve(gram+alpha*reg+np.eye(X.shape[1])*1e-8,X.T@target)

def pixel_stats(p:np.ndarray,t:np.ndarray)->dict:
    mse=float(np.mean((p-t)**2))
    return {"mae":round(float(np.mean(abs(p-t))),8),
            "psnr_db":round(float(-10*np.log10(max(mse,1e-12))),5),
            "mse":round(mse,9)}

def learn(images:dict[int,tuple[np.ndarray,np.ndarray,dict]])->dict:
    if set(images)!=(set(TRAIN)|set(TEST)):raise ValueError("Exactly five frozen original rights-verified objects required")
    rng=np.random.default_rng(3001)
    x_train={False:[],True:[]};labels=[]
    for object_id in TRAIN:
        clean8,mask,_=images[object_id]
        clean=clean8.astype(np.float32)/255.
        ys,xs=np.where(mask)
        take=rng.choice(len(xs),12000,replace=False)
        ys=ys[take];xs=xs[take]
        for sigma in SIGMAS:
            corrupted=baseline.noise(clean,sigma,3001+object_id+sigma)
            for nonlinear in (False,True):
                x_train[nonlinear].append(features(corrupted,ys,xs,nonlinear))
            labels.append(clean[ys,xs])
    targets=np.concatenate(labels).astype(np.float64)
    X={k:np.concatenate(v,axis=0) for k,v in x_train.items()}
    dev=rng.permutation(len(targets))
    cut=len(dev)//5;t=dev[cut:];d=dev[:cut]
    trained={};hyper={}
    for nonlin in (False,True):
        candidates=[]
        for alpha in ALPHAS:
            w=ridge(X[nonlin][t],targets[t],alpha)
            err=float(np.mean(abs(np.clip(X[nonlin][d]@w,0,1)-targets[d])))
            candidates.append((err,alpha))
        error,selected=min(candidates,key=lambda z:(z[0],z[1]))
        trained[nonlin]=ridge(X[nonlin],targets,selected)
        hyper["quadratic" if nonlin else "linear"]={"train_dev_mae":round(error,8),
            "alpha":selected,"weights_sha256":hashlib.sha256(trained[nonlin].astype("<f8").tobytes()).hexdigest()}
    results={};diffs=[]
    for object_id in TEST:
        clean8,mask,meta=images[object_id]
        clean=clean8.astype(np.float32)/255.
        ys,xs=np.where(mask)
        truth=clean[ys,xs].astype(np.float64)
        values={}
        for sigma in SIGMAS:
            corrupted=baseline.noise(clean,sigma,3001+object_id+sigma)
            Xlin=features(corrupted,ys,xs,False)
            Xnon=features(corrupted,ys,xs,True)
            raw=Xlin[:,4]
            mean=Xlin[:,:9].mean(axis=1)
            median=np.median(Xlin[:,:9],axis=1)
            linear=np.clip(Xlin@trained[False],0,1)
            nonlinear=np.clip(Xnon@trained[True],0,1)
            trial={"noisy_identity":raw,"fixed_3x3_mean":mean,"fixed_3x3_median":median,
                   "trained_linear_ridge":linear,"trained_quadratic_ridge":nonlinear}
            values[str(sigma)]={name:pixel_stats(val,truth) for name,val in trial.items()}
            values[str(sigma)]["nonlinear_beats_best_untrained_mae"]=bool(
                values[str(sigma)]["trained_quadratic_ridge"]["mae"] <
                min(values[str(sigma)]["fixed_3x3_median"]["mae"],
                    values[str(sigma)]["fixed_3x3_mean"]["mae"]))
            diffs.append(values[str(sigma)]["trained_quadratic_ridge"]["mae"]-
                min(values[str(sigma)]["fixed_3x3_mean"]["mae"],values[str(sigma)]["fixed_3x3_median"]["mae"]))
        results[str(object_id)]={"physical_accession":meta["accession"],"valid_photo_test_pixels":len(truth),
                                "source_original_sha256":meta["original_sha256"],"noise_trials":values}
    return {"protocol":VERSION,"original_museum_photographs_used":True,
        "original_photo_permissions":"Met API Public Domain individually checked",
        "source_receipts":{str(k):meta for k,(_,_,meta) in images.items()},
        "three_train_original_object_ids":list(TRAIN),"two_heldout_original_object_ids":list(TEST),
        "train_source_pixel_samples":len(targets),"train_source_images":3,"heldout_source_images":2,
        "same_archive_or_scribe_independence_verified":False,
        "train_hyperparameter_selected_without_test_image":True,
        "learned_models":hyper,"heldout":results,
        "quadratic_beats_fixed_mean_median_all_six_conditions":bool(all(x<0 for x in diffs)),
        "unverified_ink_stroke_segmentation_accuracy":None,
        "transliteration_reading_accuracy":None,
        "benchmark_source_independence_established":False,
        "raw_photo_or_patch_pixels_committed":False,
        "weighted_reading_capability_points":0}

def run()->dict:
    images={}
    for object_id in (*TRAIN,*TEST):
        images[object_id]=acquire(object_id)
    return learn(images)

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    out=run()
    blob=json.dumps(out,sort_keys=True,indent=2)
    if args.output:args.output.write_text(blob+"\n",encoding="utf-8")
    print(blob)

if __name__=="__main__":main()
