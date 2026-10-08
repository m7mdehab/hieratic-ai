"""Real, source-pinned AES German translation diagnostic tests (not gold OCR)."""
from __future__ import annotations
import copy
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import translation_layer as tr


class RealPublishedTranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = tr.load_sentences()

    def test_actual_publisher_counts_source_identity_rights(self):
        self.assertEqual(445, len(self.dataset["sentences"]))
        self.assertEqual(444, self.dataset["translation_count"])
        self.assertEqual(311, self.dataset["source_groups"])
        self.assertEqual("7bfcba9678b64c3526a1123996a0714b5f76812f", self.dataset["original_blob"])
        self.assertEqual("CC-BY-SA-4.0", self.dataset["publisher_rights"])

    def test_real_nonzero_heldout_translation_diagnostic(self):
        report = tr.evaluate(self.dataset)
        self.assertEqual(445, report["metrics"]["all_sentences"])
        self.assertEqual(444, report["metrics"]["scored_sentences"])
        self.assertEqual(1, report["metrics"]["missing_publisher_reference_translation"])
        self.assertEqual(311, report["source_text_groups_total"])
        self.assertGreater(report["metrics"]["tokens_total"], 2300)
        self.assertGreater(report["metrics"]["sentences_with_any_gloss"], 0)
        self.assertGreater(report["corpus_micro_word_f1"], 0.0)
        self.assertLessEqual(report["corpus_micro_word_f1"], 1.0)
        self.assertFalse(report["certified_model_performance"])
        self.assertFalse(report["expert_blind_gold"])
        self.assertFalse(report["fluent_translation_evaluation"])

    def test_reproducible_full_report_identity(self):
        left = tr.evaluate(self.dataset)
        right = tr.evaluate(self.dataset)
        self.assertEqual(left, right)
        self.assertEqual(64, len(left["report_sha256"]))
        self.assertEqual(left["report_sha256"],
                         tr.sha256(tr._canonical({k: v for k, v in left.items()
                                                  if k != "report_sha256"})).hexdigest())

    def test_holdout_no_self_cotext_influence(self):
        actual = copy.deepcopy(self.dataset["sentences"])
        sid, sample = next((sid, s) for sid, s in actual.items()
                           if len(s["token"]) > 1)
        origin = sample["text"]
        before = tr.translate_sentence(sample, tr._observations(actual))
        for s in actual.values():
            if s["text"] == origin:
                s["sentence_translation"] = "UNRELATED FORGED TARGET TEXT"
                for token in s["token"]:
                    token["cotext_translation"] = "FORGED SECRET TARGET"
        after = tr.translate_sentence(actual[sid], tr._observations(actual))
        self.assertEqual(before, after)
        self.assertNotIn("FORGED SECRET", after["gloss_sequence"])
        self.assertNotIn("UNRELATED", after["gloss_sequence"])

    def test_no_target_gold_lemma_pos_or_lexical_labels_are_used(self):
        actual = copy.deepcopy(self.dataset["sentences"])
        sid, sent = next((sid, s) for sid, s in actual.items() if s["token"])
        before = tr.translate_sentence(sent, tr._observations(actual))
        sent["sentence_translation"] = "HIDDEN PUBLISHER REFERENCE"
        for t in sent["token"]:
            t["lemmaID"] = "999999999"
            t["pos"] = "FORGED"
            t["cotext_translation"] = "FORGED"
        after = tr.translate_sentence(sent, tr._observations(actual))
        self.assertEqual(before, after)

    def test_distinct_homograph_glosses_remain_alternatives(self):
        observations = {"m": [
            ("other-text-a", "in", "1"), ("other-text-b", "from", "2"),
            ("other-text-c", "in", "3"),
        ]}
        sent = {"text": "target-text", "token": [{"written_form": "m"}],
                "sentence_translation": "unrelated"}
        result = tr.translate_sentence(sent, observations)
        self.assertEqual("in", result["gloss_sequence"])
        self.assertEqual(["in", "from"], result["units"][0]["alternatives"])
        self.assertEqual(2, result["units"][0]["independent_source_text_support"])
        self.assertEqual("ORDERED_GERMAN_WORD_GLOSS_SEQUENCE_NOT_FLUENT_TRANSLATION",
                         result["output_type"])

    def test_missing_gloss_is_abstention_not_hallucinated_translation(self):
        sent = {"text": "target", "token": [
            {"written_form": "not-attested"},
            {"written_form": "m"},
        ], "sentence_translation": "secret"}
        output = tr.translate_sentence(sent, {"m": [("target", "in", "")]})
        self.assertEqual("[?] [?]", output["gloss_sequence"])
        self.assertEqual(2, output["tokens_abstained"])

    def test_competing_source_words_and_punctuation_scoring_diagnostic(self):
        assert tr.word_f1("Der König!", "der König")["f1"] == 1.0
        assert tr.word_f1("another word", "der König")["f1"] == 0.0
        x = tr.word_f1("[?]", "der König")
        self.assertEqual(0.0, x["recall"])

    def test_no_gold_text_exposure_in_default_prediction(self):
        sid, sent = next((sid, s) for sid, s in self.dataset["sentences"].items()
                         if s["sentence_translation"].strip())
        out = tr.translate_sentence(sent, tr._observations(self.dataset["sentences"]))
        self.assertNotIn("publisher_sentence_translation", out)
        self.assertNotIn("sentence_translation", json.dumps(out))
        self.assertFalse(out["publisher_target_translation_used_for_generation"])

    def test_adversarial_modified_publisher_bytes_rejected(self):
        from ling.lexical import aes_holdout
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "aes.json"
            original = (aes_holdout.DATA / "aes_felsinschriften_ccby_sa.json").read_bytes()
            p.write_bytes(original + b" ")
            with self.assertRaisesRegex(aes_holdout.SourceError, "identity mismatch"):
                aes_holdout._blob(p, aes_holdout.EXPECTED_AES_SHA, size_limit=2_000_000)

    def test_cli_verify_and_predict_without_reference_answer(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(0, tr.main(["verify"]))
        self.assertEqual(444, json.loads(out.getvalue())["publisher_translated_sentences"])
        sid = next(iter(self.dataset["sentences"]))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(0, tr.main(["predict", "--sentence-id", sid]))
        pred = json.loads(out.getvalue())
        self.assertNotIn("publisher_sentence_translation", pred)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(1, tr.main(["predict", "--sentence-id", "BAD-ID"]))

    def test_no_network_and_no_image_claim(self):
        src = Path(tr.__file__).read_text("utf-8")
        for banned in ("requests.get(", "urlopen(", "model.generate(", "torch.load("):
            self.assertNotIn(banned, src)
        r = tr.evaluate(self.dataset)
        self.assertFalse(r["image_recognition_evaluation"])
        self.assertFalse(r["scientific_release_admitted"])


if __name__ == "__main__":
    unittest.main()
