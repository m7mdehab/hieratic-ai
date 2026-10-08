"""W6 EVAL-003: offline public-only metadata + provider documentary readiness audit.

No provider SDK, image loading, benchmark gold, API key, network request, or
permission grant. This reports blockers only; NEVER authorizes execution.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "eval/baselines/w6_provider_candidates.json"
SUITE = ROOT / "eval/baselines/suite.yaml"
PUBLIC_METADATA = ROOT / "docs/research/R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl"
PINNED_BENCHMARK = "d587dc990013f18007f1e7a8f56f96ff2f7127e2"
EXPECTED_MODELS = {
    "openai-frontier": ("openai", "gpt-6-luna", "developers.openai.com", "api.openai.com"),
    "anthropic-frontier": ("anthropic", "claude-sonnet-5-5", "platform.claude.com", "api.anthropic.com"),
    "google-frontier": ("google", "gemini-3.8-flash", "ai.google.dev", "generativelanguage.googleapis.com"),
}
SOURCE_GROUPS = {"aku": 150, "cbl": 16, "met": 37, "wm": 61, "ypm": 2}
PUBLIC_RECORD_KEYS = {
    "id", "upstream_path", "object_name", "object_holder", "source_url",
    "source_file_url", "license_claim", "source_group", "provenance_review",
    "corpus_status",
}

class ReadinessError(ValueError):
    pass


def read_snapshot(catalog_path: Path = CATALOG,
                  suite_path: Path = SUITE,
                  metadata_path: Path = PUBLIC_METADATA) -> tuple[dict[str, Any], dict[str, Any], list[Any]]:
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        suite = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
        rows = [json.loads(s) for s in metadata_path.read_text(encoding="utf-8").splitlines() if s.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ReadinessError(f"W6 evidence snapshot is missing or malformed: {exc}") from exc
    return catalog, suite, rows


def _host(url: Any) -> str | None:
    if not isinstance(url, str):
        return None
    parsed = urlparse(url)
    return parsed.hostname if parsed.scheme == "https" and not parsed.username and not parsed.password else None


def validate_snapshot(catalog: Any, suite: Any, rows: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(catalog, dict) or not isinstance(suite, dict) or not isinstance(rows, list):
        return ["catalogue, suite and metadata must be mappings/mapping/list"]
    if catalog.get("schema_version") != "1.0.0" or catalog.get("benchmark_sha") != PINNED_BENCHMARK:
        errors.append("W6 catalogue benchmark/version drift")
    for flag in ("documentary_evidence_only", "all_current_model_ids_must_remain_candidate_only", "sealed_excluded"):
        if catalog.get(flag) is not True:
            errors.append(f"documentary / quarantine flag {flag} is missing")
    for flag in ("can_execute", "externally_authorized", "provider_credentials_verified", "prices_quoted_for_full_images"):
        if catalog.get(flag) is not False:
            errors.append(f"catalogue must not assert execution/permission/price: {flag}")
    if catalog.get("provider_calls") != 0:
        errors.append("documentary research cannot claim provider execution")
    if catalog.get("scorer_status") != "PINNED_SYNTHETIC_REPLAY_ONLY_NO_REAL_RESULTS":
        errors.append("official scorer is being promoted without actual verified model calls")
    expected_total = 266
    if catalog.get("official_public_items_expected") != expected_total or catalog.get("rung_counts") != {"identify": 116, "signs": 150}:
        errors.append("reported public benchmark population was changed")
    if catalog.get("planned_attempts_full_266_by_3_models_by_3_samples") != 2394:
        errors.append("proposed attempted denominator drifted")

    models = catalog.get("models")
    if not isinstance(models, list):
        errors.append("models catalogue must be an array")
        models = []
    found: set[str] = set()
    for idx, model in enumerate(models):
        if not isinstance(model, dict):
            errors.append(f"model {idx} is not an object")
            continue
        key = model.get("key")
        if key in found:
            errors.append(f"duplicate candidate model key {key}")
        found.add(key)
        approved = EXPECTED_MODELS.get(key)
        if not approved:
            errors.append(f"unreviewed candidate model key {key}")
            continue
        provider, model_id, spec_host, api_host = approved
        if (model.get("provider"), model.get("model_id")) != (provider, model_id):
            errors.append(f"candidate model ID/provider mismatch: {key}")
        if _host(model.get("model_spec_url")) != spec_host or _host(model.get("vision_spec_url")) != spec_host:
            errors.append(f"candidate spec evidence URL is not on verified primary domain: {key}")
        if _host(model.get("api_route")) != api_host:
            errors.append(f"candidate API route host mismatch: {key}")
        for required in ("model_id_verified_from_official_docs", "image_input_verified_from_official_docs"):
            if model.get(required) is not True:
                errors.append(f"{key}: official documentary verification absent: {required}")
        if model.get("model_access_verified_in_user_account") is not False or model.get("raw_api_execution_occurred") is not False:
            errors.append(f"{key}: access/execution not independently verified")
        if model.get("model_status") != "candidate_documented_not_executed":
            errors.append(f"{key}: candidate claims runtime results")
        if model.get("effort_selection_status") != "requires_protocol_freeze_and_comparison_review":
            errors.append(f"{key}: effort setting bypasses pre-registration")
    if found != set(EXPECTED_MODELS):
        errors.append("candidate model provider cohort incomplete")

    if suite.get("status") != "planning":
        errors.append("W6 documentary snapshot requires canonical baseline suite planning-only")
    if suite.get("official_benchmark", {}).get("commit") != PINNED_BENCHMARK:
        errors.append("suite benchmark commit differs from pinned source")
    if suite.get("official_prompts", {}).get("commit") != PINNED_BENCHMARK:
        errors.append("suite official prompt commit differs from pinned source")
    if suite.get("official_benchmark", {}).get("item_manifest_sha256") is not None:
        errors.append("W6 catalogue must not silently imply a real frozen inference item manifest")
    if suite.get("official_prompts", {}).get("exact_prompt_bundle_sha256") is not None:
        errors.append("W6 catalogue must not silently imply an approved original prompt bundle")
    if any(v is True for k, v in suite.get("execution_gate", {}).items() if k != "offline_scorer_parity_confirmed"):
        errors.append("suite has a forbidden execution authorization flag")
    if suite.get("execution_gate", {}).get("max_total_spend_usd") is not None:
        errors.append("suite has an unexpected approved spend")
    suite_models = {m.get("key"): m for m in suite.get("models", []) if isinstance(m, dict)}
    if set(suite_models) != set(EXPECTED_MODELS):
        errors.append("canonical suite comparison providers differ")
    if any(x.get("provider_model_id") is not None or x.get("api_route") is not None for x in suite_models.values()):
        errors.append("research model options must not mutate pre-registered suite IDs or routes")

    ids: set[str] = set()
    groups: Counter[str] = Counter()
    if len(rows) != expected_total:
        errors.append(f"public metadata count {len(rows)} differs from 266")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"public row {idx} is not mapping")
            continue
        if set(row) != PUBLIC_RECORD_KEYS:
            errors.append(f"public row {idx} includes unauthorized data or gold-bearing fields")
        iid = row.get("id")
        if not isinstance(iid, str) or iid.startswith("hb-") or iid in ids:
            errors.append(f"sealed/duplicate/invalid public source ID at {idx}")
        ids.add(iid)
        group = row.get("source_group")
        if group not in SOURCE_GROUPS or not isinstance(iid, str) or not iid.startswith(f"{group}-"):
            errors.append(f"source family inconsistent for {iid}")
        groups[group] += 1
        if row.get("provenance_review") != "metadata_only" or row.get("corpus_status") != "QUARANTINE_EVAL_ONLY":
            errors.append(f"source metadata {iid} incorrectly promoted or dequarantined")
        if _host(row.get("source_url")) is None or _host(row.get("source_file_url")) is None:
            errors.append(f"public source {iid} has invalid URL evidence")
    if dict(groups) != SOURCE_GROUPS:
        errors.append(f"public source family totals do not match the pinned census: {dict(groups)}")
    return sorted(set(errors))


def build_readiness(catalog: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "classification": "documentary_preflight_noncertifiable",
        "benchmark_sha": PINNED_BENCHMARK,
        "metadata_only_public_items": len(rows),
        "source_families": dict(sorted(Counter(x["source_group"] for x in rows).items())),
        "identify_source_identity_count": sum(x["source_group"] != "aku" for x in rows),
        "sign_source_identity_count": sum(x["source_group"] == "aku" for x in rows),
        "candidate_model_ids": {x["provider"]: x["model_id"] for x in catalog["models"]},
        "eligible_scientific_evaluation_items": 0,
        "provider_calls_observed": 0,
        "model_scores_observed": 0,
        "execution_authorized": False,
        "all_corpus_training_admission_blocked": True,
        "owner_required_next_gates": list(catalog["shared_blockers"]),
        "official_scoring_status": "PINNED_SYNTHETIC_REPLAY_ONLY_NO_REAL_RESULTS",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--suite", type=Path, default=SUITE)
    parser.add_argument("--metadata", type=Path, default=PUBLIC_METADATA)
    args = parser.parse_args(argv)
    try:
        catalog, suite, metadata = read_snapshot(args.catalog, args.suite, args.metadata)
        errors = validate_snapshot(catalog, suite, metadata)
    except (ReadinessError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    if errors:
        for err in errors:
            print(f"REFUSED: {err}", file=sys.stderr)
        return 1
    print(json.dumps(build_readiness(catalog, metadata), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
