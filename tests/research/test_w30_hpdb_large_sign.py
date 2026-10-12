import unittest
import numpy as np
from PIL import Image
from tools import w30_hpdb_large_sign as h
class W30LargeSigns(unittest.TestCase):
    def test_pinned_publisher_source_unaltered(self):
        xs=h.source.read_catalog()
        self.assertEqual(len(xs),2065)
        fixed=h.frozen(xs)
        self.assertTrue(24<=len(fixed)<=288)
        self.assertEqual(len({x["item_id"] for x in fixed}),len(fixed))
        self.assertEqual({x["volume"] for x in fixed},{1,2,3})
        self.assertEqual(set(h.LABELS),{x["label"] for x in fixed})
    def test_actual_features_and_training(self):
        rng=np.random.default_rng(30)
        pix=h.hog(Image.fromarray(rng.integers(0,255,(32,32),dtype=np.uint8)))
        self.assertEqual(pix.shape[0],160)
        X=rng.normal(size=(24,160));y=np.array(list(h.LABELS)*3)
        clf=h.training(X,y,.1)
        self.assertEqual(len(h.predict(X,clf)),24)
    def test_original_image_url_domain_and_format(self):
        with self.assertRaises(h.source.SourceError):
            h.source.verify_iiif_url("https://evil.com/print/default.jpg")
if __name__=="__main__":unittest.main()
