"""W30 B: real Tokyo historical printed Hieratic sign classifier + authentic Met-photo OOD.

Printed source glyph crops retain publisher labels. Met original papyrus tiles
are UNLABELLED, never scored as Gardiner classes or expert reading gold.
"""
from __future__ import annotations
import argparse,hashlib,io,json,random
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image,ImageOps
from tools import w29_hpdb_sign_learning as prior
from tools import w29_cc0_original_vision as met
from tools import research_hpdb_original_pixels as hpdb

VERSION="W30-REAL-TOKYO-PRINTED-SIGN-TO-MET-ORIGINAL-UNLABELLED-OOD/1"
LABELS=prior.LABELS
MAX_PER_LABEL_VOLUME=8
ALPHAS=(0.01,0.1,1,10)
MET_CC0=(546511,554654)

def cohort(rows:list[dict])->list[dict]:
    result=[]
    for label in LABELS:
        for volume in (1,2,3):
            eligible=sorted((r for r in rows if r.get("single_sign")==label and r.get("vol")==volume
                      and r.get("kind")=="Main" and r.get("iiif_ref")),key=lambda x:str(x["id"]))
            if not eligible:raise hpdb.SourceError(f"Missing frozen {label}/volume{volume} source")
            for rank,r in enumerate(eligible[:MAX_PER_LABEL_VOLUME]):
                hpdb.verify_iiif_url(r["iiif_ref"])
                result.append({"item_id":str(r["id"]),"label":label,"volume":volume,
                    "printed_page":int(r["page"]),"url":r["iiif_ref"],
                    "rank_within_label_volume":rank,
                    "source_proxy":f"MOLLER-V{volume}-P{int(r['page']):03d}"})
    if len(result)<24 or len({x["item_id"] for x in result})!=len(result):
        raise hpdb.SourceError("Duplicate or insufficient original publisher sign source cohort")
    return result

def new_photo_tiles(raw:bytes,object_id:int,count:int=32)->list[Image.Image]:
    Image.MAX_IMAGE_PIXELS=180_000_000
    with Image.open(io.BytesIO(raw)) as im:
        if im.format!="JPEG" or im.width*im.height>180_000_000:
            raise ValueError("Invalid authentic Met original JPEG for cross-domain OOD")
        photo=ImageOps.contain(ImageOps.exif_transpose(im).convert("L"),(512,512),Image.Resampling.LANCZOS)
    if photo.width<64 or photo.height<64:raise ValueError("Museum image too small")
    rng=random.Random(3002+object_id)
    patches=[]
    for _ in range(count):
        x=rng.randrange(1,photo.width-32)
        y=rng.randrange(1,photo.height-32)
        patches.append(ImageOps.autocontrast(photo.crop((x,y,x+32,y+32))))
    return patches

def confidence(X:np.ndarray,model:tuple[np.ndarray,np.ndarray])->np.ndarray:
    w,b=model
    return np.max(X@w+b,axis=1)

