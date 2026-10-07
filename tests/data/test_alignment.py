import copy, unittest
from tools.alignment import ROOT, read, validate

class AlignmentTests(unittest.TestCase):
    def setUp(self):
        self.alignment=read(ROOT/"data/alignment/examples/synthetic.yaml")
        self.acquisition=read(ROOT/"data/alignment/examples/acquisition.synthetic.yaml")
        self.annotation=read(ROOT/"data/examples/annotation_minimal.yaml")
        self.registry=read(ROOT/"data/sources/registry.yaml")
    def test_synthetic_linked_fixture_valid_and_unresolved_not_score_eligible(self):
        errors,eligible=validate(self.alignment,self.acquisition,self.annotation,self.registry)
        self.assertEqual([],errors);self.assertEqual({"alignment-line-1":False},eligible)
    def test_reviewed_resolved_synthetic_fixture_remains_ineligible(self):
        a=copy.deepcopy(self.alignment)["alignments"][0];a.update(status="resolved",confidence=0.9,review_state="reviewed",reviewer_id="expert-1")
        manifest=copy.deepcopy(self.alignment);manifest["alignments"]=[a]
        errors,eligible=validate(manifest,self.acquisition,self.annotation,self.registry)
        self.assertEqual([],errors);self.assertFalse(eligible["alignment-line-1"])
    def test_ambiguous_target_is_not_score_eligible(self):
        ann=copy.deepcopy(self.annotation);layer=ann["lines"][0]["grapheme_sequence"];layer["gold_status"]="uncertain_with_alternatives";layer["values"].append({"value_id":"alt-1","value":["SYNTH-ALT"],"confidence":None,"equivalent_to_selected":False,"evidence_ref":None});layer["selected_value_id"]=None
        a=copy.deepcopy(self.alignment);a["alignments"][0].update(status="resolved",confidence=.9,review_state="adjudicated",reviewer_id="expert-1")
        errors,eligible=validate(a,self.acquisition,ann,self.registry)
        self.assertEqual([],errors);self.assertFalse(eligible["alignment-line-1"])
    def test_broken_page_region_and_target_references_rejected(self):
        for field,value,needle in (("page_id","ghost-page","unknown page_id"),("region_ids",["ghost-region"],"broken region reference"),("targets",[{"target_type":"line","target_id":"ghost-line"}],"unknown DATA-004 line_id")):
            bad=copy.deepcopy(self.alignment);bad["alignments"][0][field]=value
            errors,_=validate(bad,self.acquisition,self.annotation,self.registry)
            self.assertTrue(any(needle in e for e in errors),errors)
    def test_cross_page_region_and_contradictory_resolved_mapping_rejected(self):
        ann=copy.deepcopy(self.annotation);ann["pages"].append({"page_id":"page-2","coordinate_system":"normalized_0_1","dimensions":None,"orientation":"unknown","regions":[{"region_id":"region-2","region_type":"text","geometry":None,"parent_region_id":None,"child_region_ids":[]}],"reading_order":["region-2"]})
        bad=copy.deepcopy(self.alignment);bad["alignments"][0]["region_ids"]=["region-2"]
        errors,_=validate(bad,self.acquisition,ann,self.registry);self.assertTrue(any("different page" in e for e in errors))
        bad=copy.deepcopy(self.alignment);one=bad["alignments"][0];one.update(status="resolved",review_state="reviewed",reviewer_id="r1",confidence=.8)
        two=copy.deepcopy(one);two.update(alignment_id="alignment-2",targets=[{"target_type":"line","target_id":"line-1"},{"target_type":"line","target_id":"line-1"}])
        bad["alignments"].append(two)
        errors,_=validate(bad,self.acquisition,self.annotation,self.registry);self.assertTrue(any("contradictory resolved mapping" in e for e in errors))
    def test_dependency_cycles_and_benchmark_inputs_rejected(self):
        bad=copy.deepcopy(self.alignment);first=bad["alignments"][0];first["depends_on_alignment_ids"]=["alignment-2"]
        second=copy.deepcopy(first);second.update(alignment_id="alignment-2",depends_on_alignment_ids=[first["alignment_id"]]);bad["alignments"].append(second)
        errors,_=validate(bad,self.acquisition,self.annotation,self.registry);self.assertTrue(any("cycle" in e for e in errors))
        acq=copy.deepcopy(self.acquisition);acq["items"][0]["benchmark_quarantine"]=True
        errors,_=validate(self.alignment,acq,self.annotation,self.registry);self.assertTrue(any("benchmark-quarantined" in e for e in errors))
        acq=copy.deepcopy(self.acquisition);acq["items"][0]["source_id"]="SRC-HIERATICBENCH"
        errors,_=validate(self.alignment,acq,self.annotation,self.registry);self.assertTrue(any("benchmark-contaminated" in e for e in errors))
    def test_empty_targets_require_explicit_gap_like_relation(self):
        bad=copy.deepcopy(self.alignment);bad["alignments"][0]["targets"]=[];bad["alignments"][0]["relation"]="one_to_one"
        errors,_=validate(bad,self.acquisition,self.annotation,self.registry);self.assertTrue(any("empty target requires" in e for e in errors))
        bad=copy.deepcopy(self.alignment);bad["alignments"][0].update(region_ids=[],targets=[],relation="gap")
        errors,_=validate(bad,self.acquisition,self.annotation,self.registry);self.assertTrue(any("unmatched DATA-004 regions" in e for e in errors))
    def test_unresolved_entry_cannot_hide_conflicting_resolved_mapping(self):
        bad=copy.deepcopy(self.alignment)
        first=bad["alignments"][0]
        first.update(status="resolved",review_state="reviewed",reviewer_id="r1",confidence=.9)
        middle=copy.deepcopy(first);middle.update(alignment_id="alignment-middle",status="unresolved")
        last=copy.deepcopy(first);last.update(alignment_id="alignment-last",relation="one_to_many",
            targets=first["targets"]+[{"target_type":"line","target_id":"line-1"}])
        bad["alignments"]=[first,middle,last]
        errors,_=validate(bad,self.acquisition,self.annotation,self.registry)
        self.assertTrue(any("contradictory resolved mapping" in e for e in errors),errors)

    def test_synthetic_fixture_is_never_gold_score_eligible(self):
        bad=copy.deepcopy(self.alignment)
        bad["alignments"][0].update(status="resolved",review_state="adjudicated",reviewer_id="expert",confidence=.99)
        errors,eligible=validate(bad,self.acquisition,self.annotation,self.registry)
        self.assertEqual([],errors)
        self.assertFalse(any(eligible.values()))

    def test_relation_cardinality_and_hypothesis_references_are_enforced(self):
        bad=copy.deepcopy(self.alignment);bad["alignments"][0]["relation"]="one_to_many"
        errors,_=validate(bad,self.acquisition,self.annotation,self.registry);self.assertTrue(any("cardinality contradicts" in e for e in errors))
        bad=copy.deepcopy(self.alignment);bad["alignments"][0]["hypotheses"]=[{"hypothesis_id":"h1","targets":[{"target_type":"line","target_id":"ghost-line"}],"confidence":.3,"evidence_ref":"synthetic:alternative"}]
        errors,_=validate(bad,self.acquisition,self.annotation,self.registry);self.assertTrue(any("broken DATA-004 hypothesis reference" in e for e in errors))

if __name__=="__main__":unittest.main()
