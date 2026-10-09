"""Strict DDD original metadata sample schema admission tests."""
import unittest
from tools.research_ddd_prior_baseline import structural_probe
from tools.research_ddd_public_metadata import PublicSourceError
class ProvenanceProbe(unittest.TestCase):
 def test_fake_source_universe_refused(self):
  with self.assertRaises(PublicSourceError):
   structural_probe({"01":{}},{"1":{}},{"A1":{}})
 def test_real_publisher_counts_without_gold(self):
  papyri={str(i):{"doc_cluster":i%50,"copyright":"unknown"} for i in range(159)}
  samples={str(i):{"image":"1","class":"a"} for i in range(17885)}
  classes={str(i):{} for i in range(504)}
  x=structural_probe(papyri,samples,classes)
  self.assertTrue(x["no_training"])
  self.assertEqual(17885,x["samples_count"])
if __name__=="__main__":unittest.main()
