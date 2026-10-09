"""Frozen W10 original-AES archival editorial-text diagnostic.

The archive's German publisher references are a NEW text-only holdout. The
method and cohort selection were independently preregistered on the branch
before ingesting those 47 translations; no manuscript gold is asserted.
"""
from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any

from ling.translation import contextual
from ling.translation.compositional import (
    ConstrainedComposer, VERSION, MIN_CONTEXT_SUPPORT, MIN_SWAP_SUPPORT,
    MAX_ALTERNATIVES,
)
from tools.translation_layer import TranslationError, _canonical

ROOT = contextual.ROOT
COHORT = Path("ling/translation/data/w10_archive_32groups_ccby_sa.json")
COHORT_BLOB_SHA1 = "d3d7b57aef7bd10a48df6b1be340be8ff5b36e32"
ORIGINAL_AES_BLOB_SHA1 = "014cccf04235d9e093fca24ed48c62630d235852"
ORIGINAL_AES_BYTES = 5855067
COHORT_SEED = "hieratic-ai-ling003-w10-archive-v1:"
COHORT_GROUPS = 32
COHORT_SENTENCES = 47
COHORT_TRANSLATED = 47


def blob_sha(data: bytes) -> str:
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def rank_source_text_ids(ids: set[str]) -> list[str]:
    """Rank blindly by original source-text IDs, never by a German reference."""
    return sorted(ids, key=lambda text: (
        sha256((COHORT_SEED + text).encode("utf-8")).hexdigest(), text
    ))


def project_original_archive(raw: bytes) -> dict[str, Any]:
    """Reproduce the pinned 32-group subset from verified 5.8MB publisher source."""
    if len(raw) != ORIGINAL_AES_BYTES or blob_sha(raw) != ORIGINAL_AES_BLOB_SHA1:
        raise TranslationError("Original AES bbawarchive Git blob mismatch")
    try:
        original = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise TranslationError("Bad original upstream AES publisher JSON") from exc
    if not isinstance(original, dict):
        raise TranslationError("Original archive must be an object")
    groups = {record["text"] for record in original.values()}
    if len(groups) < COHORT_GROUPS:
        raise TranslationError("Too few distinct publisher source IDs")
    chosen = set(rank_source_text_ids(groups)[:COHORT_GROUPS])
    return {
        sid: {
            "text": record["text"],
            "token": [{"written_form": token["written_form"]}
                      for token in record["token"]],
            "sentence_translation": record["sentence_translation"],
        }
        for sid, record in sorted(original.items()) if record["text"] in chosen
    }


