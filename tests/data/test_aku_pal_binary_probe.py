"""W19 main-publisher item licences, URL and image integrity safety."""
import unittest
from unittest.mock import patch
from data.releases import w19_aku_pal_binary_probe as p


class OriginalSignBinaryGates(unittest.TestCase):
    def test_exact_scope_and_hostname(self):
        self.assertTrue(p.same_origin("https://aku-pal.uni-mainz.de/api/signs/6036"))
        for url in ("http://aku-pal.uni-mainz.de/api/signs/6036",
                    "https://aku-pal.uni-mainz.de.evil.test/assets.svg",
                    "https://attacker:pass@aku-pal.uni-mainz.de/a.svg",
                    "file:///tmp/a.svg"):
            with self.subTest(url=url):self.assertFalse(p.same_origin(url))

    def test_unreviewed_ids_refused(self):
        with self.assertRaises(ValueError):p.inspect_one(99999)

    def test_only_media_fields_in_official_record_are_candidates(self):
        leaves=[{"key":"image.url","safe_metadata_value":"/media/a.svg"},
                {"key":"description","safe_metadata_value":"/api/admin/export"},
                {"key":"image.external","safe_metadata_value":"https://evil.test/a.svg"},
                {"key":"image.query","safe_metadata_value":"/media/a.svg?token=secret"}]
        self.assertEqual([{"field":"image.url","url":p.ORIGIN+"/media/a.svg"}],p.candidates_from_metadata(leaves))

    def test_unlicensed_record_never_fetches_image(self):
        fake={"id":6036,"license":"CC BY-NC-SA 4.0","image":{"url":"/media/a.svg"}}
        def fake_get(url,*args):
            self.assertIn("/api/signs/",url)
            import json
            return json.dumps(fake).encode(),"application/json"
        with patch.object(p,"bounded_get",side_effect=fake_get) as get:
            result=p.inspect_one(6036)
        self.assertEqual("BLOCKED_NOT_CONFIRMED_EXACT_RECORD_RIGHTS",result["media_status"])
        self.assertFalse(result["license_per_item_confirmed"])
        self.assertEqual(1,get.call_count)

    def test_licensed_binary_success_without_gold_admission(self):
        import json
        fake={"id":6036,"license":"CC BY 4.0","image":{"url":"/media/a.svg"}}
        def fake_get(url,*args):
            if "/api/signs/" in url:return json.dumps(fake).encode(),"application/json"
            return b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',"image/svg+xml"
        with patch.object(p,"bounded_get",side_effect=fake_get):
            result=p.inspect_one(6036)
        self.assertEqual(1,result["source_binary_images_verified"])
        self.assertEqual(False,result["training_admission"])
        self.assertFalse(result["gold_admission"])

    def test_single_item_wrapped_publisher_array(self):
        import json
        obj=[{"id":6036,"license":"CC BY 4.0","image":{"url":"/media/a.svg"}}]
        with patch.object(p,"bounded_get",side_effect=lambda url,*args:
              (json.dumps(obj).encode(),"application/json") if "/api/signs/" in url
              else (b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',"image/svg+xml")):
            res=p.inspect_one(6036)
        self.assertEqual("VERIFIED_PUBLISHER_JSON",res["record"])
        self.assertEqual(1,res["source_binary_images_verified"])

    def test_nested_item_licence_and_image(self):
        import json
        doc={"id":6036,"images":[{"type":"SVG","values":["/img/data/ht/svg/ht_6036.svg"]}],
             "details":[{"items":[
                 {"key":"license","label":"Lizenz","values":["CC BY 4.0"]}]}]}
        def mockfetch(url,*args):
            if "/api/signs/" in url:return json.dumps(doc).encode(),"application/json"
            return b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',"image/svg+xml"
        with patch.object(p,"bounded_get",side_effect=mockfetch):
            result=p.inspect_one(6036)
        self.assertTrue(result["license_per_item_confirmed"])
        self.assertEqual(1,result["source_binary_images_verified"])
        self.assertFalse(result["training_admission"])

    def test_unreliable_original_id_cannot_admit(self):
        with patch.object(p,"bounded_get",return_value=(b'{"id":999,"license":"CC BY 4.0"}',"application/json")):
            res=p.inspect_one(6036)
        self.assertEqual("UNAVAILABLE",res["record"])
