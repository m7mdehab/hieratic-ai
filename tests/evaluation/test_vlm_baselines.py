"""Comprehensive synthetic unit and negative tests for VLM baseline evaluation harness.

Tests cover:
- Schema conformity and execution gate enforcement (zero-spend)
- Prompt drift and cryptographic hash validation
- Quarantined demonstration rights clearance and leakage detection
- Mandatory image conditioning enforcement
- Attempt preservation (successes, errors, abstentions, timeouts, refusals)
- Manifest auditing and tampering rejection
- Scorer stability, metrics accuracy, and bootstrap uncertainty bounds
- Paired comparison difference statistics
- Open-weight model hardware barrier reporting
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
    MockVLMAdapter,
    OpenWeightVLMAdapter,
    get_adapter,
)
from eval.vlm.runner import RunnerError, VLMRunner
from eval.vlm.scorer import (
    bootstrap_ci,
    character_error_rate,
    chrf_score,
    compare_manifests,
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
        mutated["execution_gate"]["max_paid_spend_usd"] = 50.0  # unapproved spend
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
        mutated["models"].append(mutated["models"][0])  # duplicate key
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
        # Edit template text without updating hash
        mutated["prompts"]["identify"]["zero_shot"]["user_template"] += " EXTRA TEXT"
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
            yaml.dump(mutated, tmp)
            tmp_path = Path(tmp.name)
        try:
            errors = validate_suite(tmp_path, SCHEMA_PATH)
            self.assertTrue(any("Prompt drift detected" in e for e in errors))
        finally:
            tmp_path.unlink()

    # --- 2. Quarantined Demonstrations & Leakage Prevention ---

    def test_canonical_demonstrations_validate_successfully(self) -> None:
        errors = validate_demonstrations(DEMOS_PATH, SCHEMA_PATH)
        self.assertEqual(errors, [], f"Canonical demonstrations failed validation: {errors}")

    def test_demonstration_leakage_against_eval_set_is_detected(self) -> None:
        # Pass an eval set containing one of the demo IDs
        known_eval = {"DEMO-IDENT-001", "RANDOM-TEST-999"}
        errors = validate_demonstrations(DEMOS_PATH, SCHEMA_PATH, known_eval_items=known_eval)
        self.assertTrue(any("Leakage violation" in e and "DEMO-IDENT-001" in e for e in errors))

    def test_demonstration_using_hieraticbench_prefix_fails(self) -> None:
        mutated = copy.deepcopy(self.demos_data)
        mutated["items"][0]["demo_id"] = "DEMO-AKU-001"  # reserved benchmark prefix with DEMO-
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
            yaml.dump(mutated, tmp)
            tmp_path = Path(tmp.name)
        try:
            errors = validate_demonstrations(tmp_path, SCHEMA_PATH)
            self.assertTrue(any("reserved HieraticBench prefix" in e for e in errors))
        finally:
            tmp_path.unlink()

    def test_unapproved_rights_in_demonstrations_fails(self) -> None:
        mutated = copy.deepcopy(self.demos_data)
        mutated["rights_review"]["rights_review_status"] = "in_review"
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
            yaml.dump(mutated, tmp)
            tmp_path = Path(tmp.name)
        try:
            errors = validate_demonstrations(tmp_path, SCHEMA_PATH)
            self.assertTrue(any("approved rights review" in e for e in errors))
        finally:
            tmp_path.unlink()

    # --- 3. Mandatory Image Conditioning ---

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

    # --- 4. Attempt Preservation & Auditor ---

    def test_runner_preserves_all_attempts_without_dropouts(self) -> None:
        adapter = MockVLMAdapter(self.suite_data["models"][0], simulated_mode="normal")
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()
        manifest = runner.run_suite(items, shot_mode="both")

        self.assertEqual(len(manifest["attempts"]), len(items) * 2)
        self.assertEqual(manifest["coverage_summary"]["total_attempts"], len(items) * 2)
        self.assertEqual(manifest["coverage_summary"]["success_count"], len(items) * 2)
        self.assertEqual(manifest["coverage_summary"]["coverage_rate"], 1.0)

    def test_runner_preserves_simulated_abstentions(self) -> None:
        adapter = MockVLMAdapter(self.suite_data["models"][0], simulated_mode="force_abstention")
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()[:2]
        manifest = runner.run_suite(items, shot_mode="zero_shot")

        self.assertEqual(len(manifest["attempts"]), 2)
        self.assertEqual(manifest["coverage_summary"]["abstention_count"], 2)
        self.assertEqual(manifest["coverage_summary"]["coverage_rate"], 0.0)
        for a in manifest["attempts"]:
            self.assertEqual(a["status"], "abstained")
            self.assertEqual(a["cleaned_prediction"], "[ABSTAIN]")

    def test_runner_preserves_simulated_timeouts(self) -> None:
        adapter = MockVLMAdapter(self.suite_data["models"][0], simulated_mode="force_timeout")
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()[:2]
        manifest = runner.run_suite(items, shot_mode="zero_shot")

        self.assertEqual(manifest["coverage_summary"]["timeout_count"], 2)
        for a in manifest["attempts"]:
            self.assertEqual(a["status"], "timeout")
            self.assertIsNone(a["raw_output"])
            self.assertIn("timeout", a["error_message"].lower())

    def test_runner_preserves_simulated_refusals(self) -> None:
        adapter = MockVLMAdapter(self.suite_data["models"][0], simulated_mode="force_refusal")
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()[:2]
        manifest = runner.run_suite(items, shot_mode="zero_shot")

        self.assertEqual(manifest["coverage_summary"]["refusal_count"], 2)
        for a in manifest["attempts"]:
            self.assertEqual(a["status"], "refused")
            self.assertIn("refusal", a["error_message"].lower())

    def test_manifest_auditor_detects_missing_attempt(self) -> None:
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()[:3]
        manifest = runner.run_suite(items, shot_mode="zero_shot")

        # Drop one attempt to simulate dropped failed sample
        manifest["attempts"].pop()

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(manifest, tmp)
            tmp_path = Path(tmp.name)
        try:
            errors = audit_manifest(tmp_path, SUITE_PATH, SCHEMA_PATH)
            self.assertTrue(any("Attempt count mismatch" in e for e in errors))
        finally:
            tmp_path.unlink()

    def test_manifest_auditor_detects_suite_hash_tampering(self) -> None:
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()[:2]
        manifest = runner.run_suite(items, shot_mode="zero_shot")
        manifest["suite_sha256"] = "f" * 64  # forged hash

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(manifest, tmp)
            tmp_path = Path(tmp.name)
        try:
            errors = audit_manifest(tmp_path, SUITE_PATH, SCHEMA_PATH)
            self.assertTrue(any("suite hash mismatch" in e for e in errors))
        finally:
            tmp_path.unlink()

    # --- 5. Metrics, Scorer, and Uncertainty ---

    def test_levenshtein_distance_and_error_rates(self) -> None:
        self.assertEqual(levenshtein_distance("hieratic", "hieratic"), 0)
        self.assertEqual(levenshtein_distance("", "test"), 4)
        self.assertEqual(levenshtein_distance("cat", "hat"), 1)

        self.assertAlmostEqual(character_error_rate("hieratic", "hieratic"), 0.0)
        self.assertAlmostEqual(character_error_rate("hieratic", "hierat"), 2 / 8)
        self.assertAlmostEqual(character_error_rate("hieratic", "hierati"), 1 / 8)
        self.assertAlmostEqual(character_error_rate("", ""), 0.0)

        self.assertAlmostEqual(word_error_rate("king of upper egypt", "king of upper egypt"), 0.0)
        self.assertAlmostEqual(word_error_rate("king of upper egypt", "king of egypt"), 1 / 4)

    def test_sentence_bleu_and_chrf(self) -> None:
        ref = "Beginning of the calculation of the reckoning of things."
        hyp_exact = "Beginning of the calculation of the reckoning of things."
        hyp_diff = "End of the calculation of something else entirely."

        bleu_exact = sentence_bleu(ref, hyp_exact)
        bleu_diff = sentence_bleu(ref, hyp_diff)
        self.assertAlmostEqual(bleu_exact, 1.0, places=2)
        self.assertLess(bleu_diff, bleu_exact)

        chrf_exact = chrf_score(ref, hyp_exact)
        chrf_diff = chrf_score(ref, hyp_diff)
        self.assertAlmostEqual(chrf_exact, 1.0, places=2)
        self.assertLess(chrf_diff, chrf_exact)

    def test_bootstrap_confidence_interval_bounds(self) -> None:
        values = [0.8, 0.85, 0.9, 0.75, 0.88, 0.82, 0.86, 0.79]
        low, high = bootstrap_ci(values, n_resamples=500, alpha=0.05, seed=123)
        self.assertLessEqual(low, high)
        self.assertGreaterEqual(low, 0.70)
        self.assertLessEqual(high, 0.95)

    def test_is_abstention_detection(self) -> None:
        self.assertTrue(is_abstention("[ABSTAIN] Unclear"))
        self.assertTrue(is_abstention("The inscription is illegible, uncertain."))
        self.assertFalse(is_abstention("Hieratic"))
        self.assertFalse(is_abstention(None))

    def test_scoring_manifest_and_paired_comparison(self) -> None:
        adapter = MockVLMAdapter(self.suite_data["models"][0])
        runner = VLMRunner(self.suite_data, self.demos_data, adapter, suite_path=SUITE_PATH, demos_path=DEMOS_PATH)
        items = create_synthetic_items()
        gold = create_synthetic_gold()

        manifest_zero = runner.run_suite(items, shot_mode="zero_shot", manifest_id="run_zero_01")
        manifest_few = runner.run_suite(items, shot_mode="few_shot", manifest_id="run_few_01")

        report_zero = score_manifest(manifest_zero, gold)
        self.assertIn("identify", report_zero["rungs"])
        self.assertIn("signs", report_zero["rungs"])
        self.assertIn("transliterate", report_zero["rungs"])
        self.assertIn("translate", report_zero["rungs"])

        comparisons = compare_manifests(manifest_zero, manifest_few, gold)
        self.assertGreaterEqual(len(comparisons), 1)
        for comp in comparisons:
            self.assertEqual(comp["baseline_manifest_id"], "run_zero_01")
            self.assertEqual(comp["comparison_manifest_id"], "run_few_01")
            self.assertIn("ci_95_delta", comp)

    # --- 6. Open-Weight Model Hardware Barrier Reporting ---

    def test_open_weight_adapter_reports_barrier_cleanly(self) -> None:
        qwen_cfg = next(m for m in self.suite_data["models"] if m["key"] == "qwen2.5-vl-7b-instruct")
        adapter = OpenWeightVLMAdapter(qwen_cfg)
        status = adapter.check_availability()
        self.assertIsInstance(status, AvailabilityStatus)
        # In CPU CI or standard dev without CUDA/weights, it must report unavailable or barrier
        if not status.available:
            self.assertTrue(len(status.reason) > 0)
            # Prediction must record structured failure rather than making paid external network calls
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

    # --- 7. CLI End-to-End ---

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


if __name__ == "__main__":
    unittest.main()
