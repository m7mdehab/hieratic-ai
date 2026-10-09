"""W11 frozen training-data expansion experiment (publisher-text diagnostic only)."""
from __future__ import annotations
import argparse
import json
from hashlib import sha1, sha256
from pathlib import Path
from typing import Any
from ling.translation import contextual
from ling.translation.compositional import ConstrainedComposer
from ling.translation.w10_evaluation import compare
from tools.translation_layer import TranslationError, _canonical

ROOT = contextual.ROOT
DONOR_PATH = "ling/translation/data/w11_archive_training_excluding_w10.json"
TEST_PATH = "ling/translation/data/w11_biographies_32groups_ccby_sa.json"
DONOR_BLOB = "1354bbfd832680953bec25fb5742502599763bc1"
BIOGRAPHY_BLOB = "6f26021ee4243e87657ff8afd59847f126d6ca65"
UPSTREAM_ARCHIVE_BLOB = "014cccf04235d9e093fca24ed48c62630d235852"
OLD_ARCHIVE_TEST_BLOB = "d3d7b57aef7bd10a48df6b1be340be8ff5b36e32"
PREDECLARED_GROUPS = 32
COHORT_SEED = "hieratic-ai-ling003-w11-biographies-v1:"
COHORT_CUTOFF_SHA256 = "37bde0beda59cec1a6b53e513ab5a5e77f75a8866728136f5d9ae52c7706ae26"


def blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _pinned(root: Path, path: str, expected: str, limit: int) -> dict[str, Any]:
    p = root / path
    if p.is_symlink() or not p.is_file():
        raise TranslationError(f"Pinned W11 source missing or linked: {path}")
    raw = p.read_bytes()
    if not raw or len(raw) > limit or blob(raw) != expected:
        raise TranslationError(f"W11 source Git blob mismatch: {path}")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise TranslationError("W11 source JSON object required")
    return value


def build_locked_rows(root: Path = ROOT) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    corpus = contextual.load_corpus(root=root)
    original = [x for name in contextual.DEV_CORPORA for x in corpus["groups"][name] if x["german"]]
    if len(original) != 904:
        raise TranslationError("Original W9 training census drift")
    exposed = _pinned(root, "ling/translation/data/w10_archive_32groups_ccby_sa.json",
                      OLD_ARCHIVE_TEST_BLOB, 400_000)
    exposed_ids = {x["text"] for x in exposed.values()}
    donor = _pinned(root, DONOR_PATH, DONOR_BLOB, 4_000_000)
    heldout = _pinned(root, TEST_PATH, "W11_BIOGRAPHY_BLOB_TO_BE_PINNED", 600_000)
    old_ids = {x["text_id"] for group in corpus["groups"].values() for x in group}
    archive_training = []
    for sid, row in sorted(donor.items()):
        if not isinstance(row, dict) or set(row) != {"text", "owner", "token", "sentence_translation"}:
            raise TranslationError("W11 archive training row schema drift")
        text_id, tokens, german = row["text"], row["token"], row["sentence_translation"]
        if text_id in exposed_ids or text_id in old_ids:
            raise TranslationError("W10 exposed source group or W9 group in W11 donor training")
        if not isinstance(tokens, list) or not tokens or not german.strip():
            raise TranslationError("Unusable W11 archival training sample")
        if not all(isinstance(t, dict) and set(t) == {"written_form", "cotext_translation"}
                   and isinstance(t["written_form"], str) and t["written_form"]
                   and (t["cotext_translation"] is None or isinstance(t["cotext_translation"], str))
                   for t in tokens):
            raise TranslationError("Unusable W11 original source or German cotext fields")
        archive_training.append({"sentence_id": sid, "text_id": text_id, "corpus": "bbawarchive",
                                 "forms": tuple(t["written_form"] for t in tokens),
                                 "glosses": tuple(t["cotext_translation"] for t in tokens),
                                 "german": german.strip()})
    biography = []
    for sid, row in sorted(heldout.items()):
        if not isinstance(row, dict) or set(row) != {"text", "token", "sentence_translation"}:
            raise TranslationError("W11 unseen biography evaluation row schema drift")
        toks = row["token"]
        if not isinstance(toks, list) or not toks:
            raise TranslationError("No original Egyptian tokens in W11 external item")
        if any(not isinstance(t, dict) or set(t) != {"written_form"}
               or not isinstance(t["written_form"], str) or not t["written_form"] for t in toks):
            raise TranslationError("W11 evaluation tokens include leaked target labels")
        biography.append({"sentence_id": sid, "text_id": row["text"],
                          "corpus": "bbawhistbiospzt",
                          "forms": tuple(t["written_form"] for t in toks),
                          "glosses": tuple(None for _ in toks),
                          "german": row["sentence_translation"].strip()})
    donor_ids = {x["text_id"] for x in archive_training}
    new_ids = {x["text_id"] for x in biography}
    if (len(new_ids) != PREDECLARED_GROUPS
            or old_ids & new_ids or donor_ids & new_ids
            or exposed_ids & new_ids or donor_ids & exposed_ids):
        raise TranslationError("Original W10 or W11 source group contamination")
    if len(biography) != 180 or sum(bool(x["german"]) for x in biography) != 178:
        raise TranslationError("W11 external census drift")
    if max(sha256((COHORT_SEED + x).encode("utf-8")).hexdigest() for x in new_ids) != COHORT_CUTOFF_SHA256:
        raise TranslationError("Source-ID SHA cohort changed")
    return original, archive_training, {
        "biography": biography, "old_ids": len(old_ids),
        "quarantined_w10_groups": len(exposed_ids),
        "new_groups": len(new_ids), "archive_donor_groups": len(donor_ids),
    }


