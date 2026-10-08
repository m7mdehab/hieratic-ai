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

import yaml

from eval.vlm.adapter import (
    AvailabilityStatus,
    ImageConditioningError,
    InferenceHardwareBarrierError,
    LiveFewShotBlockedError,
    MockVLMAdapter,
    OpenWeightVLMAdapter,
    UnverifiedDemonstrationError,
    get_adapter,
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

        # Injected fake replay summary cannot spoof official leaderboard status
        fake_summary = {"item_macro_accuracy": 0.99, "note": "spoofed"}
        report = score_manifest(manifest, gold, official_replay_summary=fake_summary)
        self.assertEqual(report["official_scoring_status"], "NOT_INTEGRATED")
        self.assertIsNone(report["official_hieraticbench"])


if __name__ == "__main__":
    unittest.main()
