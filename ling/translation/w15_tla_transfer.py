"""W15 preregistered AES -> TLA Late Egyptian German transfer *text* diagnostic.

No model is trained on TLA targets. This cannot validate hieratic image reading,
scribe-independent translation, fluent German or independent semantic adequacy.
Target TLA v19 JSONL is deliberately NOT bundled unless original exact publisher
bytes have been independently verified; the CLI refuses missing/changed inputs.
CC BY-SA 4.0 publisher TLA data, BBAW/SAW, Richter/Werning et al.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha1, sha256
import json
from pathlib import Path
import sys
from typing import Any

from ling.translation import w11_evaluation
from tools.translation_layer import TranslationError, _canonical, word_f1

ROOT = Path(__file__).resolve().parents[2]
DONOR_REL = w11_evaluation.DONOR
DONOR_BLOB = w11_evaluation.DONOR_BLOB
DONOR_SENTENCES = 3021
DONOR_GROUPS = 1130

TLA_DATASET = "thesaurus-linguae-aegyptiae/tla-late_egyptian-v19-premium"
TLA_REVISION = "8af85941783ba575d5a8985c80c688f948c50040"
# Non-LFS HTTP ETag from exact publisher-resolved train.jsonl response.
# Validate against actual original Git blob before treating this as a source.
TLA_PUBLISHER_GIT_BLOB = "74a058b192314b165bec33278fb882ba1333b172"
TLA_TARGET_SENTENCES = 3606
TLA_FIELDS = frozenset({
    "hieroglyphs", "transliteration", "lemmatization", "UPOS",
    "glossing", "translation", "dateNotBefore", "dateNotAfter",
})
VERSION = "ling003-w15-aes-to-tla-late-egyptian-train-only/1.0.0"
EVIDENCE_GRADE = "PUBLISHED_LATE_EGYPTIAN_CORPUS_TRANSFER_NOT_WITNESS_INDEPENDENT_GOLD"
MAX_TARGET_BYTES = 8_000_000
MAX_ROW_BYTES = 200_000


def git_blob_sha(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def load_donor(root: Path = ROOT) -> dict[str, Any]:
    """Pin actual prior W11 AES donor, never target translation or morphology."""
    donor = w11_evaluation.pinned_json(root, DONOR_REL, DONOR_BLOB, 3_000_000)
    if len(donor) != DONOR_SENTENCES:
        raise TranslationError("Frozen 3021-sentence W11 donor population changed")
    groups = set()
    editors = Counter()
    seen = set()
    for sid, row in donor.items():
        if not isinstance(sid, str) or not sid or sid in seen:
            raise TranslationError("Duplicate or malformed donor sentence ID")
        seen.add(sid)
        if not isinstance(row, dict) or set(row) != {"text", "owner", "token", "sentence_translation"}:
            raise TranslationError("W11 publisher donor schema mismatch")
        tid, owner, tokens, german = (
            row["text"], row["owner"], row["token"], row["sentence_translation"]
        )
        if not isinstance(tid, str) or not tid or not isinstance(owner, str) or not owner:
            raise TranslationError("Donor original text group or credited editor missing")
        if not isinstance(german, str) or not german or len(german) > 20_000:
            raise TranslationError("W11 publisher donor German sentence invalid")
        if not isinstance(tokens, list) or not tokens or len(tokens) > 200:
            raise TranslationError("W11 donor tokens malformed")
        for token in tokens:
            if not isinstance(token, dict) or set(token) != {"written_form", "cotext_translation"}:
                raise TranslationError("W11 original word-form/gloss fields drift")
            form, gloss = token["written_form"], token["cotext_translation"]
            if not isinstance(form, str) or not form or len(form) > 512:
                raise TranslationError("Invalid donor Egyptian original written form")
            if gloss is not None and (not isinstance(gloss, str) or len(gloss) > 512):
                raise TranslationError("Invalid donor publisher contextual German gloss")
        groups.add(tid)
        editors[owner] += 1
    if len(groups) != DONOR_GROUPS:
        raise TranslationError("Original AES donor source-group count changed")
    if dict(editors) != {"Stephan Seidlmayer": 550, "Stefan Grunert": 2463, "Ingelore Hafemann": 8}:
        raise TranslationError("Publisher donor editorial attribution drift")
    return donor


def _winner(support: dict[str, set[str]]) -> tuple[str, int]:
    if not support:
        raise TranslationError("No source-supported candidate gloss/translation")
    chosen = min(support, key=lambda value: (-len(support[value]), value))
    return chosen, len(support[chosen])


class FrozenAESIndex:
    def __init__(self, donor: dict[str, Any]):
        if len(donor) != DONOR_SENTENCES:
            raise TranslationError("Unverified donor population for source transfer")
        lexical: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        exact: dict[tuple[str, ...], dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        groups = set()
        for sid, sent in sorted(donor.items()):
            if not isinstance(sent, dict):
                raise TranslationError("W11 AES donor structure changed")
            tid = sent["text"]
            groups.add(tid)
            forms = []
            for token in sent["token"]:
                normalized = token["written_form"].casefold()
                forms.append(normalized)
                gloss = token["cotext_translation"]
                if isinstance(gloss, str) and gloss.strip():
                    lexical[normalized][gloss.strip()].add(tid)
            german = sent["sentence_translation"].strip()
            if german:
                exact[tuple(forms)][german].add(tid)
        if len(groups) != DONOR_GROUPS:
            raise TranslationError("Incorrect AES donor evidence group census")
        self.lexical = lexical
        self.exact = exact

    def predict(self, original_transliteration: str) -> dict[str, Any]:
        """Input accepts ONLY original source transcription, never target gold."""
        if not isinstance(original_transliteration, str) or len(original_transliteration) > 100_000:
            raise TranslationError("Expected raw Egyptian transliteration string only")
        forms = original_transliteration.split()
        if len(forms) > 500:
            raise TranslationError("Target token count exceeds frozen input bound")
        forms_normalized = tuple(f.casefold() for f in forms)
        output = []
        matched = 0
        for i, (orig, normal) in enumerate(zip(forms, forms_normalized)):
            candidates = self.lexical.get(normal, {})
            if candidates:
                selected, supporters = _winner(candidates)
                matched += 1
                outcome = "TRAIN_ONLY_AES_CONTEXTUAL_GLOSS"
            else:
                selected, supporters, outcome = None, 0, "ABSTAIN_NO_TRAIN_ATTESTATION"
            output.append({
                "index": i, "egyptian_form": orig,
                "candidate_german": selected, "distinct_aes_text_support": supporters,
                "evidence": outcome,
            })
        parallels = self.exact.get(forms_normalized, {})
        if forms and parallels:
            selected_full, sent_support = _winner(parallels)
            mode = "AES_TRAIN_ONLY_FULL_ORDERED_SENTENCE_PARALLEL"
        else:
            selected_full, sent_support = None, 0
            mode = "AES_TRAIN_ONLY_WORD_GLOSS_FALLBACK"
        gloss_sequence = " ".join(v["candidate_german"] or "[?]" for v in output)
        return {
            "mode": mode,
            "input_transliteration": original_transliteration,
            "word_forms": forms,
            "word_count": len(forms),
            "exact_lexical_matches": matched,
            "unknown_words": len(forms) - matched,
            "units": output,
            "gloss_sequence": gloss_sequence,
            "output_german": selected_full if selected_full is not None else gloss_sequence,
            "full_sentence_parallel_distinct_train_source_groups": sent_support,
            "target_translation_or_UPOS_used": False,
            "generates_fluent_translation": False,
        }


def parse_target_raw(raw: bytes) -> list[dict[str, str]]:
    """Strict published JSONL parser. Does not assert publisher identity on its own."""
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_TARGET_BYTES:
        raise TranslationError("TLA target raw byte-size bound violated")
    lines = raw.splitlines()
    if not lines or any(not line or len(line) > MAX_ROW_BYTES for line in lines):
        raise TranslationError("TLA dataset has blank, oversized or missing JSONL rows")
    seen_types = set()
    result = []
    for i, line in enumerate(lines, 1):
        try:
            item = json.loads(line.decode("utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise TranslationError(f"Invalid TLA published JSONL at row {i}") from exc
        if not isinstance(item, dict) or set(item) != TLA_FIELDS:
            raise TranslationError(f"TLA publisher field inventory changed at row {i}")
        if any(not isinstance(value, str) for value in item.values()):
            raise TranslationError(f"TLA fields contain nonstring values at row {i}")
        if any(len(value) > 100_000 for value in item.values()):
            raise TranslationError(f"TLA string length exceeds bound at row {i}")
        seen_types.add(tuple(sorted(item)))
        result.append(item)
    if len(seen_types) != 1:
        raise TranslationError("TLA target schema inconsistent")
    return result


def load_target(path: Path) -> dict[str, Any]:
    """Exact-publisher-byte ingestion; never accept a local replacement."""
    if path.is_symlink() or not path.is_file():
        raise TranslationError("TLA original licensed publisher JSONL missing or linked")
    raw = path.read_bytes()
    actual_blob = git_blob_sha(raw)
    if actual_blob != TLA_PUBLISHER_GIT_BLOB:
        raise TranslationError(
            "TLA raw JSONL not verified against exact published Git blob; "
            f"observed {actual_blob}, expected {TLA_PUBLISHER_GIT_BLOB}"
        )
    rows = parse_target_raw(raw)
    if len(rows) != TLA_TARGET_SENTENCES:
        raise TranslationError("TLA publisher 3606-sentence target census drift")
    return {
        "publisher_git_blob": actual_blob,
        "sha256": sha256(raw).hexdigest(),
        "bytes": len(raw),
        "publisher_revision": TLA_REVISION,
        "rows": rows,
        "rights": "CC-BY-SA-4.0",
        "witness_ids_provided_by_source": False,
    }


def evaluate(donor: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    """Scores only a publisher-verified cohort, no arbitrary synthetic gold."""
    if (target.get("publisher_git_blob") != TLA_PUBLISHER_GIT_BLOB
            or target.get("publisher_revision") != TLA_REVISION
            or target.get("rights") != "CC-BY-SA-4.0"
            or target.get("witness_ids_provided_by_source") is not False):
        raise TranslationError("Refusing non-publisher target evidence as a scored cohort")
    rows = target.get("rows")
    if not isinstance(rows, list) or len(rows) != TLA_TARGET_SENTENCES:
        raise TranslationError("TLA target population mismatch")
    index = FrozenAESIndex(donor)
    # The only input handed to the predictor is Egyptian transliteration.
    predictions = [index.predict(row["transliteration"]) for row in rows]
    by_mode = Counter()
    total_forms = matched_forms = empty_input = missing_refs = 0
    exact_train_repeat = Counter()
    total_overlap = total_pred_words = total_ref_words = 0
    sum_macro = 0.0
    for row, prediction in zip(rows, predictions):
        by_mode[prediction["mode"]] += 1
        total_forms += prediction["word_count"]
        matched_forms += prediction["exact_lexical_matches"]
        empty_input += prediction["word_count"] == 0
        reference = row["translation"]  # opened only AFTER all predictions
        if not reference.strip():
            missing_refs += 1
        metric = word_f1(prediction["output_german"], reference)
        total_overlap += metric["overlap"]
        total_pred_words += metric["predicted_word_count"]
        total_ref_words += metric["published_word_count"]
        sum_macro += metric["f1"]
    if sum(by_mode.values()) != TLA_TARGET_SENTENCES:
        raise TranslationError("TLA predictions have missing denominator")
    p = total_overlap / total_pred_words if total_pred_words else 0.0
    r = total_overlap / total_ref_words if total_ref_words else 0.0
    result = {
        "version": VERSION, "classification": EVIDENCE_GRADE,
        "train_publisher": "Schweitzer AED/AES CC BY-SA 4.0",
        "train_git_blob": DONOR_BLOB, "train_sentences": DONOR_SENTENCES,
        "train_source_text_groups": DONOR_GROUPS,
        "test_publisher": "BBAW/SAW TLA Late Egyptian v19 CC BY-SA 4.0",
        "test_revision": TLA_REVISION, "test_git_blob": TLA_PUBLISHER_GIT_BLOB,
        "test_original_sha256": target.get("sha256"), "test_original_bytes": target.get("bytes"),
        "evaluation_sentences": TLA_TARGET_SENTENCES, "reference_language": "German",
        "model": "deterministic_train_only_other_editorial_source_gloss_lookup",
        "hyperparameters_chosen_after_test": False, "all_predictions_generated_before_scoring": True,
        "total_egyptian_transliteration_tokens": total_forms,
        "train_attested_target_forms": matched_forms,
        "unattested_target_forms": total_forms - matched_forms,
        "token_form_coverage": round(matched_forms / total_forms, 8) if total_forms else 0.0,
        "sentences_with_empty_transliteration": empty_input,
        "sentences_with_missing_german_reference": missing_refs,
        "prediction_modes": dict(sorted(by_mode.items())),
        "zero_evidence_null_baseline_word_F1": 0.0,
        "candidate_total_german_words": total_pred_words,
        "reference_total_german_words": total_ref_words,
        "german_word_unigram_overlap": total_overlap,
        "german_word_micro_precision": round(p, 8),
        "german_word_micro_recall": round(r, 8),
        "german_word_micro_F1": round(2 * p * r / (p + r), 8) if p+r else 0.0,
        "german_word_sentence_macro_F1": round(sum_macro / TLA_TARGET_SENTENCES, 8),
        "publisher_original_witness_ids_available": False,
        "independent_witness_or_editorial_genealogy_split_verified": False,
        "AES_TLA_editorial_provenance_independence_verified": False,
        "original_hieratic_image_input": False,
        "certified_fluent_semantic_translation": False,
        "real_model_trained": False,
        "scientific_CAPABILITY_credit": 0.0,
        "official_EgyptianPC_TEST_opened": False,
        "limitations": [
            "TLA v19 premium publisher rows expose no source text/document/witness IDs.",
            "TLA and older AES derive from overlapping Egyptological editorial ecosystems; genealogy not cleared.",
            "Transliteration is publisher text, not original hieratic OCR or line-aligned image input.",
            "German word overlap is not translation semantic adequacy, grammatical fidelity or expert adjudication.",
            "This is source-published corpus transfer, not independent unseen physical-witness evaluation.",
            "Earlier AES train donor and public TLA dataset-card example were already exposed.",
        ],
    }
    result["report_sha256"] = sha256(_canonical(result)).hexdigest()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify-train", "verify-target", "predict", "evaluate"))
    parser.add_argument("--target-path", type=Path)
    parser.add_argument("--text")
    args = parser.parse_args(argv)
    try:
        donor = load_donor()
        if args.action == "verify-train":
            output: dict[str, Any] = {
                "donor_git_blob": DONOR_BLOB,
                "donor_sentences": len(donor),
                "donor_source_text_groups": len({s["text"] for s in donor.values()}),
                "original_late_egyptian_target_not_inspected": True,
            }
        elif args.action == "predict":
            if args.text is None:
                raise TranslationError("FORM-only predict requires --text")
            output = FrozenAESIndex(donor).predict(args.text)
        else:
            if args.target_path is None:
                raise TranslationError("TLA target requires --target-path to exact raw publisher JSONL")
            source = load_target(args.target_path)
            if args.action == "verify-target":
                output = {
                    "publisher_revision": source["publisher_revision"],
                    "original_git_blob": source["publisher_git_blob"],
                    "original_sha256": source["sha256"],
                    "bytes": source["bytes"],
                    "rows": len(source["rows"]),
                    "license": source["rights"],
                    "original_witness_identifiers_available": False,
                }
            else:
                output = evaluate(donor, source)
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (TranslationError, OSError, KeyError, TypeError, ValueError, UnicodeError) as exc:
        print("W15 TLA TRANSFER REFUSED: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