def load_archive(corpus: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    """Do not let a modified source, exposed split or extra label enter scoring."""
    path = root / COHORT
    if path.is_symlink() or not path.is_file():
        raise TranslationError("Pinned W10 archive cohort absent or linked")
    data = path.read_bytes()
    if not (1 <= len(data) <= 400_000) or blob_sha(data) != COHORT_BLOB_SHA1:
        raise TranslationError("W10 CC-BY-SA archive cohort Git blob mismatch")
    try:
        original = json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise TranslationError("W10 source cohort JSON malformed") from exc
    if not isinstance(original, dict) or len(original) != COHORT_SENTENCES:
        raise TranslationError("W10 cohort sentence population drift")
    excluded_ids = {row["text_id"] for sub in corpus["groups"].values() for row in sub}
    text_ids = set()
    published = []
    for sid, record in sorted(original.items()):
        if not isinstance(record, dict) or set(record) != {
            "text", "token", "sentence_translation"
        }:
            raise TranslationError("Unrecognized field or missing original archive record")
        text_id = record["text"]
        german = record["sentence_translation"]
        tokens = record["token"]
        if (not isinstance(sid, str) or not sid
                or not isinstance(text_id, str) or not text_id
                or not isinstance(german, str)
                or not isinstance(tokens, list) or not tokens):
            raise TranslationError("Malformed archive sentence or German reference")
        forms = []
        for token in tokens:
            if not isinstance(token, dict) or set(token) != {"written_form"}:
                raise TranslationError("Archive source token may not contain target gloss labels")
            form = token["written_form"]
            if not isinstance(form, str) or not form or len(form) > 512:
                raise TranslationError("Invalid source Egyptian written form")
            forms.append(form)
        text_ids.add(text_id)
        published.append({
            "sentence_id": sid, "text_id": text_id, "corpus": "bbawarchive",
            "forms": tuple(forms), "glosses": tuple(None for _ in forms),
            "german": german.strip(),
        })
    if len(text_ids) != COHORT_GROUPS:
        raise TranslationError("Archive source group count drift")
    if text_ids & excluded_ids:
        raise TranslationError("New archive corpus overlaps prior AES source-text IDs")
    if sum(bool(row["german"]) for row in published) != COHORT_TRANSLATED:
        raise TranslationError("Archive translation count drift")
    # All members rank at or before the locked 32nd digest cutoff. Reproducing
    # the *global* top-32 membership still requires the original 5.8MB blob.
    cutoff = "07879a455084eda945f8837f2e8cb438c1850539f9cebd8768e6b8b1aa19594d"
    digests = {
        sha256((COHORT_SEED + text_id).encode("utf-8")).hexdigest()
        for text_id in text_ids
    }
    if len(digests) != COHORT_GROUPS or max(digests) != cutoff:
        raise TranslationError("W10 preregistered SHA256 group cohort mismatch")
    return {"rows": published, "text_ids": sorted(text_ids),
            "original_sha1": ORIGINAL_AES_BLOB_SHA1,
            "derived_git_blob_sha1": COHORT_BLOB_SHA1}


def compare(rows: list[dict[str, Any]], train: list[dict[str, Any]]) -> dict[str, Any]:
    """Equal train-only evidence and complete denominators across three systems."""
    if {r["text_id"] for r in rows} & {r["text_id"] for r in train}:
        raise TranslationError("Evaluation source-text contamination")
    memory = contextual.TranslationMemory(train)
    composer = ConstrainedComposer(train)
    prediction_rows = {"gloss_control": [], "w9_contextual_memory": [],
                       "w10_composition": []}
    counts = {"unknown_token_abstentions": 0,
              "context_selected_source_units": 0,
              "independently_supported_adjacent_swaps": 0,
              "accidental_nonidentical_train_german_matches": 0}
    for row in rows:
        gloss = memory.gloss(row["forms"])
        remembered = memory.predict(row, 0.0)  # frozen prior W9 threshold
        composition = composer.predict(row)
        prediction_rows["gloss_control"].append(
            (row, {"prediction": gloss["text"], "mode": gloss["mode"]}))
        prediction_rows["w9_contextual_memory"].append((row, remembered))
        prediction_rows["w10_composition"].append((row, composition))
        counts["unknown_token_abstentions"] += composition["unknown_abstentions"]
        counts["context_selected_source_units"] += composition["context_selected_units"]
        counts["independently_supported_adjacent_swaps"] += len(
            composition["learned_adjacent_swaps"])
        counts["accidental_nonidentical_train_german_matches"] += int(
            composition["accidental_exact_nonidentical_train_german"])
    return {
        "population": {
            "sentences_seen": len(rows),
            "german_refs_present": sum(bool(row["german"]) for row in rows),
            "source_texts": len({row["text_id"] for row in rows}),
            "egyptian_tokens": sum(len(row["forms"]) for row in rows),
        },
        "metrics": {name: contextual._accumulate(items)
                    for name, items in prediction_rows.items()},
        "composition_controls": counts,
        "no_train_target_text_id_intersection": True,
        "new_editorial_source_independent_physical_support_unverified": True,
        "certified_translation_or_hieratic_reading": False,
    }


def evaluate_internal(corpus: dict[str, Any]) -> dict[str, Any]:
    """Predeclared 5-fold development only; no archive/test inference."""
    training = [row for name in contextual.DEV_CORPORA
                for row in corpus["groups"][name] if row["german"]]
    folds = []
    for fold in range(contextual.FOLDS):
        train = [r for r in training if contextual._fold(r["text_id"]) != fold]
        dev = [r for r in training if contextual._fold(r["text_id"]) == fold]
        folds.append({"fold": fold, "results": compare(dev, train)})
    if sum(f["results"]["population"]["sentences_seen"] for f in folds) != 904:
        raise TranslationError("Grouped internal development census drift")
    return {"folds": folds, "training_dev_sentences": 904,
            "used_external_references_to_select_parameters": False}


def evaluate_external(corpus: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    """Use the fixed model on one new source-group-blocked cohort only."""
    # Separate internal preflight is fixed; no metric-based model selection.
    internal = evaluate_internal(corpus)
    archive = load_archive(corpus, root)
    training = [r for name in contextual.DEV_CORPORA
                for r in corpus["groups"][name] if r["german"]]
    fresh = compare(archive["rows"], training)
    report = {
        "experiment": VERSION,
        "classification": "NEW_AES_ARCHIVE_TEXT_ONLY_PUBLISHER_EXTERNAL_DIAGNOSTIC",
        "rights": "CC-BY-SA-4.0",
        "source_revision": contextual.UPSTREAM_COMMIT,
        "upstream_archive_original_git_blob": archive["original_sha1"],
        "w10_derived_corpus_git_blob": archive["derived_git_blob_sha1"],
        "cohort": "32 complete source text IDs by preregistered SHA256 original-text-ID rank",
        "prior_revealed_tuebingen_in_training_or_tuning": False,
        "archive_training_or_tuning": False,
        "fixed_reorder_min_texts": MIN_SWAP_SUPPORT,
        "fixed_context_min_texts": MIN_CONTEXT_SUPPORT,
        "fixed_max_gloss_alternatives": MAX_ALTERNATIVES,
        "internal_fold_population": internal["training_dev_sentences"],
        "internal_fold_results": internal["folds"],
        "new_external": fresh,
        "whole_training_sentence_copying_in_composition": False,
        "independent_blind_semantic_adjudication": False,
        "verified_physical_manuscript_witness_independence": False,
        "image_conditioned_hieratic_reading": False,
        "scientifically_validated_model_experiments_added": 0,
        "capability_points": 0.0,
    }
    report["report_sha256"] = sha256(_canonical(report)).hexdigest()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "internal", "external"))
    opts = parser.parse_args(argv)
    try:
        corpus = contextual.load_corpus()
        if opts.action == "verify":
            audit = load_archive(corpus)
            output = {"original_sha1": audit["original_sha1"],
                      "derived_sha1": audit["derived_git_blob_sha1"],
                      "new_text_ids": len(audit["text_ids"]),
                      "new_sentences": len(audit["rows"]),
                      "license": "CC-BY-SA-4.0", "rights_scope": "published text only"}
        elif opts.action == "internal":
            output = evaluate_internal(corpus)
        else:
            output = evaluate_external(corpus)
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (TranslationError, OSError, ValueError) as exc:
        print(f"W10 EXTERNAL HOLDOUT REFUSED: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
