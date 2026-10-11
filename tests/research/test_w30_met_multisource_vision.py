import unittest
import numpy as np
from tools import w30_met_multisource_vision as w

class W30OriginalMuseumVisionTests(unittest.TestCase):
    def test_five_frozen_physical_object_accessions(self):
        self.assertEqual(set(w.TRAIN),{546511,554654,545445})
        self.assertEqual(set(w.TEST),{544847,549250})
        self.assertFalse(set(w.TRAIN)&set(w.TEST))
        self.assertEqual(len({acc for _,acc in (w.TRAIN|w.TEST).values()}),5)

    def test_refuses_unpreregistered_source_id(self):
        with self.assertRaisesRegex(ValueError,"Unfrozen"):
            w.acquire(9999999)

    def test_mask_nonpadding_interior_and_multimodel_features(self):
        a=np.arange(64*64,dtype=np.float32).reshape((64,64))/4096
        y=np.array([20,23,27]);x=np.array([17,32,11])
        lin=w.features(a,y,x,False)
        quadratic=w.features(a,y,x,True)
        self.assertEqual(lin.shape,(3,10))
        self.assertEqual(quadratic.shape,(3,22))
        self.assertEqual(quadratic[0,9],lin[0,0]**2)
        self.assertTrue(np.all(quadratic[:,-1]==1))

    def test_rejects_incomplete_original_five_witness_source_set(self):
        with self.assertRaisesRegex(ValueError,"Exactly five"):
            w.learn({})

    def test_quadratic_model_fits_with_fixed_training_ridge(self):
        rng=np.random.default_rng(29)
        X=rng.normal(size=(200,22))
        y=rng.normal(size=200)
        wgt=w.ridge(X,y,1)
        self.assertEqual(wgt.shape,(22,))
        self.assertTrue(np.all(np.isfinite(wgt)))

    def test_real_horizontal_neighbor_edge_gradient_metric(self):
        truth=np.array([0.,.5,1.,0.,.5])
        neighbors=np.array([True,True,False,True])
        perfect=w.pixel_stats(truth,truth,neighbors)
        self.assertEqual(perfect["horizontal_edge_gradient_mae"],0)
        self.assertEqual(perfect["actual_horizontal_pixel_pairs"],3)
        flat=w.pixel_stats(np.full_like(truth,.5),truth,neighbors)
        self.assertGreater(flat["horizontal_edge_gradient_mae"],0)
        with self.assertRaises(ValueError):
            w.pixel_stats(truth,truth,np.array([True,False]))

    def test_better_image_metric_direction(self):
        x=np.array([0,.25,.5,1.],dtype=float)
        self.assertEqual(w.pixel_stats(x,x)["mae"],0)
        self.assertEqual(w.pixel_stats(x,x)["psnr_db"],120)
        self.assertGreater(w.pixel_stats(x,x)["psnr_db"],w.pixel_stats(x,np.zeros(4))["psnr_db"])

if __name__=="__main__":unittest.main()
