from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import yaml

from tools import acquisition


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "data" / "acquisition" / "examples"


class AcquisitionManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = yaml.safe_load((ROOT / "data/sources/registry.yaml").read_text(encoding="utf-8"))
        self.schema = json.loads((ROOT / "schemas/acquisition_manifest.schema.json").read_text(encoding="utf-8"))

    def load_example(self, name: str) -> dict:
        return yaml.safe_load((EXAMPLES / name).read_text(encoding="utf-8"))

    def check(self, manifest: dict, registry: dict | None = None):
        return acquisition.validate_data(copy.deepcopy(manifest), copy.deepcopy(registry or self.registry), self.schema)

    def synthetic_reviewed_aku_manifest(self) -> dict:
        manifest = self.load_example("aku-pal-conditional.yaml")
        item = manifest["items"][0]
        item["is_synthetic_fixture"] = True
        item["review_conditions"] = [
            {"condition_id": condition_id, "satisfied": True, "evidence_urls": ["https://example.invalid/mock-review"], "notes": "synthetic fixture evidence"}
            for condition_id in sorted(
                set(next(source for source in self.registry["sources"] if source["source_id"] == "SRC-AKU-PAL")["automated_access_constraints"])
                | set(next(source for source in self.registry["sources"] if source["source_id"] == "SRC-AKU-PAL")["project_review_markers"])
            )
        ]
        item["item_rights_review"] = {
            "item_url": "synthetic://aku-pal/item-001",
            "license_identifier": "SYNTHETIC-LICENSE-REVIEWED",
            "rightsholder": "Synthetic rightsholder fixture",
            "reviewer_id": "synthetic-reviewer-001",
            "approval_status": "approved",
            "evidence_ref": "synthetic:rights-review-001",
            "reviewed_at": "2026-10-08T10:00:00Z",
        }
        item["benchmark_overlap_review"] = {
            "status": "clear",
            "reviewer_id": "synthetic-reviewer-001",
            "evidence_ref": "synthetic:overlap-review-001",
            "overlap_check_version": "synthetic-overlap-check/1",
            "reviewed_at": "2026-10-08T10:00:00Z",
        }
        return manifest

    def test_canonical_example_manifests_validate_or_fail_as_documented(self) -> None:
        allowed, plan = self.check(self.load_example("hieraticbench-evaluation.yaml"))
        self.assertEqual([], allowed)
        self.assertEqual("ALLOWED", plan[0]["decision"])
        reference, _ = self.check(self.load_example("hpdb-reference.yaml"))
        self.assertEqual([], reference)
        for name in ("hieraticbench-training-blocked.yaml", "papyrus-blocked.yaml", "aku-pal-conditional.yaml"):
            errors, plan = self.check(self.load_example(name))
            self.assertTrue(errors, name)
            self.assertEqual("REFUSED", plan[0]["decision"], name)

    def test_unknown_source_id_fails(self) -> None:
        manifest = self.load_example("hpdb-reference.yaml")
        manifest["items"][0]["source_id"] = "SRC-UNKNOWN"
        errors, _ = self.check(manifest)
        self.assertTrue(any("unknown source_id SRC-UNKNOWN" in error for error in errors), errors)

    def test_missing_source_id_fails_schema_validation(self) -> None:
        manifest = self.load_example("hpdb-reference.yaml")
        del manifest["items"][0]["source_id"]
        errors, _ = self.check(manifest)
        self.assertTrue(any("source_id" in error and "required" in error for error in errors), errors)

    def test_hieraticbench_training_fails_even_if_manifest_snapshot_claims_allowed(self) -> None:
        errors, _ = self.check(self.load_example("hieraticbench-training-blocked.yaml"))
        self.assertTrue(any("EVALUATION-ONLY" in error for error in errors), errors)
        self.assertTrue(any("benchmark-quarantined" in error for error in errors), errors)

    def test_tla_training_and_bulk_mode_fail(self) -> None:
        manifest = self.load_example("papyrus-blocked.yaml")
        item = manifest["items"][0]
        item.update({
            "source_id": "SRC-TLA",
            "canonical_object_url": "https://thesaurus-linguae-aegyptiae.de/info/text-corpus?lang=en",
            "intended_use": "training",
            "source_rights_snapshot": {"rights_class": "RESTRICTED", "use_decision": "prohibited"},
            "required_attribution": "Follow the official license page and source-specific attribution for any individually permitted academic quotation",
            "benchmark_quarantine": False,
            "benchmark_overlap_risk": "unknown",
            "provenance_urls": ["https://thesaurus-linguae-aegyptiae.de/info/licenses"],
            "evidence_urls": ["https://thesaurus-linguae-aegyptiae.de/info/licenses"],
            "acquisition_mode": "api",
        })
        errors, _ = self.check(manifest)
        self.assertTrue(any("refuses training use" in error for error in errors), errors)

    def test_not_approved_sources_fail_closed(self) -> None:
        manifest = self.load_example("papyrus-blocked.yaml")
        errors, _ = self.check(manifest)
        self.assertTrue(any("not_approved" in error for error in errors), errors)
        for source_id in ("SRC-ISUT", "SRC-HIERATICAI"):
            with self.subTest(source_id=source_id):
                isut_registry = copy.deepcopy(self.registry)
                source = next(source for source in isut_registry["sources"] if source["source_id"] == source_id)
                candidate = copy.deepcopy(manifest)
                candidate["items"][0].update({
                    "source_id": source_id,
                    "canonical_object_url": source["canonical_url"],
                    "source_rights_snapshot": {"rights_class": source["rights_class"], "use_decision": source["training_use"]},
                    "required_attribution": source["attribution_requirements"],
                    "benchmark_quarantine": source["benchmark_quarantine"],
                    "benchmark_overlap_risk": source["benchmark_overlap_risk"],
                    "provenance_urls": [source["canonical_url"]],
                    "evidence_urls": [source["canonical_url"]],
                })
                errors, _ = self.check(candidate, isut_registry)
                self.assertTrue(any("not_approved" in error for error in errors), errors)

    def test_conditional_aku_pal_requires_item_review_conditions_and_evidence(self) -> None:
        errors, _ = self.check(self.load_example("aku-pal-conditional.yaml"))
        self.assertTrue(any("lacks explicit conditions" in error for error in errors), errors)
        self.assertTrue(any("item-specific license" in error for error in errors), errors)
        self.assertTrue(any("benchmark-overlap" in error for error in errors), errors)

    def test_synthetic_reviewed_aku_is_only_a_plan_and_never_admitted(self) -> None:
        manifest = self.synthetic_reviewed_aku_manifest()
        registry = copy.deepcopy(self.registry)
        aku = next(source for source in registry["sources"] if source["source_id"] == "SRC-AKU-PAL")
        errors, plans = self.check(manifest, registry)
        self.assertEqual([], errors)
        self.assertEqual("CONDITIONAL PLAN READY", plans[0]["decision"])
        self.assertEqual("NOT ADMITTED — synthetic fixture only", plans[0]["admission_status"])
        self.assertNotIn("ALLOWED", plans[0]["decision"])
        changed_registry = copy.deepcopy(registry)
        changed_aku = next(source for source in changed_registry["sources"] if source["source_id"] == "SRC-AKU-PAL")
        changed_aku["training_use"] = "prohibited"
        errors, plans = self.check(manifest, changed_registry)
        self.assertTrue(any("refuses training use" in error for error in errors), errors)
        self.assertEqual("REFUSED", plans[0]["decision"])

    def test_placeholder_evidence_cannot_satisfy_real_item_review(self) -> None:
        manifest = self.synthetic_reviewed_aku_manifest()
        item = manifest["items"][0]
        item["is_synthetic_fixture"] = False
        item["item_rights_review"].update({
            "item_url": "https://aku-pal.uni-mainz.de/hieratogram/123",
            "evidence_ref": "https://example.invalid/review/rights",
        })
        item["benchmark_overlap_review"]["evidence_ref"] = "https://example.invalid/review/overlap"
        errors, plans = self.check(manifest)
        self.assertTrue(any("placeholder evidence" in error for error in errors), errors)
        self.assertEqual("REFUSED", plans[0]["decision"])

    def test_arbitrary_non_url_review_evidence_cannot_approve_real_item(self) -> None:
        for evidence_ref in ("reviewed by me", "artifact:unclear", "https://", "https://example.invalid/review", "https://github.com/"):
            with self.subTest(evidence_ref=evidence_ref):
                manifest = self.synthetic_reviewed_aku_manifest()
                item = manifest["items"][0]
                item["is_synthetic_fixture"] = False
                item["item_rights_review"].update({
                    "item_url": "https://aku-pal.uni-mainz.de/hieratogram/123",
                    "evidence_ref": evidence_ref,
                })
                item["benchmark_overlap_review"]["evidence_ref"] = evidence_ref
                errors, plans = self.check(manifest)
                self.assertTrue(any("non-placeholder evidence reference" in error for error in errors), errors)
                self.assertEqual("REFUSED", plans[0]["decision"])

    def test_missing_accountable_rights_reviewer_is_refused(self) -> None:
        manifest = self.synthetic_reviewed_aku_manifest()
        manifest["items"][0]["item_rights_review"]["reviewer_id"] = None
        errors, plans = self.check(manifest)
        self.assertTrue(any("item rights review requires an accountable reviewer" in error for error in errors), errors)
        self.assertEqual("REFUSED", plans[0]["decision"])

    def test_unknown_item_license_or_rightsholder_is_refused(self) -> None:
        for field in ("license_identifier", "rightsholder"):
            with self.subTest(field=field):
                manifest = self.synthetic_reviewed_aku_manifest()
                manifest["items"][0]["item_rights_review"][field] = "unknown"
                errors, plans = self.check(manifest)
                self.assertTrue(any("requires a known item-specific license" in error or "requires an identified rightsholder" in error for error in errors), errors)
                self.assertEqual("REFUSED", plans[0]["decision"])

    def test_missing_clear_benchmark_review_is_refused(self) -> None:
        manifest = self.synthetic_reviewed_aku_manifest()
        manifest["items"][0]["benchmark_overlap_review"]["status"] = "not_assessed"
        errors, plans = self.check(manifest)
        self.assertTrue(any("requires a clear benchmark-overlap assessment" in error for error in errors), errors)
        self.assertEqual("REFUSED", plans[0]["decision"])

    def test_complete_download_requires_actual_sha256_and_retrieval_time(self) -> None:
        manifest = self.load_example("hieraticbench-evaluation.yaml")
        item = manifest["items"][0]
        item.update({"acquisition_mode": "direct_download", "acquisition_status": "complete", "transformation_status": "original_bytes_only"})
        errors, _ = self.check(manifest)
        self.assertTrue(any("requires actual_sha256" in error for error in errors), errors)
        self.assertTrue(any("requires retrieval_timestamp" in error for error in errors), errors)

    def test_complete_download_with_hash_and_timestamp_passes(self) -> None:
        manifest = self.load_example("hieraticbench-evaluation.yaml")
        item = manifest["items"][0]
        item.update({
            "acquisition_mode": "direct_download",
            "acquisition_status": "complete",
            "transformation_status": "original_bytes_only",
            "actual_sha256": "a" * 64,
            "retrieval_timestamp": "2026-10-08T10:00:00Z",
        })
        errors, _ = self.check(manifest)
        self.assertEqual([], errors)

    def test_redistribution_needs_registry_rights_evidence_in_manifest(self) -> None:
        manifest = self.load_example("hpdb-reference.yaml")
        item = manifest["items"][0]
        item["redistribution_requested"] = True
        errors, _ = self.check(manifest)
        self.assertTrue(any("conditional use or redistribution lacks explicit conditions" in error for error in errors), errors)
        registry = copy.deepcopy(self.registry)
        hpdb = next(source for source in registry["sources"] if source["source_id"] == "SRC-HPDB")
        hpdb["rights_evidence_urls"] = []
        errors, _ = self.check(manifest, registry)
        self.assertTrue(any("no rights evidence for requested redistribution" in error for error in errors), errors)

    def test_logical_fingerprint_is_stable_and_ignores_retrieval_history(self) -> None:
        item = self.load_example("hpdb-reference.yaml")["items"][0]
        original = acquisition.logical_fingerprint(item)
        updated = copy.deepcopy(item)
        updated["actual_sha256"] = "a" * 64
        updated["retrieval_events"] = [{"retrieved_at": "2026-10-08T10:00:00Z", "actual_sha256": "a" * 64, "http_etag": "etag", "http_last_modified": None}]
        self.assertEqual(original, acquisition.logical_fingerprint(updated))
        changed_identity = copy.deepcopy(item)
        changed_identity["source_object_id"] = "ANOTHER-SYNTHETIC-ITEM"
        self.assertNotEqual(original, acquisition.logical_fingerprint(changed_identity))

    def test_metadata_reference_does_not_make_network_calls_or_acquire_assets(self) -> None:
        errors, plans = self.check(self.load_example("hpdb-reference.yaml"))
        self.assertEqual([], errors)
        self.assertEqual("metadata_only", plans[0]["item"]["acquisition_mode"])
        self.assertEqual("ALLOWED", plans[0]["decision"])

    def test_examples_contain_only_repository_authored_metadata(self) -> None:
        allowed_suffixes = {".yaml", ".yml", ".md"}
        for path in (ROOT / "data/acquisition").rglob("*"):
            if path.is_file():
                self.assertIn(path.suffix.lower(), allowed_suffixes, f"unexpected non-metadata file: {path}")


if __name__ == "__main__":
    unittest.main()