def execute()->dict:
    catalog=hpdb.read_catalog()
    rows=cohort(catalog)
    feats=[];receipts=[]
    for row in rows:
        raw=hpdb.fetch_original(row["url"])
        x=prior.hog(prior.gray(raw))
        feats.append(x)
        receipts.append({"item_id":row["item_id"],"gardiner_catalog_label":row["label"],
            "book_volume":row["volume"],"printed_page":row["printed_page"],
            "publisher_iiif_sha256":hashlib.sha256(raw).hexdigest(),
            "source_proxy":row["source_proxy"],"actual_publisher_original_jpeg_bytes":len(raw)})
    X=np.array(feats);Y=np.array([LABELS.index(r["label"]) for r in rows])
    V=np.array([r["volume"] for r in rows])
    if any(set(Y[V==volume])!=set(range(8)) for volume in (1,2,3)):
        raise hpdb.SourceError("Frozen print label missing in heldout historical volume")
    if {r["source_proxy"] for r in rows if r["volume"]<3}&{r["source_proxy"] for r in rows if r["volume"]==3}:
        raise hpdb.SourceError("Train and volume III share physical printed page proxy")
    tune=[]
    for alpha in ALPHAS:
        model=prior.training(X[V==1],np.array([LABELS[x] for x in Y[V==1]]),alpha)
        correct=int(np.sum(prior.predict(X[V==2],model)==Y[V==2]))
        tune.append({"alpha":alpha,"volume2_correct":correct,"volume2_total":int(sum(V==2))})
    selected=sorted(tune,key=lambda x:(-x["volume2_correct"],x["alpha"]))[0]["alpha"]
    # Source-train volume leave-one-out threshold; no printed test or actual photo
    # pixel is used for confidence calibration.
    dev_scores=[]
    for heldout in (1,2):
        model=prior.training(X[(V!=heldout)&(V<3)],
           np.array([LABELS[x] for x in Y[(V!=heldout)&(V<3)]]),selected)
        dev_scores.extend(confidence(X[V==heldout],model).tolist())
    threshold=float(np.quantile(dev_scores,.05))
    final=prior.training(X[V<3],np.array([LABELS[x] for x in Y[V<3]]),selected)
    testX=X[V==3];testY=Y[V==3]
    test_rows=[r for r in rows if r["volume"]==3]
    p=prior.predict(testX,final)
    nn=prior.nn(X[V<3],Y[V<3],testX)
    centers=prior.centroids(X[V<3],Y[V<3],testX)
    previously_exposed={r["item_id"] for r in prior.frozen(catalog)}
    # W29 first <=3 per group is already measured; not new source-blind gold.
    older_ids={r["item_id"] for r in rows if r["rank_within_label_volume"]<3 and r["volume"]==3}
    new_mask=np.array([r["item_id"] not in older_ids for r in test_rows])
    if len(test_rows)!=len(p):raise ValueError("Classifier output denominator incorrect")
    scores=confidence(testX,final)
    met_results={}
    for oid in MET_CC0:
        title=met.MET_OBJECTS[0][1] if oid==546511 else met.MET_OBJECTS[1][1]
        raw,_=met.met_original(oid,title)
        tiles=new_photo_tiles(raw,oid)
        tile_features=np.array([prior.hog(pix) for pix in tiles])
        raw_max=confidence(tile_features,final)
        met_results[str(oid)]={
            "original_met_sha256":hashlib.sha256(raw).hexdigest(),
            "original_photo_bytes":len(raw),
            "unlabelled_original_photo_tiles":len(raw_max),
            "unlabelled_tiles_rejected_under_print_train_threshold":int(np.sum(raw_max<threshold)),
            "unlabelled_tiles_accepted_by_print_model":int(np.sum(raw_max>=threshold)),
            "source_domain_only_no_true_sign_gold":True,
            "max_raw_ridge_confidence_quantiles":[round(float(x),6) for x in np.quantile(raw_max,[0,.25,.5,.75,1])]}
    old=prior.frozen(catalog)
    return {"protocol":VERSION,"original_publisher_sign_records":len(catalog),
        "original_authentic_printed_iiif_images_used":True,
        "original_met_papyrus_jpeg_pixels_used":True,
        "printed_metadata_CC_BY4":True,
        "published_iiif_print_source_records":receipts,
        "source_catalog_revision":"a8cfcf52632487cf1d61a5793d84c9b2f7192d5a",
        "catalog_labels":list(LABELS),"train_volume1_and2":True,
        "train_signs":int(sum(V<3)),"test_volume3_signs":int(sum(V==3)),
        "different_printed_volume_test":True,
        "test_original_w27_known_exposed_ids":sum(r["item_id"] in previously_exposed for r in test_rows),
        "test_w29_first3_exposed_ids":int(sum(~new_mask)),
        "test_new_relative_to_w29":int(sum(new_mask)),
        "chosen_train_only_alpha":selected,"source_train_only_tuning":tune,
        "printed_test_results":{
          "pixel_nearest_neighbour":prior.summarize(nn,testY,test_rows),
          "hog_centroid":prior.summarize(centers,testY,test_rows),
          "trained_hog_ridge":prior.summarize(p,testY,test_rows)},
        "new_printed_test_ids_not_w29":{
          "rows":int(sum(new_mask)),
          "correct":int(sum(p[new_mask]==testY[new_mask])),
          "accuracy":round(float(np.mean(p[new_mask]==testY[new_mask])),6) if sum(new_mask) else None},
        "printed_train_cross_volume_5pct_score_threshold":round(threshold,9),
        "printed_test_signs_below_threshold":int(sum(scores<threshold)),
        "original_papyrus_unlabelled_OOD":met_results,
        "blank_control_raw_model_max_score":round(float(confidence(
             np.array([prior.hog(Image.new("L",(32,32),230))]),final)[0]),6),
        "original_photo_sign_labels_or_expert_gold":False,
        "printed_test_palaeographic_independence":False,
        "official_hieratic_reading_score":None,"weighted_capability_points":0}

def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path)
    a=parser.parse_args()
    data=execute()
    text=json.dumps(data,indent=2,sort_keys=True)
    if a.output:a.output.write_text(text+"\n",encoding="utf-8")
    print(text)

if __name__=="__main__":main()
