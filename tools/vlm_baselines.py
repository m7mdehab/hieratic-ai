"""Command-line interface for reproducible VLM baseline evaluation and auditing.

Enforces suite integrity, prompt SHA-256 verification, quarantined demonstration checks,
full attempt preservation audits, promotion prevention for synthetic fixtures,
independent evaluation universe verification, and dual-channel metric scoring
under EVAL-006 document-clustered uncertainty standards.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jsonschema import Draft202012Validator, FormatChecker
import yaml

from eval.vlm.adapter import (
    BaseVLMAdapter,
    MockVLMAdapter,
    OpenWeightVLMAdapter,
    UnverifiedDemonstrationError,
    get_adapter,
)
from eval.vlm.integrity import (
    NONCERTIFIABLE_CLASSIFICATION,
    verify_attempts_against_universe,
    verify_external_authorization,
    verify_universe_anchor,
    write_json_no_clobber,
)
from eval.vlm.runner import VLMRunner
from eval.vlm.scorer import compare_manifests, score_manifest
from eval.vlm.smoke import run_real_visual_smoke
from eval.vlm.universe import (
    DEFAULT_UNIVERSE_PATH,
    admit_external_items,
    compute_universe_sha256,
    fatal_admission_errors,
    get_expected_attempts,
    get_universe_gold,
    get_universe_items,
    load_universe,
    verify_universe_integrity,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE_PATH = ROOT / "eval/vlm/suite.yaml"
DEFAULT_DEMOS_PATH = ROOT / "eval/vlm/demonstrations.yaml"
SCHEMA_PATH = ROOT / "schemas/vlm_baselines.schema.json"


class VLMCLIError(Exception):
    """Raised when a CLI command fails validation or execution."""
    pass


def load_schema(schema_path: Path = SCHEMA_PATH) -> dict[str, Any]:
    """Load JSON schema."""
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise VLMCLIError(f"Cannot read schema from {schema_path}: {exc}") from exc


def load_yaml(path: Path) -> Any:
    """Load YAML file."""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise VLMCLIError(f"Cannot read YAML from {path}: {exc}") from exc


def load_json(path: Path) -> Any:
    """Load JSON file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise VLMCLIError(f"Cannot read JSON from {path}: {exc}") from exc


def write_json_atomic(path: Path, data: Any, indent: int = 2) -> None:
    """Publish JSON with exclusive no-clobber semantics (never replaces an existing output).

    Name kept for compatibility; delegates to ``write_json_no_clobber`` (exclusive temp
    file, fsync, hard-link commit). Raises ImmutableOutputError if the target exists.
    """
    write_json_no_clobber(Path(path), data, indent=indent)


def validate_with_schema(payload: Any, schema: dict[str, Any]) -> list[str]:
    """Validate payload against schema and return list of error strings."""
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = validator.iter_errors(payload)
    return [
        f"{'.'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
        for e in sorted(errors, key=lambda e: str(list(e.absolute_path)))
    ]


def validate_suite(suite_path: Path = DEFAULT_SUITE_PATH, schema_path: Path = SCHEMA_PATH) -> list[str]:
    """Validate evaluation suite against schema and semantic consistency rules."""
    schema = load_schema(schema_path)
    suite = load_yaml(suite_path)

    errors = validate_with_schema(suite, schema)
    if errors:
        return errors

    # Check execution gate: unapproved positive spend is prohibited
    gate = suite.get("execution_gate", {})
    spend = gate.get("max_paid_spend_usd", 0.0)
    if spend > 0.0:
        errors.append(f"Unapproved positive spend limit ({spend} USD); zero-spend is mandatory.")

    if not gate.get("require_image_conditioning", False):
        errors.append("Execution gate must require image conditioning.")

    # Check model unique keys
    models = suite.get("models", [])
    keys = [m["key"] for m in models]
    if len(keys) != len(set(keys)):
        errors.append("Model candidate keys must be unique.")

    # Check prompt template hashes
    prompts = suite.get("prompts", {})
    for rung, rung_spec in prompts.items():
        for shot_mode in ["zero_shot", "few_shot"]:
            spec = rung_spec.get(shot_mode, {})
            sys_prompt = spec.get("system_prompt", "")
            usr_template = spec.get("user_template", "")
            recorded_hash = spec.get("prompt_sha256", "")

            combined = f"{sys_prompt}\n{usr_template}"
            computed_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()

            if recorded_hash != computed_hash:
                errors.append(
                    f"Prompt drift detected for rung '{rung}' ({shot_mode}): "
                    f"recorded {recorded_hash[:12]} != computed {computed_hash[:12]}"
                )

    return errors


