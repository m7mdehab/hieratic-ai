"""R-023: prove HPDB metadata never turns into image rights or expert gold."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools import hpdb_reference as ref


def source_item(item_id="201001", **override):
    d = {
        "_id": item_id,
        "_url": f"https://w3id.org/hpdb/item/{item_id}",
        "_image": "https://iiif.dl.itc.u-tokyo.ac.jp/iiif/asia/hp/2/2_023.tif/983,2131,3913,476/,200/0/default.jpg",
        "Vol": ["2"],
        "Page": ["1"],
        "Item Type": ["Main"],
        "Hieratic No": ["1"],
        "Hieroglyph No": ["A26"],
    }
    d.update(override)
    return d


class HPDBReferenceTests(unittest.TestCase):
    def test_first_published_sample_metadata_parses_without_original_media(self):
        x = ref.normalize_item(source_item())
        self.assertEqual("A26", x["unambiguous_single_gardiner_label"])
        self.assertEqual("MOLLER-V2-P001", x["source_page_group"])
        self.assertEqual("CC-BY-4.0", x["metadata_license"])
        self.assertEqual("not_independently_verified", x["underlying_scan_image_license"])
        self.assertEqual("BLOCKED_REFERENCE_METADATA_ONLY", x["training_admission"])
        self.assertIsNone(x["original_manuscript_source_identity"])

    def test_compounds_ambiguous_numbers_and_ligatures_are_not_single_label(self):
        for label,typ in [("N42/N41","Main"),("A??","Main"),("I10+D46","Ligature")]:
            with self.subTest(label=label):
                got=ref.normalize_item(source_item(**{"Hieroglyph No":[label],"Item Type":[typ]}))
                self.assertIsNone(got["unambiguous_single_gardiner_label"])

    def test_page_group_prevents_same_printed_page_duplicates(self):
        a=source_item()
        b=source_item("201002",**{"Hieroglyph No":["A30"]})
        result=ref.assemble_index([a,b], require_complete=False)
        self.assertEqual(1,result["source_page_groups"])
        self.assertEqual(2,result["declared_source_rows"])
        self.assertEqual(0,result["rights_cleared_original_manuscripts"])
        self.assertEqual(0,result["scientific_results"])

    def test_missing_duplicate_or_invalid_identity_is_rejected(self):
        for bad in [
            source_item(_id="../outside"),
            source_item(_url="https://attacker.test/another"),
            source_item(**{"Vol":["4"]}),
            source_item(**{"Page":["-1"]}),
            source_item(**{"Item Type":["unknown"]}),
            source_item(**{"Hieratic No":[]}),
        ]:
            with self.subTest(bad=bad):
                with self.assertRaises(ref.HPDBReferenceError):
                    ref.assemble_index([bad],require_complete=False)
        with self.assertRaisesRegex(ref.HPDBReferenceError,"Duplicate"):
            ref.assemble_index([source_item(),source_item()],require_complete=False)

    def test_path_or_domain_cannot_bypass_iiif_host(self):
        urls=[
            "https://evil.example/iiif/asia/hp/2/2_023.tif/1,1,1,1/,200/0/default.jpg",
            "http://iiif.dl.itc.u-tokyo.ac.jp/iiif/asia/hp/2/2_023.tif/1,1,1,1/,200/0/default.jpg",
            "https://iiif.dl.itc.u-tokyo.ac.jp.evil.test/iiif/asia/hp/2/2_023.tif/1,1,1,1/,200/0/default.jpg",
            "https://iiif.dl.itc.u-tokyo.ac.jp:8888/iiif/asia/hp/2/2_023.tif/1,1,1,1/,200/0/default.jpg",
            "https://iiif.dl.itc.u-tokyo.ac.jp:bad/iiif/asia/hp/2/2_023.tif/1,1,1,1/,200/0/default.jpg",
            "https://iiif.dl.itc.u-tokyo.ac.jp/iiif/asia/hp/../../secret.tif/1,1,1,1/,200/0/default.jpg",
            "https://root@iiif.dl.itc.u-tokyo.ac.jp/iiif/asia/hp/2/2_023.tif/1,1,1,1/,200/0/default.jpg",
            "https://iiif.dl.itc.u-tokyo.ac.jp/iiif/asia/hp/2/2_023.tif/1,1,1,1/,200/0/default.jpg?attack=1"
        ]
        for value in urls:
            with self.subTest(url=value):
                with self.assertRaisesRegex(ref.HPDBReferenceError,"IIIF"):
                    ref.normalize_item(source_item(_image=value))

    def test_complete_source_guard_rejects_partial_manual_sample(self):
        with self.assertRaisesRegex(ref.HPDBReferenceError,"2065"):
            ref.assemble_index([source_item()])
        with self.assertRaisesRegex(ref.HPDBReferenceError,"bounded"):
            ref.assemble_index([source_item()]*3001,require_complete=False)

    def test_unverified_bytes_cannot_certify_original_museum_asset(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/"index.json"
            file.write_text(json.dumps([source_item()]),encoding="utf-8")
            result=ref.read_local_index(file,require_complete=False)
            self.assertEqual("local_unattested_bytes_not_publisher_signed",result["source_file_trust"])
            self.assertEqual(64,len(result["locally_supplied_bytes_sha256"]))
            self.assertFalse(result["original_image_bytes_obtained"])
            self.assertEqual("BLOCKED_REFERENCE_METADATA_ONLY",result["source_rows"][0]["scientific_evaluation_admission"])

    def test_cli_rejects_unsafe_overwrite_and_fixture_claim_of_completeness(self):
        with tempfile.TemporaryDirectory() as temp:
            src=Path(temp)/"source.json"
            output=Path(temp)/"output.json"
            src.write_text(json.dumps([source_item()]),encoding="utf-8")
            self.assertEqual(1,ref.main(["--index",str(src),"--output",str(output)]))
            self.assertFalse(output.exists())
            self.assertEqual(0,ref.main(["--index",str(src),"--output",str(output),"--fixture-small"]))
            self.assertEqual(1,ref.main(["--index",str(src),"--output",str(output),"--fixture-small"]))

    def test_no_network_clients_or_image_reading_in_parser(self):
        source=Path(ref.__file__).read_text(encoding="utf-8")
        for snippet in ("requests.get(", "urlopen(", "Image.open(", ".get_image(", "httpx.get("):
            self.assertNotIn(snippet,source)


if __name__ == "__main__":
    unittest.main()
