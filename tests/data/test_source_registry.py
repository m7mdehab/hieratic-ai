from __future__ import annotations

import copy
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from tools import source_registry


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "data" / "sources" / "registry.yaml"
SCHEMA_PATH = ROOT / "schemas" / "data_sources.schema.json"


class SourceRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def errors(self, registry=None) -> list[str]:
        return source_registry.validate_registry_data(copy.deepcopy(self.registry if registry is None else registry), self.schema)

    def record(self, source_id: str, registry=None) -> dict:
        data = self.registry if registry is None else registry
        return next(source for source in data["sources"] if source["source_id"] == source_id)

    def test_canonical_registry_validates(self) -> None:
        errors, registry = source_registry.validate_files(REGISTRY_PATH, SCHEMA_PATH)
        self.assertEqual([], errors)
        self.assertEqual(8, len(registry["sources"]))

    def test_duplicate_source_ids_fail(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["sources"].append(copy.deepcopy(registry["sources"][0]))
        self.assertTrue(any("Duplicate source_id SRC-HIERATICBENCH" in error for error in self.errors(registry)), self.errors(registry))

    def test_missing_required_field_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        del self.record("SRC-DDD", registry)["attribution_requirements"]
        self.assertTrue(any("attribution_requirements" in error for error in self.errors(registry)))

    def test_invalid_rights_class_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        self.record("SRC-DDD", registry)["rights_class"] = "OPENISH"
        self.assertTrue(any("rights_class" in error for error in self.errors(registry)))

    def test_malformed_url_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        self.record("SRC-DDD", registry)["canonical_url"] = "not a URL"
        self.assertTrue(any("canonical_url" in error for error in self.errors(registry)))

    def test_evaluation_only_training_or_development_contradiction_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        self.record("SRC-HIERATICBENCH", registry)["training_use"] = "conditional"
        errors = self.errors(registry)
        self.assertTrue(any("EVALUATION-ONLY requires training and development" in error for error in errors), errors)

    def test_verified_primary_without_evidence_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        self.record("SRC-HPDB", registry)["evidence_urls"] = []
        errors = self.errors(registry)
        self.assertTrue(any("evidence_urls" in error and "non-empty" in error for error in errors), errors)

    def test_redistribution_without_rights_evidence_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        record = self.record("SRC-HPDB", registry)
        record["rights_evidence_urls"] = []
        errors = self.errors(registry)
        self.assertTrue(any("redistribution requires rights evidence URLs" in error for error in errors), errors)

    def test_hieraticbench_quarantine_is_enforced(self) -> None:
        registry = copy.deepcopy(self.registry)
        self.record("SRC-HIERATICBENCH", registry)["benchmark_quarantine"] = False
        errors = self.errors(registry)
        self.assertTrue(any("SRC-HIERATICBENCH: benchmark_quarantine must be true" in error for error in errors), errors)

    def test_tla_bulk_scraping_is_forbidden(self) -> None:
        registry = copy.deepcopy(self.registry)
        record = self.record("SRC-TLA", registry)
        record["automated_access_constraints"].remove("no_bulk_scraping")
        errors = self.errors(registry)
        self.assertTrue(any("SRC-TLA: missing automated access constraints" in error for error in errors), errors)

    def test_ddd_noncommercial_and_per_item_conditions_are_recorded(self) -> None:
        ddd = self.record("SRC-DDD")
        self.assertEqual("NONCOMMERCIAL", ddd["rights_class"])
        self.assertIn("PER-ITEM", ddd["project_review_markers"])
        self.assertEqual("prohibited", ddd["commercial_use"])

    def test_registry_directory_contains_metadata_only(self) -> None:
        registry_dir = ROOT / "data" / "sources"
        allowed_suffixes = {".md", ".yaml", ".yml", ".json"}
        for path in registry_dir.rglob("*"):
            if path.is_dir():
                self.assertNotIn(path.name.lower(), {"raw", "images", "assets", "corpora", "checkpoints"})
            else:
                self.assertIn(path.suffix.lower(), allowed_suffixes, f"Unexpected non-metadata file: {path}")

    def test_invalid_fixture_file_returns_failure_without_modifying_canonical_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            registry_path = Path(temporary) / "registry.yaml"
            invalid = copy.deepcopy(self.registry)
            self.record("SRC-DDD", invalid)["rights_class"] = "NOT-A-RIGHTS-CLASS"
            registry_path.write_text(yaml.safe_dump(invalid, sort_keys=False), encoding="utf-8")
            before = REGISTRY_PATH.read_bytes()
            with self.assertRaises(source_registry.SourceRegistryError):
                source_registry.load_yaml(Path(temporary) / "missing.yaml")
            with contextlib.redirect_stderr(io.StringIO()):
                result = source_registry.main(["validate", "--registry", str(registry_path), "--schema", str(SCHEMA_PATH)])
            self.assertEqual(1, result)
            self.assertEqual(before, REGISTRY_PATH.read_bytes())


if __name__ == "__main__":
    unittest.main()
