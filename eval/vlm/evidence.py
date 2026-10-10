"""Cryptographically Bound VLM Evidence Manifest Generator & Verifier.

Produces and verifies publicly safe, redacted evidence manifests from local or
hosted private attempt ledgers, enabling independent audit without leaking
private weights, raw source image pixels, or restricted publisher texts.

Enforces:
- Cryptographic binding between attempt ledger, protocol fingerprint, and model weights
- Accounting invariant conservation: planned = attempted + skipped, attempted = succeeded + failed
- Redaction of private image pixels and proprietary raw outputs into SHA-256 hashes
- Attribution and physical witness tracking across all evaluated stimuli
- Independent verification without requiring local model weights or GPU hardware
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from eval.vlm.hieratic import PINNED_MODEL_ID, PINNED_REVISION, RECORDED_WEIGHT_SHA256
from eval.vlm.ledger import verify_ledger_file_integrity
from eval.vlm.signs import (
    FROZEN_DOMAIN_BLIND_PROMPT_W27,
    FROZEN_DOMAIN_BLIND_PROMPT_W27_SHA256,
    FROZEN_LEADING_IDENT_PROMPT_W27,
    FROZEN_LEADING_IDENT_PROMPT_W27_SHA256,
    FROZEN_SCRIPT_AWARE_PROMPT_W27,
    FROZEN_SCRIPT_AWARE_PROMPT_W27_SHA256,
    PROTOCOL_VERSION_W27,
    W19_PINNED_MEDIA,
    W27_CONTROLS_METADATA,
    compute_w27_sign_protocol_hash,
)

EVIDENCE_MANIFEST_SCHEMA_VERSION = "1.1.0"


def generate_vlm_evidence_manifest(
    ledger_path: Path | str,
    *,
    report_path: Path | str | None = None,
    execution_tier: str = "agent_local_attested",
    output_path: Path | str | None = None,
    host_notes: str | None = None,
) -> dict[str, Any]:
    """Generate a publicly safe, redacted, cryptographically bound evidence manifest.

    Reads the private durable attempt ledger and optional report, verifies all
    internal consistency checks and accounting equations, redacts proprietary texts
    into output SHA-256 hashes, and returns/saves the evidence manifest.
    """
    l_path = Path(ledger_path).resolve()
    if not l_path.is_file():
        raise FileNotFoundError(f"Ledger file not found: {l_path}")

    # Audit ledger integrity
    audit = verify_ledger_file_integrity(l_path, allow_incomplete=False)
    if not audit["valid"]:
        raise ValueError("Ledger failed integrity audit: " + "; ".join(audit["errors"][:5]))

    ledger_bytes = l_path.read_bytes()
    ledger_sha256 = hashlib.sha256(ledger_bytes).hexdigest()

    # Parse ledger events
    dispatches: dict[str, dict[str, Any]] = {}
    completions: dict[str, dict[str, Any]] = {}
    skips: dict[str, dict[str, Any]] = {}
    attempt_order: list[str] = []
    run_id: str | None = None
    protocol_fp: str | None = None

    for line in ledger_bytes.decode("utf-8").splitlines():
        cl = line.strip()
        if not cl:
            continue
        rec = json.loads(cl)
        rec_type = rec.get("record_type")
        att_id = rec.get("attempt_id")

        if run_id is None:
            run_id = rec.get("run_id")
        if protocol_fp is None and rec_type in ("dispatch", "skip"):
            protocol_fp = rec.get("protocol_fingerprint")

        if rec_type == "dispatch":
            dispatches[att_id] = rec
            if att_id not in attempt_order:
                attempt_order.append(att_id)
        elif rec_type == "completion":
            completions[att_id] = rec
        elif rec_type == "skip":
            skips[att_id] = rec
            if att_id not in attempt_order:
                attempt_order.append(att_id)

    # Validate accounting equations
    succeeded = sum(1 for c in completions.values() if c.get("status") == "success")
    failed = sum(1 for c in completions.values() if c.get("status") == "failed")
    skipped = len(skips)
    attempted = succeeded + failed
    total_attempts = len(attempt_order)
    planned = total_attempts

    if planned != (attempted + skipped):
        raise ValueError(f"Accounting invariant failed: planned ({planned}) != attempted ({attempted}) + skipped ({skipped})")

    # Build sanitized per-attempt evidence records (NO private text answers, only hashes and metadata)
    sanitized_attempts: list[dict[str, Any]] = []
    for att_id in attempt_order:
        disp = dispatches.get(att_id, {})
        comp = completions.get(att_id, {})
        skip = skips.get(att_id, {})

        if skip:
            sanitized_attempts.append({
                "attempt_id": att_id,
                "attempt_index": skip.get("attempt_index"),
                "status": "skipped",
                "target_or_control_id": skip.get("target_or_control_id"),
                "skip_reason": skip.get("skip_reason"),
            })
            continue

        raw_out = comp.get("output_text", "")
        out_sha = comp.get("output_sha256") or hashlib.sha256(raw_out.encode("utf-8")).hexdigest()

        sanitized_attempts.append({
            "attempt_id": att_id,
            "attempt_index": disp.get("attempt_index"),
            "attempt_category": disp.get("attempt_category"),
            "target_or_control_id": disp.get("target_or_control_id"),
            "physical_witness": disp.get("physical_witness"),
            "task": disp.get("task"),
            "rung": disp.get("rung"),
            "prompt_variant": disp.get("prompt_variant"),
            "prompt_sha256": disp.get("prompt_sha256"),
            "stimulus_sha256": disp.get("stimulus_sha256"),
            "stimulus_dimensions": disp.get("stimulus_dimensions"),
            "model_id": disp.get("model_id"),
            "model_revision": disp.get("model_revision"),
            "model_weight_sha256": disp.get("model_weight_sha256"),
            "status": comp.get("status"),
            "completed_at": comp.get("completed_at"),
            "latency_ms": comp.get("latency_ms", 0.0),
            "token_usage": comp.get("token_usage", {}),
            "output_sha256": out_sha,
            "error_category": comp.get("error_category", "none"),
        })

    # Optional report data integration
    report_data: dict[str, Any] = {}
    if report_path is not None:
        r_p = Path(report_path).resolve()
        if r_p.is_file():
            try:
                report_data = json.loads(r_p.read_text(encoding="utf-8"))
            except Exception:
                pass

    # Build cohort provenance manifest
    cohort_metadata: list[dict[str, Any]] = []
    for m in W19_PINNED_MEDIA:
        cohort_metadata.append({
            "target_id": f"sign_{m['sign_id']}_{m['media_classification']}_{m['media_index']}",
            "sign_id": m["sign_id"],
            "media_classification": m["media_classification"],
            "physical_witness": m["physical_witness"],
            "rights": "CC BY 4.0",
            "publisher_media_url": m["publisher_media_url"],
            "source_raw_sha256": m["expected_sha256"],
            "expected_byte_size": m["expected_byte_size"],
            "role": "diagnostic_media",
        })
    for c in W27_CONTROLS_METADATA:
        cohort_metadata.append({
            "target_id": c["control_id"],
            "media_classification": c["category_type"],
            "role": c["role"],
            "description": c["description"],
            "is_synthetic": c["is_synthetic"],
            "is_held_out_gold": False,
        })

    # An unverified runtime tier cannot authenticate original inference.
    evidence_grades = {
        "grade_a_multimodal_interface":{"status":"LOCAL_ATTESTATION_NOT_INDEPENDENTLY_REPLAYED","evidence":"Original media CPU execution is locally reported only"},
        "grade_b_fixture_tests":{"status":"NOT_VERIFIED_BY_MANIFEST","evidence":"Hosted fixture test may be separately validated on exact GitHub SHA"},
        "grade_c_real_weights_loaded":{"status":"AGENT_LOCAL_WEIGHT_HASH_REPORTED","evidence":"Safetensors original bytes are not in the public custody of the reviewer"},
        "grade_d_actual_sign_media_passes":{"status":"AGENT_LOCAL_COMPLETION_RECORDS_UNVERIFIED","evidence":f"{succeeded} locally recorded successes; {failed} failed including crash-interrupted unknown outcomes. No independent real-media forward replay."},
        "grade_e_visual_sensitivity_observed":{"status":"NOT_VERIFIED","evidence":"No independent blind authentic original visual-sensitivity proof"},
        "sign_level_diagnostic_cleared":{"status":"PROVISIONAL_METADATA_ONLY","evidence":"No independent original-witness adjudication"},
        "grade_f_authentic_hieratic_gold_evaluation":{"status":"STRICTLY_NO","evidence":"No independent held-out Egyptologist gold, 0/2 capability points"},
    }

    manifest: dict[str, Any] = {
        "doc_type": "vlm_evidence_manifest",
        "manifest_version": EVIDENCE_MANIFEST_SCHEMA_VERSION,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "task_id": "VLM-001",
        "execution_tier": execution_tier,
        "evidence_provenance": "SELF_REPORTED_PRIVATE_LEDGER_NOT_ORIGINAL_REPLAY",
        "scientific_capability_points": 0.0,
        "hieratic_reading_claim": False,
        "protocol": {
            "protocol_version": PROTOCOL_VERSION_W27,
            "protocol_fingerprint": protocol_fp or compute_w27_sign_protocol_hash(),
            "domain_blind_prompt_sha256": FROZEN_DOMAIN_BLIND_PROMPT_W27_SHA256,
            "script_aware_prompt_sha256": FROZEN_SCRIPT_AWARE_PROMPT_W27_SHA256,
            "leading_ident_prompt_sha256": FROZEN_LEADING_IDENT_PROMPT_W27_SHA256,
            "domain_blind_prompt_text": FROZEN_DOMAIN_BLIND_PROMPT_W27,
            "script_aware_prompt_text": FROZEN_SCRIPT_AWARE_PROMPT_W27,
            "leading_ident_prompt_text": FROZEN_LEADING_IDENT_PROMPT_W27,
        },
        "model_spec": {
            "model_id": PINNED_MODEL_ID,
            "revision": PINNED_REVISION,
            "weight_sha256": RECORDED_WEIGHT_SHA256,
            "weight_bytes": 513028808,
            "license": "Apache-2.0",
        },
        "ledger_audit": {
            "ledger_path_rel": l_path.name,
            "ledger_sha256": ledger_sha256,
            "original_ledger_available_in_public_repository": False,
            "original_ledger_replayed_by_public_verifier": False,
            "ledger_byte_size": len(ledger_bytes),
            "run_id": run_id,
            "audit_valid": True,
            "planned_count": planned,
            "attempted_count": attempted,
            "succeeded_count": succeeded,
            "failed_count": failed,
            "skipped_count": skipped,
        },
        "cohort_metadata": cohort_metadata,
        "attempts": sanitized_attempts,
        "evidence_grades": evidence_grades,
        "host_notes": host_notes or f"Execution tier: {execution_tier}",
    }

    # Deterministic self-hash
    manifest_bytes = json.dumps(manifest, sort_keys=True, indent=2).encode("utf-8")
    manifest["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()

    if output_path is not None:
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return manifest


def verify_vlm_evidence_manifest(manifest_path: Path | str) -> dict[str, Any]:
    """Independently audit and verify a VLM evidence manifest without needing model weights or images."""
    p = Path(manifest_path).resolve()
    if not p.is_file():
        return {"valid": False, "errors": [f"Manifest file not found: {p}"]}

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"valid": False, "errors": [f"Manifest JSON parse error: {exc}"]}

    errors: list[str] = []

    # Canonical self-hash provides internal integrity, NOT outside authentication.
    if data.get("manifest_version") != EVIDENCE_MANIFEST_SCHEMA_VERSION:
        errors.append("Manifest version unsupported or predates strict redaction")
    claimed_hash = data.get("manifest_sha256")
    unsigned = dict(data)
    unsigned.pop("manifest_sha256", None)
    computed_hash = hashlib.sha256(json.dumps(unsigned, sort_keys=True, indent=2).encode("utf-8")).hexdigest()
    if claimed_hash != computed_hash:
        errors.append("Manifest canonical SHA-256 self-digest mismatch")
    if data.get("evidence_provenance") != "SELF_REPORTED_PRIVATE_LEDGER_NOT_ORIGINAL_REPLAY":
        errors.append("Missing explicit unverified original inference provenance")
    # Doc type & schema
    if data.get("doc_type") != "vlm_evidence_manifest":
        errors.append(f"Invalid doc_type: '{data.get('doc_type')}'")
    if data.get("scientific_capability_points") != 0.0:
        errors.append(f"Invalid scientific_capability_points: {data.get('scientific_capability_points')}; must be 0.0")
    if data.get("hieratic_reading_claim") is not False:
        errors.append("Invalid hieratic_reading_claim: must be False")

    # Protocol checks
    proto = data.get("protocol", {})
    if proto.get("protocol_version") != PROTOCOL_VERSION_W27:
        errors.append(f"Unexpected protocol version: '{proto.get('protocol_version')}'")
    if proto.get("domain_blind_prompt_sha256") != FROZEN_DOMAIN_BLIND_PROMPT_W27_SHA256:
        errors.append("Domain-blind prompt hash mismatch")
    if proto.get("script_aware_prompt_sha256") != FROZEN_SCRIPT_AWARE_PROMPT_W27_SHA256:
        errors.append("Script-aware prompt hash mismatch")
    if proto.get("leading_ident_prompt_sha256") != FROZEN_LEADING_IDENT_PROMPT_W27_SHA256:
        errors.append("Leading prompt hash mismatch")

    # Model spec checks
    model = data.get("model_spec", {})
    if model.get("model_id") != PINNED_MODEL_ID:
        errors.append(f"Unexpected model_id: '{model.get('model_id')}'")
    if model.get("revision") != PINNED_REVISION:
        errors.append(f"Unexpected model revision: '{model.get('revision')}'")
    if model.get("weight_sha256") != RECORDED_WEIGHT_SHA256:
        errors.append(f"Unexpected model weight SHA-256: '{model.get('weight_sha256')}'")

    # Ledger audit checks
    la = data.get("ledger_audit", {})
    planned = la.get("planned_count", 0)
    attempted = la.get("attempted_count", 0)
    succeeded = la.get("succeeded_count", 0)
    failed = la.get("failed_count", 0)
    skipped = la.get("skipped_count", 0)

    if planned != (attempted + skipped):
        errors.append(f"Accounting invariant failed: planned ({planned}) != attempted ({attempted}) + skipped ({skipped})")
    if attempted != (succeeded + failed):
        errors.append(f"Accounting invariant failed: attempted ({attempted}) != succeeded ({succeeded}) + failed ({failed})")

    # Attempts list checks
    attempts = data.get("attempts", [])
    if len(attempts) != planned:
        errors.append(f"Attempts count in manifest ({len(attempts)}) != planned ({planned})")

    valid_attempt_fields = {"attempt_id","attempt_index","attempt_category",
        "target_or_control_id","physical_witness","task","rung","prompt_variant",
        "prompt_sha256","stimulus_sha256","stimulus_dimensions","model_id",
        "model_revision","model_weight_sha256","status","completed_at",
        "latency_ms","token_usage","output_sha256","error_category"}
    valid_skip_fields = {"attempt_id","attempt_index","status","target_or_control_id","skip_reason"}
    observed_ids = set()
    observed_indices = set()
    counts = {"success":0,"failed":0,"skipped":0}
    for idx, att in enumerate(attempts):
        if not isinstance(att, dict):
            errors.append(f"Attempt [{idx}]: expected object")
            continue
        allowed = valid_skip_fields if att.get("status")=="skipped" else valid_attempt_fields
        if set(att) - allowed:
            errors.append(f"Attempt [{idx}]: forbidden or unredacted per-attempt fields")
        att_id,index = att.get("attempt_id"),att.get("attempt_index")
        if not isinstance(att_id,str) or not att_id or att_id in observed_ids:
            errors.append(f"Attempt [{idx}]: missing or duplicate ID")
        observed_ids.add(att_id)
        if type(index) is not int or index<0 or index in observed_indices:
            errors.append(f"Attempt [{idx}]: missing or duplicate attempt index")
        observed_indices.add(index)
        if att.get("status") in counts:
            counts[att["status"]]+=1
        status = att.get("status")
        if status not in ("success", "failed", "skipped"):
            errors.append(f"Attempt [{idx}]: invalid status '{status}'")
        if status in ("success", "failed"):
            out_sha = att.get("output_sha256")
            if not isinstance(out_sha, str) or len(out_sha) != 64 or any(c not in "0123456789abcdef" for c in out_sha):
                errors.append(f"Attempt [{idx}]: missing or invalid output_sha256")

    if counts != {"success":succeeded,"failed":failed,"skipped":skipped}:
        errors.append("Row-level statuses disagree with declared accounting")
    if len(observed_indices)==len(attempts) and observed_indices != set(range(len(attempts))):
        errors.append("Attempt indices do not span frozen population")
    if la.get("original_ledger_replayed_by_public_verifier") is not False:
        errors.append("Public manifest cannot claim private original ledger replay")
    if data.get("execution_tier")=="agent_local_attested" and planned==69 and (succeeded,failed,skipped)!=(67,2,0):
        errors.append("Reported W28 denominator differs from original local receipt")
    # Evidence grades checks
    eg = data.get("evidence_grades", {})
    if any(eg.get(key,{}).get("status")=="PASSED" for key in ("grade_a_multimodal_interface","grade_c_real_weights_loaded","grade_d_actual_sign_media_passes")):
        errors.append("Manifest alone cannot independently certify weight/model forward evidence")
    if eg.get("grade_f_authentic_hieratic_gold_evaluation", {}).get("status") != "STRICTLY_NO":
        errors.append("Evidence Grade F must remain STRICTLY_NO")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "manifest_path": str(p),
        "task_id": data.get("task_id"),
        "execution_tier": data.get("execution_tier"),
        "planned_count": planned,
        "attempted_count": attempted,
        "succeeded_count": succeeded,
        "failed_count": failed,
        "protocol_fingerprint": proto.get("protocol_fingerprint"),
    }
