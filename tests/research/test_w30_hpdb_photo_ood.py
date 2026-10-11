"""W30 Tokyo original printed signs vs real original museum photo OOD invariants."""
import unittest
import numpy as np
from PIL import Image
from tools import w30_hpdb_photo_ood as e

class W30PrintedSignToPhotoOODTests(unittest.TestCase):
    def test_pinned_actual_publisher_original_sign_population(self):
        rows=e.hpdb.read_catalog()
        self.assertEqual(len(rows),2065)
        sample=e.cohort(rows)
        self.assertGreaterEqual(len(sample),24)
        self.assertLessEqual(len(sample),192)
        self.assertEqual(set(x["label"] for x in sample),set(e.LABELS))
        self.assertTrue(all(x["rank_within_label_volume"]<8 for x in sample))

    def test_freeze_cannot_pick_untrusted_iiif(self):
        rows=e.hpdb.read_catalog()
        altered=[dict(x) for x in rows]
        target=next(x for x in altered if x.get("kind")=="Main" and x.get("single_sign")=="A1" and x.get("vol")==1)
        target["iiif_ref"]="https://example.invalid/fake/default.jpg"
        target["id"]="0000000000000000"
        with self.assertRaises(e.hpdb.SourceError):
            e.cohort(altered)

    def test_official_original_met_object_allowlist(self):
        self.assertEqual(e.MET_CC0,(546511,554654))
        with self.assertRaises(ValueError):
            e.met.met_original(123456,"Unapproved museum photo")

    def test_print_predictor_confidence_raw_not_gold_probability(self):
        X=np.array([[1.,0.],[0.,1.]])
        model=(np.array([[.8,.2],[.1,.9]]),np.array([0.,0.]))
        c=e.confidence(X,model)
        self.assertEqual(c.tolist(),[.8,.9])

    def test_fixed_true_image_patch_extraction_and_qualified_jpeg(self):
        from io import BytesIO
        image=Image.new("RGB",(180,140),(50,95,145))
        buf=BytesIO();image.save(buf,format="JPEG")
        patches=e.new_photo_tiles(buf.getvalue(),546511,8)
        self.assertEqual(len(patches),8)
        self.assertTrue(all(x.size==(32,32) for x in patches))

    def test_unlabelled_originals_are_not_hieratic_classification_gold(self):
        self.assertEqual(e.VERSION,"W30-REAL-TOKYO-PRINTED-SIGN-TO-MET-ORIGINAL-UNLABELLED-OOD/1")
        self.assertEqual(e.MAX_PER_LABEL_VOLUME,8)

if __name__=="__main__":unittest.main()
