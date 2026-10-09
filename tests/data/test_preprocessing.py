import hashlib, json, os, shutil, socket, struct, tempfile, threading, unittest
from unittest import mock
from pathlib import Path
import yaml
from tools import preprocessing as pp
from tools.preprocessing import ROOT, _read, run, validate_request, transform_image, decode_ppm

FIXTURE = ROOT / "data/preprocessing/fixtures/synthetic-2x2.ppm"

class PreprocessingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.fixture = self.base / "synthetic.ppm"
        shutil.copyfile(FIXTURE, self.fixture)
        self.item = {"item_id":"synthetic-page-1", "acquisition_record_id":"synthetic:fixture-v1", "source_id":"SRC-REPO-SYNTHETIC", "source_object_id":"fixture:page-1", "intended_use":"training", "asset_path":"synthetic.ppm", "input_sha256":hashlib.sha256(self.fixture.read_bytes()).hexdigest(), "rights_class":"OPEN-PD", "training_use":"allowed", "benchmark_quarantine":False, "benchmark_overlap_review":"clear", "text_input":"A\u030a", "operations":[{"kind":"orient","orientation":"rotate_90_clockwise"},{"kind":"convert_mode","mode":"RGBA"},{"kind":"resize","width":4,"height":4,"fit":"contain","resampling":"nearest"},{"kind":"crop","box":[0,0,4,4],"coordinate_system":"pixel_origin_top_left"},{"kind":"text_normalize","text_profile":"unicode-nfc","text_profile_version":"1.0.0"}]}
        self.payload = {"schema_version":"1.0.0","profile_id":"synthetic-v1","acquisition_manifest_id":"synthetic:fixture-v1","items":[self.item]}
    def tearDown(self): self.temp.cleanup()
    def test_synthetic_fixture_runs_byte_and_metadata_deterministically(self):
        errors=validate_request(self.payload, _read(ROOT/"data/sources/registry.yaml"), self.base); self.assertEqual([], errors)
        first=run_from_payload(self.payload, self.base, self.base/"one")
        second=run_from_payload(self.payload, self.base, self.base/"two")
        a=(self.base/"one/synthetic-page-1.png").read_bytes(); b=(self.base/"two/synthetic-page-1.png").read_bytes()
        self.assertEqual(a,b); self.assertEqual(hashlib.sha256(a).hexdigest(), first["items"][0]["output_sha256"])
        self.assertEqual(first, second); self.assertEqual("Å", first["items"][0]["normalized_text"])
        self.assertEqual("A\u030a", first["items"][0]["text_input"])
        self.assertEqual("6c075549728dc4137a7bbeb42ea1419a9965d54daeba7964622b70709970bd7b", first["items"][0]["output_sha256"])
        self.assertEqual("ds-c7d7d6e06cc3dc5eaab1a76e6c5f81cf313a0d4b177da4d483cff2f85670b21b", first["dataset_version_id"])
        decoded_png,_=transform_image(self.base/"one/synthetic-page-1.png",[]);self.assertEqual(a,decoded_png)
        self.assertEqual((self.base/"one/dataset-manifest.json").read_bytes(), (self.base/"two/dataset-manifest.json").read_bytes())
    def test_unknown_source_and_quarantine_are_rejected(self):
        registry=_read(ROOT/"data/sources/registry.yaml")
        bad=json.loads(json.dumps(self.payload)); bad["items"][0]["source_id"]="SRC-NOT-IN-REGISTRY"
        self.assertTrue(any("unidentified source_id" in e for e in validate_request(bad, registry, self.base)))
        bad=json.loads(json.dumps(self.payload)); bad["items"][0]["benchmark_quarantine"]=True
        self.assertTrue(validate_request(bad, registry, self.base))
    def test_real_item_without_acquisition_manifest_fails_closed(self):
        registry=_read(ROOT/"data/sources/registry.yaml")
        bad=json.loads(json.dumps(self.payload));bad["items"][0].update(source_id="SRC-HPDB",acquisition_record_id="pretend-clearance",rights_class="OPEN-BY")
        bad["acquisition_manifest_id"]="claimed-real-acquisition"
        self.assertTrue(any("require the referenced DATA-002" in e for e in validate_request(bad,registry,self.base)))
    def test_hash_mismatch_and_uncleared_overlap_are_rejected(self):
        registry=_read(ROOT/"data/sources/registry.yaml")
        bad=json.loads(json.dumps(self.payload)); bad["items"][0]["input_sha256"]="0"*64
        self.assertTrue(any("SHA-256 mismatch" in e for e in validate_request(bad, registry, self.base)))
        bad=json.loads(json.dumps(self.payload)); bad["items"][0]["benchmark_overlap_review"]="unreviewed"
        self.assertTrue(any("overlap is not cleared" in e for e in validate_request(bad, registry, self.base)))
    def test_missing_intended_use_and_path_escape_are_rejected(self):
        registry=_read(ROOT/"data/sources/registry.yaml")
        bad=json.loads(json.dumps(self.payload));del bad["items"][0]["intended_use"]
        self.assertTrue(any("intended_use" in e for e in validate_request(bad,registry,self.base)))
        bad=json.loads(json.dumps(self.payload));bad["items"][0]["asset_path"]="../outside.ppm"
        self.assertTrue(any("escapes the manifest directory" in e for e in validate_request(bad,registry,self.base)))
        bad=json.loads(json.dumps(self.payload));bad["items"][0]["asset_path"]=str(self.fixture.resolve())
        self.assertTrue(any("escapes the manifest directory" in e for e in validate_request(bad,registry,self.base)))

    def test_binary_ppm_scaling_and_png_corruption_are_checked(self):
        binary=self.base/"tiny.ppm";binary.write_bytes(b"P6\r\n2 1\r\n15\r\n"+bytes([15,0,0,0,8,15]))
        image=decode_ppm(binary);self.assertEqual("RGB",image.mode);self.assertEqual((255,0,0),image.at(0,0));self.assertEqual((0,136,255),image.at(1,0))
        png, _=transform_image(FIXTURE,[]);bad=self.base/"bad.png";bad.write_bytes(png[:-5]+b"xxxxx")
        with self.assertRaises(ValueError):transform_image(bad,[])

    def test_met_readiness_is_offline_metadata_only_and_fails_closed(self):
        with mock.patch.object(socket,"create_connection",side_effect=AssertionError("network must not be used")):
            result=pp.assess_met_original_asset_readiness(561392,"primaryImage")
        self.assertFalse(result["network_used"]);self.assertFalse(result["image_bytes_read"])
        self.assertEqual(9,result["candidate_count"]);self.assertTrue(result["all_candidates_no_go"])
        selected=result["selected_candidate"]
        self.assertEqual("https://images.metmuseum.org/CRDImages/eg/original/LC-09_184_751_EGDP035862.jpg",selected["exact_image_url"])
        self.assertIsNone(selected["image_byte_sha256"]);self.assertFalse(selected["download_performed"])
        self.assertEqual("NOT_RECORDED",result["retrieval_receipt_template"]["status"])
        self.assertTrue(selected["blockers"])

    def test_met_561345_multiaccession_filename_is_warning_not_identity_decision(self):
        result=pp.assess_met_original_asset_readiness(561345,"primaryImage")
        selected=result["selected_candidate"]
        self.assertIn("second accession-like identifier",selected["source_identity_warning"])
        self.assertEqual("09.184.703",selected["accession"])
        self.assertEqual("NO_GO",selected["go_no_go"])
        self.assertEqual(2,len(selected["available_original_views"]))
        self.assertIn("aliases, editions",selected["r021_direct_collision_screen"])
        self.assertIn("Abbott and Hearst",result["r021_global_collision_warning"])

    def test_forged_or_mutated_met_packet_image_url_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            shutil.copytree(ROOT/"data/acquisition/met/objects",root/"data/acquisition/met/objects")
            shutil.copytree(ROOT/"data/preprocessing",root/"data/preprocessing")
            shutil.copytree(ROOT/"data/acquisition/met",root/"data/acquisition/met-copy",ignore=shutil.ignore_patterns("objects"))
            shutil.copy2(ROOT/"data/acquisition/met/metadata_packet.schema.json",root/"data/acquisition/met/metadata_packet.schema.json")
            shutil.copy2(ROOT/"data/acquisition/met/r017_reconciliation.json",root/"data/acquisition/met/r017_reconciliation.json")
            original_root,original_schema,original_lock=pp.ROOT,pp.MET_PACKET_SCHEMA,pp.MET_REFERENCE_LOCK
            try:
                pp.ROOT=root;pp.MET_PACKET_SCHEMA=root/"data/acquisition/met/metadata_packet.schema.json";pp.MET_REFERENCE_LOCK=root/"data/preprocessing/met_w6_source_lock.json"
                packet_path=root/"data/acquisition/met/objects/561392.json"
                pristine=json.loads(packet_path.read_text(encoding="utf-8"))
                mutations=(
                    ("altered CDN URL",lambda value:value["observed"].update(primaryImage="https://images.metmuseum.org/CRDImages/eg/original/attacker.jpg"),"URL metadata differs"),
                    ("altered identity",lambda value:value["observed"].update(objectID=1),"object ID mismatch"),
                    ("revoked public-domain flag",lambda value:value["observed"].update(isPublicDomain=False),"public-domain flag is not true"),
                    ("submitter-created production clearance",lambda value:value.update(rights_assessment={**value["rights_assessment"],"training_admission":"ALLOWED"}),"BLOCKED_METADATA_ONLY"),
                )
                for label,mutate,error in mutations:
                    with self.subTest(label=label):
                        altered=json.loads(json.dumps(pristine));mutate(altered)
                        packet_path.write_text(json.dumps(altered),encoding="utf-8")
                        with self.assertRaisesRegex(ValueError,error):pp.assess_met_original_asset_readiness(561392,"primaryImage")
                packet_path.write_text(json.dumps(pristine),encoding="utf-8")
                with self.assertRaisesRegex(ValueError,"view must be"):
                    pp.assess_met_original_asset_readiness(561392,"primaryImageSmall")
            finally:
                pp.ROOT,pp.MET_PACKET_SCHEMA,pp.MET_REFERENCE_LOCK=original_root,original_schema,original_lock

    def test_exact_view_selector_rejects_small_or_nonexistent_alternate_urls(self):
        with self.assertRaisesRegex(ValueError,"view must be"):
            pp.assess_met_original_asset_readiness(561392,"primaryImageSmall")
        with self.assertRaisesRegex(ValueError,"does not exist"):
            pp.assess_met_original_asset_readiness(561361,"additionalImages:0")

    def test_original_image_header_inspection_checks_hash_magic_dimensions_and_mime(self):
        png,_=transform_image(FIXTURE,[])
        record=pp.inspect_original_image_bytes(png,expected_sha256=hashlib.sha256(png).hexdigest(),declared_mime="image/png")
        self.assertEqual("image/png",record["mime_type_from_magic"]);self.assertEqual([2,2],record["pixel_dimensions"])
        self.assertFalse(record["pixel_decode_verified"]);self.assertFalse(record["visual_content_reviewed"])
        with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):
            pp.inspect_original_image_bytes(png,expected_sha256="0"*64)
        with self.assertRaisesRegex(ValueError,"MIME"):
            pp.inspect_original_image_bytes(png,declared_mime="image/jpeg")
        with self.assertRaisesRegex(ValueError,"magic"):
            pp.inspect_original_image_bytes(b"not an image")

    def test_bounded_jpeg_header_reports_exif_without_claiming_pixel_decode(self):
        # Repository-authored marker fixture; it is a metadata test, not a photograph.
        tiff=b"II"+(42).to_bytes(2,"little")+(8).to_bytes(4,"little")+(1).to_bytes(2,"little")
        tiff+=(0x0112).to_bytes(2,"little")+(3).to_bytes(2,"little")+(1).to_bytes(4,"little")+(6).to_bytes(2,"little")+b"\x00\x00"+b"\x00"*4
        exif=b"Exif\x00\x00"+tiff;app1=b"\xff\xe1"+(len(exif)+2).to_bytes(2,"big")+exif
        sof=bytes([8])+(10).to_bytes(2,"big")+(20).to_bytes(2,"big")+bytes([3,1,0x11,0,2,0x11,0,3,0x11,0])
        jpeg=b"\xff\xd8"+app1+b"\xff\xc0"+(len(sof)+2).to_bytes(2,"big")+sof
        result=pp.inspect_original_image_bytes(jpeg,declared_mime="image/jpeg")
        self.assertEqual("image/jpeg",result["mime_type_from_magic"]);self.assertEqual([20,10],result["pixel_dimensions"])
        self.assertEqual(6,result["exif_orientation"]);self.assertFalse(result["pixel_decode_verified"])

    def test_oversized_and_truncated_image_headers_fail_before_decode(self):
        with mock.patch.object(pp,"MAX_INPUT_BYTES",4):
            with self.assertRaisesRegex(ValueError,"byte-size"):
                pp.inspect_original_image_bytes(b"12345")
        oversized_ihdr=struct.pack(">IIBBBBB",pp.MAX_IMAGE_PIXELS+1,1,8,6,0,0,0)
        bomb=b"\x89PNG\r\n\x1a\n"+pp._png_chunk(b"IHDR",oversized_ihdr)+pp._png_chunk(b"IDAT",b"\x78\x01\x03\x00\x00\x00\x00\x01")+pp._png_chunk(b"IEND",b"")
        with self.assertRaisesRegex(ValueError,"pixel dimensions exceed"):
            pp.inspect_original_image_bytes(bomb)
        with self.assertRaisesRegex(ValueError,"dimensions are missing"):
            pp.inspect_original_image_bytes(b"\xff\xd8\xff\xd9")

    def test_png_decompressor_rejects_unbounded_dimensions(self):
        ihdr=struct.pack(">IIBBBBB",pp.MAX_IMAGE_PIXELS+1,1,8,6,0,0,0)
        png=b"\x89PNG\r\n\x1a\n"+pp._png_chunk(b"IHDR",ihdr)+pp._png_chunk(b"IDAT",b"\x78\x01\x03\x00\x00\x00\x00\x01")+pp._png_chunk(b"IEND",b"")
        path=self.base/"dimension-bomb.png";path.write_bytes(png)
        with self.assertRaisesRegex(ValueError,"pixel dimensions exceed"):
            pp.decode_png(path)

    def test_readiness_writer_is_concurrent_no_clobber_and_cleans_failure(self):
        if os.name!="posix":self.skipTest("secure dirfd publisher is POSIX-only; unsupported hosts fail closed")
        with tempfile.TemporaryDirectory(dir=ROOT/"data/preprocessing") as directory:
            output=Path(directory)/"assessment.json";payload={"winner":"one"};outcomes=[]
            def writer(value):
                try:pp._publish_readiness_output(output,{"winner":value});outcomes.append("published")
                except ValueError:outcomes.append("refused")
            workers=[threading.Thread(target=writer,args=(value,)) for value in ("one","two")]
            for worker in workers:worker.start()
            for worker in workers:worker.join()
            self.assertCountEqual(["published","refused"],outcomes)
            self.assertIn(json.loads(output.read_text(encoding="utf-8"))["winner"],{"one","two"})
            failed=Path(directory)/"failed.json"
            with mock.patch.object(pp.os,"link",side_effect=OSError("synthetic publish failure")):
                with self.assertRaisesRegex(ValueError,"atomically published"):
                    pp._publish_readiness_output(failed,payload)
            self.assertFalse(failed.exists());self.assertEqual([],list(Path(directory).glob(".readiness-*.tmp")))

    def test_readiness_writer_detects_late_parent_swap_and_rolls_back(self):
        if os.name!="posix":self.skipTest("dirfd publication and symlink swaps require POSIX")
        with tempfile.TemporaryDirectory(dir=ROOT/"data/preprocessing") as directory:
            base=Path(directory)
            parent=base/"validated-parent"; parent.mkdir()
            decoy=base/"decoy"; decoy.mkdir()
            moved=base/"parent-moved"
            output=parent/"result.json"
            original_link=os.link
            swaps=[]
            def late_parent_swap(src,dst,**kwargs):
                parent.rename(moved)
                parent.symlink_to(decoy,target_is_directory=True)
                swaps.append(True)
                return original_link(src,dst,**kwargs)
            try:
                with mock.patch.object(pp.os,"link",side_effect=late_parent_swap):
                    with self.assertRaisesRegex(ValueError,"parent moved"):
                        pp._publish_readiness_output(output,{"source":"trusted"})
                self.assertTrue(swaps)
                self.assertFalse((decoy/"result.json").exists(),"must not write to replacement destination")
                self.assertFalse((moved/"result.json").exists(),"must roll back a renamed parent commit")
                self.assertFalse(list(moved.glob(".readiness-*.tmp")),"must clean private staging")
            finally:
                if parent.is_symlink():parent.unlink()
                if moved.exists():moved.rename(parent)

    def test_readiness_writer_rejects_path_escape_and_symlink(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"data/preprocessing") as directory:
            folder=Path(directory);target=folder/"real";target.mkdir();link=folder/"link"
            with self.assertRaisesRegex(ValueError,"under data/preprocessing"):
                pp._publish_readiness_output(ROOT/"tools/outside.json",{})
            try:link.symlink_to(target,target_is_directory=True)
            except (OSError,NotImplementedError):self.skipTest("symlinks unavailable on this host")
            with self.assertRaisesRegex(ValueError,"symlink"):
                pp._publish_readiness_output(link/"escape.json",{})