def validate_demonstrations(
    demos_path: Path = DEFAULT_DEMOS_PATH,
    schema_path: Path = SCHEMA_PATH,
    known_eval_items: set[str] | None = None,
    known_eval_image_hashes: set[str] | None = None,
    require_authentic: bool = False,
) -> list[str]:
    """Validate demonstration bank against schema, rights clearance, and leakage quarantine."""
    schema = load_schema(schema_path)
    demos = load_yaml(demos_path)

    errors = validate_with_schema(demos, schema)
    if errors:
        return errors

    status = demos.get("status")
    rights = demos.get("rights_review", {})
    items = demos.get("items", [])

    # Check for demo ID duplicates
    demo_ids = [d["demo_id"] for d in items]
    if len(demo_ids) != len(set(demo_ids)):
        errors.append("Demonstration IDs must be unique.")

    # Check ID leakage against evaluation items
    eval_set: set[str] = set(known_eval_items) if known_eval_items else set()
    hash_set: set[str] = set(known_eval_image_hashes) if known_eval_image_hashes else set()

    for d in items:
        did = d["demo_id"]
        dhash = d.get("image_sha256", "")

        # Check for forbidden HieraticBench identifier prefix leakage
        forbidden_prefixes = ["AKU-", "CBL-", "HB-", "MET-", "WM-", "YPM-"]
        if any(pfx in did for pfx in forbidden_prefixes):
            errors.append(
                f"Demonstration '{did}' uses reserved HieraticBench prefix. "
                "Quarantine violation: benchmark items cannot be used as demonstrations."
            )

        if did in eval_set:
            errors.append(f"Leakage violation: Demonstration ID '{did}' overlaps with evaluation split.")
        if dhash and dhash in hash_set:
            errors.append(f"Demonstration image hash leakage: '{did}' image hash overlaps with evaluation item.")

    # Strict clearance verification
    is_synthetic = (status == "synthetic_fixture_only")
    rights_approved = (rights.get("rights_review_status") == "approved_with_evidence")
    quarantine_verified = rights.get("quarantine_verified", False)

    if require_authentic and is_synthetic:
        errors.append(
            f"Demonstration bank '{demos.get('bank_id')}' is marked synthetic_fixture_only; "
            "authentic rights-approved demonstrations are required for live evaluation."
        )

    # Forgery detection: cannot claim approved clearance on unverified synthetic placeholders
    if rights_approved and is_synthetic:
        errors.append(
            "Demonstration clearance forgery: status is 'synthetic_fixture_only' but rights_review_status "
            "claims 'approved_with_evidence'. Synthetic placeholders cannot be certified as rights-approved."
        )

    # Real few-shot inference verification: require genuine image files on disk
    if require_authentic or (rights_approved and quarantine_verified):
        for d in items:
            img_ref = d.get("image_ref", "")
            if img_ref.startswith("facsimile://"):
                errors.append(
                    f"Demonstration '{d['demo_id']}' uses placeholder URI '{img_ref}'. "
                    "Genuine image files on disk are required for cleared evaluation."
                )
                continue

            img_path = Path(img_ref)
            if not img_path.is_file():
                errors.append(f"Demonstration '{d['demo_id']}' image file not found on disk: {img_ref}")
            else:
                actual_hash = hashlib.sha256(img_path.read_bytes()).hexdigest()
                if actual_hash != d.get("image_sha256"):
                    errors.append(
                        f"Demonstration '{d['demo_id']}' image hash mismatch: "
                        f"on-disk {actual_hash[:12]} != metadata {d.get('image_sha256')[:12]}"
                    )

    return errors


