"""W31 actual original museum-photo vs historical printed-sign source-domain model."""
from __future__ import annotations
from hashlib import sha256
from io import BytesIO
import argparse,json,urllib.request,urllib.parse
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
from tools import w30_hpdb_eleven_class as printed
from tools import w30_hpdb_photo_ood as tiles
from tools import w29_hpdb_sign_learning as hist
from tools import research_hpdb_original_pixels as hpdb
from tools import w29_cc0_original_vision as met

MET_NEW=555779
MET_TITLE="Papyrus fragments inscribed in hieratic"
MET_ACCESSION="34.1.215a"
SOURCE_API="https://collectionapi.metmuseum.org/public/collection/v1/objects/"
ALPHAS=(.01,.1,1.,10.)
VERSION="W31-ORIGINAL-PHOTO-VS-PRINT-SOURCE-DOMAIN-LINEAR-RIDGE-v1"


def novel_met():
    req=urllib.request.Request(SOURCE_API+str(MET_NEW),headers={
        "User-Agent":"HieraticAI-W31-unseen-original-Met-CC0/1.0"})
    with urllib.request.urlopen(req,timeout=35) as reply: data=json.loads(reply.read(200000))
    if (data.get("objectID")!=MET_NEW or data.get("title")!=MET_TITLE
        or data.get("accessionNumber")!=MET_ACCESSION
        or data.get("department")!="Egyptian Art"
        or data.get("isPublicDomain") is not True
        or "papyrus" not in str(data.get("medium","")).lower()):
        raise ValueError("Frozen new original museum source licence/identity unavailable")
    url=data.get("primaryImage")
    if not isinstance(url,str) or not url:raise ValueError("No approved new original photo")
    u=urllib.parse.urlsplit(url)
    if (u.scheme!="https" or u.hostname!="images.metmuseum.org"
        or not u.path.startswith("/CRDImages/eg/original/")
        or not u.path.lower().endswith((".jpg",".jpeg"))
        or u.port or u.query or u.fragment or u.username or u.password):
        raise ValueError("New image URL not museum original source")
    safe=u._replace(path=urllib.parse.quote(u.path,safe="/%-._~")).geturl()
    with urllib.request.urlopen(urllib.request.Request(safe,headers={
        "User-Agent":"HieraticAI-W31-unseen-original-Met-CC0/1.0"}),timeout=60) as reply:
        raw=reply.read(32000001)
    if not 1000<len(raw)<=32000000 or raw[:2]!=bytes((255,216)):
        raise ValueError("No bounded genuine museum JPEG original")
    Image.MAX_IMAGE_PIXELS=170000000
    with Image.open(BytesIO(raw)) as im:
        if im.format!="JPEG" or im.width*im.height>170000000:
            raise ValueError("Original photo decoder/source geometry mismatch")
        wh=[im.width,im.height]
    return raw,{"object_id":MET_NEW,"accession":MET_ACCESSION,"title":MET_TITLE,
        "original_sha256":sha256(raw).hexdigest(),"jpeg_original_bytes":len(raw),
        "original_wh":wh,"public_domain_claim_verified_from_museum_API":True}


def model(X,y,alpha):
    # Balance source domains, then ridge fit. Training labels are DOMAIN labels,
    # never ancient Egyptian glyph labels on real manuscript photographs.
    X=np.asarray(X,np.float64)
    y=np.asarray(y,np.float64)
    p=y==1;n=~p
    a=X[p].mean(axis=0);b=X[n].mean(axis=0)
    # Class-balanced linear discriminant with L2 regularization.
    xp=X-X.mean(axis=0)
    target=(y-.5)
    weights=np.where(p,1/(2*sum(p)),1/(2*sum(n)))
    gram=xp.T@(weights[:,None]*xp)+np.eye(X.shape[1])*alpha
    rhs=xp.T@(weights*target)
    coef=np.linalg.solve(gram,rhs)
    bias=.5-X.mean(axis=0)@coef
    return coef,bias


def predict(X,model_):
    coef,bias=model_
    return np.asarray(X)@coef+bias


