"""EVAL-005 regression tests: all synthetic, no manuscript or benchmark content."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from eval.analysis import review


class ErrorAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.taxonomy, cls.schema, cls.metrics = review.load_contracts()
        cls.examples = review.read_reviews(
            review.PROJECT_ROOT / "eval/analysis/examples/synthetic_reviews.jsonl"
        )

    def test_taxonomy_covers_visual_linguistic_and_integrity_stages(self) -> None:
        layers = {x["layer"] for x in self.taxonomy["error_codes"]}
        self.assertTrue({"script_identification", "layout", "sign_recognition",
                         "sequence_recognition", "transliteration", "translation",
                         "calibration", "uncertainty", "generalization",
                         "evaluation_integrity"}.issubset(layers))

    def test_synthetic_records_validate(self) -> None:
        review.validate_reviews(self.examples, self.taxonomy, self.schema, self.metrics)

    def test_duplicate_error_codes_in_taxonomy_fail(self) -> None:
        tax = copy.deepcopy(self.taxonomy)
        tax["error_codes"].append(tax["error_codes"][0])
        with tempfile.TemporaryDirectory() as temp:
            import yaml
            path = Path(temp) / "tax.yaml"
            path.write_text(yaml.safe_dump(tax), encoding="utf-8")
            with self.assertRaisesRegex(review.ReviewError, "Duplicate taxonomy"):
                review.load_contracts(taxonomy_path=path)

    def test_invalid_taxonomy_code_fails(self) -> None:
        rows = copy.deepcopy(self.examples)
        rows[0]["primary_error"] = "NOT_REAL"
        rows[0]["error_codes"] = ["NOT_REAL"]
        with self.assertRaisesRegex(review.ReviewError, "unknown taxonomy"):
            review.validate_reviews(rows, self.taxonomy, self.schema, self.metrics)

    def test_duplicate_record_id_fails(self) -> None:
        rows = copy.deepcopy(self.examples)
        rows[1]["record_id"] = rows[0]["record_id"]
        with self.assertRaisesRegex(review.ReviewError, "Duplicate record_id"):
            review.validate_reviews(rows, self.taxonomy, self.schema, self.metrics)

    def test_primary_code_must_be_in_labels(self) -> None:
        rows = copy.deepcopy(self.examples)
        rows[0]["primary_error"] = "SIGN_OMIT"
        with self.assertRaisesRegex(review.ReviewError, "primary_error must appear"):
            review.validate_reviews(rows, self.taxonomy, self.schema, self.metrics)

    def test_adjudicated_requires_reviewer(self) -> None:
        rows = copy.deepcopy(self.examples)
        del rows[0]["reviewer_id"]
        with self.assertRaisesRegex(review.ReviewError, "schema error"):
            review.validate_reviews(rows, self.taxonomy, self.schema, self.metrics)

    def test_adjudicated_requires_evidence(self) -> None:
        rows = copy.deepcopy(self.examples)
        rows[0]["evidence_refs"] = []
        with self.assertRaisesRegex(review.ReviewError, "schema error"):
            review.validate_reviews(rows, self.taxonomy, self.schema, self.metrics)

    def test_gold_unavailable_cannot_claim_scored(self) -> None:
        rows = copy.deepcopy(self.examples)
        rows[2]["score_status"] = "scored"
        with self.assertRaisesRegex(review.ReviewError, "schema error"):
            review.validate_reviews(rows, self.taxonomy, self.schema, self.metrics)

    def test_gold_unavailable_cannot_claim_sign_error(self) -> None:
        rows = copy.deepcopy(self.examples)
        rows[2]["primary_error"] = "SIGN_SUBSTITUTE"
        rows[2]["error_codes"] = ["SIGN_SUBSTITUTE"]
        with self.assertRaisesRegex(review.ReviewError, "without scorable gold"):
            review.validate_reviews(rows, self.taxonomy, self.schema, self.metrics)

    def test_contamination_cannot_be_scored(self) -> None:
        rows = copy.deepcopy(self.examples)
        rows[0]["exposure_status"] = "confirmed"
        with self.assertRaisesRegex(review.ReviewError, "schema error"):
            review.validate_reviews(rows, self.taxonomy, self.schema, self.metrics)

    def test_sealed_cannot_claim_scored_reading(self) -> None:
        rows = copy.deepcopy(self.examples)
        rows[3]["score_status"] = "scored"
        rows[3]["gold_status"] = "certain"
        with self.assertRaisesRegex(review.ReviewError, "sealed items"):
            review.validate_reviews(rows, self.taxonomy, self.schema, self.metrics)

    def test_unknown_upstream_reference_fails(self) -> None:
        rows = copy.deepcopy(self.examples)
        rows[1]["upstream_record_ids"] = ["MISSING"]
        with self.assertRaisesRegex(review.ReviewError, "unknown upstream"):
            review.validate_reviews(rows, self.taxonomy, self.schema, self.metrics)

    def test_cross_document_causal_link_fails(self) -> None:
        rows = copy.deepcopy(self.examples)
        rows[1]["document_id"] = "OTHER-DOCUMENT"
        with self.assertRaisesRegex(review.ReviewError, "cross-run/document"):
            review.validate_reviews(rows, self.taxonomy, self.schema, self.metrics)

    def test_cyclic_causal_references_fail(self) -> None:
        rows = copy.deepcopy(self.examples)
        rows[0]["upstream_record_ids"] = ["SYNTH-R2"]
        with self.assertRaisesRegex(review.ReviewError, "Cyclic"):
            review.validate_reviews(rows, self.taxonomy, self.schema, self.metrics)

    def test_invalid_metric_id_fails(self) -> None:
        rows = copy.deepcopy(self.examples)
        rows[0]["metric_id"] = "MADE_UP_SCORE"
        with self.assertRaisesRegex(review.ReviewError, "unknown EVAL-001 metric"):
            review.validate_reviews(rows, self.taxonomy, self.schema, self.metrics)

    def test_contract_version_mismatch_fails(self) -> None:
        rows = copy.deepcopy(self.examples)
        rows[0]["metric_contract_version"] = "0.0.1"
        with self.assertRaisesRegex(review.ReviewError, "metric_contract_version mismatch"):
            review.validate_reviews(rows, self.taxonomy, self.schema, self.metrics)

    def test_public_summary_never_mentions_sealed_items(self) -> None:
        result = review.summarize(self.examples, self.taxonomy)
        self.assertEqual(3, result["review_records"])
        self.assertEqual(2, result["adjudicated_clean_scored_errors"])
        self.assertEqual(1, result["affected_document_count"])
        serialized = json.dumps(result)
        self.assertNotIn("SYNTH-SEALED", serialized)
        self.assertNotIn("SYNTH-R4", serialized)
        self.assertEqual(1, result["primary_error_counts"]["SIGN_SUBSTITUTE"])
        self.assertEqual(1, result["primary_error_counts"]["TRAD_FLUENCY_MASK"])

    def test_internal_summary_reports_sealed_without_raw_text(self) -> None:
        result = review.summarize(self.examples, self.taxonomy, publication="internal")
        self.assertEqual(4, result["review_records"])
        self.assertNotIn("record_id", result)
        self.assertNotIn("document_id", result)

    def test_review_events_are_not_false_accuracy_denominators(self) -> None:
        result = review.summarize(self.examples, self.taxonomy)
        self.assertFalse(result["rates_computable"])
        self.assertIn("not a denominator", result["denominator_warning"])
        self.assertNotIn("accuracy", result)

    def test_unknown_fields_fail_to_prevent_content_leak(self) -> None:
        rows = copy.deepcopy(self.examples)
        rows[0]["raw_secret_answer"] = "synthetic example"
        with self.assertRaisesRegex(review.ReviewError, "schema error"):
            review.validate_reviews(rows, self.taxonomy, self.schema, self.metrics)

    def test_cli_validate_and_summarize(self) -> None:
        from contextlib import redirect_stdout
        from io import StringIO
        path = review.PROJECT_ROOT / "eval/analysis/examples/synthetic_reviews.jsonl"
        buf = StringIO()
        with redirect_stdout(buf):
            self.assertEqual(0, review.main(["validate", "--input", str(path)]))
        self.assertIn("PASS:", buf.getvalue())
        with redirect_stdout(buf := StringIO()):
            self.assertEqual(0, review.main(["summarize", "--input", str(path)]))
        self.assertEqual(3, json.loads(buf.getvalue())["review_records"])

    def test_cli_fail_closed_on_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.jsonl"
            path.write_text('{"invalid":', encoding="utf-8")
            from contextlib import redirect_stderr
            from io import StringIO
            with redirect_stderr(StringIO()):
                self.assertEqual(1, review.main(["validate", "--input", str(path)]))


if __name__ == "__main__":
    unittest.main()
