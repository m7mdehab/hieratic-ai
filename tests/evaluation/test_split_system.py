from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import yaml

from tools import split_system


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "eval/splits/examples"


class SplitSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metadata = yaml.safe_load((EXAMPLES / "synthetic_metadata.yaml").read_text(encoding="utf-8"))
        self.profiles = yaml.safe_load((ROOT / "eval/splits/profiles.yaml").read_text(encoding="utf-8"))
        self.schema = json.loads((ROOT / "schemas/split_manifest.schema.json").read_text(encoding="utf-8"))
        self.registry = yaml.safe_load((ROOT / "data/sources/registry.yaml").read_text(encoding="utf-8"))

    def generate(self, profile_id="PROFILE-DOC-HOLDOUT", holdout_values=None, metadata=None, registry=None):
        return split_system.generate_manifest(
            copy.deepcopy(self.metadata if metadata is None else metadata),
            self.profiles,
            profile_id,
            seed=41,
            holdout_values=holdout_values,
            generated_at="2026-10-08T12:00:00Z",
            registry=copy.deepcopy(self.registry if registry is None else registry),
        )

    def validate(self, manifest, metadata=None, registry=None):
        return split_system.validate_manifest(
            copy.deepcopy(manifest),
            copy.deepcopy(self.metadata if metadata is None else metadata),
            self.profiles,
            self.schema,
            copy.deepcopy(self.registry if registry is None else registry),
        )

    def row(self, manifest, item_id):
        return next(row for row in manifest["assignments"] if row["item_id"] == item_id)

    def test_generation_is_deterministic_for_same_metadata_profile_and_seed(self) -> None:
        first = self.generate()
        second = self.generate()
        self.assertEqual(
            [(row["item_id"], row["partition"]) for row in first["assignments"]],
            [(row["item_id"], row["partition"]) for row in second["assignments"]],
        )
        self.assertEqual(first["source_metadata_sha256"], second["source_metadata_sha256"])
        self.assertEqual([], self.validate(first))

    def test_document_leakage_is_detected(self) -> None:
        manifest = self.generate()
        first = self.row(manifest, "item-a1-page1")
        second = self.row(manifest, "item-a1-page2")
        second["partition"] = "test" if first["partition"] != "test" else "train"
        errors = self.validate(manifest)
        self.assertTrue(any("document_id doc-a1 overlaps partitions" in error for error in errors), errors)

    def test_page_leakage_is_detected(self) -> None:
        metadata = copy.deepcopy(self.metadata)
        next(item for item in metadata["items"] if item["item_id"] == "item-a2")["page_id"] = "page-a1-1"
        manifest = self.generate(metadata=metadata)
        first = self.row(manifest, "item-a1-page1")
        second = self.row(manifest, "item-a2")
        second["partition"] = "test" if first["partition"] != "test" else "train"
        errors = self.validate(manifest, metadata)
        self.assertTrue(any("page page-a1-1 overlaps partitions" in error for error in errors), errors)

    def test_scribe_holdout_and_unknown_scribe_policy(self) -> None:
        manifest = self.generate("PROFILE-SCRIBE-HOLDOUT", ["scribe-b"])
        self.assertEqual("test", self.row(manifest, "item-a3")["partition"])
        self.assertEqual("test", self.row(manifest, "item-a4")["partition"])
        self.assertEqual("train", self.row(manifest, "item-a5")["partition"])
        self.assertFalse(any(row["partition"] == "train" and row["scribe_group"] == "scribe-b" for row in manifest["assignments"]))
        self.assertEqual([], self.validate(manifest))

    def test_source_and_period_holdout_profiles_are_defined_and_enforced(self) -> None:
        source_manifest = self.generate("PROFILE-SOURCE-HOLDOUT", ["SRC-DDD"])
        self.assertTrue(all(row["partition"] == "test" for row in source_manifest["assignments"] if row["source_id"] == "SRC-DDD"))
        self.assertEqual([], self.validate(source_manifest))
        period_manifest = self.generate("PROFILE-PERIOD-HOLDOUT", ["late"])
        self.assertTrue(all(row["partition"] == "test" for row in period_manifest["assignments"] if row["period"] == "late"))
        self.assertNotEqual("test", self.row(period_manifest, "item-a5")["partition"])
        self.assertEqual([], self.validate(period_manifest))

    def test_known_benchmark_item_is_excluded_even_without_flag(self) -> None:
        manifest = self.generate()
        row = self.row(manifest, "hb-0001")
        self.assertEqual("excluded", row["partition"])
        self.assertTrue(row["exclusion_reason"])
        self.assertEqual([], self.validate(manifest))

    def test_unflagged_high_risk_aku_item_without_clearance_is_excluded(self) -> None:
        metadata = copy.deepcopy(self.metadata)
        item = next(item for item in metadata["items"] if item["item_id"] == "item-c2")
        item["benchmark_quarantine"] = False
        item["benchmark_overlap_review"] = {
            "status": "not_assessed",
            "reviewer_id": None,
            "evidence_ref": None,
            "overlap_check_version": None,
            "roster_version": None,
            "reviewed_at": None,
        }
        manifest = self.generate(metadata=metadata)
        row = self.row(manifest, "item-c2")
        self.assertEqual("excluded", row["partition"])
        self.assertIn("high_risk_benchmark_overlap_unreviewed:SRC-AKU-PAL", row["exclusion_reason"])
        self.assertEqual([], self.validate(manifest, metadata))
        forged = copy.deepcopy(manifest)
        self.row(forged, "item-c2")["partition"] = "train"
        errors = self.validate(forged, metadata)
        self.assertTrue(any("high-risk benchmark-overlap item must be excluded" in error for error in errors), errors)

    def test_confirmed_benchmark_match_and_near_duplicate_are_excluded(self) -> None:
        metadata = copy.deepcopy(self.metadata)
        matched_item = next(item for item in metadata["items"] if item["item_id"] == "item-c2")
        matched_item["benchmark_overlap_review"] = {
            "status": "synthetic_match",
            "reviewer_id": "synthetic-reviewer-002",
            "evidence_ref": "synthetic:confirmed-match-c2",
            "overlap_check_version": "synthetic-overlap-scan/1",
            "roster_version": "synthetic:hieraticbench-fixture-roster/1",
            "reviewed_at": "2026-10-08T10:00:00Z",
        }
        metadata["near_duplicate_candidates"].append({
            "left_item_id": "item-c3",
            "right_item_id": "hb-0001",
            "method": "manual",
            "similarity": None,
            "review_status": "same_content",
            "reviewer_id": "synthetic-reviewer-003",
            "evidence_ref": "synthetic:confirmed-near-duplicate-c3-hb1",
        })
        manifest = self.generate(metadata=metadata)
        self.assertEqual("excluded", self.row(manifest, "item-c2")["partition"])
        self.assertIn("benchmark_overlap_confirmed_match", self.row(manifest, "item-c2")["exclusion_reason"])
        self.assertEqual("excluded", self.row(manifest, "item-c3")["partition"])
        self.assertIn("linked_to_quarantined_benchmark", self.row(manifest, "item-c3")["exclusion_reason"])
        self.assertEqual([], self.validate(manifest, metadata))

    def test_versioned_synthetic_clearance_keeps_distinct_candidate_eligible(self) -> None:
        manifest = self.generate()
        row = self.row(manifest, "item-c2")
        self.assertIn(row["partition"], {"train", "dev", "test"})
        review = row["benchmark_overlap_review"]
        self.assertEqual("synthetic_cleared", review["status"])
        self.assertEqual("synthetic-reviewer-001", review["reviewer_id"])
        self.assertTrue(review["evidence_ref"].startswith("synthetic:"))
        self.assertTrue(review["overlap_check_version"])
        self.assertEqual([], self.validate(manifest))

    def test_overlap_clearance_requires_reviewer_evidence_and_versions(self) -> None:
        for field in ("reviewer_id", "evidence_ref", "overlap_check_version", "roster_version", "reviewed_at"):
            with self.subTest(field=field):
                metadata = copy.deepcopy(self.metadata)
                review = next(item for item in metadata["items"] if item["item_id"] == "item-c2")["benchmark_overlap_review"]
                review[field] = None
                with self.assertRaisesRegex(split_system.SplitInputError, "resolved benchmark-overlap review requires reviewer, evidence, check version, and roster version"):
                    self.generate(metadata=metadata)

    def test_high_risk_source_classification_is_derived_from_data001(self) -> None:
        registry = copy.deepcopy(self.registry)
        hpdb = next(source for source in registry["sources"] if source["source_id"] == "SRC-HPDB")
        hpdb["benchmark_overlap_risk"] = "high"
        manifest = self.generate(registry=registry)
        row = self.row(manifest, "item-a2")
        self.assertEqual("excluded", row["partition"])
        self.assertIn("high_risk_benchmark_overlap_unreviewed:SRC-HPDB", row["exclusion_reason"])
        self.assertEqual([], self.validate(manifest, registry=registry))

    def test_exact_hash_overlap_is_detected(self) -> None:
        metadata = copy.deepcopy(self.metadata)
        shared_hash = "a" * 64
        for item_id in ("item-a2", "item-b2"):
            next(item for item in metadata["items"] if item["item_id"] == item_id)["image_sha256"] = shared_hash
        manifest = self.generate(metadata=metadata)
        left = self.row(manifest, "item-a2")
        right = self.row(manifest, "item-b2")
        right["partition"] = "test" if left["partition"] != "test" else "train"
        errors = self.validate(manifest, metadata)
        self.assertTrue(any(f"exact hash {shared_hash} overlaps partitions" in error for error in errors), errors)

    def test_source_object_lineage_overlap_is_detected(self) -> None:
        metadata = copy.deepcopy(self.metadata)
        item = next(item for item in metadata["items"] if item["item_id"] == "item-b2")
        item["source_id"] = "SRC-HPDB"
        item["source_object_id"] = "object-a2"
        manifest = self.generate(metadata=metadata)
        self.row(manifest, "item-b2")["partition"] = "test" if self.row(manifest, "item-a2")["partition"] != "test" else "train"
        errors = self.validate(manifest, metadata)
        self.assertTrue(any("source_object_id SRC-HPDB::object-a2 overlaps partitions" in error for error in errors), errors)

    def test_duplicate_item_ids_fail_input_validation(self) -> None:
        metadata = copy.deepcopy(self.metadata)
        metadata["items"].append(copy.deepcopy(metadata["items"][0]))
        with self.assertRaisesRegex(split_system.SplitInputError, "duplicate item_id"):
            self.generate(metadata=metadata)

    def test_document_holdout_stratifies_sources_when_sampled(self) -> None:
        manifest = self.generate()
        rows = [row for row in manifest["assignments"] if row["partition"] != "excluded"]
        for source_id in ("SRC-HPDB", "SRC-DDD", "SRC-AKU-PAL"):
            partitions = {row["partition"] for row in rows if row["source_id"] == source_id}
            self.assertEqual({"train", "dev", "test"}, partitions)

    def test_missing_scribe_and_period_metadata_are_explicit_and_safe(self) -> None:
        scribe_manifest = self.generate("PROFILE-SCRIBE-HOLDOUT", ["scribe-b"])
        self.assertEqual("train", self.row(scribe_manifest, "item-a5")["partition"])
        period_manifest = self.generate("PROFILE-PERIOD-HOLDOUT", ["late"])
        self.assertIn(self.row(period_manifest, "item-a5")["partition"], {"train", "dev"})
        self.assertTrue(any("UNKNOWN" in warning or "low_sample_stratum" in warning for warning in period_manifest["warnings"]) or period_manifest["statistics"]["dimension_counts"]["period"]["UNKNOWN"])

    def test_near_duplicate_queue_and_cross_partition_failure_policy(self) -> None:
        manifest = self.generate()
        self.assertEqual("pending", manifest["near_duplicate_review_queue"][0]["review_status"])
        self.assertTrue(any("near_duplicate_review_pending" in warning for warning in manifest["warnings"]))
        self.assertEqual([], self.validate(manifest))

        metadata = copy.deepcopy(self.metadata)
        base = self.generate()
        train_item = next(row["item_id"] for row in base["assignments"] if row["partition"] == "train")
        test_item = next(row["item_id"] for row in base["assignments"] if row["partition"] == "test")
        metadata["near_duplicate_candidates"].append({
            "left_item_id": train_item,
            "right_item_id": test_item,
            "method": "embedding_similarity",
            "similarity": 0.95,
            "review_status": "pending",
            "reviewer_id": None,
            "evidence_ref": "synthetic-review-pair",
        })
        with self.assertRaisesRegex(split_system.SplitInputError, "pending near-duplicate review must be resolved"):
            self.generate(metadata=metadata)

    def test_confirmed_near_duplicate_pair_is_grouped_and_requires_review_evidence(self) -> None:
        metadata = copy.deepcopy(self.metadata)
        metadata["near_duplicate_candidates"].append({
            "left_item_id": "item-a2",
            "right_item_id": "item-b2",
            "method": "manual",
            "similarity": None,
            "review_status": "same_content",
            "reviewer_id": "synthetic-reviewer",
            "evidence_ref": "synthetic-review-record",
        })
        manifest = self.generate(metadata=metadata)
        self.assertEqual(self.row(manifest, "item-a2")["partition"], self.row(manifest, "item-b2")["partition"])
        self.assertEqual([], self.validate(manifest, metadata))
        metadata["near_duplicate_candidates"][-1]["evidence_ref"] = None
        with self.assertRaisesRegex(split_system.SplitInputError, "requires reviewer_id and evidence_ref"):
            self.generate(metadata=metadata)

    def test_input_version_mismatch_and_exclusion_reason_are_detected(self) -> None:
        manifest = self.generate()
        manifest["source_metadata_version"] = "stale-version"
        errors = self.validate(manifest)
        self.assertTrue(any("source_metadata_version does not match" in error for error in errors), errors)
        manifest = self.generate()
        self.row(manifest, "hb-0001")["exclusion_reason"] = None
        errors = self.validate(manifest)
        self.assertTrue(any("excluded item requires an exclusion reason" in error for error in errors), errors)

    def test_sealed_test_profile_is_policy_only(self) -> None:
        with self.assertRaisesRegex(split_system.SplitInputError, "policy profile"):
            self.generate("PROFILE-SEALED-TEST")

    def test_no_external_images_or_benchmark_answers_are_in_fixtures(self) -> None:
        for path in EXAMPLES.rglob("*"):
            if path.is_file():
                self.assertIn(path.suffix.lower(), {".yaml", ".yml", ".json", ".md"}, str(path))


if __name__ == "__main__":
    unittest.main()
