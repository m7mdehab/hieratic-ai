"""W12B preregistered Egyptian source-token POS/morphology diagnostics.

Real licensed AES editorial grammar labels only. The hidden target label file
is opened **after** predictions are generated for the immutable 24 source groups.
Do not reuse previously revealed Tuebingen/Archive/Biographies/Temple tests.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any

from ling.translation.grammar_evidence import GrammarEvidence, MORPH_FIELDS, VERSION
from ling.translation import contextual, w10_evaluation, w11_evaluation
from tools.translation_layer import TranslationError, _canonical

ROOT = contextual.ROOT
REL = Path("ling/translation/data")
LOCKS = {
    "w12_grammar_train_publisher_ccby_sa.json": "a23c5df36707044b4071b554d4c1092b127728f4",
    "w12b_amarna_inputs.json": "6ed7dd37cce3a21ea2e681162d217e3c7dca0f37",
    "w12b_amarna_reference_annotations.json": "784aeffaf033275b064a0dfaa76917109c2a0693",
    "w12b_amarna_source_universe.json": "a966eb85cff4564107ab33a97062ab8b76c8c3cb",
    "w12b_amarna_rights_manifest.json": "7b49efc5463b95d094b4d9ac002e8712fdb40c4d",
}
SOURCE_GIT_BLOB = "5e512681dc0d1ac7177a62531582b3473a0a11f2"
SEED = "hieratic-ai-ling003-w12b-amarna-grammar-v1:"
EXPECTED = {"train_sentences": 3925, "new_source_groups": 24,
            "new_sentences": 163, "egyptian_tokens": 1691, "publisher_pos_tokens": 1649}
CLASSIFICATION = "SOURCE_HELDOUT_AES_EDITORIAL_POS_MORPHOLOGY_DIAGNOSTIC_NOT_HIERATIC_GOLD"


def _blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def pinned(root: Path, filename: str) -> dict[str, Any]:
    path = root / REL / filename
    if path.is_symlink() or not path.is_file():
        raise TranslationError("Missing/linked W12B external publisher resource: " + filename)
    size = path.stat().st_size
    if size < 1 or size > 4_000_000:
        raise TranslationError("W12B resource outside audited size bounds: " + filename)
    raw = path.read_bytes()
    if len(raw) != size or _blob(raw) != LOCKS[filename]:
        raise TranslationError("W12B original-derived Git blob identity mismatch: " + filename)
    try:
        val = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise TranslationError("W12B publisher JSON decode failure") from exc
    if not isinstance(val, dict):
        raise TranslationError("W12B source must contain JSON object")
    return val


def load(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Preserve target separation and never return the test reference to training."""
    train = pinned(root, "w12_grammar_train_publisher_ccby_sa.json")
    inputs = pinned(root, "w12b_amarna_inputs.json")
    universe = pinned(root, "w12b_amarna_source_universe.json")
    rights = pinned(root, "w12b_amarna_rights_manifest.json")
    if len(train) != EXPECTED["train_sentences"] or len(inputs) != EXPECTED["new_sentences"]:
        raise TranslationError("W12B original publisher train/test population drift")
    if universe.get("original_git_blob") != SOURCE_GIT_BLOB or universe.get("original_bytes") != 14683204:
        raise TranslationError("Amarna original source identity mismatch")
    original = universe.get("all_source_ids_sorted")
    if (not isinstance(original, list) or len(original) != 399
            or original != sorted(set(original))
            or any(not isinstance(x, str) or not x for x in original)):
        raise TranslationError("Original Amarna full source-ID universe drift")
    expected = sorted(original, key=lambda t: (
        sha256((SEED + t).encode("utf-8")).hexdigest(), t
    ))[:EXPECTED["new_source_groups"]]
    if (universe.get("selected_ids_ranked") != expected
            or universe.get("selection_salt") != SEED
            or universe.get("selected_ids_sorted") != sorted(expected)):
        raise TranslationError("Selected Amarna text IDs violate original preregistered hash rank")
    original_train_ids = {x.get("text") for x in train.values()}
    target_ids = set()
    count = 0
    for sid, item in inputs.items():
        if not isinstance(sid, str) or set(item) != {"text", "forms"}:
            raise TranslationError("Amarna prediction input contains a hidden target label or unsupported field")
        forms = item["forms"]
        if not isinstance(forms, list) or not forms or any(
            not isinstance(x, str) or not x or len(x) > 512 for x in forms
        ):
            raise TranslationError("Amarna input original Egyptian token forms malformed")
        target_ids.add(item["text"])
        count += len(forms)
    if len(target_ids) != 24 or sorted(target_ids) != sorted(expected) or count != EXPECTED["egyptian_tokens"]:
        raise TranslationError("W12B original source-ID cohort or token census drift")
    if target_ids.intersection(original_train_ids):
        raise TranslationError("W12B target text identity overlaps training source")
    for row in train.values():
        if not isinstance(row, dict) or set(row) != {"text", "owner", "tokens"}:
            raise TranslationError("W12B training source contaminated with target labels")
    # Source rights and item identities are explicit, not inferred from public availability.
    if (rights.get("license") != "CC-BY-SA-4.0"
            or rights.get("source_git_blob") != SOURCE_GIT_BLOB
            or not isinstance(rights.get("rights"), list)
            or len(rights["rights"]) != len(inputs)
            or {r["source_sentence_id"] for r in rights["rights"]} != set(inputs)):
        raise TranslationError("W12B publisher rights or item attribution manifest changed")
    for r in rights["rights"]:
        if (r.get("rights_class") != "OPEN-SA" or r.get("train_admission") is not False
                or r.get("production_admission") is not False
                or r.get("test_only") is not True
                or not r.get("original_editor")
                or r.get("original_manuscript_image_matched") is not False):
            raise TranslationError("W12B evaluation item missing explicit nonadmission/rights")
    return train, inputs, {"universe": universe, "rights": rights}


