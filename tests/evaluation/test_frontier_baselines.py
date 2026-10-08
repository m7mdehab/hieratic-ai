"""EVAL-003: wholly synthetic, offline baseline provenance and capture tests."""
from __future__ import annotations

import copy
from pathlib import Path
import json
import tempfile
import unittest
import yaml

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
            with (
                patch.object(self.f,"load_manifest",return_value=fake),
                patch.object(self.f,"assert_pinned_checkout") as pinned,
                patch.object(self.f,"inspect_items",return_value=self.items),
            ):
                manifest,receipt=self.f.build_snapshot(checkout)
            pinned.assert_called_once()
            self.assertEqual(266,receipt["public_item_rung_count"])
            self.assertEqual(self.f.content_hash(prompt.read_bytes()),receipt["official_prompt_source_sha256"])
            self.assertNotIn(b"syn-sealed",manifest)



class OriginalRunFreezeTests(unittest.TestCase):
    """Purely synthetic byte-level evidence tests; zero paid calls or gold."""

    def setUp(self):
        from eval.baselines import run_freeze as f
        from unittest.mock import patch
        self.f=f
        self.patch=patch
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ext=Path(self.temp.name)
        self.vault=self.ext/"vault"
        self.vault.mkdir()
        self.upstream=self.ext/"upstream"
        (self.upstream/"bench/src").mkdir(parents=True)
        (self.upstream/"bench/src/prompts.ts").write_bytes(b"synthetic upstream prompt source")
        (self.upstream/"bench/src/score.ts").write_bytes(b"synthetic official scoring source")
        self.items=self.ext/"public-item-rungs.jsonl"
        self.public=[
           {"item_id":"SYNTH-ID","rung":"identify","split":"public"},
           {"item_id":"SYNTH-SIGN","rung":"signs","split":"public"}
        ]
        self.public_bytes="".join(json.dumps(x,sort_keys=True,separators=(",",":"))+"\n" for x in self.public).encode()
        self.items.write_bytes(self.public_bytes)
        self.attempts=self.ext/"prompt-attempts.jsonl"
        self.rows=[]
        for item in self.public:
            for sample in range(2):
                stem=f"{item['item_id']}-{sample}"
                prompt=self.vault/(stem+".txt")
                image=self.vault/(item["item_id"]+".png")
                prompt.write_bytes(("SYNTHETIC PROMPT "+stem).encode())
                image.write_bytes(("SYNTHETIC IMAGE "+item["item_id"]).encode())
                self.rows.append({
                   "item_id":item["item_id"],"rung":item["rung"],
                   "sample_index":sample,"model_key":"openai-frontier",
                   "prompt_path":prompt.name,"prompt_sha256":f.sha256_file(prompt),
                   "image_path":image.name,"image_sha256":f.sha256_file(image)
                })
        self.write_attempts()
        self.suite=copy.deepcopy(b.load_data(b.DEFAULT_SUITE))
        self.suite["status"]="execution_ready"
        self.suite["protocol"]["samples_per_item"]=2
        self.suite["official_benchmark"]["item_manifest_sha256"]=f.sha256_file(self.items)
        self.suite["official_prompts"]["exact_prompt_bundle_sha256"]="b"*64
        for flag in self.suite["execution_gate"]:
            self.suite["execution_gate"][flag]=(5.0 if flag=="max_total_spend_usd" else True)
        for model in self.suite["models"]:
            model.update(provider_model_id="synthetic-"+model["key"],api_route="synthetic-offline",effort="synthetic-not-provider")
        self.freeze=copy.deepcopy(f._read(f.DRAFT))
        self.freeze.update({
            "state":"locked","provider_model_id":"synthetic-openai-frontier",
            "provider_route":"synthetic-offline",
            "model_checkpoint_or_version":"synthetic-v0",
            "official_prompt_source_sha256":f.sha256_file(self.upstream/"bench/src/prompts.ts"),
            "scorer_source_sha256":f.sha256_file(self.upstream/"bench/src/score.ts"),
            "public_item_manifest_sha256":f.sha256_file(self.items),
            "prompt_attempts_manifest_sha256":f.sha256_file(self.attempts),
            "model_settings_sha256":"a"*64,
            "inference_code_commit":"c"*40,
            "inference_runtime_sha256":"a"*64,
            "metric_contract_sha256":f.sha256_file(b.ROOT/"eval/metric_contract.yaml"),
            "samples_per_item":2,"attempts_planned":4,"budget_cap_usd":1.0,
            "approval":{"approved":True,"approved_by":"synthetic-reviewer",
                        "approved_at":"2026-10-08T12:00:00Z",
                        "evidence_ref":"artifact:synthetic-approval"},
            "archive":{"external_private_store":True,"access_restricted":True,
                       "raw_response_retention":"private","append_only":True,
                       "encryption_at_rest":True},
            "benchmark_rights":{"evaluation_only":True,"sealed_items_excluded":True,
                  "used_for_training_or_dev":False,"few_shot_uses_benchmark":False,
                  "image_rights_reviewed":True,"item_overlap_reviewed":True,
                  "rights_review_ref":"artifact:synthetic-rights",
                  "overlap_review_ref":"artifact:synthetic-overlap"}
        })

    def write_attempts(self):
        self.attempts.write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in self.rows),encoding="utf-8")

    def verify(self,*,human=True):
        with (
            self.patch.object(self.f.adapter,"load_manifest",return_value={"benchmark":{"pinned_commit":self.f.PINNED}}),
            self.patch.object(self.f.adapter,"assert_pinned_checkout") as pinned,
            self.patch.object(self.f.adapter,"inspect_items",return_value={}),
            self.patch.object(self.f.public_freeze,"safe_public_pairs",return_value=self.public),
            self.patch.object(self.f.public_freeze,"manifest_bytes",return_value=self.public_bytes),
        ):
            result=self.f.validate_locked(
                self.freeze,self.suite,items_path=self.items,attempts_path=self.attempts,
                vault_path=self.vault,upstream_checkout=self.upstream,
                actual_approval_confirmed=human
            )
            pinned.assert_called_once()
            return result

    def expect_refused(self,needle):
        with self.assertRaisesRegex(self.f.FreezeError,needle):
            self.verify()

    def test_unapproved_draft_is_valid_but_not_executable(self):
        self.assertEqual([],self.f.validate_draft(self.f._read(self.f.DRAFT)))
        self.assertEqual(0,self.f.main(["validate-draft"]))

    def test_draft_forged_approval_refused(self):
        draft=self.f._read(self.f.DRAFT);draft["approval"]["approved"]=True
        self.assertTrue(any("draft may not claim" in e for e in self.f.validate_draft(draft)))

    def test_draft_unknown_gold_answer_field_refused(self):
        draft=self.f._read(self.f.DRAFT);draft["secret_gold_answers"]=["fake"]
        self.assertTrue(any("Additional properties" in e for e in self.f.validate_draft(draft)))

    def test_locked_preregistration_requires_external_human_approval(self):
        with self.assertRaisesRegex(self.f.FreezeError,"not consent"):
            self.verify(human=False)

    def test_synthetic_locked_receipts_pass_only_integrity_not_models(self):
        result=self.verify()
        self.assertEqual(4,result["planned_attempts"])
        self.assertFalse(result["fresh_model_result"])
        self.assertFalse(result["official_score_reproduced"])

    def test_suite_must_be_explicitly_authorized(self):
        self.suite["status"]="planning"
        self.expect_refused("separately approved")

    def test_provider_id_drift_rejected(self):
        self.freeze["provider_model_id"]="synthetic-changed"
        self.expect_refused("Provider model/version or route mismatch")

    def test_budget_greater_than_approved_cap_refused(self):
        self.freeze["budget_cap_usd"]=50.0
        self.expect_refused("budget exceeds")

    def test_unreviewed_item_rights_refused(self):
        self.freeze["benchmark_rights"]["image_rights_reviewed"]=False
        self.expect_refused("Unreviewed item-level")

    def test_incomplete_private_archive_refused(self):
        self.freeze["archive"]["encryption_at_rest"]=False
        self.expect_refused("Unsecured private")

    def test_missing_immutable_scorer_digest_refused(self):
        self.freeze["scorer_source_sha256"]=None
        self.expect_refused("Missing immutable")

    def test_corrupted_exact_prompt_file_refused(self):
        (self.vault/self.rows[0]["prompt_path"]).write_text("tampered")
        self.expect_refused("actual prompt/image bytes mismatch")

    def test_corrupted_image_file_refused(self):
        (self.vault/self.rows[0]["image_path"]).write_text("tampered")
        self.expect_refused("actual prompt/image bytes mismatch")

    def test_missing_attempt_rejected_even_with_updated_manifest_digest(self):
        self.rows.pop()
        self.write_attempts()
        self.freeze["prompt_attempts_manifest_sha256"]=self.f.sha256_file(self.attempts)
        self.expect_refused("Unrecorded attempts")

    def test_duplicate_item_attempt_rejected(self):
        self.rows[-1]=copy.deepcopy(self.rows[0])
        self.write_attempts()
        self.freeze["prompt_attempts_manifest_sha256"]=self.f.sha256_file(self.attempts)
        self.expect_refused("duplicate/unrequested")

    def test_unexpected_sealed_id_rejected(self):
        self.rows[0]["item_id"]="SYNTH-SEALED"
        self.write_attempts()
        self.freeze["prompt_attempts_manifest_sha256"]=self.f.sha256_file(self.attempts)
        self.expect_refused("duplicate/unrequested")

    def test_attempt_with_extra_gold_field_rejected(self):
        self.rows[0]["gold_transliteration"]="FAKE"
        self.write_attempts()
        self.freeze["prompt_attempts_manifest_sha256"]=self.f.sha256_file(self.attempts)
        self.expect_refused("exactly the 8 metadata fields")

    def test_prompt_path_escape_refused(self):
        self.rows[0]["prompt_path"]="../outside/secret.txt"
        self.write_attempts()
        self.freeze["prompt_attempts_manifest_sha256"]=self.f.sha256_file(self.attempts)
        self.expect_refused("path escapes")

    def test_unapproved_model_image_swap_across_samples_rejected(self):
        changed=self.vault/"different-image.png"
        changed.write_bytes(b"SYNTHETIC DIFFERENT IMAGE")
        self.rows[1]["image_path"]=changed.name
        self.rows[1]["image_sha256"]=self.f.sha256_file(changed)
        self.write_attempts()
        self.freeze["prompt_attempts_manifest_sha256"]=self.f.sha256_file(self.attempts)
        self.expect_refused("image changes across")

    def test_wrong_official_scorer_revision_refused(self):
        self.freeze["scorer_source_sha256"]="f"*64
        self.expect_refused("Official scoring-source content")

    def test_wrong_metric_contract_refused(self):
        self.freeze["metric_contract_sha256"]="f"*64
        self.expect_refused("Metric contract differs")

    def test_pinned_public_item_file_cannot_be_modified(self):
        self.items.write_bytes(self.public_bytes+b'{"item_id":"SYNTH-SEALED","rung":"translate","split":"sealed"}\n')
        self.freeze["public_item_manifest_sha256"]=self.f.sha256_file(self.items)
        self.suite["official_benchmark"]["item_manifest_sha256"]=self.f.sha256_file(self.items)
        self.expect_refused("Public item/rung IDs differ")

    def private_capture(self, raw=None, receipt_override=None):
        raw=raw if raw is not None else [
            {
                "item_id":row["item_id"],"rung":row["rung"],
                "sample_index":row["sample_index"],"provider_model_id":self.freeze["provider_model_id"],
                "prompt_sha256":row["prompt_sha256"],"status":"ok",
                "response_text":"SYNTHETIC NOT A REAL MODEL ANSWER",
                "provider_response_id":f"synthetic-{i}","timestamp":"2026-10-08T13:00:00Z"
            }
            for i,row in enumerate(self.rows)
        ]
        output=self.ext/"raw-private.jsonl"
        output.write_text("".join(json.dumps(v,sort_keys=True)+"\n" for v in raw),encoding="utf-8")
        receipt={
            "schema_version":"1.0.0","state":"captured","run_id":self.freeze["run_id"],
            "model_key":self.freeze["model_key"],"provider_model_id":self.freeze["provider_model_id"],
            "capture_sha256":self.f.sha256_file(output),
            "rendered_attempts_sha256":self.f.sha256_file(self.attempts),
            "records_expected":4,
        }
        receipt.update(receipt_override or {})
        with (
            self.patch.object(self.f.adapter,"load_manifest",return_value={"benchmark":{"pinned_commit":self.f.PINNED}}),
            self.patch.object(self.f.adapter,"assert_pinned_checkout"),
            self.patch.object(self.f.adapter,"inspect_items",return_value={}),
            self.patch.object(self.f.public_freeze,"safe_public_pairs",return_value=self.public),
            self.patch.object(self.f.public_freeze,"manifest_bytes",return_value=self.public_bytes),
        ):
            return self.f.audit_original_capture(
                self.freeze,self.suite,items_path=self.items,attempts_path=self.attempts,
                vault_path=self.vault,upstream_checkout=self.upstream,
                capture_path=output,receipt=receipt,actual_approval_confirmed=True
            )

    def test_original_raw_capture_checks_actual_different_per_item_prompts(self):
        result=self.private_capture()
        self.assertEqual(4,result["attempts_planned"])
        self.assertEqual(4,result["preserved_by_status"]["ok"])
        self.assertFalse(result["scientific_experiment_validated"])
        self.assertNotIn("response_text",json.dumps(result))

    def test_original_raw_capture_detects_unfrozen_prompt(self):
        raw=[{"item_id":row["item_id"],"rung":row["rung"],
              "sample_index":row["sample_index"],"provider_model_id":self.freeze["provider_model_id"],
              "prompt_sha256":row["prompt_sha256"],"status":"ok",
              "response_text":"SYNTHETIC","provider_response_id":"synthetic-r",
              "timestamp":"2026-10-08T13:00:00Z"} for row in self.rows]
        raw[0]["prompt_sha256"]="f"*64
        with self.assertRaisesRegex(self.f.FreezeError,"prompt digest differs"):
            self.private_capture(raw)

    def test_original_capture_cannot_silently_drop_refusal(self):
        raw=[{"item_id":row["item_id"],"rung":row["rung"],
              "sample_index":row["sample_index"],"provider_model_id":self.freeze["provider_model_id"],
              "prompt_sha256":row["prompt_sha256"],"status":"ok",
              "response_text":"SYNTHETIC","provider_response_id":"synthetic-r",
              "timestamp":"2026-10-08T13:00:00Z"} for row in self.rows]
        raw.pop()
        with self.assertRaisesRegex(self.f.FreezeError,"Incomplete original model capture"):
            self.private_capture(raw)

    def test_original_capture_preserves_failed_abstained_timeout_and_refusal(self):
        raw=[{"item_id":row["item_id"],"rung":row["rung"],
              "sample_index":row["sample_index"],"provider_model_id":self.freeze["provider_model_id"],
              "prompt_sha256":row["prompt_sha256"],"status":status,
              "response_text":"","provider_response_id":None,
              "timestamp":"2026-10-08T13:00:00Z"} for row,status in zip(
                  self.rows,("failed","abstained","timeout","refused")
              )]
        result=self.private_capture(raw)
        self.assertEqual({"failed":1,"abstained":1,"timeout":1,"refused":1},
                         result["preserved_by_status"])

    def test_raw_capture_cannot_claim_completed_scoring(self):
        with self.assertRaisesRegex(self.f.FreezeError,"cannot masquerade"):
            self.private_capture(receipt_override={"state":"scored"})

    def test_raw_capture_wrong_provider_identity_fails(self):
        with self.assertRaisesRegex(self.f.FreezeError,"identity mismatch"):
            self.private_capture(receipt_override={"provider_model_id":"fake-other-model"})

    def test_raw_capture_requires_timezone_aware_timestamp(self):
        raw=[{"item_id":row["item_id"],"rung":row["rung"],
              "sample_index":row["sample_index"],"provider_model_id":self.freeze["provider_model_id"],
              "prompt_sha256":row["prompt_sha256"],"status":"ok",
              "response_text":"SYNTHETIC","provider_response_id":"synthetic-r",
              "timestamp":"2026-10-08T13:00:00Z"} for row in self.rows]
        raw[0]["timestamp"]="2026-10-08T13:00:00"
        with self.assertRaisesRegex(self.f.FreezeError,"invalid timestamp"):
            self.private_capture(raw)

    def test_locked_cli_fails_even_with_metadata_because_no_human_consent_in_ci(self):
        record=self.ext/"run.json"
        record.write_text(json.dumps(self.freeze),encoding="utf-8")
        suite=self.ext/"suite.yaml"
        suite.write_text(yaml.safe_dump(self.suite),encoding="utf-8")
        self.assertEqual(1,self.f.main([
           "verify-locked","--record",str(record),"--suite",str(suite),
           "--items",str(self.items),"--attempts",str(self.attempts),
           "--vault",str(self.vault),"--upstream-checkout",str(self.upstream)
        ]))


if __name__=="__main__":
    unittest.main()
