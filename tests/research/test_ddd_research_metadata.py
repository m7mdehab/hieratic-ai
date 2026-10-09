"""DDD source rights, per-papyrus photographic identities and research boundaries."""
from __future__ import annotations
import io,json,zipfile,unittest
from tools.research_ddd_public_metadata import safe_url,inspect_metadata,PublicSourceError
def fixture():
 papyri={f"{i:03d}":{"name":f"support{i}","copyright":"Copyright Museo Egizio","doc_cluster":i%50} for i in range(1,160)}
 papyri["003"]["name"]="C1880rt_rotated";papyri["003"]["doc_cluster"]=1
 papyri["004"]["name"]="C1880rt";papyri["004"]["doc_cluster"]=1
 f=io.BytesIO()
 with zipfile.ZipFile(f,"w") as z:z.writestr("annotations/001.json",'{"shapes":[]}')
 source={"papyri.json":json.dumps(papyri).encode(),
         "classes.json":json.dumps({"A1":"provisional"}).encode(),
         "samples.json":json.dumps([{"class_id":"A1"}]).encode(),
         "DDD_annotations.zip":f.getvalue(),
         "Readme - Splits.txt":b"C-C"}
 bench=[{"id":f"syn-{i}","object_name":"unrelated"} for i in range(266)]
 return source,bench
class DDDResearchRightsTests(unittest.TestCase):
 def test_bounded_original_publisher_endpoint(self):
  self.assertTrue(safe_url("https://zenodo.org/records/20553713/files/papyri.json?download=1"))
  for u in ("http://zenodo.org/","https://zenodo.org.evil.tld/","https://username@zenodo.org/","https://evil.org/"):
   self.assertFalse(safe_url(u))
 def test_source_files_allowlisted(self):
  from tools.research_ddd_public_metadata import FILES
  self.assertEqual(5,len(FILES))
  self.assertTrue(all(x[1]<18_000_000 for x in FILES.values()))
  self.assertFalse(any("DDD_images.zip"==name for name in FILES))
 def test_document_holdout_and_noncommercial_license(self):
  source,bench=fixture();z=inspect_metadata(source,bench)
  self.assertEqual([1],z["cat1880_same_physical_cluster"])
  self.assertFalse(z["data008_production_corpus_admission"])
  self.assertEqual("UNKNOWN_QUARANTINED",z["benchmark_overlap"])
  self.assertIn("NONCOMMERCIAL",z["licence_for_dataset_annotations"])
  self.assertEqual(0,z["source_image_bytes_committed"])
  self.assertEqual("C-B",z["recommended_first_research_only_closed_set_holdout_split"])
  self.assertEqual("O-B",z["recommended_first_research_only_open_set_holdout_split"])
  self.assertNotIn("C-D",z["publisher_document_disjoint_split_protocols"])
  self.assertIn("C-D",z["publisher_random_sample_splits_not_valid_as_document_holdout"])
 def test_two_cat1880_views_cannot_be_split_as_distinct_objects(self):
  source,bench=fixture();s=json.loads(source["papyri.json"]);s["004"]["doc_cluster"]=44
  source["papyri.json"]=json.dumps(s).encode()
  with self.assertRaises(PublicSourceError):inspect_metadata(source,bench)
 def test_missing_per_item_photo_rights_refused(self):
  source,bench=fixture();s=json.loads(source["papyri.json"]);s["050"].pop("copyright")
  source["papyri.json"]=json.dumps(s).encode()
  with self.assertRaises(PublicSourceError):inspect_metadata(source,bench)
 def test_public_metadata_snapshot_drift_refused(self):
  source,bench=fixture()
  with self.assertRaises(PublicSourceError):inspect_metadata(source,bench[:-1])
 def test_wrong_papyrus_denominator_refused(self):
  source,bench=fixture();s=json.loads(source["papyri.json"]);s.pop("159")
  source["papyri.json"]=json.dumps(s).encode()
  with self.assertRaises(PublicSourceError):inspect_metadata(source,bench)
 def test_zip_path_escape_refused(self):
  source,bench=fixture()
  f=io.BytesIO()
  with zipfile.ZipFile(f,"w") as z:z.writestr("../illegal.json",'{"shapes":[]}')
  source["DDD_annotations.zip"]=f.getvalue()
  with self.assertRaises(PublicSourceError):inspect_metadata(source,bench)
 def test_source_census_does_not_read_sealed_data(self):
  source,bench=fixture();d=inspect_metadata(source,bench)
  self.assertEqual([],d["R017_public_literal_cat1880_matches"])
  self.assertFalse(d["sealed_benchmark_unblinded"])

 def test_real_w23_publisher_source_receipt_unchanged(self):
  from pathlib import Path
  from tools.research_ddd_public_metadata import FILES
  source=Path(__file__).resolve().parents[2]/"docs/research/R028_DDD_ORIGINAL_PUBLIC_METADATA_RECEIPTS.json"
  receipt=json.loads(source.read_text(encoding="utf8"))
  self.assertEqual(159,receipt["publisher_images"])
  self.assertEqual(50,receipt["actual_cluster_count"])
  self.assertEqual(504,receipt["source_classes_length"])
  self.assertEqual(17885,receipt["source_samples_length"])
  self.assertEqual(5,len(receipt["verified_publisher_files"]))
  self.assertEqual(set(FILES),{x["file"] for x in receipt["verified_publisher_files"]})
  self.assertEqual(0,receipt["original_image_files_retrieved"])
  self.assertFalse(receipt["data008_production_corpus_admission"])
  self.assertEqual([1],receipt["cat1880_same_physical_cluster"])

if __name__=="__main__":unittest.main()
