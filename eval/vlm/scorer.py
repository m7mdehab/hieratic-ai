"""Scoring engine and uncertainty quantification for VLM baseline evaluations.

Reuses official HieraticBench and project-stage metric formulas (accuracy, CER, WER, BLEU, chrF)
with explicit abstention rates, selective risk, and non-parametric bootstrap confidence intervals.
"""
from __future__ import annotations

from collections import Counter
import math
import random
import re
from typing import Any, Sequence


class ScorerError(ValueError):
    """Raised when scoring fails due to invalid data or missing gold."""
    pass


def levenshtein_distance(seq1: Sequence[Any], seq2: Sequence[Any]) -> int:
    """Compute standard Levenshtein edit distance between two sequences."""
    n1, n2 = len(seq1), len(seq2)
    if n1 == 0:
        return n2
    if n2 == 0:
        return n1

    prev_row = list(range(n2 + 1))
    for i, c1 in enumerate(seq1):
        curr_row = [i + 1] * (n2 + 1)
        for j, c2 in enumerate(seq2):
            cost = 0 if c1 == c2 else 1
            curr_row[j + 1] = min(
                curr_row[j] + 1,       # insertion
                prev_row[j + 1] + 1,   # deletion
                prev_row[j] + cost,    # substitution
            )
        prev_row = curr_row
    return prev_row[n2]


def character_error_rate(ref: str, hyp: str) -> float:
    """Compute character error rate: distance / len(ref)."""
    ref_chars = list(ref.strip())
    hyp_chars = list(hyp.strip())
    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0
    dist = levenshtein_distance(ref_chars, hyp_chars)
    return dist / len(ref_chars)


def word_error_rate(ref: str, hyp: str) -> float:
    """Compute word error rate: distance / len(ref_words)."""
    ref_words = ref.strip().split()
    hyp_words = hyp.strip().split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    dist = levenshtein_distance(ref_words, hyp_words)
    return dist / len(ref_words)


def extract_ngrams(tokens: list[str], n: int) -> Counter[tuple[str, ...]]:
    """Extract token n-grams and their frequencies."""
    return Counter(tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1))


def sentence_bleu(ref: str, hyp: str, max_n: int = 4) -> float:
    """Compute sentence-level BLEU with smoothing and brevity penalty."""
    ref_tokens = ref.strip().lower().split()
    hyp_tokens = hyp.strip().lower().split()

    if not hyp_tokens:
        return 0.0
    if not ref_tokens:
        return 0.0

    hyp_len = len(hyp_tokens)
    ref_len = len(ref_tokens)

    # Brevity penalty
    if hyp_len > ref_len:
        bp = 1.0
    else:
        bp = math.exp(1.0 - (ref_len / hyp_len)) if hyp_len > 0 else 0.0

    precisions: list[float] = []
    for n in range(1, max_n + 1):
        hyp_ngrams = extract_ngrams(hyp_tokens, n)
        ref_ngrams = extract_ngrams(ref_tokens, n)
        total_hyp_ngrams = max(0, hyp_len - n + 1)

        if total_hyp_ngrams == 0:
            break

        clipped_matches = sum(min(count, ref_ngrams.get(ng, 0)) for ng, count in hyp_ngrams.items())
        # Add-1 smoothing for zero counts
        smoothed_precision = (clipped_matches + 1.0) / (total_hyp_ngrams + 1.0)
        precisions.append(smoothed_precision)

    if not precisions:
        return 0.0

    geom_mean = math.exp(sum(math.log(p) for p in precisions) / len(precisions))
    return round(bp * geom_mean, 4)


def chrf_score(ref: str, hyp: str, char_order: int = 6, beta: float = 2.0) -> float:
    """Compute character n-gram F-score (chrF)."""
    ref_chars = list(ref.strip().lower().replace(" ", ""))
    hyp_chars = list(hyp.strip().lower().replace(" ", ""))

    if not ref_chars or not hyp_chars:
        return 0.0

    total_f = 0.0
    count = 0
    for n in range(1, char_order + 1):
        ref_ngrams = Counter(tuple(ref_chars[i:i + n]) for i in range(len(ref_chars) - n + 1))
        hyp_ngrams = Counter(tuple(hyp_chars[i:i + n]) for i in range(len(hyp_chars) - n + 1))

        hyp_total = sum(hyp_ngrams.values())
        ref_total = sum(ref_ngrams.values())

        if hyp_total == 0 or ref_total == 0:
            continue

        matches = sum(min(cnt, ref_ngrams.get(ng, 0)) for ng, cnt in hyp_ngrams.items())
        prec = matches / hyp_total if hyp_total > 0 else 0.0
        rec = matches / ref_total if ref_total > 0 else 0.0

        if (prec + rec) > 0:
            b2 = beta ** 2
            f = ((1 + b2) * prec * rec) / ((b2 * prec) + rec)
            total_f += f
            count += 1

    return round(total_f / count, 4) if count > 0 else 0.0


