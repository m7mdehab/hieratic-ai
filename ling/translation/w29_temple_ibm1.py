"""W29 C first-use prospective AES temple-text IBM Model 1 Egyptian→German.

Strict source-only prediction subprocess, reference labels opened after outputs.
Original publisher raw content private/transient, public receipts only.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from hashlib import sha1,sha256
import argparse,json,math,random,sys,urllib.request
from pathlib import Path
from typing import Any
from ling.translation import w28_letters_first_use as previous
from ling.translation import contextual
from ling.translation.compositional import ConstrainedComposer
from tools.translation_layer import TranslationError,_words,word_f1

ORIGINAL_FILE="_aes_bbawtempelbib.json"
ORIGINAL_REV="35276d2527cca1a055e31ed5f6683e777717170f"
ORIGINAL_SHA1="f8135fee93c0ed27b5d6a110605f1a842fb6d8b6"
ORIGINAL_SIZE=9679845
URL=f"https://raw.githubusercontent.com/simondschweitzer/aes/{ORIGINAL_REV}/files/aes/{ORIGINAL_FILE}"
PROTOCOL="W29-AES-TEMPLE-FIRST-USE-IBM1-v1"
HASH_SALT="hieratic-ai-w29-temple-first-use:"
GROUPS=32
EM_EPOCHS=4
MIN_SOURCE_SUPPORT=2
UNKNOWN="[?]"


def canonical(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")


def gitblob(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def original_rows(raw:bytes)->dict[str,dict]:
    if len(raw)!=ORIGINAL_SIZE or gitblob(raw)!=ORIGINAL_SHA1:
        raise TranslationError("Original publisher source byte size or Git blob did not match frozen target")
    data=json.loads(raw)
    if not isinstance(data,dict) or len(data)<GROUPS:
        raise TranslationError("Original published source not sentence corpus")
    for sid,row in data.items():
        if (not isinstance(sid,str) or not isinstance(row,dict)
            or not isinstance(row.get("text"),str) or not row["text"]
            or not isinstance(row.get("token"),list)
            or not isinstance(row.get("sentence_translation"),str)):
            raise TranslationError("Source fields differ from frozen AES schema")
    return data


def choose(data:dict[str,dict])->list[str]:
    ids={r["text"] for r in data.values()}
    if len(ids)<GROUPS:raise TranslationError("Original publisher corpus fewer than 32 text IDs")
    return sorted(ids,key=lambda text_id:(sha256((HASH_SALT+text_id).encode()).hexdigest(),text_id))[:GROUPS]


def fetch_and_split(raw:bytes,inputs:Path,refs:Path)->dict:
    rows=original_rows(raw);included=set(choose(rows))
    if inputs.exists() or refs.exists() or inputs.resolve()==refs.resolve():
        raise TranslationError("Source and private reference outputs must be new separate files")
    source_only=[];private_refs=[]
    for sid,item in sorted(rows.items()):
        if item["text"] not in included:continue
        forms=[]
        for token in item["token"]:
            if not isinstance(token,dict) or not isinstance(token.get("written_form"),str):
                raise TranslationError("Unexpected original Egyptian source unit")
            forms.append(token["written_form"])
        source_only.append({"sentence_id":sid,"text_id":item["text"],"forms":forms})
        private_refs.append({"sentence_id":sid,"text_id":item["text"],"german":item["sentence_translation"]})
    if len({x["text_id"] for x in source_only})!=GROUPS or len(source_only)!=len(private_refs):
        raise TranslationError("Fixed heldout source-group denominator not closed")
    if any(not x["forms"] for x in source_only):
        raise TranslationError("Original empty source sentences: fixed cohort blocked, cannot silently prune")
    inputs.write_bytes(canonical(source_only))
    refs.write_bytes(canonical(private_refs))
    return {"source_github_blob_sha1":gitblob(raw),"source_sha256":sha256(raw).hexdigest(),
        "source_original_bytes":len(raw),"frozen_groups":GROUPS,
        "source_sentences":len(source_only),"source_inputs_sha256":sha256(inputs.read_bytes()).hexdigest(),
        "private_publisher_german_reference_sha256":sha256(refs.read_bytes()).hexdigest(),
        "prediction_reads_reference_file":False}


class IBM1:
    """Unsupervised lexical word alignment fitted solely on donor references.

    EM step trains P(German-word|Egyptian-form) with a NULL donor token.
    An unseen Egyptian word abstains rather than copy/hallucinate target German.
    """
    def __init__(self,train:list[dict]):
        self.train=train
        self.support=Counter()
        self.training_groups={r["text_id"] for r in train}
        vocab:dict[str,set[str]]=defaultdict(set)
        sentences=[]
        for row in train:
            egypt=tuple(str(x) for x in row["forms"] if x)
            german=tuple(_words(row["german"]))
            if not egypt or not german:continue
            sources=tuple(sorted(set(egypt)))+("<NULL>",)
            targets=tuple(german)
            sentences.append((sources,targets))
            for e in set(egypt):
                self.support[e]+=1
            for e in sources:
                vocab[e].update(targets)
        self.sentence_count=len(sentences)
        self.prob={e:{g:1.0/len(words) for g in sorted(words)}
                   for e,words in vocab.items() if words}
        for _ in range(EM_EPOCHS):
            numer:dict[str,dict[str,float]]=defaultdict(lambda:defaultdict(float))
            denom:dict[str,float]=defaultdict(float)
            for eforms,gwords in sentences:
                for g in gwords:
                    z=sum(self.prob[e].get(g,0.) for e in eforms if e in self.prob)
                    if z<1e-20:continue
                    for e in eforms:
                        current=self.prob.get(e,{}).get(g,0.)
                        if current<=0:continue
                        mass=current/z
                        numer[e][g]+=mass;denom[e]+=mass
            self.prob={e:{g:val/denom[e] for g,val in words.items()}
                       for e,words in numer.items() if denom[e]>0}
        self.best={e:sorted(weights.items(),key=lambda g:(-g[1],g[0]))[0][0]
                   for e,weights in self.prob.items() if weights and e!="<NULL>"}

    def predict(self,forms:tuple[str,...])->tuple[str,int]:
        values=[self.best.get(form,UNKNOWN) if self.support[form]>=MIN_SOURCE_SUPPORT else UNKNOWN
                for form in forms]
        return " ".join(values),values.count(UNKNOWN)


def _train()->list[dict]:
    donors,bundle=previous._train()
    if len(donors)!=3925:raise TranslationError("Frozen W11 3925 donor count changed")
    return donors


def predict(inputs:list[dict])->tuple[list[dict],dict]:
    train=_train()
    old_ids={r["text_id"] for r in train}
    src=[previous.project_input(x) for x in inputs]
    if len({r["text_id"] for r in src})!=GROUPS:raise TranslationError("Target frozen text groups mismatch")
    if any(r["text_id"] in old_ids for r in src):
        raise TranslationError("Original new target shares known training text ID")
    # Includes historically exposed W10-16 heldout IDs. Do not accept overlap.
    known=contextual.TranslationMemory(train)
    learned=IBM1(train)
    composer=ConstrainedComposer(train)
    result=[];total_unknown=0
    for row in src:
        gloss=known.gloss(row["forms"])
        fixed=composer.predict(row)
        new,unknown=learned.predict(row["forms"])
        total_unknown+=unknown
        result.append({"sentence_id":row["sentence_id"],"text_id":row["text_id"],
            "input_sha256":sha256(canonical(row["forms"])).hexdigest(),
            "baseline_gloss":gloss["text"],"baseline_w10":fixed["prediction"],
            "ibm1":new,"ibm1_unknown_source_tokens":unknown})
    meta={"donor_sentences":len(train),"donor_text_groups":len(old_ids),
          "ibm1_actual_training_sentences":learned.sentence_count,
          "ibm1_trained_translation_source_forms":len(learned.best),
          "em_iterations":EM_EPOCHS,
          "training_data_excludes_new_german_references":True,
          "prediction_count":len(result),
          "predictor_uses_publisher_new_german_gold":False,
          "total_ibm1_unknown_source_tokens":total_unknown}
    return result,meta


def f1(triple:tuple[int,int,int])->float:
    a,b,c=triple
    return 2*a/(b+c) if b+c else 0


def score(inputs:list[dict],predictions:list[dict],refs:list[dict])->dict:
    a={r["sentence_id"]:r for r in inputs};p={r["sentence_id"]:r for r in predictions};g={r["sentence_id"]:r for r in refs}
    if len(a)!=len(inputs) or set(a)!=set(p) or set(a)!=set(g) or len(p)!=len(predictions) or len(g)!=len(refs):
        raise TranslationError("Frozen 32-group target sentence denominator changed")
    bygroup=defaultdict(lambda:{name:[0,0,0] for name in ("baseline_gloss","baseline_w10","ibm1")})
    totals={name:[0,0,0] for name in ("baseline_gloss","baseline_w10","ibm1")}
    nref=0;missing=0;source_tokens=0;unknowns=0
    for sid,row in a.items():
        prediction=p[sid];gold=g[sid]
        if prediction["text_id"]!=row["text_id"] or gold["text_id"]!=row["text_id"]:
            raise TranslationError("Target row/group alignment mismatch")
        if prediction["input_sha256"]!=sha256(canonical(row["forms"])).hexdigest():
            raise TranslationError("Egyptian original forms changed after model fitting")
        source_tokens+=len(row["forms"])
        unknowns+=prediction["ibm1_unknown_source_tokens"]
        german=gold["german"]
        if not german:missing+=1;continue
        nref+=1
        for name in totals:
            m=word_f1(prediction[name],german)
            counts=(m["overlap"],m["predicted_word_count"],m["published_word_count"])
            for i,n in enumerate(counts):
                totals[name][i]+=n
                bygroup[row["text_id"]][name][i]+=n
    gids=sorted(bygroup)
    if len({x["text_id"] for x in a.values()})!=GROUPS:
        raise TranslationError("Heldout 32 groups missing")
    rng=random.Random(29);deltas=[]
    for _ in range(2000):
        selected=[bygroup[gids[rng.randrange(len(gids))]] for j in gids]
        A=tuple(sum(x["ibm1"][i] for x in selected) for i in range(3))
        B=tuple(sum(x["baseline_w10"][i] for x in selected) for i in range(3))
        deltas.append(f1(A)-f1(B))
    deltas.sort()
    return {"version":PROTOCOL,"frozen_source_groups":GROUPS,
      "total_sentences":len(inputs),"with_original_german_reference":nref,
      "without_original_german_reference":missing,
      "original_egyptian_tokens":source_tokens,"ibm1_unknown_source_units":unknowns,
      "metrics":{name:{"german_word_micro_f1":round(f1(tuple(v)),8),
                       "correct_word_multiset_overlap":v[0],"predicted_words":v[1],"reference_words":v[2]}
                 for name,v in totals.items()},
      "ibm1_minus_w10_text_group_bootstrap_95pct":[round(deltas[49],8),round(deltas[1949],8)],
      "trained_IBM1_on_original_publisher_donor":True,
      "new_heldout_editorial_german_labels_seen_only_after_predicted_archive":True,
      "original_photographs_used":False,
      "expert_semantic_translation_accuracy":None,
      "source_physical_manuscript_independence_confirmed":False,
      "model_training_or_reading_capability_points":0}


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("stage",choices=("fetch","train-predict","score"))
    p.add_argument("--private",type=Path,required=True)
    args=p.parse_args()
    if not args.private.is_dir() or args.private.is_symlink():
        raise TranslationError("Preexisting private temporary directory required")
    input_file=args.private/"egyptian_inputs.json"
    gold_file=args.private/"private_german_references.json"
    prediction_file=args.private/"locked_ibm1_predictions.json"
    if args.stage=="fetch":
        req=urllib.request.Request(URL,headers={"User-Agent":"HieraticAI-W29-publisher-original-temple/1.0"})
        with urllib.request.urlopen(req,timeout=50) as f:
            raw=f.read(11_000_001)
        if len(raw)>11_000_000:raise TranslationError("Publisher source exceeds 11MB cap")
        result=fetch_and_split(raw,input_file,gold_file)
    elif args.stage=="train-predict":
        if prediction_file.exists():raise TranslationError("Prediction archive cannot be overwritten after fitting")
        results,meta=predict(json.loads(input_file.read_text("utf-8")))
        prediction_file.write_bytes(canonical(results))
        result={**meta,"prediction_archive_SHA256":sha256(prediction_file.read_bytes()).hexdigest()}
    else:
        result=score(json.loads(input_file.read_text("utf-8")),
            json.loads(prediction_file.read_text("utf-8")),
            json.loads(gold_file.read_text("utf-8")))
        result["locked_prediction_archive_SHA256"]=sha256(prediction_file.read_bytes()).hexdigest()
        result["original_source_inputs_SHA256"]=sha256(input_file.read_bytes()).hexdigest()
        result["private_reference_archive_SHA256"]=sha256(gold_file.read_bytes()).hexdigest()
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except (TranslationError,ValueError,KeyError,OSError) as exc:
        print("W29 first-use experiment REFUSED: "+str(exc),file=sys.stderr)
        raise SystemExit(2)
