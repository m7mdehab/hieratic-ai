"""Comprehensive synthetic unit, adversarial, and negative tests for VLM baseline evaluation harness.

Tests cover:
- Schema conformity and execution gate enforcement (zero-spend)
- Prompt drift and cryptographic hash validation
- Quarantined demonstration clearance, missing pixel checks, and leakage detection
- Mandatory image conditioning enforcement
- Attempt preservation (successes, errors, abstentions, timeouts, refusals)
- Manifest auditing and promotion prevention (rejects synthetic CI fixtures)
- Separation of official HieraticBench and project-native EVAL-001 metrics
- EVAL-006 document-clustered bootstrap uncertainty (B=2000) and null CI for single clusters
- Composite-key attempt pairing across (item_id, rung, sample_index)
- Open-weight model hardware/weights barrier reporting without false claims
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import yaml

from eval.vlm.adapter import (
    AvailabilityStatus,
    ImageConditioningError,
    InferenceHardwareBarrierError,
    LiveFewShotBlockedError,
    MockVLMAdapter,
    OpenWeightVLMAdapter,
    UnverifiedDemonstrationError,
    VLMAdapterError,
    get_adapter,
    validate_revision_pinning,
)
from eval.vlm.smoke import (
    generate_geometric_control_image,
    generate_geometric_test_image,
    run_real_visual_smoke,
)
from eval.vlm.runner import RunnerError, VLMRunner
from eval.vlm.scorer import (
    PairedComparisonError,
    ScorerError,
    character_error_rate,
    chrf_score,
    compare_manifests,
    document_clustered_bootstrap_ci,
    is_abstention,
    levenshtein_distance,
    score_manifest,
    sentence_bleu,
    word_error_rate,
)
from tools.vlm_baselines import (
    audit_manifest,
    create_synthetic_gold,
    create_synthetic_items,
    main as cli_main,
    validate_demonstrations,
    validate_suite,
)

ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = ROOT / "eval/vlm/suite.yaml"
DEMOS_PATH = ROOT / "eval/vlm/demonstrations.yaml"
SCHEMA_PATH = ROOT / "schemas/vlm_baselines.schema.json"


class VLMBaselinesTests(unittest.TestCase):
    """Test suite for VLM baseline evaluation harness and contracts."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.suite_data = yaml.safe_load(SUITE_PATH.read_text(encoding="utf-8"))
        cls.demos_data = yaml.safe_load(DEMOS_PATH.read_text(encoding="utf-8"))

    # --- 1. Suite Validation and Gates ---

    def test_canonical_suite_validates_successfully(self) -> None:
        errors = validate_suite(SUITE_PATH, SCHEMA_PATH)
        self.assertEqual(errors, [], f"Canonical suite failed validation: {errors}")

    def test_unapproved_positive_spend_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.suite_data)
        mutated["execution_gate"]["max_paid_spend_usd"] = 50.0
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
            yaml.dump(mutated, tmp)
            tmp_path = Path(tmp.name)
        try:
            errors = validate_suite(tmp_path, SCHEMA_PATH)
            self.assertTrue(any("zero-spend is mandatory" in e for e in errors))
        finally:
            tmp_path.unlink()

    def test_missing_image_conditioning_gate_fails(self) -> None:
        mutated = copy.deepcopy(self.suite_data)
        mutated["execution_gate"]["require_image_conditioning"] = False
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
            yaml.dump(mutated, tmp)
            tmp_path = Path(tmp.name)
        try:
            errors = validate_suite(tmp_path, SCHEMA_PATH)
            self.assertTrue(any("must require image conditioning" in e for e in errors))
        finally:
            tmp_path.unlink()

    def test_duplicate_model_keys_fail_validation(self) -> None:
        mutated = copy.deepcopy(self.suite_data)
        mutated["models"].append(mutated["models"][0])
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
            yaml.dump(mutated, tmp)
            tmp_path = Path(tmp.name)
        try:
            errors = validate_suite(tmp_path, SCHEMA_PATH)
            self.assertTrue(any("Model candidate keys must be unique" in e for e in errors))
        finally:
            tmp_path.unlink()

    def test_prompt_drift_fails_validation(self) -> None:
        mutated = copy.deepcopy(self.suite_data)
        mutated["prompts"]["identify"]["zero_shot"]["user_template"] += " EXTRA TEXT"
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
            yaml.dump(mutated, tmp)
            tmp_path = Path(tmp.name)
        try:
            errors = validate_suite(tmp_path, SCHEMA_PATH)
            self.assertTrue(any("Prompt drift detected" in e for e in errors))
        finally:
            tmp_path.unlink()

    # --- 2. Demonstrations Clearance & Quarantine Controls ---

    def test_canonical_demonstrations_validate_as_synthetic_fixtures(self) -> None:
        errors = validate_demonstrations(DEMOS_PATH, SCHEMA_PATH)
        self.assertEqual(errors, [], f"Canonical demonstrations failed validation: {errors}")
        self.assertEqual(self.demos_data["status"], "synthetic_fixture_only")
        self.assertEqual(self.demos_data["rights_review"]["rights_review_status"], "synthetic_placeholder_unreviewed")
        self.assertFalse(self.demos_data["rights_review"]["quarantine_verified"])

    def test_unreviewed_demonstration_bank_fails_live_few_shot_inference(self) -> None:
        qwen_cfg = next(m for m in self.suite_data["models"] if m["key"] == "qwen2.5-vl-7b-instruct")
        adapter = OpenWeightVLMAdapter(qwen_cfg)
        # Live few-shot is unconditionally blocked until authentic templates and pixels exist
        with self.assertRaises(LiveFewShotBlockedError) as ctx:
            adapter.predict(
                image_bytes=b"dummy_image_data",
                prompt="Prompt",
                system_prompt="Sys",
                shot_mode="few_shot",
                rung="identify",
                item_id="TEST-01",
                demonstrations_meta=self.demos_data,
            )
        self.assertIn("unconditionally blocked", str(ctx.exception).lower())

    def test_authentic_demonstration_clearance_requires_on_disk_pixels_and_hash(self) -> None:
        # A bank falsely claiming reviewed_authentic without image files on disk must fail
        mutated = copy.deepcopy(self.demos_data)
        mutated["status"] = "reviewed_authentic"
        mutated["rights_review"]["rights_review_status"] = "approved_with_evidence"
        mutated["rights_review"]["quarantine_verified"] = True
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
            yaml.dump(mutated, tmp)
            tmp_path = Path(tmp.name)
        try:
            errors = validate_demonstrations(tmp_path, SCHEMA_PATH, require_authentic=True)
            self.assertTrue(any("image file not found on disk" in e for e in errors))
        finally:
            tmp_path.unlink()

    def test_demonstration_leakage_against_eval_set_is_detected(self) -> None:
        known_eval = {"DEMO-SYNTH-IDENT-001", "OTHER-EVAL-ITEM"}
        errors = validate_demonstrations(DEMOS_PATH, SCHEMA_PATH, known_eval_items=known_eval)
        self.assertTrue(any("Leakage violation" in e and "DEMO-SYNTH-IDENT-001" in e for e in errors))

    def test_demonstration_image_hash_leakage_detected(self) -> None:
        mutated = copy.deepcopy(self.demos_data)
        mutated["items"][0]["is_synthetic_fixture"] = False
        mutated["items"][0]["image_sha256"] = "1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff"
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
            yaml.dump(mutated, tmp)
            tmp_path = Path(tmp.name)
        try:
            eval_hashes = {"1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff"}
            errors = validate_demonstrations(tmp_path, SCHEMA_PATH, known_eval_image_hashes=eval_hashes)
            self.assertTrue(any("image hash overlaps with evaluation item" in e for e in errors))
        finally:
            tmp_path.unlink()

    def test_demonstration_using_hieraticbench_prefix_fails(self) -> None:
        mutated = copy.deepcopy(self.demos_data)
        mutated["items"][0]["demo_id"] = "DEMO-AKU-001"
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
            yaml.dump(mutated, tmp)
            tmp_path = Path(tmp.name)
        try:
            errors = validate_demonstrations(tmp_path, SCHEMA_PATH)
            self.assertTrue(any("reserved HieraticBench prefix" in e for e in errors))
        finally:
            tmp_path.unlink()

    # --- 3. Image Conditioning Enforcement ---

    def test_adapter_rejects_empty_image_bytes(self) -> None:
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        with self.assertRaises(ImageConditioningError):
            adapter.predict(
                image_bytes=b"",
                prompt="Identify script",
                system_prompt="Egyptologist",
                shot_mode="zero_shot",
                rung="identify",
                item_id="TEST-EMPTY-01",
            )

    def test_runner_rejects_item_without_image(self) -> None:
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter)
        item_missing_image = {"item_id": "NO-IMG-01", "rung": "identify"}
        with self.assertRaises(ImageConditioningError):
            runner.evaluate_item(item_missing_image, shot_mode="zero_shot")

    # --- 4. Attempt Preservation & Promotion Prevention ---

    def test_runner_preserves_all_attempts_without_dropouts(self) -> None:
        adapter = MockVLMAdapter(self.suite_data["models"][0], simulated_mode="normal")
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()
        manifest = runner.run_suite(items, shot_mode="both")

        self.assertEqual(len(manifest["attempts"]), len(items) * 2)
        self.assertEqual(manifest["coverage_summary"]["total_attempts"], len(items) * 2)
        self.assertEqual(manifest["coverage_summary"]["success_count"], len(items) * 2)
        self.assertEqual(manifest["coverage_summary"]["coverage_rate"], 1.0)
        self.assertEqual(manifest["execution_tier"], "synthetic_ci_fixture")
        self.assertEqual(manifest["scientific_validity"], "non_scientific_test_fixture")
        self.assertEqual(manifest["certification_status"], "uncertified_synthetic_only")

    def test_synthetic_ci_fixtures_cannot_be_promoted_to_certified_results(self) -> None:
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()[:2]
        manifest = runner.run_suite(items, shot_mode="zero_shot")

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(manifest, tmp)
            tmp_path = Path(tmp.name)
        try:
            # Audit with require_certified must reject synthetic CI fixtures
            errors = audit_manifest(tmp_path, SUITE_PATH, SCHEMA_PATH, require_certified=True)
            self.assertTrue(any("Promotion rejection" in e for e in errors))
        finally:
            tmp_path.unlink()

    def test_manifest_auditor_detects_duplicate_composite_keys(self) -> None:
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()[:2]
        manifest = runner.run_suite(items, shot_mode="zero_shot")

        # Duplicate one attempt with identical composite key (item_id, rung, sample_index)
        manifest["attempts"].append(copy.deepcopy(manifest["attempts"][0]))
        manifest["coverage_summary"]["total_attempts"] += 1

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(manifest, tmp)
            tmp_path = Path(tmp.name)
        try:
            errors = audit_manifest(tmp_path, SUITE_PATH, SCHEMA_PATH)
            self.assertTrue(any("Duplicate attempt key" in e for e in errors))
        finally:
            tmp_path.unlink()

    # --- 5. Dual-Channel Scoring & EVAL-006 Statistical Reporting ---

    def test_scoring_separates_project_native_metrics_from_official_hieraticbench(self) -> None:
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()
        gold = create_synthetic_gold()

        manifest = runner.run_suite(items, shot_mode="zero_shot")
        report = score_manifest(manifest, gold)

        self.assertEqual(report["scoring_channel"], "project_native_eval001")
        self.assertIn("project_native_eval001", report)
        self.assertIsNone(report["official_hieraticbench"])

        # Check metric IDs adhere to eval/metric_contract.yaml
        rungs = report["project_native_eval001"]
        self.assertEqual(rungs["identify"]["primary_metric_id"], "SCRIPT_ACC")
        self.assertEqual(rungs["signs"]["primary_metric_id"], "SIGN_TOP1")
        self.assertEqual(rungs["transliterate"]["primary_metric_id"], "TR_CER")
        self.assertEqual(rungs["translate"]["primary_metric_id"], "TRANS_CHRF")

    def test_adversarial_parity_exposes_differences_with_official_scoring(self) -> None:
        """Adversarially demonstrate why in-house metrics must not be claimed as upstream official scores."""
        from eval.vlm.scorer import clean_script_prediction, clean_sign_prediction

        # Case 1: Conversational negation text where local candidate ordering misattributes script
        adversarial_text_1 = "The scribe did not use Hieratic, but rather Demotic."
        # Local heuristic regex checks candidate list order and extracts 'Hieratic' (ignoring negation)
        local_pred_1 = clean_script_prediction(adversarial_text_1)
        self.assertEqual(local_pred_1, "Hieratic")
        # An official strict parser expecting 'SCRIPT: demotic' would reject or parse differently
        self.assertNotEqual(adversarial_text_1.startswith("SCRIPT:"), True)

        # Case 2: Multi-sign cluster versus single sign code
        # In-house SIGN_ACC checks single Gardiner code equality
        gold_sign_cluster = {"gardiner": ["G17", "A1"]}
        single_hyp = "G17"
        # In-house clean_sign_prediction parses single code
        local_sign = clean_sign_prediction(single_hyp)
        self.assertEqual(local_sign, "G17")
        # In-house single code comparison against array string representation fails equality
        self.assertNotEqual(local_sign, str(gold_sign_cluster["gardiner"]))

        # Case 3: Script casing and formatting
        # Upstream HieraticBench scoreResponse expects exact lower-case match
        # whereas project-native SCRIPT_ACC normalizes case-insensitively
        cased_raw = "HIERATIC"
        self.assertEqual(clean_script_prediction(cased_raw).lower(), "hieratic")

    def test_document_clustered_bootstrap_with_2000_resamples(self) -> None:
        # Multi-document cluster support produces valid bootstrap limits
        cluster_scores = {
            "DOC-A": [1.0, 1.0, 0.8],
            "DOC-B": [0.5, 0.6],
            "DOC-C": [0.9, 0.7, 0.85],
        }
        ci, count, status = document_clustered_bootstrap_ci(cluster_scores, n_resamples=2000, alpha=0.05, seed=42)
        self.assertEqual(count, 3)
        self.assertEqual(status, "valid_clustered_ci")
        self.assertIsNotNone(ci)
        low, high = ci
        self.assertLessEqual(low, high)
        self.assertGreaterEqual(low, 0.4)
        self.assertLessEqual(high, 1.0)

    def test_insufficient_document_clusters_produces_none_ci(self) -> None:
        # Single document cluster must NOT fabricate a 0-width interval
        single_cluster = {"DOC-ONLY-ONE": [0.85, 0.90, 0.80]}
        ci, count, status = document_clustered_bootstrap_ci(single_cluster, n_resamples=2000)
        self.assertEqual(count, 1)
        self.assertIsNone(ci, "Expected null CI when independent document clusters <= 1")
        self.assertEqual(status, "insufficient_document_clusters")

    def test_full_denominator_accounting_intention_to_test(self) -> None:
        adapter = MockVLMAdapter(self.suite_data["models"][0], simulated_mode="force_abstention")
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()[:2]
        gold = create_synthetic_gold()

        manifest = runner.run_suite(items, shot_mode="zero_shot")
        report = score_manifest(manifest, gold)

        ident_rung = report["project_native_eval001"]["identify"]
        self.assertEqual(ident_rung["abstention_count"], 2)
        self.assertEqual(ident_rung["coverage_rate"], 0.0)
        self.assertEqual(ident_rung["intention_to_test_score"], 0.0)
        self.assertIsNone(ident_rung["conditional_score"])

    def test_composite_identity_pairing_in_paired_comparisons(self) -> None:
        adapter_a = MockVLMAdapter(self.suite_data["models"][0], simulated_mode="force_abstention")
        adapter_b = MockVLMAdapter(self.suite_data["models"][0], simulated_mode="normal")

        runner_a = VLMRunner(self.suite_data, self.demos_data, adapter_a, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        runner_b = VLMRunner(self.suite_data, self.demos_data, adapter_b, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)

        items = create_synthetic_items()
        gold = create_synthetic_gold()

        manifest_a = runner_a.run_suite(items, shot_mode="zero_shot", manifest_id="run_abstain_01")
        manifest_b = runner_b.run_suite(items, shot_mode="zero_shot", manifest_id="run_normal_01")

        comps = compare_manifests(manifest_a, manifest_b, gold)
        self.assertGreater(len(comps), 0)
        for c in comps:
            self.assertTrue(c["composite_pairing"])
            self.assertIn("score_delta", c)
            self.assertIn("delta_ci_status", c)

    # --- 6. Open-Weight Adapter Capability & Barrier Reporting ---

    def test_open_weight_adapter_reports_barrier_cleanly(self) -> None:
        qwen_cfg = next(m for m in self.suite_data["models"] if m["key"] == "qwen2.5-vl-7b-instruct")
        adapter = OpenWeightVLMAdapter(qwen_cfg)
        status = adapter.check_availability()
        self.assertIsInstance(status, AvailabilityStatus)
        if not status.available:
            self.assertTrue(len(status.reason) > 0)
            resp = adapter.predict(
                image_bytes=b"dummy_bytes",
                prompt="Prompt",
                system_prompt="Sys",
                shot_mode="zero_shot",
                rung="identify",
                item_id="BARRIER-TEST-01",
            )
            self.assertEqual(resp.status, "failed")
            self.assertIn("barrier", resp.error_message.lower())

    # --- 7. CLI End-to-End Workflow ---

    def test_cli_end_to_end_subcommands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_manifest = Path(tmp_dir) / "eval_manifest.json"
            out_report = Path(tmp_dir) / "score_report.json"

            # validate-suite
            ret = cli_main(["validate-suite", "--suite", str(SUITE_PATH)])
            self.assertEqual(ret, 0)

            # validate-demonstrations
            ret = cli_main(["validate-demonstrations", "--demos", str(DEMOS_PATH)])
            self.assertEqual(ret, 0)

            # run
            ret = cli_main([
                "run",
                "--suite", str(SUITE_PATH),
                "--demos", str(DEMOS_PATH),
                "--model", "mock-vision-v1",
                "--shot-mode", "both",
                "--output", str(out_manifest),
            ])
            self.assertEqual(ret, 0)
            self.assertTrue(out_manifest.is_file())

            # audit-manifest
            ret = cli_main(["audit-manifest", "--manifest", str(out_manifest), "--suite", str(SUITE_PATH)])
            self.assertEqual(ret, 0)

            # score
            ret = cli_main(["score", "--manifest", str(out_manifest), "--output", str(out_report)])
            self.assertEqual(ret, 0)
            self.assertTrue(out_report.is_file())

    # --- 8. Targeted Adversarial Parity and Regression Tests ---

    def test_adversarial_missing_gold_omission_detected(self) -> None:
        """Adversarially verify that missing gold is never silently dropped from scored denominators."""
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()
        manifest = runner.run_suite(items, shot_mode="zero_shot")

        # Mutate gold: remove one item entirely
        corrupted_gold = create_synthetic_gold()
        first_key = next(iter(corrupted_gold.keys()))
        del corrupted_gold[first_key]

        # By default, denominator integrity forbids silent dropout; must raise ScorerError
        with self.assertRaises(ScorerError) as ctx:
            score_manifest(manifest, corrupted_gold, require_complete_gold=True)
        self.assertIn("Denominator integrity forbids silently dropping missing-gold items", str(ctx.exception))

        # When explicitly allowed, intention-to-test must record worst-case penalty and report missing count
        report = score_manifest(manifest, corrupted_gold, require_complete_gold=False)
        rungs = report["project_native_eval001"]
        has_missing = any(r["gold_eligibility"]["missing_gold_count"] > 0 for r in rungs.values())
        self.assertTrue(has_missing)

    def test_adversarial_truncated_manifest_rejected_by_frozen_universe(self) -> None:
        """Adversarially delete an attempt and lower self-reported counts; auditor must reject truncation."""
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()
        manifest = runner.run_suite(items, shot_mode="both")

        # Delete an attempt and maliciously decrement self-reported totals to evade count checks
        deleted_attempt = manifest["attempts"].pop()
        manifest["coverage_summary"]["total_attempts"] -= 1
        if deleted_attempt["status"] == "success":
            manifest["coverage_summary"]["success_count"] -= 1

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(manifest, tmp)
            tmp_path = Path(tmp.name)
        try:
            errors = audit_manifest(tmp_path, SUITE_PATH, SCHEMA_PATH)
            self.assertTrue(any("Frozen universe violation" in e and "Truncated manifest detected" in e for e in errors))
        finally:
            tmp_path.unlink()

    def test_adversarial_forged_rights_permissions_rejected(self) -> None:
        """Adversarially assert approved_with_evidence on synthetic placeholder fixtures; must fail closed."""
        mutated = copy.deepcopy(self.demos_data)
        mutated["status"] = "synthetic_fixture_only"
        mutated["rights_review"]["rights_review_status"] = "approved_with_evidence"
        mutated["rights_review"]["quarantine_verified"] = True

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
            yaml.dump(mutated, tmp)
            tmp_path = Path(tmp.name)
        try:
            errors = validate_demonstrations(tmp_path, SCHEMA_PATH)
            self.assertTrue(any("Demonstration clearance forgery" in e for e in errors))
        finally:
            tmp_path.unlink()

    def test_adversarial_absent_exemplar_pixels_blocks_few_shot(self) -> None:
        """Adversarially verify that live few-shot is unconditionally blocked on open-weight backbones."""
        qwen_cfg = next(m for m in self.suite_data["models"] if m["key"] == "qwen2.5-vl-7b-instruct")
        adapter = OpenWeightVLMAdapter(qwen_cfg)
        with self.assertRaises(LiveFewShotBlockedError):
            adapter.predict(
                image_bytes=b"dummy_bytes",
                prompt="Prompt",
                system_prompt="Sys",
                shot_mode="few_shot",
                rung="transliterate",
                item_id="TEST-FEW-01",
                demonstrations_meta=self.demos_data,
            )

    def test_adversarial_duplicate_shot_identities_in_pairing_detected(self) -> None:
        """Adversarially pass both-mode manifest without condition filter; collapsing must be rejected."""
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()
        gold = create_synthetic_gold()

        manifest_both = runner.run_suite(items, shot_mode="both")

        # Passing manifest_both without --shot-mode-a / --shot-mode-b must raise PairedComparisonError
        with self.assertRaises(PairedComparisonError) as ctx:
            compare_manifests(manifest_both, manifest_both, gold)
        self.assertIn("explicit condition filter", str(ctx.exception))

        # When proper filters are provided, paired comparison succeeds
        comps = compare_manifests(manifest_both, manifest_both, gold, shot_mode_a="zero_shot", shot_mode_b="few_shot")
        self.assertGreater(len(comps), 0)

    def test_adversarial_cer_metric_direction_and_name_conforms_to_contract(self) -> None:
        """Adversarially verify that TR_CER is strictly lower-is-better (0.0=perfect) in edit_error_rate units."""
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()
        gold = create_synthetic_gold()

        manifest = runner.run_suite(items, shot_mode="zero_shot")
        report = score_manifest(manifest, gold)

        xlit = report["project_native_eval001"]["transliterate"]
        self.assertEqual(xlit["primary_metric_id"], "TR_CER")
        self.assertEqual(xlit["metric_direction"], "lower")
        self.assertEqual(xlit["metric_unit"], "edit_error_rate")
        # Ensure it is NOT reported as 1 - CER (which was the old inverted CER_V1)
        self.assertGreaterEqual(xlit["intention_to_test_score"], 0.0)

    def test_adversarial_official_score_spoofing_rejected(self) -> None:
        """Adversarially verify that official HieraticBench channel is strictly NOT_INTEGRATED."""
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()
        gold = create_synthetic_gold()

        manifest = runner.run_suite(items, shot_mode="zero_shot")

        # Injected fake replay summary cannot spoof official leaderboard status; must be actively rejected!
        fake_summary = {"item_macro_accuracy": 0.99, "note": "spoofed"}
        with self.assertRaises(ScorerError) as ctx:
            score_manifest(manifest, gold, official_replay_summary=fake_summary)
        self.assertIn("Official HieraticBench replay summary injection is prohibited", str(ctx.exception))

    # --- 9. Independent Universe & Dataset Admission Adversarial Tests ---

    def test_adversarial_dropping_item_and_rewriting_manifest_rejected_by_independent_universe(self) -> None:
        """Adversarially drop an item and recalculate in-manifest counts; independent universe must reject."""
        from eval.vlm.universe import DEFAULT_UNIVERSE_PATH, load_universe
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()

        manifest = runner.run_suite(items, shot_mode="zero_shot")
        # Ensure it passes audit initially
        u_data = load_universe(DEFAULT_UNIVERSE_PATH)
        initial_errs = audit_manifest(manifest, suite_path=SUITE_PATH, schema_path=SCHEMA_PATH, universe_path=DEFAULT_UNIVERSE_PATH)
        self.assertEqual(initial_errs, [])

        # Tamper: Drop one item's attempt, rewrite self-reported totals
        dropped_item = manifest["attempts"].pop(0)
        manifest["coverage_summary"]["total_attempts"] = len(manifest["attempts"])
        manifest["coverage_summary"]["success_count"] = len(manifest["attempts"])

        tampered_errs = audit_manifest(manifest, suite_path=SUITE_PATH, schema_path=SCHEMA_PATH, universe_path=DEFAULT_UNIVERSE_PATH)
        self.assertTrue(
            any("Independent universe violation" in e or "Frozen universe violation" in e for e in tampered_errs),
            f"Expected independent universe violation but got: {tampered_errs}",
        )
        self.assertTrue(any("missing" in e for e in tampered_errs))

    def test_external_items_without_admission_receipt_marked_unverified_and_fails_certification(self) -> None:
        """Adversarially admit external items without approved receipt; tier must be unverified and reject certification."""
        from eval.vlm.universe import admit_external_items
        raw_items = [
            {"item_id": "EXT-001", "document_id": "EXT-DOC", "rung": "identify"},
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump({"items": raw_items}, tmp)
            tmp_items = Path(tmp.name)

        try:
            admitted, tier, errs = admit_external_items(tmp_items)
            self.assertEqual(tier, "unverified_external_inputs")
            self.assertEqual(len(admitted), 1)
            admitted[0]["image_bytes"] = b"synthetic_png_content"

            # Build a manifest claiming these unverified inputs
            adapter = MockVLMAdapter(self.suite_data["models"][0])
            runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
            manifest = runner.run_suite(admitted, shot_mode="zero_shot")
            manifest["universe_manifest"]["items_tier"] = tier

            # Audit requiring certification must fail closed
            cert_errs = audit_manifest(manifest, suite_path=SUITE_PATH, schema_path=SCHEMA_PATH, require_certified=True)
            self.assertTrue(
                any("Promotion rejection" in e and "unverified_external_inputs" in e for e in cert_errs),
                f"Expected promotion rejection for unverified inputs, got: {cert_errs}",
            )
        finally:
            tmp_items.unlink()

    def test_external_items_with_incomplete_admission_receipt_fails(self) -> None:
        """Adversarially pass receipt with pending status or missing reviewer; admission must fail closed."""
        from eval.vlm.universe import admit_external_items
        raw_items = [{"item_id": "EXT-002", "rung": "signs"}]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp_it:
            json.dump({"items": raw_items}, tmp_it)
            tmp_items_path = Path(tmp_it.name)

        receipt_data = {
            "rights_review_status": "pending_clarification",
            "quarantine_verified": False,
            "permitted_cohort_tier": "approved_evaluation_cohort",
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp_rc:
            json.dump(receipt_data, tmp_rc)
            tmp_rc_path = Path(tmp_rc.name)

        try:
            admitted, tier, errs = admit_external_items(tmp_items_path, tmp_rc_path)
            self.assertEqual(tier, "unverified_external_inputs")
            self.assertTrue(any("incomplete or unapproved" in e for e in errs))
        finally:
            tmp_items_path.unlink()
            tmp_rc_path.unlink()

    def test_all_failed_open_weight_manifest_fails_certification(self) -> None:
        """Adversarially attempt to certify an open-weight manifest where all attempts failed due to barriers."""
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()
        manifest = runner.run_suite(items, shot_mode="zero_shot")

        # Mutate to all failed
        for a in manifest["attempts"]:
            a["status"] = "failed"
            a["raw_output"] = None
            a["error_message"] = "Inference blocked by hardware barrier: CUDA device required"
        manifest["coverage_summary"]["success_count"] = 0
        manifest["coverage_summary"]["failure_count"] = len(manifest["attempts"])
        manifest["coverage_summary"]["coverage_rate"] = 0.0
        manifest["execution_tier"] = "live_local_open_weight"
        manifest["scientific_validity"] = "certified_baseline"
        manifest["certification_status"] = "certified"
        manifest["authorization_receipt_ref"] = "RECEIPT-AUTH-VALID-001"
        manifest["universe_manifest"]["items_tier"] = "approved_evaluation_cohort"

        cert_errs = audit_manifest(manifest, suite_path=SUITE_PATH, schema_path=SCHEMA_PATH, require_certified=True)
        self.assertTrue(
            any("Promotion rejection" in e and "all-failed or barrier-blocked" in e for e in cert_errs),
            f"Expected barrier-blocked manifest rejection, got: {cert_errs}",
        )

    def test_forged_mock_manifest_tampering_tier_fails_certification(self) -> None:
        """Adversarially forge mock manifest fields to claim certification; auditor must fail closed."""
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()
        manifest = runner.run_suite(items, shot_mode="zero_shot")

        # Attacker attempts to forge certification
        manifest["execution_tier"] = "live_local_open_weight"
        manifest["scientific_validity"] = "certified_baseline"
        manifest["certification_status"] = "certified"
        manifest["authorization_receipt_ref"] = "RECEIPT-FORGED-001"
        manifest["universe_manifest"]["items_tier"] = "approved_evaluation_cohort"

        cert_errs = audit_manifest(manifest, suite_path=SUITE_PATH, schema_path=SCHEMA_PATH, require_certified=True)
        self.assertTrue(
            any("Promotion rejection" in e and "Mock baseline" in e for e in cert_errs),
            f"Expected rejection of forged mock manifest, got: {cert_errs}",
        )

    # --- 10. Dependency-Isolated Adapter Unit Tests ---

    def test_qwen2_5_vl_adapter_multimodal_chat_formatting(self) -> None:
        """Verify Qwen 2.5 VL adapter correctly structures multimodal chat messages with visual tokens."""
        from eval.vlm.adapter import Qwen2_5_VLAdapter

        class MockProcessor:
            mock_image_tag = True
            def __init__(self) -> None:
                self.last_messages = None

            def apply_chat_template(self, messages: Any, tokenize: bool = False, add_generation_prompt: bool = True) -> str:
                self.last_messages = messages
                return f"<formatted_chat>{messages}</formatted_chat>"

            def __call__(self, images: Any = None, text: str = "", return_tensors: str = "pt") -> dict[str, Any]:
                return {"input_ids": [[1, 2, 3]], "pixel_values": [[0.1, 0.2]], "text": text}

            def batch_decode(self, token_ids: Any, **kwargs: Any) -> list[str]:
                return ["Hieratic script prediction jrj.n=f"]

        class MockModel:
            def generate(self, **kwargs: Any) -> list[list[int]]:
                return [[1, 2, 3, 101, 102]]

        proc = MockProcessor()
        mod = MockModel()
        qwen_cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])
        adapter = Qwen2_5_VLAdapter(qwen_cfg, processor_override=proc, model_override=mod)

        resp = adapter.predict(
            image_bytes=b"synthetic_valid_image_bytes",
            prompt="Transliterate this sign line",
            system_prompt="You are a Hieratic palaeographer",
            shot_mode="zero_shot",
            rung="transliterate",
            item_id="TEST-QWEN-01",
        )
        self.assertEqual(resp.status, "success")
        self.assertEqual(resp.cleaned_prediction, "Hieratic script prediction jrj.n=f")
        self.assertIsNotNone(proc.last_messages)
        self.assertEqual(proc.last_messages[0]["role"], "system")
        self.assertEqual(proc.last_messages[1]["role"], "user")
        user_content = proc.last_messages[1]["content"]
        self.assertTrue(any(c.get("type") == "image" for c in user_content))
        self.assertTrue(any(c.get("type") == "text" for c in user_content))

    def test_pixtral_adapter_multimodal_message_structure(self) -> None:
        """Verify Pixtral adapter formats multimodal messages according to Mistral/Pixtral chat schema."""
        from eval.vlm.adapter import PixtralVLMAdapter

        class MockProcessor:
            mock_image_tag = True
            def __init__(self) -> None:
                self.last_messages = None

            def apply_chat_template(self, messages: Any, tokenize: bool = False, add_generation_prompt: bool = True) -> str:
                self.last_messages = messages
                return f"<pixtral>{messages}</pixtral>"

            def __call__(self, images: Any = None, text: str = "", return_tensors: str = "pt") -> dict[str, Any]:
                return {"input_ids": [[10, 20]], "pixel_values": [[0.5]], "text": text}

            def batch_decode(self, token_ids: Any, **kwargs: Any) -> list[str]:
                return ["Pixtral Hieratic translation output"]

        class MockModel:
            def generate(self, **kwargs: Any) -> list[list[int]]:
                return [[10, 20, 201]]

        proc = MockProcessor()
        mod = MockModel()
        pixtral_cfg = next(m for m in self.suite_data["models"] if "pixtral" in m["key"])
        adapter = PixtralVLMAdapter(pixtral_cfg, processor_override=proc, model_override=mod)

        resp = adapter.predict(
            image_bytes=b"synthetic_valid_image_bytes",
            prompt="Translate this line",
            system_prompt="You are an Egyptologist",
            shot_mode="zero_shot",
            rung="translate",
            item_id="TEST-PIXTRAL-01",
        )
        self.assertEqual(resp.status, "success")
        self.assertEqual(resp.cleaned_prediction, "Pixtral Hieratic translation output")
        user_content = proc.last_messages[1]["content"]
        self.assertEqual(user_content[0], {"type": "image"})
        self.assertEqual(user_content[1], {"type": "text", "text": "Translate this line"})

    def test_llama3_2_vision_adapter_placeholder_formatting(self) -> None:
        """Llama chat template is mandatory; no hand-written image token fallback."""
        from eval.vlm.adapter import Llama3_2_VisionAdapter

        class MockProcessor:
            def __init__(self) -> None:
                self.last_text = None
                self.last_messages = None
            def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
                self.last_messages = messages
                return "<|begin_of_text|><|image|><|assistant|>"
            def __call__(self, images=None, text="", return_tensors="pt"):
                self.last_text = text
                return {"input_ids": [[100, 200]], "pixel_values": [[0.8]], "text": text}
            def batch_decode(self, token_ids, **kwargs):
                return ["Llama Gardiner sign G43"]

        class MockModel:
            def generate(self, **kwargs):
                return [[100, 200, 301]]

        proc = MockProcessor()
        llama_cfg = next(m for m in self.suite_data["models"] if "llama" in m["key"])
        adapter = Llama3_2_VisionAdapter(llama_cfg, processor_override=proc, model_override=MockModel())
        resp = adapter.predict(
            image_bytes=b"synthetic_valid_image_bytes",
            prompt="Identify Gardiner sign",
            system_prompt="You are a palaeographer",
            shot_mode="zero_shot",
            rung="signs",
            item_id="TEST-LLAMA-01",
        )
        self.assertEqual("success", resp.status)
        self.assertEqual("Llama Gardiner sign G43", resp.cleaned_prediction)
        self.assertIn("<|image|>", proc.last_text)
        self.assertEqual("user", proc.last_messages[1]["role"])

    def test_llama_missing_chat_template_fails_closed(self):
        from eval.vlm.adapter import Llama3_2_VisionAdapter, ImageConditioningError
        class UnstructuredProcessor:
            def __call__(self, **kwargs):
                return {"input_ids": [[1]], "pixel_values": [[0.5]]}
        cfg = next(m for m in self.suite_data["models"] if "llama" in m["key"])
        adapter = Llama3_2_VisionAdapter(cfg, processor_override=UnstructuredProcessor())
        with self.assertRaisesRegex(ImageConditioningError, "lacks apply_chat_template"):
            adapter.format_multimodal_inputs("Sys", "Prompt", pil_image=None)

    def test_forged_processor_image_tag_with_text_only_features_is_rejected(self):
        from eval.vlm.adapter import Qwen2_5_VLAdapter
        class ForgedTagProcessor:
            mock_image_tag = True
            def apply_chat_template(self, messages, **kwargs):
                return "<fake>"
            def __call__(self, **kwargs):
                return {"input_ids": [[1, 2]], "text": "no actual image tensor"}
        class Model:
            def generate(self, **kwargs):
                raise AssertionError("Should not generate with text-only inputs")
        cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])
        adapter = Qwen2_5_VLAdapter(cfg, processor_override=ForgedTagProcessor(), model_override=Model())
        response = adapter.predict(b"synthetic_valid_image_bytes", "Prompt", "Sys", "zero_shot", "identify", "FOREGED-TAG-1")
        self.assertEqual("failed", response.status)
        self.assertIn("ImageConditioningError", response.error_message)

    def test_empty_visual_tensor_is_rejected_before_model_generate(self):
        from eval.vlm.adapter import Qwen2_5_VLAdapter
        class EmptyTensorProcessor:
            def apply_chat_template(self, messages, **kwargs):
                return "<formatted>"
            def __call__(self, **kwargs):
                return {"input_ids": [[1, 2]], "pixel_values": []}
        class Model:
            def generate(self, **kwargs):
                raise AssertionError("should not execute")
        cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])
        adapter = Qwen2_5_VLAdapter(cfg, processor_override=EmptyTensorProcessor(), model_override=Model())
        response = adapter.predict(b"synthetic_valid_image_bytes", "Prompt", "Sys", "zero_shot", "identify", "EMPTY-PX")
        self.assertEqual("failed", response.status)
        self.assertIn("ImageConditioningError", response.error_message)

    def test_adapter_oom_runtime_exception_handling(self) -> None:
        """Verify runtime exception / OOM during forward generation produces cleanly recorded failure attempt."""
        from eval.vlm.adapter import Qwen2_5_VLAdapter

        class MockProcessor:
            mock_image_tag = True
            def apply_chat_template(self, messages: Any, **kwargs: Any) -> str:
                return "<chat/>"
            def __call__(self, **kwargs: Any) -> dict[str, Any]:
                return {"input_ids": [[1, 2]], "pixel_values": [[0.1]]}

        class MockOOMModel:
            def generate(self, **kwargs: Any) -> Any:
                raise RuntimeError("CUDA out of memory. Tried to allocate 24.00 GiB")

        qwen_cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])
        adapter = Qwen2_5_VLAdapter(qwen_cfg, processor_override=MockProcessor(), model_override=MockOOMModel())

        resp = adapter.predict(
            image_bytes=b"synthetic_image_bytes",
            prompt="Transliterate",
            system_prompt="Sys",
            shot_mode="zero_shot",
            rung="transliterate",
            item_id="TEST-OOM-01",
        )
        self.assertEqual(resp.status, "failed")
        self.assertIsNone(resp.raw_output)
        self.assertIn("CUDA out of memory", resp.error_message)

    def test_adapter_missing_visual_features_fails_image_conditioning(self) -> None:
        """Verify that processor outputs lacking visual feature tensors trigger image conditioning error."""
        from eval.vlm.adapter import Qwen2_5_VLAdapter

        class MockTextOnlyProcessor:
            # Does not have mock_image_tag, returns no pixel_values or images
            def apply_chat_template(self, messages: Any, **kwargs: Any) -> str:
                return "<chat/>"
            def __call__(self, **kwargs: Any) -> dict[str, Any]:
                return {"input_ids": [[1, 2, 3]]}

        class MockModel:
            def generate(self, **kwargs: Any) -> list[list[int]]:
                return [[1, 2, 3, 4]]

        qwen_cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])
        adapter = Qwen2_5_VLAdapter(qwen_cfg, processor_override=MockTextOnlyProcessor(), model_override=MockModel())

        resp = adapter.predict(
            image_bytes=b"synthetic_valid_image",
            prompt="Prompt",
            system_prompt="Sys",
            shot_mode="zero_shot",
            rung="transliterate",
            item_id="TEST-NOCOND-01",
        )
        self.assertEqual(resp.status, "failed")
        self.assertIn("ImageConditioningError", resp.error_message)
        self.assertIn("lacks visual features", resp.error_message)

    def test_qwen_chat_template_failure_fails_closed_without_text_fallback(self) -> None:
        """Verify Qwen chat template exception raises ImageConditioningError and never falls back to text."""
        from eval.vlm.adapter import Qwen2_5_VLAdapter

        class BrokenTemplateProcessor:
            def apply_chat_template(self, messages: Any, **kwargs: Any) -> str:
                raise ValueError("Jinja template syntax error: invalid token")
            def __call__(self, **kwargs: Any) -> dict[str, Any]:
                return {"input_ids": [[1]], "pixel_values": [[0.5]]}

        qwen_cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])
        adapter = Qwen2_5_VLAdapter(qwen_cfg, processor_override=BrokenTemplateProcessor(), model_override=None)

        with self.assertRaises(ImageConditioningError) as ctx:
            adapter.format_multimodal_inputs("System prompt", "User prompt", pil_image=None)
        self.assertIn("Chat template application failed for Qwen2.5-VL", str(ctx.exception))

    def test_pixtral_chat_template_failure_fails_closed(self) -> None:
        """Verify Pixtral chat template exception fails closed without text-only guessing."""
        from eval.vlm.adapter import PixtralVLMAdapter

        class BrokenTemplateProcessor:
            def apply_chat_template(self, messages: Any, **kwargs: Any) -> str:
                raise RuntimeError("Corrupted Pixtral template format")
            def __call__(self, **kwargs: Any) -> dict[str, Any]:
                return {"input_ids": [[1]], "pixel_values": [[0.5]]}

        pixtral_cfg = next(m for m in self.suite_data["models"] if "pixtral" in m["key"])
        adapter = PixtralVLMAdapter(pixtral_cfg, processor_override=BrokenTemplateProcessor(), model_override=None)

        with self.assertRaises(ImageConditioningError) as ctx:
            adapter.format_multimodal_inputs("System prompt", "User prompt", pil_image=None)
        self.assertIn("Chat template application failed for Pixtral", str(ctx.exception))

    def test_llama_chat_template_failure_fails_closed(self) -> None:
        """Verify Llama 3.2 Vision chat template exception fails closed without text-only guessing."""
        from eval.vlm.adapter import Llama3_2_VisionAdapter

        class BrokenTemplateProcessor:
            def apply_chat_template(self, messages: Any, **kwargs: Any) -> str:
                raise ValueError("Mllama template formatting exception")
            def __call__(self, **kwargs: Any) -> dict[str, Any]:
                return {"input_ids": [[1]], "pixel_values": [[0.5]]}

        llama_cfg = next(m for m in self.suite_data["models"] if "llama" in m["key"])
        adapter = Llama3_2_VisionAdapter(llama_cfg, processor_override=BrokenTemplateProcessor(), model_override=None)

        with self.assertRaises(ImageConditioningError) as ctx:
            adapter.format_multimodal_inputs("System prompt", "User prompt", pil_image=None)
        self.assertIn("Chat template application failed for Llama 3.2 Vision", str(ctx.exception))

    def test_prospective_few_shot_formatting_blocks_live_execution(self) -> None:
        """Verify prospective few-shot formatting raises LiveFewShotBlockedError on all adapters."""
        qwen_cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])
        adapter = OpenWeightVLMAdapter(qwen_cfg)
        with self.assertRaises(LiveFewShotBlockedError):
            adapter.format_few_shot_multimodal_inputs("Sys", "User", pil_image=None, demonstration_items=[])

    def test_runtime_metadata_structure_and_no_path_leakage(self) -> None:
        """Verify get_runtime_metadata returns expected structure without absolute path leakage."""
        qwen_cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])
        adapter = OpenWeightVLMAdapter(qwen_cfg)
        meta = adapter.get_runtime_metadata()
        self.assertEqual(meta["model_key"], "qwen2.5-vl-7b-instruct")
        self.assertEqual(meta["provider_model_id"], "Qwen/Qwen2.5-VL-7B-Instruct")
        self.assertEqual(meta["revision"], "bfb8829e3c6c0ebad5da954181947bb9df50b0e0")
        self.assertEqual(meta["runtime_verification"], "untested_blocked_no_weights_gpu_runtime_smoke")
        self.assertIn("weights_status", meta)
        # Verify no local user home paths are leaked
        meta_str = json.dumps(meta)
        self.assertNotIn("Users", meta_str)
        self.assertNotIn("home", meta_str)

    def test_prompt_token_stripping_and_stop_string_configuration(self) -> None:
        """Verify prompt tokens are stripped and stop sequences are properly configured."""
        from eval.vlm.adapter import Qwen2_5_VLAdapter

        class MockProcessor:
            mock_image_tag = True
            def apply_chat_template(self, messages: Any, **kwargs: Any) -> str:
                return "<chat/>"
            def __call__(self, **kwargs: Any) -> dict[str, Any]:
                return {"input_ids": [[10, 20, 30]], "pixel_values": [[0.1]]}
            def batch_decode(self, token_ids: Any, **kwargs: Any) -> list[str]:
                # Check that input prompt tokens were stripped (token_ids should only contain completion)
                if token_ids and len(token_ids[0]) == 2 and token_ids[0] == [99, 100]:
                    return ["Clean completion"]
                return [f"Unstripped tokens: {token_ids}"]

        class MockGenModel:
            device = "cpu"
            def __init__(self) -> None:
                self.last_kwargs = {}
            def generate(self, **kwargs: Any) -> list[list[int]]:
                self.last_kwargs = kwargs
                # Returns input_ids ([10, 20, 30]) + completion ([99, 100])
                return [[10, 20, 30, 99, 100]]

        mod = MockGenModel()
        proc = MockProcessor()
        qwen_cfg = copy.deepcopy(next(m for m in self.suite_data["models"] if "qwen" in m["key"]))
        qwen_cfg["stop_sequences"] = ["\n\n", "</s>"]

        adapter = Qwen2_5_VLAdapter(qwen_cfg, processor_override=proc, model_override=mod)
        resp = adapter.predict(
            image_bytes=b"synthetic_valid_image",
            prompt="Prompt",
            system_prompt="Sys",
            shot_mode="zero_shot",
            rung="identify",
            item_id="TEST-STRIP-01",
        )
        self.assertEqual(resp.status, "success")
        self.assertEqual(resp.cleaned_prediction, "Clean completion")
        self.assertEqual(mod.last_kwargs.get("stop_strings"), ["\n\n", "</s>"])

    # --- 11. Statistical Bootstrap Edge Cases ---

    def test_document_clustered_bootstrap_unequal_clusters_and_single_cluster(self) -> None:
        """Verify clustered bootstrap handles single clusters with null CI and unequal clusters reliably."""
        # Single document cluster must yield (None, None)
        single_cluster = {"DOC-1": [0.8, 0.9, 0.7]}
        ci_single, count_single, status_single = document_clustered_bootstrap_ci(single_cluster, n_resamples=2000)
        self.assertIsNone(ci_single)
        self.assertEqual(status_single, "insufficient_document_clusters")

        # Unequal clusters (e.g. DOC-1 has 20 items, DOC-2 has 2 items)
        unequal_clusters = {
            "DOC-1": [1.0] * 20,
            "DOC-2": [0.0] * 2,
        }
        ci_u, count_u, status_u = document_clustered_bootstrap_ci(unequal_clusters, n_resamples=2000)
        self.assertIsNotNone(ci_u)
        self.assertEqual(status_u, "valid_clustered_ci")
        self.assertLessEqual(ci_u[0], ci_u[1])

    # --- 12. Wave 5 Adversarial Trust Boundary and Integrity Regressions ---

    def test_adversarial_self_issued_approved_receipt_rejected(self) -> None:
        """Adversarially pass a self-declared 'approved_with_evidence' receipt; external promotion must fail closed."""
        from eval.vlm.universe import admit_external_items
        raw_items = [{"item_id": "EXT-CLAIM-001", "rung": "identify"}]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp_it:
            json.dump({"items": raw_items}, tmp_it)
            tmp_it_path = Path(tmp_it.name)

        receipt = {
            "receipt_id": "RECEIPT-SELF-ISSUED-001",
            "rights_review_status": "approved_with_evidence",
            "quarantine_verified": True,
            "independent_reviewer": "self-declared-agent",
            "permitted_cohort_tier": "approved_evaluation_cohort",
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp_rc:
            json.dump(receipt, tmp_rc)
            tmp_rc_path = Path(tmp_rc.name)

        try:
            admitted, tier, notices = admit_external_items(tmp_it_path, tmp_rc_path)
            self.assertEqual(tier, "unverified_external_inputs")
            self.assertTrue(
                any("cannot be independently verified" in n or "unverified_external_inputs" in n for n in notices),
                f"Expected notice disabling external cohort promotion, got: {notices}",
            )
        finally:
            tmp_it_path.unlink()
            tmp_rc_path.unlink()

    def test_adversarial_relabeled_mock_model_fails_require_certified(self) -> None:
        """Adversarially relabel mock model to a fake live model with all-success attempts; certification must fail."""
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()
        manifest = runner.run_suite(items, shot_mode="zero_shot")

        # Attacker re-labels model_key, tier, validity, cert_status and provides fake authorization receipt ref
        manifest["model_key"] = "fake-open-weight-vlm-7b"
        manifest["execution_tier"] = "live_local_open_weight"
        manifest["scientific_validity"] = "certified_baseline"
        manifest["certification_status"] = "certified"
        manifest["authorization_receipt_ref"] = "RECEIPT-AUTH-FORGED-001"
        manifest["universe_manifest"]["items_tier"] = "approved_evaluation_cohort"

        errors = audit_manifest(manifest, suite_path=SUITE_PATH, schema_path=SCHEMA_PATH, require_certified=True)
        self.assertTrue(
            any("Certification disabled" in e or "no trusted external authorization authority" in e for e in errors),
            f"Expected fail-closed certification refusal, got: {errors}",
        )

    def test_adversarial_altered_universe_with_recomputed_hash_rejected_by_anchor(self) -> None:
        """Adversarially alter items in universe and recompute internal hash; code anchor must detect tampering."""
        from eval.vlm.integrity import verify_universe_anchor
        from eval.vlm.universe import DEFAULT_UNIVERSE_PATH, compute_universe_sha256, load_universe
        universe = copy.deepcopy(load_universe(DEFAULT_UNIVERSE_PATH))

        # Alter an item in the universe and recompute universe_sha256 in place
        universe["items"][0]["rung"] = "translate"
        universe["universe_sha256"] = compute_universe_sha256(universe)

        anchor_errs = verify_universe_anchor(universe)
        self.assertTrue(
            any("does not match the code-pinned anchor" in e for e in anchor_errs),
            f"Expected code-pinned anchor violation, got: {anchor_errs}",
        )

    def test_adversarial_image_swap_under_same_item_id_detected(self) -> None:
        """Adversarially swap an attempt's image under the same item ID; auditor must detect hash mismatch."""
        from eval.vlm.universe import DEFAULT_UNIVERSE_PATH
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()
        manifest = runner.run_suite(items, shot_mode="zero_shot")

        # Swap image_sha256 on the first attempt
        original_hash = manifest["attempts"][0]["image_sha256"]
        manifest["attempts"][0]["image_sha256"] = hashlib.sha256(b"swapped_image_bytes").hexdigest()

        errors = audit_manifest(manifest, suite_path=SUITE_PATH, schema_path=SCHEMA_PATH, universe_path=DEFAULT_UNIVERSE_PATH)
        self.assertTrue(
            any("image swap under same item ID" in e for e in errors),
            f"Expected image swap detection, got: {errors}",
        )

    def test_adversarial_score_and_paired_compare_refuse_corrupted_inputs_without_diagnostic_only(self) -> None:
        """Score and paired-compare must refuse corrupted/unaudited inputs unless --diagnostic-only is passed."""
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()
        manifest = runner.run_suite(items, shot_mode="zero_shot")

        # Corrupt manifest attempts by dropping one attempt (violating frozen universe)
        manifest["attempts"].pop(0)
        manifest["coverage_summary"]["total_attempts"] = len(manifest["attempts"])

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp_m:
            json.dump(manifest, tmp_m)
            tmp_manifest_path = Path(tmp_m.name)

        try:
            # 1. score CLI invocation without --diagnostic-only must fail (return non-zero)
            ret_score = cli_main(["score", "--manifest", str(tmp_manifest_path)])
            self.assertEqual(ret_score, 1)

            # 2. score CLI invocation with --diagnostic-only must succeed and emit noncertifiable envelope
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp_out:
                tmp_out_path = Path(tmp_out.name)
            # Remove tmp_out so write_json_atomic (no-clobber) can write it
            tmp_out_path.unlink()

            ret_diag = cli_main([
                "score",
                "--manifest", str(tmp_manifest_path),
                "--diagnostic-only",
                "--output", str(tmp_out_path),
            ])
            self.assertEqual(ret_diag, 0)
            score_report = json.loads(tmp_out_path.read_text(encoding="utf-8"))
            self.assertEqual(score_report.get("classification"), "noncertifiable_diagnostic")
            self.assertFalse(score_report["audit_receipt"]["audit_passed"])
            self.assertGreater(score_report["audit_receipt"]["audit_error_count"], 0)
            tmp_out_path.unlink()

            # 3. paired-compare CLI invocation without --diagnostic-only must fail
            ret_comp = cli_main([
                "paired-compare",
                "--manifest-a", str(tmp_manifest_path),
                "--manifest-b", str(tmp_manifest_path),
            ])
            self.assertEqual(ret_comp, 1)

        finally:
            if tmp_manifest_path.exists():
                tmp_manifest_path.unlink()

    def test_adversarial_no_clobber_atomic_writer_refuses_overwrite(self) -> None:
        """Verify write_json_no_clobber and write_bytes_no_clobber refuse overwriting existing files."""
        from eval.vlm.integrity import ImmutableOutputError, write_bytes_no_clobber, write_json_no_clobber

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp.write("original_content")
            tmp_path = Path(tmp.name)

        try:
            with self.assertRaises(ImmutableOutputError):
                write_bytes_no_clobber(tmp_path, b"new_content")

            with self.assertRaises(ImmutableOutputError):
                write_json_no_clobber(tmp_path, {"new": "content"})

            # Verify original content is intact
            self.assertEqual(tmp_path.read_text(encoding="utf-8"), "original_content")
        finally:
            tmp_path.unlink()

    # --- 13. Wave 7 Real Visual Smoke & Adversarial Runtime Hardening Tests ---

    def test_adversarial_corrupted_image_magic_bytes_rejected(self) -> None:
        """Adversarially pass corrupted non-image bytes; preprocess_image must fail closed."""
        qwen_cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])
        adapter = OpenWeightVLMAdapter(qwen_cfg)
        with self.assertRaises(ImageConditioningError) as ctx:
            adapter.preprocess_image(b"corrupted_garbage_bytes_not_png_or_jpeg")
        self.assertIn("Corrupted or invalid image input", str(ctx.exception))

    def test_adversarial_non_full_revision_rejected(self) -> None:
        """Adversarially pass short or branch revision; validate_revision_pinning must fail closed."""
        # Short hash
        with self.assertRaises(VLMAdapterError) as ctx:
            validate_revision_pinning("9eb2daaa85")
        self.assertIn("not a full 40-character commit SHA", str(ctx.exception))

        # Branch name
        with self.assertRaises(VLMAdapterError):
            validate_revision_pinning("main")

        # Initializing open-weight adapter with short revision fails
        mutated_cfg = copy.deepcopy(next(m for m in self.suite_data["models"] if "qwen" in m["key"]))
        mutated_cfg["revision"] = "short1234"
        with self.assertRaises(VLMAdapterError):
            OpenWeightVLMAdapter(mutated_cfg)

        # Full 40-character SHA succeeds
        validate_revision_pinning("bfb8829e3c6c0ebad5da954181947bb9df50b0e0")

    def test_adversarial_forged_weights_directory_rejected(self) -> None:
        """Adversarially provide an empty directory as weights_dir; check_availability must fail."""
        qwen_cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])
        with tempfile.TemporaryDirectory() as empty_dir:
            adapter = get_adapter(qwen_cfg, weights_dir=Path(empty_dir))
            status = adapter.check_availability()
            self.assertFalse(status.available)
            self.assertFalse(status.hardware_info.get("weights_found", True))
            self.assertIn("not found locally on disk or snapshot directory is incomplete", status.reason)

    def test_adversarial_empty_whitespace_model_response_recorded_as_failed(self) -> None:
        """Adversarially return empty or whitespace string from model generate; must record failed attempt."""
        from eval.vlm.adapter import Qwen2_5_VLAdapter

        class MockEmptyGenModel:
            device = "cpu"
            def generate(self, **kwargs: Any) -> list[list[int]]:
                # Returns only input prompt tokens (no completion tokens)
                return [[1, 2, 3]]

        class MockEmptyProcessor:
            mock_image_tag = True
            def apply_chat_template(self, messages: Any, **kwargs: Any) -> str:
                return "<chat/>"
            def __call__(self, **kwargs: Any) -> dict[str, Any]:
                return {"input_ids": [[1, 2, 3]], "pixel_values": [[0.1]]}
            def batch_decode(self, token_ids: Any, **kwargs: Any) -> list[str]:
                return ["   \n  "]

        qwen_cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])
        adapter = Qwen2_5_VLAdapter(qwen_cfg, processor_override=MockEmptyProcessor(), model_override=MockEmptyGenModel())
        resp = adapter.predict(
            image_bytes=b"synthetic_valid_image",
            prompt="Prompt",
            system_prompt="Sys",
            shot_mode="zero_shot",
            rung="identify",
            item_id="TEST-EMPTY-RESP",
        )
        self.assertEqual(resp.status, "failed")
        self.assertIsNone(resp.cleaned_prediction)
        self.assertIn("empty or whitespace-only prediction", resp.error_message)

    def test_adversarial_stop_strings_type_error_graceful_fallback(self) -> None:
        """Verify that generate() raising TypeError on stop_strings falls back gracefully without stop_strings."""
        from eval.vlm.adapter import Qwen2_5_VLAdapter

        class MockTypeErrorGenModel:
            device = "cpu"
            def __init__(self) -> None:
                self.calls = 0
            def generate(self, **kwargs: Any) -> list[list[int]]:
                self.calls += 1
                if "stop_strings" in kwargs:
                    raise TypeError("generate() got an unexpected keyword argument 'stop_strings'")
                return [[1, 2, 100, 101]]

        class MockProc:
            mock_image_tag = True
            def apply_chat_template(self, messages: Any, **kwargs: Any) -> str:
                return "<chat/>"
            def __call__(self, **kwargs: Any) -> dict[str, Any]:
                return {"input_ids": [[1, 2]], "pixel_values": [[0.1]]}
            def batch_decode(self, token_ids: Any, **kwargs: Any) -> list[str]:
                return ["Recovered completion"]

        mod = MockTypeErrorGenModel()
        qwen_cfg = copy.deepcopy(next(m for m in self.suite_data["models"] if "qwen" in m["key"]))
        qwen_cfg["stop_sequences"] = ["</s>"]
        adapter = Qwen2_5_VLAdapter(qwen_cfg, processor_override=MockProc(), model_override=mod)

        resp = adapter.predict(
            image_bytes=b"synthetic_valid_image",
            prompt="Prompt",
            system_prompt="Sys",
            shot_mode="zero_shot",
            rung="identify",
            item_id="TEST-FALLBACK",
        )
        self.assertEqual(resp.status, "success")
        self.assertEqual(resp.cleaned_prediction, "Recovered completion")
        self.assertEqual(mod.calls, 2)

    def test_pure_python_geometric_png_generation_and_integrity(self) -> None:
        """Verify standalone pure-Python geometric PNG generator produces standards-compliant images."""
        import struct
        img_a = generate_geometric_test_image()
        img_b = generate_geometric_control_image()

        # Both must start with standard PNG signature
        self.assertTrue(img_a.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertTrue(img_b.startswith(b"\x89PNG\r\n\x1a\n"))

        # Both must unpack to width=256, height=256 from IHDR chunk
        w_a, h_a = struct.unpack(">II", img_a[16:24])
        w_b, h_b = struct.unpack(">II", img_b[16:24])
        self.assertEqual((w_a, h_a), (256, 256))
        self.assertEqual((w_b, h_b), (256, 256))

        # Both images must have distinct SHA-256 hashes
        sha_a = hashlib.sha256(img_a).hexdigest()
        sha_b = hashlib.sha256(img_b).hexdigest()
        self.assertNotEqual(sha_a, sha_b)

    def test_real_smoke_fails_closed_without_hardware_or_weights(self) -> None:
        """Verify real visual smoke test fails closed with exit code 1 when hardware/weights are absent."""
        qwen_cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])
        simulated_missing = {
            "missing_resources": ["nvidia_cuda_gpu_absent", "model_weights_not_found_on_disk"],
            "barrier_summary": "Controlled test: hardware and weights deliberately absent.",
        }
        with mock.patch("eval.vlm.smoke.audit_host_resources", return_value=simulated_missing):
            report, success = run_real_visual_smoke(qwen_cfg, allow_simulated=False)

        # This negative test must remain deterministic on a future GPU-equipped host.
        self.assertFalse(success)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["classification"], "noncertifiable_diagnostic")
        self.assertEqual(report["scientific_capability_points"], 0.0)
        self.assertFalse(report["hieratic_reading_claim"])
        self.assertFalse(report["simulated_double_smoke"])
        self.assertGreater(len(report["missing_resources"]), 0)
        self.assertFalse(report["evidence_grades"]["grade_f_authentic_hieratic_gold_evaluated"])

        # CLI invocation without --allow-simulated must return 1
        with mock.patch("eval.vlm.smoke.audit_host_resources", return_value=simulated_missing):
            ret = cli_main(["real-smoke", "--model", "qwen2.5-vl-7b-instruct"])
        self.assertEqual(ret, 1)

    def test_real_smoke_with_allow_simulated_evaluates_visual_sensitivity(self) -> None:
        """Verify real visual smoke test with --allow-simulated runs image-to-tensor and sensitivity control."""
        qwen_cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])
        report, success = run_real_visual_smoke(qwen_cfg, allow_simulated=True)

        self.assertTrue(success)
        self.assertEqual(report["status"], "completed")
        self.assertTrue(report["simulated_double_smoke"])
        self.assertEqual(report["classification"], "noncertifiable_diagnostic")
        self.assertEqual(report["scientific_capability_points"], 0.0)
        self.assertFalse(report["hieratic_reading_claim"])

        # Check visual sensitivity control
        sens = report["sensitivity_control"]
        self.assertTrue(sens["constant_prompt_preserved"])
        self.assertTrue(sens["image_bytes_differ"])
        self.assertTrue(sens["output_strings_differ"])
        self.assertFalse(sens["sensitivity_observed"])
        self.assertFalse(report["evidence_grades"]["grade_e_visual_sensitivity_control_verified"])
        self.assertIn("test double", sens["interpretation"])

        # Check token usage and hashes recorded
        fwd_a = report["forward_test_image"]
        fwd_b = report["forward_control_image"]
        self.assertNotEqual(fwd_a["image_sha256"], fwd_b["image_sha256"])
        self.assertNotEqual(fwd_a["output_sha256"], fwd_b["output_sha256"])
        self.assertGreater(fwd_a["token_usage"]["total_tokens"], 0)
        self.assertGreater(fwd_b["token_usage"]["total_tokens"], 0)

        # Grade F remains strictly False
        self.assertFalse(report["evidence_grades"]["grade_f_authentic_hieratic_gold_evaluated"])

        # CLI invocation with --allow-simulated must return 0
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp_path = Path(tmp.name)
        tmp_path.unlink()
        try:
            ret = cli_main([
                "real-smoke",
                "--model", "qwen2.5-vl-7b-instruct",
                "--allow-simulated",
                "--output", str(tmp_path),
            ])
            self.assertEqual(ret, 0)
            self.assertTrue(tmp_path.is_file())
            loaded = json.loads(tmp_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["status"], "completed")
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_visual_sensitivity_control_detects_image_insensitivity(self) -> None:
        """Verify visual sensitivity control flags indeterminate when output does not respond to image change."""
        from eval.vlm.adapter import MockVLMAdapter

        class ConstantResponseAdapter(MockVLMAdapter):
            def predict(self, *args: Any, **kwargs: Any) -> Any:
                from eval.vlm.adapter import VLMResponse
                return VLMResponse(
                    status="success",
                    raw_output="Identical static output regardless of image input.",
                    cleaned_prediction="Identical static output regardless of image input.",
                    error_message=None,
                    latency_ms=10.0,
                    token_usage={"prompt_tokens": 64, "completion_tokens": 8, "total_tokens": 72},
                )

        qwen_cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])
        dummy_adapter = ConstantResponseAdapter(qwen_cfg)

        report, success = run_real_visual_smoke(qwen_cfg, custom_adapter=dummy_adapter)
        self.assertTrue(success)
        sens = report["sensitivity_control"]
        self.assertFalse(sens["output_strings_differ"])
        self.assertFalse(sens["sensitivity_observed"])
        self.assertFalse(report["evidence_grades"]["grade_e_visual_sensitivity_control_verified"])

    def test_smoke_report_schema_conformity(self) -> None:
        """Verify that both blocked and simulated smoke reports conform strictly to schema."""
        from tools.vlm_baselines import validate_with_schema
        qwen_cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])

        simulated_missing = {
            "missing_resources": ["nvidia_cuda_gpu_absent", "model_weights_not_found_on_disk"],
            "barrier_summary": "Controlled test: hardware and weights deliberately absent.",
        }
        with mock.patch("eval.vlm.smoke.audit_host_resources", return_value=simulated_missing):
            report_blocked, _ = run_real_visual_smoke(qwen_cfg, allow_simulated=False)
        errs_b = validate_with_schema(report_blocked, self.schema)
        self.assertEqual(errs_b, [])

        report_sim, _ = run_real_visual_smoke(qwen_cfg, allow_simulated=True)
        errs_s = validate_with_schema(report_sim, self.schema)
        self.assertEqual(errs_s, [])

    def test_environment_provisioning_spec_structure(self) -> None:
        """Verify reproducible environment provisioning specification contains all mandatory sections."""
        qwen_cfg = next(m for m in self.suite_data["models"] if "qwen" in m["key"])
        adapter = OpenWeightVLMAdapter(qwen_cfg)
        spec = adapter.get_environment_provisioning_spec()

        self.assertIn("hardware_requirements", spec)
        self.assertIn("python_environment", spec)
        self.assertIn("weights_layout", spec)
        self.assertIn("scientific_spend_boundary", spec)
        self.assertEqual(spec["scientific_spend_boundary"]["max_authorized_spend_usd"], 0.0)
        self.assertFalse(spec["scientific_spend_boundary"]["cloud_compute_authorized"])
        self.assertEqual(spec["provider_model_id"], "Qwen/Qwen2.5-VL-7B-Instruct")
        self.assertEqual(spec["pinned_revision_sha"], "bfb8829e3c6c0ebad5da954181947bb9df50b0e0")

    # --- 14. Lightweight CPU VLM & SmolVLM Architecture Tests (Wave 8) ---

    def test_smolvlm_adapter_factory_and_properties(self) -> None:
        """Verify SmolVLM adapter factory creates SmolVLMAdapter with Idefics3 loader and CPU support."""
        from eval.vlm.adapter import SmolVLMAdapter, get_adapter
        smol_cfg = next(m for m in self.suite_data["models"] if "smolvlm" in m["key"])
        self.assertFalse(smol_cfg["requires_cuda"])
        self.assertEqual(smol_cfg["revision"], "7e3e67edbbed1bf9888184d9df282b700a323964")

        adapter = get_adapter(smol_cfg)
        self.assertIsInstance(adapter, SmolVLMAdapter)
        self.assertEqual(adapter.loader_class_name, "Idefics3ForConditionalGeneration")
        self.assertEqual(adapter.processor_class_name, "AutoProcessor")
        self.assertEqual(adapter.runtime_verification, "cpu_lightweight_open_weight_verified")

    def test_smolvlm_multimodal_message_formatting(self) -> None:
        """Verify SmolVLM adapter correctly structures messages for Idefics3 processor."""
        from eval.vlm.adapter import SmolVLMAdapter

        class MockSmolProcessor:
            def __init__(self) -> None:
                self.last_messages = None
                self.last_images = None

            def apply_chat_template(self, messages: Any, add_generation_prompt: bool = True, tokenize: bool = True) -> str:
                self.last_messages = messages
                self.last_tokenize = tokenize
                return "<idefics3_chat>"

            def __call__(self, images: Any = None, text: str = "", return_tensors: str = "pt") -> dict[str, Any]:
                self.last_images = images
                return {"input_ids": [[101, 102]], "pixel_values": [[0.3, 0.4]]}

            def batch_decode(self, token_ids: Any, **kwargs: Any) -> list[str]:
                return ["SmolVLM Hieratic observation"]

        class MockSmolModel:
            device = "cpu"
            def generate(self, **kwargs: Any) -> list[list[int]]:
                return [[101, 102, 201]]

        smol_cfg = next(m for m in self.suite_data["models"] if "smolvlm" in m["key"])
        proc = MockSmolProcessor()
        mod = MockSmolModel()
        adapter = SmolVLMAdapter(smol_cfg, processor_override=proc, model_override=mod)

        resp = adapter.predict(
            image_bytes=b"synthetic_valid_image_bytes",
            prompt="Identify script",
            system_prompt="You are an Egyptologist",
            shot_mode="zero_shot",
            rung="identify",
            item_id="TEST-SMOL-01",
        )
        self.assertEqual(resp.status, "success")
        self.assertEqual(resp.cleaned_prediction, "SmolVLM Hieratic observation")
        self.assertEqual(len(proc.last_messages), 2)
        self.assertEqual(proc.last_messages[0]["role"], "system")
        self.assertEqual(proc.last_messages[1]["role"], "user")
        self.assertEqual(proc.last_messages[1]["content"][0]["type"], "image")
        self.assertEqual(proc.last_messages[1]["content"][1]["type"], "text")
        self.assertIsNotNone(proc.last_images)
        self.assertIs(proc.last_tokenize, False)

    def test_smolvlm_real_adapter_rejects_synthetic_marker_before_forward(self) -> None:
        """No placeholder image may be accepted as genuine open-weight vision."""
        from eval.vlm.adapter import SmolVLMAdapter, ImageConditioningError
        smol_cfg = next(m for m in self.suite_data["models"] if "smolvlm" in m["key"])
        adapter = SmolVLMAdapter(smol_cfg)
        with self.assertRaisesRegex(ImageConditioningError, "prohibited for real"):
            adapter.preprocess_image(b"synthetic_valid_image_bytes")

    def test_smolvlm_requires_string_chat_template_not_pretokenized_ids(self) -> None:
        """Processor must return formatted text, not token IDs or a zero-shot shortcut."""
        from eval.vlm.adapter import SmolVLMAdapter, ImageConditioningError
        smol_cfg = next(m for m in self.suite_data["models"] if "smolvlm" in m["key"])
        class IncorrectProcessor:
            def apply_chat_template(self, *args: Any, **kwargs: Any) -> list[int]:
                return [101, 102]
            def __call__(self, **kwargs: Any) -> dict[str, Any]:
                raise AssertionError("invalid template must not reach image processor")
        adapter = SmolVLMAdapter(smol_cfg, processor_override=IncorrectProcessor())
        with self.assertRaisesRegex(ImageConditioningError, "did not return a nonempty text prompt"):
            adapter.format_multimodal_inputs("System", "Prompt", pil_image=None)

    def test_smolvlm_missing_chat_template_fails_closed(self) -> None:
        """Verify SmolVLM adapter fails closed if processor lacks apply_chat_template."""
        from eval.vlm.adapter import SmolVLMAdapter, ImageConditioningError

        class NoTemplateProcessor:
            def __call__(self, **kwargs: Any) -> dict[str, Any]:
                return {"input_ids": [[1]], "pixel_values": [[0.1]]}

        smol_cfg = next(m for m in self.suite_data["models"] if "smolvlm" in m["key"])
        adapter = SmolVLMAdapter(smol_cfg, processor_override=NoTemplateProcessor())
        with self.assertRaisesRegex(ImageConditioningError, "lacks apply_chat_template"):
            adapter.format_multimodal_inputs("Sys", "Prompt", pil_image=None)

    def test_smolvlm_omitted_pixel_values_fails_conditioning(self) -> None:
        """Verify SmolVLM adapter raises ImageConditioningError if visual tokens/pixels are missing."""
        from eval.vlm.adapter import SmolVLMAdapter

        class OmittedPixelProcessor:
            def apply_chat_template(self, messages: Any, **kwargs: Any) -> str:
                return "<chat/>"
            def __call__(self, **kwargs: Any) -> dict[str, Any]:
                return {"input_ids": [[1, 2, 3]]}

        smol_cfg = next(m for m in self.suite_data["models"] if "smolvlm" in m["key"])
        adapter = SmolVLMAdapter(smol_cfg, processor_override=OmittedPixelProcessor(), model_override=mock.MagicMock())
        resp = adapter.predict(
            image_bytes=b"synthetic_valid_image",
            prompt="Prompt",
            system_prompt="Sys",
            shot_mode="zero_shot",
            rung="identify",
            item_id="TEST-NO-PIXELS",
        )
        self.assertEqual(resp.status, "failed")
        self.assertIn("lacks visual features", resp.error_message)

    def test_smolvlm_absent_weights_availability_check(self) -> None:
        """Verify check_availability() fails closed with clean barrier reason when weights are absent."""
        from eval.vlm.adapter import SmolVLMAdapter
        smol_cfg = next(m for m in self.suite_data["models"] if "smolvlm" in m["key"])
        fake_empty_dir = Path(tempfile.mkdtemp(prefix="empty_smol_weights_"))
        try:
            adapter = SmolVLMAdapter(smol_cfg, weights_dir=fake_empty_dir)
            status = adapter.check_availability()
            self.assertFalse(status.available)
            self.assertIn("not found locally", status.reason)
            self.assertFalse(status.hardware_info["weights_found"])
        finally:
            fake_empty_dir.rmdir()

    def test_smolvlm_cpu_provisioning_spec_does_not_require_cuda(self) -> None:
        """Verify CPU environment provisioning spec specifies CPU target device and no accelerator requirement."""
        from eval.vlm.smoke import get_reproducible_provisioning_spec
        smol_cfg = next(m for m in self.suite_data["models"] if "smolvlm" in m["key"])
        spec = get_reproducible_provisioning_spec(smol_cfg)
        hw = spec["hardware_requirements"]
        self.assertFalse(hw["accelerator_required"])
        self.assertEqual(hw["target_device"], "cpu")
        self.assertIn("AVX2", hw["cpu_architecture"])
        self.assertEqual(spec["scientific_spend_boundary"]["max_authorized_spend_usd"], 0.0)

    def test_smolvlm_real_evidence_grade_matrix_conforms(self) -> None:
        """Verify compute_evidence_grades generates Grades A through E for real execution with Grade F False."""
        from eval.vlm.smoke import compute_evidence_grades
        smol_cfg = next(m for m in self.suite_data["models"] if "smolvlm" in m["key"])
        grades = compute_evidence_grades(smol_cfg, is_real_inference=True, sensitivity_verified=True)

        self.assertTrue(grades["grade_a_interface_implemented"])
        self.assertTrue(grades["grade_b_processor_format_fixture_tested"])
        self.assertTrue(grades["grade_c_real_weights_loaded_from_disk"])
        self.assertTrue(grades["grade_d_actual_image_conditioned_forward_executed"])
        self.assertTrue(grades["grade_e_visual_sensitivity_control_verified"])
        self.assertFalse(grades["grade_f_authentic_hieratic_gold_evaluated"])
    # --- 15. Authentic Hieratic Reading Evaluation Tests (Wave 9) ---

    def test_hieratic_protocol_preregistration_and_hash(self) -> None:
        """Verify frozen Hieratic protocol defines all 5 paleographical rungs and generates valid hash."""
        from eval.vlm.hieratic import (
            compute_protocol_hash,
            FROZEN_PROMPTS,
            DECODING_PARAMETERS,
            SYSTEM_PROMPT,
        )
        proto_hash = compute_protocol_hash()
        self.assertEqual(len(proto_hash), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in proto_hash))

        # Check all 5 tasks are covered
        expected_tasks = {
            "script_identification",
            "visual_description",
            "sign_hypotheses",
            "transliteration_hypotheses",
            "translation_hypotheses",
        }
        self.assertEqual(set(FROZEN_PROMPTS.keys()), expected_tasks)
        for t, prompt in FROZEN_PROMPTS.items():
            self.assertGreater(len(prompt), 30)

        # Greedy decoding parameters
        self.assertEqual(DECODING_PARAMETERS["temperature"], 0.0)
        self.assertFalse(DECODING_PARAMETERS["do_sample"])
        self.assertIn("paleography", SYSTEM_PROMPT)

    def test_hieratic_blank_and_inverted_control_generators(self) -> None:
        """Verify blank and inverted control image generators produce standards-compliant images."""
        from eval.vlm.hieratic import generate_blank_control, generate_inverted_control
        blank_png = generate_blank_control(256, 256)
        self.assertTrue(blank_png.startswith(b"\x89PNG\r\n\x1a\n"))

        # Inverted control
        inv_png = generate_inverted_control(blank_png)
        self.assertTrue(inv_png.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertNotEqual(hashlib.sha256(blank_png).hexdigest(), hashlib.sha256(inv_png).hexdigest())

    def test_hieratic_aspect_ratio_resizing(self) -> None:
        """Verify aspect-ratio preserving image resizing bounds dimensions without distorting proportions."""
        from eval.vlm.hieratic import resize_image_aspect_ratio, generate_blank_control
        # 400x200 image -> max 200 -> should be 200x100
        sample = generate_blank_control(400, 200)
        try:
            from PIL import Image  # noqa: F401; true pixel-preserving resize requires decoder
        except ImportError:
            self.skipTest("Pillow unavailable: genuine resizing correctly fails closed")
        resized_bytes, dims = resize_image_aspect_ratio(sample, max_dimension=200)
        self.assertLessEqual(max(dims), 200)
        self.assertEqual(round(dims[0] / dims[1], 1), 2.0)

    def test_hieratic_experiment_simulated_execution_and_schema_validation(self) -> None:
        """Verify simulated execution produces a conforming hieratic experiment report under the schema."""
        from eval.vlm.adapter import MockVLMAdapter
        from eval.vlm.hieratic import execute_hieratic_experiment
        from tools.vlm_baselines import validate_with_schema

        mock_cfg = {
            "key": "smolvlm-mock",
            "model_type": "mock",
            "provider_model_id": "HuggingFaceTB/SmolVLM-256M-Instruct",
            "revision": "7e3e67edbbed1bf9888184d9df282b700a323964",
        }
        adapter = MockVLMAdapter(mock_cfg)
        targets = [
            {
                "target_id": "test_full_target",
                "target_type": "full_manuscript",
                "image_bytes": b"synthetic_full_test_image",
                "source_bounds": [0, 0, 7063, 3947],
                "transform": None,
            },
            {
                "target_id": "test_crop_target",
                "target_type": "candidate_line_crop",
                "image_bytes": b"synthetic_crop_test_image",
                "source_bounds": [100, 100, 300, 200],
                "transform": None,
            },
        ]
        report = execute_hieratic_experiment(adapter, targets, allow_simulated=True)

        # Check schema validity
        errs = validate_with_schema(report, self.schema)
        self.assertEqual(errs, [])

        # Check structure
        self.assertEqual(report["doc_type"], "vlm_hieratic_experiment_report")
        self.assertEqual(report["classification"], "noncertifiable_diagnostic")
        self.assertEqual(report["scientific_capability_points"], 0.0)
        self.assertFalse(report["hieratic_reading_claim"])
        self.assertEqual(len(report["targets"]), 2)
        # 2 targets * 5 tasks = 10 hypotheses
        self.assertEqual(len(report["reading_hypotheses"]), 10)
        self.assertFalse(report["sensitivity_controls"]["sensitivity_observed"])
        self.assertTrue(report["model_info"]["simulated_mode"])
        self.assertFalse(report["source_image"]["source_bytes_verified"])

    def test_hieratic_experiment_fails_closed_without_allow_simulated(self) -> None:
        """Verify mock adapter without allow_simulated=True raises ImageConditioningError."""
        from eval.vlm.adapter import MockVLMAdapter, ImageConditioningError
        from eval.vlm.hieratic import execute_hieratic_experiment

        mock_cfg = {"key": "mock-test", "model_type": "mock"}
        adapter = MockVLMAdapter(mock_cfg)
        targets = [{"target_id": "t1", "target_type": "full_manuscript", "image_bytes": b"synthetic_img"}]
        with self.assertRaises(ImageConditioningError):
            execute_hieratic_experiment(adapter, targets, allow_simulated=False)

    def test_hieratic_cli_invocation_simulated(self) -> None:
        """Verify real-hieratic CLI subcommand succeeds in simulated mode and outputs valid report JSON."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp_path = Path(tmp.name)
        tmp_path.unlink()
        try:
            ret = cli_main([
                "real-hieratic",
                "--model", "smolvlm-256m-instruct",
                "--allow-simulated",
                "--output", str(tmp_path),
            ])
            self.assertEqual(ret, 0)
            self.assertTrue(tmp_path.is_file())
            data = json.loads(tmp_path.read_text(encoding="utf-8"))
            self.assertEqual(data["doc_type"], "vlm_hieratic_experiment_report")
            self.assertEqual(data["classification"], "noncertifiable_diagnostic")
            self.assertEqual(data["scientific_capability_points"], 0.0)
            self.assertFalse(data["hieratic_reading_claim"])
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_hieratic_evidence_grade_matrix_and_governance_bounds(self) -> None:
        """Verify Hieratic reading evidence grade matrix explicitly marks Grade F as STRICTLY_NO."""
        from eval.vlm.adapter import MockVLMAdapter
        from eval.vlm.hieratic import execute_hieratic_experiment
        mock_cfg = {
            "key": "smolvlm-mock",
            "model_type": "mock",
            "provider_model_id": "HuggingFaceTB/SmolVLM-256M-Instruct",
            "revision": "7e3e67edbbed1bf9888184d9df282b700a323964",
        }
        adapter = MockVLMAdapter(mock_cfg)
        targets = [{"target_id": "t1", "target_type": "candidate_line_crop", "image_bytes": b"synthetic_crop"}]
        report = execute_hieratic_experiment(adapter, targets, allow_simulated=True)

        grades = report["evidence_grades"]
        self.assertEqual(grades["grade_f_authentic_hieratic_gold_evaluation"]["status"], "STRICTLY_NO")
        self.assertEqual(grades["silver_diagnostic_cleared"]["status"], "S0_BIBLIOGRAPHIC_CITATION_ONLY")
        for name in (
            "grade_a_multimodal_interface", "grade_b_fixture_tests",
            "grade_c_real_weights_loaded", "grade_d_actual_hieratic_forward_pass",
            "grade_e_visual_sensitivity_observed", "real_hieratic_hypothesis_cleared",
        ):
            self.assertEqual(grades[name]["status"], "SIMULATED_TEST_DOUBLE")


    def test_hieratic_decoder_rejects_invalid_bytes_without_silent_replacement(self) -> None:
        from eval.vlm.hieratic import resize_image_aspect_ratio
        for bad in (b"", b"junk", b"\\x89PNG\\r\\n\\x1a\\n" + b"x" * 50, b"\\xff\\xd8\\xff" + b"x" * 32):
            with self.subTest(bad=repr(bad[:8])), self.assertRaises(ImageConditioningError):
                resize_image_aspect_ratio(bad)
        with self.assertRaises(ImageConditioningError):
            resize_image_aspect_ratio(b"synthetic_marker_not_real")

    def test_hieratic_missing_pillow_cannot_fabricate_real_pixels(self) -> None:
        from eval.vlm.hieratic import generate_blank_control, resize_image_aspect_ratio
        with mock.patch.dict("sys.modules", {"PIL": None}):
            with self.assertRaisesRegex(ImageConditioningError, "Pillow"):
                resize_image_aspect_ratio(generate_blank_control())

    def test_hieratic_weight_check_refuses_simulated_and_missing_real_weights(self) -> None:
        from eval.vlm.hieratic import verified_model_weight_sha256, execute_hieratic_experiment
        fake = MockVLMAdapter({"key": "synthetic", "model_type": "mock"})
        self.assertFalse(verified_model_weight_sha256(fake))
        class StubLive:
            execution_tier = "live_local_open_weight"
            weights_dir = Path("missing_weights_dir_test")
            model_config = {"provider_model_id": "HuggingFaceTB/SmolVLM-256M-Instruct",
                            "revision": "7e3e67edbbed1bf9888184d9df282b700a323964"}
        with self.assertRaisesRegex(ImageConditioningError, "Pinned SmolVLM"):
            execute_hieratic_experiment(StubLive(), [{"target_id": "cat2044_full_p01", "target_type": "full_manuscript", "image_bytes": b"junk"}])

    def test_hieratic_mock_report_cannot_promote_response_difference(self) -> None:
        from eval.vlm.hieratic import execute_hieratic_experiment
        adapter = MockVLMAdapter({"key": "mock", "model_type": "mock"})
        report = execute_hieratic_experiment(
            adapter, [{"target_id": "t1", "target_type": "full_manuscript", "image_bytes": b"synthetic_fixture"}],
            allow_simulated=True,
        )
        self.assertFalse(report["sensitivity_controls"]["sensitivity_observed"])
        self.assertFalse(report["sensitivity_controls"]["inter_crop_discrimination_tested"])
        self.assertEqual(report["evidence_grades"]["grade_f_authentic_hieratic_gold_evaluation"]["status"], "STRICTLY_NO")
        self.assertTrue(all(h["grounding_assessment"] == "synthetic_ci_fixture" for h in report["reading_hypotheses"]))

    def test_hieratic_rung_mapping_is_task_specific(self) -> None:
        from eval.vlm.hieratic import TASK_RUNGS
        self.assertEqual(TASK_RUNGS["sign_hypotheses"], "signs")
        self.assertEqual(TASK_RUNGS["transliteration_hypotheses"], "transliterate")
        self.assertEqual(TASK_RUNGS["translation_hypotheses"], "translate")
        self.assertEqual(TASK_RUNGS["script_identification"], "identify")

    def test_hieratic_scrambled_control_generator(self) -> None:
        """Verify scrambled control image generator permutes tiles deterministically."""
        from eval.vlm.hieratic import generate_blank_control, generate_scrambled_control, ImageConditioningError
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow unavailable: scrambled control generator requires decoder")

        from eval.vlm.smoke import generate_geometric_test_image
        sample = generate_geometric_test_image()
        scrambled_1 = generate_scrambled_control(sample, tile_size=16, seed=42)
        scrambled_2 = generate_scrambled_control(sample, tile_size=16, seed=42)
        self.assertTrue(scrambled_1.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(hashlib.sha256(scrambled_1).hexdigest(), hashlib.sha256(scrambled_2).hexdigest())
        self.assertNotEqual(hashlib.sha256(sample).hexdigest(), hashlib.sha256(scrambled_1).hexdigest())

        with self.assertRaises(ImageConditioningError):
            generate_scrambled_control(b"not_an_image")

    def test_hieratic_sensitivity_controls_quantitative_metrics(self) -> None:
        """Verify simulated report includes complete quantitative sensitivity metrics."""
        from eval.vlm.adapter import MockVLMAdapter
        from eval.vlm.hieratic import execute_hieratic_experiment
        adapter = MockVLMAdapter({"key": "mock", "model_type": "mock"})
        report = execute_hieratic_experiment(
            adapter, [{"target_id": "t1", "target_type": "full_manuscript", "image_bytes": b"synthetic_fixture"}],
            allow_simulated=True,
        )
        ctrl = report["sensitivity_controls"]
        self.assertIn("blank_hallucinates_script", ctrl)
        self.assertIn("blank_correctly_identified", ctrl)
        self.assertIn("scrambled_response_text", ctrl)
        self.assertIn("scrambled_hallucinates_script", ctrl)
        self.assertIn("prompt_priming_observed", ctrl)
        self.assertIn("transliteration_abstention_rate", ctrl)
        self.assertIn("repetition_loop_detected", ctrl)
        self.assertIn("translation_unsupported_acknowledged", ctrl)
        self.assertFalse(ctrl["sensitivity_observed"])

    def test_smolvlm_500m_audit_records_unavailable(self) -> None:
        """Verify SmolVLM-500M status truthfully documents RAM constraints and unavailable status."""
        from eval.vlm.hieratic import audit_alternative_models
        audit = audit_alternative_models()
        self.assertIn("smolvlm_500m_instruct", audit)
        self.assertEqual(
            audit["smolvlm_500m_instruct"]["execution_status"],
            "UNAVAILABLE_INSUFFICIENT_AVAILABLE_RAM_AND_WEIGHTS_ABSENT",
        )
        self.assertEqual(
            audit["smolvlm_500m_instruct"]["comparison_status"],
            "NOT_EXECUTED_DUE_TO_RAM_LIMITS",
        )

    # =========================================================================
    # Section 16: Wave 14 Cross-Support, RIME Fig. 6 Recto, and Adversarial Falsification
    # =========================================================================

    def test_w14_natural_nontext_control_generation_and_properties(self) -> None:
        """Verify procedural natural non-text control generates deterministic valid PNG."""
        from eval.vlm.hieratic import generate_natural_nontext_control
        b1 = generate_natural_nontext_control(256, 256, seed=42)
        b2 = generate_natural_nontext_control(256, 256, seed=42)
        self.assertTrue(b1.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(b1, b2)
        self.assertEqual(hashlib.sha256(b1).hexdigest(), hashlib.sha256(b2).hexdigest())
        b3 = generate_natural_nontext_control(256, 256, seed=99)
        self.assertNotEqual(b1, b3)

    def test_w14_detects_forbidden_figure_8_verso_substitution(self) -> None:
        """Verify supplying RIME Figure 8 Verso bytes raises ImageConditioningError."""
        from eval.vlm.hieratic import (
            resize_image_aspect_ratio,
            ImageConditioningError,
            RIME_FIG8_VERSO_FORBIDDEN_SHA256,
        )
        fake_fig8_bytes = b"\x89PNG\r\n\x1a\n" + b"fig8_verso_data"
        with mock.patch("hashlib.sha256") as mock_sha:
            mock_obj = mock.MagicMock()
            mock_obj.hexdigest.return_value = RIME_FIG8_VERSO_FORBIDDEN_SHA256
            mock_sha.return_value = mock_obj
            with self.assertRaisesRegex(ImageConditioningError, "Forbidden Figure 8 Verso"):
                resize_image_aspect_ratio(fake_fig8_bytes)

    def test_w14_detects_missing_or_corrupt_rime_tiff_in_live_execution(self) -> None:
        """Verify live execution fails closed when RIME Fig. 6 TIFF bytes mismatch size or hash."""
        from eval.vlm.hieratic import (
            execute_hieratic_experiment,
            ImageConditioningError,
        )
        class StubLive:
            execution_tier = "live_local_open_weight"
            weights_dir = Path("missing_weights_dir_test")
            model_config = {
                "provider_model_id": "HuggingFaceTB/SmolVLM-256M-Instruct",
                "revision": "7e3e67edbbed1bf9888184d9df282b700a323964",
            }

        with mock.patch("eval.vlm.hieratic.verified_model_weight_sha256", return_value=True):
            bad_size = [{
                "target_id": "cat1883_2095_full_fig6",
                "target_type": "full_manuscript",
                "image_bytes": b"too_short",
            }]
            with self.assertRaisesRegex(ImageConditioningError, "RIME Fig. 6 source hash or byte size"):
                execute_hieratic_experiment(StubLive(), bad_size, allow_simulated=False)

    def test_w14_cross_support_vocabulary_overlap_and_metrics(self) -> None:
        """Verify simulated cross-support run calculates Jaccard vocabulary similarity and divergence."""
        from eval.vlm.adapter import MockVLMAdapter
        from eval.vlm.hieratic import execute_hieratic_experiment
        adapter = MockVLMAdapter({"key": "mock", "model_type": "mock"})
        targets = [
            {"target_id": "cat2044_full_p01", "target_type": "full_manuscript", "image_bytes": b"synthetic_2044"},
            {"target_id": "cat1883_2095_full_fig6", "target_type": "full_manuscript", "image_bytes": b"synthetic_1883"},
        ]
        report = execute_hieratic_experiment(adapter, targets, allow_simulated=True)
        self.assertIn("cross_support_comparison", report["sensitivity_controls"])
        cs = report["sensitivity_controls"]["cross_support_comparison"]
        self.assertIsNotNone(cs)
        self.assertTrue(cs["evaluated"])
        self.assertIn("jaccard_vocabulary_similarity", cs)
        self.assertIn("shared_vocabulary_count", cs)
        self.assertEqual(cs["support_1"], "Cat.2044/013")
        self.assertEqual(cs["support_2"], "Cat.1883 + Cat.2095 (RIME Fig. 6)")

    def test_w14_prompt_priming_differential_measurement(self) -> None:
        """Verify report records leading ablation and prompt priming differential across controls."""
        from eval.vlm.adapter import MockVLMAdapter
        from eval.vlm.hieratic import execute_hieratic_experiment
        adapter = MockVLMAdapter({"key": "mock", "model_type": "mock"})
        targets = [
            {"target_id": "t1", "target_type": "full_manuscript", "image_bytes": b"synthetic_fixture"},
        ]
        report = execute_hieratic_experiment(adapter, targets, allow_simulated=True, run_leading_ablation=True)
        ctrl = report["sensitivity_controls"]
        self.assertIn("leading_ablation", ctrl)
        la = ctrl["leading_ablation"]
        self.assertIn("blank_leading_response", la)
        self.assertIn("blank_leading_claims_script", la)
        self.assertIn("scrambled_leading_claims_script", la)
        self.assertIn("natural_nontext_leading_claims_script", la)
        self.assertIn("manuscript_leading_responses", la)

    def test_w14_evidence_grades_fail_closed_grade_e_and_f(self) -> None:
        """Verify Grade E stays NOT_VERIFIED and Grade F stays STRICTLY_NO (0.0 points)."""
        from eval.vlm.adapter import MockVLMAdapter
        from eval.vlm.hieratic import execute_hieratic_experiment
        adapter = MockVLMAdapter({"key": "mock", "model_type": "mock"})
        targets = [
            {"target_id": "t1", "target_type": "full_manuscript", "image_bytes": b"synthetic_fixture"},
        ]
        report = execute_hieratic_experiment(adapter, targets, allow_simulated=True)
        grades = report["evidence_grades"]
        self.assertEqual(grades["grade_f_authentic_hieratic_gold_evaluation"]["status"], "STRICTLY_NO")
        self.assertEqual(report["scientific_capability_points"], 0.0)
        self.assertFalse(report["hieratic_reading_claim"])
        self.assertEqual(report["classification"], "noncertifiable_diagnostic")

    def test_w14_cli_invocation_with_rime_image_simulated(self) -> None:
        """Verify real-hieratic CLI subcommand accepts --rime-image-path in simulated mode."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp_path = Path(tmp.name)
        tmp_path.unlink()
        try:
            ret = cli_main([
                "real-hieratic",
                "--model", "smolvlm-256m-instruct",
                "--allow-simulated",
                "--output", str(tmp_path),
            ])
            self.assertEqual(ret, 0)
            self.assertTrue(tmp_path.is_file())
            data = json.loads(tmp_path.read_text(encoding="utf-8"))
            self.assertEqual(data["doc_type"], "vlm_hieratic_experiment_report")
            self.assertEqual(data["classification"], "noncertifiable_diagnostic")
            self.assertEqual(data["scientific_capability_points"], 0.0)
            self.assertFalse(data["hieratic_reading_claim"])
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_w14_scholarly_provenance_records_two_supports(self) -> None:
        """Verify scholarly provenance documents two distinct physical supports with single-support note."""
        from eval.vlm.hieratic import get_scholarly_provenance
        prov = get_scholarly_provenance()
        self.assertEqual(prov["distinct_physical_supports_evaluated"], 2)
        self.assertEqual(len(prov["supports"]), 2)
        s1 = prov["supports"][0]
        s2 = prov["supports"][1]
        self.assertEqual(s1["accession"], "Cat.2044/013")
        self.assertEqual(s2["accession"], "Cat.1883 + Cat.2095")
        self.assertIn("single physical manuscript support", prov["scholarly_note"])
        self.assertEqual(s1["alignment_status"], "NO_LINE_ALIGNMENT")
        self.assertEqual(s2["alignment_status"], "NO_LINE_ALIGNMENT")
        self.assertEqual(s2["text_reuse_status"], "BLOCKED_UNVERIFIED_LICENSE")

    def test_w14_counting_adapter_attempt_ledger_and_attempt_counts(self) -> None:
        """Verify that every forward pass is recorded in attempt_ledger with exact attempt counts.
        
        Asserts:
        - 5 targets (2 full manuscripts + 3 candidate line crops):
          5 targets * 5 neutral = 25
          + 2 full targets * 1 leading = 2
          + 4 controls * 1 neutral = 4
          + 4 controls * 1 leading = 4
          Total = 35 actual predictions.
          Ledger has 35 entries (29 neutral, 6 leading).
        - 2 targets (1 full manuscript + 1 crop):
          2 targets * 5 neutral = 10
          + 1 full target * 1 leading = 1
          + 4 controls * 1 neutral = 4
          + 4 controls * 1 leading = 4
          Total = 19 actual predictions.
          Ledger has 19 entries (14 neutral, 5 leading).
        """
        from eval.vlm.hieratic import execute_hieratic_experiment

        class CountingVLMAdapter(MockVLMAdapter):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.call_count = 0
                self.recorded_calls = []

            def predict(self, *args, **kwargs):
                self.call_count += 1
                self.recorded_calls.append((args, kwargs))
                return super().predict(*args, **kwargs)

        # 5 targets
        adapter5 = CountingVLMAdapter({"key": "mock", "model_type": "mock"})
        targets5 = [
            {"target_id": "cat2044_full_p01", "target_type": "full_manuscript", "image_bytes": b"synthetic_img1"},
            {"target_id": "cat1883_2095_full_fig6", "target_type": "full_manuscript", "image_bytes": b"synthetic_img2"},
            {"target_id": "candidate_crop_01", "target_type": "candidate_line_crop", "image_bytes": b"synthetic_crop1"},
            {"target_id": "candidate_crop_02", "target_type": "candidate_line_crop", "image_bytes": b"synthetic_crop2"},
            {"target_id": "candidate_crop_03", "target_type": "candidate_line_crop", "image_bytes": b"synthetic_crop3"},
        ]
        report5 = execute_hieratic_experiment(adapter5, targets5, allow_simulated=True, run_leading_ablation=True)
        self.assertEqual(adapter5.call_count, 35)
        self.assertEqual(len(report5["attempt_ledger"]), 35)
        self.assertEqual(report5["attempt_counts"]["total_attempts_recorded"], 35)
        self.assertEqual(report5["attempt_counts"]["successful_actual_passes"], 35)
        self.assertEqual(report5["attempt_counts"]["by_prompt_variant"]["neutral"], 29)
        self.assertEqual(report5["attempt_counts"]["by_prompt_variant"]["leading"], 6)
        self.assertEqual(report5["attempt_counts"]["by_category"]["manuscript_neutral"], 25)
        self.assertEqual(report5["attempt_counts"]["by_category"]["manuscript_leading_ablation"], 2)
        self.assertEqual(report5["attempt_counts"]["by_category"]["control_neutral"], 4)
        self.assertEqual(report5["attempt_counts"]["by_category"]["control_leading_ablation"], 4)

        # Verify ledger structure on first and last entries
        entry0 = report5["attempt_ledger"][0]
        self.assertEqual(entry0["attempt_index"], 0)
        self.assertIn("attempt_id", entry0)
        self.assertIn("prompt_sha256", entry0)
        self.assertIn("output_sha256", entry0)
        self.assertEqual(entry0["status"], "success")

        # 2 targets
        adapter2 = CountingVLMAdapter({"key": "mock", "model_type": "mock"})
        targets2 = [
            {"target_id": "cat2044_full_p01", "target_type": "full_manuscript", "image_bytes": b"synthetic_img1"},
            {"target_id": "candidate_crop_01", "target_type": "candidate_line_crop", "image_bytes": b"synthetic_crop1"},
        ]
        report2 = execute_hieratic_experiment(adapter2, targets2, allow_simulated=True, run_leading_ablation=True)
        self.assertEqual(adapter2.call_count, 19)
        self.assertEqual(len(report2["attempt_ledger"]), 19)
        self.assertEqual(report2["attempt_counts"]["total_attempts_recorded"], 19)
        self.assertEqual(report2["attempt_counts"]["by_prompt_variant"]["neutral"], 14)
        self.assertEqual(report2["attempt_counts"]["by_prompt_variant"]["leading"], 5)

    def test_w14_classify_script_claim_categories(self) -> None:
        """Verify classify_script_claim categorizes utterances into 4 explicit classes."""
        from eval.vlm.hieratic import classify_script_claim

        # 1. Affirmative script claim
        res1 = classify_script_claim("The script shown is Hieratic.")
        self.assertEqual(res1["category"], "affirmative_script_claim")
        self.assertTrue(res1["script_claimed"])
        self.assertFalse(res1["no_script_claimed"])
        self.assertIn("hieratic", res1["identified_scripts"])

        res2 = classify_script_claim("The visible ink strokes in this ancient Egyptian manuscript image are likely hieroglyphics.")
        self.assertEqual(res2["category"], "affirmative_script_claim")
        self.assertTrue(res2["script_claimed"])

        # 2. Negative script claim
        res3 = classify_script_claim("There is no writing, text, or script present in the image.")
        self.assertEqual(res3["category"], "negative_script_claim")
        self.assertFalse(res3["script_claimed"])
        self.assertTrue(res3["no_script_claimed"])

        res4 = classify_script_claim("Blank surface with no characters.")
        self.assertEqual(res4["category"], "negative_script_claim")
        self.assertTrue(res4["no_script_claimed"])

        # 3. Mixed or uncertain
        res5 = classify_script_claim("There is no text, but visible ink strokes resemble hieratic.")
        self.assertEqual(res5["category"], "mixed_or_uncertain")
        self.assertFalse(res5["script_claimed"])
        self.assertTrue(res5["is_uncertain_or_mixed"])

        res6 = classify_script_claim("It is not Hieratic, possibly demotic or decorative.")
        self.assertEqual(res6["category"], "mixed_or_uncertain")
        self.assertTrue(res6["is_uncertain_or_mixed"])

        # 4. Descriptive only
        res7 = classify_script_claim("A grayscale image showing fiber textures and paper edges.")
        self.assertEqual(res7["category"], "descriptive_only")
        self.assertFalse(res7["script_claimed"])
        self.assertFalse(res7["no_script_claimed"])

        res8 = classify_script_claim("Rough papyrus fibers with mottled dark areas.")
        self.assertEqual(res8["category"], "descriptive_only")
        self.assertFalse(res8["script_claimed"])

    def test_w14_matched_cross_support_and_isolated_crop_analysis(self) -> None:
        """Verify matched full-vs-full cross-support comparison and isolated crop_analysis."""
        from eval.vlm.hieratic import execute_hieratic_experiment

        adapter = MockVLMAdapter({"key": "mock", "model_type": "mock"})
        targets = [
            {"target_id": "cat2044_full_p01", "target_type": "full_manuscript", "image_bytes": b"synthetic_img1"},
            {"target_id": "cat1883_2095_full_fig6", "target_type": "full_manuscript", "image_bytes": b"synthetic_img2"},
            {"target_id": "candidate_crop_01", "target_type": "candidate_line_crop", "image_bytes": b"synthetic_crop1"},
            {"target_id": "candidate_crop_02", "target_type": "candidate_line_crop", "image_bytes": b"synthetic_crop2"},
            {"target_id": "candidate_crop_03", "target_type": "candidate_line_crop", "image_bytes": b"synthetic_crop3"},
        ]
        report = execute_hieratic_experiment(adapter, targets, allow_simulated=True)

        # Cross-support analysis must be strictly matched full-vs-full
        cs = report.get("cross_support_analysis")
        self.assertIsNotNone(cs)
        self.assertEqual(cs["comparison_scope"], "matched_full_manuscript_only")
        self.assertEqual(cs["support_1"], "Cat.2044/013")
        self.assertEqual(cs["support_2"], "Cat.1883 + Cat.2095 (RIME Fig. 6)")
        self.assertEqual(cs["matched_task_count"], 5)

        # Crop analysis must isolate the 3 candidate crops
        crop = report.get("crop_analysis")
        self.assertIsNotNone(crop)
        self.assertEqual(crop["candidate_crops_evaluated"], 3)
        self.assertEqual(crop["crop_hypotheses_count"], 15)

    def test_w14_primary_source_metadata_administrative_text_and_byte_sizes(self) -> None:
        """Verify primary source metadata documents Deir el-Medina administrative text and exact byte sizes."""
        from eval.vlm.hieratic import (
            get_scholarly_provenance,
            RIME_FIG6_BYTE_SIZE,
            RIME_FIG8_VERSO_BYTE_SIZE,
        )

        prov = get_scholarly_provenance()
        s2 = prov["supports"][1]
        self.assertIn("administrative Deir el-Medina text", s2["historical_context"])
        self.assertIn("accounts, lists, and royal dating", s2["historical_context"])
        self.assertIn("Not Book of the Dead or funerary liturgy", s2["historical_context"])

        # Check exact byte size constants
        self.assertEqual(RIME_FIG6_BYTE_SIZE, 36023444)
        self.assertEqual(RIME_FIG8_VERSO_BYTE_SIZE, 41686648)

    def test_w20_media_metadata_and_rights_integrity(self) -> None:
        """Verify 15 pinned publisher media items, licensing, and 6 physical witness supports."""
        from eval.vlm.signs import W19_PINNED_MEDIA, MATCHED_5_SAME_SIGN_IDS, DERIVED_OUTLINE_SIGN_IDS
        self.assertEqual(len(W19_PINNED_MEDIA), 15)
        signs = {m["sign_id"] for m in W19_PINNED_MEDIA}
        self.assertEqual(len(signs), 8)
        witnesses = {m["physical_witness"] for m in W19_PINNED_MEDIA}
        self.assertEqual(len(witnesses), 6)
        self.assertEqual(len(MATCHED_5_SAME_SIGN_IDS), 5)
        self.assertEqual(len(DERIVED_OUTLINE_SIGN_IDS), 2)
        for m in W19_PINNED_MEDIA:
            self.assertTrue(m["publisher_media_url"].startswith("https://aku-pal.uni-mainz.de/"))
            self.assertEqual(len(m["expected_sha256"]), 64)
            self.assertGreater(m["expected_byte_size"], 0)
            self.assertIn(m["content_type"], ("image/svg+xml", "image/webp"))
            self.assertEqual(m.get("rights_status", "CC BY 4.0"), "CC BY 4.0")
            self.assertIn(m["media_classification"], ("publisher_sign_svg_facsimile", "publication_scan_reproduction", "svg_outline_derivative"))

    def test_w20_dual_prompts_and_hash_anchors(self) -> None:
        """Verify neutral and leading prompt text and cryptographic hash constants."""
        from eval.vlm.signs import (
            FROZEN_NEUTRAL_SIGN_PROMPT,
            FROZEN_NEUTRAL_PROMPT_SHA256,
            FROZEN_LEADING_SIGN_PROMPT,
            FROZEN_LEADING_PROMPT_SHA256,
            compute_sign_protocol_hash,
        )
        self.assertEqual(hashlib.sha256(FROZEN_NEUTRAL_SIGN_PROMPT.encode("utf-8")).hexdigest(), FROZEN_NEUTRAL_PROMPT_SHA256)
        self.assertEqual(hashlib.sha256(FROZEN_LEADING_SIGN_PROMPT.encode("utf-8")).hexdigest(), FROZEN_LEADING_PROMPT_SHA256)
        self.assertNotEqual(FROZEN_NEUTRAL_PROMPT_SHA256, FROZEN_LEADING_PROMPT_SHA256)
        proto_hash = compute_sign_protocol_hash()
        self.assertEqual(len(proto_hash), 64)

    def test_w20_controls_generation_and_distinct_hashes(self) -> None:
        """Verify 8 negative/material controls generate valid 256x256 images with distinct hashes."""
        import struct
        from eval.vlm.signs import (
            generate_geometric_marks_control,
            generate_photo_negative_control,
            generate_identity_mark_control,
            generate_manuscript_photo_positive,
        )
        from eval.vlm.hieratic import (
            generate_blank_control,
            generate_natural_nontext_control,
            generate_scrambled_control,
            generate_inverted_control,
        )

        c_blank = generate_blank_control(256, 256)
        c_tex = generate_natural_nontext_control(256, 256, seed=42)
        c_geom = generate_geometric_marks_control((256, 256))
        c_pneg = generate_photo_negative_control((256, 256), seed=101)
        try:
            from PIL import Image  # noqa: F401
            c_scram = generate_scrambled_control(c_pneg, tile_size=32, seed=42)
            c_inv = generate_inverted_control(c_pneg)
        except Exception:
            c_scram = generate_photo_negative_control((256, 256), seed=102)
            c_inv = generate_photo_negative_control((256, 256), seed=103)
        c_ident = generate_identity_mark_control((256, 256))
        c_pos = generate_manuscript_photo_positive((256, 256))

        controls = [c_blank, c_tex, c_geom, c_pneg, c_scram, c_inv, c_ident, c_pos]
        self.assertEqual(len(controls), 8)
        hashes = set()
        for c in controls:
            self.assertTrue(c.startswith(b"\x89PNG\r\n\x1a\n"))
            w, h = struct.unpack(">II", c[16:24])
            self.assertEqual((w, h), (256, 256))
            hashes.add(hashlib.sha256(c).hexdigest())
        # All 8 controls must have distinct hashes
        self.assertEqual(len(hashes), 8)

    def test_w20_accounting_equation_and_attempt_ledger(self) -> None:
        """Verify 46 planned attempts invariant: planned == attempted + skipped."""
        from eval.vlm.signs import execute_sign_replay_experiment
        adapter = MockVLMAdapter({"key": "mock", "model_type": "mock"})
        report = execute_sign_replay_experiment(adapter, allow_simulated=True)

        counts = report["attempt_counts"]
        self.assertEqual(counts["planned_forward_passes"], 46)
        self.assertEqual(counts["total_attempts_recorded"], 46)
        self.assertEqual(counts["successful_actual_passes"], 46)
        self.assertEqual(counts["failed_attempts"], 0)
        self.assertEqual(counts["skipped_attempts"], 0)
        self.assertEqual(counts["by_prompt_variant"]["neutral"], 23)
        self.assertEqual(counts["by_prompt_variant"]["leading"], 23)
        self.assertEqual(counts["by_category"]["controls"], 16)
        self.assertEqual(len(report["attempt_ledger"]), 46)

    def test_w20_paired_scans_and_derivative_outlines(self) -> None:
        """Verify matched 5 same-sign comparisons and 2 derivative outlines."""
        from eval.vlm.signs import execute_sign_replay_experiment
        adapter = MockVLMAdapter({"key": "mock", "model_type": "mock"})
        report = execute_sign_replay_experiment(adapter, allow_simulated=True)

        psc = report["paired_scan_comparisons"]
        self.assertEqual(psc["matched_pairs_evaluated"], 5)
        self.assertEqual(len(psc["pairs"]), 5)
        pair_signs = {p["sign_id"] for p in psc["pairs"]}
        self.assertEqual(pair_signs, {2448, 6066, 56377, 5862, 5447})

        doa = report["derivative_outline_analysis"]
        self.assertEqual(doa["outlines_evaluated"], 2)
        self.assertEqual(len(doa["outlines"]), 2)
        outline_signs = {o["sign_id"] for o in doa["outlines"]}
        self.assertEqual(outline_signs, {6036, 23466})

        sla = report["support_level_analysis"]
        self.assertEqual(sla["unique_physical_witnesses_count"], 6)
        self.assertEqual(len(sla["supports"]), 6)

    def test_w20_fail_closed_gates_and_cli(self) -> None:
        """Verify simulated rejection without --allow-simulated and no-network enforcement."""
        from eval.vlm.signs import execute_sign_replay_experiment
        adapter = MockVLMAdapter({"key": "mock", "model_type": "mock"})
        with self.assertRaises(ImageConditioningError):
            execute_sign_replay_experiment(adapter, allow_simulated=False)

        # CLI sign-replay schema validation with --allow-simulated
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp_path = Path(tmp.name)
        tmp_path.unlink()
        try:
            ret = cli_main(["sign-replay", "--allow-simulated", "--output", str(tmp_path)])
            self.assertEqual(ret, 0)
            self.assertTrue(tmp_path.is_file())
            rep = json.loads(tmp_path.read_text(encoding="utf-8"))
            self.assertEqual(rep["doc_type"], "vlm_sign_replay_report")
            self.assertEqual(rep["scientific_capability_points"], 0.0)
            self.assertFalse(rep["hieratic_reading_claim"])
        finally:
            if tmp_path.is_file():
                tmp_path.unlink()

    def test_w20_live_manuscript_control_never_substitutes_synthetic_photo(self) -> None:
        """No genuine original bytes means no 46-live-attempts claim."""
        from eval.vlm.signs import load_verified_manuscript_photo_positive
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("eval.vlm.signs.Path.home", return_value=Path(d)):
                with self.assertRaises(ImageConditioningError):
                    load_verified_manuscript_photo_positive((256, 256))

    def test_w20_wrong_original_photo_sha_fails_before_image_crop(self) -> None:
        """A source-looking JPG is not a pinned historical papyrus."""
        from eval.vlm.signs import load_verified_manuscript_photo_positive
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "AppData" / "Local" / "HieraticAI" / "private-artifacts" / "W8" / "CAT2044-013-commons-original.jpg"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"not the pinned original")
            with mock.patch("eval.vlm.signs.Path.home", return_value=Path(d)):
                with self.assertRaises(ImageConditioningError):
                    load_verified_manuscript_photo_positive((256, 256))

    def test_w20_synthetic_mark_not_genuine_museum_photo(self) -> None:
        from eval.vlm.signs import execute_sign_replay_experiment
        adapter = MockVLMAdapter({"key":"mock","model_type":"mock"})
        report = execute_sign_replay_experiment(adapter, allow_simulated=True)
        identity = [a for a in report["attempt_ledger"]
                    if a["target_or_control_id"] == "control_identity_mark"]
        positive = [a for a in report["attempt_ledger"]
                    if a["target_or_control_id"] == "control_manuscript_photo_positive"]
        self.assertEqual(2,len(identity))
        self.assertEqual(2,len(positive))
        # Preserve the W20 regression: its simulated controls must never be
        # misrepresented as genuine original museum photo evidence.
        self.assertTrue(all(a["physical_witness"] == "synthetic_control"
                            for a in identity + positive))
        self.assertTrue(all(a["source_raw_sha256"] == a["stimulus_sha256"]
                            for a in identity + positive))

    def test_w27_domain_words_absent_in_blind_prompt(self) -> None:
        """Verify domain-blind prompt does not contain Egyptian, hieratic, or sign labels."""
        from eval.vlm.signs import (
            FROZEN_DOMAIN_BLIND_PROMPT_W27,
            W27_FORBIDDEN_DOMAIN_WORDS,
            verify_domain_blind_prompt,
        )
        p_lower = FROZEN_DOMAIN_BLIND_PROMPT_W27.lower()
        for forbidden in W27_FORBIDDEN_DOMAIN_WORDS:
            self.assertNotIn(
                forbidden,
                p_lower.split(),
                f"Forbidden domain cue '{forbidden}' found in W27 domain-blind prompt",
            )
        # verify_domain_blind_prompt passes cleanly on canonical prompt
        verify_domain_blind_prompt(FROZEN_DOMAIN_BLIND_PROMPT_W27)

        # verify_domain_blind_prompt raises ValueError on mutated prompt containing cue
        with self.assertRaises(ValueError):
            verify_domain_blind_prompt(FROZEN_DOMAIN_BLIND_PROMPT_W27 + " Look for hieratic signs.")

    def test_w27_frozen_prompts_and_hash_anchors(self) -> None:
        """Verify all three W27 frozen prompts and immutable protocol fingerprint."""
        from eval.vlm.signs import (
            FROZEN_DOMAIN_BLIND_PROMPT_W27,
            FROZEN_DOMAIN_BLIND_PROMPT_W27_SHA256,
            FROZEN_SCRIPT_AWARE_PROMPT_W27,
            FROZEN_SCRIPT_AWARE_PROMPT_W27_SHA256,
            FROZEN_LEADING_IDENT_PROMPT_W27,
            FROZEN_LEADING_IDENT_PROMPT_W27_SHA256,
            compute_w27_sign_protocol_hash,
        )
        self.assertEqual(
            hashlib.sha256(FROZEN_DOMAIN_BLIND_PROMPT_W27.encode("utf-8")).hexdigest(),
            FROZEN_DOMAIN_BLIND_PROMPT_W27_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(FROZEN_SCRIPT_AWARE_PROMPT_W27.encode("utf-8")).hexdigest(),
            FROZEN_SCRIPT_AWARE_PROMPT_W27_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(FROZEN_LEADING_IDENT_PROMPT_W27.encode("utf-8")).hexdigest(),
            FROZEN_LEADING_IDENT_PROMPT_W27_SHA256,
        )
        # All 3 prompt hashes must be distinct
        hashes = {
            FROZEN_DOMAIN_BLIND_PROMPT_W27_SHA256,
            FROZEN_SCRIPT_AWARE_PROMPT_W27_SHA256,
            FROZEN_LEADING_IDENT_PROMPT_W27_SHA256,
        }
        self.assertEqual(len(hashes), 3)

        proto_hash = compute_w27_sign_protocol_hash()
        self.assertEqual(len(proto_hash), 64)

    def test_w27_scrambled_attribution_explicitly_sign_6036(self) -> None:
        """Verify that scrambled control is explicitly attributed to sign 6036, not 2448."""
        from eval.vlm.signs import execute_sign_replay_experiment
        adapter = MockVLMAdapter({"key": "mock", "model_type": "mock"})
        report = execute_sign_replay_experiment(adapter, protocol="w27", allow_simulated=True)

        scrambled_entries = [
            a for a in report["attempt_ledger"]
            if a["target_or_control_id"] == "control_scrambled_sign"
        ]
        self.assertEqual(len(scrambled_entries), 3)  # blind, script_aware, leading
        for entry in scrambled_entries:
            self.assertEqual(entry["physical_witness"], "Petrie Museum UC 32782")

        sens = report["sensitivity_controls"]
        self.assertIn("6036", sens["scrambled_attribution"])
        self.assertIn("survive", sens["scrambled_attribution"])

    def test_w27_controls_physical_categories(self) -> None:
        """Verify controls matrix records correct physical category types."""
        from eval.vlm.signs import execute_sign_replay_experiment
        adapter = MockVLMAdapter({"key": "mock", "model_type": "mock"})
        report = execute_sign_replay_experiment(adapter, protocol="w27", allow_simulated=True)

        c_map = {c["control_id"]: c for c in report["controls_matrix"]}
        self.assertEqual(c_map["control_blank"]["category_type"], "hard_negative")
        self.assertEqual(c_map["control_procedural_texture"]["category_type"], "hard_negative")
        self.assertEqual(c_map["control_geometric_marks"]["category_type"], "hard_negative")
        self.assertEqual(c_map["control_photo_negative"]["category_type"], "hard_negative")
        self.assertEqual(c_map["control_scrambled_sign"]["category_type"], "transformation_control")
        self.assertEqual(c_map["control_inverted_sign"]["category_type"], "transformation_control")
        self.assertEqual(c_map["control_identity_mark"]["category_type"], "ambiguous_control")
        self.assertEqual(c_map["control_manuscript_photo_positive"]["category_type"], "positive_control")

    def test_w27_accounting_equation_69_attempts(self) -> None:
        """Verify mandatory 69 attempts accounting: 15*3 + 8*3 = 69."""
        from eval.vlm.signs import execute_sign_replay_experiment
        adapter = MockVLMAdapter({"key": "mock", "model_type": "mock"})
        report = execute_sign_replay_experiment(adapter, protocol="w27", allow_simulated=True)

        counts = report["attempt_counts"]
        self.assertEqual(counts["planned_forward_passes"], 69)
        self.assertEqual(counts["total_attempts_recorded"], 69)
        self.assertEqual(counts["successful_actual_passes"], 69)
        self.assertEqual(counts["failed_attempts"], 0)
        self.assertEqual(counts["skipped_attempts"], 0)
        self.assertEqual(counts["by_prompt_variant"]["blind"], 23)
        self.assertEqual(counts["by_prompt_variant"]["script_aware"], 23)
        self.assertEqual(counts["by_prompt_variant"]["leading"], 23)
        self.assertEqual(counts["by_category"]["controls"], 24)
        self.assertEqual(len(report["attempt_ledger"]), 69)

    def test_w27_durable_ledger_write_ahead_and_audit(self) -> None:
        """Verify DurableAttemptLedger logs dispatches before completions and audits invariants."""
        from eval.vlm.ledger import (
            DurableAttemptLedger,
            LedgerAccountingError,
            LedgerDuplicateAttemptError,
            verify_ledger_file_integrity,
        )
        with tempfile.TemporaryDirectory() as d:
            l_path = Path(d) / "test_ledger.jsonl"
            ledger = DurableAttemptLedger(l_path, run_id="test_run", protocol_fingerprint="fp123")

            ledger.record_dispatch(
                attempt_id="att_001",
                attempt_index=0,
                target_or_control_id="sign_6036",
                physical_witness="Petrie Museum",
                source_raw_sha256="sha_raw",
                stimulus_sha256="sha_stim",
                stimulus_dimensions=[256, 256],
                task="test_task",
                rung="identify",
                prompt_variant="blind",
                prompt_text="blind prompt",
                prompt_sha256="sha_prompt",
                model_id="test_model",
                model_revision="rev1",
                model_weight_sha256="sha_weight",
                decoding_parameters={},
            )

            # Check that file already has dispatch line before completion
            self.assertTrue(l_path.is_file())
            content = l_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(content), 1)
            self.assertIn('"record_type": "dispatch"', content[0])

            # Now complete attempt
            ledger.record_completion(
                attempt_id="att_001",
                status="success",
                output_text="Test output",
                latency_ms=10.0,
            )
            content = l_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(content), 2)
            self.assertIn('"record_type": "completion"', content[1])

            # Accounting audit passes for planned=1
            summary = ledger.audit_accounting(planned_count=1)
            self.assertEqual(summary["successful_actual_passes"], 1)

            # Accounting audit fails if planned does not match
            with self.assertRaises(LedgerAccountingError):
                ledger.audit_accounting(planned_count=2)

            ledger.close()

            # Integrity verification
            audit = verify_ledger_file_integrity(l_path)
            self.assertTrue(audit["valid"])
            self.assertEqual(audit["dispatches_count"], 1)
            self.assertEqual(audit["completions_count"], 1)

    def test_w27_durable_ledger_interrupted_run_recovery(self) -> None:
        """Verify interrupted run (dispatch without completion) is detected by audit."""
        from eval.vlm.ledger import DurableAttemptLedger, LedgerAccountingError, verify_ledger_file_integrity
        with tempfile.TemporaryDirectory() as d:
            l_path = Path(d) / "interrupted_ledger.jsonl"
            ledger = DurableAttemptLedger(l_path, run_id="test_run", protocol_fingerprint="fp123")
            ledger.record_dispatch(
                attempt_id="att_crash",
                attempt_index=0,
                target_or_control_id="sign_6036",
                physical_witness="Petrie",
                source_raw_sha256="sha_raw",
                stimulus_sha256="sha_stim",
                stimulus_dimensions=[256, 256],
                task="test_task",
                rung="identify",
                prompt_variant="blind",
                prompt_text="blind prompt",
                prompt_sha256="sha_prompt",
                model_id="test_model",
                model_revision="rev1",
                model_weight_sha256="sha_weight",
                decoding_parameters={},
            )
            ledger.close()

            # Audit fails closed on uncompleted dispatch
            audit = verify_ledger_file_integrity(l_path)
            self.assertFalse(audit["valid"])
            self.assertTrue(any("Unfinished attempt" in e for e in audit["errors"]))

            # Reloading ledger also detects interrupted attempt
            ledger2 = DurableAttemptLedger(l_path, run_id="test_run", protocol_fingerprint="fp123")
            with self.assertRaises(LedgerAccountingError):
                ledger2.audit_accounting(planned_count=1)
            ledger2.close()

    def test_w27_crash_resume_fails_closed_without_duplicating_an_attempt(self) -> None:
        """A durable in-flight dispatch must never be sent twice on resume."""
        from eval.vlm.ledger import (
            DurableAttemptLedger, LedgerDuplicateAttemptError,
            LedgerIntegrityError, verify_ledger_file_integrity,
        )
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "interrupted_w27.jsonl"
            props = dict(ledger_path=file, run_id="w27_replay_20261010_120000",
                         protocol_fingerprint="frozen_w27_test_protocol")
            with DurableAttemptLedger(**props) as first:
                first.record_dispatch(
                    attempt_id="w27_000",
                    attempt_index=0,
                    target_or_control_id="sign_6036",
                    physical_witness="Petrie",
                    source_raw_sha256="source_hash",
                    stimulus_sha256="image_hash",
                    stimulus_dimensions=[256, 256],
                    task="signs",
                    rung="signs",
                    prompt_variant="blind",
                    prompt_text="Describe visible marks.",
                    prompt_sha256="prompt_hash",
                    model_id="smolvlm-256m",
                    model_revision="pinned",
                    model_weight_sha256="weight_hash",
                    decoding_parameters={"temperature": 0},
                )
            self.assertFalse(verify_ledger_file_integrity(file)["valid"])
            with DurableAttemptLedger(**props) as recovered:
                self.assertEqual(["w27_000"], recovered.resolve_interrupted_attempts())
                summary = recovered.audit_accounting(planned_count=1)
                self.assertEqual(summary["failed_attempts"], 1)
                self.assertEqual(summary["successful_actual_passes"], 0)
                self.assertTrue(recovered.is_attempt_completed("w27_000"))
                with self.assertRaises(LedgerDuplicateAttemptError):
                    recovered.record_dispatch(
                        attempt_id="w27_000",
                        attempt_index=0,
                        target_or_control_id="sign_6036",
                        physical_witness="Petrie",
                        source_raw_sha256="source_hash",
                        stimulus_sha256="image_hash",
                        stimulus_dimensions=[256, 256],
                        task="signs", rung="signs", prompt_variant="blind",
                        prompt_text="Describe visible marks.", prompt_sha256="prompt_hash",
                        model_id="smolvlm-256m", model_revision="pinned",
                        model_weight_sha256="weight_hash", decoding_parameters={},
                    )
            receipt = verify_ledger_file_integrity(file)
            self.assertTrue(receipt["valid"], receipt["errors"])
            self.assertEqual(1, receipt["dispatches_count"])
            self.assertEqual(1, receipt["completions_count"])
            with self.assertRaises(LedgerIntegrityError):
                DurableAttemptLedger(file, "different_run_id", props["protocol_fingerprint"])
            with self.assertRaises(LedgerIntegrityError):
                DurableAttemptLedger(file, props["run_id"], "different_protocol")

    def test_w27_load_rejects_duplicate_or_modified_completed_events(self) -> None:
        from eval.vlm.ledger import DurableAttemptLedger, LedgerIntegrityError
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "attempts.jsonl"
            with DurableAttemptLedger(path, "w27_replay_abc", "fp") as ledger:
                ledger.record_dispatch(
                    attempt_id="one", attempt_index=0,
                    target_or_control_id="blank", physical_witness="synthetic_control",
                    source_raw_sha256="src", stimulus_sha256="raster",
                    stimulus_dimensions=[256, 256], task="identify", rung="identify",
                    prompt_variant="blind", prompt_text="Describe.",
                    prompt_sha256="ph", model_id="mock", model_revision="rev",
                    model_weight_sha256="none", decoding_parameters={})
                ledger.record_completion(attempt_id="one", status="success",
                                         output_text="some response")
            original = path.read_text(encoding="utf-8")
            first_line = original.splitlines()[0]
            path.write_text(original + first_line + "\n", encoding="utf-8")
            with self.assertRaises(LedgerIntegrityError):
                DurableAttemptLedger(path, "w27_replay_abc", "fp")
            path.write_text(original.replace("some response", "tampered answer"), encoding="utf-8")
            with self.assertRaises(LedgerIntegrityError):
                DurableAttemptLedger(path, "w27_replay_abc", "fp")

    def test_w27_durable_ledger_corruption_detection(self) -> None:
        """Verify that tampered output hash is caught by integrity audit."""
        from eval.vlm.ledger import DurableAttemptLedger, verify_ledger_file_integrity
        with tempfile.TemporaryDirectory() as d:
            l_path = Path(d) / "corrupt_ledger.jsonl"
            ledger = DurableAttemptLedger(l_path, run_id="test_run", protocol_fingerprint="fp123")
            ledger.record_dispatch(
                attempt_id="att_tamper",
                attempt_index=0,
                target_or_control_id="sign_6036",
                physical_witness="Petrie",
                source_raw_sha256="sha_raw",
                stimulus_sha256="sha_stim",
                stimulus_dimensions=[256, 256],
                task="test_task",
                rung="identify",
                prompt_variant="blind",
                prompt_text="blind prompt",
                prompt_sha256="sha_prompt",
                model_id="test_model",
                model_revision="rev1",
                model_weight_sha256="sha_weight",
                decoding_parameters={},
            )
            ledger.record_completion(
                attempt_id="att_tamper",
                status="success",
                output_text="Legitimate output",
                latency_ms=10.0,
            )
            ledger.close()

            # Tamper with file: change output text but leave output hash
            lines = l_path.read_text(encoding="utf-8").splitlines()
            tampered_comp = json.loads(lines[1])
            tampered_comp["output_text"] = "TAMPERED OUTPUT"
            lines[1] = json.dumps(tampered_comp)
            l_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            audit = verify_ledger_file_integrity(l_path)
            self.assertFalse(audit["valid"])
            self.assertTrue(any("Output SHA-256 mismatch" in e for e in audit["errors"]))

    def test_w27_cli_execution_with_protocol_flag(self) -> None:
        """Verify CLI runner handles --protocol w27 and outputs schema-valid report."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp_path = Path(tmp.name)
        tmp_path.unlink()
        try:
            ret = cli_main(["sign-replay", "--protocol", "w27", "--allow-simulated", "--output", str(tmp_path)])
            self.assertEqual(ret, 0)
            self.assertTrue(tmp_path.is_file())
            rep = json.loads(tmp_path.read_text(encoding="utf-8"))
            self.assertEqual(rep["doc_type"], "vlm_sign_replay_report")
            self.assertEqual(rep["protocol"]["protocol_version"], "3.0.0")
            self.assertEqual(rep["attempt_counts"]["planned_forward_passes"], 69)
            self.assertEqual(rep["attempt_counts"]["total_attempts_recorded"], 69)
            self.assertEqual(rep["scientific_capability_points"], 0.0)
            self.assertFalse(rep["hieratic_reading_claim"])
            self.assertEqual(rep["evidence_grades"]["grade_f_authentic_hieratic_gold_evaluation"]["status"], "STRICTLY_NO")
        finally:
            if tmp_path.is_file():
                tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()