def is_abstention(text: str | None) -> bool:
    """Check if model explicitly abstained from answering."""
    if not text:
        return False
    lower = text.strip().lower()
    abstention_cues = [
        "[abstain]",
        "uncertain",
        "i cannot determine",
        "illegible",
        "unidentifiable",
        "insufficient evidence",
    ]
    return any(cue in lower for cue in abstention_cues)


def clean_script_prediction(raw: str | None) -> str:
    """Extract canonical script label from raw output."""
    if not raw:
        return ""
    candidates = ["hieratic", "hieroglyphic", "demotic", "coptic"]
    lower = raw.lower()
    for c in candidates:
        if re.search(r"\b" + c + r"\b", lower):
            return c.capitalize()
    return raw.strip().split()[0] if raw.strip() else ""


def clean_sign_prediction(raw: str | None) -> str:
    """Extract Gardiner sign code from raw output."""
    if not raw:
        return ""
    match = re.search(r"\b([A-Z][0-9]{1,3}[a-z]?)\b", raw)
    if match:
        return match.group(1).upper()
    return raw.strip().upper()


def bootstrap_ci(
    values: list[float],
    n_resamples: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float]:
    """Compute non-parametric bootstrap confidence interval."""
    if not values:
        return (0.0, 0.0)
    if len(values) == 1:
        return (values[0], values[0])

    rng = random.Random(seed)
    n = len(values)
    means: list[float] = []
    for _ in range(n_resamples):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        means.append(sum(sample) / n)

    means.sort()
    lower_idx = int((alpha / 2.0) * n_resamples)
    upper_idx = int((1.0 - alpha / 2.0) * n_resamples) - 1
    return (round(means[lower_idx], 4), round(means[upper_idx], 4))


