"""W29-A genuine original Cat1880 CC0 photograph: train CPU spatial denoiser.

No original manuscript reading labels. Original bytes transient; stdout aggregate.
"""
from __future__ import annotations
import argparse
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


def learn(gray:np.ndarray)->dict:
    if gray.shape!=(768,1536):raise ValueError("exact downsampled original size required")
    clean=gray.astype(np.float32)/255.0
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
    clean_targets=clean[yy,xx]
    # Threshold is train-side quantile ONLY, not gold Hieratic ink segmentation.
    threshold=float(np.percentile(clean[:,1:TRAIN_EDGE-1],33))
    comparisons={}
    for sigma in SIGMAS:
        corrupted=noise(clean,sigma,RANDOM_SEED+sigma)
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
                   "spatially_disjoint_with_4px_gap":True,"comparisons":comparisons},
        "negative_controls":controls,
        "learned_from_real_original_pixels":True,
        "self_supervised_synthetic_corruption_target":"original CC0 photo luminance",
        "original_photo_heldout_witness_independent":False,
        "actual_hieratic_sign_transcription_gold":False,
        "hieratic_reading_accuracy":None,
        "source_overlap_with_sealed_test_cleared":False,
        "raw_image_or_patches_committed":False,"weighted_capability_points":0}


def run()->dict:
    raw=original.fetch()
    verified=original.original(raw)
    # Decode original before any model training; no synthetic replacement source.
    gray=ImageOps.exif_transpose(verified).convert("L").resize(OUTPUT_WH,Image.Resampling.LANCZOS)
    return learn(np.asarray(gray,dtype=np.uint8))


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    value=run()
    result=json.dumps(value,indent=2,sort_keys=True)
    if args.output:
        args.output.write_text(result+"\n",encoding="utf-8")
    print(result)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
