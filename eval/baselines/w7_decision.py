"""Offline W7 EVAL-003 first-transport decision auditor; never calls a provider.

Checks an unapproved, non-executable research decision against independently
recorded source provenance and the planning-only canonical baseline suite.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "eval/baselines/w7_first_run_decision.json"
SOURCE = ROOT / "docs/research/R022_MET_LINKED_OBJECT_PILOT_DECISION.json"
SUITE = ROOT / "eval/baselines/suite.yaml"
CANDIDATES = ROOT / "eval/baselines/w6_provider_candidates.json"

MODEL_IDS = {
    "openai-frontier": ("gpt-6-luna", "https://developers.openai.com", "https://developers.openai.com", 0.10, 0.50),
    "anthropic-frontier": ("claude-sonnet-5-5", "https://platform.claude.com", "https://platform.claude.com", 2.00, 10.00),
    "google-frontier": ("gemini-3.8-flash", "https://ai.google.dev", "https://ai.google.dev", 0.75, 3.75),
}


def load() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        json.loads(DECISION.read_text(encoding="utf-8")),
        json.loads(SOURCE.read_text(encoding="utf-8")),
        yaml.safe_load(SUITE.read_text(encoding="utf-8")),
        json.loads(CANDIDATES.read_text(encoding="utf-8")),
    )


def audit(decision: Any, source: Any, suite: Any, catalog: Any) -> list[str]:
    errors: list[str] = []
    if any(not isinstance(x, dict) for x in (decision, source, suite, catalog)):
        return ["decision/source/suite/candidate documents must be mappings"]
    if decision.get("schema_version") != "1.0.0" or decision.get("decision_id") != "EVAL003-W7-TRANSPORT-THEN-REAL-PUBLIC-RUN":
        errors.append("unexpected W7 decision contract")
    if source.get("research_id") != "R-022" or source.get("decision") != "PRIORITIZE_MET_561392;HOLD_MET_561345_IN_LINKED_GROUP":
        errors.append("R-022 source decision identity mismatch")
    if suite.get("status") != "planning" or catalog.get("can_execute") is not False:
        errors.append("canonically approved suite/provider access cannot be inferred from planning documents")
    if suite.get("execution_gate", {}).get("explicit_user_permission_for_paid_inference") is not False:
        errors.append("user paid API authorization is missing")
    for name in ("execution_authorized", "payment_authorized", "api_credentials_verified", "private_capture_vault_verified",
                 "source_image_bytes_verified", "source_gold_licence_verified", "official_public_benchmark_item_manifest_frozen",
                 "official_prompt_bytes_frozen", "formal_run_preregistered", "provider_account_model_access_tested"):
        if decision.get(name) is not False:
            errors.append(f"unverified authority/operational gate {name} must remain false")
    for name in ("eligible_paid_api_calls", "actual_provider_calls", "actual_source_images_sent", "actual_scored_hieratic_predictions"):
        if decision.get(name) != 0 or isinstance(decision.get(name), bool):
            errors.append(f"documentary research cannot claim actual API activity: {name}")
    if decision.get("scientific_status") != "NOT_EXECUTED_NONCERTIFIABLE":
        errors.append("unverified science or certified result claimed")

    phases = decision.get("phases")
    if not isinstance(phases, list) or [p.get("name") for p in phases if isinstance(p, dict)] != ["P0", "P1"] or len(phases) != 2:
        errors.append("P0 owned fixture then P1 public evaluation must be explicit")
    else:
        p0, p1 = phases
        if (p0.get("source_kind"), p1.get("source_kind")) != ("locally_generated_owned_fixture", "pinned_official_public_eval_only"):
            errors.append("source roles in preflight phases changed")
        for p in phases:
            if p.get("source_item_id", None) is not None or p.get("source_image_sha256") is not None:
                errors.append("image/item identity supplied before verified controlled custody")
            if p.get("max_images") != 1 or p.get("max_attempts") != 1:
                errors.append("unapproved expansion beyond a single preflight attempt")
            if p.get("metrics_allowed") is not False or p.get("hieratic_score_claim_allowed") is not False:
                errors.append("transport pilots cannot generate Hieratic accuracy claims")
            if p.get("estimated_cost_usd") is not None or p.get("substitution_allowed") is not False:
                errors.append("pre-authorized bill/substitute must remain null/disabled")
            if not str(p.get("status", "")).startswith("AWAITING_"):
                errors.append("pilot phase claims execution readiness")

    prov = decision.get("candidate_providers")
    if not isinstance(prov, list) or len(prov) != 3:
        errors.append("provider candidates must remain exactly 3 documentary options")
    else:
        keys = set()
        for p in prov:
            if not isinstance(p, dict):
                errors.append("provider record invalid")
                continue
            key = p.get("key")
            keys.add(key)
            expected = MODEL_IDS.get(key)
            if not expected:
                errors.append("unreviewed provider key")
                continue
            model_id, model_doc_prefix, pricing_doc_prefix, input_rate, output_rate = expected
            if p.get("id") != model_id or not str(p.get("model_doc", "")).startswith(model_doc_prefix + "/") or not str(p.get("pricing_doc", "")).startswith(pricing_doc_prefix + "/"):
                errors.append(f"model ID or first-party pricing/model source mismatch: {key}")
            if p.get("input_usd_per_million_tokens") != input_rate or p.get("output_usd_per_million_tokens") != output_rate:
                errors.append(f"quoted published default model rate drift; refresh official pricing: {key}")
            if p.get("verify_current_rate_before_spend") is not True:
                errors.append(f"provider {key} may not charge an assumed stale quote")
        if keys != set(MODEL_IDS):
            errors.append("candidate provider keys are incomplete")

    policy = decision.get("cost_policy")
    if not isinstance(policy, dict):
        errors.append("price and usage custody policy missing")
    else:
        for name in ("max_total_spend_usd", "provider_image_token_count_actual", "provider_thinking_token_count_actual"):
            if policy.get(name) is not None:
                errors.append("cost/usage budget field cannot be filled by public documentation alone: " + name)
        if policy.get("no_spend_estimate_until_image_dimensions_token_count_and_account_rate_verified") is not True or policy.get("credits_or_free_tier_assumed") is not False:
            errors.append("uncounted image tokens/free credits being treated as an agreed estimate")
    guard = decision.get("source_guard")
    chosen = source.get("primary_candidate", {})
    companion = source.get("linked_group", {})
    if not isinstance(guard, dict) or not isinstance(chosen, dict) or not isinstance(companion, dict):
        errors.append("Met source evidence contracts missing")
    else:
        if chosen.get("object_id") != 561392 or chosen.get("accession") != "09.184.751":
            errors.append("preferred Met first source changed without independent audit")
        if set(companion.get("object_ids", [])) != {561345, 561369} or companion.get("relation_verified_from_primary_museum_page") is not True:
            errors.append("Met explicit companion object link not carried into source control")
        if guard.get("first_original_pilot_met_id") != 561392 or set(guard.get("met_associated_companion_ids", [])) != {561345, 561369}:
            errors.append("linked Met object contamination group absent")
        if guard.get("original_met_image_bytes_in_repo") is not False or guard.get("same_support_group_independence_verified") is not False or guard.get("r017_literal_screen_only_not_clearance") is not True:
            errors.append("source pixels/benchmark independence falsely promoted")
        if guard.get("sources_eligible_for_training") != 0:
            errors.append("source metadata falsely promoted to corpus")
    if source.get("newly_validated_image_line_pairs") != 0 or source.get("owner_authorized_outreach") is not False or source.get("institution_contacted") is not False:
        errors.append("false specialist engagement or image/line scientific evidence")
    if not isinstance(decision.get("required_owner_actions"), list) or len(decision["required_owner_actions"]) < 6:
        errors.append("explicit external owner gates omitted")
    return sorted(set(errors))


def main() -> int:
    try:
        results = load()
        errors = audit(*results)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"W7 first-run decision REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if errors:
        for err in errors:
            print(f"W7 first-run decision REFUSED: {err}", file=sys.stderr)
        return 1
    print(json.dumps({
        "classification": "documentary_preflight_noncertifiable",
        "source_rank_1": "Met 561392/09.184.751",
        "linked_group_blocked": "Met 561345/09.184.703 + 561369/09.184.728",
        "candidate_provider_count": 3,
        "execution_authorized": False,
        "actual_provider_calls": 0,
        "actual_eligible_image_line_pairs": 0,
        "next_stage": "owner-approved one-owned-image actual transport smoke, then separately frozen public-only science",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