def audit_manifest(
    manifest_path: Path | str | dict[str, Any],
    suite_path: Path | str = DEFAULT_SUITE_PATH,
    schema_path: Path | str | dict[str, Any] = SCHEMA_PATH,
    universe_path: Path | str | dict[str, Any] = DEFAULT_UNIVERSE_PATH,
    require_certified: bool = False,
    items_path: Path | str | None = None,
) -> list[str]:
    """Audit run manifest completeness, schema compliance, universe integrity, and promotion gating."""
    if isinstance(schema_path, dict):
        schema = schema_path
    else:
        schema = load_schema(Path(schema_path))

    if isinstance(manifest_path, dict):
        manifest = manifest_path
    else:
        manifest = load_json(Path(manifest_path))

    errors = validate_with_schema(manifest, schema)
    if errors:
        return errors

    tier = manifest.get("execution_tier")
    validity = manifest.get("scientific_validity")
    cert_status = manifest.get("certification_status")
    model_key = manifest.get("model_key")
    cov = manifest.get("coverage_summary", {})
    attempts = manifest.get("attempts", [])

    # Promotion prevention: fail-closed certification gate.
    # Every field checked below lives in the editable manifest, so none of them can ever
    # *establish* certification. Certification requires externally anchored evidence
    # (verified authorization authority, source evidence, model-inference receipt).
    # Until that exists, --require-certified fails unconditionally.
    if require_certified:
        auth_ok, auth_msg = verify_external_authorization(manifest)
        if not auth_ok:
            errors.append(f"Promotion rejection / Certification disabled: {auth_msg}")
        errors.append(
            "Promotion rejection / Certification disabled: no actual model-inference receipt, externally anchored "
            "source evidence or independently verified cohort authorization is available; manifest tier, model key, "
            "status, receipt reference and success counts are user-editable and are not evidence."
        )
        if not manifest.get("authorization_receipt_ref"):
            errors.append(
                f"Promotion rejection / Certification rejection: Manifest '{manifest.get('manifest_id')}' lacks an "
                "independently verified experiment authorization receipt. "
                "Self-declared preflight manifests cannot be certified."
            )
        if tier not in {"live_local_open_weight", "authorized_external_model"} or validity != "certified_baseline":
            errors.append(
                f"Promotion rejection / Certification rejection: Manifest execution tier '{tier}' / validity '{validity}' "
                "is not an independently certified production execution tier "
                "('live_local_open_weight' / 'certified_baseline' required)."
            )
        if cert_status != "certified":
            errors.append(
                f"Promotion rejection / Certification rejection: Manifest certification status '{cert_status}' is not 'certified'."
            )
        if model_key == "mock-vision-v1":
            errors.append(
                "Promotion rejection / Certification rejection: Mock baseline 'mock-vision-v1' cannot produce certified scientific results."
            )
        cov_rate = cov.get("coverage_rate", 0.0)
        successes = cov.get("success_count", 0)
        if cov_rate < 0.95 or successes == 0:
            errors.append(
                f"Promotion rejection / Certification rejection: Incomplete or failed execution (coverage rate {cov_rate}, "
                f"success count {successes}); all-failed or barrier-blocked manifests cannot be certified."
            )
        univ = manifest.get("universe_manifest", {})
        if univ.get("items_tier") != "approved_evaluation_cohort":
            errors.append(
                f"Promotion rejection / Certification rejection: Items tier '{univ.get('items_tier')}' is not an "
                "approved evaluation cohort with verified independent rights clearance."
            )

    # Independent Universe Integrity Verification
    univ = manifest.get("universe_manifest")
    if not univ:
        errors.append("Manifest is missing required 'universe_manifest' block.")
    else:
        try:
            if isinstance(universe_path, dict):
                universe_data = universe_path
                target_name = universe_data.get("universe_id", "in_memory_universe")
            else:
                target_universe_path = Path(universe_path)
                universe_data = load_universe(target_universe_path)
                target_name = target_universe_path.name

            u_errors = verify_universe_integrity(universe_data)
            errors.extend([f"Universe anchor violation: {e}" for e in verify_universe_anchor(universe_data)])
            if u_errors:
                errors.extend([f"Independent universe '{target_name}' integrity error: {e}" for e in u_errors])
            else:
                errors.extend(verify_attempts_against_universe(manifest, universe_data))
                expected_u_id = universe_data.get("universe_id")
                expected_u_sha = universe_data.get("universe_sha256")
                manifest_u_id = univ.get("universe_id")
                manifest_u_sha = univ.get("universe_sha256")

                # Match universe identity & hash
                if manifest_u_id and manifest_u_id != expected_u_id:
                    errors.append(
                        f"Independent universe identity mismatch: manifest declares '{manifest_u_id}' "
                        f"!= independent universe '{expected_u_id}'"
                    )

                if manifest_u_sha != expected_u_sha:
                    errors.append(
                        f"Independent universe hash mismatch: manifest declares {manifest_u_sha[:12] if manifest_u_sha else 'null'} "
                        f"!= independent universe {expected_u_sha[:12]}"
                    )

                # Compute expected attempts from the independent universe for the manifest's shot mode
                expected_attempt_keys = get_expected_attempts(universe_data, manifest.get("shot_mode", "zero_shot"))

                if len(attempts) != len(expected_attempt_keys):
                    errors.append(
                        f"Frozen universe violation / Independent universe violation: recorded attempts {len(attempts)} != "
                        f"expected universe attempts {len(expected_attempt_keys)}. Truncated manifest detected."
                    )

                actual_attempt_keys = sorted(
                    f"{a['item_id']}::{a['rung']}::{a.get('shot_mode', 'zero_shot')}::{a.get('sample_index', 0)}"
                    for a in attempts
                )

                missing_from_manifest = sorted(set(expected_attempt_keys) - set(actual_attempt_keys))
                extra_in_manifest = sorted(set(actual_attempt_keys) - set(expected_attempt_keys))

                if missing_from_manifest:
                    errors.append(
                        f"Independent universe violation: Manifest is missing {len(missing_from_manifest)} expected attempts "
                        f"(e.g. {missing_from_manifest[:3]}). Dropped item detected."
                    )
                if extra_in_manifest:
                    errors.append(
                        f"Independent universe violation: Manifest contains {len(extra_in_manifest)} unregistered attempts "
                        f"(e.g. {extra_in_manifest[:3]})."
                    )

        except Exception as exc:
            errors.append(f"Independent universe audit failed to load {universe_path}: {exc}")

    if len(attempts) != cov.get("total_attempts"):
        errors.append(f"Attempt count mismatch: recorded {len(attempts)} != summary {cov.get('total_attempts')}")

    # Check composite key uniqueness: (item_id, rung, shot_mode, sample_index)
    seen_composite = set()
    for i, a in enumerate(attempts):
        comp_key = (a["item_id"], a["rung"], a.get("shot_mode", "zero_shot"), a.get("sample_index", 0))
        if comp_key in seen_composite:
            errors.append(f"Duplicate attempt key: {comp_key} at attempt {i}")
        seen_composite.add(comp_key)

        status = a.get("status")
        if status not in {"success", "failed", "abstained", "refused", "timeout"}:
            errors.append(f"Attempt {i} has invalid status '{status}'")
        if status == "success" and not a.get("raw_output"):
            errors.append(f"Attempt {i} marked success but has null raw_output")
        if status in {"failed", "refused", "timeout"} and not a.get("error_message"):
            errors.append(f"Attempt {i} marked {status} but lacks diagnostic error_message")

    # Verify suite SHA-256 match if local suite exists
    if isinstance(suite_path, (Path, str)):
        suite_path_obj = Path(suite_path)
        if suite_path_obj.is_file():
            current_suite_sha = hashlib.sha256(suite_path_obj.read_bytes()).hexdigest()
            if manifest.get("suite_sha256") != current_suite_sha:
                errors.append(
                    f"Manifest suite hash mismatch: manifest {manifest.get('suite_sha256')[:12]} != "
                    f"current {current_suite_sha[:12]}"
                )

    return errors