def score_manifest(
    manifest: dict[str, Any],
    gold_items: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compute evaluation report from run manifest and gold dictionary."""
    attempts = manifest.get("attempts", [])
    if not attempts:
        raise ScorerError("Manifest contains no attempts to score.")

    manifest_id = manifest["manifest_id"]
    model_key = manifest["model_key"]
    shot_mode = manifest["shot_mode"]
    coverage_rate = manifest["coverage_summary"]["coverage_rate"]

    by_rung: dict[str, list[dict[str, Any]]] = {}
    for a in attempts:
        by_rung.setdefault(a["rung"], []).append(a)

    scored_rungs: dict[str, Any] = {}

    for rung, rung_attempts in by_rung.items():
        primary_scores: list[float] = []
        abstained_count = 0
        secondary_accum: dict[str, list[float]] = {}

        for a in rung_attempts:
            item_id = a["item_id"]
            gold = gold_items.get(item_id)
            if not gold:
                continue

            raw_pred = a.get("raw_output")
            status = a.get("status")

            if status == "abstained" or is_abstention(raw_pred):
                abstained_count += 1
                primary_scores.append(0.0)
                continue

            if status != "success" or not raw_pred:
                primary_scores.append(0.0)
                continue

            if rung == "identify":
                gold_script = gold.get("script", "").capitalize()
                pred_script = clean_script_prediction(raw_pred)
                acc = 1.0 if (pred_script.lower() == gold_script.lower()) else 0.0
                primary_scores.append(acc)

            elif rung == "signs":
                gold_sign = gold.get("gardiner", "").upper()
                pred_sign = clean_sign_prediction(raw_pred)
                acc = 1.0 if (pred_sign == gold_sign) else 0.0
                primary_scores.append(acc)

            elif rung == "transliterate":
                gold_xlit = gold.get("transliteration", "")
                pred_xlit = a.get("cleaned_prediction") or raw_pred
                cer = character_error_rate(gold_xlit, pred_xlit)
                wer = word_error_rate(gold_xlit, pred_xlit)
                acc_proxy = max(0.0, 1.0 - cer)
                primary_scores.append(acc_proxy)
                secondary_accum.setdefault("cer", []).append(cer)
                secondary_accum.setdefault("wer", []).append(wer)

            elif rung == "translate":
                gold_trans = gold.get("translation", "")
                pred_trans = a.get("cleaned_prediction") or raw_pred
                bleu = sentence_bleu(gold_trans, pred_trans)
                chrf = chrf_score(gold_trans, pred_trans)
                primary_scores.append(bleu)
                secondary_accum.setdefault("chrf", []).append(chrf)

        sample_count = len(primary_scores)
        mean_score = round(sum(primary_scores) / sample_count, 4) if sample_count > 0 else 0.0
        ci_lower, ci_upper = bootstrap_ci(primary_scores) if sample_count > 0 else (0.0, 0.0)
        abstention_rate = round(abstained_count / sample_count, 4) if sample_count > 0 else 0.0

        metric_name = {
            "identify": "script_accuracy",
            "signs": "sign_accuracy",
            "transliterate": "character_accuracy",
            "translate": "sentence_bleu_4",
        }.get(rung, "accuracy")

        sec_metrics = {k: round(sum(v) / len(v), 4) for k, v in secondary_accum.items() if v}

        scored_rungs[rung] = {
            "primary_metric": metric_name,
            "primary_score": mean_score,
            "primary_ci_95": [ci_lower, ci_upper],
            "secondary_metrics": sec_metrics,
            "sample_count": sample_count,
            "abstention_rate": abstention_rate,
        }

    report = {
        "doc_type": "vlm_score_report",
        "schema_version": "1.0.0",
        "report_id": f"report_{manifest_id}",
        "manifest_id": manifest_id,
        "model_key": model_key,
        "shot_mode": shot_mode,
        "coverage_rate": coverage_rate,
        "rungs": scored_rungs,
    }
    return report


def compare_manifests(
    manifest_a: dict[str, Any],
    manifest_b: dict[str, Any],
    gold_items: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute paired statistical comparison between two manifests over identical items."""
    report_a = score_manifest(manifest_a, gold_items)
    report_b = score_manifest(manifest_b, gold_items)

    comparisons: list[dict[str, Any]] = []

    # Map attempts by item_id and rung
    attempts_a = {(a["item_id"], a["rung"]): a for a in manifest_a.get("attempts", [])}
    attempts_b = {(b["item_id"], b["rung"]): b for b in manifest_b.get("attempts", [])}

    common_keys = sorted(set(attempts_a.keys()) & set(attempts_b.keys()))
    by_rung_keys: dict[str, list[tuple[str, str]]] = {}
    for k in common_keys:
        by_rung_keys.setdefault(k[1], []).append(k)

    for rung, keys in by_rung_keys.items():
        scores_a: list[float] = []
        scores_b: list[float] = []
        deltas: list[float] = []

        metric_name = report_a["rungs"].get(rung, {}).get("primary_metric", "score")

        for item_id, _ in keys:
            gold = gold_items.get(item_id)
            if not gold:
                continue

            att_a = attempts_a[(item_id, rung)]
            att_b = attempts_b[(item_id, rung)]

            def eval_single(att: dict[str, Any]) -> float:
                if att.get("status") != "success":
                    return 0.0
                raw = att.get("raw_output")
                if not raw or is_abstention(raw):
                    return 0.0
                if rung == "identify":
                    return 1.0 if (clean_script_prediction(raw).lower() == gold.get("script", "").lower()) else 0.0
                elif rung == "signs":
                    return 1.0 if (clean_sign_prediction(raw) == gold.get("gardiner", "").upper()) else 0.0
                elif rung == "transliterate":
                    return max(0.0, 1.0 - character_error_rate(gold.get("transliteration", ""), att.get("cleaned_prediction") or raw))
                elif rung == "translate":
                    return sentence_bleu(gold.get("translation", ""), att.get("cleaned_prediction") or raw)
                return 0.0

            sa = eval_single(att_a)
            sb = eval_single(att_b)
            scores_a.append(sa)
            scores_b.append(sb)
            deltas.append(sb - sa)

        if not deltas:
            continue

        mean_a = round(sum(scores_a) / len(scores_a), 4)
        mean_b = round(sum(scores_b) / len(scores_b), 4)
        delta_mean = round(sum(deltas) / len(deltas), 4)
        ci_low, ci_high = bootstrap_ci(deltas)

        comparisons.append({
            "baseline_manifest_id": manifest_a["manifest_id"],
            "comparison_manifest_id": manifest_b["manifest_id"],
            "rung": rung,
            "metric": metric_name,
            "baseline_score": mean_a,
            "comparison_score": mean_b,
            "score_delta": delta_mean,
            "paired_samples": len(deltas),
            "ci_95_delta": [ci_low, ci_high],
        })

    return comparisons
