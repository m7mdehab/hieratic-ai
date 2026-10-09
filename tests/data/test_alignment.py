import copy, subprocess, sys, unittest
from tools.alignment import ROOT, read, validate, validate_reference_geometry, validate_w10_line_pair

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

class ReferenceOnlyGeometryTests(unittest.TestCase):
    def setUp(self):
        self.packet=read(ROOT/"data/alignment/w9_rime/CAT1883-CAT2095-recto-reference-geometry.json")
    def test_real_rime_pointer_geometry_validates_but_is_not_line_alignment(self):
        self.assertEqual([],validate_reference_geometry(self.packet))
        self.assertEqual(3,len(self.packet["geometry_regions"]))
        self.assertFalse(self.packet["line_level_alignment"])
        self.assertIsNone(self.packet["data004_annotation_id"])
        self.assertTrue(all(region["gold_scoreable"] is False for region in self.packet["geometry_regions"]))
    def test_source_hash_wrong_support_and_out_of_bounds_are_rejected(self):
        for mutate in (
            lambda packet: packet["source"].update(source_sha256="0"*64),
            lambda packet: packet["source"].update(physical_support_group="Cat.1883 only"),
            lambda packet: packet["geometry_regions"][0].update(source_bounds=[0,0,7000,100]),
        ):
            bad=copy.deepcopy(self.packet);mutate(bad)
            self.assertTrue(validate_reference_geometry(bad))
    def test_cannot_promote_reference_geometry_to_text_or_gold(self):
        bad=copy.deepcopy(self.packet);bad["rights_boundary"]["line_text_included"]=True
        self.assertTrue(validate_reference_geometry(bad))
        bad=copy.deepcopy(self.packet);bad["line_level_alignment"]=True
        self.assertTrue(validate_reference_geometry(bad))
        bad=copy.deepcopy(self.packet);bad["geometry_regions"][0]["gold_scoreable"]=True
        self.assertTrue(validate_reference_geometry(bad))
    def test_duplicate_region_ids_are_rejected(self):
        bad=copy.deepcopy(self.packet);bad["geometry_regions"][1]["region_id"]=bad["geometry_regions"][0]["region_id"]
        self.assertTrue(any("duplicate reference geometry" in error for error in validate_reference_geometry(bad)))

class W10LawfulLinePairTests(unittest.TestCase):
    def setUp(self):
        self.packet=read(ROOT/"data/alignment/w10_lawful_line_pair/CAT1883-CAT2095-verso-pleyte-line-2.json")
    def test_candidate_validates_as_metadata_only_unreviewed_non_gold(self):
        self.assertEqual([],validate_w10_line_pair(self.packet))
        candidate=self.packet["line_pair_candidate"]
        self.assertEqual("unreviewed",candidate["review_state"])
        self.assertFalse(candidate["gold_scoreable"])
        self.assertFalse(self.packet["gold_eligible"])
        self.assertIsNone(self.packet["data004_annotation_id"])
        self.assertEqual("blocked",self.packet["training_admission"])
        self.assertFalse(candidate["line_text_embedded"])
    def test_candidate_cli_is_deterministic(self):
        command=[sys.executable,"-m","tools.alignment","validate-w10-pair"]
        first=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,check=False)
        second=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,check=False)
        self.assertEqual(0,first.returncode,first.stderr)
        self.assertEqual(first.stdout,second.stdout)
    def test_attacker_mutations_to_image_identity_rights_and_geometry_are_rejected(self):
        mutations=(
            lambda p:p["source"]["image"].update(sha256="0"*64),
            lambda p:p["source"].update(view="recto"),
            lambda p:p["source"].update(physical_support_group="Cat.1883 only"),
            lambda p:p["source"]["image"].update(coordinate_asset_sha256="f"*64),
            lambda p:p["source"]["image"].update(license_evidence_status="unknown"),
            lambda p:p["edition"].update(license_evidence_status="unverified"),
            lambda p:p["line_pair_candidate"]["geometry"].update(bounds=[1,2,1,4]),
            lambda p:p["line_pair_candidate"]["geometry"].update(bounds=[-3,2,17,14]),
            lambda p:p["line_pair_candidate"]["geometry"].update(bounds=[1,-2,17,14]),
        )
        for mutate in mutations:
            bad=copy.deepcopy(self.packet);mutate(bad)
            with self.subTest(packet=bad):self.assertTrue(validate_w10_line_pair(bad))
    def test_cross_collection_or_unsupported_edition_line_identity_is_rejected(self):
        for field,value in (("witness_source_object_id","Cat.2044/013"),("numbered_item",3),("printed_page",42),("plate","XXX")):
            bad=copy.deepcopy(self.packet);bad["edition"].update({field:value})
            with self.subTest(field=field):self.assertTrue(validate_w10_line_pair(bad))
    def test_line_pointer_cannot_embed_transcription_or_claim_unknown_annotation(self):
        bad=copy.deepcopy(self.packet);bad["edition"]["line_text_embedded"]=True
        self.assertTrue(validate_w10_line_pair(bad))
        bad=copy.deepcopy(self.packet);bad["data004_annotation_id"]="annotation-made-up"
        self.assertTrue(validate_w10_line_pair(bad))
    def test_ambiguous_geometry_and_attempted_gold_promotion_are_rejected(self):
        bad=copy.deepcopy(self.packet);bad["line_pair_candidate"]["geometry"]["bounds"]=[2800,1690,2800,2020]
        self.assertTrue(validate_w10_line_pair(bad))
        for field,value in (("mapping_state","verified"),("review_state","reviewed"),("reviewer_id","self-appointed"),("gold_scoreable",True)):
            bad=copy.deepcopy(self.packet);bad["line_pair_candidate"][field]=value
            with self.subTest(field=field):self.assertTrue(validate_w10_line_pair(bad))
        bad=copy.deepcopy(self.packet);bad["gold_eligible"]=True
        self.assertTrue(validate_w10_line_pair(bad))
    def test_unresolved_plate_and_geometry_ambiguity_is_disclosed(self):
        note=self.packet["line_pair_candidate"]["ambiguity_note"]
        self.assertIn("Plate XXIX could not be visually cross-checked",note)
        self.assertIn("exact line correspondence remains unresolved",note)
        self.assertIn("not independently reviewed",self.packet["line_pair_candidate"]["geometry"]["basis"])

if __name__=="__main__":unittest.main()
