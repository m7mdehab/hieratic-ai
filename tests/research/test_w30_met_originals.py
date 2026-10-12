import unittest
import numpy as np
from tools import w30_met_originals as m

class W30OriginalMuseumPhotoTests(unittest.TestCase):
    def test_frozen_new_supports_never_seen_in_w29(self):
        self.assertEqual({x[0] for x in m.FREEZE if x[3]=="test"},{544847,555779})
        self.assertEqual({x[0] for x in m.FREEZE if x[3]=="train"},{546511,554654})
        self.assertEqual(len({x[2] for x in m.FREEZE}),4)
    def test_no_test_training_leak_by_function_signature(self):
        r=np.random.default_rng(3)
        X=r.integers(0,255,(80,140),dtype=np.uint8)
        weight,fit=m.fit_on_sources([X,X])
        self.assertEqual(fit["train_pairs"],108000)
        self.assertEqual(len(weight),10)
        scores=m.eval_image(X,weight,555779)
        self.assertEqual(scores["valid_unpadded_evaluation_pixels"],78*138)
        self.assertEqual(len(scores["noise_controls"]),3)
        self.assertTrue(scores["source_is_train_disjoint"])
    def test_source_does_not_claim_ocr_certification(self):
        self.assertEqual(m.IMAGE_PREFIX,"/CRDImages/eg/original/")
        self.assertNotEqual(m.FREEZE[2][2],m.FREEZE[0][2])
if __name__=="__main__":unittest.main()
