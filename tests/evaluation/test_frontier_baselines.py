"""EVAL-003: wholly synthetic, offline baseline provenance and capture tests."""
from __future__ import annotations

import copy
from pathlib import Path
import json
import tempfile
import unittest

from eval.baselines import baselinectl as b


class FrontierBaselineContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.planning=b.load_data(b.DEFAULT_SUITE)
        cls.schema=json.loads(b.SUITE_SCHEMA.read_text(encoding="utf-8"))

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.items=self.root/"synthetic-items.jsonl"
        self.capture=self.root/"private-synthetic-capture.jsonl"
        self.records=[{"item_id":"SYNTHETIC-1","rung":"identify","split":"public"},
                      {"item_id":"SYNTHETIC-2","rung":"signs","split":"public"}]
        self.items.write_text("".join(json.dumps(x)+"\n" for x in self.records),encoding="utf-8")
        self.suite=copy.deepcopy(self.planning)
        self.suite["status"]="execution_ready"
        self.suite["protocol"]["samples_per_item"]=2
        self.suite["official_benchmark"]["item_manifest_sha256"]=b.digest(self.items)
        self.suite["official_prompts"]["exact_prompt_bundle_sha256"]="f"*64
        for k in self.suite["execution_gate"]:
            self.suite["execution_gate"][k]=True if k!="max_total_spend_usd" else 1.0
        for model in self.suite["models"]:
            model["provider_model_id"]=f"synthetic-{model['key']}"
            model["effort"]="synthetic-controlled"
            model["api_route"]="synthetic-offline"
        self.model=self.suite["models"][0]
        self.raw=[]
        for row in self.records:
            for sample in range(2):
                self.raw.append({
                    "item_id":row["item_id"],"rung":row["rung"],"sample_index":sample,
                    "provider_model_id":self.model["provider_model_id"],
                    "prompt_sha256":"f"*64,
                    "status":"ok","response_text":"SYNTHETIC PLACEHOLDER NOT A MODEL PREDICTION",
                    "provider_response_id":f"syn-{row['item_id']}-{sample}",
                    "timestamp":"2026-10-08T00:00:00Z"
                })
        self.write_capture()
        self.receipt=self.make_receipt()

    def write_capture(self):
        self.capture.write_text("".join(json.dumps(x)+"\n" for x in self.raw),encoding="utf-8")

    def make_receipt(self):
        return {"schema_version":"1.0.0","suite_id":self.suite["suite_id"],
                "model_key":self.model["key"],"provider_model_id":self.model["provider_model_id"],
                "raw_capture_sha256":b.digest(self.capture),
                "item_manifest_sha256":b.digest(self.items),
                "prompt_sha256":"f"*64,"records_expected":4,"status":"captured"}

    def audit(self):
        return b.verify_capture(self.suite,self.items,self.capture,self.receipt)

    def test_planning_suite_is_valid_but_not_executable(self):
        self.assertEqual([],b.validate_suite(self.planning,self.schema))
        self.assertEqual("planning",self.planning["status"])

    def test_only_pinned_benchmark_commit_allowed(self):
        modified=copy.deepcopy(self.planning)
        modified["official_benchmark"]["commit"]="a"*40
        self.assertTrue(any("pinned" in e for e in b.validate_suite(modified,self.schema)))

    def test_model_keys_must_be_unique(self):
        modified=copy.deepcopy(self.planning)
        modified["models"][1]["key"]=modified["models"][0]["key"]
        self.assertTrue(any("unique" in e for e in b.validate_suite(modified,self.schema)))

    def test_execution_ready_requires_permitted_spend(self):
        self.suite["execution_gate"]["budget_approved"]=False
        self.assertTrue(any("budget_approved" in e for e in b.validate_suite(self.suite,self.schema)))

    def test_execution_ready_requires_exact_provider_ids(self):
        self.suite["models"][0]["provider_model_id"]=None
        self.assertTrue(any("exact provider" in e for e in b.validate_suite(self.suite,self.schema)))

    def test_official_prompts_are_immutable(self):
        self.suite["official_prompts"]["no_examples"]=False
        self.assertTrue(b.validate_suite(self.suite,self.schema))

    def test_public_only_item_manifest_accepted(self):
        self.assertEqual(2,len(b.parse_item_manifest(self.items,self.suite)))

    def test_sealed_item_cannot_enter_local_run(self):
        self.records[0]["split"]="sealed"
        self.items.write_text("".join(json.dumps(x)+"\n" for x in self.records),encoding="utf-8")
        with self.assertRaisesRegex(b.BaselineError,"sealed"):
            b.parse_item_manifest(self.items,self.suite)

    def test_translation_rung_not_scorable_on_public_gold(self):
        self.records[0]["rung"]="translate"
        self.items.write_text("".join(json.dumps(x)+"\n" for x in self.records),encoding="utf-8")
        with self.assertRaisesRegex(b.BaselineError,"out-of-contract"):
            b.parse_item_manifest(self.items,self.suite)

    def test_duplicate_item_rung_fails(self):
        self.records.append(copy.deepcopy(self.records[0]))
        self.items.write_text("".join(json.dumps(x)+"\n" for x in self.records),encoding="utf-8")
        with self.assertRaisesRegex(b.BaselineError,"repeated"):
            b.parse_item_manifest(self.items,self.suite)

    def test_clean_synthetic_capture_integrity_passes_but_does_not_score(self):
        self.assertEqual([],b.validate_suite(self.suite,self.schema))
        report=self.audit()
        self.assertEqual(4,report["captured_attempts"])
        self.assertFalse(report["scoring_reproduced"])
        self.assertFalse(report["fresh_model_results_validated"])
        self.assertNotIn("response_text",json.dumps(report))

    def test_missing_attempt_cannot_improve_score_by_cherry_picking(self):
        self.raw.pop();self.write_capture();self.receipt["raw_capture_sha256"]=b.digest(self.capture)
        with self.assertRaisesRegex(b.BaselineError,"Incomplete capture"):
            self.audit()

    def test_duplicate_attempt_fails(self):
        self.raw[-1]=copy.deepcopy(self.raw[0]);self.write_capture()
        self.receipt["raw_capture_sha256"]=b.digest(self.capture)
        with self.assertRaisesRegex(b.BaselineError,"duplicate"):
            self.audit()

    def test_failed_attempt_preserved_in_denominator(self):
        self.raw[0]["status"]="failed";self.raw[0]["response_text"]=""
        self.raw[0]["provider_response_id"]=None
        self.write_capture();self.receipt["raw_capture_sha256"]=b.digest(self.capture)
        self.assertEqual(1,self.audit()["failed_attempts_preserved"])

    def test_drifted_prompt_refused(self):
        self.raw[0]["prompt_sha256"]="a"*64;self.write_capture()
        self.receipt["raw_capture_sha256"]=b.digest(self.capture)
        with self.assertRaisesRegex(b.BaselineError,"provider/prompt"):
            self.audit()

    def test_capture_hash_drift_refused(self):
        self.receipt["raw_capture_sha256"]="a"*64
        with self.assertRaisesRegex(b.BaselineError,"SHA-256"):
            self.audit()

    def test_mismatched_model_identity_refused(self):
        self.receipt["provider_model_id"]="different-model"
        with self.assertRaisesRegex(b.BaselineError,"model/provider identity"):
            self.audit()

    def test_raw_capture_inside_repository_refused(self):
        with tempfile.TemporaryDirectory(dir=b.ROOT) as temp:
            protected=Path(temp)/"synthetic-raw.jsonl"
            protected.write_text(self.capture.read_text(encoding="utf-8"),encoding="utf-8")
            with self.assertRaisesRegex(b.BaselineError,"outside the public repository"):
                b.verify_capture(self.suite,self.items,protected,self.receipt)

    def test_snapshot_receipt_cannot_be_called_scored(self):
        self.receipt["status"]="scored"
        with self.assertRaisesRegex(b.BaselineError,"never certifies scores"):
            self.audit()

    def test_manifest_must_match_upstream_if_metadata_supplied(self):
        known={"SYNTHETIC-1":{"split":"public","rungs":["identify"]},
               "SYNTHETIC-2":{"split":"sealed","rungs":["signs"]}}
        with self.assertRaisesRegex(b.BaselineError,"not an eligible public"):
            b.parse_item_manifest(self.items,self.suite,known)

    def test_no_network_or_provider_client_imported(self):
        import inspect
        source=inspect.getsource(b)
        self.assertNotIn("requests.",source)
        self.assertNotIn("urllib.request",source)
        self.assertNotIn("openai.",source)
        self.assertNotIn("anthropic.",source)



