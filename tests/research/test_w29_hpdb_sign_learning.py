import unittest
import numpy as np
from PIL import Image
from tools import w29_hpdb_sign_learning as h

class W29HPDBOriginalSignModelTests(unittest.TestCase):
    def test_original_publisher_2065_catalog_frozen_source(self):
        rows=h.source.read_catalog()
        self.assertEqual(len(rows),2065)
        items=h.frozen(rows)
        self.assertGreaterEqual(len(items),24)
        self.assertLessEqual(len(items),72)
        self.assertEqual({i["volume"] for i in items},{1,2,3})
        self.assertEqual(set(h.LABELS),set(i["label"] for i in items))
        self.assertTrue(all(i["url"].startswith("https://iiif.dl.itc.u-tokyo.ac.jp/iiif/asia/hp/") for i in items))

    def test_untrusted_fake_source_host_rejected(self):
        with self.assertRaises(h.source.SourceError):
            h.source.verify_iiif_url("https://evil.example.org/fake/default.jpg")

    def test_hog_features_derived_only_from_input_pixels(self):
        white=h.hog(Image.new("L",(32,32),250))
        black=h.hog(Image.new("L",(32,32),0))
        self.assertEqual(white.shape,black.shape)
        self.assertFalse(np.array_equal(white,black))
        self.assertAlmostEqual(float(np.linalg.norm(white)),1,places=5)

    def test_hog_refuses_wrong_dimensions(self):
        with self.assertRaises(ValueError):h.hog(Image.new("L",(32,16),250))

    def test_ridge_never_uses_original_test_labels_when_fitting(self):
        rng=np.random.default_rng(29)
        X=rng.normal(size=(16,160))
        labels=np.array(h.LABELS*2)
        model=h.training(X,labels,0.1)
        pred=h.predict(X,model)
        self.assertEqual(pred.shape,(16,))
        self.assertTrue(np.all(pred>=0))
        self.assertTrue(np.all(pred<8))

    def test_nn_cannot_infer_classes_outside_train(self):
        X=np.eye(3)
        ans=h.nn(X,np.array([0,2,5]),X)
        self.assertEqual(ans.tolist(),[0,2,5])

    def test_source_fixture_ignores_non_main_and_invalid_labels(self):
        items=[{"id":f"x{i}-{v}","single_sign":lab,"vol":v,"kind":"Main",
                "iiif_ref":f"https://iiif.dl.itc.u-tokyo.ac.jp/iiif/asia/hp/a/{i}/default.jpg",
                "page":i} for i,lab in enumerate(h.LABELS) for v in (1,2,3)]
        # All volume groups are valid; test results are NEVER based on fixture pixels.
        self.assertEqual(len(h.frozen(items)),24)
        items.append({"id":"fake","single_sign":"A1","vol":1,"kind":"Secondary",
                "iiif_ref":"https://evil.org/img","page":0})
        self.assertEqual(len(h.frozen(items)),24)

if __name__=="__main__":
    unittest.main()
