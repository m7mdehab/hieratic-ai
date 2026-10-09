"""W17 AKU-PAL public source evidence checks; no downloaded assets."""
from __future__ import annotations
import unittest
from unittest.mock import patch
from data.releases import w17_aku_pal_source_probe as probe


class AKUPALW17SafeProbeTests(unittest.TestCase):
    def test_expected_exactly_eight_source_records_and_six_witnesses(self):
        self.assertEqual((6036,2448,23466,6066,32833,56377,5862,5447),probe.RECORDS)

    def test_external_unguarded_urls_refused(self):
        for url in ("http://aku-pal.uni-mainz.de/signs/6036",
                    "https://untrusted.example/signs/6036",
                    "file:///etc/passwd"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    probe.page_probe(url)

    def test_url_escapes_not_allowed_by_exact_origin(self):
        with self.assertRaises(ValueError):
            probe.page_probe("https://aku-pal.uni-mainz.de.evil.example/signs/6036")

    def test_unavailable_sources_remain_explicitly_unverified(self):
        with patch.object(probe.urllib.request,"urlopen",side_effect=probe.urllib.error.URLError("blocked")):
            result=probe.page_probe(probe.ORIGIN+"/signs/6036")
        self.assertEqual("UNAVAILABLE",result["status"])
        self.assertIsNone(result["original_sha256"])
        self.assertFalse(result["contains_ccby"])
        self.assertEqual(0,result["original_image_bytes_acquired"])

    def test_source_page_http_200_does_not_claim_gold_or_train_admission(self):
        class Headers:
            def get(self,*a): return "text/html"
        class FakeResponse:
            status=200
            headers=Headers()
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def read(self,n):return b'<html><div>CC BY 4.0</div><img src="sample"></html>'
            def geturl(self):return probe.ORIGIN+"/signs/6036"
        with patch.object(probe.urllib.request,"urlopen",return_value=FakeResponse()):
            result=probe.page_probe(probe.ORIGIN+"/signs/6036")
        self.assertTrue(result["contains_ccby"])
        self.assertEqual(1,result["image_reference_count"])
        self.assertEqual(0,result["original_image_bytes_acquired"])
        self.assertEqual("HTTP_200_SOURCE_BYTES_VERIFIED",result["status"])

    def test_synthetic_negative_binary_source_over_limit_refused(self):
        class Headers:
            def get(self,*a):return "text/html"
        class FakeResponse:
            status=200
            headers=Headers()
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def read(self,n):return b'x'*n
            def geturl(self):return probe.ORIGIN+"/signs/6036"
        with patch.object(probe.urllib.request,"urlopen",return_value=FakeResponse()):
            result=probe.page_probe(probe.ORIGIN+"/signs/6036",max_bytes=50)
        self.assertEqual("UNAVAILABLE",result["status"])
        self.assertIsNone(result["original_sha256"])
