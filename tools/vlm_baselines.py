"""Command-line interface for reproducible VLM baseline evaluation and auditing.

Enforces suite integrity, prompt SHA-256 verification, quarantined demonstration checks,
full attempt preservation audits, promotion prevention for synthetic fixtures,
and dual-channel metric scoring under EVAL-006 document-clustered uncertainty standards.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from eval.vlm.adapter import (
    BaseVLMAdapter,
    MockVLMAdapter,
    OpenWeightVLMAdapter,
    UnverifiedDemonstrationError,
    get_adapter,
)
from eval.vlm.runner import VLMRunner
from eval.vlm.scorer import compare_manifests, score_manifest

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

        if did in eval_set:
            errors.append(f"Leakage violation: demonstration '{did}' overlaps with evaluation item.")

        if dhash in hash_set and not d.get("is_synthetic_fixture", False):
            errors.append(f"Leakage violation: demonstration '{did}' image hash overlaps with evaluation item.")

        benchmark_prefixes = ("AKU-", "CBL-", "HB-", "MET-", "WM-", "YPM-")
        if did.startswith(benchmark_prefixes) or any(did.startswith(f"DEMO-{p}") for p in benchmark_prefixes):
            errors.append(f"Demonstration '{did}' uses a reserved HieraticBench prefix; quarantine violated.")

    # Clearance forgery detection: synthetic fixture banks cannot claim approved rights
    if status == "synthetic_fixture_only":
        if rights.get("rights_review_status") == "approved_with_evidence":
            errors.append("Demonstration clearance forgery: 'synthetic_fixture_only' bank cannot assert 'approved_with_evidence'.")
        if rights.get("quarantine_verified"):
            errors.append("Demonstration clearance forgery: 'synthetic_fixture_only' bank cannot assert quarantine_verified=true.")

    # Authentic clearance verification
    if require_authentic or status == "reviewed_authentic" or rights.get("rights_review_status") == "approved_with_evidence":
        if rights.get("rights_review_status") != "approved_with_evidence":
            errors.append("Authentic demonstration bank requires rights_review_status='approved_with_evidence'.")
        if not rights.get("quarantine_verified", False):
            errors.append("Authentic demonstration bank requires quarantine_verified=true.")

        for d in items:
            img_ref = d.get("image_ref", "")
            if not img_ref or img_ref.startswith("facsimile://"):
                errors.append(f"Demonstration '{d['demo_id']}' lacks authentic image file on disk: {img_ref}")
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
    manifest_path: Path,
    suite_path: Path = DEFAULT_SUITE_PATH,
    schema_path: Path = SCHEMA_PATH,
    require_certified: bool = False,
    items_path: Path | None = None,
) -> list[str]:
    """Audit run manifest completeness, schema compliance, hash stability, and promotion gating."""
    schema = load_schema(schema_path)
    manifest = load_json(manifest_path)

    errors = validate_with_schema(manifest, schema)
    if errors:
        return errors

    tier = manifest.get("execution_tier")
    validity = manifest.get("scientific_validity")

    # Promotion prevention: synthetic CI fixtures can NEVER be promoted to certified scientific results
    if require_certified:
        if tier == "synthetic_ci_fixture" or validity == "non_scientific_test_fixture":
            errors.append(
                f"Promotion rejection: Manifest '{manifest.get('manifest_id')}' is a "
                f"'{tier}' ({validity}) and cannot be promoted to certified scientific results."
            )

    attempts = manifest.get("attempts", [])
    cov = manifest.get("coverage_summary", {})

    if len(attempts) != cov.get("total_attempts"):
        errors.append(f"Attempt count mismatch: recorded {len(attempts)} != summary {cov.get('total_attempts')}")

    # Frozen universe verification
    univ = manifest.get("universe_manifest")
    if univ:
        expected_cnt = univ.get("expected_attempt_count")
        if expected_cnt is not None and len(attempts) != expected_cnt:
            errors.append(
                f"Frozen universe violation: recorded attempts {len(attempts)} != "
                f"expected universe attempts {expected_cnt}. Truncated manifest detected."
            )

        recorded_sha = univ.get("universe_sha256")
        if recorded_sha and len(attempts) == expected_cnt:
            attempt_keys = sorted(
                f"{a['item_id']}::{a['rung']}::{a.get('shot_mode', 'zero_shot')}::{a.get('sample_index', 0)}"
                for a in attempts
            )
            attempt_sha = hashlib.sha256(json.dumps(attempt_keys).encode("utf-8")).hexdigest()
            if attempt_sha != recorded_sha:
                errors.append(
                    f"Frozen universe hash mismatch: attempts hash {attempt_sha[:12]} != "
                    f"universe manifest {recorded_sha[:12]}"
                )

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
    if suite_path.is_file():
        current_suite_sha = hashlib.sha256(suite_path.read_bytes()).hexdigest()
        if manifest.get("suite_sha256") != current_suite_sha:
            errors.append(
                f"Manifest suite hash mismatch: manifest {manifest.get('suite_sha256')[:12]} != "
                f"current {current_suite_sha[:12]}"
            )

    return errors


def create_synthetic_items() -> list[dict[str, Any]]:
    """Create reproducible synthetic items across multiple document clusters for offline verification."""
    return [
        {
            "item_id": "SYNTH-DOCA-IDENT-001",
            "document_id": "DOC-PAPYRUS-A",
            "rung": "identify",
            "image_bytes": b"synthetic_palaeography_hieratic_glyph_01",
        },
        {
            "item_id": "SYNTH-DOCA-IDENT-002",
            "document_id": "DOC-PAPYRUS-A",
            "rung": "identify",
            "image_bytes": b"synthetic_palaeography_hieratic_glyph_02",
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
    """Create synthetic gold dictionary corresponding to synthetic items."""
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
    p_run.add_argument("--items", type=Path, default=None, help="Path to evaluation items JSON/YAML")
    p_run.add_argument("--model", type=str, default="mock-vision-v1")
    p_run.add_argument("--shot-mode", type=str, choices=["zero_shot", "few_shot", "both", "zero-shot", "few-shot"], default="both")
    p_run.add_argument("--output", type=Path, required=True, help="Path to save run manifest JSON")
    p_run.add_argument("--simulated-mode", type=str, default="normal", help="Simulation mode for mock adapter")
    p_run.add_argument("--weights-dir", type=Path, default=None, help="Local weights directory for open-weight VLM")

    # audit-manifest
    p_audit = subparsers.add_parser("audit-manifest", help="Audit run manifest completeness and integrity")
    p_audit.add_argument("--manifest", type=Path, required=True)
    p_audit.add_argument("--suite", type=Path, default=DEFAULT_SUITE_PATH)
    p_audit.add_argument("--items", type=Path, default=None)
    p_audit.add_argument("--require-certified", action="store_true", help="Reject synthetic CI fixtures")

    # score
    p_score = subparsers.add_parser("score", help="Score run manifest and generate report")
    p_score.add_argument("--manifest", type=Path, required=True)
    p_score.add_argument("--gold", type=Path, default=None)
    p_score.add_argument("--output", type=Path, default=None)
    p_score.add_argument("--allow-incomplete-gold", action="store_true", help="Permit missing gold without failing closed")

    # paired-compare
    p_comp = subparsers.add_parser("paired-compare", help="Compare two run manifests on identical items")
    p_comp.add_argument("--manifest-a", type=Path, required=True)
    p_comp.add_argument("--manifest-b", type=Path, required=True)
    p_comp.add_argument("--shot-mode-a", type=str, default=None, help="Condition filter for manifest A")
    p_comp.add_argument("--shot-mode-b", type=str, default=None, help="Condition filter for manifest B")
    p_comp.add_argument("--gold", type=Path, default=None)
    p_comp.add_argument("--output", type=Path, default=None)

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
                adapter = OpenWeightVLMAdapter(model_cfg, weights_dir=args.weights_dir)

            runner = VLMRunner(suite, demos, adapter, suite_path=args.suite, demos_path=args.demos)

            if args.items and args.items.is_file():
                items = load_json(args.items) if args.items.suffix == ".json" else load_yaml(args.items)
                items_tier = "verified_external_items"
            else:
                items = create_synthetic_items()
                items_tier = "synthetic_ci_items"

            shot_mode = args.shot_mode.replace("-", "_")
            manifest = runner.run_suite(items, shot_mode=shot_mode, items_tier=items_tier)

            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            print(f"PASS: Evaluation complete. Manifest written to {args.output}")
            print(f"  Execution tier: {manifest['execution_tier']}")
            print(f"  Attempts recorded: {manifest['coverage_summary']['total_attempts']}")
            print(f"  Coverage rate: {manifest['coverage_summary']['coverage_rate']}")
            return 0

        elif args.command == "audit-manifest":
            errors = audit_manifest(
                args.manifest,
                args.suite,
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
            gold = load_json(args.gold) if (args.gold and args.gold.is_file()) else create_synthetic_gold()
            report = score_manifest(
                manifest,
                gold,
                require_complete_gold=(not args.allow_incomplete_gold),
            )

            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
                print(f"Report written to {args.output}")

            print(f"PASS: Scored manifest '{manifest['manifest_id']}' (Channel: {report['scoring_channel']}):")
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
            gold = load_json(args.gold) if (args.gold and args.gold.is_file()) else create_synthetic_gold()

            comps = compare_manifests(
                manifest_a,
                manifest_b,
                gold,
                shot_mode_a=args.shot_mode_a,
                shot_mode_b=args.shot_mode_b,
            )
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(comps, indent=2), encoding="utf-8")
                print(f"Comparison written to {args.output}")

            print(f"PASS: Paired comparison ({manifest_a['model_key']} vs {manifest_b['model_key']}):")
            for c in comps:
                ci_str = str(c['delta_cluster_ci_95']) if c['delta_cluster_ci_95'] else f"[{c['delta_ci_status']}]"
                print(
                    f"  [{c['rung']}] Delta ({c['metric_id']}, {c['metric_direction']}): {c['score_delta']} "
                    f"(95% Clustered CI: {ci_str}) over N={c['paired_samples']} paired attempts"
                )
            return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