def method_score(test: list[dict[str, Any]], train: list[dict[str, Any]], *,
                 method: str) -> dict[str, Any]:
    if {x["text_id"] for x in test} & {x["text_id"] for x in train}:
        raise TranslationError("W11 target text group leaked into training")
    if method == "composition":
        predictor = ConstrainedComposer(train).predict
    elif method == "gloss":
        model = contextual.TranslationMemory(train)
        predictor = lambda row: {"prediction": model.gloss(row["forms"])["text"],
                                 "mode": "TRAIN_ONLY_GLOSS_FALLBACK"}
    elif method == "memory":
        predictor = lambda row: contextual.TranslationMemory(train).predict(row, 0.0)
    else:
        raise TranslationError("Unknown frozen W11 method")
    # Train the memory exactly once; avoid per-target reconstruction.
    if method == "memory":
        model = contextual.TranslationMemory(train)
        predictor = lambda row: model.predict(row, 0.0)
    composed = [(row, predictor(row)) for row in test]
    from ling.translation.contextual import _accumulate
    metrics = _accumulate(composed)
    unknowns = sum(out.get("unknown_abstentions", 0) for _, out in composed)
    return {"metrics": metrics, "unknown_abstentions": unknowns,
            "swaps": sum(len(out.get("learned_adjacent_swaps", [])) for _, out in composed),
            "exact_nonidentical_german_collision": sum(bool(out.get("accidental_exact_nonidentical_train_german")) for _, out in composed)}


def evaluate(root: Path = ROOT) -> dict[str, Any]:
    baseline, donor, provenance = build_locked_rows(root)
    test = provenance["biography"]
    combined = baseline + donor
    results = {}
    for name, method, train in (
        ("original_gloss", "gloss", baseline),
        ("original_composition", "composition", baseline),
        ("expanded_gloss", "gloss", combined),
        ("expanded_composition", "composition", combined),
        ("expanded_memory_unsafe", "memory", combined),
    ):
        results[name] = method_score(test, train, method=method)
    result = {
        "experiment": "ling003-w11-frozen-training-expansion-new-biography-domain/1.0.0",
        "preregistration": "W11_PREREG_SCALED_TRAIN_BIOGRAPHY_HOLDOUT.md",
        "original_publisher_revision": contextual.UPSTREAM_COMMIT,
        "rights_class": "CC-BY-SA-4.0_OPEN-SA_TEXT_ONLY",
        "donor_original_git_blob": UPSTREAM_ARCHIVE_BLOB,
        "heldout_original_git_blob": BIOGRAPHY_BLOB,
        "donor_derived_git_blob": DONOR_BLOB,
        "external_selection_seed": COHORT_SEED,
        "prior_w10_archive_test_group_count_excluded": provenance["quarantined_w10_groups"],
        "original_training_rows": len(baseline),
        "additional_archive_training_rows": len(donor),
        "expanded_training_rows": len(combined),
        "additional_archive_training_text_groups": provenance["archive_donor_groups"],
        "new_biography_external_group_count": provenance["new_groups"],
        "new_biography_external_sentence_count": len(test),
        "new_biography_translated_sentence_count": sum(bool(x["german"]) for x in test),
        "new_biography_source_tokens": sum(len(x["forms"]) for x in test),
        "results": results,
        "test_is_now_exposed_after_first_use": True,
        "never_tuned_on_exposed_w10_tuebingen_or_w11_biographies": True,
        "not_licensed_original_hieratic_images": True,
        "not_physically_verified_distinct_witnesses": True,
        "no_expert_blind_semantic_adequacy": True,
        "scientific_model_achievement_accepted": False,
        "capability_points": 0.0,
    }
    result["report_sha256"] = sha256(_canonical(result)).hexdigest()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("verify", "evaluate"))
    args = parser.parse_args(argv)
    try:
        result = evaluate() if args.action == "evaluate" else None
        if result is None:
            original, training, cohort = build_locked_rows()
            result = {"original_train": len(original), "expanded_donor": len(training),
                      "new_external_groups": cohort["new_groups"],
                      "new_external_sentences": len(cohort["biography"]),
                      "rights": "CC-BY-SA-4.0; open scholarly text only"}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (TranslationError, OSError, ValueError, KeyError, TypeError) as exc:
        print("W11 FROZEN EVALUATION REFUSED: " + str(exc), file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
