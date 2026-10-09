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


    def test_real_cross_source_publisher_full_german_sentence_parallels(self):
        report = tr.evaluate(self.dataset)
        self.assertEqual(
            14, report["metrics"]["sentences_with_cross_text_attested_full_german_translation"])
        paragraphs = tr._parallel_translations(self.dataset["sentences"])
        actual = [
            tr.translate_sentence(sent, tr._observations(self.dataset["sentences"]),
                                  parallel_translations=paragraphs)
            for sent in self.dataset["sentences"].values()
        ]
        full = [p for p in actual if p["publisher_attested_german_sentence"]]
        self.assertEqual(14, len(full))
        for p in full:
            self.assertEqual("CROSS_TEXT_EXACT_SENTENCE_PARALLEL", p["translation_mode"])
            self.assertGreater(p["independent_source_text_support_for_sentence"], 0)
            self.assertNotEqual("", p["publisher_attested_german_sentence"])

    def test_forged_target_sentence_translation_cannot_self_retrieve(self):
        records = copy.deepcopy(self.dataset["sentences"])
        sid, chosen = next(iter(records.items()))
        own_text = chosen["text"]
        for s in records.values():
            if s["text"] == own_text:
                s["sentence_translation"] = "A TARGET-ONLY SECRET GERMAN REFERENCE"
        lookup = tr._parallel_translations(records)
        out = tr.translate_sentence(records[sid], tr._observations(records),
                                    parallel_translations=lookup)
        self.assertNotEqual("A TARGET-ONLY SECRET GERMAN REFERENCE",
                            out["publisher_attested_german_sentence"])
        self.assertFalse(out["publisher_target_translation_used_for_generation"])


    def test_ling002_immutable_interpretation_chain_preserves_alternatives(self):
        from tools import lexical_interpretation as lex
        from tools import linguistic_normalization as norm
        from tools.source_registry import load_yaml
        import hashlib
        root = Path(lex.ROOT)
        annotation, raw = norm.read(root / "data/examples/annotation_ambiguous.yaml")
        request, _ = norm.read(root / "ling/normalization/examples/synthetic.yaml")
        request["annotation_sha256"] = hashlib.sha256(raw).hexdigest()
        registry = load_yaml(root / "data/sources/registry.yaml")
        normal = norm.build(request, annotation, raw, registry)
        lexical_data, _ = lex.read_data(root / "ling/lexical/examples/synthetic.yaml")
        interpretation = lex.build(normal, lexical_data, registry)
        original = copy.deepcopy(interpretation)
        result = tr.translate_interpretation_manifest(
            interpretation, tr._observations(self.dataset["sentences"]))
        self.assertEqual(original, interpretation)
        self.assertEqual(interpretation["interpretation_version_id"],
                         result["input_ling002_interpretation_id"])
        self.assertEqual(len(interpretation["items"]), len(result["items"]))
        self.assertEqual(
            [x["source_value_id"] for x in interpretation["items"][0]["readings"]],
            [x["source_value_id"] for x in result["items"][0]["readings"]])
        self.assertTrue(result["ling002_original_not_modified"])
        self.assertFalse(result["certified_sentence_translation"])
        self.assertEqual(64, len(result["translation_version_sha256"]))
        self.assertEqual(result, tr.translate_interpretation_manifest(
            interpretation, tr._observations(self.dataset["sentences"])))

    def test_ling002_source_identity_hash_tamper_rejected(self):
        from tools import lexical_interpretation as lex
        from tools import linguistic_normalization as norm
        from tools.source_registry import load_yaml
        import hashlib
        root = Path(lex.ROOT)
        annotation, raw = norm.read(root / "data/examples/annotation_ambiguous.yaml")
        request, _ = norm.read(root / "ling/normalization/examples/synthetic.yaml")
        request["annotation_sha256"] = hashlib.sha256(raw).hexdigest()
        reg = load_yaml(root / "data/sources/registry.yaml")
        data, _ = lex.read_data(root / "ling/lexical/examples/synthetic.yaml")
        interpretation = lex.build(norm.build(request, annotation, raw, reg), data, reg)
        interpretation["items"][0]["readings"][0]["normalized_text"] = "FORGED"
        with self.assertRaisesRegex(tr.TranslationError, "hash drift"):
            tr.translate_interpretation_manifest(interpretation, {})

    def test_german_gloss_adapter_preserves_ambiguous_readings_and_abstentions(self):
        from tools import lexical_interpretation as lex
        from tools import linguistic_normalization as norm
        from tools.source_registry import load_yaml
        import hashlib
        root = Path(lex.ROOT)
        ann, raw = norm.read(root / "data/examples/annotation_ambiguous.yaml")
        request, _ = norm.read(root / "ling/normalization/examples/synthetic.yaml")
        request["annotation_sha256"] = hashlib.sha256(raw).hexdigest()
        reg = load_yaml(root / "data/sources/registry.yaml")
        data, _ = lex.read_data(root / "ling/lexical/examples/synthetic.yaml")
        interpretation = lex.build(norm.build(request, ann, raw, reg), data, reg)
        forms = [r["normalized_text"] for i in interpretation["items"]
                 for r in i["readings"] if r["normalized_text"]]
        x = forms[0]
        entries = {x: [("another-source", "GLOSS1", ""), ("different-source", "GLOSS2", "")]}
        results = tr.translate_interpretation_manifest(interpretation, entries)
        readings = [r for i in results["items"] for r in i["readings"]]
        found = next(r for r in readings if r["normalized_text"] == x)
        self.assertEqual("AMBIGUOUS_GERMAN_GLOSS", found["translation_status"])
        self.assertEqual(2, len(found["german_gloss_candidates"]))
        self.assertTrue(any(r["translation_status"] == "NO_CROSS_TEXT_GLOSS_ABSTAIN"
                            for r in readings if r["normalized_text"] != x))

    def test_no_network_and_no_image_claim(self):
        src = Path(tr.__file__).read_text("utf-8")
        for banned in ("requests.get(", "urlopen(", "model.generate(", "torch.load("):
            self.assertNotIn(banned, src)
        r = tr.evaluate(self.dataset)
        self.assertFalse(r["image_recognition_evaluation"])
        self.assertFalse(r["scientific_release_admitted"])