def score(predictions: dict[str, Any], targets: dict[str, Any],
          original_inputs: dict[str, Any]) -> dict[str, Any]:
    """Read publisher gold only for evaluation, once every prediction is fixed."""
    if set(predictions) != set(targets) or set(targets) != set(original_inputs):
        raise TranslationError("W12B test gold/prediction row identity mismatch")
    fields = {f: {"labels": 0, "top1": 0, "candidate_recall": 0,
                  "prediction_coverage": 0} for f in MORPH_FIELDS}
    totals = {"all_sentences": len(original_inputs), "original_egyptian_tokens": 0,
              "publisher_pos_labels": 0, "publisher_pos_missing": 0,
              "baseline_correct": 0, "context_correct": 0,
              "baseline_covered": 0, "context_covered": 0,
              "pos_alternative_contains_gold": 0, "context_source_supported": 0,
              "pos_prediction_changed_by_context": 0,
              "adjacent_pairs_with_train_support": 0,
              "pos_ambiguity_tokens": 0}
    groups = defaultdict(lambda: [0, 0, 0])
    for sid in sorted(original_inputs):
        inputs, gold, prediction = original_inputs[sid], targets[sid], predictions[sid]
        forms = inputs["forms"]
        if not isinstance(gold, dict) or set(gold) != {"pos", "features"}:
            raise TranslationError("W12B gold has unexpected fields")
        if (not isinstance(gold["pos"], list) or len(gold["pos"]) != len(forms)
                or not isinstance(gold["features"], list)
                or len(gold["features"]) != len(forms)):
            raise TranslationError("W12B original target publisher annotation length mismatch")
        units = prediction["units"]
        if len(units) != len(forms):
            raise TranslationError("W12B predicted token count mismatch")
        totals["original_egyptian_tokens"] += len(forms)
        totals["adjacent_pairs_with_train_support"] += sum(
            x["train_texts_with_same_adjacent_pos"] > 0
            for x in prediction["adjacent_pos_evidence"]
        )
        for i, (unit, pos, morph) in enumerate(zip(units, gold["pos"], gold["features"])):
            if unit["source_slot"] != i or unit["written_form"] != forms[i]:
                raise TranslationError("W12B prediction source slot mismatch")
            if pos is None:
                totals["publisher_pos_missing"] += 1
            elif not isinstance(pos, str) or not pos:
                raise TranslationError("W12B invalid publisher POS label")
            else:
                totals["publisher_pos_labels"] += 1
                groups[inputs["text"]][0] += 1
                totals["baseline_correct"] += int(unit["baseline_pos"] == pos)
                totals["context_correct"] += int(unit["context_pos"] == pos)
                groups[inputs["text"]][1] += int(unit["baseline_pos"] == pos)
                groups[inputs["text"]][2] += int(unit["context_pos"] == pos)
                totals["baseline_covered"] += int(unit["baseline_pos"] is not None)
                totals["context_covered"] += int(unit["context_pos"] is not None)
                totals["pos_alternative_contains_gold"] += int(
                    pos in {x["pos"] for x in unit["alternatives"]})
            totals["context_source_supported"] += int(unit["pos_decision"] in {
                "TWO_SIDED", "LEFT", "RIGHT"})
            totals["pos_prediction_changed_by_context"] += int(
                unit["baseline_pos"] != unit["context_pos"])
            totals["pos_ambiguity_tokens"] += int(len(unit["alternatives"]) > 1)
            if not isinstance(morph, dict) or any(k not in MORPH_FIELDS for k in morph):
                raise TranslationError("W12B target morphology fields invalid")
            for name, value in morph.items():
                if not isinstance(value, str) or not value:
                    raise TranslationError("W12B malformed publisher morphology label")
                stats = fields[name]
                stats["labels"] += 1
                proposed = unit["morphological_candidates"][name]
                stats["prediction_coverage"] += int(bool(proposed))
                stats["top1"] += int(bool(proposed) and proposed[0]["value"] == value)
                stats["candidate_recall"] += int(value in {x["value"] for x in proposed})
    if totals["original_egyptian_tokens"] != 1691 or totals["publisher_pos_labels"] != 1649:
        raise TranslationError("W12B target population labels mismatch")
    den = totals["publisher_pos_labels"]
    results = {**totals,
        "baseline_micro_pos_accuracy_all_labels": round(totals["baseline_correct"] / den, 8),
        "context_micro_pos_accuracy_all_labels": round(totals["context_correct"] / den, 8),
        "baseline_pos_coverage_all_labels": round(totals["baseline_covered"] / den, 8),
        "context_pos_coverage_all_labels": round(totals["context_covered"] / den, 8),
        "pos_candidate_recall_all_labels": round(totals["pos_alternative_contains_gold"] / den, 8),
        "baseline_conditional_accuracy_covered": (
            round(totals["baseline_correct"] / totals["baseline_covered"], 8)
            if totals["baseline_covered"] else None),
        "context_conditional_accuracy_covered": (
            round(totals["context_correct"] / totals["context_covered"], 8)
            if totals["context_covered"] else None),
        "macro_source_group_baseline_pos_accuracy": (
            round(sum(v[1] / v[0] for v in groups.values()) / len(groups), 8) if groups else None),
        "macro_source_group_context_pos_accuracy": (
            round(sum(v[2] / v[0] for v in groups.values()) / len(groups), 8) if groups else None),
        "groups_with_publisher_pos": len(groups),
    }
    return {"pos": results, "morphology_by_source_field": fields,
            "certified_subject_object_agent_roles": False,
            "original_manuscript_heldout_gold": False}


