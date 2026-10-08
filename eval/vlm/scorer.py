"""Scoring engine and uncertainty quantification for VLM baseline evaluations.

Implements dual-channel evaluation:
1. Official HieraticBench Scorer channel (authoritative: upstream TypeScript bench/src/score.ts)
2. Project-Native EVAL-001 Diagnostics (explicitly labeled in-house metrics from eval/metric_contract.yaml)

Enforces EVAL-006 statistical standards:
- At least 2,000 document-clustered bootstrap resamples (B=2000).
- Explicit null confidence intervals for single or zero document clusters (rejects fabricated 0-width CIs).
- Composite-key pairing across (item_id, rung, sample_index).
- Full denominator accounting: intention-to-test and conditional scores with explicit failure and abstention rates.
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


def document_clustered_bootstrap_ci(
    items_by_cluster: dict[str, list[float]],
    n_resamples: int = 2000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[tuple[float, float] | None, int, str]:
    """Compute non-parametric document-clustered bootstrap confidence interval (EVAL-006 standard).

    Returns:
        (ci_bounds, cluster_count, status_str)
        If cluster_count <= 1, ci_bounds is None and status is 'insufficient_document_clusters'.
    """
    cluster_ids = list(items_by_cluster.keys())
    cluster_count = len(cluster_ids)

    # Reject fabricated zero-width intervals for single or zero clusters
    if cluster_count <= 1:
        return (None, cluster_count, "insufficient_document_clusters")

    rng = random.Random(seed)
    resample_means: list[float] = []

    for _ in range(n_resamples):
        sampled_clusters = [cluster_ids[rng.randint(0, cluster_count - 1)] for _ in range(cluster_count)]
        sampled_values: list[float] = []
        for cid in sampled_clusters:
            sampled_values.extend(items_by_cluster[cid])

        if sampled_values:
            resample_means.append(sum(sampled_values) / len(sampled_values))
        else:
            resample_means.append(0.0)

    resample_means.sort()
    low_idx = int((alpha / 2.0) * n_resamples)
    high_idx = int((1.0 - alpha / 2.0) * n_resamples) - 1

    return (
        (round(resample_means[low_idx], 4), round(resample_means[high_idx], 4)),
        cluster_count,
        "valid_clustered_ci",
    )


def score_manifest(
    manifest: dict[str, Any],
    gold_items: dict[str, dict[str, Any]],
    official_replay_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute structured evaluation report with explicit channel separation and clustered uncertainty."""
    attempts = manifest.get("attempts", [])
    if not attempts:
        raise ScorerError("Manifest contains no attempts to score.")

    manifest_id = manifest["manifest_id"]
    model_key = manifest["model_key"]
    shot_mode = manifest["shot_mode"]
    execution_tier = manifest.get("execution_tier", "synthetic_ci_fixture")
    scientific_validity = manifest.get("scientific_validity", "non_scientific_test_fixture")
    cert_status = manifest.get("certification_status", "uncertified_synthetic_only")

    by_rung: dict[str, list[dict[str, Any]]] = {}
    for a in attempts:
        by_rung.setdefault(a["rung"], []).append(a)

    project_native_rungs: dict[str, Any] = {}

    for rung, rung_attempts in by_rung.items():
        total_scheduled = len(rung_attempts)
        total_attempted = total_scheduled

        success_count = sum(1 for a in rung_attempts if a["status"] == "success")
        abstention_count = sum(1 for a in rung_attempts if a["status"] == "abstained")
        failure_count = sum(1 for a in rung_attempts if a["status"] == "failed")
        timeout_count = sum(1 for a in rung_attempts if a["status"] == "timeout")
        refusal_count = sum(1 for a in rung_attempts if a["status"] == "refused")

        # Cluster attempts by document_id
        cluster_intention_scores: dict[str, list[float]] = {}
        conditional_scores: list[float] = []
        secondary_accum: dict[str, list[float]] = {}

        for a in rung_attempts:
            item_id = a["item_id"]
            doc_id = a.get("document_id") or item_id.rsplit("-", 1)[0]
            gold = gold_items.get(item_id)
            if not gold:
                continue

            raw_pred = a.get("raw_output")
            status = a.get("status")

            # Score computation for project-native metrics
            if status != "success" or not raw_pred or is_abstention(raw_pred):
                # Intention-to-test scores failure/abstention as 0.0
                cluster_intention_scores.setdefault(doc_id, []).append(0.0)
                continue

            # Valid response scoring
            score_val = 0.0
            if rung == "identify":
                gold_script = gold.get("script", "").capitalize()
                pred_script = clean_script_prediction(raw_pred)
                score_val = 1.0 if (pred_script.lower() == gold_script.lower()) else 0.0

            elif rung == "signs":
                gold_sign = gold.get("gardiner", "").upper()
                pred_sign = clean_sign_prediction(raw_pred)
                score_val = 1.0 if (pred_sign == gold_sign) else 0.0

            elif rung == "transliterate":
                gold_xlit = gold.get("transliteration", "")
                pred_xlit = a.get("cleaned_prediction") or raw_pred
                cer = character_error_rate(gold_xlit, pred_xlit)
                wer = word_error_rate(gold_xlit, pred_xlit)
                score_val = max(0.0, 1.0 - cer)
                secondary_accum.setdefault("cer", []).append(round(cer, 4))
                secondary_accum.setdefault("wer", []).append(round(wer, 4))

            elif rung == "translate":
                gold_trans = gold.get("translation", "")
                pred_trans = a.get("cleaned_prediction") or raw_pred
                bleu = sentence_bleu(gold_trans, pred_trans)
                chrf = chrf_score(gold_trans, pred_trans)
                score_val = bleu
                secondary_accum.setdefault("chrf", []).append(round(chrf, 4))

            cluster_intention_scores.setdefault(doc_id, []).append(score_val)
            conditional_scores.append(score_val)

        # Flat values across all clusters for intention-to-test mean
        all_intent = [s for cluster_vals in cluster_intention_scores.values() for s in cluster_vals]
        intent_mean = round(sum(all_intent) / len(all_intent), 4) if all_intent else 0.0
        cond_mean = round(sum(conditional_scores) / len(conditional_scores), 4) if conditional_scores else None

        # 2,000 document-clustered bootstrap resamples (EVAL-006 standard)
        ci_bounds, cluster_cnt, ci_status = document_clustered_bootstrap_ci(
            cluster_intention_scores,
            n_resamples=2000,
            alpha=0.05,
        )

        cov_rate = round(success_count / total_scheduled, 4) if total_scheduled > 0 else 0.0
        abst_rate = round(abstention_count / total_scheduled, 4) if total_scheduled > 0 else 0.0

        metric_id = {
            "identify": "SCRIPT_ACC",
            "signs": "SIGN_ACC",
            "transliterate": "CER_V1",
            "translate": "TRANSLATION_BLEU_4",
        }.get(rung, "ACCURACY")

        sec_metrics = {k: round(sum(v) / len(v), 4) for k, v in secondary_accum.items() if v}

        project_native_rungs[rung] = {
            "primary_metric_id": metric_id,
            "intention_to_test_score": intent_mean,
            "conditional_score": cond_mean,
            "cluster_bootstrap_ci_95": list(ci_bounds) if ci_bounds else None,
            "cluster_count": cluster_cnt,
            "cluster_ci_status": ci_status,
            "total_scheduled": total_scheduled,
            "total_attempted": total_attempted,
            "success_count": success_count,
            "abstention_count": abstention_count,
            "failure_count": failure_count,
            "timeout_count": timeout_count,
            "refusal_count": refusal_count,
            "coverage_rate": cov_rate,
            "abstention_rate": abst_rate,
            "secondary_metrics": sec_metrics,
        }

    report = {
        "doc_type": "vlm_score_report",
        "schema_version": "1.0.0",
        "report_id": f"report_{manifest_id}",
        "manifest_id": manifest_id,
        "execution_tier": execution_tier,
        "scientific_validity": scientific_validity,
        "certification_status": cert_status,
        "scoring_channel": "dual_channel_comparison" if official_replay_summary else "project_native_eval001",
        "official_hieraticbench": official_replay_summary,
        "model_key": model_key,
        "shot_mode": shot_mode,
        "coverage_rate": manifest["coverage_summary"]["coverage_rate"],
        "project_native_eval001": project_native_rungs,
    }
    return report


