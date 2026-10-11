import unittest
import numpy as np
from tools import w30_hpdb_eleven_class as s

class W30ElevenClassOriginalPublisherTests(unittest.TestCase):
    def test_catalog_counts_frozen_before_new_source_pixels(self):
        c=s.source.read_catalog()
        self.assertEqual(len(c),2065)
        a=s.frozen(c)
        self.assertEqual(len(a),74)
        self.assertEqual(sum(x["volume"]==3 for x in a),25)
        self.assertEqual(len(set(x["item_id"] for x in a)),74)
        self.assertEqual(set(x["label"] for x in a),set(s.LABELS))

    def test_original_source_catalog_tampering_refused(self):
        c=s.source.read_catalog()
        subset=[x for x in c if not (x.get("single_sign")=="S42" and x.get("vol")==3 and x.get("kind")=="Main") ]
        with self.assertRaises(s.source.SourceError):
            s.frozen(subset)

    def test_exact_train_source_11_class_ridge(self):
        rng=np.random.default_rng(30)
        X=rng.normal(size=(40,16))
        Y=np.arange(40)%11
        model=s.model_fit(X,Y,.1)
        out=s.outputs(X,model)
        self.assertEqual(out.shape,(40,11))
        self.assertEqual(model[0].shape,(16,11))

    def test_accuracy_per_class_full_denominator(self):
        gold=np.arange(11,dtype=int)
        report=s.summary(gold,gold,[{"printed_support_proxy":str(i)} for i in range(11)])
        self.assertEqual(report["correct"],11)
        self.assertEqual(report["top1_accuracy"],1.0)
        self.assertEqual(report["macro_accuracy"],1.0)

    def test_original_genuine_met_photo_unlabelled_only(self):
        self.assertEqual(s.earlier.MET_CC0,(546511,554654))
        self.assertIn("UNLABELLED",s.VERSION)

if __name__=="__main__":unittest.main()
