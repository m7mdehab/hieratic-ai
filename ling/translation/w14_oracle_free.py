"""W14 original TRAIN-only Egyptian-PC predicted-POS -> dependency diagnostic.

This file NEVER retrieves original official DEV/TEST, never claims Hieratic image
reading or fluent translation. The Pepi group comes from W13's historically
exposed TRAIN partition: a retrospective, not independently blind holdout.
Copyright: UD Egyptian-PC / University of Jaen, CC BY-SA 4.0.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from ling.translation.w13_egyptian_pc import FixedOraclePosSyntax, has_cycle, _gitblob
from tools.translation_layer import TranslationError, _canonical

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "ling/translation/data/w14_egyptian_pc_train_only_ccby_sa.json"
DERIVED_BLOB = "2b42a078e6ec4277a5ab7016d6f966c3545a7894"
ORIGINAL_TRAIN_BLOB = "ea262ee047943b81c0e0db8ff139ec7deb9b7b53"
ORIGINAL_TREE = "fca8538287cb69fd07b811eb55dcfd25584f3006"
TRAIN_GROUPS = frozenset({"Teti", "Neith", "Merenre"})
HELDOUT_GROUP = "Pepi"
VERSION = "w14-epc-train-only-nonoracle-syntax/1.0.0"


def _valid_sentence(sent: Any) -> None:
    if not isinstance(sent, dict) or set(sent) != {"id", "group", "rows"}:
        raise TranslationError("Invalid original publisher sentence fields")
    if not isinstance(sent["id"], str) or not sent["id"] or sent["group"] not in TRAIN_GROUPS | {HELDOUT_GROUP}:
        raise TranslationError("Missing or unregistered publisher sentence identity")
    rows = sent["rows"]
    if not isinstance(rows, list) or not rows:
        raise TranslationError("Empty publisher sentence")
    n = len(rows)
    heads = []
    for i, row in enumerate(rows, 1):
        if not isinstance(row, list) or len(row) != 4:
            raise TranslationError("Malformed original word label row")
        form, pos, head, rel = row
        if (not isinstance(form, str) or not form or not isinstance(pos, str) or not pos
                or type(head) is not int or head < 0 or head > n or head == i
                or not isinstance(rel, str) or not rel):
            raise TranslationError("Invalid original word token, UPOS or dependency")
        heads.append(head)
    if heads.count(0) != 1 or has_cycle(heads):
        raise TranslationError("Publisher original gold graph not single-rooted/acyclic")


def load_dataset(root: Path = ROOT) -> dict[str, Any]:
    path = root / DATA.relative_to(ROOT)
    if not path.is_file() or path.is_symlink():
        raise TranslationError("Pinned W14 original-TRAIN-derived material unavailable")
    raw = path.read_bytes()
    if len(raw) > 2_000_000 or _gitblob(raw) != DERIVED_BLOB:
        raise TranslationError("W14 source-derived Git blob identity mismatch")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise TranslationError("W14 source-derived manifest malformed")
    expected = {
        "schema_version": "1.0.0", "source": "UniversalDependencies/UD_Egyptian-PC",
        "source_tree": ORIGINAL_TREE, "original_train_git_blob": ORIGINAL_TRAIN_BLOB,
        "rights": "CC-BY-SA-4.0", "sentence_count": 1619, "token_count": 19486,
        "original_dev_labels_exposed_elsewhere": True, "official_test_accessed": False,
        "split": {"training_groups": ["Teti", "Neith", "Merenre"], "evaluation_groups": ["Pepi"]},
    }
    if any(obj.get(key) != value for key, value in expected.items()):
        raise TranslationError("Original source identity, rights or preregistered split drift")
    if "University of Jaén" not in obj.get("attribution", ""):
        raise TranslationError("Source attribution absent")
    sentences = obj.get("sentences")
    if not isinstance(sentences, list) or len(sentences) != 1619:
        raise TranslationError("Original sentence denominator changed")
    groups = Counter()
    ids = set()
    for sent in sentences:
        _valid_sentence(sent)
        if sent["id"] in ids:
            raise TranslationError("Duplicate original sentence ID")
        ids.add(sent["id"])
        groups[sent["group"]] += 1
    if groups != {"Teti": 744, "Neith": 40, "Merenre": 6, "Pepi": 829}:
        raise TranslationError("Publisher witness-group census drift")
    if sum(len(sent["rows"]) for sent in sentences) != 19486:
        raise TranslationError("Original token denominator changed")
    return obj


def _winner(counts: Counter[str]) -> str:
    if not counts:
        raise TranslationError("No train-only UPOS observations")
    return min(counts, key=lambda key: (-counts[key], key))


class TrainOnlyOracleFree:
    """Train only on accepted publisher group rows; infer from FORM strings alone."""

    def __init__(self, training: list[dict[str, Any]]):
        if not training or any(s["group"] not in TRAIN_GROUPS for s in training):
            raise TranslationError("Train/test group mixing refused")
        self.total_pos: Counter[str] = Counter()
        self.exact: dict[str, Counter[str]] = defaultdict(Counter)
        self.suffix: dict[int, dict[str, Counter[str]]] = {
            1: defaultdict(Counter), 2: defaultdict(Counter), 3: defaultdict(Counter)
        }
        stats: dict[str, Counter[str]] = {
            "head_relation_upos_direction_counts": Counter(),
            "dependent_upos_relation_counts": Counter(),
            "root_upos_counts": Counter(),
        }
        for sentence in training:
            rows = sentence["rows"]
            for i, (form, pos, head, rel) in enumerate(rows, 1):
                form_key = form.casefold()
                self.total_pos[pos] += 1
                self.exact[form_key][pos] += 1
                for k in (1, 2, 3):
                    if len(form_key) >= k:
                        self.suffix[k][form_key[-k:]][pos] += 1
                if head == 0:
                    stats["root_upos_counts"][pos] += 1
                    direction, head_pos = "root", "ROOT"
                else:
                    direction = "left" if head < i else "right"
                    head_pos = rows[head - 1][1]
                stats["head_relation_upos_direction_counts"][
                    "|".join((pos, head_pos, direction, rel))
                ] += 1
                stats["dependent_upos_relation_counts"]["|".join((pos, rel))] += 1
        self.majority = _winner(self.total_pos)
        self.syntax = FixedOraclePosSyntax(stats)

    def predict_pos(self, forms: list[str]) -> tuple[list[str], list[str]]:
        if (not isinstance(forms, list) or not forms
                or any(not isinstance(x, str) or not x for x in forms)):
            raise TranslationError("Inference accepts only nonempty raw FORM strings; no gold labels")
        tags, methods = [], []
        for form in forms:
            key = form.casefold()
            if key in self.exact:
                tag, method = _winner(self.exact[key]), "exact_train_form"
            else:
                matched = False
                for length, minimum in ((3, 3), (2, 5), (1, 8)):
                    if len(key) >= length:
                        counts = self.suffix[length].get(key[-length:], Counter())
                        if sum(counts.values()) >= minimum:
                            tag, method = _winner(counts), "suffix_" + str(length)
                            matched = True
                            break
                if not matched:
                    tag, method = self.majority, "global_train_majority"
            tags.append(tag)
            methods.append(method)
        return tags, methods

    def predict(self, forms: list[str]) -> dict[str, Any]:
        pos, status = self.predict_pos(forms)
        heads, rels = self.syntax.predict(pos)
        return {"UPOS": pos, "heads": heads, "relations": rels, "POS_evidence": status}

    def weak_baseline(self, forms: list[str]) -> dict[str, Any]:
        # Same frozen train majority class for every form; previous-token parser.
        pos = [self.majority] * len(forms)
        heads, rels = self.syntax.baseline(pos)
        return {"UPOS": pos, "heads": heads, "relations": rels}


def _score(pred: dict[str, Any], rows: list[list[Any]]) -> tuple[int, int]:
    if len(pred["heads"]) != len(rows) or len(pred["relations"]) != len(rows):
        raise TranslationError("Predicted token denominator drift")
    if pred["heads"].count(0) != 1 or has_cycle(pred["heads"]):
        raise TranslationError("Invalid predicted dependency tree")
    uas = sum(ph == row[2] for ph, row in zip(pred["heads"], rows))
    las = sum(ph == row[2] and pr == row[3]
              for ph, pr, row in zip(pred["heads"], pred["relations"], rows))
    return uas, las


def _pos_macro_f1(confusion: dict[str, Counter[str]]) -> float:
    tags = set(confusion)
    for row in confusion.values():
        tags.update(row)
    if not tags:
        return 0.
    f1 = []
    for tag in sorted(tags):
        tp = confusion.get(tag, Counter())[tag]
        support = sum(confusion.get(tag, Counter()).values())
        guessed = sum(row[tag] for row in confusion.values())
        f1.append(2 * tp / (support + guessed) if support + guessed else 0.)
    return sum(f1) / len(f1)


def evaluate(data: dict[str, Any]) -> dict[str, Any]:
    training = [s for s in data["sentences"] if s["group"] in TRAIN_GROUPS]
    targets = [s for s in data["sentences"] if s["group"] == HELDOUT_GROUP]
    if (len(training) != 790 or len(targets) != 829
            or sum(len(s["rows"]) for s in training) != 9157
            or sum(len(s["rows"]) for s in targets) != 10329):
        raise TranslationError("Frozen group split/denominator mismatch")
    train_ids = {s["id"] for s in training}
    if train_ids & {s["id"] for s in targets}:
        raise TranslationError("Cross-group sentence identity leakage")
    train_sequences = {tuple(row[0] for row in s["rows"]) for s in training}
    cross_group_exact_duplicates = sum(
        tuple(row[0] for row in s["rows"]) in train_sequences for s in targets
    )
    model = TrainOnlyOracleFree(training)
    # Predictions are explicitly produced before scoring source gold.
    predictions = []
    for sent in targets:
        forms = [row[0] for row in sent["rows"]]
        nonoracle = model.predict(forms)
        weak = model.weak_baseline(forms)
        # Clearly separated privileged upper-bound diagnosis, NEVER the headline.
        oracle_upos = [row[1] for row in sent["rows"]]
        oracle_heads, oracle_rels = model.syntax.predict(oracle_upos)
        predictions.append((nonoracle, weak, {
            "UPOS": oracle_upos, "heads": oracle_heads, "relations": oracle_rels
        }))
    summaries = {mode: Counter() for mode in ("weak_baseline", "nonoracle", "oracle_UPOS_diagnostic")}
    pos_confusion: dict[str, Counter[str]] = defaultdict(Counter)
    statuses = Counter()
    relations: dict[str, Counter[str]] = defaultdict(Counter)
    by_upos: dict[str, Counter[str]] = defaultdict(Counter)
    for sent, (nonoracle, weak, oracle) in zip(targets, predictions):
        rows = sent["rows"]
        for mode, prediction in (
            ("weak_baseline", weak), ("nonoracle", nonoracle),
            ("oracle_UPOS_diagnostic", oracle)
        ):
            correct_head, correct_las = _score(prediction, rows)
            summaries[mode].update(sentences=1, tokens=len(rows),
                                   correct_head=correct_head,
                                   correct_head_and_relation=correct_las)
        for row, upos, method, head, rel in zip(
            rows, nonoracle["UPOS"], nonoracle["POS_evidence"],
            nonoracle["heads"], nonoracle["relations"]
        ):
            pos_confusion[row[1]][upos] += 1
            statuses[method] += 1
            relations[row[3]]["tokens"] += 1
            relations[row[3]]["head_correct"] += int(head == row[2])
            relations[row[3]]["label_correct"] += int(head == row[2] and rel == row[3])
            by_upos[row[1]]["tokens"] += 1
            by_upos[row[1]]["pos_correct"] += int(upos == row[1])
            by_upos[row[1]]["head_correct"] += int(head == row[2])
            by_upos[row[1]]["label_correct"] += int(head == row[2] and rel == row[3])
    n = 10329
    scored = {}
    for mode, counts in summaries.items():
        if counts["tokens"] != n or counts["sentences"] != 829:
            raise TranslationError("Unaccounted original heldout tokens")
        scored[mode] = {
            "sentences": counts["sentences"], "tokens": counts["tokens"],
            "correct_head": counts["correct_head"],
            "correct_head_and_relation": counts["correct_head_and_relation"],
            "UAS": round(counts["correct_head"] / n, 8),
            "LAS": round(counts["correct_head_and_relation"] / n, 8),
            "invalid_trees": 0,
        }
    correctly_tagged = sum(pos_confusion[tag][tag] for tag in pos_confusion)
    report = {
        "experiment": VERSION,
        "classification": "RETROSPECTIVE_EXPOSED_TRAIN_ONLY_GROUP_DIAGNOSTIC_NOT_NEW_BLIND_TEST",
        "original_source_tree": ORIGINAL_TREE, "original_train_git_blob": ORIGINAL_TRAIN_BLOB,
        "source_derived_git_blob": DERIVED_BLOB, "license": "CC-BY-SA-4.0",
        "publisher_groups_training": sorted(TRAIN_GROUPS), "publisher_group_heldout": HELDOUT_GROUP,
        "training_sentences": len(training), "training_tokens": 9157,
        "evaluation_sentences": len(targets), "evaluation_tokens": n,
        "train_heldout_sentence_id_overlap": 0,
        "heldout_sentences_with_exact_training_form_sequence": cross_group_exact_duplicates,
        "source_witness_and_editor_genealogy_independence_verified": False,
        "training_corpus_aggregate_statistics_previously_exposed_in_W13": True,
        "original_official_DEV_previously_exposed": True,
        "original_official_TEST_opened": False,
        "nonoracle_gold_UPOS_used_for_predictions": False,
        "predicted_UPOS_correct": correctly_tagged,
        "predicted_UPOS_accuracy": round(correctly_tagged / n, 8),
        "predicted_UPOS_macro_F1": round(_pos_macro_f1(pos_confusion), 8),
        "predicted_POS_evidence_counts": dict(sorted(statuses.items())),
        "models": scored,
        "oracle_UAS_minus_nonoracle_UAS": round(
            scored["oracle_UPOS_diagnostic"]["UAS"] - scored["nonoracle"]["UAS"], 8),
        "oracle_LAS_minus_nonoracle_LAS": round(
            scored["oracle_UPOS_diagnostic"]["LAS"] - scored["nonoracle"]["LAS"], 8),
        "true_relation_errors": {k: dict(v) for k, v in sorted(relations.items())},
        "true_UPOS_errors": {k: dict(v) for k, v in sorted(by_upos.items())},
        "publisher_group_macro_UAS": scored["nonoracle"]["UAS"],
        "publisher_group_macro_LAS": scored["nonoracle"]["LAS"],
        "heldout_publisher_group_count": 1,
        "later_hieratic_image_ocr_evaluated": False,
        "semantic_translation_or_expert_gold_evaluated": False,
        "trained_neural_model": False,
        "independent_witness_generalization_established": False,
        "LING003_capability_points_earned": 0.0,
    }
    report["report_sha256"] = sha256(_canonical(report)).hexdigest()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "evaluate", "predict"))
    parser.add_argument("--form", action="append", default=[], help="Original FORM; repeat for tokens")
    args = parser.parse_args(argv)
    try:
        data = load_dataset()
        if args.action == "verify":
            out: dict[str, Any] = {
                "source_train_blob": ORIGINAL_TRAIN_BLOB,
                "source_derived_blob": DERIVED_BLOB, "rights": data["rights"],
                "publisher_sentences": 1619, "publisher_tokens": 19486,
                "evaluation_group": HELDOUT_GROUP,
                "dev_labels_not_loaded": True, "test_not_opened": True
            }
        elif args.action == "evaluate":
            if args.form:
                raise TranslationError("Evaluation parameters frozen; no custom FORM args")
            out = evaluate(data)
        else:
            if not args.form:
                raise TranslationError("Prediction requires one or more --form values")
            train = [s for s in data["sentences"] if s["group"] in TRAIN_GROUPS]
            out = TrainOnlyOracleFree(train).predict(args.form)
            out["no_reference_gold_accessed"] = True
        print(json.dumps(out, sort_keys=True, indent=2, ensure_ascii=False))
        return 0
    except (TranslationError, OSError, ValueError, TypeError, KeyError) as exc:
        print("W14 EGYPTIAN SYNTAX REFUSED: " + str(exc), file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