def evaluate(root: Path = ROOT) -> dict[str, Any]:
    train, inputs, provenance = load(root)
    model = GrammarEvidence(train)
    # Freeze the entire prediction batch BEFORE loading test reference bytes.
    results = {sid: model.predict(entry["forms"], entry["text"])
               for sid, entry in sorted(inputs.items())}
    targets = pinned(root, "w12b_amarna_reference_annotations.json")
    metrics = score(results, targets, inputs)
    report = {
        "experiment": VERSION, "classification": CLASSIFICATION,
        "source_revision": "35276d2527cca1a055e31ed5f6683e777717170f",
        "source_license": "CC-BY-SA-4.0",
        "source_git_blob": SOURCE_GIT_BLOB,
        "first_blocked_temple_cohort_exposed_not_used": True,
        "new_amarna_external_cohort_now_exposed_after_this_evaluation": True,
        "train_sentences": len(train),
        "train_source_texts": len(model.train_text_ids),
        "new_publisher_test_groups": len(provenance["universe"]["selected_ids_ranked"]),
        "source_group_overlap": False,
        "model_use_target_german_or_publisher_pos_during_inference": False,
        "raw_publisher_images_evaluated": 0,
        "fluently_translated_sentences_evaluated": 0,
        "semantic_roles_trained_or_evaluated": 0,
        "trained_neural_models": 0,
        "scientific_capability_points": 0.0,
        "metrics": metrics,
    }
    report["report_sha256"] = sha256(_canonical(report)).hexdigest()
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("verify", "evaluate"))
    opts = p.parse_args(argv)
    try:
        if opts.action == "verify":
            train, items, _ = load()
            report = {"original_git_blob": SOURCE_GIT_BLOB,
                      "train_sentences": len(train), "new_test_sentences": len(items),
                      "license": "CC-BY-SA-4.0", "admitted_production": False}
        else:
            report = evaluate()
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (TranslationError, OSError, ValueError) as exc:
        print("W12B GRAMMAR REFUSED: " + str(exc), file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
