"""W30 C genuine first-use original AES Amarna phrase-aware IBM1 CPU study.

The original publisher German answers are stored under a separate path and
read ONLY in the final scoring process, after immutable prediction byte digest.
"""
from __future__ import annotations
import argparse,hashlib,json,random,sys,urllib.request
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any
from ling.translation import w29_temple_ibm1 as prior
from tools.translation_layer import TranslationError,_words

SOURCE_FILE="_aes_bbawamarna.json"
SOURCE_COMMIT="35276d2527cca1a055e31ed5f6683e777717170f"
SOURCE_BLOB="5e512681dc0d1ac7177a62531582b3473a0a11f2"
SOURCE_BYTES=14683204
SOURCE_URL=f"https://raw.githubusercontent.com/simondschweitzer/aes/{SOURCE_COMMIT}/files/aes/{SOURCE_FILE}"
HASH_SALT="hieratic-ai-w30-amarna-first-use:"
GROUP_COUNT=32
SUPPORT_GRID=(2,3,5)
MARGIN_GRID=(0.5,1.0)
VERSION="W30-ORIGINAL-UNEXPOSED-AMARNA-PHRASE-IBM1/1"

def frozen_ids(rows:dict[str,dict])->list[str]:
    ids={str(item["text"]) for item in rows.values()}
    if len(ids)<GROUP_COUNT:raise TranslationError("New original AES file has fewer than 32 text groups, fail-closed")
    return sorted(ids,key=lambda x:(hashlib.sha256((HASH_SALT+x).encode()).hexdigest(),x))[:GROUP_COUNT]

def source_rows(raw:bytes)->dict[str,dict]:
    if len(raw)!=SOURCE_BYTES or prior.gitblob(raw)!=SOURCE_BLOB:
        raise TranslationError("New AES publisher source original byte identity drift")
    rows=json.loads(raw)
    if not isinstance(rows,dict) or len(rows)<GROUP_COUNT:raise TranslationError("Not original source sentence map")
    for sid,row in rows.items():
        if not isinstance(row,dict) or not isinstance(row.get("text"),str) or not isinstance(row.get("token"),list) or not isinstance(row.get("sentence_translation"),str):
            raise TranslationError("New publisher sentence shape unexpected")
    return rows

def source_split(raw:bytes,path_source:Path,path_gold:Path)->dict:
    rows=source_rows(raw)
    selection=set(frozen_ids(rows))
    if path_source.exists() or path_gold.exists():raise TranslationError("Cannot overwrite original heldout freeze")
    source=[];gold=[]
    for sid,row in sorted(rows.items()):
        if row["text"] not in selection:continue
        tokens=row["token"]
        if any(not isinstance(t,dict) or not isinstance(t.get("written_form"),str) for t in tokens):
            raise TranslationError("Original source token shape invalid")
        forms=[t["written_form"] for t in tokens]
        if not forms:raise TranslationError("Empty original source sentence cannot be silently dropped")
        source.append({"sentence_id":sid,"text_id":row["text"],"forms":forms})
        gold.append({"sentence_id":sid,"text_id":row["text"],"german":row["sentence_translation"]})
    if len({x["text_id"] for x in source})!=GROUP_COUNT or len(source)!=len(gold):
        raise TranslationError("New source group census unexpectedly changed")
    path_source.write_bytes(prior.canonical(source))
    path_gold.write_bytes(prior.canonical(gold))
    return {"version":VERSION,"source_bytes":len(raw),"source_git_blob":prior.gitblob(raw),
            "source_sha256":hashlib.sha256(raw).hexdigest(),
            "frozen_text_groups":GROUP_COUNT,"source_sentences":len(source),
            "new_source_only_sha256":hashlib.sha256(path_source.read_bytes()).hexdigest(),
            "sealed_publisher_reference_sha256":hashlib.sha256(path_gold.read_bytes()).hexdigest(),
            "reference_opened_by_predictor":False}

