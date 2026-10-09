import copy, struct, subprocess, sys, tempfile, unittest
from pathlib import Path
from tools.alignment import ROOT, read, validate, validate_reference_geometry, validate_w10_line_pair, validate_w14_correspondence, tiff_dimensions

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

class W14PhysicalCorrespondenceTests(unittest.TestCase):
    def setUp(self):
        self.packet=read(ROOT/"data/alignment/w14_physical_line_evidence/plate_xxix_correspondence.json")

    def test_visual_dossier_validates_and_preserves_negative_scientific_result(self):
        self.assertEqual([],validate_w14_correspondence(self.packet))
        finding=self.packet["finding"]
        self.assertEqual("rejected_side_mismatch",finding["candidate_state"])
        self.assertFalse(finding["exact_line_correspondence"])
        self.assertEqual("unresolved",finding["plate_reverse_panel_line_correspondence"])
        self.assertEqual(1,finding["independent_physical_supports_inspected"])
        self.assertEqual(0,finding["independent_expert_reviewed_line_pairs"])
        self.assertFalse(finding["scoreable_gold"])
        self.assertEqual("blocked",finding["training_admission"])

    def test_cli_is_deterministic_and_reports_visual_inspection(self):
        command=[sys.executable,"-m","tools.alignment","validate-w14-dossier"]
        first=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,check=False)
        second=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,check=False)
        self.assertEqual(0,first.returncode,first.stderr)
        self.assertEqual(first.stdout,second.stdout)
        self.assertIn('"plate_visually_inspected": true',first.stdout)
        self.assertIn('"candidate_state": "rejected_side_mismatch"',first.stdout)
        self.assertIn('"expert_reviewed_line_pairs": 0',first.stdout)

    def test_adversarial_identity_and_nearby_line_substitutions_are_rejected(self):
        mutations=(
            (lambda p:p["physical_support"].update(source_object_id="Cat.1883 only"),"support"),
            (lambda p:p["physical_support"].update(image_view="recto"),"image_view"),
            (lambda p:p["candidate_locator"].update(volume_2_plate="XXX"),"volume_2_plate"),
            (lambda p:p["candidate_locator"].update(numbered_item=3),"numbered_item"),
            (lambda p:p["image_asset"].update(figure=6),"figure"),
            (lambda p:p["image_asset"].update(sha256="0"*64),"sha256"),
            (lambda p:p["candidate_locator"].update(original_candidate_bounds=[2800,1680,6500,2020]),"approximate source-image envelope"),
        )
        for mutate,needle in mutations:
            bad=copy.deepcopy(self.packet);mutate(bad)
            with self.subTest(needle=needle):self.assertTrue(any(needle in error for error in validate_w14_correspondence(bad)),validate_w14_correspondence(bad))

    def test_rights_transform_benchmark_and_reviewer_claims_fail_closed(self):
        mutations=(
            (lambda p:p["image_asset"].update(license_evidence_status="unknown"),"license_evidence_status"),
            (lambda p:p["edition_assets"].update(rights_evidence_status="unverified"),"rights_evidence_status"),
            (lambda p:p["edition_assets"].update(volume_2_rights_evidence_url="https://example.org/fake"),"not verified separately"),
            (lambda p:p["inspection"].update(transformations=["mirrored to fit image"]),"transformation"),
            (lambda p:p["finding"].update(benchmark_overlap="clear"),"benchmark_overlap"),
            (lambda p:p["finding"].update(reviewer_id="self"),"reviewer_id"),
            (lambda p:p["finding"].update(independent_expert_reviewed_line_pairs=1),"independent_expert_reviewed_line_pairs"),
            (lambda p:p["finding"].update(scoreable_gold=True),"scoreable_gold"),
            (lambda p:p["finding"].update(training_admission="allowed"),"training_admission"),
        )
        for mutate,needle in mutations:
            bad=copy.deepcopy(self.packet);mutate(bad)
            with self.subTest(needle=needle):self.assertTrue(any(needle in error for error in validate_w14_correspondence(bad)),validate_w14_correspondence(bad))

    def test_render_derivative_and_invalid_visual_geometry_are_rejected(self):
        bad=copy.deepcopy(self.packet);bad["inspection"]["rendered_assets"][1]["sha256"]="f"*64
        self.assertTrue(any("rendered asset sha256 mismatch" in error for error in validate_w14_correspondence(bad)))
        bad=copy.deepcopy(self.packet);bad["inspection"]["visual_regions"][0]["bounds"]=[12,22,12,50]
        self.assertTrue(any("invalid visual-region geometry" in error for error in validate_w14_correspondence(bad)))
        bad=copy.deepcopy(self.packet);bad["image_asset"]["coordinate_asset_sha256"]="a"*64
        self.assertTrue(any("coordinate_asset_sha256" in error for error in validate_w14_correspondence(bad)))
        bad=copy.deepcopy(self.packet);bad["coordinate_comparison"].update(mapping_state="mapped",affine_transform=[1,0,0,1,0,0])
        self.assertTrue(validate_w14_correspondence(bad))

    def test_stdlib_tiff_inspector_reads_dimension_tags_and_rejects_bad_header(self):
        content=b"II"+struct.pack("<HI",42,8)+struct.pack("<H",2)
        content+=struct.pack("<HHII",256,4,1,6595)+struct.pack("<HHII",257,4,1,4710)+struct.pack("<I",0)
        with tempfile.TemporaryDirectory() as folder:
            good=Path(folder)/"fixture.tif";good.write_bytes(content)
            self.assertEqual((6595,4710),tiff_dimensions(good))
            bad=Path(folder)/"bad.tif";bad.write_bytes(b"not-tiff")
            with self.assertRaises(ValueError):tiff_dimensions(bad)

    def test_the_new_dossier_does_not_rewrite_the_historical_candidate(self):
        historical=read(ROOT/"data/alignment/w10_lawful_line_pair/CAT1883-CAT2095-verso-pleyte-line-2.json")
        self.assertEqual("proposed_unreviewed_candidate",historical["line_pair_candidate"]["mapping_state"])
        self.assertIn("could not be visually cross-checked",historical["line_pair_candidate"]["ambiguity_note"])
        self.assertEqual("rejected_side_mismatch",self.packet["finding"]["candidate_state"])

if __name__=="__main__":unittest.main()
