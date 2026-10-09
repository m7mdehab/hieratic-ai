"""R026 source-only forensic integrity, no original Egyptian assets in CI."""
import copy,json,unittest
from unittest.mock import patch
from tools import research_cat1880_retrieval as p

class OriginalResearchByteGates(unittest.TestCase):
    def test_only_exact_original_source_origins(self):
        self.assertTrue(p.url_ok("https://commons.wikimedia.org/w/api.php"))
        self.assertTrue(p.url_ok("https://upload.wikimedia.org/wikipedia/commons/a/b/c.jpg",media=True))
        for url in ("http://commons.wikimedia.org/w/api.php","https://commons.wikimedia.org.evil.tld/w/api.php",
                    "https://commons.wikimedia.org/wiki/File:danger", "https://evil.tld/c.jpg",
                    "https://user:pass@upload.wikimedia.org/c.jpg"):
            self.assertFalse(p.url_ok(url,media=url.endswith(".jpg")))
    def test_cc0_not_confused_with_nc_and_pdm(self):
        meta={"extmetadata":{"LicenseShortName":{"value":"CC BY-NC-SA 4.0"},
                             "LicenseUrl":{"value":"https://creativecommons.org/licenses/by-nc-sa/4.0/"}}}
        self.assertFalse(p.license_evidence(p.SOURCES[0],meta)[0])
        self.assertFalse(p.license_evidence(p.SOURCES[1],meta)[0])
        meta["extmetadata"]["LicenseShortName"]["value"]="CC0 1.0"
        self.assertTrue(p.license_evidence(p.SOURCES[0],meta)[0])
        self.assertFalse(p.license_evidence(p.SOURCES[1],meta)[0])
        meta["extmetadata"]["LicenseShortName"]["value"]="Public domain"
        self.assertFalse(p.license_evidence(p.SOURCES[0],meta)[0])
        self.assertTrue(p.license_evidence(p.SOURCES[1],meta)[0])
    def test_pdm_contact_sheet_never_stored_as_original_asset(self):
        self.assertFalse(any("CORPUS_V1" in item["key"] for item in p.SOURCES))
        self.assertTrue(all(item["max_bytes"]<50_000_000 for item in p.SOURCES))

    def test_source_ids_fixed(self):
        self.assertEqual(2,len(p.SOURCES))
        self.assertEqual("MuseoEgizio:Cat.1880",p.SOURCES[0]["source"])
        self.assertIn("papyrusdeturin02muse",p.SOURCES[1]["title"])
    def test_unavailable_api_leaves_no_magic_bytes_or_fake_sha(self):
        with patch.object(p,"first_image_info",side_effect=ValueError("blocked")):
            result=p.inspect(p.SOURCES[0])
        self.assertEqual("BLOCKED_ORIGINAL_SOURCE_EVIDENCE",result["status"])
        self.assertIsNone(result["original_sha256"])
        self.assertFalse(result["admitted_training"])
    def test_item_license_failure_must_never_request_media(self):
        meta={"mime":"image/jpeg","size":1000,"sha1":"0"*40,
              "url":"https://upload.wikimedia.org/wikipedia/commons/a/a/a.jpg",
              "extmetadata":{"LicenseShortName":{"value":"CC BY-NC-SA 4.0"}}}
        with patch.object(p,"first_image_info",return_value=(meta,"a"*64)):
            with patch.object(p,"http_bytes",side_effect=AssertionError("ILLEGAL DOWNLOAD")):
                z=p.inspect(p.SOURCES[0])
        self.assertEqual("BLOCKED_NO_ITEM_LICENSE_IN_PUBLISHER_RECORD",z["status"])
        self.assertFalse(z["source_media_original_downloaded"])
    def test_item_url_and_size_mismatch_fails(self):
        meta={"mime":"image/jpeg","size":2,"sha1":"0"*40,
              "url":"https://evil.test/evil.jpg",
              "extmetadata":{"LicenseShortName":{"value":"CC0 1.0"}}}
        with patch.object(p,"first_image_info",return_value=(meta,"a"*64)):
            with patch.object(p,"http_bytes",side_effect=ValueError("bad origin")):
                z=p.inspect(p.SOURCES[0])
        self.assertEqual("BLOCKED_ORIGINAL_SOURCE_EVIDENCE",z["status"])
        self.assertIsNone(z["original_sha256"])
if __name__=="__main__":unittest.main()
