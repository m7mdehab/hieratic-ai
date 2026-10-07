import copy, unittest
from pathlib import Path
from tools.sign_mappings import ROOT, load, validate

class SignMappingTests(unittest.TestCase):
    def setUp(self): self.payload=load(ROOT/"data/mappings/examples/synthetic.yaml")
    def test_synthetic_unresolved_record_is_valid_and_keeps_layers_separate(self):
        self.assertEqual([],validate(self.payload))
        rec=self.payload["records"][0]
        self.assertIsNone(rec["observed_hieratic"]["value"])
        self.assertIsNone(rec["hieroglyphic_correspondence"]["value"])
        self.assertIsNone(rec["transliteration_value"]["value"])
    def test_duplicate_identity_and_variant_ids_rejected(self):
        bad=copy.deepcopy(self.payload);bad["records"].append(copy.deepcopy(bad["records"][0]))
        self.assertTrue(any("duplicate identity ID" in e for e in validate(bad)))
        bad=copy.deepcopy(self.payload);bad["records"][0]["variants"]=[{"variant_id":"v1","variant_status":"candidate","description":"synthetic","provenance":[]},{"variant_id":"v1","variant_status":"candidate","description":"synthetic","provenance":[]}]
        self.assertTrue(any("duplicate variant ID" in e for e in validate(bad)))
    def test_supported_claim_requires_citation_and_reference_integrity(self):
        bad=copy.deepcopy(self.payload);claim=bad["records"][0]["observed_hieratic"];claim.update(value="asserted",status="supported")
        self.assertTrue(any("supported claim requires" in e for e in validate(bad)))
        bad=copy.deepcopy(self.payload);bad["relations"]=[{"relation_id":"r1","from_identity_id":"missing","to_identity_id":"SYNTHETIC-OBS-001","relation_type":"variant_of","status":"proposed","confidence":None,"provenance":[]}]
        self.assertTrue(any("unknown identity" in e for e in validate(bad)))
    def test_supported_historical_claim_requires_verified_metadata_not_just_text(self):
        bad=copy.deepcopy(self.payload)
        claim=bad["records"][0]["observed_hieratic"]
        claim.update(value="synthetic-not-history",status="supported",citations=[{
            "citation_id":"synthetic-citation-1","reference":"fictional-book","claim_scope":"synthetic-only",
            "verified_metadata":False
        }])
        self.assertTrue(any("verified citation metadata" in e for e in validate(bad)))
        claim["citations"][0]["verified_metadata"]=True
        self.assertEqual([],validate(bad))

    def test_accepted_variant_must_have_verified_provenance(self):
        bad=copy.deepcopy(self.payload)
        bad["records"][0]["variants"]=[{"variant_id":"synthetic-v-1","variant_status":"accepted_variant","description":"synthetic","provenance":[]}]
        self.assertTrue(any("accepted variant requires verified provenance" in e for e in validate(bad)))

    def test_hierarchy_cycles_and_duplicate_edges_rejected(self):
        bad=copy.deepcopy(self.payload);bad["records"].append(copy.deepcopy(bad["records"][0]));bad["records"][1]["identity_id"]="SYNTHETIC-OBS-002"
        rel=lambda rid,a,b:{"relation_id":rid,"from_identity_id":a,"to_identity_id":b,"relation_type":"subclass_of","status":"proposed","confidence":None,"provenance":[]}
        bad["relations"]=[rel("r1","SYNTHETIC-OBS-001","SYNTHETIC-OBS-002"),rel("r2","SYNTHETIC-OBS-002","SYNTHETIC-OBS-001")]
        self.assertTrue(any("cycle" in e for e in validate(bad)))
        bad["relations"].append(rel("r3","SYNTHETIC-OBS-001","SYNTHETIC-OBS-002"))
        self.assertTrue(any("duplicate relation edge" in e for e in validate(bad)))

if __name__=="__main__":unittest.main()
