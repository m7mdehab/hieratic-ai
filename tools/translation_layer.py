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


def _parallel_translations(sentences: dict[str, Any]) -> dict[tuple[str, ...], list[tuple[str, str]]]:
    """Published whole-sentence parallels, never target source text itself."""
    groups: dict[tuple[str, ...], set[tuple[str, str]]] = defaultdict(set)
    for sentence in sentences.values():
        german = sentence["sentence_translation"].strip()
        if german and sentence["token"]:
            key = tuple(token["written_form"] for token in sentence["token"])
            groups[key].add((sentence["text"], german))
    return {key: sorted(value) for key, value in groups.items()}


def translate_sentence(sentence: dict[str, Any],
                       observations: dict[str, list[tuple[str, str, str]]], *,
                       parallel_translations: dict[tuple[str, ...], list[tuple[str, str]]] | None = None) -> dict[str, Any]:
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
    # An identical complete Egyptian token sequence attested in a DIFFERENT
    # original text ID may supply a genuinely published German full sentence.
    # This is a retrieval-only literary parallel, not a learned translation.
    source_words = tuple(token["written_form"] for token in sentence["token"])
    parallels = [(text_id, translated) for text_id, translated in
                 (parallel_translations or {}).get(source_words, ())
                 if text_id != target_text]
    choices: dict[str, set[str]] = defaultdict(set)
    for text_id, german in parallels:
        choices[german].add(text_id)
    ordered_parallels = sorted(choices, key=lambda text: (-len(choices[text]), text))
    published_peer_translation = ordered_parallels[0] if ordered_parallels else None
    return {
        "source_text_id": target_text,
        "translation_mode": ("CROSS_TEXT_EXACT_SENTENCE_PARALLEL" if published_peer_translation
                             else "ORDERED_COTEXT_GLOSS_FALLBACK"),
        "publisher_attested_german_sentence": published_peer_translation,
        "independent_source_text_support_for_sentence": (
            len(choices[published_peer_translation]) if published_peer_translation else 0),
        "other_publisher_sentential_alternatives": ordered_parallels[1:12],
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
    parallels = _parallel_translations(sentences)
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
        prediction = translate_sentence(sentence, observations,
                                        parallel_translations=parallels)
        if prediction["publisher_attested_german_sentence"]:
            counts["sentences_with_cross_text_attested_full_german_translation"] += 1
        # Published target is opened ONLY after the independent prediction.
        # Score exactly the actual output selected by the translation layer:
        # source-independent publisher sentence where attested, otherwise gloss.
        predicted_german = (prediction["publisher_attested_german_sentence"]
                            or prediction["gloss_sequence"])
        metric = word_f1(predicted_german, sentence["sentence_translation"])
        if prediction["publisher_attested_german_sentence"] and metric["f1"] == 1:
            counts["cross_text_publisher_full_sentence_word_exact"] += 1
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
                "actual_translation_output": predicted_german,
                "translation_mode": prediction["translation_mode"],
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
        "generated_output": "exact_cross_text_publisher_sentence_where_attested_else_word_gloss_sequence",
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




def translate_interpretation_manifest(
    interpretation: dict[str, Any], observations: dict[str, list[tuple[str, str, str]]],
    *, excluded_text_id: str | None = None,
) -> dict[str, Any]:
    """Chain authentic LING-002 interpreted readings into German gloss hypotheses.

    The original LING-002 manifest is retained intact; each alternative reading
    receives a separately sourced glossary candidate. No invented morphology,
    no inferred source text ID, no claims that Egyptian text was recognized
    from original image bytes, and no scoring against a target reference.
    """
    from tools import lexical_interpretation as lexical
    if not isinstance(interpretation, dict):
        raise TranslationError("LING-002 interpretation must be an object")
    try:
        schema = json.loads(lexical.SCHEMA_PATH.read_text("utf-8"))
        errors = lexical.definition_errors(
            interpretation, schema, "interpretationManifest", "interpretation")
    except (ValueError, OSError, TypeError, KeyError) as exc:
        raise TranslationError(f"LING-002 interpretation validation failed: {exc}") from exc
    if errors:
        raise TranslationError("Invalid LING-002 interpretation: " + "; ".join(errors[:4]))
    identity = {k: v for k, v in interpretation.items()
                if k not in ("schema_version", "interpretation_version_id")}
    if interpretation["interpretation_version_id"] != (
        "lex-" + sha256(_canonical(identity)).hexdigest()
    ):
        raise TranslationError("LING-002 version hash drift: lexical source modified")
    reg = interpretation["interpretation_input"]["source_registry_id"]
    if reg == "SRC-AES-OPEN" and not excluded_text_id:
        raise TranslationError(
            "AES source text requires independent excluded_text_id to prevent label leakage")
    if excluded_text_id is not None and (
        not isinstance(excluded_text_id, str) or len(excluded_text_id) > 256
        or not excluded_text_id.strip()
    ):
        raise TranslationError("Invalid excluded source text ID")
    items = []
    for item in interpretation["items"]:
        readings = []
        for reading in item["readings"]:
            form = reading["normalized_text"]
            if form is None:
                readings.append({
                    "source_value_id": reading["source_value_id"], "normalized_text": None,
                    "source_outcome": reading["outcome"], "german_gloss_candidates": [],
                    "translation_status": "UNKNOWN_SOURCE_READING",
                    "translations_blind_certified": False,
                })
                continue
            if len(form) > 512:
                raise TranslationError("Unbounded LING-002 source form")
            by_gloss: dict[str, set[str]] = defaultdict(set)
            for text_id, gloss, _ in observations.get(form, []):
                if text_id != excluded_text_id:
                    by_gloss[gloss].add(text_id)
            alternatives = sorted(by_gloss, key=lambda x: (-len(by_gloss[x]), x))
            readings.append({
                "source_value_id": reading["source_value_id"],
                "normalized_text": form,
                "source_outcome": reading["outcome"],
                "german_gloss_candidates": [
                    {"text": g, "other_source_texts_support": len(by_gloss[g])}
                    for g in alternatives[:25]
                ],
                "remaining_gloss_alternatives": max(0, len(alternatives) - 25),
                "translation_status": (
                    "AMBIGUOUS_GERMAN_GLOSS" if len(alternatives) > 1
                    else "GERMAN_GLOSS_CANDIDATE" if alternatives
                    else "NO_CROSS_TEXT_GLOSS_ABSTAIN"
                ),
                "translations_blind_certified": False,
            })
        items.append({
            "unit_id": item["unit_id"], "line_id": item["line_id"],
            "token_id": item["token_id"], "original_outcome": item["outcome"],
            "readings": readings,
        })
    result = {
        "version": VERSION,
        "input_ling002_interpretation_id": interpretation["interpretation_version_id"],
        "input_ling002_source": interpretation["interpretation_input"],
        "excluded_aes_source_text_id": excluded_text_id,
        "source_language": "Ancient Egyptian transliteration",
        "target_language": "German",
        "output_type": "LAYERED_TOKEN_MEANING_GLOSSES_WITH_ALTERNATIVES",
        "items": items,
        "ling002_original_not_modified": True,
        "publisher_source_layer": "AES_CC_BY_SA_CROSS_TEXT_EDITORIAL_GLOSSES",
        "source_original_hieratic_image_observed": False,
        "certified_sentence_translation": False,
    }
    result["translation_version_sha256"] = sha256(_canonical(result)).hexdigest()
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("verify", "evaluate", "predict", "from-lexical"))
    p.add_argument("--interpretation", type=Path, default=None)
    p.add_argument("--exclude-text-id", default=None)
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
        elif a.action == "from-lexical":
            if not a.interpretation or not a.interpretation.is_file() or a.interpretation.stat().st_size > 8_000_000:
                raise TranslationError("An existing bounded --interpretation JSON is required")
            try:
                imported = json.loads(a.interpretation.read_text("utf-8"))
            except (ValueError, UnicodeError, OSError) as exc:
                raise TranslationError(f"Invalid LING-002 interpretation: {exc}") from exc
            out = translate_interpretation_manifest(
                imported, _observations(data["sentences"]),
                excluded_text_id=a.exclude_text_id)
        else:
            if not a.sentence_id or a.sentence_id not in data["sentences"]:
                raise TranslationError("Exact source sentence ID required")
            out = translate_sentence(
                data["sentences"][a.sentence_id], _observations(data["sentences"]),
                parallel_translations=_parallel_translations(data["sentences"]))
        print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (source.SourceError, TranslationError, ValueError, OSError) as exc:
        print(f"TRANSLATION-LAYER REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
