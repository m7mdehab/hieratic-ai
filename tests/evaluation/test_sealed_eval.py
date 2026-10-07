"""EVAL-006 synthetic sealed evaluation safety and release gate tests.

All record examples are fabricated metadata; no sealed item IDs, reading gold,
copyrighted images, model outputs or genuine results are present.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from eval.sealed import protocolctl as s


class SealedEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol=s.load(s.PROTOCOL_PATH)
        cls.schema=s.load(s.SCHEMA_PATH)
        cls.draft=s.load(s.ROOT/"eval/sealed/examples/draft.synthetic.json")

    def frozen(self):
        r=copy.deepcopy(self.draft)
        r["state"]="frozen"
        r["protocol_sha256"]=s.sha256(s.PROTOCOL_PATH)
        r["freeze_sha256"]="a"*64
        r["freeze_created_at"]="2026-10-08T10:00:00Z"
        r["first_sealed_access_at"]=None
        r["roles"]={
            "training_operator":"synthetic-trainer",
            "sealed_custodian":"synthetic-custodian",
            "blind_scorer":"synthetic-scorer",
            "adjudicator":"synthetic-adjudicator",
            "release_authorities":["synthetic-release-1","synthetic-release-2"]
        }
        r["frozen_inputs"]={k:("a"*40 if k=="inference_code_commit" else "a"*64) for k in s.REQUIRED_HASHES}
        r["frozen_inputs"]["metric_contract_sha256"]=s.sha256(s.METRICS_PATH)
        r["metric_ids"]=["SIGN_TOP1","TR_CER"]
        r["rights"]={"status":"cleared","reviewer_id":"synthetic-rights-reviewer","evidence_ref":"artifact:synthetic-rights"}
        r["overlap"]={"status":"cleared","roster_sha256":"a"*64,"reviewer_id":"synthetic-overlap-reviewer","evidence_ref":"artifact:synthetic-overlap-review","unresolved_candidates":0}
        r["contamination"]["status"]="none_detected"
        return r

    def scored(self):
        r=self.frozen()
        r["state"]="scored"
        r["first_sealed_access_at"]="2026-10-08T11:00:00Z"
        r["attempts"]={"expected":3,"received":3,"failed":1,"abstained":1,"excluded_unscorable":0}
        r["scoring"].update({
            "status":"scored","scorer_sha256":"a"*64,
            "prediction_archive_sha256":"c"*64,
            "score_archive_sha256":"d"*64,
            "attempted_metric_ids":["SIGN_TOP1","TR_CER"]
        })
        return r

    def publishable(self):
        r=self.scored()
        r["state"]="publishable"
        r["scoring"]["status"]="independently_reproduced"
        r["scoring"]["document_macro_report_sha256"]="e"*64
        r["scoring"]["bootstrap_report_sha256"]="f"*64
        r["adjudication"].update({
            "status":"complete","blinded_to_model":True,
            "reviewer_id":"synthetic-adjudicator",
            "evidence_ref":"artifact:synthetic-expert-review","unresolved_gold_count":0
        })
        r["approvals"]=[{
            "reviewer_id":i,"approved":True,"evidence_ref":"artifact:synthetic-approval",
            "reviewed_at":"2026-10-08T12:00:00Z"
        } for i in ("synthetic-release-1","synthetic-release-2")]
        r["release_artifacts"]=[{
            "role":name,"sha256":"f"*64,"reference":"artifact:synthetic-"+name
        } for name in sorted(s.PUBLIC_ARTIFACTS)]
        return r

    def err(self,r,phrase):
        problems=s.validate_release(r,self.schema,self.protocol)
        self.assertTrue(any(phrase in x for x in problems),problems)

    def test_policy_versions_match_accepted_authorities(self):
        self.assertEqual([],s.validate_protocol(self.protocol))

    def test_draft_fixture_remains_nonexecuted_and_valid(self):
        self.assertEqual([],s.validate_release(self.draft,self.schema,self.protocol))

    def test_synthetic_frozen_metadata_contract_is_valid(self):
        self.assertEqual([],s.validate_release(self.frozen(),self.schema,self.protocol))

    def test_synthetic_scored_metadata_contract_is_valid(self):
        self.assertEqual([],s.validate_release(self.scored(),self.schema,self.protocol))

    def test_synthetic_publishable_metadata_contract_is_valid(self):
        self.assertEqual([],s.validate_release(self.publishable(),self.schema,self.protocol))

    def test_unpinned_protocol_hash_rejected(self):
        r=self.frozen();r["protocol_sha256"]="b"*64
        self.err(r,"protocol SHA-256 mismatch")

    def test_metric_contract_drift_rejected(self):
        r=self.frozen();r["frozen_inputs"]["metric_contract_sha256"]="c"*64
        self.err(r,"metric contract SHA-256")

    def test_unrecognized_metric_rejected(self):
        r=self.frozen();r["metric_ids"]=["FAKE_READING_SCORE"]
        self.err(r,"unknown metric IDs")

    def test_missing_prediction_checkpoint_ref_fails(self):
        r=self.frozen();r["frozen_inputs"]["model_checkpoint_sha256"]=None
        self.err(r,"required immutable input hashes")

    def test_model_custodian_separation_enforced(self):
        r=self.frozen();r["roles"]["sealed_custodian"]="synthetic-trainer"
        self.err(r,"must be distinct")

    def test_release_authority_cannot_be_custodian(self):
        r=self.frozen();r["roles"]["release_authorities"][0]="synthetic-custodian"
        self.err(r,"release authorities cannot")

    def test_freeze_after_first_sealed_access_fails(self):
        r=self.scored();r["freeze_created_at"]="2026-10-08T12:00:00Z"
        self.err(r,"frozen after first sealed access")

    def test_unknown_rights_cannot_be_frozen(self):
        r=self.frozen();r["rights"]["status"]="unreviewed"
        self.err(r,"rights clearance absent")

    def test_unknown_benchmark_overlap_cannot_be_frozen(self):
        r=self.frozen();r["overlap"]["status"]="unreviewed"
        self.err(r,"overlap review incomplete")

    def test_unresolved_near_duplicate_blocks_freeze(self):
        r=self.frozen();r["overlap"]["unresolved_candidates"]=1
        self.err(r,"overlap review incomplete")

    def test_missing_attempts_fail_scored_state(self):
        r=self.scored();r["attempts"]["received"]=2
        self.err(r,"incomplete predictions/attempts")

    def test_zero_attempts_cannot_be_scored(self):
        r=self.scored();r["attempts"]["expected"]=0;r["attempts"]["received"]=0
        self.err(r,"zero denominator")

    def test_attempt_statuses_cannot_exceed_attempts(self):
        r=self.scored();r["attempts"]["abstained"]=3
        self.err(r,"exceed attempts")

    def test_off_protocol_posthoc_metric_fails(self):
        r=self.scored();r["scoring"]["attempted_metric_ids"]=["SCRIPT_ACC"]
        self.err(r,"post-hoc metric addition")

    def test_upstream_score_conflation_refused(self):
        r=self.scored();r["scoring"]["official_external_metric_separate"]=False
        self.err(r,"must not be conflated")

    def test_score_engine_drift_refused(self):
        r=self.scored();r["scoring"]["scorer_sha256"]="d"*64
        self.err(r,"preregistered scorer")

    def test_suspected_contamination_blocks_scores(self):
        r=self.scored();r["contamination"]["status"]="suspected"
        self.err(r,"contamination uncertain")

    def test_confirmed_contamination_blocks_publication(self):
        r=self.publishable();r["contamination"]["status"]="confirmed"
        self.err(r,"contamination uncertain")

    def test_blind_gold_adjudication_mandatory(self):
        r=self.publishable();r["adjudication"]["blinded_to_model"]=False
        self.err(r,"not blind")

    def test_unresolved_gold_blocks_publication(self):
        r=self.publishable();r["adjudication"]["unresolved_gold_count"]=1
        self.err(r,"incomplete or not blind")

    def test_independent_rescoring_mandatory(self):
        r=self.publishable();r["scoring"]["status"]="scored"
        self.err(r,"independent scoring")

    def test_document_group_uncertainty_mandatory(self):
        r=self.publishable();r["scoring"]["bootstrap_report_sha256"]=None
        self.err(r,"clustered uncertainty")

    def test_release_requires_two_approved_independent_reviewers(self):
        r=self.publishable();r["approvals"]=r["approvals"][:1]
        self.err(r,"missing independent release approval")

    def test_conflicted_release_reviewer_refused(self):
        r=self.publishable()
        r["approvals"][0]["reviewer_id"]="synthetic-trainer"
        self.err(r,"missing independent release approval")

    def test_missing_release_artifact_refused(self):
        r=self.publishable();r["release_artifacts"]=r["release_artifacts"][1:]
        self.err(r,"incomplete provenance/report artifacts")

    def test_incident_with_publication_rejected(self):
        r=self.publishable()
        r["contamination"]["incidents"]=[{
          "incident_id":"SYNTH-INCIDENT","status":"dismissed",
          "affected_runs":["SYNTHETIC-RUN"],"evidence_refs":["artifact:synthetic-review"],
          "reviewer_id":"synthetic-custodian","decision":"review required",
          "public_disclosure":True
        }]
        self.err(r,"contamination incidents require")

    def test_unknown_extra_field_cannot_embed_sealed_answer(self):
        r=self.draft.copy();r["secret_gold_text"]="SYNTHETIC-SECRET-FAKE"
        self.err(r,"Additional properties")

    def test_cli_validates_protocol_and_draft_example(self):
        self.assertEqual(0,s.main(["validate-protocol"]))
        self.assertEqual(0,s.main(["validate-release","--input",str(s.ROOT/"eval/sealed/examples/draft.synthetic.json")]))

    def test_nothing_in_public_record_is_raw_gold(self):
        obj=self.publishable()
        serialized=json.dumps(obj)
        self.assertNotIn("transliteration_reference",serialized)
        self.assertNotIn("raw_image",serialized)
        self.assertNotIn("secret_gold_text",serialized)


if __name__=="__main__":
    unittest.main()
