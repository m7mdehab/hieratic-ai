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



class W28PublicPhysicalBenchmarkLineageTests(unittest.TestCase):
    """Real public source metadata; all modified split records remain synthetic."""

    @classmethod
    def setUpClass(cls) -> None:
        from eval.splits import public_benchmark_lineage as bm
        cls.bm = bm
        cls.public = bm.load_public()
        cls.index = bm.public_index()

    def _meta(self):
        return yaml.safe_load((EXAMPLES / "synthetic_metadata.yaml").read_text(encoding="utf-8"))

    def _registry(self):
        return yaml.safe_load((ROOT / "data/sources/registry.yaml").read_text(encoding="utf-8"))

    def _profiles(self):
        return yaml.safe_load((ROOT / "eval/splits/profiles.yaml").read_text(encoding="utf-8"))

    def test_266_exact_pinned_public_records_and_no_sealed_items(self):
        self.assertEqual(len(self.public),266)
        self.assertNotIn("hb-0001",{x["id"] for x in self.public})
        self.assertNotIn("hb-0002",{x["id"] for x in self.public})
        self.assertEqual(self.bm.audit_public()["unseen_sealed_records_inspected"],0)
        self.assertEqual(self.bm.audit_public()["public_records"],266)
        self.assertFalse(self.bm.audit_public()["metadata_nonmatch_is_clearance"])

    def test_tampered_original_public_metadata_blob_fails_closed(self):
        raw=self.bm.PUBLIC_METADATA.read_bytes()
        self.assertEqual(self.bm.git_blob_sha(raw),self.bm.FROZEN_REGISTER_GIT_BLOB)
        with self.assertRaisesRegex(self.bm.LineageError,"identity drift"):
            self.bm.parse_public_bytes(raw.replace(b"aku-0001",b"aku-9999",1))

    def test_source_register_with_gold_field_fails_even_if_count_266(self):
        raw=self.bm.PUBLIC_METADATA.read_bytes()
        rows=[json.loads(z) for z in raw.decode("utf-8").splitlines()]
        rows[0]["gardiner_gold"]="FORBIDDEN"
        corrupt=("\n".join(json.dumps(z) for z in rows)+"\n").encode()
        with self.assertRaisesRegex(self.bm.LineageError,"Unexpected source fields"):
            self.bm.parse_public_bytes(corrupt,require_frozen=False)

    def test_missing_public_source_rows_refused_not_assumed_cleared(self):
        raw=self.bm.PUBLIC_METADATA.read_bytes()
        with self.assertRaisesRegex(self.bm.LineageError,"266 rows"):
            self.bm.parse_public_bytes(b"\n".join(raw.splitlines()[:-1])+b"\n",require_frozen=False)

    def test_same_met_museum_physical_support_across_signs(self):
        r=self.bm.match_item({"institution":"Metropolitan Museum of Art",
                              "source_object_id":"22.3.517"})
        self.assertEqual(r["status"],"PUBLIC_PHYSICAL_SOURCE_MATCH_QUARANTINE")
        self.assertTrue({"aku-0013","aku-0041","aku-0118","aku-0125"}.issubset(set(r["public_item_ids"])))
        self.assertFalse(r["rights_clearance_granted"])

    def test_brooklyn_and_berlin_repeated_supports(self):
        brook=self.bm.match_item({"institution":"Brooklyn Museum","source_object_id":"47.218.84"})
        berlin=self.bm.match_item({"institution":"Berlin","source_object_id":"P 3057"})
        self.assertEqual(brook["public_count"],5)
        self.assertEqual(berlin["public_count"],5)

    def test_turin_roman_inventory_schemes_remain_distinct(self):
        self.assertNotEqual(self.bm.physical_key("Museo Egizio","CGT 54050"),
                            self.bm.physical_key("Museo Egizio","Cat.54050"))
        self.assertNotEqual(self.bm.physical_key("Museo Egizio","S.17507/2"),
                            self.bm.physical_key("Museo Egizio","Cat.17507"))
        hits=self.bm.match_item({"institution":"Turin, Museo Egizio","source_object_id":"CGT 54050"})
        self.assertEqual(hits["public_count"],3)

    def test_chester_beatty_papyrus_page_same_physical_group(self):
        r=self.bm.match_item({"institution":"Chester Beatty","source_object_id":"Pap XXII"})
        self.assertEqual(set(r["public_item_ids"]),{"cbl-0004","cbl-0009"})

    def test_cross_museum_duplicate_numeric_ids_not_assumed_same(self):
        self.assertNotEqual(self.bm.physical_key("Brooklyn Museum","22.3.517"),
                            self.bm.physical_key("Metropolitan Museum","22.3.517"))

    def test_unverified_cat1880_meta_nonmatch_is_not_clear(self):
        r=self.bm.match_item({"institution":"Museo Egizio","source_object_id":"Cat.1880"})
        self.assertEqual(r["status"],"UNKNOWN_NOT_CLEARED")
        self.assertEqual(r["public_item_ids"],[])
        self.assertFalse(r["independent_no_overlap_proven"])

    def test_no_institution_does_not_guess_identity_from_bare_number(self):
        r=self.bm.match_item({"institution":None,"source_object_id":"22.3.517"})
        self.assertEqual(r["status"],"UNKNOWN_NOT_CLEARED")
        self.assertIsNone(r["physical_key"])

    def test_noninventory_printed_page_number_not_physical_key(self):
        self.assertIsNone(self.bm.physical_key("Museo Egizio","Pleyte Rossi printed plate 35"))
        self.assertIsNone(self.bm.physical_key("Berlin","volume II page 3057"))

    def test_cross_provider_same_witness_is_atomic_before_split(self):
        meta=self._meta()
        a=next(x for x in meta["items"] if x["item_id"]=="item-a2")
        b=next(x for x in meta["items"] if x["item_id"]=="item-c2")
        self.assertNotEqual(a["source_id"],b["source_id"])
        a["institution"]="Metropolitan Museum of Art"
        b["institution"]="New York City, Metropolitan Museum of Art"
        a["source_object_id"]="22.3.517"
        b["source_object_id"]="22.3.517"
        components=split_system._atomic_components(meta)
        self.assertTrue(any({a["item_id"],b["item_id"]}.issubset(
            {x["item_id"] for x in component}) for component in components))

    def test_public_benchmark_source_excluded_even_when_unflagged(self):
        meta=self._meta()
        a=next(x for x in meta["items"] if x["item_id"]=="item-a2")
        a["institution"]="Metropolitan Museum of Art"
        a["source_object_id"]="22.3.517"
        a["benchmark_quarantine"]=False
        registry=self._registry();profile=self._profiles()
        manifest=split_system.generate_manifest(
            meta,profile,"PROFILE-DOC-HOLDOUT",seed=12,registry=registry
        )
        row=next(x for x in manifest["assignments"] if x["item_id"]==a["item_id"])
        self.assertEqual(row["partition"],"excluded")
        self.assertIn("known_public_benchmark_physical_support:MET:NUM:22.3.517",
                      row["exclusion_reason"])
        self.assertEqual([],split_system.validate_manifest(
            manifest,meta,profile,json.loads((ROOT/"schemas/split_manifest.schema.json").read_text()),registry))

    def test_fake_benchmark_clearance_cannot_override_exact_public_match(self):
        meta=self._meta()
        meta["synthetic_fixture"]=False
        a=next(x for x in meta["items"] if x["item_id"]=="item-a2")
        a["institution"]="Brooklyn Museum"
        a["source_object_id"]="47.218.84"
        a["benchmark_overlap_review"]={
            "status":"clear","reviewer_id":"claims-reviewer",
            "evidence_ref":"https://www.brooklynmuseum.org/collection/",
            "overlap_check_version":"manual-2026",
            "roster_version":self._profiles()["benchmark_overlap_policy"]["roster"]["version"],
            "reviewed_at":"2026-10-10T12:00:00Z"
        }
        # A self-filled review object does not override PUBLIC known source match.
        row=split_system._overlap_exclusion_reason(
            a,{x["source_id"]:x for x in self._registry()["sources"]},False
        )
        self.assertIn("known_public_benchmark_physical_support",row)

    def test_forged_assignment_to_train_detected_on_public_match(self):
        meta=self._meta();a=next(x for x in meta["items"] if x["item_id"]=="item-a2")
        a["institution"]="Brooklyn Museum";a["source_object_id"]="47.218.84"
        registry=self._registry();profile=self._profiles()
        result=split_system.generate_manifest(meta,profile,"PROFILE-DOC-HOLDOUT",seed=12,registry=registry)
        row=next(x for x in result["assignments"] if x["item_id"]==a["item_id"])
        row["partition"]="train";row["exclusion_reason"]=None
        errs=split_system.validate_manifest(
            result,meta,profile,json.loads((ROOT/"schemas/split_manifest.schema.json").read_text()),registry
        )
        self.assertTrue(any("high-risk benchmark-overlap" in x for x in errs),errs)

    def test_cross_collection_nonmatch_never_gives_rights_or_sealed_clearance(self):
        result=self.bm.match_item({"institution":"Metropolitan Museum of Art",
                                    "source_object_id":"09.184.1"})
        self.assertEqual(result["status"],"UNKNOWN_NOT_CLEARED")
        self.assertFalse(result["independent_no_overlap_proven"])
        self.assertFalse(result["sealed_test_items_inspected"])

    def test_actual_pinned_public_inventory_diagnostic_is_complete(self):
        audit=self.bm.audit_public()
        self.assertEqual(audit["recognized_public_item_count"],135)
        self.assertEqual(audit["recognized_physical_inventory_groups"],90)
        self.assertEqual(audit["repeated_public_groups"],20)
        self.assertEqual(audit["unrecognized_public_rows"],131)
        self.assertEqual(audit["cross_family_public_groups"],[])
        self.assertEqual(audit["group_sizes"],{1:70,2:9,3:1,4:6,5:4})

    def test_externally_tampered_manifest_cannot_split_same_publicly_unlisted_museum_object(self):
        meta=self._meta()
        a=next(x for x in meta["items"] if x["item_id"]=="item-a2")
        b=next(x for x in meta["items"] if x["item_id"]=="item-a3")
        a["institution"]=b["institution"]="Metropolitan Museum of Art"
        a["source_object_id"]=b["source_object_id"]="22.3.599"
        profile=self._profiles(); registry=self._registry()
        manifest=split_system.generate_manifest(
            meta,profile,"PROFILE-DOC-HOLDOUT",seed=12,registry=registry
        )
        assigned={row["item_id"]:row for row in manifest["assignments"]}
        self.assertEqual(assigned[a["item_id"]]["partition"],
                         assigned[b["item_id"]]["partition"])
        assigned[a["item_id"]]["partition"]="train"
        assigned[b["item_id"]]["partition"]="test"
        errors=split_system.validate_manifest(
            manifest,meta,profile,
            json.loads((ROOT/"schemas/split_manifest.schema.json").read_text()),registry
        )
        self.assertTrue(any("physical accession MET:NUM:22.3.599 overlaps partitions" in e for e in errors),errors)

    def test_real_public_census_group_counts_no_unfrozen_source(self):
        audit=self.bm.audit_public()
        self.assertEqual(audit["family_counts"],
                         {"aku":150,"cbl":16,"met":37,"wm":61,"ypm":2})
        self.assertEqual(audit["public_records"],
                         audit["recognized_public_item_count"]+audit["unrecognized_public_rows"])
        self.assertEqual(audit["original_image_hash_comparison_performed"],False)


if __name__ == "__main__":
    unittest.main()