def dev_split(donor:list[dict])->tuple[list[dict],list[dict]]:
    text_ids={x["text_id"] for x in donor}
    ranked=sorted(text_ids,key=lambda x:(hashlib.sha256(("hieratic-ai-w30-phrase-internal:"+x).encode()).hexdigest(),x))
    dev=set(ranked[:max(1,len(ranked)//5)])
    return [x for x in donor if x["text_id"] not in dev],[x for x in donor if x["text_id"] in dev]

class PhraseIBM1:
    def __init__(self,donor:list[dict]):
        self.base=prior.IBM1(donor)
        self.pair_support=Counter()
        self.pair_weights:dict[tuple[str,str],Counter]=defaultdict(Counter)
        for row in donor:
            src=tuple(str(x) for x in row["forms"])
            tgt=_words(row["german"])
            if len(src)<2 or len(tgt)<2:continue
            target_pairs=Counter(zip(tgt,tgt[1:]))
            for a,b in zip(src,src[1:]):
                if self.base.support[a]<2 or self.base.support[b]<2:continue
                pair=(a,b)
                self.pair_support[pair]+=1
                # Source-aware lexical support; do not simply memorize a donor
                # whole sentence or inspect external German references.
                pa=self.base.prob.get(a,{})
                pb=self.base.prob.get(b,{})
                for (g1,g2),c in target_pairs.items():
                    normal=pa.get(g1,0)*pb.get(g2,0)
                    reverse=pa.get(g2,0)*pb.get(g1,0)
                    strength=max(normal,reverse)*c
                    if strength>0:
                        self.pair_weights[pair][(g1,g2)]+=strength
        self.best={pair:sorted(c.items(),key=lambda x:(-x[1],x[0]))[0]
                   for pair,c in self.pair_weights.items() if c}

    def emit(self,forms:tuple[str,...],support:int,margin:float)->tuple[str,int,int]:
        token=[self.base.predict((f,))[0] for f in forms]
        unknown=sum(t==prior.UNKNOWN for t in token)
        output=[];i=0;replacements=0
        while i<len(forms):
            if i+1<len(forms):
                pair=forms[i],forms[i+1]
                candidate=self.best.get(pair)
                if candidate and self.pair_support[pair]>=support:
                    (g1,g2),strength=candidate
                    p1=self.base.prob.get(pair[0],{})
                    p2=self.base.prob.get(pair[1],{})
                    usual=max(p1.values(),default=0)*max(p2.values(),default=0)
                    if (g1,g2)!=(token[i],token[i+1]) and strength/max(1,self.pair_support[pair]) >= margin*usual:
                        output.extend((g1,g2));i+=2;replacements+=1
                        continue
            output.append(token[i]);i+=1
        return " ".join(output),unknown,replacements

def _tokens(s:str)->list[str]:
    return list(_words(s))

def bigram_counts(pred:str,target:str)->tuple[int,int,int]:
    a=Counter(zip(_tokens(pred),_tokens(pred)[1:]))
    b=Counter(zip(_tokens(target),_tokens(target)[1:]))
    return sum((a&b).values()),sum(a.values()),sum(b.values())

def metric(acc:tuple[int,int,int])->float:
    hit,total,pub=acc
    return (2*hit)/(total+pub) if total+pub else 0.0

def train_predict(sources:list[dict])->tuple[list[dict],dict]:
    if len({x["text_id"] for x in sources})!=GROUP_COUNT:
        raise TranslationError("Unexpected 32 source-group population")
    donor=prior._train()
    disjoint={x["text_id"] for x in sources}.isdisjoint({x["text_id"] for x in donor})
    if not disjoint:raise TranslationError("Heldout original source IDs overlap donor")
    tr,dev=dev_split(donor)
    devmodel=PhraseIBM1(tr)
    # Only donor-internal group-disjoint reference scores select phrase grid.
    scores=[]
    for support in SUPPORT_GRID:
        for margin in MARGIN_GRID:
            a=[0,0,0];known=0
            for x in dev:
                guess,_,_ =devmodel.emit(tuple(x["forms"]),support,margin)
                q=bigram_counts(guess,x["german"])
                for i in range(3):a[i]+=q[i]
                known+=1
            scores.append({"support":support,"margin":margin,"dev_bigram_f1":metric(tuple(a)),"dev_rows":known})
    choice=sorted(scores,key=lambda q:(-q["dev_bigram_f1"],q["support"],q["margin"]))[0]
    model=PhraseIBM1(donor)
    control=prior.ConstrainedComposer(donor)
    out=[];unknown=0;changes=0
    for row in sources:
        cleaned=prior.previous.project_input(row)
        ibm,no= model.base.predict(cleaned["forms"])
        phrase,noun,nreplace=model.emit(cleaned["forms"],choice["support"],choice["margin"])
        old=control.predict(cleaned)["prediction"]
        out.append({"sentence_id":row["sentence_id"],"text_id":row["text_id"],
            "egyptian_sha256":hashlib.sha256(prior.canonical(row["forms"])).hexdigest(),
            "old_w10":old,"ibm1":ibm,"phrase_ibm1":phrase,
            "unknown_source_tokens":no,"phrase_substitutions":nreplace})
        unknown+=no;changes+=nreplace
    return out,{"donor_sentences":len(donor),"donor_train_internal_sentences":len(tr),
                "donor_dev_internal_sentences":len(dev),"real_ibm1_fitting_rows":model.base.sentence_count,
                "original_conditional_forms":len(model.base.best),
                "trained_phrase_context_types":len(model.best),
                "tuned_phrase_threshold":choice,
                "train_internal_dev_grid":scores,
                "new_target_predictions":len(out),"total_unknown_source_tokens":unknown,
                "actual_phrase_substitutions":changes,
                "new_publisher_german_references_seen_during_fit_or_prediction":False}

def _add(dst:list[int],item:tuple[int,int,int])->None:
    for i in range(3):dst[i]+=item[i]

def score(source:list[dict],pred:list[dict],gold:list[dict])->dict:
    original={x["sentence_id"]:x for x in source}
    predictions={x["sentence_id"]:x for x in pred}
    refs={x["sentence_id"]:x for x in gold}
    if len(original)!=len(source) or len(predictions)!=len(pred) or len(refs)!=len(gold) or set(original)!=set(predictions) or set(original)!=set(refs):
        raise TranslationError("Frozen original/answer/prediction exact population mismatch")
    groups=defaultdict(lambda:{(model,kind):[0,0,0] for model in ("old_w10","ibm1","phrase_ibm1") for kind in ("words","bigrams")})
    all_counts={(model,kind):[0,0,0] for model in ("old_w10","ibm1","phrase_ibm1") for kind in ("words","bigrams")}
    num_gold=0;missing=0;units=0;unk=0;changes=0
    for sid,row in original.items():
        rec=predictions[sid];ref=refs[sid]
        if rec["text_id"]!=row["text_id"] or ref["text_id"]!=row["text_id"] or rec["egyptian_sha256"]!=hashlib.sha256(prior.canonical(row["forms"])).hexdigest():
            raise TranslationError("Source original sentence/group SHA mismatch")
        units+=len(row["forms"]);unk+=rec["unknown_source_tokens"];changes+=rec["phrase_substitutions"]
        target=ref["german"]
        if not target:missing+=1;continue
        num_gold+=1
        for model in ("old_w10","ibm1","phrase_ibm1"):
            a=Counter(_tokens(rec[model]));b=Counter(_tokens(target))
            word=(sum((a&b).values()),sum(a.values()),sum(b.values()))
            gram=bigram_counts(rec[model],target)
            for key,item in (( (model,"words"),word),((model,"bigrams"),gram)):
                _add(all_counts[key],item);_add(groups[row["text_id"]][key],item)
    if len({x["text_id"] for x in source})!=GROUP_COUNT:raise TranslationError("Expected complete 32 original source groups")
    results={name:{kind:{"f1":round(metric(tuple(all_counts[(name,kind)])),8),
                         "overlap":all_counts[(name,kind)][0],
                         "predicted_units":all_counts[(name,kind)][1],
                         "reference_units":all_counts[(name,kind)][2]}
                     for kind in ("words","bigrams")}
             for name in ("old_w10","ibm1","phrase_ibm1")}
    randomizer=random.Random(30);identities=sorted(groups);boost=[]
    for _ in range(2000):
        selected=[groups[identities[randomizer.randrange(len(identities))]] for _ in identities]
        a=[sum(t[("phrase_ibm1","words")][j] for t in selected) for j in range(3)]
        b=[sum(t[("ibm1","words")][j] for t in selected) for j in range(3)]
        boost.append(metric(tuple(a))-metric(tuple(b)))
    boost.sort()
    return {"schema":VERSION,"original_heldout_text_groups":GROUP_COUNT,
        "total_original_sentences":len(source),"scored_nonempty_german_reference":num_gold,
        "missing_german_reference":missing,
        "original_source_tokens":units,"unknown_source_tokens":unk,
        "actual_phrase_substitutions":changes,
        "real_cpu_model_fit":True,
        "model_results":results,
        "phrase_minus_ibm_word_micro_f1_group_bootstrap_interval":[round(boost[49],8),round(boost[1949],8)],
        "new_gold_accessed_after_predictions_frozen":True,
        "original_hieratic_photos_used":False,
        "qualified_egyptologist_semantic_accuracy":None,
        "physical_manuscript_disjointness_verified":False,
        "weighted_points_earned":0}

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("stage",choices=("fetch","train","score"))
    parser.add_argument("--private",type=Path,required=True)
    args=parser.parse_args()
    root=args.private
    if not root.is_dir() or root.is_symlink():raise TranslationError("Private temporary directory required")
    source=root/"source_only.json";gold=root/"sealed_german_editorial.json";pred=root/"predictions_sha_frozen.json"
    if args.stage=="fetch":
        with urllib.request.urlopen(urllib.request.Request(SOURCE_URL,headers={
                "User-Agent":"HieraticAI-W30-first-use-Amarna-CPU-study/1.0"}),timeout=55) as handle:
            raw=handle.read(16_000_001)
        if len(raw)>16_000_000:raise TranslationError("Original publisher source exceeds declared 16MB cap")
        result=source_split(raw,source,gold)
    elif args.stage=="train":
        if pred.exists():raise TranslationError("Previously frozen predictions cannot be overwritten")
        res,report=train_predict(json.loads(source.read_text()))
        pred.write_bytes(prior.canonical(res))
        result={**report,"prediction_archive_sha256":hashlib.sha256(pred.read_bytes()).hexdigest()}
    else:
        result=score(json.loads(source.read_text()),json.loads(pred.read_text()),json.loads(gold.read_text()))
        result.update({"source_only_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
                       "sealed_editorial_ref_sha256":hashlib.sha256(gold.read_bytes()).hexdigest(),
                       "locked_prediction_archive_sha256":hashlib.sha256(pred.read_bytes()).hexdigest()})
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except (TranslationError,KeyError,ValueError,OSError) as exc:
        print("W30 FIRST USE FAIL CLOSED: "+str(exc),file=sys.stderr)
        raise SystemExit(2)
