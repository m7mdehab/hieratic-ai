"""W11: frozen train-side expansion, genuinely new AES biographies text-only test.

All inputs are publisher CC BY-SA 4.0 text, never original Hieratic pixels.
Model methods are unchanged W10 composer and W9 frozen text memory.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha1, sha256
import argparse
import json
from pathlib import Path
from typing import Any

from ling.translation import contextual, w10_evaluation
from ling.translation.compositional import ConstrainedComposer
from tools.translation_layer import TranslationError, _canonical

ROOT = contextual.ROOT
DONOR = Path("ling/translation/data/w11_archive_training_excluding_w10.json")
BIOGRAPHIES = Path("ling/translation/data/w11_biography_external_32groups_ccby_sa.json")
SOURCE_ARCHIVE_BLOB = "014cccf04235d9e093fca24ed48c62630d235852"
SOURCE_BIOGRAPHY_BLOB = "6f26021ee4243e87657ff8afd59847f126d6ca65"
DONOR_BLOB = "1354bbfd832680953bec25fb5742502599763bc1"
BIOGRAPHY_BLOB = "7e5654b5d8194c3deb764cf37a8e2bce2c624855"
BIOGRAPHY_HASH_SALT = "hieratic-ai-ling003-w11-biographies-v1:"
BIOGRAPHY_HASH_CUTOFF = "37bde0beda59cec1a6b53e513ab5a5e77f75a8866728136f5d9ae52c7706ae26"
DONOR_EXPECTED_SENTENCES = 3021
DONOR_EXPECTED_TEXT_GROUPS = 1130
BIOGRAPHY_EXPECTED_SENTENCES = 180
BIOGRAPHY_EXPECTED_TRANSLATED = 178
BIOGRAPHY_EXPECTED_GROUPS = 32
CLASSIFICATION = "NEW_PUBLISHED_AES_BIOGRAPHY_TEXT_ONLY_SOURCE_GROUP_DIAGNOSTIC"
VERSION = "ling003-w11-expanded-archive-v1"


def git_blob_sha1(content: bytes) -> str:
    return sha1(b"blob " + str(len(content)).encode("ascii") + b"\\0" + content).hexdigest()


def pinned_json(root: Path, path: Path, digest: str, max_bytes: int) -> dict[str, Any]:
    file = root / path
    if file.is_symlink() or not file.is_file():
        raise TranslationError("W11 source absent or linked: " + str(path))
    size = file.stat().st_size
    if not 1 <= size <= max_bytes:
        raise TranslationError("W11 source size outside locked bound")
    raw = file.read_bytes()
    if len(raw) != size or git_blob_sha1(raw) != digest:
        raise TranslationError("W11 derived source Git blob identity mismatch: " + str(path))
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise TranslationError("W11 source JSON malformed") from exc
    if not isinstance(data, dict):
        raise TranslationError("W11 source JSON expected object")
    return data


def load(corpus: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    """Prove every donor and heldout source identity is disjoint; no silent filters."""
    archived = pinned_json(root, DONOR, DONOR_BLOB, 3_000_000)
    biography = pinned_json(root, BIOGRAPHIES, BIOGRAPHY_BLOB, 400_000)
    prior_ids = {row["text_id"] for group in corpus["groups"].values() for row in group}
    earlier = w10_evaluation.load_archive(corpus, root=root)
    former_ids = set(earlier["text_ids"])
    donor_ids: set[str] = set()
    train_extra = []
    authors: Counter[str] = Counter()

    if len(archived) != DONOR_EXPECTED_SENTENCES:
        raise TranslationError("W11 donor sentence census mismatch")
    for sid, rec in sorted(archived.items()):
        if not isinstance(sid, str) or not isinstance(rec, dict) or set(rec) != {
            "text", "owner", "token", "sentence_translation"
        }:
            raise TranslationError("W11 donor has unrecognized or missing fields")
        text_id, owner = rec["text"], rec["owner"]
        if (not isinstance(text_id, str) or not text_id
                or not isinstance(owner, str) or not owner.strip()):
            raise TranslationError("W11 donor lacks original text or editor identity")
        if text_id in prior_ids or text_id in former_ids:
            raise TranslationError("W11 donor would train on old evaluation material")
        token, german = rec["token"], rec["sentence_translation"]
        if not isinstance(token, list) or not token or not isinstance(german, str) or not german.strip():
            raise TranslationError("W11 donor missing required published labels")
        forms, glosses = [], []
        for tok in token:
            if not isinstance(tok, dict) or set(tok) != {"written_form", "cotext_translation"}:
                raise TranslationError("W11 donor token source labels malformed")
            form, gloss = tok["written_form"], tok["cotext_translation"]
            if (not isinstance(form, str) or not form or len(form) > 512
                    or (gloss is not None and (not isinstance(gloss, str) or len(gloss) > 512))):
                raise TranslationError("W11 donor input invalid")
            forms.append(form)
            glosses.append(gloss if gloss else None)
        authors[owner] += 1
        donor_ids.add(text_id)
        train_extra.append({
            "sentence_id": sid, "text_id": text_id, "corpus": "bbawarchive_non_w10",
            "forms": tuple(forms), "glosses": tuple(glosses), "german": german.strip(),
        })
    if len(donor_ids) != DONOR_EXPECTED_TEXT_GROUPS:
        raise TranslationError("W11 donor group count mismatch")
    if dict(authors) != {"Stephan Seidlmayer": 550, "Stefan Grunert": 2463, "Ingelore Hafemann": 8}:
        raise TranslationError("W11 editor attribution or donor census drift")

    if len(biography) != BIOGRAPHY_EXPECTED_SENTENCES:
        raise TranslationError("W11 test sentence census mismatch")
    test = []
    target_ids: set[str] = set()
    for sid, rec in sorted(biography.items()):
        if not isinstance(sid, str) or not isinstance(rec, dict) or set(rec) != {
            "text", "token", "sentence_translation"
        }:
            raise TranslationError("W11 target contains unexpected train-only fields")
        tid, original_tokens, german = rec["text"], rec["token"], rec["sentence_translation"]
        if (not isinstance(tid, str) or not tid
                or not isinstance(original_tokens, list) or not original_tokens
                or not isinstance(german, str)):
            raise TranslationError("W11 target editorial record malformed")
        if tid in donor_ids or tid in prior_ids or tid in former_ids:
            raise TranslationError("W11 target overlaps any prior source or donor group")
        forms = []
        for token in original_tokens:
            if not isinstance(token, dict) or set(token) != {"written_form"}:
                raise TranslationError("W11 target token may not contain publisher gold labels")
            form = token["written_form"]
            if not isinstance(form, str) or not form or len(form) > 512:
                raise TranslationError("W11 target Egyptian form invalid")
            forms.append(form)
        test.append({
            "sentence_id": sid, "text_id": tid, "corpus": "bbawhistbiospzt",
            "forms": tuple(forms), "glosses": tuple(None for _ in forms),
            "german": german.strip(),
        })
        target_ids.add(tid)
    if (len(target_ids) != BIOGRAPHY_EXPECTED_GROUPS
            or sum(bool(v["german"]) for v in test) != BIOGRAPHY_EXPECTED_TRANSLATED):
        raise TranslationError("W11 frozen target population drift")
    rank_digests = {
        sha256((BIOGRAPHY_HASH_SALT + name).encode("utf-8")).hexdigest()
        for name in target_ids
    }
    if len(rank_digests) != BIOGRAPHY_EXPECTED_GROUPS or max(rank_digests) != BIOGRAPHY_HASH_CUTOFF:
        raise TranslationError("W11 biographies preregistered source-group cutoff mismatch")
    return {
        "donor": train_extra, "test": test, "donor_text_ids": sorted(donor_ids),
        "test_text_ids": sorted(target_ids),
        "prior_heldout_text_ids": sorted(former_ids),
        "donor_owners": dict(sorted(authors.items())),
    }


def _measure(pairs: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    return contextual._accumulate(pairs)


def evaluate(corpus: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    """Frozen five-way comparison; references are read solely by _accumulate."""
    bundle = load(corpus, root=root)
    old_train = [row for name in contextual.DEV_CORPORA
                 for row in corpus["groups"][name] if row["german"]]
    if len(old_train) != 904:
        raise TranslationError("W9 old train population changed")
    augmented = old_train + bundle["donor"]
    old_memory = contextual.TranslationMemory(old_train)
    new_memory = contextual.TranslationMemory(augmented)
    old_composer = ConstrainedComposer(old_train)
    new_composer = ConstrainedComposer(augmented)
    score_pairs: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {
        "w9_904_gloss": [],
        "w10_904_composer": [],
        "w11_expanded_gloss": [],
        "w11_expanded_composer": [],
        "w11_expanded_memory_threshold_0": [],
    }
    coverage = Counter()
    for row in bundle["test"]:
        plain_old = old_memory.gloss(row["forms"])
        plain_new = new_memory.gloss(row["forms"])
        old = old_composer.predict(row)
        new = new_composer.predict(row)
        recalled = new_memory.predict(row, 0.0)
        coverage["source_tokens"] += len(row["forms"])
        coverage["old_gloss_unknown"] += plain_old["abstentions"]
        coverage["new_gloss_unknown"] += plain_new["abstentions"]
        coverage["old_composer_unknown"] += old["unknown_abstentions"]
        coverage["new_composer_unknown"] += new["unknown_abstentions"]
        coverage["old_composer_local_swaps"] += len(old["learned_adjacent_swaps"])
        coverage["new_composer_local_swaps"] += len(new["learned_adjacent_swaps"])
        coverage["new_composer_context_units"] += new["context_selected_units"]
        coverage["new_composer_exact_nonidentical_german_matches"] += int(
            new["accidental_exact_nonidentical_train_german"])
        score_pairs["w9_904_gloss"].append((row, {
            "prediction": plain_old["text"], "mode": plain_old["mode"]}))
        score_pairs["w10_904_composer"].append((row, old))
        score_pairs["w11_expanded_gloss"].append((row, {
            "prediction": plain_new["text"], "mode": plain_new["mode"]}))
        score_pairs["w11_expanded_composer"].append((row, new))
        score_pairs["w11_expanded_memory_threshold_0"].append((row, recalled))
    metrics = {name: _measure(pairs) for name, pairs in score_pairs.items()}
    return {
        "experiment": VERSION,
        "classification": CLASSIFICATION,
        "publisher": "Simon D. Schweitzer / AES and AED editors",
        "license": "CC-BY-SA-4.0_OPEN_SA_EDITORIAL_TEXT_ONLY",
        "source_revision": contextual.UPSTREAM_COMMIT,
        "original_training_archive_git_blob": SOURCE_ARCHIVE_BLOB,
        "original_biographies_git_blob": SOURCE_BIOGRAPHY_BLOB,
        "derived_donor_git_blob": DONOR_BLOB,
        "derived_external_git_blob": BIOGRAPHY_BLOB,
        "training": {
            "old_w9_translated_sentences": len(old_train),
            "additional_archive_translated_sentences": len(bundle["donor"]),
            "total_training_translated_sentences": len(augmented),
            "additional_archive_original_texts": len(bundle["donor_text_ids"]),
            "per_editor_donor_sentence_counts": bundle["donor_owners"],
            "w10_quarantined_group_count": len(bundle["prior_heldout_text_ids"]),
            "previous_tuebingen_reserved_test_in_training": False,
            "w10_archive_external_test_in_training": False,
            "w11_biographies_external_test_in_training": False,
        },
        "new_external": {
            "total_original_sentences": len(bundle["test"]),
            "publisher_german_references": sum(bool(r["german"]) for r in bundle["test"]),
            "original_source_text_groups": len(bundle["test_text_ids"]),
            "metrics": metrics,
            "lexical_and_composition_controls": dict(sorted(coverage.items())),
        },
        "frozen_methods": {
            "original_w10_compositional_model_unchanged": True,
            "old_w9_similarity_threshold": 0.0,
            "context_train_support": 2,
            "reorder_train_support": 2,
            "reorder_strictly_more_than_two_times_forward": True,
            "unknown_source_token_abstentions": True,
        },
        "original_ling003_capability_points": 0.0,
        "science_is_full_semantic_translation": False,
        "not_original_hieratic_pixels": True,
        "independently_verified_distinct_physical_manuscripts": False,
        "independent_expert_gold": False,
        "results_do_not_justify_model_selection_on_this_exposed_test": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "evaluate"))
    opts = parser.parse_args(argv)
    try:
        corpus = contextual.load_corpus()
        if opts.action == "verify":
            source = load(corpus)
            report = {"donor_sentences": len(source["donor"]),
                      "donor_source_text_groups": len(source["donor_text_ids"]),
                      "external_sentences": len(source["test"]),
                      "external_text_groups": len(source["test_text_ids"]),
                      "licensed": "CC-BY-SA-4.0"}
        else:
            report = evaluate(corpus)
        report["report_sha256"] = sha256(_canonical(report)).hexdigest()
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (TranslationError, ValueError, OSError) as exc:
        print(f"W11 REFUSED: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
