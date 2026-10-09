"""Source-constrained Egyptian→German lexical and local-order composition, W10.

Ancient Egyptian written forms are curated AES transliteration, not original
Hieratic pixels. German units come solely from other source-text training
glosses, and swaps require independent published pair-order evidence.
No fluent-semantic, named-entity, or independent-witness accuracy is claimed.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Any

from tools.translation_layer import TranslationError, _words

MIN_CONTEXT_SUPPORT = 2
MIN_SWAP_SUPPORT = 2
MAX_ALTERNATIVES = 12
VERSION = "ling003-w10-constrained-composition/1.0.0"


def unique_location(words: list[str], gloss: str) -> int | None:
    phrase = _words(gloss)
    if not phrase or len(phrase) > 6:
        return None
    locations = [i for i in range(len(words) - len(phrase) + 1)
                 if words[i:i + len(phrase)] == phrase]
    return locations[0] if len(locations) == 1 else None


class ConstrainedComposer:
    def __init__(self, rows: list[dict[str, Any]]):
        if not rows:
            raise TranslationError("Cannot fit empty compositional training set")
        self.train_ids = {r["text_id"] for r in rows}
        self.glosses = defaultdict(lambda: defaultdict(set))
        self.context = defaultdict(lambda: defaultdict(set))
        self.left = defaultdict(lambda: defaultdict(set))
        self.right = defaultdict(lambda: defaultdict(set))
        self.orders = defaultdict(lambda: {"normal": set(), "inverted": set()})
        self.train_german = defaultdict(set)
        for row in sorted(rows, key=lambda r: (r["text_id"], r["sentence_id"])):
            forms, glosses = row["forms"], row["glosses"]
            if len(forms) != len(glosses):
                raise TranslationError("Source token and gloss lengths differ")
            for i, (form, gloss) in enumerate(zip(forms, glosses)):
                if not gloss or not gloss.strip() or len(gloss) > 512:
                    continue
                left = forms[i - 1] if i else ""
                right = forms[i + 1] if i + 1 < len(forms) else ""
                g = gloss.strip()
                text = row["text_id"]
                self.glosses[form][g].add(text)
                self.context[(form, left, right)][g].add(text)
                self.left[(form, left)][g].add(text)
                self.right[(form, right)][g].add(text)
            if not row["german"]:
                continue
            german = _words(row["german"])
            self.train_german[" ".join(german)].add(forms)
            for i in range(len(forms) - 1):
                if forms[i] == forms[i + 1] or not glosses[i] or not glosses[i + 1]:
                    continue
                a = unique_location(german, glosses[i])
                b = unique_location(german, glosses[i + 1])
                if a is None or b is None or a == b:
                    continue
                if not (a + len(_words(glosses[i])) <= b or
                        b + len(_words(glosses[i + 1])) <= a):
                    continue
                direction = "normal" if a < b else "inverted"
                self.orders[(forms[i], forms[i + 1])][direction].add(row["text_id"])

    def unit(self, form: str, left: str, right: str) -> dict[str, Any]:
        source = self.glosses.get(form, {})
        if not source:
            return {"form": form, "gloss": None, "abstain": True,
                    "selection": "UNKNOWN_ABSTAIN", "alternatives": []}
        alternatives = sorted(source, key=lambda v: (-len(source[v]), v))
        chosen, mode, support = alternatives[0], "GLOBAL_OTHER_TEXT_GLOSS", len(source[alternatives[0]])
        for label, by, key in (
            ("TWO_SIDED_CONTEXT", self.context, (form, left, right)),
            ("LEFT_CONTEXT", self.left, (form, left)),
            ("RIGHT_CONTEXT", self.right, (form, right)),
        ):
            supported = [(len(ids), g) for g, ids in by.get(key, {}).items()
                         if len(ids) >= MIN_CONTEXT_SUPPORT]
            if supported:
                supported.sort(key=lambda x: (-x[0], x[1]))
                support, chosen = supported[0]
                mode = label
                break
        return {
            "form": form, "gloss": chosen, "abstain": False, "selection": mode,
            "supporting_train_texts": support,
            "alternatives": [{"gloss": g, "train_texts": len(source[g])}
                             for g in alternatives[:MAX_ALTERNATIVES]],
            "syntactic_role": "UNINFERRED_NO_TARGET_GRAMMAR_LABELS",
        }

    def predict(self, row: dict[str, Any]) -> dict[str, Any]:
        if row["text_id"] in self.train_ids:
            raise TranslationError("Target source text ID is in training")
        forms = row["forms"]
        units = [
            self.unit(form, forms[i - 1] if i else "",
                      forms[i + 1] if i + 1 < len(forms) else "")
            for i, form in enumerate(forms)
        ]
        positions, evidence = [], []
        i = 0
        while i < len(forms):
            if i + 1 < len(forms) and units[i]["gloss"] and units[i + 1]["gloss"]:
                votes = self.orders.get((forms[i], forms[i + 1]))
                normal = len(votes["normal"]) if votes else 0
                reverse = len(votes["inverted"]) if votes else 0
                if reverse >= MIN_SWAP_SUPPORT and reverse > 2 * normal:
                    positions += [i + 1, i]
                    evidence.append({"slots": [i, i + 1], "reverse_texts": reverse,
                                     "normal_texts": normal})
                    i += 2
                    continue
            positions.append(i)
            i += 1
        result = " ".join(units[j]["gloss"] or "[?]" for j in positions)
        key = " ".join(_words(result))
        return {
            "sentence_id": row["sentence_id"], "source_text_id": row["text_id"],
            "source_forms": list(forms), "prediction": result,
            "mode": "COMPOSITIONAL_TRAIN_ONLY_GLOSS_UNITS",
            "units": units, "emitted_slot_order": positions,
            "learned_adjacent_swaps": evidence,
            "context_selected_units": sum(x["selection"] in (
                "TWO_SIDED_CONTEXT", "LEFT_CONTEXT", "RIGHT_CONTEXT") for x in units),
            "unknown_abstentions": sum(x["abstain"] for x in units),
            "accidental_exact_nonidentical_train_german": (
                bool(key) and key in self.train_german
                and forms not in self.train_german[key]
            ),
            "whole_sentence_retrieval": False,
            "target_reference_or_labels_used": False,
            "fluent_or_semantically_certified": False,
        }
