"""Source-text-held-out Egyptian→German lexical translation baseline on real AES.

The baseline generates a sequence of word-level German contextual glosses, NOT
a grammatically fluent whole-sentence neural translation. Against publisher
sentence translations it is an authentic *diagnostic* separate from visual OCR.
No target-text labels/translation may enter candidate selection. Every cited
published source remains CC BY-SA 4.0; no new blind expert gold is claimed.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

from ling.lexical import aes_holdout as source

VERSION = "ling003-aes-translation/1.0.0"
SOURCE_SENTENCE_TOTAL = 445
SOURCE_TRANSLATED_TOTAL = 444
SOURCE_TEXT_GROUP_TOTAL = 311


class TranslationError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_sentences(*, root: Path = source.ROOT) -> dict[str, Any]:
    """Independently pin publisher bytes and confirm the existing source rights."""
    bundle = source.read_bundle(root=root)
    path = root / "ling/lexical/data/aes_felsinschriften_ccby_sa.json"
    data = json.loads(source._blob(path, source.EXPECTED_AES_SHA, size_limit=2_000_000))
    if not isinstance(data, dict) or len(data) != SOURCE_SENTENCE_TOTAL:
        raise TranslationError("AES genuine published corpus population changed")
    groups = set()
    n_with_translation = 0
    for sid, sentence in data.items():
        if not isinstance(sid, str) or not isinstance(sentence, dict):
            raise TranslationError("Invalid publisher sentence identity")
        text_id, translation, tokens = sentence.get("text"), sentence.get("sentence_translation"), sentence.get("token")
        if not isinstance(text_id, str) or not text_id or not isinstance(translation, str) or not isinstance(tokens, list):
            raise TranslationError("Malformed publisher sentence/translation data")
        groups.add(text_id)
        if translation.strip():
            n_with_translation += 1
        if any(not isinstance(t, dict) or not isinstance(t.get("written_form"), str)
               for t in tokens):
            raise TranslationError("Malformed original publisher word form")
    if len(groups) != SOURCE_TEXT_GROUP_TOTAL or n_with_translation != SOURCE_TRANSLATED_TOTAL:
        raise TranslationError("AES source witness groups or translated sentences changed")
    return {
        "sentences": data,
        "source_revision": bundle["manifest"]["aes"]["revision"],
        "original_blob": source.EXPECTED_AES_SHA,
        "publisher_rights": bundle["manifest"]["license"],
        "source_groups": len(groups),
        "translation_count": n_with_translation,
    }


def _observations(sentences: dict[str, Any]) -> dict[str, list[tuple[str, str, str]]]:
    """Build *only* prior publisher cotext glosses, keyed by original form.

    Each candidate is labelled with its original source text, so a held-out
    source text can never retrieve its own target cotext annotation.
    """
    idx: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    for sent in sentences.values():
        origin = sent["text"]
        for token in sent["token"]:
            form, gloss = token.get("written_form"), token.get("cotext_translation")
            if (isinstance(form, str) and form and isinstance(gloss, str)
                    and gloss.strip() and len(gloss) <= 512):
                idx[form].add((origin, gloss.strip(), str(token.get("lemmaID") or "")))
    return {form: sorted(values) for form, values in idx.items()}


def translate_sentence(sentence: dict[str, Any],
                       observations: dict[str, list[tuple[str, str, str]]]) -> dict[str, Any]:
    """Produce deterministic *gloss-sequence translation*, never an editorial copy."""
    target_text = sentence["text"]
    units: list[dict[str, Any]] = []
    no_gloss = 0
    for i, token in enumerate(sentence["token"]):
        form = token["written_form"]
        # Never inspect token["cotext_translation"] or the sentence translation:
        # publisher gold remains evaluation-only for the held-out source text.
        matches = [(g, lid, origin) for origin, g, lid in observations.get(form, [])
                   if origin != target_text]
        # Do not use target token lemma ID either: that is editorial source gold.
        by_gloss: dict[str, set[str]] = defaultdict(set)
        for gloss, lid, origin in matches:
            by_gloss[gloss].add(origin)
        ranked = sorted(by_gloss, key=lambda g: (-len(by_gloss[g]), g))
        candidate = ranked[0] if ranked else None
        if candidate is None:
            no_gloss += 1
        units.append({
            "index": i, "source_form": form,
            "candidate_german_gloss": candidate,
            "alternatives": ranked[:12], "other_alternatives": max(0, len(ranked) - 12),
            "independent_source_text_support": len(by_gloss[candidate]) if candidate else 0,
            "status": "CROSS_TEXT_COTEXT_REFERENCE" if candidate else "ABSTAIN_UNATTESTED",
        })
    return {
        "source_text_id": target_text,
        "output_type": "ORDERED_GERMAN_WORD_GLOSS_SEQUENCE_NOT_FLUENT_TRANSLATION",
        "gloss_sequence": " ".join(x["candidate_german_gloss"] if x["candidate_german_gloss"]
                                    else "[?]" for x in units),
        "units": units,
        "tokens_total": len(units), "tokens_abstained": no_gloss,
        "publisher_target_translation_used_for_generation": False,
        "certified_translation_accuracy": False,
    }


def _words(text: str) -> list[str]:
    # Explicit whitespace/token punctuation normalization for a *diagnostic*.
    # It is NOT an Egyptological scholarly normalization of the source text.
    return re.findall(r"[^\W_]+", text.casefold(), flags=re.UNICODE)


def word_f1(candidate: str, published: str) -> dict[str, Any]:
    target, guess = Counter(_words(published)), Counter(_words(candidate))
    overlap = sum((target & guess).values())
    n_target, n_guess = sum(target.values()), sum(guess.values())
    precision = overlap / n_guess if n_guess else 0.0
    recall = overlap / n_target if n_target else 0.0
    return {
        "overlap": overlap, "predicted_word_count": n_guess,
        "published_word_count": n_target,
        "precision": round(precision, 8),
        "recall": round(recall, 8),
        "f1": round((2 * precision * recall / (precision + recall))
                    if precision + recall else 0.0, 8),
    }


def evaluate(data: dict[str, Any], *, include_examples: bool = False) -> dict[str, Any]:
    """Score 444 real published sentence translations with text-ID exclusion."""
    sentences = data["sentences"]
    observations = _observations(sentences)
    counts = Counter()
    per_text: dict[str, dict[str, int]] = defaultdict(lambda: {"sentences": 0, "scored": 0})
    cases = []
    sum_f1 = 0.0
    total_overlap = total_pred = total_ref = 0
    for sid, sentence in sorted(sentences.items()):
        counts["all_sentences"] += 1
        if not sentence["sentence_translation"].strip():
            counts["missing_publisher_reference_translation"] += 1
            continue
        prediction = translate_sentence(sentence, observations)
        # Published target is opened ONLY after the independent prediction.
        metric = word_f1(prediction["gloss_sequence"], sentence["sentence_translation"])
        counts["scored_sentences"] += 1
        counts["tokens_total"] += prediction["tokens_total"]
        counts["tokens_abstained"] += prediction["tokens_abstained"]
        counts["sentences_with_any_gloss"] += prediction["tokens_abstained"] < prediction["tokens_total"]
        counts["perfect_overlap_sentences"] += metric["f1"] == 1
        per_text[sentence["text"]]["sentences"] += 1
        per_text[sentence["text"]]["scored"] += 1
        sum_f1 += metric["f1"]
        total_overlap += metric["overlap"]
        total_pred += metric["predicted_word_count"]
        total_ref += metric["published_word_count"]
        if include_examples and len(cases) < 10:
            cases.append({
                "sentence_id": sid, "text_id": sentence["text"],
                "prediction_gloss_sequence": prediction["gloss_sequence"],
                "publisher_sentence_translation": sentence["sentence_translation"],
                "word_overlap_f1": metric["f1"], "token_abstentions": prediction["tokens_abstained"],
            })
    assert counts["all_sentences"] == SOURCE_SENTENCE_TOTAL
    assert counts["scored_sentences"] == SOURCE_TRANSLATED_TOTAL
    micro_p = total_overlap / total_pred if total_pred else 0.0
    micro_r = total_overlap / total_ref if total_ref else 0.0
    report = {
        "version": VERSION,
        "classification": "ACTUAL_PUBLISHED_TRANSLATION_DIAGNOSTIC_NOT_CERTIFIED_HELDOUT_MT",
        "publisher_original_git_blob": data["original_blob"],
        "published_license": data["publisher_rights"],
        "source_text_groups_total": data["source_groups"],
        "source_text_groups_scored": len(per_text),
        "split": "LEAVE_ENTIRE_AES_TEXT_ID_OUT_OF_COTEXT_REFERENCE_CANDIDATES",
        "reference_language": "German",
        "generated_output": "deterministic_cross_text_word_gloss_sequence",
        "metrics": dict(sorted(counts.items())),
        "mean_sentence_word_f1": round(sum_f1 / counts["scored_sentences"], 8),
        "corpus_micro_word_precision": round(micro_p, 8),
        "corpus_micro_word_recall": round(micro_r, 8),
        "corpus_micro_word_f1": round(2 * micro_p * micro_r / (micro_p + micro_r) if micro_p + micro_r else 0.0, 8),
        "examples": cases,
        "image_recognition_evaluation": False,
        "fluent_translation_evaluation": False,
        "expert_blind_gold": False,
        "scientific_release_admitted": False,
        "certified_model_performance": False,
        "limitations": [
            "Publisher sentence translations are editorial references, not newly blind expert labels.",
            "Cross-text cotext gloss selection is a deterministic baseline, not a fluent language model.",
            "AES texts and publisher AED share editorial provenance and may share underlying witnesses.",
            "Text-ID exclusion does not prove held-out physical manuscript or scribe independence.",
            "One source language's syntactic/semantic features are not captured by bag-of-word F1.",
            "German target punctuation, inflection and idioms make literal unigram overlap a limited metric.",
        ],
    }
    report["report_sha256"] = sha256(_canonical(report)).hexdigest()
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("verify", "evaluate", "predict"))
    p.add_argument("--sentence-id", default=None)
    p.add_argument("--examples", action="store_true")
    a = p.parse_args(argv)
    try:
        data = load_sentences()
        if a.action == "verify":
            out = {
                "publisher_sentences": len(data["sentences"]),
                "publisher_translated_sentences": data["translation_count"],
                "source_text_groups": data["source_groups"],
                "original_source_blob_sha1": data["original_blob"],
                "license": data["publisher_rights"],
                "certified_evaluation": False,
            }
        elif a.action == "evaluate":
            out = evaluate(data, include_examples=a.examples)
        else:
            if not a.sentence_id or a.sentence_id not in data["sentences"]:
                raise TranslationError("Exact source sentence ID required")
            out = translate_sentence(
                data["sentences"][a.sentence_id], _observations(data["sentences"]))
        print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (source.SourceError, TranslationError, ValueError, OSError) as exc:
        print(f"TRANSLATION-LAYER REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
