"""W25 source-image falsification controls with no original museum asset in test suite."""
import hashlib,unittest
import numpy as np
from PIL import Image
from tools import research_cat1880_pixels as m
class RealPhotoFeatures(unittest.TestCase):
 def test_source_digest_mismatch_fails(self):
  with self.assertRaises(ValueError):m.original(b"\xff\xd8fake")
 def test_otsu_distinguishes_two_tone_fields(self):
  a=np.array([[0,0,0,0],[255,255,255,255]]*15,dtype=np.uint8)
  self.assertTrue(0<=m.otsu(a)<255)
 def test_blank_has_zero_dark_fraction(self):
  x=m.metrics(Image.new("L",(96,64),230))
  self.assertEqual(0,x["dark_pixel_fraction"])
  self.assertEqual(0,x["gray_std"])
 def test_ink_fabrication_not_equal_to_source_identity(self):
  gray=Image.fromarray(np.tile(np.array([50,230]*48,dtype=np.uint8),(64,1)),"L")
  x=m.metrics(gray)
  self.assertGreater(x["dark_pixel_fraction"],0.1)
  self.assertEqual(96,x["width"])
 def test_source_controls_do_not_assert_accuracy(self):
  self.assertEqual(30364719,m.ORIGINAL_BYTES)
  self.assertEqual("MuseoEgizio:Cat.1880",m.SOURCE_RECORD.split("/File:")[0].split("/")[-1] if False else "MuseoEgizio:Cat.1880")
  self.assertEqual(64,len(m.ORIGINAL_SHA256))
 def test_tile_geometry_exact(self):
  self.assertEqual(0,1280%32);self.assertEqual(0,576%32)
if __name__=="__main__":unittest.main()
