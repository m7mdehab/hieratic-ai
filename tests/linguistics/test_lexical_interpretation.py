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

from tools import lexical_interpretation as lexical
from tools import linguistic_normalization as normalization
from tools.source_registry import load_yaml

ROOT = Path(__file__).resolve().parents[2]
ANNOTATION_PATH = ROOT / "data/examples/annotation_ambiguous.yaml"
REQUEST_PATH = ROOT / "ling/normalization/examples/synthetic.yaml"
LEXICON_PATH = ROOT / "ling/lexical/examples/synthetic.yaml"


class LexicalInterpretationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / "schemas/lexical_interpretation.schema.json").read_text(encoding="utf-8"))
        cls.registry = load_yaml(ROOT / "data/sources/registry.yaml")

    def setUp(self):
        annotation, raw = normalization.read(ANNOTATION_PATH)
        request, _ = normalization.read(REQUEST_PATH)
        # Bind this synthetic request to this checkout's exact fixture bytes.
        request["annotation_sha256"] = hashlib.sha256(raw).hexdigest()
        self.manifest = normalization.build(request, annotation, raw, self.registry)
        self.lexicon, _ = lexical.read_data(LEXICON_PATH)

    @staticmethod
    def reseal_manifest(manifest):
        identity = {k: copy.deepcopy(v) for k, v in manifest.items() if k not in {"schema_version", "normalization_version_id"}}
        manifest["normalization_version_id"] = "ling-" + lexical.digest(lexical.canonical(identity))

    def test_synthetic_cli_and_output_are_deterministic_and_preserve_alternatives(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "normalization.json"
            output = Path(folder) / "interpretation.json"
            source.write_text(json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")
            checked = subprocess.run([sys.executable, "-m", "tools.lexical_interpretation", "validate", str(source), "--lexicon", str(LEXICON_PATH)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, checked.returncode, checked.stderr)
            first = lexical.build(self.manifest, self.lexicon, self.registry, self.schema)
            second = lexical.build(self.manifest, self.lexicon, self.registry, self.schema)
            self.assertEqual(first, second)
            unit = first["items"][0]
            self.assertEqual("ambiguous", unit["outcome"])
            self.assertEqual(["transliteration-a", "transliteration-b"], unit["source_value_ids"])
            self.assertEqual(["SYNTHETIC-READING-A", "SYNTHETIC-READING-B"], [r["normalized_text"] for r in unit["readings"]])
            self.assertEqual("SYNTHETIC-READING-A", unit["diplomatic_transliteration"]["values"][0]["value"])
            self.assertFalse(first["metrics"]["computed"])
            written = subprocess.run([sys.executable, "-m", "tools.lexical_interpretation", "interpret", str(source), "--lexicon", str(LEXICON_PATH), "--output", str(output)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, written.returncode, written.stderr)
            self.assertEqual(first, json.loads(output.read_text(encoding="utf-8")))

    def test_normalization_hash_drift_fails_closed(self):
        changed = copy.deepcopy(self.manifest)
        changed["annotation"]["sha256"] = "0" * 64
        errors = lexical.validate_normalization(changed, self.schema)
        self.assertTrue(any("normalization_version_id" in error for error in errors), errors)

    def test_exact_unicode_form_hash_and_normalized_value_hash_are_checked(self):
        changed_lexicon = copy.deepcopy(self.lexicon)
        changed_lexicon["entries"][0]["form"] = "SYNTHETIC-READING-Á"
        self.assertTrue(any("form_sha256" in error for error in lexical.validate_lexicon(changed_lexicon, self.schema, self.registry)))
        changed = copy.deepcopy(self.manifest)
        changed["items"][0]["values"][0]["normalized_text"] += "x"
        self.assertTrue(any("normalized text/hash mismatch" in error for error in lexical.validate_normalization(changed, self.schema)))

    def test_unknown_missing_and_unattested_are_distinct(self):
        missing = copy.deepcopy(self.manifest)
        missing["items"][0]["gold_status"] = "missing_annotation"
        self.reseal_manifest(missing)
        result = lexical.build(missing, self.lexicon, self.registry, self.schema)
        self.assertEqual("unknown", result["items"][0]["outcome"])
        unknown_form = copy.deepcopy(self.manifest)
        unknown_form["items"] = [copy.deepcopy(unknown_form["items"][0])]
        item = unknown_form["items"][0]
        item["gold_status"] = "certain"
        item["values"] = [copy.deepcopy(item["values"][1])]
        item["acceptable_reading_ids"] = [item["values"][0]["source_value_id"]]
        self.reseal_manifest(unknown_form)
        result = lexical.build(unknown_form, self.lexicon, self.registry, self.schema)
        self.assertEqual("unattested", result["items"][0]["outcome"])

    def test_conflicting_analyses_are_all_preserved_as_ambiguous(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["items"][0]["gold_status"] = "certain"
        manifest["items"][0]["values"] = [copy.deepcopy(manifest["items"][0]["values"][0])]
        manifest["items"][0]["acceptable_reading_ids"] = ["transliteration-a"]
        self.reseal_manifest(manifest)
        lexicon = copy.deepcopy(self.lexicon)
        duplicate = copy.deepcopy(lexicon["entries"][0])
        duplicate.update({"entry_id": "synthetic-analysis-b", "lemma": {"lemma_id": "synthetic-lemma-b", "value": "SYNTHETIC-LEMMA-B"}})
        lexicon["entries"].append(duplicate)
        result = lexical.build(manifest, lexicon, self.registry, self.schema)
        self.assertEqual("ambiguous", result["items"][0]["outcome"])
        self.assertEqual(["synthetic-analysis-a", "synthetic-analysis-b"], [a["entry_id"] for a in result["items"][0]["readings"][0]["analyses"]])

    def test_unsupported_morphology_is_rejected(self):
        lexicon = copy.deepcopy(self.lexicon)
        lexicon["entries"][0]["grammatical_features"]["invented_category"] = "asserted"
        self.assertTrue(lexical.validate_lexicon(lexicon, self.schema, self.registry))

    def test_invalid_source_citations_and_unverified_rights_fail_closed(self):
        lexicon = copy.deepcopy(self.lexicon)
        entry = lexicon["entries"][0]
        entry["scientific_status"] = "scholarly_candidate"
        lexicon["scientific_status"] = "scholarly_candidate"
        entry["rights"] = {"rights_class": "OPEN-BY", "intended_use": "research", "attribution": "required", "review_status": "independently_verified"}
        entry["attestations"] = [{"citation": {"citation_id": "citation-1", "bibliographic_reference": "Unverified source citation", "locator": "p. 1", "url": "https://example.org/item", "verification_evidence_url": "https://example.org/evidence", "verified_by": "reviewer", "verified_at": "2026-10-08"}, "source_identity": {"source_registry_id": "SRC-MISSING", "source_object_id": "object-1", "source_content_sha256": "a" * 64}, "historical_period": None, "context": "synthetic test", "confidence": 0.1, "uncertainty": []}]
        errors = lexical.validate_lexicon(lexicon, self.schema, self.registry)
        self.assertTrue(any("invalid source reference" in error for error in errors), errors)
        entry["attestations"][0]["source_identity"]["source_registry_id"] = "SRC-HPDB"
        entry["rights"]["review_status"] = "pending"
        errors = lexical.validate_lexicon(lexicon, self.schema, self.registry)
        self.assertTrue(any("rights are not independently cleared" in error for error in errors), errors)

    def test_unicode_normalization_collision_keeps_both_source_readings(self):
        manifest = copy.deepcopy(self.manifest)
        item = manifest["items"][0]
        item["gold_status"] = "uncertain_with_alternatives"
        one, two = copy.deepcopy(item["values"])
        one["normalized_text"] = "Å"
        two["normalized_text"] = "Å"
        for val in (one, two):
            val["normalized_sha256"] = lexical.digest(val["normalized_text"].encode("utf-8"))
        item["values"] = [one, two]
        item["acceptable_reading_ids"] = [one["source_value_id"], two["source_value_id"]]
        self.reseal_manifest(manifest)
        result = lexical.build(manifest, self.lexicon, self.registry, self.schema)
        self.assertEqual("ambiguous", result["items"][0]["outcome"])
        self.assertEqual(2, len(result["items"][0]["readings"]))
        self.assertNotEqual(result["items"][0]["readings"][0]["normalized_text"], result["items"][0]["readings"][1]["normalized_text"])


if __name__ == "__main__":
    unittest.main()