def compare_manifests(
    manifest_a: dict[str, Any],
    manifest_b: dict[str, Any],
    gold_items: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute paired statistical comparison pairing attempts strictly across (item_id, rung, sample_index).

    Follows EVAL-006 clustered resampling over document clusters.
    """
    # Key attempts on composite identity: (item_id, rung, sample_index)
    attempts_a = {(a["item_id"], a["rung"], a.get("sample_index", 0)): a for a in manifest_a.get("attempts", [])}
    attempts_b = {(b["item_id"], b["rung"], b.get("sample_index", 0)): b for b in manifest_b.get("attempts", [])}

    common_composite_keys = sorted(set(attempts_a.keys()) & set(attempts_b.keys()))
    by_rung_keys: dict[str, list[tuple[str, str, int]]] = {}
    for k in common_composite_keys:
        by_rung_keys.setdefault(k[1], []).append(k)

    comparisons: list[dict[str, Any]] = []

    for rung, composite_keys in by_rung_keys.items():
        cluster_deltas: dict[str, list[float]] = {}
        scores_a_all: list[float] = []
        scores_b_all: list[float] = []

        metric_id = {
            "identify": "SCRIPT_ACC",
            "signs": "SIGN_ACC",
            "transliterate": "CER_V1",
            "translate": "TRANSLATION_BLEU_4",
        }.get(rung, "SCORE")

        for item_id, _, s_idx in composite_keys:
            gold = gold_items.get(item_id)
            if not gold:
                continue

            att_a = attempts_a[(item_id, rung, s_idx)]
            att_b = attempts_b[(item_id, rung, s_idx)]
            doc_id = att_a.get("document_id") or att_b.get("document_id") or item_id.rsplit("-", 1)[0]

            def eval_attempt(att: dict[str, Any]) -> float:
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

            sa = eval_attempt(att_a)
            sb = eval_attempt(att_b)
            delta = sb - sa

            scores_a_all.append(sa)
            scores_b_all.append(sb)
            cluster_deltas.setdefault(doc_id, []).append(delta)

        if not scores_a_all:
            continue

        mean_a = round(sum(scores_a_all) / len(scores_a_all), 4)
        mean_b = round(sum(scores_b_all) / len(scores_b_all), 4)
        all_deltas = [d for dlist in cluster_deltas.values() for d in dlist]
        delta_mean = round(sum(all_deltas) / len(all_deltas), 4)

        # Clustered bootstrap over document clusters
        ci_bounds, cluster_cnt, ci_status = document_clustered_bootstrap_ci(
            cluster_deltas,
            n_resamples=2000,
            alpha=0.05,
        )

        comparisons.append({
            "baseline_manifest_id": manifest_a["manifest_id"],
            "comparison_manifest_id": manifest_b["manifest_id"],
            "rung": rung,
            "metric_id": metric_id,
            "composite_pairing": True,
            "baseline_score": mean_a,
            "comparison_score": mean_b,
            "score_delta": delta_mean,
            "paired_samples": len(all_deltas),
            "delta_cluster_ci_95": list(ci_bounds) if ci_bounds else None,
            "delta_ci_status": ci_status,
        })

    return comparisons
