"""Adverse original-source DDD metadata and document-group split tests."""
import copy,unittest
from tools.research_ddd_prior_baseline import group_aware_baseline,SEED,stable_rank
from tools.research_ddd_public_metadata import PublicSourceError
def fixtures():
    papyri={f"{i:03d}":{"name":f"object_{i}","doc_cluster":i%50,
        "copyright":"source review pending"} for i in range(159)}
    papyri["003"]["name"]="C1880rt_rotated"
    papyri["004"]["name"]="C1880rt"
    papyri["003"]["doc_cluster"]=1
    papyri["004"]["doc_cluster"]=1
    samples={f"{i:05d}":{"sample_number":f"{i:05d}",
      "document_number":f"{i%159:03d}","class_label":f"C{i%504}"} for i in range(17885)}
    classes={str(i):{"class_label":f"C{i}"} for i in range(504)}
    return papyri,samples,classes
class OriginalGroupedNegativeTests(unittest.TestCase):
    def test_all_real_publisher_shape_invariants_with_no_image_training(self):
        a,b,c=fixtures()
        z=group_aware_baseline(a,b,c)
        self.assertEqual(17885,z["source_samples"])
        self.assertEqual(50,z["source_distinct_manuscripts"])
        self.assertEqual(0,z["source_object_partition_intersection_count"])
        self.assertEqual(50,z["sample_random_control_total_clusters"])
        self.assertTrue(z["sample_random_control_document_clusters_contaminated"]>0)
        self.assertEqual(0,z["weighted_capability_points_awarded"])
        self.assertIsNone(z["empirical_hieratic_image_recognition_accuracy"])
    def test_repeatable_split_and_cat1880_one_support(self):
        a,b,c=fixtures()
        z=group_aware_baseline(a,b,c);q=group_aware_baseline(a,b,c)
        self.assertEqual(z,q)
        self.assertEqual(1,z["cat1880_variant_source_cluster_count"])
    def test_source_cluster_forgery_refused(self):
        a,b,c=fixtures();a["004"]["doc_cluster"]=49
        with self.assertRaises(PublicSourceError):group_aware_baseline(a,b,c)
    def test_sample_doc_unknown_rejected(self):
        a,b,c=fixtures();b["00000"]["document_number"]="999"
        with self.assertRaises(PublicSourceError):group_aware_baseline(a,b,c)
    def test_undocumented_class_rejected(self):
        a,b,c=fixtures();b["00000"]["class_label"]="fabricated"
        with self.assertRaises(PublicSourceError):group_aware_baseline(a,b,c)
    def test_fake_sample_identity_refused(self):
        a,b,c=fixtures();b["00000"]["sample_number"]="99999"
        with self.assertRaises(PublicSourceError):group_aware_baseline(a,b,c)
    def test_rights_empty_refused(self):
        a,b,c=fixtures();del a["010"]["copyright"]
        with self.assertRaises(PublicSourceError):group_aware_baseline(a,b,c)
    def test_sample_universe_drift_refused(self):
        a,b,c=fixtures();b.pop("00000")
        with self.assertRaises(PublicSourceError):group_aware_baseline(a,b,c)
if __name__=="__main__":unittest.main()
