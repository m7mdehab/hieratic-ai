"""W30 B2 NEW 11-class source-count-frozen Tokyo IIIF print sign learning.

Original real publisher IIIF sign JPEGs, actual public domain Met photo patches
only as UNLABELLED OOD probes. No protected Hieratic gold is opened.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
from tools import w30_hpdb_photo_ood as earlier
from tools import w29_hpdb_sign_learning as old
from tools import research_hpdb_original_pixels as source
from tools import w29_cc0_original_vision as met

LABELS=("A19","A2","G1","G17","G37","O50","S42","V10","V29","W22","W24")
EXPECTED={"A19":(2,2,2),"A2":(2,2,2),"G1":(3,2,2),"G17":(2,2,2),
          "G37":(2,2,2),"O50":(2,2,2),"S42":(3,3,3),"V10":(2,2,3),
          "V29":(3,3,3),"W22":(2,2,2),"W24":(2,2,2)}
ALPHAS=(0.01,0.1,1.,10.)
VERSION="W30-PUBLISHER-11-CLASS-REAL-PIXEL-TRAIN-AND-AUTHENTIC-MET-OOD/2"

def frozen(rows:list[dict])->list[dict]:
    eligible=[r for r in rows if r.get("kind")=="Main" and r.get("iiif_ref")
               and r.get("single_sign") in LABELS]
    group={}
    for label in LABELS:
        for vol in (1,2,3):
            selected=sorted((r for r in eligible if r["single_sign"]==label and r["vol"]==vol),
                            key=lambda q:str(q["id"]))
            if len(selected)!=EXPECTED[label][vol-1]:
                raise source.SourceError("Exact publisher original source-count drift for "+label+"/"+str(vol))
            group[label,vol]=selected
    out=[]
    for label in LABELS:
        for vol in (1,2,3):
            for rank,row in enumerate(group[label,vol]):
                source.verify_iiif_url(row["iiif_ref"])
                out.append({"item_id":str(row["id"]),"label":label,"volume":vol,
                           "url":row["iiif_ref"],"printed_page":int(row["page"]),
                           "printed_support_proxy":f"MOLLER-V{vol}-P{int(row['page']):03d}",
                           "catalog_rank":rank})
    if len(out)!=74 or len({x["item_id"] for x in out})!=74:
        raise source.SourceError("Frozen B2 full population not exactly 74 original signs")
    return out

def model_fit(X:np.ndarray,y:np.ndarray,alpha:float)->tuple[np.ndarray,np.ndarray]:
    onehot=np.zeros((len(y),len(LABELS)),np.float64)
    onehot[np.arange(len(y)),y]=1
    mean=X.mean(axis=0)
    centered=X-mean
    w=centered.T @ np.linalg.solve(centered@centered.T+np.eye(len(y))*alpha,onehot)
    return w,onehot.mean(axis=0)-mean@w

def outputs(X:np.ndarray,model:tuple[np.ndarray,np.ndarray])->np.ndarray:
    w,b=model
    return X@w+b

def centroid(X:np.ndarray,y:np.ndarray,test:np.ndarray)->np.ndarray:
    c=np.array([np.mean(X[y==i],axis=0) for i in range(len(LABELS))])
    return np.argmin(np.sum((test[:,None,:]-c[None,:,:])**2,axis=2),axis=1)

def summary(pred:np.ndarray,gold:np.ndarray,rows:list[dict])->dict:
    classes={}
    for i,label in enumerate(LABELS):
        mask=gold==i
        classes[label]={"count":int(mask.sum()),"correct":int((pred[mask]==gold[mask]).sum())}
    return {"total":len(gold),"correct":int((pred==gold).sum()),
            "top1_accuracy":round(float(np.mean(pred==gold)),7),
            "macro_accuracy":round(float(np.mean([v["correct"]/v["count"] for v in classes.values()])),7),
            "by_label":classes,
            "distinct_printed_book_page_proxies":len({x["printed_support_proxy"] for x in rows})}

def run()->dict:
    catalogue=source.read_catalog()
    cohort=frozen(catalogue)
    features=[];receipts=[]
    for x in cohort:
        raw=source.fetch_original(x["url"])
        features.append(old.hog(old.gray(raw)))
        receipts.append({"catalog_sign_id":x["item_id"],"catalog_label":x["label"],
            "volume":x["volume"],"printed_book_page":x["printed_page"],
            "source_sha256":hashlib.sha256(raw).hexdigest(),
            "source_jpeg_bytes":len(raw),"publisher_iiif_url":x["url"]})
    X=np.array(features);Y=np.array([LABELS.index(x["label"]) for x in cohort]);V=np.array([x["volume"] for x in cohort])
    if int((V!=3).sum())!=49 or int((V==3).sum())!=25:
        raise source.SourceError("Actual cohort split does not match frozen 49/25 source denominator")
    trial=[]
    for alpha in ALPHAS:
        predictor=model_fit(X[V==1],Y[V==1],alpha)
        good=int((np.argmax(outputs(X[V==2],predictor),axis=1)==Y[V==2]).sum())
        trial.append({"alpha":alpha,"validation_correct":good,"validation_count":24})
    chosen=sorted(trial,key=lambda x:(-x["validation_correct"],x["alpha"]))[0]["alpha"]
    # No original photo/test labels influence the OOD threshold or hyperparameters.
    devscores=[]
    for val in (1,2):
        train=(V!=val)&(V<3)
        mdl=model_fit(X[train],Y[train],chosen)
        devscores.extend(np.max(outputs(X[V==val],mdl),axis=1).tolist())
    threshold=float(np.quantile(devscores,.05))
    mdl=model_fit(X[V<3],Y[V<3],chosen)
    test=(V==3)
    printed=[x for x in cohort if x["volume"]==3]
    score=outputs(X[test],mdl)
    ridge=np.argmax(score,axis=1)
    nn=old.nn(X[V<3],Y[V<3],X[test])
    center=centroid(X[V<3],Y[V<3],X[test])
    # Absolute prior W27 and W29/B1 exposed test item IDs are recorded,
    # never called virgin regardless of printed-volume separation.
    knownW27={r["item_id"] for r in source.frozen_cohort(catalogue)}
    knownW29={r["item_id"] for r in old.frozen(catalogue)}
    knownB1={r["item_id"] for r in earlier.cohort(catalogue) if r["volume"]==3}
    known=knownW27|knownW29|knownB1
    mask=np.array([r["item_id"] not in known for r in printed])
    actual={}
    for object_id in earlier.MET_CC0:
        title=met.MET_OBJECTS[0][1] if object_id==546511 else met.MET_OBJECTS[1][1]
        raw,_=met.met_original(object_id,title)
        tiles=earlier.new_photo_tiles(raw,object_id,32)
        probs=np.max(outputs(np.array([old.hog(tile) for tile in tiles]),mdl),axis=1)
        actual[str(object_id)]={"original_CC0_image_sha256":hashlib.sha256(raw).hexdigest(),
            "original_photo_bytes":len(raw),
            "unlabelled_original_papyrus_tiles":len(tiles),
            "unlabelled_tiles_below_train_only_print_score_threshold":int(sum(probs<threshold)),
            "unlabelled_original_photo_tiles_accepted_by_print_classifier":int(sum(probs>=threshold)),
            "true_sign_accuracy_not_measured":True,
            "raw_max_ridge_score_quantiles":[round(float(z),7) for z in np.quantile(probs,[0,.25,.5,.75,1])]}
    return {"protocol":VERSION,"publisher_original_metadata_signs":len(catalogue),
            "real_original_printed_iiif_photo_pixels_used":True,
            "original_public_domain_met_photo_pixels_used":True,
            "actual_publisher_original_sign_JPEG_SHA_records":receipts,
            "eleven_frozen_gardiner_sign_classes":list(LABELS),
            "split_by_historical_printed_book_volume":True,
            "train_real_original_iiif_crops":int(sum(V!=3)),
            "test_real_original_iiif_crops":int(sum(V==3)),
            "trained_ridge_alpha_from_volume2_only":chosen,
            "train_validation_grid":trial,
            "heldout_print_test_scores":{"pixel_nearest_neighbour":summary(nn,Y[test],printed),
                "hog_centroid":summary(center,Y[test],printed),
                "trained_hog_ridge":summary(ridge,Y[test],printed)},
            "heldout_test_known_prior_exposed_ids_count":int(sum(~mask)),
            "heldout_test_new_relative_to_W27_W29_B1":{"items":int(sum(mask)),
                "correct":int(sum(ridge[mask]==Y[test][mask])),
                "top1_accuracy":round(float(np.mean(ridge[mask]==Y[test][mask])),7) if sum(mask) else None},
            "printed_train_only_cross_volume_threshold":round(threshold,8),
            "printed_test_sign_images_below_threshold":int(sum(np.max(score,axis=1)<threshold)),
            "met_photo_unlabelled_OOD_results":actual,
            "image_domain_only_not_annotated_photo_sign_gold":True,
            "publisher_IIIF_is_historical_printed_edition_not_papyrus":True,
            "official_reading_accuracy":None,"weighted_capability_points":0}

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    value=run()
    text=json.dumps(value,indent=2,sort_keys=True)
    if a.output:a.output.write_text(text+"\n",encoding="utf-8")
    print(text)

if __name__=="__main__":main()
