"""W29 real photo denoiser algorithm: synthetic unit input only, never gold."""
import unittest
import numpy as np
from tools import w29_cc0_original_vision as w

class W29CC0DenoiserTests(unittest.TestCase):
    def test_refuses_substituted_source_dimensions(self):
        with self.assertRaisesRegex(ValueError,"exact downsampled"):
            w.learn(np.zeros((120,100),np.uint8))

    def test_linear_features_have_exact_center_and_bias(self):
        x=np.arange(8*12,dtype=np.float32).reshape(8,12)/255
        v=w.patch_features(x,np.array([3]),np.array([4]))
        self.assertEqual(v.shape,(1,10))
        self.assertAlmostEqual(v[0,4],x[3,4])
        self.assertEqual(v[0,-1],1)

    def test_invalid_footprint_refused(self):
        a=np.zeros((8,10),np.float32)
        with self.assertRaises(ValueError):
            w.patch_features(a,np.array([1]),np.array([0]))

    def test_train_only_fixed_sample_sizes_and_alpha(self):
        x=np.random.default_rng(29).integers(0,255,size=(768,1536),dtype=np.uint8)
        v=w.learn(x)
        self.assertEqual(v["train"]["sampled_pixels"],108000)
        self.assertEqual(v["heldout"]["pixels_per_sigma"],766*507)
        self.assertIn(v["train"]["selected_train_only_ridge_alpha"],w.ALPHAS)
        self.assertIsNone(v["hieratic_reading_accuracy"])
        self.assertFalse(v["original_photo_heldout_witness_independent"])
        self.assertEqual(v["weighted_capability_points"],0)

    def test_metrics_identical_when_predictions_clean(self):
        x=np.linspace(0,1,20)
        v=w.report(x,x,0.4)
        self.assertEqual(v["mae"],0)
        self.assertEqual(v["dark_fraction_abs_error"],0)
        self.assertEqual(v["psnr_db"],120.0)

    def test_synthetic_inputs_never_replace_source_original(self):
        self.assertEqual(w.original.ORIGINAL_BYTES,30364719)
        self.assertEqual(w.original.ORIGINAL_SHA256,"2f637e7d59785cce7308e478f6a59fb5c54e0ba9c694621e4072c8b2f2594ee5")

if __name__=="__main__":
    unittest.main()