class W8PrivateImageInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.vault=self.root/"vault";self.vault.mkdir()
        self.env=mock.patch.dict(os.environ,{"LOCALAPPDATA":str(self.root)},clear=False);self.env.start()
        self.suffix=mock.patch.object(pp,"W8_VAULT_SUFFIX",Path("vault"));self.suffix.start()
        self.addCleanup(self.suffix.stop);self.addCleanup(self.env.stop);self.addCleanup(self.temp.cleanup)
        self.profile=pp._w8_load_profile()
        self.data=b"synthetic private-evidence contract fixture"
        source=self.profile["source_lock"].copy();source.update({"file_sha256":hashlib.sha256(self.data).hexdigest(),"file_sha1":hashlib.sha1(self.data).hexdigest(),"byte_size":len(self.data)})
        self.profile["source_lock"]=source
        self.image=self.vault/"CAT2044-013-commons-original.jpg";self.image.write_bytes(self.data)
        self.evidence=self.vault/"CAT2044.json"
        self.record={"candidate_id":"CAT2044","source_object_id":"Cat.2044/013","physical_support_group":"Cat.2044/013","commons_pageid":source["commons_pageid"],"commons_api_response_sha256":source["commons_api_response_sha256"],"source_sha256":source["file_sha256"],"source_byte_size":len(self.data),"commons_file_sha1":source["file_sha1"],"declared_dimensions":source["dimensions"],"mime_type":"image/jpeg","exact_original_file_url":"https://upload.wikimedia.org"+source["exact_original_path"]+"?utm_source=commons.wikimedia.org","commons_file_page_url":source["exact_file_page"],"commons_file_revision_url":source["exact_file_revision"],"license":{"identifier":"CC0","url":source["license_url"],"file_credit_observation":"Museo Egizio","official_museum_policy_url":source["official_museum_policy_url"],"papyrus_database_image_policy_url":source["papyrus_database_image_policy_url"]},"use_boundary":{"source_registry_status":"NOT_REGISTERED","benchmark_overlap_status":"UNRESOLVED_QUARANTINED","training_admission":"BLOCKED","development_admission":"BLOCKED","evaluation_admission":"NOT_AUTHORIZED","gold_or_transcription":"NONE"}}
        self.evidence.write_text(json.dumps(self.record),encoding="utf-8")

    def test_exact_source_evidence_is_bound_and_never_admitted(self):
        data,evidence,source,evidence_sha=pp._w8_verify_inputs(self.image,self.evidence,self.profile)
        self.assertEqual(self.data,data);self.assertEqual("Cat.2044/013",source["source_object_id"])
        self.assertEqual("NOT_REGISTERED",evidence["use_boundary"]["source_registry_status"])
        self.assertEqual(hashlib.sha256(self.evidence.read_bytes()).hexdigest(),evidence_sha)

    def test_changed_image_hash_wrong_support_license_or_promotion_refuses(self):
        self.image.write_bytes(self.data+b"tamper")
        with self.assertRaisesRegex(ValueError,"hash/size"):
            pp._w8_verify_inputs(self.image,self.evidence,self.profile)
        self.image.write_bytes(self.data)
        for field,value,pattern in (("source_object_id","Cat.9999","source lock"),("physical_support_group","another-support","source lock"),("exact_original_file_url","https://attacker.invalid/upload.wikimedia.org"+self.profile["source_lock"]["exact_original_path"],"source lock")):
            bad=dict(self.record);bad[field]=value;self.evidence.write_text(json.dumps(bad),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,pattern):pp._w8_verify_inputs(self.image,self.evidence,self.profile)
        for field,value in (("commons_api_response_sha256","0"*64),("commons_pageid",1)):
            bad=dict(self.record);bad[field]=value;self.evidence.write_text(json.dumps(bad),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"source lock"):pp._w8_verify_inputs(self.image,self.evidence,self.profile)
        for field,value in (("identifier","CC-BY"),("url","https://example.invalid/license")):
            bad=json.loads(json.dumps(self.record));bad["license"][field]=value;self.evidence.write_text(json.dumps(bad),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"license evidence"):pp._w8_verify_inputs(self.image,self.evidence,self.profile)
        bad=json.loads(json.dumps(self.record));bad["license"]["official_museum_policy_url"]="https://attacker.invalid/";self.evidence.write_text(json.dumps(bad),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"license evidence"):pp._w8_verify_inputs(self.image,self.evidence,self.profile)
        for field,value in (("benchmark_overlap_status","CLEAR"),("training_admission","ALLOWED"),("gold_or_transcription","VERIFIED")):
            bad=json.loads(json.dumps(self.record));bad["use_boundary"][field]=value;self.evidence.write_text(json.dumps(bad),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"promoted"):pp._w8_verify_inputs(self.image,self.evidence,self.profile)

    def test_evidence_and_image_must_be_inside_vault_without_symlinks(self):
        outside=self.root/"CAT2044-013-commons-original.jpg";outside.write_bytes(self.data)
        with self.assertRaisesRegex(ValueError,"inside the protected"):
            pp._w8_verify_inputs(outside,self.evidence,self.profile)
        link=self.vault/"CAT2044.json.link"
        try:link.symlink_to(self.evidence)
        except (OSError,NotImplementedError):self.skipTest("symlink creation unavailable")
        with self.assertRaisesRegex(ValueError,"symlink"):
            pp._w8_verify_inputs(self.image,link,self.profile)

    def test_locked_profile_detects_parameter_mutation(self):
        payload=json.loads(pp.W8_PROFILE.read_text(encoding="utf-8"));payload["limits"]["analysis_downsample_factor"]=1
        profile_path=self.root/"altered-profile.json";profile_path.write_text(json.dumps(payload),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"profile hash"):
            pp._w8_load_profile(profile_path)

    def test_locked_profile_hash_is_stable_across_checkout_line_endings(self):
        profile_path=self.root/"crlf-profile.json"
        normalized=pp.W8_PROFILE.read_bytes().replace(b"\r\n",b"\n")
        profile_path.write_bytes(normalized.replace(b"\n",b"\r\n"))
        loaded=pp._w8_load_profile(profile_path)
        self.assertEqual(loaded["profile_id"],"w8-cat2044-unlabelled-image-inspection")
        self.assertEqual(loaded["source_lock"]["file_sha256"],pp.W8_EXPECTED_SHA256)

    def test_pixel_region_and_line_proposals_are_synthetic_and_non_gold(self):
        try:from PIL import Image,ImageDraw
        except ImportError:self.skipTest("Pillow is an optional local-only W8 JPEG runtime")
        image=Image.new("RGB",(1600,1280),(245,245,245));draw=ImageDraw.Draw(image)
        draw.rectangle((80,100,1510,1180),fill=(155,112,78))
        for y in (450,650,850):draw.line((220,y,1380,y+8),fill=(45,35,28),width=15)
        analysis=pp._w8_pixel_analysis(image,pp._w8_load_profile())
        self.assertEqual(analysis,pp._w8_pixel_analysis(image,pp._w8_load_profile()))
        self.assertGreater(len(analysis["candidate_material_regions"]),0)
        self.assertGreater(len(analysis["candidate_line_regions"]),0)
        self.assertTrue(all(line["status"].endswith("not_transcription_gold") for line in analysis["candidate_line_regions"]))
        self.assertTrue(all(line["reading_status"]=="UNKNOWN_UNREVIEWED" for line in analysis["candidate_line_regions"]))
        self.assertIn("coordinate_transform_source_to_analysis",analysis)

    def test_decoder_refuses_oversize_and_corrupt_bytes(self):
        with self.assertRaisesRegex(ValueError,"byte bound"):
            pp._w8_decode(b"x"*(pp.W8_MAX_BYTES+1),self.profile["source_lock"])
        with self.assertRaisesRegex(ValueError,"missing"):
            pp._w8_decode(b"bad jpeg",self.profile["source_lock"])
        height,width=6000,6000
        sof=b"\xff\xd8\xff\xc0\x00\x0b\x08"+height.to_bytes(2,"big")+width.to_bytes(2,"big")+b"\x01\x01\x11\x00\xff\xd9"
        with self.assertRaisesRegex(ValueError,"pixel dimensions exceed"):
            pp._jpeg_header(sof,max_pixels=pp.W8_MAX_PIXELS)

    def test_private_output_is_no_clobber_and_failed_derivative_write_cleans_directory(self):
        try:from PIL import Image
        except ImportError:self.skipTest("Pillow is an optional local-only W8 JPEG runtime")
        output=self.vault/"inspection"
        output.mkdir()
        with mock.patch.object(pp,"_w8_load_profile",return_value=self.profile),mock.patch.object(pp,"_w8_verify_inputs",return_value=(self.data,self.record,self.profile["source_lock"],"evidence-hash")),mock.patch.object(pp,"_w8_decode",return_value=Image.new("RGB",(32,24),(120,90,60))),mock.patch.object(pp,"_w8_pixel_analysis",return_value={"analysis_dimensions":[4,3],"downsample_factor":8,"candidate_material_regions":[],"candidate_line_regions":[],"coordinate_transform_source_to_analysis":[[.125,0,0],[0,.125,0],[0,0,1]]}):
            with self.assertRaisesRegex(ValueError,"already exists"):
                pp.inspect_w8_real_image(Path("profile"),Path("image"),Path("evidence"),output)
        output.rmdir()
        with mock.patch.object(pp,"_w8_load_profile",return_value=self.profile),mock.patch.object(pp,"_w8_verify_inputs",return_value=(self.data,self.record,self.profile["source_lock"],"evidence-hash")),mock.patch.object(pp,"_w8_decode",return_value=Image.new("RGB",(32,24),(120,90,60))),mock.patch.object(pp,"_w8_pixel_analysis",return_value={"analysis_dimensions":[4,3],"downsample_factor":8,"candidate_material_regions":[],"candidate_line_regions":[],"coordinate_transform_source_to_analysis":[[.125,0,0],[0,.125,0],[0,0,1]]}),mock.patch.object(Image.Image,"save",side_effect=OSError("synthetic derivative failure")):
            with self.assertRaisesRegex(OSError,"derivative failure"):
                pp.inspect_w8_real_image(Path("profile"),Path("image"),Path("evidence"),output)
        self.assertFalse(output.exists())

