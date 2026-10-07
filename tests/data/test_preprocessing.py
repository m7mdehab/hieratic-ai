import hashlib, json, shutil, tempfile, unittest
from pathlib import Path
import yaml
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

def run_from_payload(payload, base, out):
    manifest=base/"manifest.yaml"; manifest.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")
    return run(manifest, out)

if __name__ == "__main__": unittest.main()
