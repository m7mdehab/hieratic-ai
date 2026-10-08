from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from tools import linguistic_normalization as ling
from tools.source_registry import load_yaml

ROOT = Path(__file__).resolve().parents[2]
ANNOTATION_PATH = ROOT / "data/examples/annotation_ambiguous.yaml"
REQUEST_PATH = ROOT / "ling/normalization/examples/synthetic.yaml"


def load_yaml_file(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class LinguisticNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.annotation, self.annotation_bytes = ling.read(ANNOTATION_PATH)
        self.request, _ = ling.read(REQUEST_PATH)
        self.registry = load_yaml(ROOT / "data/sources/registry.yaml")

    def test_synthetic_cli_validation_and_output_are_reproducible(self):
        checked = subprocess.run([sys.executable, "-m", "tools.linguistic_normalization", "validate", str(REQUEST_PATH), "--annotation", str(ANNOTATION_PATH)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, checked.returncode, checked.stderr)
        self.assertIn("PASS:", checked.stdout)
        first = ling.build(self.request, self.annotation, self.annotation_bytes, self.registry)
        second = ling.build(self.request, self.annotation, self.annotation_bytes, self.registry)
        self.assertEqual(first, second)
        item = first["items"][0]
        self.assertEqual("uncertain_with_alternatives", item["gold_status"])
        self.assertEqual(["transliteration-a", "transliteration-b"], item["acceptable_reading_ids"])
        self.assertEqual(2, len(item["values"]))
        self.assertFalse(item["linguistic_analysis"]["transformed"])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "normalization.json"
            normalized = subprocess.run([sys.executable, "-m", "tools.linguistic_normalization", "normalize", str(REQUEST_PATH), "--annotation", str(ANNOTATION_PATH), "--output", str(output)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, normalized.returncode, normalized.stderr)
            self.assertEqual(first["normalization_version_id"], json.loads(output.read_text(encoding="utf-8"))["normalization_version_id"])
            again = subprocess.run([sys.executable, "-m", "tools.linguistic_normalization", "normalize", str(REQUEST_PATH), "--annotation", str(ANNOTATION_PATH), "--output", str(output)], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(0, again.returncode)
            self.assertIn("immutable", again.stderr)

    def test_atomic_publish_never_overwrites_concurrent_destination(self):
        from unittest.mock import patch
        import os
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "normalization.json"
            original_link = os.link
            marker = "another-writer-is-authoritative"
            def competing_link(src, dst):
                output.write_text(marker, encoding="utf-8")
                return original_link(src, dst)
            with patch.object(ling.os, "link", side_effect=competing_link):
                outcome = ling.main([
                    "normalize", str(REQUEST_PATH), "--annotation",
                    str(ANNOTATION_PATH), "--output", str(output)
                ])
            self.assertEqual(1, outcome)
            self.assertEqual(marker, output.read_text(encoding="utf-8"))
            self.assertEqual([], list(output.parent.glob(".normalization.json.*.tmp")))

    def test_normalization_collision_is_reported_without_collapsing_alternatives(self):
        annotation = copy.deepcopy(self.annotation)
        layer = annotation["lines"][0]["transliteration"]
        layer["values"][0]["value"] = "a\u030a"
        layer["values"][1]["value"] = "å"
        raw = json.dumps(annotation, ensure_ascii=False, sort_keys=True).encode("utf-8")
        request = copy.deepcopy(self.request)
        request["annotation_sha256"] = hashlib.sha256(raw).hexdigest()
        errors, _ = ling.validate_request(request, annotation, raw, self.registry)
        self.assertEqual([], errors)
        result = ling.build(request, annotation, raw, self.registry)
        self.assertEqual(1, len(result["collisions"]))
        self.assertFalse(result["collisions"][0]["collapsed"])
        self.assertEqual(2, len(result["items"][0]["values"]))
        self.assertEqual(1, len({value["normalized_text"] for value in result["items"][0]["values"]}))

    def test_broken_line_value_and_annotation_hash_are_refused(self):
        errors, _ = ling.validate_request(self.request, self.annotation, self.annotation_bytes, self.registry)
        self.assertEqual([], errors)
        request = copy.deepcopy(self.request)
        request["items"][0]["line_id"] = "missing-line"
        errors, _ = ling.validate_request(request, self.annotation, self.annotation_bytes, self.registry)
        self.assertTrue(any("unknown DATA-004 line_id" in error for error in errors), errors)
        request = copy.deepcopy(self.request)
        request["items"][0]["source_value_ids"] = ["transliteration-a"]
        errors, _ = ling.validate_request(request, self.annotation, self.annotation_bytes, self.registry)
        self.assertTrue(any("preserve every DATA-004 alternative" in error for error in errors), errors)
        request = copy.deepcopy(self.request)
        request["annotation_sha256"] = "0" * 64
        errors, _ = ling.validate_request(request, self.annotation, self.annotation_bytes, self.registry)
        self.assertTrue(any("exact DATA-004 input bytes" in error for error in errors), errors)

    def test_token_links_and_alternatives_resolve_to_data004(self):
        annotation = copy.deepcopy(self.annotation)
        line = annotation["lines"][0]
        line["normalized_representation"]["tokenization_profile"] = "synthetic-tokenization/1"
        line["normalized_representation"]["tokens"] = [{
            "token_id": "token-2", "sequence_ref": line["sequence_id"], "gold_status": "uncertain_with_alternatives",
            "value": {"gold_status": "uncertain_with_alternatives", "values": [
                {"value_id": "token-value-a", "value": "A\u030a", "confidence": 0.5, "equivalent_to_selected": False},
                {"value_id": "token-value-b", "value": "Å", "confidence": 0.5, "equivalent_to_selected": False}],
                "selected_value_id": None, "explanation": "Synthetic alternative spellings."},
            "acceptable_lemmas": [], "morphology_bundles": []
        }]
        raw = json.dumps(annotation, ensure_ascii=False, sort_keys=True).encode("utf-8")
        request = copy.deepcopy(self.request)
        request["annotation_sha256"] = hashlib.sha256(raw).hexdigest()
        request["profile_id"] = "unicode-nfc"
        request["items"] = [{"unit_id": "synthetic-token-2", "line_id": "line-2", "source_layer": "normalized_token", "token_id": "token-2",
                             "reading_group_id": "synthetic-token-readings", "source_value_ids": ["token-value-a", "token-value-b"],
                             "whitespace_semantics": "unknown", "line_break_semantics": "unknown"}]
        errors, _ = ling.validate_request(request, annotation, raw, self.registry)
        self.assertEqual([], errors)
        result = ling.build(request, annotation, raw, self.registry)
        item = result["items"][0]
        self.assertEqual("token-2", item["token_id"])
        self.assertEqual(["token-value-a", "token-value-b"], item["acceptable_reading_ids"])
        self.assertEqual(2, len(item["diplomatic_transliteration"]["values"]))

    def test_missing_transliteration_gold_stays_missing(self):
        annotation = copy.deepcopy(self.annotation)
        del annotation["lines"][0]["transliteration"]
        raw = json.dumps(annotation, ensure_ascii=False, sort_keys=True).encode("utf-8")
        request = copy.deepcopy(self.request)
        request["annotation_sha256"] = hashlib.sha256(raw).hexdigest()
        request["profile_id"] = "identity"
        request["items"][0]["source_value_ids"] = []
        errors, _ = ling.validate_request(request, annotation, raw, self.registry)
        self.assertEqual([], errors)
        item = ling.build(request, annotation, raw, self.registry)["items"][0]
        self.assertEqual("missing_annotation", item["gold_status"])
        self.assertEqual([], item["values"])

    def test_profile_rules_preserve_editorial_marks_and_respect_whitespace_semantics(self):
        output, evidence = ling.normalize_text("  [A?]  \r\n B  ", "translit_compare_v1", "1.0.0", "significant", "significant")
        self.assertEqual("[A?]  \n B", output)
        self.assertIn("no_punctuation_rewrite", load_yaml_file(ROOT / "ling/normalization/profiles.yaml")["profiles"]["translit_compare_v1"]["restrictions"])
        self.assertFalse(evidence["reversible"])
        collapsed, _ = ling.normalize_text("A  B", "translit_compare_v1", "1.0.0", "token_separator", "significant")
        self.assertEqual("A B", collapsed)

    def test_unsupported_profile_and_invalid_token_reference_fail_closed(self):
        with self.assertRaisesRegex(ling.NormalizationError, "unsupported profile/version"):
            ling.normalize_text("value", "invented-lexical-rule", "1", "unknown", "unknown")
        annotation = copy.deepcopy(self.annotation)
        raw = json.dumps(annotation, ensure_ascii=False, sort_keys=True).encode("utf-8")
        request = copy.deepcopy(self.request)
        request["annotation_sha256"] = hashlib.sha256(raw).hexdigest()
        request["items"][0].update({"source_layer": "normalized_token", "token_id": "missing-token"})
        errors, _ = ling.validate_request(request, annotation, raw, self.registry)
        self.assertTrue(any("unknown DATA-004 token_id" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