def run_from_payload(payload, base, out):
    manifest=base/"manifest.yaml"; manifest.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")
    return run(manifest, out)

class W9RimeGeometryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        self.local=self.base/"local";self.vault=self.local/"HieraticAI/private-artifacts/W9";self.vault.mkdir(parents=True)
        self.previous_localappdata=os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"]=str(self.local)
        self.image=self.vault/"CAT1883-CAT2095-RIME-fig6-recto-original.tif"
        try:
            from PIL import Image,ImageDraw
        except ImportError:self.skipTest("Pillow optional image runtime unavailable")
        source=Image.new("RGB",(32,24),"white");ImageDraw.Draw(source).rectangle((4,5,27,18),fill=(110,80,48));source.save(self.image,format="TIFF",compression="raw")
        self.data=self.image.read_bytes();self.digest=hashlib.sha256(self.data).hexdigest()
        self.evidence=self.vault/"CAT1883-CAT2095-FIG6.json"
        self.packet={"source_sha256":self.digest,"source_byte_size":len(self.data),"source_object_id":"Cat.1883 + Cat.2095","physical_support_group":"Cat.1883 + Cat.2095 (one joined five-fragment support)","exact_original_file_url":"https://rivista.museoegizio.it/wp-content/themes/annotum-base/assets/articles/4418/content/6/original.tif","use_boundary":{"source_registry_status":"NOT_REGISTERED","training_admission":"BLOCKED","gold_or_transcription":"NONE"}}
        self.evidence.write_text(json.dumps(self.packet),encoding="utf-8")
        self.profile=self.base/"profile.json"
        self.profile.write_text(json.dumps({"profile_id":"w9-rime-cat1883-cat2095-recto-geometry","profile_version":"1.0.0","engine_version":"W9-test","source_lock":{"source_sha256":self.digest,"byte_size":len(self.data),"dimensions":[32,24],"exact_file_url":self.packet["exact_original_file_url"]},"outputs":{"training_admission":"BLOCKED","annotation_or_gold":"NONE","article_text_reuse":"BLOCKED_UNVERIFIED_LICENSE"}}),encoding="utf-8")
        self.locks=mock.patch.multiple(pp,W9_RIME_SHA256=self.digest,W9_RIME_BYTES=len(self.data),W9_RIME_DIMENSIONS=[32,24])
        self.locks.start()
    def tearDown(self):
        self.locks.stop()
        if self.previous_localappdata is None:os.environ.pop("LOCALAPPDATA",None)
        else:os.environ["LOCALAPPDATA"]=self.previous_localappdata
        self.temp.cleanup()
    def test_geometry_only_tiff_overlay_is_deterministic_and_unlabelled(self):
        one=pp.inspect_w9_rime_image(self.profile,self.image,self.evidence,self.vault/"out-1")
        two=pp.inspect_w9_rime_image(self.profile,self.image,self.evidence,self.vault/"out-2")
        self.assertEqual(one["processing_id"],two["processing_id"])
        self.assertEqual(one["overlay"]["sha256"],two["overlay"]["sha256"])
        self.assertEqual("NONE",one["line_alignment"]);self.assertFalse(one["gold_or_annotation_created"])
        self.assertEqual("BLOCKED",one["training_admission"])
    def test_source_hash_and_evidence_mutations_fail_closed(self):
        self.image.write_bytes(self.data+b"x")
        with self.assertRaisesRegex(pp.PreprocessingError,"byte size, TIFF signature, or hash"):
            pp.inspect_w9_rime_image(self.profile,self.image,self.evidence,self.vault/"bad-source")
        self.image.write_bytes(self.data);self.packet["source_object_id"]="Cat.1880";self.evidence.write_text(json.dumps(self.packet),encoding="utf-8")
        with self.assertRaisesRegex(pp.PreprocessingError,"evidence identity or rights boundary"):
            pp.inspect_w9_rime_image(self.profile,self.image,self.evidence,self.vault/"bad-evidence")
    def test_profile_rights_promotion_is_rejected(self):
        profile=json.loads(self.profile.read_text(encoding="utf-8"));profile["outputs"]["training_admission"]="ALLOWED";self.profile.write_text(json.dumps(profile),encoding="utf-8")
        with self.assertRaisesRegex(pp.PreprocessingError,"promote rights or scholarly status"):
            pp.inspect_w9_rime_image(self.profile,self.image,self.evidence,self.vault/"promoted")

if __name__ == "__main__": unittest.main()