def create_synthetic_items() -> list[dict[str, Any]]:
    """Backwards-compatible convenience helper returning synthetic preflight universe items."""
    try:
        universe = load_universe(DEFAULT_UNIVERSE_PATH)
        return get_universe_items(universe)
    except Exception:
        # Fallback if universe.yaml not yet initialized
        return [
            {
                "item_id": "SYNTH-DOCA-IDENT-001",
                "document_id": "DOC-PAPYRUS-A",
                "rung": "identify",
                "image_bytes": b"synthetic_palaeography_hieratic_papyrus_01",
            },
            {
                "item_id": "SYNTH-DOCA-IDENT-002",
                "document_id": "DOC-PAPYRUS-A",
                "rung": "identify",
                "image_bytes": b"synthetic_palaeography_hieratic_papyrus_02",
            },
            {
                "item_id": "SYNTH-DOCB-IDENT-001",
                "document_id": "DOC-RELIEF-B",
                "rung": "identify",
                "image_bytes": b"synthetic_palaeography_hieroglyphic_relief_01",
            },
            {
                "item_id": "SYNTH-DOCB-IDENT-002",
                "document_id": "DOC-RELIEF-B",
                "rung": "identify",
                "image_bytes": b"synthetic_palaeography_hieroglyphic_relief_02",
            },
            {
                "item_id": "SYNTH-DOCA-SIGN-001",
                "document_id": "DOC-PAPYRUS-A",
                "rung": "signs",
                "image_bytes": b"synthetic_sign_isolated_a01",
            },
            {
                "item_id": "SYNTH-DOCB-SIGN-001",
                "document_id": "DOC-RELIEF-B",
                "rung": "signs",
                "image_bytes": b"synthetic_sign_isolated_g43",
            },
            {
                "item_id": "SYNTH-DOCA-XLIT-001",
                "document_id": "DOC-PAPYRUS-A",
                "rung": "transliterate",
                "image_bytes": b"synthetic_phrase_manuscript_line_01",
            },
            {
                "item_id": "SYNTH-DOCB-XLIT-001",
                "document_id": "DOC-RELIEF-B",
                "rung": "transliterate",
                "image_bytes": b"synthetic_phrase_manuscript_line_02",
            },
            {
                "item_id": "SYNTH-DOCA-TRANS-001",
                "document_id": "DOC-PAPYRUS-A",
                "rung": "translate",
                "image_bytes": b"synthetic_passage_inscribed_column_01",
            },
            {
                "item_id": "SYNTH-DOCB-TRANS-001",
                "document_id": "DOC-RELIEF-B",
                "rung": "translate",
                "image_bytes": b"synthetic_passage_inscribed_column_02",
            },
        ]


