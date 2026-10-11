"""W29-A genuine original Cat1880 CC0 photograph: train CPU spatial denoiser.

No original manuscript reading labels. Original bytes transient; stdout aggregate.
"""
from __future__ import annotations
import argparse,io,urllib.request,urllib.parse
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from tools import research_cat1880_pixels as original

MODEL_VERSION="W29-CC0-SPATIAL-RIDGE-DENOISER/1"
RANDOM_SEED=2901
OUTPUT_WH=(1536,768)
TRAIN_EDGE=1024
TEST_START=1028
SIGMAS=(8,16,24)
ALPHAS=(0.001,0.01,0.1,1.0)
FEATURES=10
TRAIN_SAMPLES=36000


def noise(clean:np.ndarray,sigma:int,seed:int)->np.ndarray:
    rng=np.random.default_rng(seed)
    return np.clip(clean+rng.normal(0,sigma/255.0,clean.shape).astype(np.float32),0,1)


def patch_features(img:np.ndarray,ys:np.ndarray,xs:np.ndarray)->np.ndarray:
    if img.ndim!=2 or xs.size!=ys.size or xs.size==0:raise ValueError("invalid pixel features")
    if np.any(xs<1) or np.any(xs>=img.shape[1]-1) or np.any(ys<1) or np.any(ys>=img.shape[0]-1):
        raise ValueError("patch outside valid image")
    out=np.empty((len(xs),FEATURES),np.float64)
    for j,(dy,dx) in enumerate(((dy,dx) for dy in (-1,0,1) for dx in (-1,0,1))):
        out[:,j]=img[ys+dy,xs+dx]
    out[:,9]=1.
    return out


def fit(X:np.ndarray,y:np.ndarray,alpha:float)->np.ndarray:
    gram=X.T@X
    regularizer=np.eye(FEATURES)
    regularizer[-1,-1]=0
    return np.linalg.solve(gram+alpha*regularizer+np.eye(FEATURES)*1e-9,X.T@y)


def report(pred:np.ndarray,truth:np.ndarray,threshold:float)->dict:
    err=pred.astype(np.float64)-truth.astype(np.float64)
    mse=float(np.mean(err*err))
    return {"mae":round(float(np.mean(np.abs(err))),8),
            "psnr_db":round(float(-10*np.log10(max(mse,1e-12))),5),
            "mse":round(mse,9),
            "dark_fraction_abs_error":round(float(abs(np.mean(pred<threshold)-np.mean(truth<threshold))),8)}


