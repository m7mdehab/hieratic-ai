import unittest
import numpy as np
from tools import w31_original_print_domain as w
class W31DomainTests(unittest.TestCase):
 def test_exact_new_original_source_frozen(self):
  self.assertEqual((w.MET_NEW,w.MET_ACCESSION),(555779,"34.1.215a"))
  self.assertNotIn(w.MET_NEW,[x[0] for x in w.met.MET_OBJECTS])
 def test_original_publisher_population_is_frozen(self):
  rows=w.hpdb.read_catalog()
  self.assertEqual(len(w.printed.frozen(rows)),74)
 def test_finite_domain_detector_and_threshold(self):
  rng=np.random.default_rng(31)
  positive=rng.normal(loc=.5,size=(30,160))
  negative=rng.normal(loc=-.5,size=(20,160))
  X=np.vstack([positive,negative]);y=np.array([1]*30+[0]*20)
  fit=w.model(X,y,.01)
  scores=w.predict(X,fit)
  self.assertEqual(scores.shape,(50,))
  self.assertTrue(np.isfinite(scores).all())
 def test_never_equates_domain_with_gardiner_gold(self):
  self.assertIn("print",w.VERSION.lower())
if __name__=="__main__":unittest.main()
