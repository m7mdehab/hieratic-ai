"""W29 B actual Tokyo IIIF printed palaeography supervised CPU sign learning.

Original licensed historical book sign pixels only, never original papyrus photo
or sealed benchmark. Book *volume* holdout; no claim independent physical scribe.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from hashlib import sha256
import argparse,io,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps,ImageEnhance,ImageFilter
from tools import research_hpdb_original_pixels as source

LABELS=tuple(source.LABELS)
TRAIN_VOLUMES=(1,2)
TEST_VOLUME=3
CAP_PER_LABEL_VOLUME=3
ALPHAS=(0.01,0.1,1.,10.)
PROTOCOL="W29-TOKYO-PRINTED-REAL-PIXELS-RIDGE-HOG/1"
SEED=2902


def frozen(rows:list[dict])->list[dict]:
    result=[]
    for label in LABELS:
        for v in (1,2,3):
            group=sorted((x for x in rows if x.get("single_sign")==label and x.get("vol")==v
                 and x.get("kind")=="Main" and x.get("iiif_ref")),key=lambda x:str(x["id"]))
            if not group:raise source.SourceError(f"Unavailable printed sign {label} vol {v}")
            for row in group[:CAP_PER_LABEL_VOLUME]:
                source.verify_iiif_url(row["iiif_ref"])
                result.append({"item_id":str(row["id"]),"label":label,"volume":v,
                    "printed_page":int(row["page"]),"url":row["iiif_ref"],
                    "source_proxy":f"MOLLER-V{v}-P{int(row['page']):03d}"})
    if len({x["item_id"] for x in result})!=len(result) or len(result)<24:
        raise source.SourceError("Duplicate sign source IDs or inadequate cohort")
    train={x["source_proxy"] for x in result if x["volume"] in TRAIN_VOLUMES}
    test={x["source_proxy"] for x in result if x["volume"]==TEST_VOLUME}
    if train&test:raise source.SourceError("Historical volume / page source overlap")
    return result


def gray(raw:bytes)->Image.Image:
    with Image.open(io.BytesIO(raw)) as im:
        if im.format!="JPEG" or im.width*im.height>source.MAX_PIXEL_AREA:
            raise source.SourceError("Missing original JPEG or oversized source pixels")
        return ImageOps.autocontrast(im.convert("L")).resize((32,32),Image.Resampling.LANCZOS)


def hog(frame:Image.Image)->np.ndarray:
    if frame.size!=(32,32):raise ValueError("32 pixel source required")
    a=np.asarray(frame,dtype=np.float64)/255
    gy,gx=np.gradient(a)
    angle=(np.arctan2(gy,gx)+np.pi)%(2*np.pi)
    bins=np.minimum(7,(angle/(2*np.pi)*8).astype(np.int32))
    mag=np.sqrt(gx*gx+gy*gy)
    hist=[]
    for cy in range(4):
        for cx in range(4):
            r=slice(cy*8,(cy+1)*8);c=slice(cx*8,(cx+1)*8)
            hist.extend(np.bincount(bins[r,c].ravel(),weights=mag[r,c].ravel(),minlength=8))
    # Source-colour and ink-projection context; all features from original pixels.
    line=np.r_[a.mean(axis=1)[::2],a.mean(axis=0)[::2]]
    ink=(a<np.quantile(a,.4)).astype(np.float64)
    density=np.r_[ink.mean(axis=1)[::2],ink.mean(axis=0)[::2]]
    feat=np.r_[hist,line,density]
    return feat/(np.linalg.norm(feat)+1e-12)


def training(X:np.ndarray,y:np.ndarray,alpha:float)->tuple[np.ndarray,np.ndarray]:
    ymat=np.zeros((len(y),len(LABELS)),np.float64)
    for i,label in enumerate(y):ymat[i,LABELS.index(label)]=1.
    mean=np.mean(X,axis=0)
    centered=X-mean
    gram=centered.T@centered
    # primal or dual, dual is substantially cheaper for small sign cohorts.
    kernel=centered@centered.T
    coef=centered.T@np.linalg.solve(kernel+alpha*np.eye(len(y)),ymat)
    intercept=ymat.mean(axis=0)
    return coef,intercept-coef.T@mean


def predict(X:np.ndarray,fit:tuple[np.ndarray,np.ndarray])->np.ndarray:
    w,b=fit
    return np.argmax(X@w+b,axis=1)


def nn(Xtr:np.ndarray,ytr:np.ndarray,Xtest:np.ndarray)->np.ndarray:
    dist=((Xtest[:,None,:]-Xtr[None,:,:])**2).sum(axis=2)
    return ytr[np.argmin(dist,axis=1)]


def centroids(Xtr:np.ndarray,ytr:np.ndarray,Xtest:np.ndarray)->np.ndarray:
    prototype=np.array([Xtr[ytr==idx].mean(axis=0) for idx in range(len(LABELS))])
    return np.argmin(((Xtest[:,None,:]-prototype[None,:,:])**2).sum(axis=2),axis=1)


def summarize(pred:np.ndarray,gold:np.ndarray,ids:list[dict])->dict:
    counts=Counter();correct=Counter()
    for p,y,row in zip(pred,gold,ids):
        counts[LABELS[int(y)]]+=1
        correct[LABELS[int(y)]]+=int(p==y)
    per={label:{"total":counts[label],"correct":correct[label],
                "accuracy":round(correct[label]/max(1,counts[label]),6)} for label in LABELS}
    return {"total":len(pred),"correct":int(np.sum(pred==gold)),
            "top1_accuracy":round(float(np.mean(pred==gold)),6),
            "balanced_label_accuracy":round(float(np.mean([per[l]["accuracy"] for l in LABELS])),6),
            "per_label":per,
            "distinct_printed_page_proxies":len({x["source_proxy"] for x in ids})}


def run()->dict:
    rows=source.read_catalog()
    cohort=frozen(rows)
    frames={};receipts={}
    for item in cohort:
        raw=source.fetch_original(item["url"])
        frames[item["item_id"]]=gray(raw)
        receipts[item["item_id"]]={"image_sha256":sha256(raw).hexdigest(),
             "printed_page_proxy":item["source_proxy"],"volume":item["volume"],
             "label":item["label"],"original_jpeg_bytes":len(raw)}
    X=np.array([hog(frames[x["item_id"]]) for x in cohort])
    y=np.array([LABELS.index(x["label"]) for x in cohort])
    v=np.array([x["volume"] for x in cohort])
    if set(y[v==1])!=set(range(8)) or set(y[v==2])!=set(range(8)) or set(y[v==3])!=set(range(8)):
        raise source.SourceError("Missing frozen label in an original historical volume")
    # Train hyperparameters only via old vol I -> validation vol II.
    tuning=[]
    for alpha in ALPHAS:
        p=predict(X[v==2],training(X[v==1],np.array([LABELS[i] for i in y[v==1]]),alpha))
        tuning.append((int((p==y[v==2]).sum()),alpha))
    best_alpha=sorted(tuning,key=lambda z:(-z[0],z[1]))[0][1]
    tr=v!=3;te=v==3
    clf=training(X[tr],np.array([LABELS[i] for i in y[tr]]),best_alpha)
    test_items=[x for x in cohort if x["volume"]==3]
    baseline=nn(X[tr],y[tr],X[te])
    center=centroids(X[tr],y[tr],X[te])
    ridge=predict(X[te],clf)
    perturbed={}
    for variant in ("contrast_70pct","invert","gaussian_blur"):
        copies=[]
        for x in test_items:
            image=frames[x["item_id"]]
            if variant=="contrast_70pct":changed=ImageEnhance.Contrast(image).enhance(.7)
            elif variant=="invert":changed=ImageOps.invert(image)
            else:changed=image.filter(ImageFilter.GaussianBlur(radius=1.0))
            copies.append(hog(changed))
        pp=predict(np.array(copies),clf)
        perturbed[variant]=summarize(pp,y[te],test_items)
    blank=hog(Image.new("L",(32,32),230))
    blank_scores=blank@clf[0]+clf[1]
    w27_ids={x["item_id"] for x in source.frozen_cohort(rows)}
    return {"schema":"w29-hpdb-authentic-iiif-cpu-classifiers-v1",
      "source":"original public Tokyo IIIF printed Moller sign crops",
      "publisher_catalog_revision":"a8cfcf52632487cf1d61a5793d84c9b2f7192d5a",
      "source_collection":source.SOURCE_COLLECTION,"usage_policy":source.SOURCE_POLICY,
      "license_notice":"HPDB CC BY 4.0 published sign metadata; Tokyo publisher source terms checked in W27",
      "original_iiif_jpeg_pixels_actually_read":True,
      "published_manifest_original_sample_receipts":receipts,
      "original_papyrus_photographs_included":False,
      "train_volume_ids":[1,2],"test_volume_ids":[3],
      "train_items":int(tr.sum()),"test_items":int(te.sum()),
      "frozen_max_per_label_per_volume":CAP_PER_LABEL_VOLUME,
      "test_known_w27_exposed_sign_item_overlap":sum(1 for x in test_items if x["item_id"] in w27_ids),
      "train_only_volume2_selection":{"alpha_candidates":list(ALPHAS),"chosen":best_alpha,
          "dev_accuracies":[{"alpha":alpha,"correct":score,"total":int(sum(v==2))}
                            for score,alpha in tuning]},
      "test_original_pixels":{"one_nearest_neighbor":summarize(baseline,y[te],test_items),
          "nearest_centroid_hog":summarize(center,y[te],test_items),
          "trained_ridge_hog":summarize(ridge,y[te],test_items)},
      "test_ridge_corruption_robustness":perturbed,
      "blank_control_predicted_label":LABELS[int(np.argmax(blank_scores))],
      "paper_book_witness_not_independent_manuscript":True,
      "expert_hieratic_sign_reading_gold_available":False,
      "official_benchmark_or_capability_points":0}


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    data=run()
    doc=json.dumps(data,sort_keys=True,indent=2)
    if a.output:a.output.write_text(doc+"\n",encoding="utf-8")
    print(doc)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