class W9ContextualPublisherExperimentTests(unittest.TestCase):
    """Real AES CC-BY-SA paired-language test plus strict source-group leakage."""

    @classmethod
    def setUpClass(cls):
        from ling.translation import contextual
        cls.engine = contextual
        cls.corpus = contextual.load_corpus()
        cls.report = contextual.evaluate_corpus(cls.corpus)

    def test_all_four_exact_publisher_git_blobs_and_group_population(self):
        eng = self.engine
        from ling.lexical import aes_holdout
        expected = eng.EXPECTED_COUNTS
        self.assertEqual(4, len(self.corpus["groups"]))
        self.assertEqual(1156, sum(map(len, self.corpus["groups"].values())))
        self.assertEqual(418, len(self.corpus["all_text_ids"]))
        self.assertEqual(1151, sum(
            bool(x["german"]) for group in self.corpus["groups"].values() for x in group))
        for name, (_, _, _, blob) in expected.items():
            path = (aes_holdout.ROOT / "ling/lexical/data/aes_felsinschriften_ccby_sa.json"
                    if name == "bbawfelsinschriften"
                    else aes_holdout.ROOT / f"ling/translation/data/_aes_{name}.json")
            self.assertEqual(blob, eng._blob_sha(path.read_bytes()))
        self.assertEqual("CC-BY-SA-4.0", self.corpus["manifest"]["license"])

    def test_publisher_external_corpus_is_wholly_separate_from_internal_folds(self):
        groups = self.corpus["groups"]
        training = {r["text_id"] for c in self.engine.DEV_CORPORA for r in groups[c]}
        test = {r["text_id"] for r in groups[self.engine.EXTERNAL_CORPUS]}
        self.assertTrue(training)
        self.assertEqual(21, len(test))
        self.assertFalse(training.intersection(test))
        self.assertEqual(247, self.report["external_test_sentences"])
        self.assertEqual(21, self.report["external_test_text_groups"])
        self.assertEqual(904, self.report["internal_training_dev_sentences"])
        self.assertEqual(5, len(self.report["five_fold_group_counts"]))
        self.assertEqual(904, sum(x["dev_sentences"] for x in self.report["five_fold_group_counts"]))
        self.assertEqual(self.engine.EXTERNAL_CORPUS, self.report["corpus_name"])

    def test_actual_publisher_external_translation_is_scored_and_not_certified(self):
        results = self.report["external_test_metrics"]
        ref = results["gloss_control"]
        improved = results["contextual_translation_memory"]
        self.assertEqual(ref["sentences_scored"], 247)
        self.assertEqual(improved["sentences_scored"], 247)
        self.assertGreater(ref["reference_words"], 0)
        self.assertGreater(improved["reference_words"], 0)
        self.assertGreaterEqual(ref["micro_word_f1"], 0)
        self.assertLessEqual(improved["micro_word_f1"], 1)
        self.assertGreaterEqual(improved["macro_sentence_char_ngram_f2"], 0)
        self.assertLessEqual(improved["macro_sentence_char_ngram_f2"], 1)
        self.assertFalse(self.report["scientific_certification"])
        self.assertFalse(self.report["not_fluent_generative_translation"] is False)
        self.assertEqual(0, self.report["physical_original_manuscript_images"])
        self.assertEqual(0, self.report["editorially_blind_gold_references"])
        print("W9_AUTHENTIC_TEXT_EVALUATION " + json.dumps({
            "selected_threshold": self.report["selected_threshold"],
            "heldout": self.report["external_test_metrics"],
            "dev_thresholds": self.report["internal_threshold_selection"],
            "report_sha256": self.report["report_sha256"],
        }, ensure_ascii=False, sort_keys=True))

    def test_dev_threshold_is_chosen_without_external_reference(self):
        x = self.report
        tuning = x["internal_threshold_selection"]
        self.assertEqual(list(self.engine.THRESHOLDS), [q["threshold"] for q in tuning])
        expected = sorted(
            tuning, key=lambda v: (-v["dev_context_word_f1"], -v["threshold"]))[0]
        self.assertEqual(expected["threshold"], x["selected_threshold"])
        self.assertEqual("ENTIRE_PREDECLARED_AES_SUBCORPUS_EXCLUDED_FROM_TRAINING_TUNING_AND_GLOSSES",
                         x["external_test_policy"])
        for row in x["five_fold_group_counts"]:
            self.assertGreater(row["train_text_groups"], 0)
            self.assertGreater(row["dev_text_groups"], 0)

    def test_exact_reproducible_report_digest(self):
        r = self.report
        self.assertEqual(64, len(r["report_sha256"]))
        identity = {k: v for k, v in r.items() if k != "report_sha256"}
        self.assertEqual(self.engine.sha256(self.engine._canonical(identity)).hexdigest(),
                         r["report_sha256"])
        # A cold model run is deterministic, stable and not Python-hash-dependent.
        self.assertEqual(r, self.engine.evaluate_corpus(self.corpus))

    def test_missing_german_editorial_target_cannot_influence_external_prediction(self):
        eng = self.engine
        train = [r for name in eng.DEV_CORPORA for r in self.corpus["groups"][name] if r["german"]]
        model = eng.TranslationMemory(train)
        sample = self.corpus["groups"][eng.EXTERNAL_CORPUS][0]
        first = model.predict(sample, 0.3)
        forged = dict(sample, german="COMPROMISED TARGET REFERENCE",
                      glosses=tuple("FORGED TARGET GLOSS" for _ in sample["forms"]))
        second = model.predict(forged, 0.3)
        self.assertEqual(first, second)
        self.assertNotIn("COMPROMISED", str(first))
        self.assertFalse(first["published_reference_used_for_prediction"])
        self.assertFalse(first["editorial_source_token_labels_used_for_prediction"])

    def test_entire_source_text_is_excluded_from_internal_validation(self):
        eng = self.engine
        all_train = [r for name in eng.DEV_CORPORA for r in self.corpus["groups"][name]
                     if r["german"]]
        heldout = next(r for r in all_train if r["forms"])
        filtered = [r for r in all_train if r["text_id"] != heldout["text_id"]]
        model = eng.TranslationMemory(filtered)
        prediction = model.predict(heldout, 0.0)
        nearest = prediction["nearest_training"]
        if nearest is not None:
            self.assertNotEqual(heldout["text_id"], nearest["source_text_id"])
        self.assertTrue(all(
            record["text_id"] != heldout["text_id"] for record in model.sentences))
        self.assertFalse(any(
            heldout["text_id"] in texts
            for candidates in model.observations.values() for texts in candidates.values()))

    def test_genuine_context_changes_sentence_retrieval_and_names_remain_warning(self):
        eng = self.engine
        source = [
            {"sentence_id": "a", "text_id": "textA", "corpus": "test",
             "forms": ("A", "B", "C"), "glosses": ("one", "two", "three"),
             "german": "A familiar sentence with a specific personal name."},
            {"sentence_id": "b", "text_id": "textB", "corpus": "test",
             "forms": ("A", "D", "E"), "glosses": ("one", "four", "five"),
             "german": "A different formula with a different personal name."},
        ]
        model = eng.TranslationMemory(source)
        query = dict(source[0], sentence_id="heldout", text_id="heldout",
                     german="HIDDEN GOLD", glosses=(None, None, None))
        p = model.predict(query, 0.0)
        self.assertEqual("CROSS_TEXT_SENTENCE_RETRIEVAL", p["mode"])
        self.assertEqual("textA", p["nearest_training"]["source_text_id"])
        self.assertTrue(p["nearest_training"]["exact_egyptian_form_sequence"])
        self.assertFalse(p["contextual_translation_is_scholarly_verified"])
        modified = dict(query, forms=("A", "D", "E"))
        q = model.predict(modified, 0.0)
        self.assertEqual("textB", q["nearest_training"]["source_text_id"])
        self.assertNotEqual(p["prediction"], q["prediction"])

    def test_one_generic_shared_form_cannot_copy_whole_sentence(self):
        eng = self.engine
        row = {"sentence_id": "a", "text_id": "known", "corpus": "synthetic",
               "forms": ("jr", "m", "name"), "glosses": ("do", "in", "John"),
               "german": "John does the deed in the city."}
        model = eng.TranslationMemory([row])
        query = dict(row, sentence_id="query", text_id="other",
                     forms=("jr", "unknown", "else"),
                     glosses=(None, None, None), german="HIDDEN")
        p = model.predict(query, 0.0)
        self.assertEqual("TRAIN_ONLY_GLOSS_FALLBACK", p["mode"])
        self.assertIsNone(p["nearest_training"])
        self.assertIn("[?]", p["prediction"])

    def test_unlicensed_or_modified_source_bytes_rejected_by_independent_hash(self):
        eng = self.engine
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "publisher.json"
            original = (eng.ROOT / "ling/translation/data/_aes_smaek.json").read_bytes()
            p.write_bytes(original + b" ")
            with self.assertRaisesRegex(eng.TranslationError, "blob identity mismatch"):
                eng._json_pinned(p, eng.EXPECTED_COUNTS["smaek"][3], limit=4_000_000)

    def test_character_ngram_diagnostic_is_bounded_and_not_sacrebleu(self):
        eng = self.engine
        self.assertAlmostEqual(1.0, eng.chrf2("Der König.", "Der König."))
        self.assertAlmostEqual(0.0, eng.chrf2("AAA", "zzz"))
        self.assertGreater(eng.chrf2("Der Koenig.", "Der König."), 0)
        self.assertLess(eng.chrf2("Der Koenig.", "Der König."), 1)

    def test_cli_verifies_original_four_subcorpora_without_spend(self):
        eng = self.engine
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(0, eng.main(["verify"]))
        report = json.loads(output.getvalue())
        self.assertEqual(1156, report["total_sentences"])
        self.assertEqual(418, report["total_group_ids"])


if __name__ == "__main__":
    unittest.main()
