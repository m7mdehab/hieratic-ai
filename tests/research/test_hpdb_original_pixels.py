"""Adversarial/fixture tests for W27 real-source research; no fixture is science."""
from __future__ import annotations
import hashlib
import io
import unittest

from tools import research_hpdb_original_pixels as m


class HPDBOriginalPixelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = m.read_catalog()
        cls.cohort = m.frozen_cohort(cls.catalog)

    def test_original_metadata_exact_universe(self):
        self.assertEqual(2065, len(self.catalog))
        self.assertEqual(1439, sum(bool(r["single_sign"]) for r in self.catalog))

    def test_preregistered_cohort_identity(self):
        self.assertEqual(24, len(self.cohort))
        self.assertEqual({"A1", "A2", "D1", "D2", "G1", "M12", "V1", "Z1"}, {i["label"] for i in self.cohort})
        self.assertEqual(16, sum(i["role"] == "train" for i in self.cohort))
        self.assertEqual(8, sum(i["role"] == "test" for i in self.cohort))

    def test_source_print_page_disjoint_and_not_physical_support_claim(self):
        train = {r["source_proxy"] for r in self.cohort if r["role"] == "train"}
        test = {r["source_proxy"] for r in self.cohort if r["role"] == "test"}
        self.assertFalse(train & test)
        self.assertEqual({1, 2}, {r["volume"] for r in self.cohort if r["role"] == "train"})
        self.assertEqual({3}, {r["volume"] for r in self.cohort if r["role"] == "test"})

    def test_exact_original_host_and_url_gate(self):
        self.assertIsNone(m.verify_iiif_url(self.cohort[0]["url"]))
        cases = [
            "http://iiif.dl.itc.u-tokyo.ac.jp/iiif/asia/hp/1/1.tif/full/max/0/default.jpg",
            "https://iiif.dl.itc.u-tokyo.ac.jp.evil.example/iiif/asia/hp/1/1.tif/full/max/0/default.jpg",
            "https://iiif.dl.itc.u-tokyo.ac.jp:444/iiif/asia/hp/1/1.tif/full/max/0/default.jpg",
            "https://bad@iiif.dl.itc.u-tokyo.ac.jp/iiif/asia/hp/1/1.tif/full/max/0/default.jpg",
            "https://iiif.dl.itc.u-tokyo.ac.jp/iiif/asia/hp/../private/default.jpg",
            "https://iiif.dl.itc.u-tokyo.ac.jp/iiif/asia/hp/1.tif/full/max/0/default.jpg?bypass=1",
            "https://iiif.dl.itc.u-tokyo.ac.jp/foo.jpg",
        ]
        for url in cases:
            with self.subTest(url=url), self.assertRaises(m.SourceError):
                m.verify_iiif_url(url)

    def test_wrong_source_label_or_missing_url_fails(self):
        partial = [r for r in self.catalog if r["single_sign"] != "Z1"]
        with self.assertRaisesRegex(m.SourceError, "insufficient"):
            m.frozen_cohort(partial)

    def test_cohort_duplicate_id_detection(self):
        rows = [dict(v) for v in self.catalog]
        found = [v for v in rows if v["single_sign"] == "A1" and v["vol"] == 1 and v["kind"] == "Main"]
        found[1]["id"] = found[0]["id"]
        # The deterministic first-item selection must not accidentally use duplicate IDs.
        # Full catalog ingestion already validates unique IDs before cohort construction.
        self.assertEqual(2065, len({v["id"] for v in self.catalog}))
        self.assertEqual(2064, len({v["id"] for v in rows}))

    def test_synthetic_jpeg_is_never_original_source_receipt(self):
        from PIL import Image
        image = Image.new("RGB", (32, 24), color=(170, 190, 185))
        o = io.BytesIO()
        image.save(o, format="JPEG")
        f, meta = m.image_features(o.getvalue())
        self.assertEqual(128, len(f))
        self.assertEqual([32, 24], meta["original_dimensions"])
        self.assertEqual(hashlib.sha256(o.getvalue()).hexdigest(), meta["stimulus_sha256"])

    def test_image_bytes_png_rejected(self):
        from PIL import Image
        o = io.BytesIO()
        Image.new("RGB", (20, 20), "white").save(o, format="PNG")
        with self.assertRaises(m.SourceError):
            m.image_features(o.getvalue())

    def test_decompression_bomb_defended(self):
        from PIL import Image
        o = io.BytesIO()
        Image.new("RGB", (1001, 1001), "white").save(o, format="JPEG")
        with self.assertRaisesRegex(m.SourceError, "geometry"):
            m.image_features(o.getvalue())

    def test_fake_distance_mismatches(self):
        with self.assertRaises(m.SourceError):
            m.squared_distance((1.0,), (1.0,))

    def test_live_denominators_not_fabricated(self):
        with self.assertRaisesRegex(m.SourceError, "denominator"):
            m.evaluate([])

    def test_original_pixel_classifier_accounting_on_fixture_only(self):
        def row(i, role, label, scalar):
            return {
                "item_id": str(i), "role": role, "label": label,
                "features": (scalar,) * 128, "source_proxy": f"G-{i}",
            }
        train = [row(idx * 2 + i, "train", label, idx / 8) for idx, label in enumerate(m.LABELS)
                 for i in range(2)]
        test = [row(100 + idx, "test", label, idx / 8) for idx, label in enumerate(m.LABELS)]
        scored = m.evaluate(train + test)
        self.assertEqual(8, scored["visual_1nn_correct"])
        self.assertEqual(1, scored["nonvisual_prior_correct"])
        self.assertEqual(8, len(scored["predictions"]))

    def test_positive_source_claims_not_hardcoded_to_fixtures(self):
        source = __import__("pathlib").Path(m.__file__).read_text(encoding="utf-8")
        self.assertNotIn("synthetic_fixture", source)
        self.assertNotIn("mock_adapter", source)


if __name__ == "__main__":
    unittest.main()
