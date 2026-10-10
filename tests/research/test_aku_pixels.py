"""Original W19 source identity and original pixel false-substitution controls."""
import json,unittest
from pathlib import Path
from tools import research_aku_pixels as m
class ScanSourceControls(unittest.TestCase):
 def test_exact_w19_original_five(self):
  data=json.loads(m.MANIFEST.read_text("utf8"))
  c=m.scan_records(data)
  self.assertEqual(5,len(c))
  self.assertTrue(all(m.allowed(media["publisher_media_url"],i["id"]) for i,media in c))
 def test_disallow_another_id_or_host(self):
  self.assertFalse(m.allowed("https://aku-pal.uni-mainz.de/img/data/ht/scan/ht_111_2.webp",2448))
  self.assertFalse(m.allowed("https://evil.tld/img/data/ht/scan/ht_2448_2.webp",2448))
 def test_disallow_nonhieratic_hg(self):
  self.assertFalse(m.allowed("https://aku-pal.uni-mainz.de/img/data/hg/hg_2448.svg",2448))
 def test_source_hash_incorrect_cannot_be_called_real(self):
  with self.assertRaises(ValueError):m.inspect(b"RIFF", "0"*64,4)
 def test_require_all_five_origins_and_no_generalization(self):
  data=json.loads(m.MANIFEST.read_text("utf8"))
  for item in data["items"]:
   for media in item["publisher_media"]:
    if media["image_classification"]=="publication_scan_reproduction":
     media["image_classification"]="svg_outline_derivative"
     with self.assertRaises(ValueError):m.scan_records(data)
     return
if __name__=="__main__":unittest.main()