def create_synthetic_gold() -> dict[str, dict[str, Any]]:
    """Backwards-compatible convenience helper returning synthetic preflight universe gold."""
    try:
        universe = load_universe(DEFAULT_UNIVERSE_PATH)
        return get_universe_gold(universe)
    except Exception:
        return {
            "SYNTH-DOCA-IDENT-001": {"script": "Hieratic"},
            "SYNTH-DOCA-IDENT-002": {"script": "Hieratic"},
            "SYNTH-DOCB-IDENT-001": {"script": "Hieroglyphic"},
            "SYNTH-DOCB-IDENT-002": {"script": "Hieroglyphic"},
            "SYNTH-DOCA-SIGN-001": {"gardiner": "A1"},
            "SYNTH-DOCB-SIGN-001": {"gardiner": "G43"},
            "SYNTH-DOCA-XLIT-001": {"transliteration": "jrj.n=f m mnw=f"},
            "SYNTH-DOCB-XLIT-001": {"transliteration": "ḏd-mdw jn Wsjr"},
            "SYNTH-DOCA-TRANS-001": {"translation": "He made it as his monument."},
            "SYNTH-DOCB-TRANS-001": {"translation": "Words spoken by Osiris."},
        }


def make_audit_receipt(audit_errors: list[str], universe_path: Path | str | dict[str, Any]) -> dict[str, Any]:
    """Describe what was (and was not) audited. Outputs are never certifiable in this preflight."""
    try:
        udata = universe_path if isinstance(universe_path, dict) else load_universe(Path(universe_path))
        universe_id = udata.get("universe_id")
        universe_sha = compute_universe_sha256(udata)
    except Exception:
        universe_id, universe_sha = None, None
    return {
        "audit_passed": not audit_errors,
        "audit_error_count": len(audit_errors),
        "audit_errors": list(audit_errors),
        "universe_id": universe_id,
        "universe_sha256_computed": universe_sha,
        "universe_trust": "code_pinned_synthetic_preflight_self_check_only",
        "external_authorization": "not_integrated",
        "certifiable": False,
        "scope": "attempted universe of the audited manifest(s); not a benchmark-complete scientific result",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproducible VLM baseline runner and audit CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate-suite
    p_val_suite = subparsers.add_parser("validate-suite", help="Validate evaluation suite configuration")
    p_val_suite.add_argument("--suite", type=Path, default=DEFAULT_SUITE_PATH)

    # validate-demonstrations
    p_val_demos = subparsers.add_parser("validate-demonstrations", help="Validate few-shot demonstration bank")
    p_val_demos.add_argument("--demos", type=Path, default=DEFAULT_DEMOS_PATH)
    p_val_demos.add_argument("--require-authentic", action="store_true", help="Fail if bank is a synthetic fixture")

    # run
    p_run = subparsers.add_parser("run", help="Execute evaluation run")
    p_run.add_argument("--suite", type=Path, default=DEFAULT_SUITE_PATH)
    p_run.add_argument("--demos", type=Path, default=DEFAULT_DEMOS_PATH)
    p_run.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE_PATH, help="Path to evaluation universe YAML/JSON")
    p_run.add_argument("--items", type=Path, default=None, help="Path to external evaluation items JSON/YAML")
    p_run.add_argument("--admission-receipt", type=Path, default=None, help="Path to independent admission receipt for external items")
    p_run.add_argument("--model", type=str, default="mock-vision-v1")
    p_run.add_argument("--shot-mode", type=str, choices=["zero_shot", "few_shot", "both", "zero-shot", "few-shot"], default="both")
    p_run.add_argument("--output", type=Path, required=True, help="Path to save run manifest JSON")
    p_run.add_argument("--simulated-mode", type=str, default="normal", help="Simulation mode for mock adapter")
    p_run.add_argument("--weights-dir", type=Path, default=None, help="Local weights directory for open-weight VLM")

    # audit-manifest
    p_audit = subparsers.add_parser("audit-manifest", help="Audit run manifest completeness and integrity")
    p_audit.add_argument("--manifest", type=Path, required=True)
    p_audit.add_argument("--suite", type=Path, default=DEFAULT_SUITE_PATH)
    p_audit.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE_PATH, help="Path to independently pinned universe")
    p_audit.add_argument("--items", type=Path, default=None)
    p_audit.add_argument("--require-certified", action="store_true", help="Reject uncertified preflight manifests")

    # score
    p_score = subparsers.add_parser("score", help="Score run manifest and generate report")
    p_score.add_argument("--manifest", type=Path, required=True)
    p_score.add_argument("--gold", type=Path, default=None)
    p_score.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE_PATH)
    p_score.add_argument("--output", type=Path, default=None)
    p_score.add_argument("--allow-incomplete-gold", action="store_true", help="Permit missing gold without failing closed")
    p_score.add_argument("--diagnostic-only", action="store_true", help="Score even if the input audit fails; output is stamped noncertifiable with the audit errors")

    # paired-compare
    p_comp = subparsers.add_parser("paired-compare", help="Compare two run manifests on identical items")
    p_comp.add_argument("--manifest-a", type=Path, required=True)
    p_comp.add_argument("--manifest-b", type=Path, required=True)
    p_comp.add_argument("--shot-mode-a", type=str, default=None, help="Condition filter for manifest A")
    p_comp.add_argument("--shot-mode-b", type=str, default=None, help="Condition filter for manifest B")
    p_comp.add_argument("--gold", type=Path, default=None)
    p_comp.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE_PATH)
    p_comp.add_argument("--output", type=Path, default=None)
    p_comp.add_argument("--diagnostic-only", action="store_true", help="Compare even if an input audit fails; output is stamped noncertifiable with the audit errors")

    # real-smoke
    p_smoke = subparsers.add_parser("real-smoke", help="Execute real visual smoke test on local hardware and model weights")
    p_smoke.add_argument("--model", type=str, default="qwen2.5-vl-7b-instruct", help="Model candidate key to evaluate")
    p_smoke.add_argument("--suite", type=Path, default=DEFAULT_SUITE_PATH, help="Path to evaluation suite YAML")
    p_smoke.add_argument("--weights-dir", type=Path, default=None, help="Local directory containing model snapshot weights")
    p_smoke.add_argument("--output", type=Path, default=None, help="Path to write structured smoke report JSON")
    p_smoke.add_argument("--allow-simulated", action="store_true", help="Allow simulated test doubles for dry-run verification in test environments")

    # real-hieratic
    p_hieratic = subparsers.add_parser("real-hieratic", help="Execute authentic Hieratic reading experiment on manuscript image and crops")
    p_hieratic.add_argument("--model", type=str, default="smolvlm-256m-instruct", help="Model candidate key to evaluate")
    p_hieratic.add_argument("--suite", type=Path, default=DEFAULT_SUITE_PATH, help="Path to evaluation suite YAML")
    p_hieratic.add_argument("--weights-dir", type=Path, default=None, help="Local directory containing model snapshot weights")
    p_hieratic.add_argument("--image-path", type=Path, default=None, help="Path to authentic Cat.2044 JPEG image file")
    p_hieratic.add_argument("--crops-dir", type=Path, default=None, help="Path to directory containing deterministic line crops and inspection-manifest.json")
    p_hieratic.add_argument("--output", type=Path, default=None, help="Path to write structured hieratic experiment report JSON")
    p_hieratic.add_argument("--allow-simulated", action="store_true", help="Allow simulated mock adapter execution in test/CI environments")

    args = parser.parse_args(argv)

    try:
        if args.command == "validate-suite":
            errors = validate_suite(args.suite)
            if errors:
                print("Suite validation FAILED:", file=sys.stderr)
                for e in errors:
                    print(f"  - {e}", file=sys.stderr)
                return 1
            print(f"PASS: Suite '{args.suite.name}' is valid, frozen, and enforces zero spend.")
            return 0

        elif args.command == "validate-demonstrations":
            errors = validate_demonstrations(args.demos, require_authentic=args.require_authentic)
            if errors:
                print("Demonstration validation FAILED:", file=sys.stderr)
                for e in errors:
                    print(f"  - {e}", file=sys.stderr)
                return 1
            demos = load_yaml(args.demos)
            st = demos.get("status")
            print(f"PASS: Demonstration bank '{args.demos.name}' passed validation (Status: {st}).")
            return 0

        elif args.command == "run":
            suite = load_yaml(args.suite)
            demos = load_yaml(args.demos)

            # Find model config
            model_cfg = next((m for m in suite["models"] if m["key"] == args.model), None)
            if not model_cfg:
                raise VLMCLIError(f"Model key '{args.model}' not found in suite.")

            if model_cfg["model_type"] == "mock":
                adapter = MockVLMAdapter(model_cfg, simulated_mode=args.simulated_mode)
            else:
                adapter = get_adapter(model_cfg, weights_dir=args.weights_dir)

            universe_data = None
            if args.universe and args.universe.is_file():
                universe_data = load_universe(args.universe)

            runner = VLMRunner(
                suite,
                demos,
                adapter,
                suite_path=args.suite,
                demos_path=args.demos,
                universe_data=universe_data,
                universe_path=args.universe,
            )

            if args.items and args.items.is_file():
                items, items_tier, adm_errors = admit_external_items(args.items, args.admission_receipt)
                for note in adm_errors:
                    if note not in fatal_admission_errors(adm_errors):
                        print(note, file=sys.stderr)
                fatal = fatal_admission_errors(adm_errors)
                if fatal:
                    raise VLMCLIError(f"External items admission failed: {'; '.join(fatal)}")
            else:
                if universe_data:
                    items = get_universe_items(universe_data)
                    items_tier = universe_data.get("universe_tier", "synthetic_preflight_universe")
                else:
                    items = create_synthetic_items()
                    items_tier = "synthetic_ci_items"

            shot_mode = args.shot_mode.replace("-", "_")
            manifest = runner.run_suite(items, shot_mode=shot_mode, items_tier=items_tier)

            write_json_atomic(args.output, manifest)
            print(f"PASS: Evaluation complete. Manifest written to {args.output}")
            print(f"  Execution tier: {manifest['execution_tier']}")
            print(f"  Attempts recorded: {manifest['coverage_summary']['total_attempts']}")
            print(f"  Coverage rate: {manifest['coverage_summary']['coverage_rate']}")
            return 0

        elif args.command == "audit-manifest":
            errors = audit_manifest(
                args.manifest,
                args.suite,
                universe_path=args.universe,
                require_certified=args.require_certified,
                items_path=args.items,
            )
            if errors:
                print("Manifest audit FAILED:", file=sys.stderr)
                for e in errors:
                    print(f"  - {e}", file=sys.stderr)
                return 1
            print(f"PASS: Manifest '{args.manifest.name}' is complete and conforms to contract.")
            return 0

        elif args.command == "score":
            manifest = load_json(args.manifest)
            audit_errors = audit_manifest(
                args.manifest, DEFAULT_SUITE_PATH, universe_path=args.universe
            )
            if audit_errors and not args.diagnostic_only:
                print("Score REFUSED: input manifest failed independent audit (use --diagnostic-only for a "
                      "noncertifiable diagnostic):", file=sys.stderr)
                for e in audit_errors:
                    print(f"  - {e}", file=sys.stderr)
                return 1
            if args.gold and args.gold.is_file():
                gold = load_json(args.gold) if args.gold.suffix.lower() == ".json" else load_yaml(args.gold)
            elif args.universe and args.universe.is_file():
                u_data = load_universe(args.universe)
                gold = get_universe_gold(u_data)
            else:
                gold = create_synthetic_gold()

            report = score_manifest(
                manifest,
                gold,
                require_complete_gold=(not args.allow_incomplete_gold),
            )
            report["audit_receipt"] = make_audit_receipt(audit_errors, args.universe)
            report["classification"] = NONCERTIFIABLE_CLASSIFICATION

            if args.output:
                write_json_atomic(args.output, report)
                print(f"Report written to {args.output}")

            print(
                f"PASS: Scored manifest '{manifest['manifest_id']}' (Channel: {report['scoring_channel']}; "
                f"classification: {NONCERTIFIABLE_CLASSIFICATION}; input audit "
                f"{'passed' if not audit_errors else 'FAILED (diagnostic-only)'}):"
            )
            for rung, rdata in report["project_native_eval001"].items():
                ci_str = str(rdata['cluster_bootstrap_ci_95']) if rdata['cluster_bootstrap_ci_95'] else f"[{rdata['cluster_ci_status']}]"
                print(
                    f"  [{rung}] {rdata['primary_metric_id']} ({rdata['metric_direction']}): "
                    f"Intention-to-test={rdata['intention_to_test_score']} "
                    f"(Clusters={rdata['cluster_count']}, 95% Clustered CI: {ci_str}) "
                    f"Coverage={rdata['coverage_rate']}"
                )
            return 0

        elif args.command == "paired-compare":
            manifest_a = load_json(args.manifest_a)
            manifest_b = load_json(args.manifest_b)
            audit_errors = audit_manifest(
                args.manifest_a, DEFAULT_SUITE_PATH, universe_path=args.universe
            ) + audit_manifest(args.manifest_b, DEFAULT_SUITE_PATH, universe_path=args.universe)
            if audit_errors and not args.diagnostic_only:
                print("Paired comparison REFUSED: an input manifest failed independent audit (use "
                      "--diagnostic-only for a noncertifiable diagnostic):", file=sys.stderr)
                for e in audit_errors:
                    print(f"  - {e}", file=sys.stderr)
                return 1
            if args.gold and args.gold.is_file():
                gold = load_json(args.gold) if args.gold.suffix.lower() == ".json" else load_yaml(args.gold)
            elif args.universe and args.universe.is_file():
                u_data = load_universe(args.universe)
                gold = get_universe_gold(u_data)
            else:
                gold = create_synthetic_gold()

            comps = compare_manifests(
                manifest_a,
                manifest_b,
                gold,
                shot_mode_a=args.shot_mode_a,
                shot_mode_b=args.shot_mode_b,
            )
            envelope = {
                "classification": NONCERTIFIABLE_CLASSIFICATION,
                "audit_receipt": make_audit_receipt(audit_errors, args.universe),
                "comparisons": comps,
            }
            if args.output:
                write_json_atomic(args.output, envelope)
                print(f"Comparison written to {args.output}")

            print(
                f"PASS: Paired comparison ({manifest_a['model_key']} vs {manifest_b['model_key']}; "
                f"classification: {NONCERTIFIABLE_CLASSIFICATION}):"
            )
            for c in comps:
                ci_str = str(c['delta_cluster_ci_95']) if c['delta_cluster_ci_95'] else f"[{c['delta_ci_status']}]"
                print(
                    f"  [{c['rung']}] Delta ({c['metric_id']}, {c['metric_direction']}): {c['score_delta']} "
                    f"(95% Clustered CI: {ci_str}) over N={c['paired_samples']} paired attempts"
                )
            return 0

        elif args.command == "real-smoke":
            suite = load_yaml(args.suite)
            model_cfg = next((m for m in suite["models"] if m["key"] == args.model), None)
            if not model_cfg:
                raise VLMCLIError(f"Model key '{args.model}' not found in suite.")

            report, success = run_real_visual_smoke(
                model_cfg,
                weights_dir=args.weights_dir,
                allow_simulated=args.allow_simulated,
            )

            if args.output:
                write_json_atomic(args.output, report)
                print(f"Smoke report written to {args.output}")

            if not success:
                print(f"BLOCKED: Real visual smoke test blocked for model '{args.model}':", file=sys.stderr)
                for res in report.get("missing_resources", []):
                    print(f"  - Missing prerequisite: {res}", file=sys.stderr)
                print(f"Barrier summary: {report.get('barrier_summary')}", file=sys.stderr)
                return 1

            print(f"PASS: Real visual smoke test completed for model '{args.model}' (Simulated: {report.get('simulated_double_smoke')}).")
            if "forward_test_image" in report:
                print(f"  Image A SHA-256: {report['forward_test_image']['image_sha256'][:16]}...")
            if "forward_control_image" in report:
                print(f"  Image B SHA-256: {report['forward_control_image']['image_sha256'][:16]}...")
            if "sensitivity_control" in report:
                print(f"  Visual sensitivity observed: {report['sensitivity_control']['sensitivity_observed']}")
            print(f"  Classification: {report['classification']} (0.0 capability points)")
            return 0

        elif args.command == "real-hieratic":
            from eval.vlm.hieratic import execute_hieratic_experiment
            suite = load_yaml(args.suite)
            model_cfg = next((m for m in suite["models"] if m["key"] == args.model), None)
            if not model_cfg:
                raise VLMCLIError(f"Model key '{args.model}' not found in suite.")

            targets = []
            # 1. Load full image if provided
            if args.image_path and args.image_path.is_file():
                img_bytes = args.image_path.read_bytes()
                targets.append({
                    "target_id": "cat2044_full_p01",
                    "target_type": "full_manuscript",
                    "image_bytes": img_bytes,
                    "source_bounds": [0, 0, 7063, 3947],
                    "transform": None,
                })

            # 2. Load crops if crops_dir provided
            if args.crops_dir and args.crops_dir.is_dir():
                manifest_file = args.crops_dir / "inspection-manifest.json"
                crop_records = []
                if manifest_file.is_file():
                    try:
                        insp_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                        crop_records = insp_data.get("crop_records", [])
                    except Exception:
                        pass

                for idx, c_path in enumerate(sorted(args.crops_dir.glob("line-candidate-*.png"))[:3], 1):
                    rec = next((r for r in crop_records if r.get("crop_artifact") == c_path.name), {})
                    targets.append({
                        "target_id": f"cat2044_line_candidate_{idx:03d}",
                        "target_type": "candidate_line_crop",
                        "image_bytes": c_path.read_bytes(),
                        "source_bounds": rec.get("source_box") or rec.get("crop_source_bounds"),
                        "transform": rec.get("source_to_crop_transform"),
                    })

            if not targets:
                if args.allow_simulated:
                    targets.append({
                        "target_id": "fixture_cat2044_full",
                        "target_type": "full_manuscript",
                        "image_bytes": b"synthetic_hieratic_full_manuscript_bytes",
                        "source_bounds": [0, 0, 7063, 3947],
                        "transform": None,
                    })
                    targets.append({
                        "target_id": "fixture_cat2044_line_001",
                        "target_type": "candidate_line_crop",
                        "image_bytes": b"synthetic_hieratic_line_crop_bytes",
                        "source_bounds": [100, 100, 300, 200],
                        "transform": None,
                    })
                else:
                    raise VLMCLIError("No authentic Hieratic image or crops provided. Specify --image-path or --crops-dir.")

            if args.allow_simulated:
                adapter = MockVLMAdapter(model_cfg, simulated_mode="normal")
            else:
                adapter = get_adapter(model_cfg, weights_dir=args.weights_dir)

            report = execute_hieratic_experiment(adapter, targets, allow_simulated=args.allow_simulated)

            # Validate against schema
            schema = load_schema(SCHEMA_PATH)
            errs = validate_with_schema(report, schema)
            if errs:
                raise VLMCLIError(f"Hieratic experiment report failed schema validation: {errs[0]}")

            if args.output:
                write_json_atomic(args.output, report)
                print(f"Hieratic report written to {args.output}")

            print(f"PASS: Authentic Hieratic experiment completed for model '{args.model}' (Targets: {len(targets)}).")
            print(f"  Protocol SHA-256: {report['protocol']['protocol_sha256'][:16]}...")
            print(f"  Visual sensitivity observed: {report['sensitivity_controls']['sensitivity_observed']}")
            print(f"  Classification: {report['classification']} (0.0 capability points)")
            return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