def learn(gray:np.ndarray,test_gray:np.ndarray|None=None)->dict:
    if gray.shape!=(768,1536):raise ValueError("exact downsampled original size required")
    if test_gray is not None and test_gray.shape!=(768,1536):
        raise ValueError("second original image must have same bounded working size")
    clean=gray.astype(np.float32)/255.0
    independent_clean=(test_gray.astype(np.float32)/255.0) if test_gray is not None else clean
    rng=np.random.default_rng(RANDOM_SEED)
    training_idx=rng.choice((gray.shape[0]-2)*(TRAIN_EDGE-2),TRAIN_SAMPLES,replace=False)
    ty=(training_idx//(TRAIN_EDGE-2)+1).astype(np.int64)
    tx=(training_idx%(TRAIN_EDGE-2)+1).astype(np.int64)
    train_X=[];train_y=[]
    for sigma in SIGMAS:
        corrupted=noise(clean,sigma,RANDOM_SEED+sigma)
        train_X.append(patch_features(corrupted,ty,tx))
        train_y.append(clean[ty,tx].astype(np.float64))
    X=np.concatenate(train_X);y=np.concatenate(train_y)
    # Fixed, deterministically selected internal 20% dev, no test pixels used.
    perm=rng.permutation(X.shape[0])
    d=perm[:X.shape[0]//5];t=perm[X.shape[0]//5:]
    best=(float("inf"),None,None)
    for alpha in ALPHAS:
        w=fit(X[t],y[t],alpha)
        error=float(np.mean(np.abs(np.clip(X[d]@w,0,1)-y[d])))
        if error<best[0]:best=(error,alpha,w)
    # Refit only on training pixels after dev-only alpha selection.
    _,alpha,_=best
    weights=fit(X,y,alpha)
    test_y,test_x=np.mgrid[1:767,TEST_START:1535]
    yy=test_y.reshape(-1);xx=test_x.reshape(-1)
    if yy.size!=766*507 or xx.min()<=TRAIN_EDGE:
        raise ValueError("train/test spatial overlap")
    clean_targets=independent_clean[yy,xx]
    # Threshold is train-side quantile ONLY, not gold Hieratic ink segmentation.
    threshold=float(np.percentile(clean[:,1:TRAIN_EDGE-1],33))
    comparisons={}
    for sigma in SIGMAS:
        corrupted=noise(independent_clean,sigma,RANDOM_SEED+sigma)
        test_X=patch_features(corrupted,yy,xx)
        smooth=np.mean(test_X[:,:9],axis=1)
        reg=np.clip(test_X@weights,0,1)
        center=test_X[:,4]
        comparisons[str(sigma)]={
          "noisy_identity":report(center,clean_targets,threshold),
          "fixed_3x3_mean":report(smooth,clean_targets,threshold),
          "fitted_3x3_ridge":report(reg,clean_targets,threshold),
          "ridge_beats_untrained_identity_mae":bool(np.mean(abs(reg-clean_targets))<np.mean(abs(center-clean_targets))),
        }
    # Fixed non-image language controls; results are geometry diagnostics only.
    blank=np.full_like(clean,0.9)
    inverted=1.0-clean
    controls={"blank_constant_unique_luminance":int(np.unique(blank).size),
              "inversion_mean_difference":round(float(np.mean(abs(inverted-clean))),6),
              "source_clean_test_has_nonzero_variance":bool(np.std(clean_targets)>0.01)}
    return {"version":MODEL_VERSION,"original_photo_CC0_sha256":original.ORIGINAL_SHA256,
        "source_license_file_page":original.SOURCE_RECORD,
        "one_physical_support":"MuseoEgizio:Cat.1880",
        "raw_original_dimensions":list(original.EXPECTED_WH),
        "working_resize_wh":list(OUTPUT_WH),
        "train": {"x_range":[1,TRAIN_EDGE-2],"sampled_pixels":TRAIN_SAMPLES*3,
                  "noise_sigmas":list(SIGMAS),"selected_train_only_ridge_alpha":alpha,
                  "internal_dev_MAE":round(best[0],7),
                  "learned_weights_sha256":sha256(weights.astype("<f8").tobytes()).hexdigest()},
        "heldout":{"x_range":[TEST_START,1534],"pixels_per_sigma":int(yy.size),
                   "spatially_disjoint_with_4px_gap":True,
                   "heldout_different_physical_museum_object":test_gray is not None,
                   "comparisons":comparisons},
        "negative_controls":controls,
        "learned_from_real_original_pixels":True,
        "self_supervised_synthetic_corruption_target":"original CC0 photo luminance",
        "original_photo_heldout_witness_independent":test_gray is not None,
        "actual_hieratic_sign_transcription_gold":False,
        "hieratic_reading_accuracy":None,
        "source_overlap_with_sealed_test_cleared":False,
        "raw_image_or_patches_committed":False,"weighted_capability_points":0}


MET_OBJECTS=(
    (546511,"Nine fragments of hieratic text","15.3.1136"),
    (554654,"Letter with hieratic inscription","27.3.561a, b"),
)
MET_API_ROOT="https://collectionapi.metmuseum.org/public/collection/v1/objects/"
MET_IMAGE_HOST="images.metmuseum.org"
MET_IMAGE_PATH="/CRDImages/eg/original/"


def met_original(object_id:int,expected_title:str)->tuple[bytes,dict]:
    if object_id not in {x[0] for x in MET_OBJECTS}:
        raise ValueError("Unexpected non-frozen museum object")
    url=MET_API_ROOT+str(object_id)
    with urllib.request.urlopen(urllib.request.Request(url,headers={
        "User-Agent":"HieraticAI-W29-original-met-open-access-study/1.0",
        "Accept":"application/json"}),timeout=40) as response:
        if response.status!=200:
            raise ValueError("Met original public API did not return 200")
        metadata=json.loads(response.read(200_000))
    if (metadata.get("objectID")!=object_id or
        metadata.get("isPublicDomain") is not True or
        metadata.get("title")!=expected_title or
        metadata.get("department")!="Egyptian Art" or
        "papyrus" not in str(metadata.get("medium","")).casefold()):
        raise ValueError("Met original public domain identity/medium or rights not attested")
    image_url=metadata.get("primaryImage")
    if not isinstance(image_url,str) or not image_url:
        raise ValueError("Public domain original has no downloadable image")
    info=urllib.parse.urlsplit(image_url)
    if (info.scheme!="https" or info.hostname!=MET_IMAGE_HOST
        or info.username or info.password or info.query or info.fragment
        or not info.path.startswith(MET_IMAGE_PATH)
        or not info.path.lower().endswith((".jpg",".jpeg"))):
        raise ValueError("Met original image URL host/path/format not trusted")
    with urllib.request.urlopen(urllib.request.Request(image_url,headers={
        "User-Agent":"HieraticAI-W29-original-met-open-access-study/1.0",
        "Accept":"image/jpeg"}),timeout=65) as response:
        if response.status!=200:
            raise ValueError("Met original photo response not successful")
        raw=response.read(36_000_001)
    if not 1000<len(raw)<=36_000_000 or raw[:2]!=b"\\xff\\xd8":
        raise ValueError("Original Met public photo JPEG bytes missing/too large")
    return raw,{"object_id":object_id,"accession":metadata.get("accessionNumber"),
                "title":expected_title,"rights_met_is_public_domain":True,
                "object_api":url,"original_photo_url":image_url,
                "original_photo_sha256":sha256(raw).hexdigest(),"original_photo_bytes":len(raw)}


def run_met()->dict:
    assets=[]
    gray=[]
    for object_id,title,accession in MET_OBJECTS:
        raw,record=met_original(object_id,title)
        if str(record["accession"]).strip()!=accession:
            raise ValueError("Frozen original Met accession drift")
        Image.MAX_IMAGE_PIXELS=200_000_000
        with Image.open(io.BytesIO(raw)) as image:
            if image.format!="JPEG" or image.width*image.height>200_000_000:
                raise ValueError("Original Met source was not bounded JPEG image")
            record["original_photo_dimensions"]=[image.width,image.height]
            pixels=ImageOps.exif_transpose(image).convert("L").resize(
                OUTPUT_WH,Image.Resampling.LANCZOS)
            gray.append(np.asarray(pixels,dtype=np.uint8))
        assets.append(record)
    result=learn(gray[0],gray[1])
    result.update({"source":"Met Museum two genuine CC0 original Hieratic papyrus photographs",
        "source_met_open_access_policy":"https://www.metmuseum.org/about-the-met/policies-and-documents/open-access",
        "source_originals":assets,
        "physical_support_train":"Met:15.3.1136",
        "physical_support_test":"Met:27.3.561a,b",
        "train_test_physical_source_disjoint":True,
        "original_photo_CC0_sha256":None,
        "one_physical_support":None,
        "raw_original_dimensions":None,
        "source_license_file_page":None,
        "heldout_different_physical_papyrus":True,
        "model_execution":"genuine original independent Met photos; not Hieratic text recognition"})
    return result


def run()->dict:
    raw=original.fetch()
    verified=original.original(raw)
    # Decode original before any model training; no synthetic replacement source.
    gray=ImageOps.exif_transpose(verified).convert("L").resize(OUTPUT_WH,Image.Resampling.LANCZOS)
    return learn(np.asarray(gray,dtype=np.uint8))


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path)
    p.add_argument("--met-two-originals",action="store_true")
    args=p.parse_args()
    value=run_met() if args.met_two_originals else run()
    result=json.dumps(value,indent=2,sort_keys=True)
    if args.output:
        args.output.write_text(result+"\n",encoding="utf-8")
    print(result)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
