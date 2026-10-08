from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from tools import lexical_interpretation as lexical
from tools import linguistic_normalization as normalization
from tools.source_registry import load_yaml

ROOT = Path(__file__).resolve().parents[2]
ANNOTATION_PATH = ROOT / "data/examples/annotation_ambiguous.yaml"
REQUEST_PATH = ROOT / "ling/normalization/examples/synthetic.yaml"
LEXICON_PATH = ROOT / "ling/lexical/examples/synthetic.yaml"


class LexicalInterpretationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / "schemas/lexical_interpretation.schema.json").read_text(encoding="utf-8"))
        cls.registry = load_yaml(ROOT / "data/sources/registry.yaml")

    def setUp(self):
        annotation, raw = normalization.read(ANNOTATION_PATH)
        request, _ = normalization.read(REQUEST_PATH)
        # Bind this synthetic request to this checkout's exact fixture bytes.
        request["annotation_sha256"] = hashlib.sha256(raw).hexdigest()
        self.manifest = normalization.build(request, annotation, raw, self.registry)
        self.lexicon, _ = lexical.read_data(LEXICON_PATH)

    @staticmethod
    def reseal_manifest(manifest):
        identity = {k: copy.deepcopy(v) for k, v in manifest.items() if k not in {"schema_version", "normalization_version_id"}}
        manifest["normalization_version_id"] = "ling-" + lexical.digest(lexical.canonical(identity))

    def test_synthetic_cli_and_output_are_deterministic_and_preserve_alternatives(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "normalization.json"
            output = Path(folder) / "interpretation.json"
            source.write_text(json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")
            checked = subprocess.run([sys.executable, "-m", "tools.lexical_interpretation", "validate", str(source), "--lexicon", str(LEXICON_PATH)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, checked.returncode, checked.stderr)
            first = lexical.build(self.manifest, self.lexicon, self.registry, self.schema)
            second = lexical.build(self.manifest, self.lexicon, self.registry, self.schema)
            self.assertEqual(first, second)
            unit = first["items"][0]
            self.assertEqual("ambiguous", unit["outcome"])
            self.assertEqual(["transliteration-a", "transliteration-b"], unit["source_value_ids"])
            self.assertEqual(["SYNTHETIC-READING-A", "SYNTHETIC-READING-B"], [r["normalized_text"] for r in unit["readings"]])
            self.assertEqual("SYNTHETIC-READING-A", unit["diplomatic_transliteration"]["values"][0]["value"])
            self.assertFalse(first["metrics"]["computed"])
            written = subprocess.run([sys.executable, "-m", "tools.lexical_interpretation", "interpret", str(source), "--lexicon", str(LEXICON_PATH), "--output", str(output)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, written.returncode, written.stderr)
            self.assertEqual(first, json.loads(output.read_text(encoding="utf-8")))

    def test_normalization_hash_drift_fails_closed(self):
        changed = copy.deepcopy(self.manifest)
        changed["annotation"]["sha256"] = "0" * 64
        errors = lexical.validate_normalization(changed, self.schema)
        self.assertTrue(any("normalization_version_id" in error for error in errors), errors)

    def test_exact_unicode_form_hash_and_normalized_value_hash_are_checked(self):
        changed_lexicon = copy.deepcopy(self.lexicon)
        changed_lexicon["entries"][0]["form"] = "SYNTHETIC-READING-Á"
        self.assertTrue(any("form_sha256" in error for error in lexical.validate_lexicon(changed_lexicon, self.schema, self.registry)))
        changed = copy.deepcopy(self.manifest)
        changed["items"][0]["values"][0]["normalized_text"] += "x"
        self.assertTrue(any("normalized text/hash mismatch" in error for error in lexical.validate_normalization(changed, self.schema)))

    def test_unknown_missing_and_unattested_are_distinct(self):
        missing = copy.deepcopy(self.manifest)
        missing["items"][0]["gold_status"] = "missing_annotation"
        self.reseal_manifest(missing)
        result = lexical.build(missing, self.lexicon, self.registry, self.schema)
        self.assertEqual("unknown", result["items"][0]["outcome"])
        unknown_form = copy.deepcopy(self.manifest)
        unknown_form["items"] = [copy.deepcopy(unknown_form["items"][0])]
        item = unknown_form["items"][0]
        item["gold_status"] = "certain"
        item["values"] = [copy.deepcopy(item["values"][1])]
        item["acceptable_reading_ids"] = [item["values"][0]["source_value_id"]]
        self.reseal_manifest(unknown_form)
        result = lexical.build(unknown_form, self.lexicon, self.registry, self.schema)
        self.assertEqual("unattested", result["items"][0]["outcome"])

    def test_conflicting_analyses_are_all_preserved_as_ambiguous(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["items"][0]["gold_status"] = "certain"
        manifest["items"][0]["values"] = [copy.deepcopy(manifest["items"][0]["values"][0])]
        manifest["items"][0]["acceptable_reading_ids"] = ["transliteration-a"]
        self.reseal_manifest(manifest)
        lexicon = copy.deepcopy(self.lexicon)
        duplicate = copy.deepcopy(lexicon["entries"][0])
        duplicate.update({"entry_id": "synthetic-analysis-b", "lemma": {"lemma_id": "synthetic-lemma-b", "value": "SYNTHETIC-LEMMA-B"}})
        lexicon["entries"].append(duplicate)
        result = lexical.build(manifest, lexicon, self.registry, self.schema)
        self.assertEqual("ambiguous", result["items"][0]["outcome"])
        self.assertEqual(["synthetic-analysis-a", "synthetic-analysis-b"], [a["entry_id"] for a in result["items"][0]["readings"][0]["analyses"]])

    def test_unsupported_morphology_is_rejected(self):
        lexicon = copy.deepcopy(self.lexicon)
        lexicon["entries"][0]["grammatical_features"]["invented_category"] = "asserted"
        self.assertTrue(lexical.validate_lexicon(lexicon, self.schema, self.registry))

    def test_invalid_source_citations_and_unverified_rights_fail_closed(self):
        lexicon = copy.deepcopy(self.lexicon)
        entry = lexicon["entries"][0]
        entry["scientific_status"] = "scholarly_candidate"
        lexicon["scientific_status"] = "scholarly_candidate"
        entry["rights"] = {"rights_class": "OPEN-BY", "intended_use": "research", "attribution": "required", "review_status": "independently_verified"}
        entry["attestations"] = [{"citation": {"citation_id": "citation-1", "bibliographic_reference": "Unverified source citation", "locator": "p. 1", "url": "https://example.org/item", "verification_evidence_url": "https://example.org/evidence", "verified_by": "reviewer", "verified_at": "2026-10-08"}, "source_identity": {"source_registry_id": "SRC-MISSING", "source_object_id": "object-1", "source_content_sha256": "a" * 64}, "historical_period": None, "context": "synthetic test", "confidence": 0.1, "uncertainty": []}]
        errors = lexical.validate_lexicon(lexicon, self.schema, self.registry)
        self.assertTrue(any("invalid source reference" in error for error in errors), errors)
        entry["attestations"][0]["source_identity"]["source_registry_id"] = "SRC-HPDB"
        entry["rights"]["review_status"] = "pending"
        errors = lexical.validate_lexicon(lexicon, self.schema, self.registry)
        self.assertTrue(any("rights are not independently cleared" in error for error in errors), errors)

    def test_unicode_normalization_collision_keeps_both_source_readings(self):
        manifest = copy.deepcopy(self.manifest)
        item = manifest["items"][0]
        item["gold_status"] = "uncertain_with_alternatives"
        one, two = copy.deepcopy(item["values"])
        one["normalized_text"] = "Å"
        two["normalized_text"] = "Å"
        for val in (one, two):
            val["normalized_sha256"] = lexical.digest(val["normalized_text"].encode("utf-8"))
        item["values"] = [one, two]
        item["acceptable_reading_ids"] = [one["source_value_id"], two["source_value_id"]]
        self.reseal_manifest(manifest)
        result = lexical.build(manifest, self.lexicon, self.registry, self.schema)
        self.assertEqual("ambiguous", result["items"][0]["outcome"])
        self.assertEqual(2, len(result["items"][0]["readings"]))
        self.assertNotEqual(result["items"][0]["readings"][0]["normalized_text"], result["items"][0]["readings"][1]["normalized_text"])




class RealPublishedEgyptianLexicalTests(unittest.TestCase):
    """Full genuine AED dictionary + AES source-text-held-out test suite."""

    @classmethod
    def setUpClass(cls):
        from ling.lexical import aes_holdout as scholar
        cls.scholar = scholar
        cls.bundle = scholar.read_bundle()

    def test_real_source_35k_lemmas_445_sentences_311_text_groups(self):
        b = self.bundle
        self.assertEqual(35052, len(b["lemmas"]))
        self.assertEqual(445, b["manifest"]["aes"]["expected_sentences"])
        self.assertEqual(2526, len(b["tokens"]))
        self.assertEqual(311, len(b["texts"]))
        self.assertEqual(2305, sum(bool(t["lemmaID"]) for t in b["tokens"]))
        self.assertEqual("CC-BY-SA-4.0", b["manifest"]["license"])
        self.assertEqual("not_admitted_DATA008", b["manifest"]["train_dev_release"])

    def test_actual_publisher_blob_identifiers_and_manifest_integrity(self):
        from ling.lexical.aes_holdout import _blob, EXPECTED_AES_SHA, EXPECTED_PART_SHA, DATA
        p = DATA / "aes_felsinschriften_ccby_sa.json"
        self.assertGreater(len(_blob(p, EXPECTED_AES_SHA, size_limit=2_000_000)), 1_000_000)
        for i, sha in enumerate(EXPECTED_PART_SHA, 1):
            p = DATA / f"aed_lemmas_part{i:02d}.jsonl"
            self.assertTrue(_blob(p, sha, size_limit=1_500_000))

    def test_real_aed_lemma_identity_and_attested_english_gloss(self):
        lemma = self.bundle["lemmas"]["tla1"]
        self.assertEqual("ꜣ", lemma["form"])
        self.assertEqual("substantive/substantive_masc", lemma["pos_source"])
        self.assertEqual("tla863246", lemma["root_ref"])
        self.assertEqual("vulture; bird (gen.)", lemma["english_gloss"])

    def test_actual_scholarly_lookup_returns_lemma_and_alternatives_without_gold(self):
        s = self.scholar.analyse(self.bundle, "ꜣ")
        self.assertIn(s["outcome"], {"interpreted", "ambiguous"})
        self.assertIn("1", {x["lemma_id"] for x in s["candidates"]})
        candidate = next(x for x in s["candidates"] if x["lemma_id"] == "1")
        self.assertIn("AED_DICTIONARY_EXACT_LEMMA_FORM", candidate["source_layers"])
        self.assertEqual("substantive/substantive_masc", candidate["dictionary_pos"])
        self.assertFalse(s["training_corpus_admitted"])
        self.assertFalse(s["certified_science"])

    def test_all_311_source_texts_held_out_and_scored_without_fake_accuracy(self):
        report = self.scholar.evaluate(self.bundle)
        self.assertEqual(311, report["source_text_groups"])
        counts = report["metrics"]
        self.assertEqual(2526, counts["tokens_total"])
        self.assertEqual(2305, counts["tokens_with_published_lemma"])
        self.assertGreater(counts["lemma_in_candidates"], 500)
        self.assertGreater(counts["single_lemma_candidate"], 50)
        self.assertGreater(counts["tokens_with_published_morphology"], 100)
        self.assertEqual("BLOCKED", report["training_admission"])
        self.assertEqual(0, report["scored_blind_gold_evaluations"])
        self.assertEqual(0, report["certified_hieratic_image_reading_experiments"])
        self.assertEqual(64, len(report["report_sha256"]))
        import json
        print("LING002_REAL_SCHOLARLY_DIAGNOSTIC=" + json.dumps({"source_text_groups": report["source_text_groups"], "scoreable_text_groups": report["source_text_groups_with_scoreable_lemma"], "counts": counts, "ratios": report["ratios"], "report_sha256": report["report_sha256"]}, ensure_ascii=False, sort_keys=True))
        for ratio in report["ratios"].values():
            if ratio is not None:
                self.assertGreaterEqual(ratio, 0)
                self.assertLessEqual(ratio, 1)

    def test_predictions_are_invariant_to_gold_poison_from_own_text(self):
        import copy
        scholar = self.scholar
        base = copy.deepcopy(self.bundle)
        form_token = next(t for t in base["tokens"]
                          if t["written_form"] and t["lemmaID"])
        base.pop("observations", None)
        before = scholar.analyse(
            base, form_token["written_form"], excluded_text_id=form_token["text"])
        # A leaked target text would make source-gold mutation change the answer.
        for token in base["tokens"]:
            if token["text"] == form_token["text"]:
                token["lemmaID"] = "999999999999"
                token["pos"] = "FORGED"
                token["features"] = {"genus": "forged"}
        base.pop("observations", None)
        after = scholar.analyse(
            base, form_token["written_form"], excluded_text_id=form_token["text"])
        self.assertEqual(before, after)

    def test_do_not_transfer_morphology_from_same_text_to_itself(self):
        s = self.scholar
        b = self.bundle
        tokens_by_form = {}
        for token in b["tokens"]:
            if token["written_form"] and token["lemmaID"]:
                tokens_by_form.setdefault(token["written_form"], []).append(token)
        selected = next(
            token for token in b["tokens"]
            if token["features"] and token["lemmaID"] and token["written_form"]
            and all(x["text"] == token["text"]
                    for x in tokens_by_form[token["written_form"]])
        )
        result = s.analyse(b, selected["written_form"],
                           excluded_text_id=selected["text"])
        self.assertTrue(all(not row["observed_morphology_alternatives"]
                            for row in result["candidates"]))

    def test_source_publisher_markup_and_morphology_not_inferred(self):
        for sample in self.bundle["tokens"][:200]:
            self.assertIsInstance(sample["features"], dict)
        result = self.scholar.analyse(self.bundle, "NOT-A-SCHOLARLY-EGYPTIAN-FORM")
        self.assertEqual("unattested", result["outcome"])
        self.assertEqual([], result["candidates"])

    def test_tampered_lexicon_bytes_and_aes_bytes_fail_closed(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            altered = root / "aed_lemmas_part01.jsonl"
            original = self.scholar.DATA / altered.name
            altered.write_bytes(original.read_bytes() + b"\n")
            with self.assertRaisesRegex(self.scholar.SourceError, "identity mismatch"):
                self.scholar._blob(
                    altered, self.scholar.EXPECTED_PART_SHA[0], size_limit=1_500_000)
            aes = root / "aes.json"
            aes.write_bytes((self.scholar.DATA /
                             "aes_felsinschriften_ccby_sa.json").read_bytes() + b" ")
            with self.assertRaisesRegex(self.scholar.SourceError, "identity mismatch"):
                self.scholar._blob(
                    aes, self.scholar.EXPECTED_AES_SHA, size_limit=2_000_000)

    def test_forged_manifest_rights_and_source_revision_are_rejected(self):
        import tempfile, json
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mf = json.loads((self.scholar.DATA /
                             "scholarly_source_manifest.json").read_text("utf-8"))
            mf["train_dev_release"] = "production_approved"
            (root / "scholarly_source_manifest.json").write_text(
                json.dumps(mf), encoding="utf-8")
            with self.assertRaisesRegex(self.scholar.SourceError,
                                        "train_dev_release"):
                self.scholar._load_manifest(root)
            mf["train_dev_release"] = "not_admitted_DATA008"
            mf["aed"]["revision"] = "forged"
            (root / "scholarly_source_manifest.json").write_text(
                json.dumps(mf), encoding="utf-8")
            with self.assertRaisesRegex(self.scholar.SourceError,
                                        "publisher source revision"):
                self.scholar._load_manifest(root)

    def test_real_cli_verify_lookup_evaluate(self):
        from tools import lexical_interpretation as cli
        import contextlib, io, json
        for argv, key in [
            (["scholarly-aes", "verify"], "aed_lemmas"),
            (["scholarly-aes", "lookup", "--form", "ꜣ"], "candidates"),
            (["scholarly-aes", "evaluate"], "metrics"),
        ]:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(0, cli.main(argv))
            self.assertIn(key, json.loads(output.getvalue()))

    def test_no_network_licensed_scholarly_data_only(self):
        from pathlib import Path
        code = Path(self.scholar.__file__).read_text("utf-8")
        for term in ("requests.get(", "urlopen(", "httpx.get(", "Image.open(",
                     "torch.load(", "model.generate("):
            self.assertNotIn(term, code)
        self.assertNotIn("visual_accuracy", self.scholar.evaluate(self.bundle))


if __name__ == "__main__":
    unittest.main()
