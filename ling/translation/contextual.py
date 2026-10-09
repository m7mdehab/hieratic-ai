"""W9 genuine AES Egyptian→German contextual translation-memory experiment.

All corpora are publisher CC-BY-SA-4.0 text snapshots pinned by Git blob SHA-1.
A *fixed external subcorpus* never contributes labels, cotext glosses, indices,
threshold selection or language-model statistics. Internal threshold selection
uses five source-text-group folds. Metrics are text-only editorial diagnostics:
a retrieved whole sentence may hallucinate different names, isn't proof of
Egyptological correctness, and is NOT an evaluated original Hieratic image.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha1, sha256
import argparse
import json
import math
from pathlib import Path
import re
from typing import Any

from tools.translation_layer import TranslationError, _canonical, _words, word_f1
from ling.lexical import aes_holdout as aes_source

ROOT = aes_source.ROOT
MANIFEST = ROOT / "ling/translation/data/source_manifest.json"
VERSION = "w9-aes-contextual-translation-memory/1.0.0"
UPSTREAM_COMMIT = "35276d2527cca1a055e31ed5f6683e777717170f"
EXPECTED_COUNTS = {
    "bbawfelsinschriften": (445, 444, 311, "7bfcba9678b64c3526a1123996a0714b5f76812f"),
    "smaek": (38, 38, 8, "82f6f6229283d6c4174373e39b12871761bc81ec"),
    "bbawgraeberspzt": (426, 422, 78, "a427ccf25e92fc7f5d849536af78ae39ae923327"),
    "tuebingerstelen": (247, 247, 21, "87ac34335acd3dc1533580b2017a689fa87abda1"),
}
DEV_CORPORA = ("bbawfelsinschriften", "smaek", "bbawgraeberspzt")
EXTERNAL_CORPUS = "tuebingerstelen"
FOLDS = 5
THRESHOLDS = (0.0, 0.15, 0.3, 0.45, 0.6, 0.8, 1.0)


def _blob_sha(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _json_pinned(path: Path, expected: str, limit: int) -> Any:
    if path.is_symlink() or not path.is_file():
        raise TranslationError("Missing or linked AES publisher source")
    n = path.stat().st_size
    if not (1 <= n <= limit):
        raise TranslationError("AES source exceeds exact corpus size bound")
    data = path.read_bytes()
    if len(data) != n or _blob_sha(data) != expected:
        raise TranslationError("AES publisher source Git blob identity mismatch")
    return json.loads(data.decode("utf-8"))


def load_corpus(root: Path = ROOT) -> dict[str, Any]:
    """Reject mutable source rights/provenance, duplicate text or sentence IDs."""
    # Reuse LING-002's independent verified upstream publisher/registry contract.
    parent = aes_source.read_bundle(root=root)
    try:
        manifest = json.loads((root / "ling/translation/data/source_manifest.json").read_text("utf-8"))
    except (ValueError, OSError, UnicodeError) as exc:
        raise TranslationError("W9 source manifest unreadable") from exc
    if (manifest.get("upstream_revision") != UPSTREAM_COMMIT
            or manifest.get("license") != "CC-BY-SA-4.0"
            or manifest.get("rights_scope") !=
               "scholarly published Egyptian transliteration/German editorial sentence and cotext text only; no original manuscript image or gold certification"
            or manifest.get("train_dev_corpora") != list(DEV_CORPORA)
            or manifest.get("never_tune_reserved_external_subcorpus") != EXTERNAL_CORPUS
            or manifest.get("expected_total_sentences") != 1156
            or manifest.get("expected_translated_sentences") != 1151
            or manifest.get("expected_text_groups") != 418):
        raise TranslationError("W9 licensed corpus/split manifesto changed")
    if not isinstance(manifest.get("files"), list) or len(manifest["files"]) != 4:
        raise TranslationError("Expected precisely four pinned AES corpora")
    all_rows: dict[str, list[dict[str, Any]]] = {}
    ids: set[str] = set()
    all_texts: set[str] = set()
    for name, record in zip((*DEV_CORPORA, EXTERNAL_CORPUS), manifest["files"]):
        n, translated, texts, blob = EXPECTED_COUNTS[name]
        expected_path = ("ling/lexical/data/aes_felsinschriften_ccby_sa.json"
                         if name == "bbawfelsinschriften"
                         else f"ling/translation/data/_aes_{name}.json")
        if (record.get("name") != name or record.get("path") != expected_path
                or record.get("git_blob_sha1") != blob
                or (record.get("sentences"), record.get("translated"), record.get("text_groups")) !=
                   (n, translated, texts)
                or record.get("role") != (
                    "locked_external_subcorpus_test" if name == EXTERNAL_CORPUS else "internal_dev_train")):
            raise TranslationError(f"AES {name} publisher manifest drift")
        raw = _json_pinned(root / expected_path, blob, limit=4_000_000)
        if not isinstance(raw, dict) or len(raw) != n:
            raise TranslationError(f"AES {name} source sentence population changed")
        group_ids: set[str] = set()
        count_translated = 0
        rows: list[dict[str, Any]] = []
        for sid, sent in sorted(raw.items()):
            if not isinstance(sid, str) or not isinstance(sent, dict) or sid in ids:
                raise TranslationError("Duplicate or invalid source sentence")
            text_id = sent.get("text")
            german = sent.get("sentence_translation")
            tokens = sent.get("token")
            if (not isinstance(text_id, str) or not text_id or
                    not isinstance(german, str) or not isinstance(tokens, list) or not tokens):
                raise TranslationError("Broken real AES sentence fields")
            forms: list[str] = []
            glosses: list[str | None] = []
            for token in tokens:
                form = token.get("written_form") if isinstance(token, dict) else None
                if not isinstance(form, str) or not form or len(form) > 512:
                    raise TranslationError("Unusable or forged original Egyptian word form")
                cotext = token.get("cotext_translation")
                if cotext is not None and not isinstance(cotext, str):
                    raise TranslationError("Unusable published cotext gloss")
                forms.append(form)
                glosses.append(cotext if cotext and cotext.strip() and len(cotext) <= 512 else None)
            ids.add(sid)
            group_ids.add(text_id)
            if german.strip():
                count_translated += 1
            rows.append({
                "sentence_id": sid, "text_id": text_id, "corpus": name,
                "forms": tuple(forms), "glosses": tuple(glosses),
                "german": german.strip(),
            })
        if len(group_ids) != texts or count_translated != translated:
            raise TranslationError(f"AES {name} group/reference count changed")
        if all_texts.intersection(group_ids):
            raise TranslationError("AES published text identity reused across corpora")
        all_texts.update(group_ids)
        all_rows[name] = rows
    if (sum(map(len, all_rows.values())) != 1156 or
            sum(sum(bool(r["german"]) for r in group) for group in all_rows.values()) != 1151
            or len(all_texts) != 418 or parent["manifest"]["license"] != "CC-BY-SA-4.0"):
        raise TranslationError("W9 legitimate source dataset census drift")
    return {"manifest": manifest, "groups": all_rows, "all_text_ids": sorted(all_texts)}


def _fold(group_id: str) -> int:
    """Stable split independent of Python hash randomization and file order."""
    return int(sha256(group_id.encode("utf-8")).hexdigest()[:12], 16) % FOLDS


class TranslationMemory:
    """Train-only German sentence retrieval and cotext with explicit abstention."""

    def __init__(self, training: list[dict[str, Any]]):
        if not training:
            raise TranslationError("Cannot fit contextual memory without publisher training sentences")
        self.sentences = sorted(
            (r for r in training if r["german"]),
            key=lambda r: (r["text_id"], r["sentence_id"]),
        )
        self.observations: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self.frequency: Counter[str] = Counter()
        self.source_sequences: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
        for row in self.sentences:
            self.frequency.update(set(row["forms"]))
            self.source_sequences[row["forms"]].append(row)
            for form, gloss in zip(row["forms"], row["glosses"]):
                if gloss:
                    self.observations[form][gloss].add(row["text_id"])
        self.document_count = len(self.sentences)
        self._gloss_cache: dict[tuple[str, ...], dict[str, Any]] = {}
        self._neighbor_cache: dict[tuple[tuple[str, ...], str], dict[str, Any] | None] = {}
        self._weights: list[tuple[dict[str, float], float]] = []
        for row in self.sentences:
            weights = {token: self._idf(token) ** 2 for token in set(row["forms"])}
            norm = math.sqrt(sum(v * v for v in weights.values()))
            self._weights.append((weights, norm))

    def _idf(self, term: str) -> float:
        return math.log(1 + (self.document_count + 1) / (1 + self.frequency[term]))

    def gloss(self, forms: tuple[str, ...]) -> dict[str, Any]:
        if forms in self._gloss_cache:
            return self._gloss_cache[forms]
        items = []
        for term in forms:
            by = self.observations.get(term, {})
            alternatives = sorted(by, key=lambda x: (-len(by[x]), x))
            best = alternatives[0] if alternatives else None
            items.append({
                "source": term, "german": best,
                "candidates": [{"gloss": x, "supporting_train_source_texts": len(by[x])}
                               for x in alternatives[:12]],
                "abstained": best is None,
            })
        result = {
            "text": " ".join(item["german"] or "[?]" for item in items),
            "units": items, "abstentions": sum(item["abstained"] for item in items),
            "mode": "TRAIN_ONLY_GLOSS_FALLBACK",
        }
        self._gloss_cache[forms] = result
        return result

    def neighbor(self, forms: tuple[str, ...], excluded_text_id: str) -> dict[str, Any] | None:
        cache_key = (forms, excluded_text_id)
        if cache_key in self._neighbor_cache:
            return self._neighbor_cache[cache_key]
        candidates = []
        qset = set(forms)
        qweights = {term: self._idf(term) ** 2 for term in qset}
        qnorm = math.sqrt(sum(x * x for x in qweights.values()))
        for idx, row in enumerate(self.sentences):
            if row["text_id"] == excluded_text_id:
                continue
            w, norm = self._weights[idx]
            shared = qset.intersection(w)
            # One common generic title must never justify copying a whole sentence.
            if not shared or (len(qset) > 1 and len(shared) < 2):
                continue
            dot = sum(qweights[t] * w[t] for t in shared)
            cosine = dot / (qnorm * norm) if qnorm and norm else 0.0
            length_ratio = min(len(forms), len(row["forms"])) / max(
                len(forms), len(row["forms"]))
            score = cosine * length_ratio
            if score <= 0:
                continue
            coverage = sum(qweights[x] for x in shared) / sum(qweights.values())
            if coverage < 0.25:
                continue
            candidates.append((score, len(shared), row["text_id"], row["sentence_id"], row))
        if not candidates:
            self._neighbor_cache[cache_key] = None
            return None
        candidates.sort(key=lambda entry: (-entry[0], -entry[1], entry[2], entry[3]))
        best = candidates[0]
        source = best[4]
        result = {
            "text": source["german"], "cosine_length_similarity": round(best[0], 8),
            "shared_source_forms": best[1],
            "source_text_id": source["text_id"],
            "source_sentence_id": source["sentence_id"],
            "source_corpus": source["corpus"],
            "exact_egyptian_form_sequence": forms == source["forms"],
            "source_form_difference": sorted(set(source["forms"]) ^ set(forms)),
            "mode": "CROSS_TEXT_SENTENCE_RETRIEVAL",
        }
        self._neighbor_cache[cache_key] = result
        return result

    def predict(self, row: dict[str, Any], threshold: float) -> dict[str, Any]:
        fallback = self.gloss(row["forms"])
        peer = self.neighbor(row["forms"], row["text_id"])
        use_peer = peer is not None and peer["cosine_length_similarity"] >= threshold
        result = {
            "sentence_id": row["sentence_id"], "source_text_id": row["text_id"],
            "source_corpus": row["corpus"],
            "source_forms": list(row["forms"]),
            "prediction": peer["text"] if use_peer else fallback["text"],
            "mode": peer["mode"] if use_peer else fallback["mode"],
            "nearest_training": peer,
            "token_abstentions_in_gloss": fallback["abstentions"],
            "published_reference_used_for_prediction": False,
            "editorial_source_token_labels_used_for_prediction": False,
            "image_conditional": False,
            "contextual_translation_is_scholarly_verified": False,
            "note": "Nearest German editorial sentence may contain source-specific names or grammar; not authoritative.",
        }
        return result


def _multisets(candidate: str, reference: str) -> tuple[int, int, int]:
    a, b = Counter(_words(candidate)), Counter(_words(reference))
    return sum((a & b).values()), sum(a.values()), sum(b.values())


def _char_ngrams(text: str, n: int) -> Counter[str]:
    text = re.sub(r"\s+", " ", text.casefold().strip())
    return Counter(text[i:i + n] for i in range(max(0, len(text) - n + 1)))


def chrf2(candidate: str, reference: str) -> float:
    """Documented in-house chrF2-style char n=1..6 diagnostic (not sacreBLEU)."""
    ps, rs = [], []
    for n in range(1, 7):
        a, b = _char_ngrams(candidate, n), _char_ngrams(reference, n)
        overlap = sum((a & b).values())
        pa, pb = sum(a.values()), sum(b.values())
        ps.append(overlap / pa if pa else 0.0)
        rs.append(overlap / pb if pb else 0.0)
    p, r = sum(ps) / 6, sum(rs) / 6
    return (5 * p * r / (4 * p + r)) if (4 * p + r) else 0.0


def _accumulate(rows: list[tuple[dict[str, Any], str]]) -> dict[str, Any]:
    overlap = predicted = references = 0
    sentence_f1 = sentence_chr = 0.0
    count = 0
    groups = set()
    modes: Counter[str] = Counter()
    contam = 0
    for row, output in rows:
        if not row["german"]:
            continue
        x, a, b = _multisets(output["prediction"], row["german"])
        overlap += x
        predicted += a
        references += b
        sentence_f1 += word_f1(output["prediction"], row["german"])["f1"]
        sentence_chr += chrf2(output["prediction"], row["german"])
        count += 1
        groups.add(row["text_id"])
        modes[output["mode"]] += 1
        contam += int(output["mode"] == "CROSS_TEXT_SENTENCE_RETRIEVAL"
                      and not output["nearest_training"]["exact_egyptian_form_sequence"])
    return {
        "sentences_scored": count, "source_text_groups": len(groups),
        "word_multiset_overlap": overlap,
        "predicted_words": predicted, "reference_words": references,
        "micro_word_f1": round(2 * overlap / (predicted + references), 8)
            if predicted + references else 0.0,
        "macro_sentence_word_f1": round(sentence_f1 / count, 8) if count else 0.0,
        "macro_sentence_char_ngram_f2": round(sentence_chr / count, 8) if count else 0.0,
        "prediction_modes": dict(sorted(modes.items())),
        "retrievals_with_nonidentical_source_sequence": contam,
    }


def _scored_comparison(items: list[tuple[dict[str, Any], TranslationMemory]],
                       threshold: float) -> dict[str, Any]:
    legacy, contextual = [], []
    for row, model in items:
        base = model.gloss(row["forms"])
        legacy.append((row, {"prediction": base["text"], "mode": base["mode"]}))
        contextual.append((row, model.predict(row, threshold)))
    return {
        "gloss_control": _accumulate(legacy),
        "contextual_translation_memory": _accumulate(contextual),
    }


def evaluate_corpus(corpus: dict[str, Any]) -> dict[str, Any]:
    """Select retrieval threshold only with grouped dev folds; test is untouched."""
    training = [r for sub in DEV_CORPORA for r in corpus["groups"][sub] if r["german"]]
    external = [r for r in corpus["groups"][EXTERNAL_CORPUS] if r["german"]]
    internal_predictions: list[tuple[dict[str, Any], TranslationMemory]] = []
    fold_stats = []
    for fold in range(FOLDS):
        train = [r for r in training if _fold(r["text_id"]) != fold]
        dev = [r for r in training if _fold(r["text_id"]) == fold]
        text_train = {r["text_id"] for r in train}
        text_dev = {r["text_id"] for r in dev}
        if not dev or text_train.intersection(text_dev):
            raise TranslationError("Not an independent source-text grouped internal split")
        model = TranslationMemory(train)
        internal_predictions.extend((row, model) for row in dev)
        fold_stats.append({
            "fold": fold, "train_text_groups": len(text_train),
            "dev_text_groups": len(text_dev), "dev_sentences": len(dev),
        })
    if len(internal_predictions) != len(training):
        raise TranslationError("Not all source-group dev sentences scored exactly once")
    tuning = []
    for threshold in THRESHOLDS:
        score = _scored_comparison(internal_predictions, threshold)
        tuning.append({
            "threshold": threshold,
            "dev_gloss_word_f1": score["gloss_control"]["micro_word_f1"],
            "dev_context_word_f1": score["contextual_translation_memory"]["micro_word_f1"],
            "dev_context_char_f2": score["contextual_translation_memory"]["macro_sentence_char_ngram_f2"],
            "dev_retrieved": score["contextual_translation_memory"]["prediction_modes"].get(
                "CROSS_TEXT_SENTENCE_RETRIEVAL", 0),
        })
    # Select on DEV WORD F1 only. Frozen threshold is used unchanged on test;
    # tie breaker picks stricter threshold to reduce unsupported copied text.
    selected = sorted(tuning, key=lambda x: (-x["dev_context_word_f1"], -x["threshold"]))[0]
    final = TranslationMemory(training)
    train_texts = {r["text_id"] for r in training}
    external_texts = {r["text_id"] for r in external}
    if train_texts.intersection(external_texts):
        raise TranslationError("External text label contamination")
    external_comparison = _scored_comparison([(r, final) for r in external],
                                             selected["threshold"])
    # Report per-subcorpus denominators; the external domain stays one separate
    # never-trained test and cannot be folded into the dev tune metric.
    results = {
        "experiment": VERSION,
        "classification": "REAL_PUBLISHER_TEXT_ONLY_SOURCE_GROUPED_DIAGNOSTIC",
        "raw_source_revision": UPSTREAM_COMMIT,
        "source_git_blobs": {item["name"]: item["git_blob_sha1"]
                             for item in corpus["manifest"]["files"]},
        "licensed": "CC-BY-SA-4.0",
        "source_sentences": 1156,
        "source_translated_sentences": 1151,
        "physical_original_manuscript_images": 0,
        "editorially_blind_gold_references": 0,
        "corpus_name": EXTERNAL_CORPUS,
        "external_test_policy": "ENTIRE_PREDECLARED_AES_SUBCORPUS_EXCLUDED_FROM_TRAINING_TUNING_AND_GLOSSES",
        "internal_grouping_policy": "SHA256_TEXT_ID_5_FOLDS_NO_SHARED_TEXT_WITHIN_FOLD",
        "selected_threshold": selected["threshold"],
        "internal_training_dev_sentences": len(training),
        "external_test_sentences": len(external),
        "external_test_text_groups": len(external_texts),
        "five_fold_group_counts": fold_stats,
        "internal_threshold_selection": tuning,
        "external_test_metrics": external_comparison,
        "trained_neural_parameters": 0,
        "model_kind": "deterministic_train_only_tfidf_sentence_memory_with_german_cotext_fallback",
        "token_reference_accessed_before_prediction": False,
        "scientific_certification": False,
        "not_fluent_generative_translation": True,
        "not_original_image_reading": True,
        "not_manuscript_group_independence": True,
        "accuracy_is_semantic_quality": False,
        "limitations": [
            "Publisher's subcorpus and text IDs may share editorial or physical manuscript genealogy.",
            "Large matched German noun/name fragments can be copied wrongly in near matches.",
            "Selection objective and reporting are word/character overlap, not blind semantic adequacy.",
            "The test corpus was reserved before threshold optimization but does not guarantee new witness, period or scribe.",
            "Written-form tokens are curated Egyptian transliteration, not real OCR predictions from Hieratic pixels.",
            "No paid API, GPU inference, protected benchmark gold or production dataset admission was performed.",
        ],
    }
    results["report_sha256"] = sha256(_canonical(results)).hexdigest()
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "evaluate", "predict"))
    parser.add_argument("--sentence-id")
    parser.add_argument("--output", type=Path)
    options = parser.parse_args(argv)
    try:
        dataset = load_corpus()
        if options.action == "verify":
            output = {
                "corpora": {k: len(v) for k, v in dataset["groups"].items()},
                "total_sentences": sum(map(len, dataset["groups"].values())),
                "total_group_ids": len(dataset["all_text_ids"]),
                "source_revision": UPSTREAM_COMMIT,
                "license": dataset["manifest"]["license"],
            }
        elif options.action == "evaluate":
            output = evaluate_corpus(dataset)
        else:
            if not options.sentence_id:
                raise TranslationError("Specify exact source sentence ID for prediction")
            train = [r for name in DEV_CORPORA for r in dataset["groups"][name] if r["german"]]
            probe = next((r for name in dataset["groups"] for r in dataset["groups"][name]
                          if r["sentence_id"] == options.sentence_id), None)
            if probe is None:
                raise TranslationError("Unknown sentence ID")
            if probe["corpus"] in DEV_CORPORA:
                train = [r for r in train if r["text_id"] != probe["text_id"]]
            output = TranslationMemory(train).predict(probe, 0.3)
            output["selection_type"] = "EXPLORATORY_FIXED_THRESHOLD_NOT_TUNED"
        if options.output:
            if options.output.is_symlink() or options.output.exists():
                raise TranslationError("Refusing overwrite of evaluation report")
            if not options.output.parent.is_dir():
                raise TranslationError("Report parent directory missing")
            try:
                with options.output.open("x", encoding="utf-8", newline="\n") as target:
                    target.write(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
            except FileExistsError as exc:
                raise TranslationError("Refusing concurrent output replacement") from exc
        else:
            print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (TranslationError, aes_source.SourceError, ValueError, OSError) as exc:
        print(f"CONTEXTUAL TRANSLATION REFUSED: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
