"""W28 original-publisher AES letters: prospective no-reference-in-predictor evaluation.

Actual 19,946,763-byte original AES source must hash to the frozen Git blob.
Research-text-only; source-text groups are not independently physical witnesses.
No publisher German reference is ever supplied to the prediction subprocess.
No model scoring, labels or raw output content is written to the public repo.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha1, sha256
import itertools
import json
from pathlib import Path
import random
import re
import sys
import urllib.request
from typing import Any

from ling.translation import contextual, w11_evaluation
from ling.translation.compositional import ConstrainedComposer
from tools.translation_layer import TranslationError, _words, word_f1

UPSTREAM_REV = "35276d2527cca1a055e31ed5f6683e777717170f"
SOURCE_BLOB = "2c8db01616a37c75a3566e3b64d94a75fdf194c2"
SOURCE_SIZE = 19_946_763
SOURCE_URL = ("https://raw.githubusercontent.com/simondschweitzer/aes/"
              + UPSTREAM_REV + "/files/aes/_aes_bbawbriefe.json")
GROUP_SALT = "hieratic-w28-letters-v1:"
GROUP_COUNT = 32
MAX_BYTES = 25_000_000
VERSION = "W28-AES-LETTERS-SOURCE-LOCKED-1"
UNKNOWN = "[?]"


def blob_sha(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def check_original(raw: bytes) -> dict[str, dict[str, Any]]:
    if len(raw) != SOURCE_SIZE or blob_sha(raw) != SOURCE_BLOB:
        raise TranslationError("Original AES BBAW letters blob drift / truncated original")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict) or len(parsed) < GROUP_COUNT:
        raise TranslationError("Original publisher source schema unexpectedly changed")
    seen = set()
    for sid, rec in parsed.items():
        if (not isinstance(sid, str) or not sid or not isinstance(rec, dict)
                or not isinstance(rec.get("text"), str) or not rec["text"]
                or not isinstance(rec.get("token"), list)
                or not isinstance(rec.get("sentence_translation"), str)):
            raise TranslationError("Malformed original publisher sentence record")
        if sid in seen:
            raise TranslationError("Repeated publisher sentence ID")
        seen.add(sid)
    return parsed


def frozen_groups(source: dict[str, dict[str, Any]]) -> list[str]:
    ids = sorted({rec["text"] for rec in source.values()})
    if len(ids) < GROUP_COUNT:
        raise TranslationError("Fewer than 32 original source text IDs")
    return sorted(ids, key=lambda g: (sha256((GROUP_SALT + g).encode()).hexdigest(), g))[:GROUP_COUNT]


def source_to_separated_files(original: bytes, inp: Path, references: Path) -> dict[str, Any]:
    """Split in source-loading custody, then run predictor as a different process.

    Group selection examines only text IDs; missing German reference remains
    a *scoring abstention*, never a population-selection criterion.
    """
    source = check_original(original)
    selected = set(frozen_groups(source))
    inputs, labels = [], []
    for sid, rec in sorted(source.items()):
        if rec["text"] not in selected:
            continue
        forms = []
        for token in rec["token"]:
            if not isinstance(token, dict):
                raise TranslationError("Malformed selected Egyptian source token")
            form = token.get("written_form")
            if not isinstance(form, str) or not 0 < len(form) <= 512:
                raise TranslationError("Malformed selected Egyptian written form")
            forms.append(form)
        inputs.append({"sentence_id": sid, "text_id": rec["text"],
                       "forms": forms})
        labels.append({"sentence_id": sid, "text_id": rec["text"],
                       "german": rec["sentence_translation"].strip()})
    if not inputs or len({x["text_id"] for x in inputs}) != GROUP_COUNT:
        raise TranslationError("Fixed cohort lacks all frozen source groups")
    if any(not x["forms"] for x in inputs):
        raise TranslationError("Empty source sentence; no silent sample removal")
    if inp.resolve() == references.resolve() or inp.exists() or references.exists():
        raise TranslationError("Source/reference outputs must be new distinct paths")
    # External private work directory only; never committed or sent to Actions artifacts.
    inp.write_bytes(canonical(inputs))
    references.write_bytes(canonical(labels))
    return {"source_sha256": sha256(original).hexdigest(),
            "source_git_blob_sha1": blob_sha(original),
            "groups": GROUP_COUNT, "sentences": len(inputs),
            "source_input_sha256": sha256(inp.read_bytes()).hexdigest(),
            "gold_reference_sha256": sha256(references.read_bytes()).hexdigest(),
            "publisher_german_reference_in_predictor": False}


def _train() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    corpus = contextual.load_corpus()
    bundle = w11_evaluation.load(corpus)
    old = [row for name in contextual.DEV_CORPORA for row in corpus["groups"][name]
           if row["german"]]
    if len(old) != 904 or len(bundle["donor"]) != 3021:
        raise TranslationError("Pinned 3925 original AES donors changed")
    return old + bundle["donor"], bundle


class TrainSupportedPhraseComposer:
    """Strict, non-generative 3-token phrase-order vote over other texts.

    Learns only exact original-form triplets where published *cotext* German
    glosses have distinct single words in a publisher German sentence.
    Unknown/unsupported blocks fall back to W10 two-token composer.
    Never inserts any invented German word or retrieves an entire sentence.
    """

    def __init__(self, train: list[dict[str, Any]]):
        self.base = ConstrainedComposer(train)
        self.triplets: dict[tuple[str, str, str], dict[tuple[int, int, int], set[str]]] = defaultdict(
            lambda: defaultdict(set))
        self.train_german = {" ".join(_words(row["german"])) for row in train}
        for row in train:
            forms, glosses = row["forms"], row["glosses"]
            german = _words(row["german"])
            for i in range(len(forms) - 2):
                g = glosses[i:i+3]
                if any(not v or len(_words(v)) != 1 for v in g):
                    continue
                canonical_gloss = [_words(v)[0] for v in g]
                if len(set(canonical_gloss)) != 3:
                    continue
                # Do not infer positions from duplicates in target German text.
                if any(german.count(v) != 1 for v in canonical_gloss):
                    continue
                pos = [german.index(v) for v in canonical_gloss]
                permutation = tuple(sorted(range(3), key=lambda j: pos[j]))
                self.triplets[tuple(forms[i:i+3])][permutation].add(row["text_id"])

    def predict(self, row: dict[str, Any]) -> dict[str, Any]:
        if set(row) != {"sentence_id", "text_id", "forms", "glosses", "corpus"}:
            raise TranslationError("Target input contains extra fields (possible gold leakage)")
        baseline = self.base.predict(row)
        forms, units = row["forms"], baseline["units"]
        permutations, positions, i = [], [], 0
        while i < len(forms):
            if i + 2 < len(forms) and all(units[k]["gloss"] for k in range(i, i+3)):
                votes = self.triplets.get(tuple(forms[i:i+3]), {})
                default = len(votes.get((0,1,2), set()))
                proposals = sorted(((len(groups), perm) for perm, groups in votes.items()
                                    if perm != (0,1,2)), reverse=True)
                if proposals and proposals[0][0] >= 3 and proposals[0][0] > 2 * default:
                    # A three-word, source-form-specific inversion needs 3 independent
                    # training TEXT groups (not necessarily 3 physical witnesses).
                    n, perm = proposals[0]
                    positions.extend(i+j for j in perm)
                    permutations.append({"slots": [i,i+1,i+2], "train_text_votes": n})
                    i += 3
                    continue
            # Conservative fallback uses W10 precommitted two-token ordering.
            i += 1
        if not permutations:
            baseline["mode"] = "W28_TRAIN_SUPPORTED_PHRASE_ABSTAIN_FALLBACK_W10"
            baseline["three_token_reorders"] = []
            return baseline
        # Reapply selected triple-blocks while preserving nonselected slot ordering.
        fixed = []
        replacements = {tuple(p["slots"]): positions[j*3:j*3+3]
                        for j,p in enumerate(permutations)}
        idx = 0
        while idx < len(forms):
            hit = next((key for key in replacements if key[0] == idx), None)
            if hit:
                fixed.extend(replacements[hit]); idx += 3
            else:
                fixed.append(idx); idx += 1
        # Never add content words without training support.
        result = " ".join(units[j]["gloss"] or UNKNOWN for j in fixed)
        baseline.update({"prediction": result, "mode":"W28_SOURCE_VOTED_TRIPLETS",
                         "emitted_slot_order": fixed,
                         "three_token_reorders": permutations,
                         "accidental_exact_nonidentical_train_german":
                            bool(" ".join(_words(result)) in self.train_german)})
        return baseline


def project_input(rec: dict[str, Any]) -> dict[str, Any]:
    if set(rec) != {"sentence_id", "text_id", "forms"}:
        raise TranslationError("Predictor input may contain no gold or privileged target fields")
    if not isinstance(rec["forms"], list) or not rec["forms"]:
        raise TranslationError("Predictor requires original Egyptian token sequence")
    if any(not isinstance(x, str) or not x or len(x)>512 for x in rec["forms"]):
        raise TranslationError("Malformed input forms")
    return {"sentence_id":rec["sentence_id"],"text_id":rec["text_id"],
            "forms":tuple(rec["forms"]), "glosses":tuple(None for _ in rec["forms"]),
            "corpus":"w28_letters_original_new_32_groups"}


def predict_frozen(inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    train, bundle = _train()
    indexed = {row["text_id"] for row in train}
    projected = [project_input(r) for r in inputs]
    if len({r["text_id"] for r in projected}) != GROUP_COUNT:
        raise TranslationError("Frozen target group count not 32")
    if any(r["text_id"] in indexed for r in projected):
        raise TranslationError("Heldout text source collision with train")
    old_reserved = bundle["prior_heldout_text_ids"] | bundle["test_text_ids"]
    if any(r["text_id"] in old_reserved for r in projected):
        raise TranslationError("Target matches a previously exposed source group")
    baseline = contextual.TranslationMemory(train)
    composer = ConstrainedComposer(train)
    structured = TrainSupportedPhraseComposer(train)
    out = []
    for row in projected:
        gloss = baseline.gloss(row["forms"])
        w10 = composer.predict(row)
        w28 = structured.predict(row)
        out.append({"sentence_id":row["sentence_id"], "text_id":row["text_id"],
                    "source_form_sha256":sha256(canonical(row["forms"])).hexdigest(),
                    "gloss":gloss["text"], "w10":w10["prediction"],
                    "w28":w28["prediction"], "w28_mode":w28["mode"],
                    "unknown_tokens":w28["unknown_abstentions"],
                    "reordered_triplets":len(w28["three_token_reorders"]),
                    "direct_reference_field_used":False})
    return out


def score_frozen(inputs: list[dict[str,Any]], predictions: list[dict[str,Any]],
                 gold: list[dict[str,Any]]) -> dict[str,Any]:
    if len(inputs)!=len(predictions) or len(gold)!=len(inputs):
        raise TranslationError("Predictions and originals must close frozen denominator")
    ids = [x["sentence_id"] for x in inputs]
    if len(ids)!=len(set(ids)) or sorted(ids)!=sorted(x["sentence_id"] for x in predictions):
        raise TranslationError("Missing/extra/duplicate prediction IDs")
    if sorted(ids)!=sorted(x["sentence_id"] for x in gold):
        raise TranslationError("Gold reference populations differ")
    all_pred = {p["sentence_id"]:p for p in predictions}
    all_gold = {g["sentence_id"]:g for g in gold}
    metrics = {name:Counter() for name in ("gloss","w10","w28")}
    by_group: dict[str, dict[str,tuple[int,int,int]]] = defaultdict(dict)
    nrefs, zero_refs = 0,0
    source_token_count=unknown_total=triplets=0
    for row in inputs:
        sid=row["sentence_id"]; pred=all_pred[sid]; truth=all_gold[sid]
        if truth["text_id"]!=row["text_id"] or pred["text_id"]!=row["text_id"]:
            raise TranslationError("Golden reference moved across source group")
        if pred["source_form_sha256"]!=sha256(canonical(row["forms"])).hexdigest():
            raise TranslationError("Prediction source form bytes drift")
        if pred["direct_reference_field_used"] is not False:
            raise TranslationError("Gold used to generate a prediction")
        source_token_count+=len(row["forms"]);unknown_total+=pred["unknown_tokens"]
        triplets+=pred["reordered_triplets"]
        if not truth["german"]:
            zero_refs+=1
        else:
            nrefs+=1
        for name in metrics:
            if truth["german"]:
                m=word_f1(pred[name],truth["german"])
                v=(m["overlap"],m["predicted_word_count"],m["published_word_count"])
            else:
                v=(0,len(_words(pred[name])),0)
            metrics[name].update({"overlap":v[0],"pred_words":v[1],"ref_words":v[2],
                                  "scored":bool(truth["german"])})
            prev=by_group[row["text_id"]].get(name,(0,0,0))
            by_group[row["text_id"]][name]=tuple(prev[i]+v[i] for i in range(3))
    def f1(a:tuple[int,int,int]) -> float:
        intersection, pred, ref=a
        return 2*intersection/(pred+ref) if pred+ref else 0.0
    results={}
    for name,ctr in metrics.items():
        a=(ctr["overlap"],ctr["pred_words"],ctr["ref_words"])
        results[name]={"german_micro_f1":round(f1(a),8), "overlap_words":a[0],
                       "predicted_words":a[1],"reference_words":a[2],
                       "scored_sentences":ctr["scored"]}
    # Exact heldout group bootstrap is diagnostic only: documents may be
    # editorially/codicologically related even when source IDs differ.
    groups=sorted(by_group)
    rnd=random.Random(28);deltas=[]
    for _ in range(2000):
        sample=[by_group[groups[rnd.randrange(len(groups))]] for __ in groups]
        w10=tuple(sum(x["w10"][j] for x in sample) for j in range(3))
        w28=tuple(sum(x["w28"][j] for x in sample) for j in range(3))
        deltas.append(f1(w28)-f1(w10))
    deltas.sort()
    return {"protocol":VERSION,"new_source":SOURCE_BLOB,
            "source_groups":len(groups),"frozen_sentences":len(inputs),
            "with_german_references":nrefs,"without_german_reference":zero_refs,
            "source_egyptian_tokens":source_token_count,
            "w28_abstaining_source_units":unknown_total,
            "w28_triple_reorder_events":triplets,
            "diagnostic_scores":results,
            "w28_minus_w10_document_group_bootstrap_95pct":
                [round(deltas[49],8),round(deltas[1949],8)],
            "actual_hieratic_image_reading":False,
            "independent_physical_witness_split_proven":False,
            "qualified_semantic_gold_adjudicated":False,
            "capability_points_claimed":0.0}


def main(argv: list[str]|None=None) -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("stage",choices=("fetch","predict","score"))
    ap.add_argument("--workdir",type=Path,required=True)
    args=ap.parse_args(argv)
    wd=args.workdir
    if not wd.is_dir() or wd.is_symlink():
        raise TranslationError("Private workdir must pre-exist and be non-symlink")
    inp=wd/"source_inputs.json";gold=wd/"private_references.json"
    pred=wd/"private_predictions.json"
    if args.stage=="fetch":
        request=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"HieraticAI-W28-research/1.0"})
        with urllib.request.urlopen(request,timeout=45) as response:
            raw=response.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:
            raise TranslationError("Published source exceeds 25MB research limit")
        result=source_to_separated_files(raw,inp,gold)
        print(json.dumps(result,sort_keys=True))
    elif args.stage=="predict":
        if pred.exists() or not inp.is_file():
            raise TranslationError("Predictions must be written exactly once")
        predicted=predict_frozen(json.loads(inp.read_text("utf-8")))
        pred.write_bytes(canonical(predicted))
        print(json.dumps({"predictions":len(predicted),
                          "private_prediction_sha256":sha256(pred.read_bytes()).hexdigest(),
                          "does_not_read_private_reference_file":True},sort_keys=True))
    else:
        result=score_frozen(json.loads(inp.read_text("utf-8")),
                            json.loads(pred.read_text("utf-8")),
                            json.loads(gold.read_text("utf-8")))
        result["prediction_archive_sha256"]=sha256(pred.read_bytes()).hexdigest()
        result["source_input_sha256"]=sha256(inp.read_bytes()).hexdigest()
        result["private_reference_sha256"]=sha256(gold.read_bytes()).hexdigest()
        print(json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (ValueError,RuntimeError,KeyError,OSError) as exc:
        print(f"W28 transfer blocked: {exc}",file=sys.stderr)
        raise SystemExit(2)
