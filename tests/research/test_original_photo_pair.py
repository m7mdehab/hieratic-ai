"""W20 R025 adverse rights / physical source / public metadata tests."""
import copy,json,unittest
from pathlib import Path
from tools.research_photo_pair import audit
ROOT=Path(__file__).resolve().parents[2]
def fixture():
    m=json.loads((ROOT/"docs/research/R025_CC0_PHOTO_EDITION_MATRIX.json").read_text("utf-8"))
    p=[{"id":"synthetic-%03d"%i,"object_name":"Other museum"} for i in range(266)]
    return m,p
class PhotoEditionResearchTests(unittest.TestCase):
    def test_actual_public_source_census_and_scientific_boundary(self):
        m,p=fixture()
        p=[json.loads(z) for z in (ROOT/"docs/research/R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl").read_text("utf-8").splitlines() if z.strip()]
        r=audit(m,p)
        self.assertEqual(266,r["public_benchmark_metadata_records_checked"])
        self.assertEqual(0,r["exact_match_count"])
        self.assertEqual(19,r["institution_family_count"])
        self.assertEqual(3,r["original_physical_supports"])
        self.assertEqual(7,r["public_photo_pages_cited"])
        self.assertFalse(r["benchmark_nonoverlap_certified"])
        self.assertFalse(r["production_admission"])
        self.assertEqual(0,r["certified_physical_image_to_line_pairs"])
    def test_number_boundary_67591_is_not_6759(self):
        m,p=fixture()
        p[0]["source_url"]="https://aku-pal.uni-mainz.de/signs/67591"
        self.assertEqual(0,audit(m,p)["exact_match_count"])
        p[0]["object_name"]="Museo Egizio Suppl. 6759"
        self.assertEqual(1,audit(m,p)["exact_match_count"])
    def test_source_grouping_seven_files_do_not_become_seven_manuscripts(self):
        m,p=fixture()
        z=audit(m,p)
        self.assertEqual(3,z["original_physical_supports"])
        self.assertEqual(7,len(z["media"]))
        self.assertEqual(1,len(set(x["physical_support"] for x in z["media"] if "Cat.1880" in x["physical_support"])))
    def test_synthetic_claim_forgery_refused(self):
        for k,v in [("training_admission",True),("original_photos_acquired",1),
             ("exact_photo_to_written_line_pairs",1),("independent_expert_reviewed_pairs",1),
             ("benchmark_status","CLEARED")]:
            with self.subTest(field=k):
                m,p=fixture();m[k]=v
                with self.assertRaises(ValueError):audit(m,p)
    def test_source_pdf_edition_byte_and_line_assertions_refused(self):
        for field,value in [("original_pdf_bytes_acquired",True),
            ("photo_to_specific_plate_region","MATCHED"),("cat1880_printed_text_pages",[49,65])]:
            with self.subTest(field=field):
                m,p=fixture();m["historical_edition"][field]=value
                with self.assertRaises(ValueError):audit(m,p)
    def test_wrong_source_census_revision_refused(self):
        m,p=fixture()
        with self.assertRaises(ValueError):audit(m,p[:-1])
    def test_raster_file_sha_not_invented(self):
        m,p=fixture()
        m["source_objects"][0]["files"][0]["original_media_SHA256"]="0"*64
        with self.assertRaises(ValueError):audit(m,p)
    def test_personal_mark_control_not_falsely_translated(self):
        m,p=fixture()
        self.assertIn("IDENTITY_MARKS",m["source_objects"][2]["type"])
        m["source_objects"][2]["exact_face_and_line_alignment"]="VERIFIED_LINE"
        with self.assertRaises(ValueError):audit(m,p)
    def test_benchmark_object_ids_from_other_institutions_do_not_imply_clearance(self):
        m,p=fixture()
        p[0]["object_name"]="Museo Egizio Turin related collection unspecified"
        q=audit(m,p)
        self.assertEqual(1,q["institution_family_count"])
        self.assertEqual(0,q["exact_match_count"])
        self.assertFalse(q["benchmark_nonoverlap_certified"])
if __name__=="__main__":unittest.main()