class PublicBenchmarkFreezeTests(unittest.TestCase):
    """Synthetic-only checks of public benchmark identity/metadata freeze."""

    def setUp(self):
        from eval.baselines import public_freeze as f
        self.f=f
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir=Path(self.tmp.name)
        self.items={}
        for n in range(116):
            key=f"syn-identify-{n:04d}"
            self.items[key]={"split":"public","rungs":("identify",),"id":key}
        for n in range(150):
            key=f"syn-sign-{n:04d}"
            self.items[key]={"split":"public","rungs":("signs",),"id":key}
        for n in range(2):
            key=f"syn-sealed-{n}"
            self.items[key]={"split":"sealed","rungs":("identify","signs"),"id":key}

    def test_only_266_public_item_rung_records(self):
        rows=self.f.safe_public_pairs(self.items)
        self.assertEqual(266,len(rows))
        self.assertEqual(116,sum(r["rung"]=="identify" for r in rows))
        self.assertEqual(150,sum(r["rung"]=="signs" for r in rows))
        self.assertTrue(all(r["split"]=="public" for r in rows))

    def test_never_exports_sealed_ids_or_reading_gold(self):
        binary=self.f.manifest_bytes(self.items)
        self.assertNotIn(b"syn-sealed",binary)
        self.assertNotIn(b"gardiner",binary)
        self.assertNotIn(b"transliteration",binary)
        self.assertNotIn(b"translation",binary)

    def test_count_drift_refused(self):
        del self.items["syn-identify-0000"]
        with self.assertRaisesRegex(self.f.PublicFreezeError,"inventory count"):
            self.f.safe_public_pairs(self.items)

    def test_unauthorized_new_public_item_rung_refused(self):
        self.items["syn-sealed-0"]["split"]="public"
        with self.assertRaisesRegex(self.f.PublicFreezeError,"count mismatch"):
            self.f.safe_public_pairs(self.items)

    def test_manifest_is_byte_deterministic_across_dictionary_order(self):
        left=self.f.manifest_bytes(self.items)
        right=self.f.manifest_bytes(dict(reversed(list(self.items.items()))))
        self.assertEqual(left,right)

    def _stub_snapshot(self):
        import unittest.mock
        binary=self.f.manifest_bytes(self.items)
        receipt={"schema_version":"1.0.0","manifest_sha256":self.f.content_hash(binary),
                 "official_prompt_source_sha256":"c"*64,"public_item_rung_count":266}
        return unittest.mock.patch.object(self.f,"build_snapshot",return_value=(binary,receipt))

    def test_freeze_and_verify_offline_synthetic(self):
        with self._stub_snapshot():
            self.f.freeze(self.dir,self.dir)
            verified=self.f.verify(self.dir,self.dir)
            self.assertEqual(266,verified["public_item_rung_count"])

    def test_freeze_cannot_overwrite_original_receipt(self):
        with self._stub_snapshot():
            self.f.freeze(self.dir,self.dir)
            with self.assertRaisesRegex(self.f.PublicFreezeError,"do not overwrite"):
                self.f.freeze(self.dir,self.dir)

    def test_tampered_public_item_manifest_rejected(self):
        with self._stub_snapshot():
            self.f.freeze(self.dir,self.dir)
            (self.dir/"public-item-rungs.jsonl").write_text("tampered",encoding="utf-8")
            with self.assertRaisesRegex(self.f.PublicFreezeError,"differs"):
                self.f.verify(self.dir,self.dir)

    def test_tampered_prompt_hash_receipt_rejected(self):
        with self._stub_snapshot():
            self.f.freeze(self.dir,self.dir)
            p=self.dir/"public-freeze-receipt.json"
            rec=json.loads(p.read_text(encoding="utf-8"))
            rec["official_prompt_source_sha256"]="a"*64
            p.write_text(json.dumps(rec),encoding="utf-8")
            with self.assertRaisesRegex(self.f.PublicFreezeError,"differs"):
                self.f.verify(self.dir,self.dir)

    def test_repo_as_artifact_store_refused(self):
        with self.assertRaisesRegex(self.f.PublicFreezeError,"outside this repository"):
            self.f._validate_dest(self.f.ROOT)

    def test_missing_output_directory_refused(self):
        with self.assertRaisesRegex(self.f.PublicFreezeError,"Existing external output"):
            self.f._validate_dest(self.dir/"missing-directory")

    def test_pinned_snapshot_inspects_only_metadata_and_prompt_hash(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as check:
            checkout=Path(check)
            prompt=checkout/"bench/src/prompts.ts"
            prompt.parent.mkdir(parents=True)
            prompt.write_text("export const syntheticOnly=true;",encoding="utf-8")
            fake={"benchmark":{"pinned_commit":self.f.load_manifest()["benchmark"]["pinned_commit"]}}
            with (\n                patch.object(self.f,"load_manifest",return_value=fake),\n                patch.object(self.f,"assert_pinned_checkout") as pinned,\n                patch.object(self.f,"inspect_items",return_value=self.items),\n            ):
                manifest,receipt=self.f.build_snapshot(checkout)
            pinned.assert_called_once()
            self.assertEqual(266,receipt["public_item_rung_count"])
            self.assertEqual(self.f.content_hash(prompt.read_bytes()),receipt["official_prompt_source_sha256"])
            self.assertNotIn(b"syn-sealed",manifest)


if __name__=="__main__":
    unittest.main()
