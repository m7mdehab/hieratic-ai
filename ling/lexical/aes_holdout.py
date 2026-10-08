"""Real Ancient Egyptian lexical/morphological reference and source-held-out diagnostic.

Publisher sources: Simon D. Schweitzer's AED-TEI and AES, CC BY-SA 4.0.
This is authentic scholarly text metadata, not image OCR, a language model,
blind Egyptologist gold, sealed evaluation, or dataset production admission.

In the diagnostic, no token annotation from the target *text ID* is allowed
into its candidate-generation index. The common public AED dictionary is
an openly published reference and can overlap with AES editorial sources.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha1, sha256
import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data"
VERSION = "ling-aes-scholarship-holdout/1.0.0"
FEATURES = ("adjective", "genus", "inflection", "morphology", "number",
            "numerus", "particle", "pronoun", "status", "verbalClass", "voice")

EXPECTED_PART_SHA = (
    "ccb5250132e970a3d2e9ad9d6a27adc3a0bef63c",
    "73fb1452a900a6487109e7ff3e35a3547e8fcb92",
    "13c8b90a35e9666cfc1fb7aaaf40630f03f8378f",
    "7b9b786d63124b80ce6abdf177acb87d0584d594",
    "9c51f59a063aa582965bbc1162ceef96de8b872c",
    "2e8c8404c360885f16f335da02e9336add0792a1",
    "12e81a8173b741e64b3f3caee458304be0a13bbe",
)
EXPECTED_AES_SHA = "7bfcba9678b64c3526a1123996a0714b5f76812f"
EXPECTED_AED_SOURCE_SHA = "078f2f7b83bd642b6530ed000dbc68f9aa79c06e"


class SourceError(ValueError):
    """Publisher source, provenance or holdout invariant failed."""


def _blob(path: Path, sha: str, *, size_limit: int) -> bytes:
    """Git object identity verification prevents changed JSON from self-certifying."""
    if path.is_symlink() or not path.is_file():
        raise SourceError(f"Missing or linked source file {path.name}")
    size = path.stat().st_size
    if size == 0 or size > size_limit:
        raise SourceError(f"Out-of-bound source file {path.name}")
    raw = path.read_bytes()
    if len(raw) != size:
        raise SourceError(f"Source file changed during read: {path.name}")
    actual = sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    if actual != sha:
        raise SourceError(f"Published source Git blob identity mismatch: {path.name}")
    return raw


def _load_manifest(data: Path) -> dict[str, Any]:
    try:
        mf = json.loads((data / "scholarly_source_manifest.json").read_text("utf-8"))
    except (ValueError, OSError) as exc:
        raise SourceError(f"Invalid scholarly manifest: {exc}") from exc
    expected = {
        "license": "CC-BY-SA-4.0",
        "classification": "SCHOLARLY_PUBLISHED_OPEN_SA_TEXT_ONLY",
        "scientific_status": "DEVELOPMENT_GRADE_OPEN_SCHOLARLY_REFERENCE_NOT_BLIND_OR_IMAGE_GOLD",
        "train_dev_release": "not_admitted_DATA008",
        "verified_expert_gold": "published_editor_annotations_not_new_blind_review",
    }
    for k, value in expected.items():
        if mf.get(k) != value:
            raise SourceError(f"Unverified scholarly manifest status: {k}")
    aed = mf.get("aed", {})
    aes = mf.get("aes", {})
    if (aed.get("revision") != "462c722e0323e05641aea2eee8cdf1e27303d939"
        or aed.get("upstream_git_blob_sha1") != EXPECTED_AED_SOURCE_SHA
        or aes.get("revision") != "35276d2527cca1a055e31ed5f6683e777717170f"
        or aes.get("git_blob_sha1") != EXPECTED_AES_SHA
        or aes.get("expected_sentences") != 445
        or aed.get("expected_entries") != 35052
        or mf.get("source_registry_ids") != ["SRC-AED-TEI", "SRC-AES-OPEN"]):
        raise SourceError("Pinned publisher source revision changed")
    actual_parts = aed.get("partitions")
    if (not isinstance(actual_parts, list) or len(actual_parts) != 8
        or any(row != [f"aed_lemmas_part{i:02d}.jsonl", EXPECTED_PART_SHA[i - 1],
                           5000 if i <= 7 else 52]
               for i, row in enumerate(actual_parts, start=1))):
        raise SourceError("Publisher lexical partition manifest changed")
    return mf


def _validate_rights(root: Path) -> None:
    import yaml
    registry_path = root / "data" / "sources" / "registry.yaml"
    reg = yaml.safe_load(registry_path.read_text("utf-8"))
    src = {x["source_id"]: x for x in reg["sources"]}
    for key in ("SRC-AED-TEI", "SRC-AES-OPEN"):
        item = src.get(key)
        if (not item or item.get("verified_status") != "VERIFIED-PRIMARY"
                or item.get("rights_class") != "OPEN-SA"
                or item.get("development_use") != "allowed"
                or "SHARE-ALIKE-REVIEW" not in item.get("project_review_markers", [])):
            raise SourceError(f"Verified CC BY-SA text-layer rights missing for {key}")


def read_bundle(*, root: Path = ROOT, data: Path | None = None) -> dict[str, Any]:
    """Load full real, immutable publisher snapshots; never fetch URLs."""
    data = data or root / "ling" / "lexical" / "data"
    mf = _load_manifest(data)
    _validate_rights(root)
    lemmas: dict[str, dict[str, Any]] = {}
    forms: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ix, expected in enumerate(EXPECTED_PART_SHA, 1):
        path = data / f"aed_lemmas_part{ix:02d}.jsonl"
        raw = _blob(path, expected, size_limit=1_500_000)
        lines = raw.decode("utf-8").splitlines()
        if len(lines) != (5000 if ix <= 7 else 52):
            raise SourceError(f"AED partition row count invalid: {ix}")
        for line in lines:
            x = json.loads(line)
            if (not isinstance(x, dict)
                or set(x) != {"lemma_id", "form", "pos_source",
                             "root_ref", "english_gloss"}
                or not re.fullmatch(r"tla\d+", x["lemma_id"])
                or not isinstance(x["form"], str) or not x["form"]
                or not isinstance(x["pos_source"], str) or not x["pos_source"]
                or x["lemma_id"] in lemmas):
                raise SourceError(f"Malformed/duplicate AED lemma in part {ix}")
            if x["root_ref"] is not None and not re.fullmatch(r"tla\d+", x["root_ref"]):
                raise SourceError("Invalid AED root xref")
            lemmas[x["lemma_id"]] = x
            forms[x["form"]].append(x)
    if len(lemmas) != 35052:
        raise SourceError("Incomplete AED scholarly dictionary")
    raw = _blob(data / "aes_felsinschriften_ccby_sa.json",
                EXPECTED_AES_SHA, size_limit=2_000_000)
    corpus = json.loads(raw.decode("utf-8"))
    if not isinstance(corpus, dict) or len(corpus) != 445:
        raise SourceError("AES scholar sentence count invalid")
    tokens: list[dict[str, Any]] = []
    seen: set[str] = set()
    texts: set[str] = set()
    for sentence_id, sentence in sorted(corpus.items()):
        if not isinstance(sentence, dict):
            raise SourceError("Malformed scholarly sentence")
        source_text = sentence.get("text")
        if not isinstance(source_text, str) or not source_text:
            raise SourceError("Missing original-source text ID")
        texts.add(source_text)
        for offset, token in enumerate(sentence.get("token", [])):
            publisher_id = token.get("_id")
            if publisher_id is not None and (not isinstance(publisher_id, str) or not publisher_id):
                raise SourceError("Malformed publisher token ID")
            # Fifteen damaged/unlabelled publisher tokens have no _id. Preserve
            # that absence; a stable local locator is NOT an editorial ID.
            tid = publisher_id or f"UNIDENTIFIED_SOURCE_TOKEN:{sentence_id}:{offset}"
            if tid in seen:
                raise SourceError("Duplicate publisher token or derived locator")
            seen.add(tid)
            tokens.append({
                "id": tid, "publisher_token_id": publisher_id,
                "sentence_id": sentence_id, "text": source_text,
                "written_form": token.get("written_form"),
                "lemmaID": token.get("lemmaID"),
                "lemma_form": token.get("lemma_form"),
                "pos": token.get("pos"),
                "features": {k: token[k] for k in FEATURES
                             if k in token and token[k] not in (None, "")},
            })
    if (len(tokens) != 2526 or len(texts) != 311
        or sum(bool(t["lemmaID"]) for t in tokens) != 2305
        or sum(t["publisher_token_id"] is None for t in tokens) != 15):
        raise SourceError("Published AES token/text/lemma census drift")
    # No scholarly token is rewritten or filled in when its published labels
    # are absent. A separate source-text holdout controls candidate training.
    return {
        "manifest": mf, "lemmas": lemmas, "forms": forms, "tokens": tokens,
        "texts": texts, "aes_blob": EXPECTED_AES_SHA,
    }


def _observed_by_form(tokens: list[dict[str, Any]]
                      ) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for token in tokens:
        if token["written_form"] and token["lemmaID"]:
            groups[token["written_form"]].append(token)
    return groups


def analyse(bundle: dict[str, Any], form: str, *,
            excluded_text_id: str | None = None) -> dict[str, Any]:
    """Return all *source-observed* candidates with reproducible alternatives.

    Leave-text-out excludes target text labels from AES lookup. AED is common
    published dictionary, never a blind/gold independent annotation.
    No morphology is inferred from POS, spelling or gloss heuristics.
    """
    if not isinstance(form, str) or not form or len(form) > 512:
        raise SourceError("A real nonempty form (<=512 codepoints) is required")
    observations = bundle.get("observations")
    if observations is None:
        observations = _observed_by_form(bundle["tokens"])
    candidates: dict[str, dict[str, Any]] = {}
    for row in bundle["forms"].get(form, []):
        lemma_id = row["lemma_id"].removeprefix("tla")
        candidates[lemma_id] = {
            "lemma_id": lemma_id, "lemma_form": row["form"],
            "dictionary_pos": row["pos_source"], "root_ref": row["root_ref"],
            "english_gloss": row["english_gloss"],
            "source_layers": ["AED_DICTIONARY_EXACT_LEMMA_FORM"],
            "published_pos_alternatives": [],
            "observed_morphology_alternatives": [],
        }
    morph_by_lemma: dict[str, set[tuple[tuple[str, str], ...]]] = defaultdict(set)
    pos_by_lemma: dict[str, set[str]] = defaultdict(set)
    for token in observations.get(form, []):
        if token["text"] == excluded_text_id:
            continue
        lemma_id = token["lemmaID"]
        if lemma_id not in candidates:
            record = bundle["lemmas"].get("tla" + lemma_id) if lemma_id.isdecimal() else None
            candidates[lemma_id] = {
                "lemma_id": lemma_id,
                "lemma_form": record["form"] if record else None,
                "dictionary_pos": record["pos_source"] if record else None,
                "root_ref": record["root_ref"] if record else None,
                "english_gloss": record["english_gloss"] if record else None,
                "source_layers": [],
                "published_pos_alternatives": [],
                "observed_morphology_alternatives": [],
            }
        if "AES_CROSS_TEXT_OBSERVED_FORM" not in candidates[lemma_id]["source_layers"]:
            candidates[lemma_id]["source_layers"].append(
                "AES_CROSS_TEXT_OBSERVED_FORM")
        if token["pos"]:
            pos_by_lemma[lemma_id].add(token["pos"])
        if token["features"]:
            # Original publisher strings are preserved; absent features are NOT
            # interpreted as explicit feature negations.
            morph_by_lemma[lemma_id].add(
                tuple(sorted((key, str(value))
                             for key, value in token["features"].items())))
    for lemma_id, cand in candidates.items():
        cand["published_pos_alternatives"] = sorted(pos_by_lemma[lemma_id])
        cand["observed_morphology_alternatives"] = [
            dict(bundle_) for bundle_ in sorted(morph_by_lemma[lemma_id])]
    ordered = [candidates[k] for k in sorted(candidates)]
    return {
        "form": form, "excluded_source_text": excluded_text_id,
        "outcome": "unattested" if not ordered else
                   ("interpreted" if len(ordered) == 1 else "ambiguous"),
        "candidate_count": len(ordered), "candidates": ordered,
        "source": "CC_BY_SA_SCHOLARLY_AED_AES_REFERENCE_NOT_BLIND_GOLD",
        "training_corpus_admitted": False, "certified_science": False,
    }


def evaluate(bundle: dict[str, Any]) -> dict[str, Any]:
    """Evaluate independently for each source text with its own labels hidden.

    This is an *exhaustive* leave-one-text-out development diagnostic on the
    real publisher annotations, not a statistically independent blinded test.
    """
    bundle["observations"] = _observed_by_form(bundle["tokens"])
    counts: Counter[str] = Counter()
    per_text: dict[str, Counter[str]] = defaultdict(Counter)
    examples = []
    for token in bundle["tokens"]:
        counts["tokens_total"] += 1
        gold = token["lemmaID"]
        if not gold or not token["written_form"]:
            counts["tokens_without_editor_lemma_or_form"] += 1
            continue
        counts["tokens_with_published_lemma"] += 1
        t = per_text[token["text"]]
        t["with_lemma"] += 1
        result = analyse(bundle, token["written_form"],
                         excluded_text_id=token["text"])
        ids = {c["lemma_id"].removeprefix("tla") for c in result["candidates"]}
        if ids:
            counts["lemma_candidate_covered"] += 1
        if gold in ids:
            counts["lemma_in_candidates"] += 1
            t["lemma_in_candidates"] += 1
        else:
            if len(examples) < 25:
                examples.append({
                    "token_id": token["id"], "text_id": token["text"],
                    "form": token["written_form"],
                    "published_gold_lemma_id": gold,
                    "candidate_lemma_ids": sorted(ids)[:12],
                })
        if len(ids) == 1:
            counts["single_lemma_candidate"] += 1
            if gold in ids:
                counts["correct_single_candidate"] += 1
        if token["pos"]:
            counts["tokens_with_published_pos"] += 1
            if any(c["lemma_id"].removeprefix("tla") == gold and
                   (token["pos"] in c["published_pos_alternatives"] or
                    (c["dictionary_pos"] or "").split("/")[0] == token["pos"])
                   for c in result["candidates"]):
                counts["published_pos_in_candidates"] += 1
        if token["features"]:
            counts["tokens_with_published_morphology"] += 1
            if any(c["observed_morphology_alternatives"]
                   for c in result["candidates"]):
                counts["morphology_candidate_covered"] += 1
            if any(c["lemma_id"].removeprefix("tla") == gold
                   and token["features"] in
                       c["observed_morphology_alternatives"]
                   for c in result["candidates"]):
                counts["published_morphology_bundle_in_candidates"] += 1
    if len(per_text) != 311:
        raise SourceError("Source-held-out count changed")
    def ratio(num: str, denom: str) -> float | None:
        n = counts[denom]
        return round(counts[num] / n, 6) if n else None
    summary = {
        "schema_version": "1.0.0",
        "generator": VERSION,
        "evidence_grade": "PUBLISHED_SCHOLARLY_TEXT_LABEL_DIAGNOSTIC",
        "evaluation": "EXHAUSTIVE_LEAVE_ONE_AES_TEXT_ID_OUT_NO_TARGET_LABEL_IN_LOOKUP",
        "dataset_rights": "CC-BY-SA-4.0; text-only, share-alike retained",
        "source_aed_lemma_count": len(bundle["lemmas"]),
        "source_aes_sentence_count": 445,
        "source_text_groups": len(bundle["texts"]),
        "metrics": dict(sorted(counts.items())),
        "ratios": {
            "lemma_candidate_coverage": ratio(
                "lemma_candidate_covered", "tokens_with_published_lemma"),
            "lemma_candidate_recall": ratio(
                "lemma_in_candidates", "tokens_with_published_lemma"),
            "single_lemma_correct_given_single": (
                round(counts["correct_single_candidate"] /
                      counts["single_lemma_candidate"], 6)
                if counts["single_lemma_candidate"] else None),
            "pos_alternative_recall": ratio(
                "published_pos_in_candidates", "tokens_with_published_pos"),
            "morphology_bundle_candidate_recall": ratio(
                "published_morphology_bundle_in_candidates",
                "tokens_with_published_morphology"),
        },
        "failure_examples_first_25": examples,
        "scientific_limitations": [
            "Public editorial corpus, shared published dictionary, possible pretrained exposure",
            "Text-ID holdout is not verified physical manuscript/scribe independence",
            "Published token lemmas are editorial silver labels, not blind two-reader gold",
            "Exact-form lookup cannot read images, infer unseen morphology or assess translation",
            "No DATA-008 corpus promotion, held-out HieraticBench test or capability certification",
        ],
        "training_admission": "BLOCKED",
        "certified_hieratic_image_reading_experiments": 0,
        "scored_blind_gold_evaluations": 0,
    }
    summary["report_sha256"] = sha256(json.dumps(
        summary, sort_keys=True, ensure_ascii=False,
        separators=(",", ":")).encode("utf-8")).hexdigest()
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("verify")
    sub.add_parser("evaluate")
    q = sub.add_parser("lookup")
    q.add_argument("--form", required=True)
    q.add_argument("--exclude-text-id", default=None)
    a = parser.parse_args(argv)
    try:
        bundle = read_bundle()
        if a.action == "verify":
            out = {
                "aed_lemmas": len(bundle["lemmas"]),
                "aes_sentences": 445, "aes_tokens": len(bundle["tokens"]),
                "aes_source_texts": len(bundle["texts"]),
                "license": "CC-BY-SA-4.0",
                "science": "REFERENCE_AND_EDITORIAL_LABELS_ONLY",
            }
        elif a.action == "evaluate":
            out = evaluate(bundle)
        else:
            out = analyse(bundle, a.form, excluded_text_id=a.exclude_text_id)
        print(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except (SourceError, ValueError, TypeError, OSError) as exc:
        print(f"LING-002 real scholarly reference refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
