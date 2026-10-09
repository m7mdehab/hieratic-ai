"""W12B: publisher-attested ancient Egyptian POS/morphology evidence, not grammar-role gold.

No unseen source annotation is allowed in training. Every POS alternative
and morphological value must be observed under the same original Egyptian form
in independent training original text IDs. Adjacent POS support is descriptive,
NEVER a dependency parse or assertion of meaning.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Any
from tools.translation_layer import TranslationError

MORPH_FIELDS = ("genus", "numerus", "status", "inflection", "voice", "verbalClass")
MIN_CONTEXT_DOCUMENTS = 2
VERSION = "ling003-w12b-original-aes-grammar-evidence/1.0.0"


def _rank(votes: dict[str, set[str]]) -> list[str]:
    return sorted(votes, key=lambda pos: (-len(votes[pos]), pos))


class GrammarEvidence:
    """Train-only exact-form grammar hypotheses; no German/target references."""

    def __init__(self, training: dict[str, Any]):
        self.train_text_ids: set[str] = set()
        self.lexical = defaultdict(lambda: defaultdict(set))
        self.context = defaultdict(lambda: defaultdict(set))
        self.left = defaultdict(lambda: defaultdict(set))
        self.right = defaultdict(lambda: defaultdict(set))
        self.morph = defaultdict(lambda: defaultdict(set))
        self.transitions = defaultdict(set)
        self.train_sentences = len(training)
        for sid, sent in sorted(training.items()):
            if not isinstance(sent, dict) or set(sent) != {"text", "owner", "tokens"}:
                raise TranslationError("Grammar training record contains unsupported fields")
            doc_id = sent["text"]
            tokens = sent["tokens"]
            if not isinstance(doc_id, str) or not doc_id or not isinstance(tokens, list) or not tokens:
                raise TranslationError("Training text ID or tokens missing")
            self.train_text_ids.add(doc_id)
            forms = []
            for token in tokens:
                if set(token) != {"form", "pos", "features"} or not isinstance(token["form"], str):
                    raise TranslationError("Grammar training token or source fields malformed")
                if not token["form"] or len(token["form"]) > 512:
                    raise TranslationError("Grammar training Egyptian written form invalid")
                if token["pos"] is not None and not isinstance(token["pos"], str):
                    raise TranslationError("Original Egyptian POS is malformed")
                if not isinstance(token["features"], dict) or any(
                    key not in MORPH_FIELDS or not isinstance(value, str)
                    for key, value in token["features"].items()
                ):
                    raise TranslationError("Unsupported source morphological field")
                forms.append(token["form"])
            for i, token in enumerate(tokens):
                form, pos = token["form"], token["pos"]
                if not pos:
                    continue
                l = forms[i - 1] if i else ""
                rr = forms[i + 1] if i + 1 < len(forms) else ""
                self.lexical[form][pos].add(doc_id)
                self.context[(form, l, rr)][pos].add(doc_id)
                self.left[(form, l)][pos].add(doc_id)
                self.right[(form, rr)][pos].add(doc_id)
                for key, value in token["features"].items():
                    if value:
                        self.morph[(form, pos, key)][value].add(doc_id)
                if i + 1 < len(tokens) and tokens[i + 1]["pos"]:
                    self.transitions[(pos, tokens[i + 1]["pos"])].add(doc_id)

    def predict(self, forms: list[str], text_id: str) -> dict[str, Any]:
        if text_id in self.train_text_ids:
            raise TranslationError("Target original text ID overlaps grammar training")
        if not isinstance(forms, list) or not forms or any(
            not isinstance(f, str) or not f or len(f) > 512 for f in forms
        ):
            raise TranslationError("Target Egyptian source forms are missing or malformed")
        units = []
        for i, form in enumerate(forms):
            observed = self.lexical.get(form, {})
            ranked = _rank(observed)
            base = ranked[0] if ranked else None
            context_pos = base
            decision = "FORM_MAJORITY" if base else "UNSEEN_FORM_ABSTAIN"
            evidence = len(observed[base]) if base else 0
            l = forms[i - 1] if i else ""
            rr = forms[i + 1] if i + 1 < len(forms) else ""
            for label, table, key in (
                ("TWO_SIDED", self.context, (form, l, rr)),
                ("LEFT", self.left, (form, l)),
                ("RIGHT", self.right, (form, rr)),
            ):
                by_pos = table.get(key, {})
                approved = {
                    x: ids for x, ids in by_pos.items()
                    if x in observed and len(ids) >= MIN_CONTEXT_DOCUMENTS
                }
                if approved:
                    context_pos = _rank(approved)[0]
                    evidence = len(approved[context_pos])
                    decision = label
                    break
            morph = {}
            for field in MORPH_FIELDS:
                candidates = self.morph.get((form, context_pos, field), {}) if context_pos else {}
                morph[field] = [
                    {"value": v, "distinct_training_texts": len(candidates[v])}
                    for v in _rank(candidates)
                ]
            units.append({
                "source_slot": i, "written_form": form,
                "baseline_pos": base, "context_pos": context_pos,
                "pos_decision": decision,
                "selected_pos_distinct_training_texts": evidence,
                "alternatives": [
                    {"pos": v, "distinct_training_texts": len(observed[v])}
                    for v in ranked
                ],
                "morphological_candidates": morph,
                "semantic_role": "UNKNOWN_NOT_INFERRED",
                "syntactic_dependency": "NOT_PREDICTED",
            })
        adjacent = []
        for j in range(len(units) - 1):
            a, bb = units[j]["context_pos"], units[j + 1]["context_pos"]
            adjacent.append({
                "source_slot_pair": [j, j + 1],
                "pos_pair": [a, bb],
                "train_texts_with_same_adjacent_pos": (
                    len(self.transitions.get((a, bb), set())) if a and bb else 0
                ),
                "relation_type": "ORIGINAL_TOKEN_ADJACENCY_NOT_DEPENDENCY_PARSE",
            })
        return {
            "source_text_id": text_id, "forms": list(forms),
            "model": VERSION, "units": units, "adjacent_pos_evidence": adjacent,
            "publisher_target_pos_or_morph_used": False,
            "fluent_translation_claim": False, "grammatical_role_claim": False,
        }
