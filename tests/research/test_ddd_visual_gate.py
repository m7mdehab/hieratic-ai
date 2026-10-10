"""Adversarial licensing, provenance, source and cohort invariants for W26."""
import copy
import unittest

from tools.research_ddd_public_metadata import PublicSourceError
from tools.research_ddd_visual_gate import (
    SOURCE_SHA256, REASONS, build_preflight, validate_positive_clearance,
    verified_source,
)


def fixtures():
    papyri = {f"{i:03d}":{"name":f"object_{i}","doc_cluster":i%50,
               "copyright":"© Scan/Museo Egizio", "TPOP_ref":{"document":i+1}}
              for i in range(159)}
    papyri["003"]["name"]="C1880rt_rotated"
    papyri["004"]["name"]="C1880rt"
    papyri["003"]["doc_cluster"]=1
    papyri["004"]["doc_cluster"]=1
    samples={f"{i:05d}":{"sample_number":f"{i:05d}",
                 "document_number":f"{i%159:03d}","class_label":f"C{i%504}"}
             for i in range(17885)}
    classes={str(i):{"class_label":f"C{i}"} for i in range(504)}
    return papyri,samples,classes


class W26GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p,cls.s,cls.c=fixtures()
        cls.report=build_preflight(cls.p,cls.s,cls.c)

    def test_complete_real_original_shape_never_promoted(self):
        r=self.report
        self.assertEqual(159,len(r["per_image_ledger"]))
        self.assertEqual(50,r["input_universe"]["physical_supports"])
        self.assertEqual(17885,r["input_universe"]["samples"])
        self.assertEqual({"train":35,"dev":7,"test":8},r["split"]["groups"])
        self.assertEqual(0,r["rights_approved_image_count"])
        self.assertIsNone(r["heldout_visual_accuracy"])
        self.assertFalse(r["model_trained"])
        self.assertEqual("HARD_BLOCKED",r["production_corpus_status"])

    def test_stable_source_group_holdout_including_rotations(self):
        a={r["image_id"]:r for r in self.report["per_image_ledger"]}
        self.assertEqual(a["003"]["physical_witness_group"],a["004"]["physical_witness_group"])
        self.assertEqual(a["003"]["research_diagnostic_partition"],a["004"]["research_diagnostic_partition"])
        self.assertEqual(self.report,build_preflight(self.p,self.s,self.c))

    def test_every_item_rights_and_benchmark_default_fail_closed(self):
        for row in self.report["per_image_ledger"]:
            self.assertEqual(list(REASONS),row["blocked_reasons"])
            self.assertFalse(row["image_training_admitted"])
            self.assertFalse(row["image_evaluation_admitted"])

    def test_no_guess_from_museum_copyright_or_tpop_ref(self):
        self.assertEqual(159,self.report["metadata_observations"]["images_with_tpop_document_metadata"])
        self.assertEqual(0,self.report["training_admitted_image_count"])

    def test_wrong_original_manuscript_cluster_rejected(self):
        p=copy.deepcopy(self.p);p["004"]["doc_cluster"]=49
        with self.assertRaises(PublicSourceError):build_preflight(p,self.s,self.c)

    def test_missing_item_copyright_rejected(self):
        p=copy.deepcopy(self.p);p["020"]["copyright"]=""
        with self.assertRaises(PublicSourceError):build_preflight(p,self.s,self.c)

    def test_missing_samples_rejected(self):
        s=copy.deepcopy(self.s);del s["00000"]
        with self.assertRaises(PublicSourceError):build_preflight(self.p,s,self.c)

    def test_forged_source_sample_label_rejected(self):
        s=copy.deepcopy(self.s);s["00000"]["class_label"]="forged"
        with self.assertRaises(PublicSourceError):build_preflight(self.p,s,self.c)

    def test_unknown_original_image_rejected(self):
        s=copy.deepcopy(self.s);s["00000"]["document_number"]="999"
        with self.assertRaises(PublicSourceError):build_preflight(self.p,s,self.c)

    def test_bad_original_image_id_rejected(self):
        p=copy.deepcopy(self.p);p["003foo"]=p.pop("003")
        with self.assertRaises(PublicSourceError):build_preflight(p,self.s,self.c)

    def test_boolean_group_id_rejected(self):
        p=copy.deepcopy(self.p);p["020"]["doc_cluster"]=True
        with self.assertRaises(PublicSourceError):build_preflight(p,self.s,self.c)

    def test_publisher_source_hash_must_be_exact_not_only_wellformed(self):
        raw={k:b"{}" for k in SOURCE_SHA256}
        with self.assertRaises(PublicSourceError):verified_source(raw)

    def test_missing_clearance_ref_rejected(self):
        with self.assertRaises(PublicSourceError):validate_positive_clearance(
            self.report,{"protocol":"R033_IMAGE_RIGHTS_CLAIM_PACKET_V1","images":[{"image_id":"003"}]})

    def valid_claim(self):
        return {"protocol":"R033_IMAGE_RIGHTS_CLAIM_PACKET_V1","images":[{
            "image_id":"003", "image_sha256":"a"*64,"original_archive_sha256":"b"*64,
            "permission_url":"https://example.org/rights/003", "permission_reviewed_by":"external-reviewer",
            "benchmark_screen_url":"https://example.org/audit/003","benchmark_reviewed_by":"external-reviewer",
            "intended_track":"NONCOMMERCIAL_RESEARCH_ONLY",
            "benchmark_decision":"INDEPENDENTLY_CLEARED_NO_OVERLAP",
            "permission_decision":"ITEM_REVIEWED_RESEARCH_USE_ONLY"}]}

    def test_even_full_asserted_clearance_does_not_authenticate_or_admit(self):
        result=validate_positive_clearance(self.report,self.valid_claim())
        self.assertEqual(1,len(result["provisional_evidence_packets"]))
        self.assertFalse(result["training_admission"])
        self.assertFalse(result["scientific_certification"])
        self.assertFalse(result["production_admission"])

    def test_commercial_promotion_and_unknown_benchmark_rejected(self):
        c=self.valid_claim();c["images"][0]["intended_track"]="COMMERCIAL"
        with self.assertRaises(PublicSourceError):validate_positive_clearance(self.report,c)
        c=self.valid_claim();c["images"][0]["benchmark_decision"]="UNKNOWN"
        with self.assertRaises(PublicSourceError):validate_positive_clearance(self.report,c)

    def test_duplicate_document_claims_rejected(self):
        c=self.valid_claim();c["images"].append(copy.deepcopy(c["images"][0]))
        with self.assertRaises(PublicSourceError):validate_positive_clearance(self.report,c)


if __name__=="__main__": unittest.main()