def run():
    catalogue=hpdb.read_catalog()
    cohort=printed.frozen(catalogue)
    X=[];Y=[];V=[];hashes=[]
    for row in cohort:
        original=hpdb.fetch_original(row["url"])
        X.append(hist.hog(hist.gray(original)))
        Y.append(1);V.append(row["volume"])
        hashes.append({"publisher_item_id":row["item_id"],"publisher_volume":row["volume"],
                       "label_original_metadata":row["label"],
                       "source_original_SHA256":sha256(original).hexdigest()})
    train_photos=[];meta=[]
    for oid,title,_ in met.MET_OBJECTS:
        raw,receipt=met.met_original(oid,title)
        photo=tiles.new_photo_tiles(raw,oid,32)
        train_photos.extend(hist.hog(f) for f in photo)
        meta.append({"object_id":oid,"original_sha256":sha256(raw).hexdigest(),
                     "training_domain_photo_tiles":len(photo)})
    new_raw,new_source=novel_met()
    # No test pixels are used for training, threshold tuning or sample selection.
    test_photos=[hist.hog(f) for f in tiles.new_photo_tiles(new_raw,MET_NEW,32)]
    XA=np.array([f for f,v in zip(X,V) if v==1]+train_photos)
    YA=np.array([1]*sum(v==1 for v in V)+[0]*len(train_photos))
    Xdev=np.array([f for f,v in zip(X,V) if v==2])
    # Train-side dev positives from historical vol II; negative dev only
    # deterministic even half of the known training-original photo tiles.
    Xdev=np.vstack([Xdev,np.asarray(train_photos[::2])])
    Ydev=np.array([1]*sum(v==2 for v in V)+[0]*len(train_photos[::2]))
    trial=[]
    for alpha in ALPHAS:
        m=model(XA,YA,alpha)
        scores=predict(Xdev,m)
        trial.append({"alpha":alpha,"correct":int(sum((scores>=.5)==Ydev)),
                     "total":len(Ydev)})
    alpha=sorted(trial,key=lambda z:(-z["correct"],z["alpha"]))[0]["alpha"]
    final=np.array([f for f,v in zip(X,V) if v in (1,2)]+train_photos)
    target=np.array([1]*sum(v in (1,2) for v in V)+[0]*len(train_photos))
    fit=model(final,target,alpha)
    Xtest=np.array([f for f,v in zip(X,V) if v==3]+test_photos)
    truth=np.array([1]*sum(v==3 for v in V)+[0]*len(test_photos))
    scores=predict(Xtest,fit)
    pred=(scores>=.5).astype(int)
    tp=int(sum((truth==1)&(pred==1)));fn=int(sum((truth==1)&(pred==0)))
    tn=int(sum((truth==0)&(pred==0)));fp=int(sum((truth==0)&(pred==1)))
    return {"version":VERSION,"genuine_publisher_original_sign_crops":len(hashes),
       "genuine_original_met_source_photos_train":meta,"new_met_original_photo":new_source,
       "publisher_source_sha_records":hashes,"trained_on_real_source_images":True,
       "frozen_training_examples":{"publisher_train":int(sum(v in (1,2) for v in V)),
                                   "photo_tiles":len(train_photos)},
       "train_only_tuning":trial,"chosen_alpha":alpha,
       "heldout":{"publisher_print_vol3":int(sum(v==3 for v in V)),
                  "new_original_photo_tiles":len(test_photos),
                  "true_print_accepted":tp,"print_rejected":fn,
                  "new_photo_rejected":tn,"new_photo_false_admitted":fp,
                  "balanced_domain_accuracy":round(.5*(tp/max(1,tp+fn)+tn/max(1,tn+fp)),7),
                  "photo_rejection_rate":round(tn/max(1,tn+fp),7),
                  "print_accept_rate":round(tp/max(1,tp+fn),7)},
       "true_manuscript_sign_accuracy":None,
       "source_independent_palaeography_gold":False,
       "publisher_photographic_raw_pixels_committed":False,
       "weighted_capability_points":0}


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path);a=p.parse_args()
    s=json.dumps(run(),sort_keys=True,indent=2)
    if a.output:a.output.write_text(s+"\n")
    print(s)

if __name__=="__main__":main()
