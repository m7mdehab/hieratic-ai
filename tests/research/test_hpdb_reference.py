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


class RealPublishedHPDBMetadataTests(unittest.TestCase):
    """Full 2,065-entry real CC BY metadata snapshot, never Tokyo IIIF pixels."""

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2] / "data" / "references" / "hpdb"
        cls.manifest = json.loads((cls.root/"metadata_manifest.json").read_text(encoding="utf-8"))
        cls.rows = []
        for volume in (1, 2, 3):
            path = cls.root / f"moller_v{volume}_ccby4_metadata.jsonl"
            cls.rows.extend(json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip())

    def test_real_source_population_and_pinned_provenance(self):
        self.assertEqual(2065, len(self.rows))
        self.assertEqual(2065, self.manifest["total_sign_records"])
        self.assertEqual("6efc36471b47255cfc03f6ba8cf9c887a293bb89", self.manifest["source_git_blob_sha1"])
        self.assertEqual("a8cfcf52632487cf1d61a5793d84c9b2f7192d5a", self.manifest["pinned_repository_commit"])
        self.assertEqual("CC-BY-4.0", self.manifest["metadata_license"])
        self.assertFalse(self.manifest["underlying_scans_license_verified"])
        self.assertFalse(self.manifest["underlying_scans_downloaded"])
        self.assertEqual("BLOCKED_REFERENCE_METADATA_ONLY", self.manifest["corpus_training_admission"])

    def test_real_all_ids_unique_and_exact_source_pointers(self):
        ids = [x["id"] for x in self.rows]
        self.assertEqual(len(ids), len(set(ids)))
        for x in self.rows:
            self.assertEqual("https://w3id.org/hpdb/item/"+x["id"], x["item_url"])
            self.assertTrue(ref._safe_image_reference(x["iiif_ref"]))
            self.assertIn(x["kind"], {"Main","Number","Ligature"})
            self.assertIn(x["vol"], {1,2,3})
            self.assertGreater(x["page"], 0)
            self.assertLessEqual(x["page"], 250)

    def test_real_source_groups_types_and_uncertainties(self):
        from collections import Counter
        self.assertEqual(Counter({1:738,2:670,3:657}),Counter(x["vol"] for x in self.rows))
        self.assertEqual(Counter({"Main":1626,"Number":251,"Ligature":188}),Counter(x["kind"] for x in self.rows))
        self.assertEqual(214,len({(x["vol"],x["page"]) for x in self.rows}))
        self.assertEqual(1439,sum(x["single_sign"] is not None for x in self.rows))
        self.assertEqual(626,sum(x["single_sign"] is None for x in self.rows))
        for x in self.rows:
            if x["single_sign"] is not None:
                self.assertEqual(x["gardiner_printed"], x["single_sign"])

    def test_actual_bundle_cannot_be_converted_into_source_gold(self):
        for x in self.rows:
            self.assertNotIn("image_bytes", x)
            self.assertNotIn("gold", x)
            self.assertNotIn("transcription", x)
            self.assertNotIn("reading_verified", x)
            self.assertNotIn("training_admission", x)
        self.assertFalse(self.manifest["source_original_manuscripts_identified"])
        self.assertFalse(self.manifest["gold_expert_verified"])
        self.assertFalse(self.manifest["source_witness_independence_verified"])
        self.assertEqual("BLOCKED_REFERENCE_METADATA_ONLY",self.manifest["scientific_evaluation_admission"])

    def test_mixed_case_gardiner_labels_are_not_corrupted(self):
        original=source_item(**{"Hieroglyph No":["Aa1"]})
        item=ref.normalize_item(original)
        self.assertEqual("Aa1",item["unambiguous_single_gardiner_label"])


if __name__ == "__main__":
    unittest.main()
