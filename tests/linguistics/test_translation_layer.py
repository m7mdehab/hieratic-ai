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
        # Preserve the *negative* reserved-domain result as a falsifiable benchmark.
        self.assertEqual(0.15275625, ref["micro_word_f1"])
        self.assertEqual(0.14259102, improved["micro_word_f1"])
        self.assertLess(improved["micro_word_f1"], ref["micro_word_f1"])
        self.assertEqual(40, improved["prediction_modes"]["CROSS_TEXT_SENTENCE_RETRIEVAL"])
        self.assertEqual(40, improved["retrievals_with_nonidentical_source_sequence"])
        self.assertEqual(0.0, self.report["selected_threshold"])
        self.assertEqual(
            "3e8b42915d0a5cfce9a1a8cde78d503b319c18cbd3ed3ec28cafa745167402aa",
            self.report["report_sha256"])

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



class W10FrozenArchiveCompositionalTests(unittest.TestCase):
    """Non-copying composition, genuine new publisher domain and leak barriers."""

    @classmethod
    def setUpClass(cls):
        from ling.translation import contextual, w10_evaluation
        cls.corpus = contextual.load_corpus()
        cls.archive = w10_evaluation.load_archive(cls.corpus)

    def test_untouched_archive_32_groups_47_translations_no_previous_ids(self):
        from ling.translation import w10_evaluation as ev
        self.assertEqual("014cccf04235d9e093fca24ed48c62630d235852",
                         self.archive["original_sha1"])
        self.assertEqual("d3d7b57aef7bd10a48df6b1be340be8ff5b36e32",
                         self.archive["derived_git_blob_sha1"])
        self.assertEqual(32, len(self.archive["text_ids"]))
        self.assertEqual(47, len(self.archive["rows"]))
        self.assertTrue(all(r["german"] for r in self.archive["rows"]))
        old_ids = {r["text_id"] for group in self.corpus["groups"].values() for r in group}
        self.assertFalse(old_ids.intersection(self.archive["text_ids"]))
        self.assertEqual(ev.COHORT_GROUPS, 32)

    def test_publisher_archive_cannot_mutate_pinned_bytes(self):
        from ling.translation import w10_evaluation as ev
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ev.COHORT
            p.parent.mkdir(parents=True)
            p.write_bytes((ev.ROOT / ev.COHORT).read_bytes() + b" ")
            with self.assertRaisesRegex(tr.TranslationError, "Git blob mismatch"):
                ev.load_archive(self.corpus, Path(td))

    def test_original_archive_hash_reproduction_fails_closed_on_fake_source(self):
        from ling.translation import w10_evaluation as ev
        with self.assertRaisesRegex(tr.TranslationError, "Git blob mismatch"):
            ev.project_original_archive(b'{"fake":{}}')

    def test_independent_two_texts_support_reversing_exact_local_pair_only(self):
        from ling.translation.compositional import ConstrainedComposer
        training = [
            {"sentence_id": f"s{i}", "text_id": f"train-{i}", "corpus": "fixture",
             "forms": ("a", "b"), "glosses": ("Alpha", "Beta"),
             "german": "Beta Alpha"} for i in range(2)
        ]
        probe = {"sentence_id": "p", "text_id": "not-training", "corpus": "probe",
                 "forms": ("a", "b"), "german": "SECRET TARGET TRANSLATION"}
        p = ConstrainedComposer(training).predict(probe)
        self.assertEqual("Beta Alpha", p["prediction"])
        self.assertEqual([1, 0], p["emitted_slot_order"])
        self.assertEqual(2, p["learned_adjacent_swaps"][0]["reverse_texts"])
        self.assertFalse(p["whole_sentence_retrieval"])
        self.assertFalse(p["target_reference_or_labels_used"])
        self.assertFalse(p["fluent_or_semantically_certified"])
        self.assertEqual(p, ConstrainedComposer(training).predict(
            {**probe, "german": "FORGED REFERENCE", "glosses": ("xx", "yy"),
             "morphology": "UNSEEN_GOLD"}))

    def test_one_source_repeated_sentences_never_count_as_independent_voters(self):
        from ling.translation.compositional import ConstrainedComposer
        training = [
            {"sentence_id": f"s{i}", "text_id": "one-source", "corpus": "fixture",
             "forms": ("a", "b"), "glosses": ("Alpha", "Beta"),
             "german": "Beta Alpha"} for i in range(6)
        ]
        x = ConstrainedComposer(training).predict(
            {"sentence_id": "t", "text_id": "other", "forms": ("a", "b")})
        self.assertEqual("Alpha Beta", x["prediction"])
        self.assertEqual([], x["learned_adjacent_swaps"])

    def test_unknown_name_never_imports_foreign_name_from_german_sentence(self):
        from ling.translation.compositional import ConstrainedComposer
        train = [{"sentence_id": "s", "text_id": "source",
                  "forms": ("a", "b"), "glosses": ("Gott", "geben"),
                  "german": "Gott schenkt Ramses die Sonne"}]
        probe = {"sentence_id": "t", "text_id": "target",
                 "forms": ("a", "PRIVATE_NEW_NAME", "b"),
                 "german": "TARGET REFERENCE FORGED"}
        out = ConstrainedComposer(train).predict(probe)
        self.assertEqual("Gott [?] geben", out["prediction"])
        self.assertNotIn("Ramses", out["prediction"])
        self.assertEqual(1, out["unknown_abstentions"])
        self.assertFalse(out["whole_sentence_retrieval"])

    def test_source_group_leakage_is_rejected_even_if_sentence_id_differs(self):
        from ling.translation.compositional import ConstrainedComposer
        train = [{"sentence_id": "s1", "text_id": "source",
                  "forms": ("a",), "glosses": ("der",), "german": "der"}]
        with self.assertRaisesRegex(tr.TranslationError, "in training"):
            ConstrainedComposer(train).predict(
                {"sentence_id": "different", "text_id": "source", "forms": ("a",)})

    def test_actual_untouched_archive_all_47_are_scored_once_and_three_systems(self):
        from ling.translation import w10_evaluation as ev
        report = ev.evaluate_external(self.corpus)
        fresh = report["new_external"]
        self.assertEqual(47, fresh["population"]["sentences_seen"])
        self.assertEqual(47, fresh["population"]["german_refs_present"])
        self.assertEqual(32, fresh["population"]["source_texts"])
        self.assertEqual(904, report["internal_fold_population"])
        self.assertEqual(5, len(report["internal_fold_results"]))
        for name in ("gloss_control", "w9_contextual_memory", "w10_composition"):
            self.assertEqual(47, fresh["metrics"][name]["sentences_scored"])
        self.assertEqual(0.0, report["capability_points"])
        self.assertFalse(report["verified_physical_manuscript_witness_independence"])
        self.assertFalse(report["independent_blind_semantic_adjudication"])
        self.assertFalse(report["image_conditioned_hieratic_reading"])
        self.assertFalse(report["archive_training_or_tuning"])
        self.assertFalse(report["prior_revealed_tuebingen_in_training_or_tuning"])
        self.assertEqual(report, ev.evaluate_external(self.corpus))
        self.assertEqual(64, len(report["report_sha256"]))
        print("W10_ARCHIVE_NEW_EXTERNAL_DIAGNOSTIC " + json.dumps({
            "sha256": report["report_sha256"],
            "new_external": fresh,
            "internal_folds": [{
                "fold": x["fold"],
                "compositional_micro_word_f1":
                    x["results"]["metrics"]["w10_composition"]["micro_word_f1"],
            } for x in report["internal_fold_results"]],
        }, sort_keys=True, ensure_ascii=False))



    def test_archive_item_rights_manifest_and_nonadmission_are_explicit(self):
        from ling.translation import w10_evaluation as ev
        manifest = json.loads(
            (ev.ROOT / "ling/translation/data/w10_archive_rights_manifest.json").read_text(
                encoding="utf-8"))
        self.assertEqual("OPEN-SA", manifest["source_record"]["rights_class"])
        self.assertEqual("CC-BY-SA-4.0", manifest["items"][0]["license"])
        self.assertEqual("014cccf04235d9e093fca24ed48c62630d235852",
                         manifest["source_record"]["original_git_blob_sha1"])
        self.assertFalse(manifest["source_record"]["exact_original_SHA256_available"])
        self.assertEqual(47, len(manifest["items"]))
        self.assertEqual(
            {row["sentence_id"] for row in self.archive["rows"]},
            {item["original_sentence_id"] for item in manifest["items"]})
        for item in manifest["items"]:
            self.assertTrue(item["original_editor"])
            self.assertEqual("EXTERNAL_EVALUATION_ONLY_NOT_TRAINING", item["split_role"])
            self.assertFalse(item["training_admission"])
            self.assertFalse(item["production_release_admission"])
            self.assertFalse(item["original_item_sha256_verified"])
            self.assertFalse(item["photographed_manuscript_view_linked"])



class W11ExpandedTrainingFreshBiographyTests(unittest.TestCase):
    """Frozen expanded training; W10 and exposed Tuebingen data excluded."""

    @classmethod
    def setUpClass(cls):
        from ling.translation import contextual, w11_evaluation
        cls.corpus = contextual.load_corpus()
        cls.data = w11_evaluation.load(cls.corpus)

    def test_original_archive_3021_donor_1130_groups_and_quarantined_w10(self):
        self.assertEqual(3021, len(self.data["donor"]))
        self.assertEqual(1130, len(self.data["donor_text_ids"]))
        self.assertEqual(32, len(self.data["prior_heldout_text_ids"]))
        self.assertEqual(
            {"Stephan Seidlmayer": 550, "Stefan Grunert": 2463, "Ingelore Hafemann": 8},
            self.data["donor_owners"])
        donor_ids = set(self.data["donor_text_ids"])
        prior_w10 = set(self.data["prior_heldout_text_ids"])
        previous = {r["text_id"] for grp in self.corpus["groups"].values() for r in grp}
        self.assertFalse(donor_ids & prior_w10)
        self.assertFalse(donor_ids & previous)
        self.assertFalse(set(self.data["test_text_ids"]) & (donor_ids | prior_w10 | previous))

    def test_new_biographies_180_sentences_32_groups_and_178_refs(self):
        self.assertEqual(180, len(self.data["test"]))
        self.assertEqual(32, len(self.data["test_text_ids"]))
        self.assertEqual(178, sum(bool(row["german"]) for row in self.data["test"]))
        self.assertTrue(all(all(g is None for g in row["glosses"])
                            for row in self.data["test"]))
        self.assertTrue(all(row["corpus"] == "bbawhistbiospzt" for row in self.data["test"]))

    def test_original_digest_locks_reject_mutated_external_and_donor(self):
        from ling.translation import w11_evaluation as ev
        for path, expected, max_bytes in (
            (ev.DONOR, ev.DONOR_BLOB, 3_000_000),
            (ev.BIOGRAPHIES, ev.BIOGRAPHY_BLOB, 400_000),
        ):
            original = (ev.ROOT / path).read_bytes()
            with tempfile.TemporaryDirectory() as temp:
                item = Path(temp) / path
                item.parent.mkdir(parents=True)
                item.write_bytes(original + b" ")
                with self.assertRaisesRegex(tr.TranslationError, "Git blob identity mismatch"):
                    ev.pinned_json(Path(temp), path, expected, max_bytes)

    def test_duplicate_train_group_and_fake_reference_cannot_improve_predictions(self):
        from ling.translation.compositional import ConstrainedComposer
        from ling.translation import contextual
        train = [row for name in contextual.DEV_CORPORA
                 for row in self.corpus["groups"][name] if row["german"]]
        composer = ConstrainedComposer(train)
        original = self.data["test"][0]
        result = composer.predict(original)
        fake = {**original, "german": "A FORGED GERMAN TARGET SENTENCE",
                "glosses": tuple("secret" for _ in original["forms"])}
        self.assertEqual(result, composer.predict(fake))
        with self.assertRaisesRegex(tr.TranslationError, "in training"):
            composer.predict({**original, "text_id": train[0]["text_id"]})

    def test_frozen_w11_five_way_full_population_and_negative_controls(self):
        from ling.translation import w11_evaluation as ev
        report = ev.evaluate(self.corpus)
        self.assertEqual(904, report["training"]["old_w9_translated_sentences"])
        self.assertEqual(3021, report["training"]["additional_archive_translated_sentences"])
        self.assertEqual(3925, report["training"]["total_training_translated_sentences"])
        self.assertEqual(32, report["training"]["w10_quarantined_group_count"])
        self.assertEqual(180, report["new_external"]["total_original_sentences"])
        self.assertEqual(178, report["new_external"]["publisher_german_references"])
        self.assertEqual(32, report["new_external"]["original_source_text_groups"])
        self.assertEqual({
            "w9_904_gloss", "w10_904_composer", "w11_expanded_gloss",
            "w11_expanded_composer", "w11_expanded_memory_threshold_0",
        }, set(report["new_external"]["metrics"]))
        for value in report["new_external"]["metrics"].values():
            self.assertEqual(178, value["sentences_scored"])
        self.assertFalse(report["science_is_full_semantic_translation"])
        self.assertFalse(report["independent_expert_gold"])
        self.assertFalse(report["independently_verified_distinct_physical_manuscripts"])
        self.assertEqual(0, report["original_ling003_capability_points"])
        self.assertEqual(report, ev.evaluate(self.corpus))
        self.assertEqual(40, len(ev.git_blob_sha1(b"test")))
        print("W11_FRESH_BIOGRAPHY_EXTERNAL " + json.dumps({
            "training": report["training"],
            "external": report["new_external"],
            "sha256": tr.sha256(tr._canonical(report)).hexdigest(),
        }, sort_keys=True, ensure_ascii=False))


    def test_biography_original_editors_share_alike_and_quarantine_manifest(self):
        from ling.translation import w11_evaluation as ev
        records = json.loads(
            (ev.ROOT / "ling/translation/data/w11_biography_rights_manifest.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(180, len(records["items"]))
        self.assertEqual(32, records["population"]["source_text_groups"])
        self.assertEqual(178, records["population"]["translated_sentences"])
        self.assertEqual({"Silke Grallert": 101, "Gunnar Sperveslage": 8,
                          "Roberto A. Díaz Hernández": 57, "John M. Iskander": 14},
                         records["population"]["original_editor_distribution"])
        self.assertEqual("CC-BY-SA-4.0", records["source"]["publisher_license"])
        self.assertEqual(ev.BIOGRAPHY_BLOB, records["source"]["derived_git_blob"])
        self.assertEqual(32, records["quarantine"]["prior_w10_exposed_archive_groups_excluded_from_training"])
        self.assertFalse(records["quarantine"]["data008_admission"])
        self.assertEqual(
            {row["sentence_id"] for row in self.data["test"]},
            {item["source_sentence_id"] for item in records["items"]})
        for item in records["items"]:
            self.assertTrue(item["source_owner"])
            self.assertFalse(item["development_or_training_use"])
            self.assertFalse(item["original_image_matched"])
            self.assertFalse(item["blind_egyptologist_gold"])
            self.assertFalse(item["physical_manuscript_independence_verified"])



    def test_w11_biography_cohort_is_exact_global_sha256_top32(self):
        from ling.translation import w11_evaluation as ev
        import hashlib
        universe = ev.pinned_json(ev.ROOT, ev.BIOGRAPHY_UNIVERSE,
                                  ev.BIOGRAPHY_UNIVERSE_BLOB, 30_000)
        original_ids = universe["source_text_ids_sorted"]
        self.assertEqual(141, len(original_ids))
        self.assertEqual(1110, universe["original_sentence_count"])
        self.assertEqual(1095, universe["original_translated_sentence_count"])
        disallowed = set(self.data["donor_text_ids"])
        disallowed.update(self.data["prior_heldout_text_ids"])
        disallowed.update(r["text_id"] for group in self.corpus["groups"].values()
                          for r in group)
        ranked = sorted((x for x in original_ids if x not in disallowed),
                        key=lambda x: (hashlib.sha256(
                            (ev.BIOGRAPHY_HASH_SALT + x).encode("utf-8")).hexdigest(), x))
        self.assertEqual(set(ranked[:32]), set(self.data["test_text_ids"]))
        self.assertEqual(universe["selected_group_ids_sorted"],
                         sorted(self.data["test_text_ids"]))

    def test_w11_biography_original_universe_identity_drift_fails_closed(self):
        from ling.translation import w11_evaluation as ev
        with tempfile.TemporaryDirectory() as folder:
            location = Path(folder) / ev.BIOGRAPHY_UNIVERSE
            location.parent.mkdir(parents=True, exist_ok=True)
            location.write_bytes((ev.ROOT / ev.BIOGRAPHY_UNIVERSE).read_bytes() + b" ")
            with self.assertRaisesRegex(tr.TranslationError, "Git blob identity mismatch"):
                ev.pinned_json(Path(folder), ev.BIOGRAPHY_UNIVERSE,
                               ev.BIOGRAPHY_UNIVERSE_BLOB, 30_000)


class W12BFrozenGrammarEvidenceTests(unittest.TestCase):
    """True AES publisher POS evidence, negative rights, source and gold leakage checks."""

    @classmethod
    def setUpClass(cls):
        from ling.translation import w12b_evaluation as ev
        cls.ev = ev
        cls.training, cls.inputs, _ = ev.load()

    def test_completeness_and_strict_new_24_text_id_population(self):
        self.assertEqual(3925, len(self.training))
        self.assertEqual(163, len(self.inputs))
        self.assertEqual(24, len({x["text"] for x in self.inputs.values()}))
        self.assertEqual(1691, sum(len(x["forms"]) for x in self.inputs.values()))
        self.assertFalse({x["text"] for x in self.inputs.values()} &
                         {x["text"] for x in self.training.values()})

    def test_original_source_universe_reproduces_rank_not_only_cutoff(self):
        from hashlib import sha256
        u = self.ev.pinned(self.ev.ROOT, "w12b_amarna_source_universe.json")
        original = u["all_source_ids_sorted"]
        expected = sorted(original, key=lambda t: (
            sha256((self.ev.SEED + t).encode("utf-8")).hexdigest(), t))[:24]
        self.assertEqual(expected, u["selected_ids_ranked"])
        self.assertEqual("5e512681dc0d1ac7177a62531582b3473a0a11f2",
                         u["original_git_blob"])
        self.assertEqual(399, len(original))

    def test_a_genuine_unknown_form_must_abstain_and_decline_roles(self):
        from ling.translation.grammar_evidence import GrammarEvidence
        model = GrammarEvidence({"test-s": {
            "text": "training-only", "owner": "test", "tokens": [
                {"form": "a", "pos": "substantive", "features": {"genus": "feminine"}}
            ]
        }})
        out = model.predict(["a", "never_seen"], "new_source_group")
        self.assertEqual("substantive", out["units"][0]["context_pos"])
        self.assertIsNone(out["units"][1]["context_pos"])
        self.assertEqual([], out["units"][1]["alternatives"])
        self.assertEqual("UNKNOWN_NOT_INFERRED", out["units"][0]["semantic_role"])
        self.assertEqual("NOT_PREDICTED", out["units"][0]["syntactic_dependency"])
        self.assertFalse(out["fluent_translation_claim"])

    def test_repeated_same_text_cannot_forge_independent_context_support(self):
        from ling.translation.grammar_evidence import GrammarEvidence
        training = {
            "s1": {"text": "same-text", "owner": "test", "tokens": [
                {"form": "L", "pos": "pronoun", "features": {}},
                {"form": "H", "pos": "verb", "features": {}},
                {"form": "R", "pos": "substantive", "features": {}}]},
            "s2": {"text": "same-text", "owner": "test", "tokens": [
                {"form": "L", "pos": "pronoun", "features": {}},
                {"form": "H", "pos": "verb", "features": {}},
                {"form": "R", "pos": "substantive", "features": {}}]},
            "s3": {"text": "other-training", "owner": "test", "tokens": [
                {"form": "H", "pos": "adjective", "features": {}}]},
        }
        p = GrammarEvidence(training).predict(["L", "H", "R"], "heldout")
        self.assertEqual("FORM_MAJORITY", p["units"][1]["pos_decision"])
        self.assertEqual(2, len(p["units"][1]["alternatives"]))
        self.assertEqual("adjective", p["units"][1]["baseline_pos"])
        self.assertEqual("adjective", p["units"][1]["context_pos"])
        self.assertEqual("verb", p["units"][1]["alternatives"][1]["pos"])

    def test_contextual_tag_needs_two_distinct_source_groups(self):
        from ling.translation.grammar_evidence import GrammarEvidence
        training = {}
        for idx in range(2):
            training[f"ctx{idx}"] = {"text": f"ctx-{idx}", "owner": "test", "tokens": [
                {"form": "L", "pos": "pronoun", "features": {}},
                {"form": "H", "pos": "verb", "features": {}},
                {"form": "R", "pos": "substantive", "features": {}}]}
        for idx in range(3):
            training[f"other{idx}"] = {"text": f"other-{idx}", "owner": "test", "tokens": [
                {"form": "H", "pos": "adjective", "features": {}}]}
        p = GrammarEvidence(training).predict(["L", "H", "R"], "heldout")
        self.assertEqual("adjective", p["units"][1]["baseline_pos"])
        self.assertEqual("verb", p["units"][1]["context_pos"])
        self.assertEqual("TWO_SIDED", p["units"][1]["pos_decision"])
        self.assertEqual(2, p["units"][1]["selected_pos_distinct_training_texts"])

    def test_heldout_pos_reference_cannot_enter_prediction(self):
        from ling.translation.grammar_evidence import GrammarEvidence
        model = GrammarEvidence(self.training)
        sent, inp = next(iter(self.inputs.items()))
        before = model.predict(inp["forms"], inp["text"])
        # Target POS/German/morphology are NOT accepted by the predict signature;
        # even an externally forged record has no chance to enter the method.
        forged = {"forms": list(inp["forms"]), "text": inp["text"],
                  "pos": ["FORGED"] * len(inp["forms"]),
                  "german": "FORGED GERMAN", "lemmaID": "FORGED"}
        self.assertEqual(before, model.predict(forged["forms"], forged["text"]))

    def test_target_source_group_overlap_is_rejected(self):
        from ling.translation.grammar_evidence import GrammarEvidence
        model = GrammarEvidence(self.training)
        original = next(iter(self.training.values()))
        with self.assertRaisesRegex(tr.TranslationError, "overlaps"):
            model.predict([original["tokens"][0]["form"]], original["text"])

    def test_hash_tampering_fails_closed_without_gold_substitution(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / self.ev.REL / "w12b_amarna_inputs.json"
            p.parent.mkdir(parents=True)
            p.write_bytes((self.ev.ROOT / self.ev.REL /
                           "w12b_amarna_inputs.json").read_bytes() + b" ")
            with self.assertRaisesRegex(tr.TranslationError, "Git blob identity mismatch"):
                self.ev.pinned(Path(td), "w12b_amarna_inputs.json")

    def test_all_historic_source_rights_and_nonadmission(self):
        rights = self.ev.pinned(self.ev.ROOT, "w12b_amarna_rights_manifest.json")
        self.assertEqual("CC-BY-SA-4.0", rights["license"])
        self.assertEqual(163, len(rights["rights"]))
        self.assertTrue(all(x["rights_class"] == "OPEN-SA"
                            and x["test_only"] is True
                            and x["production_admission"] is False
                            and x["train_admission"] is False
                            for x in rights["rights"]))

    def test_first_use_original_editorial_pos_and_morphology_are_evaluated(self):
        out = self.ev.evaluate()
        self.assertEqual(3925, out["train_sentences"])
        self.assertEqual(24, out["new_publisher_test_groups"])
        self.assertEqual(1691, out["metrics"]["pos"]["original_egyptian_tokens"])
        self.assertEqual(1649, out["metrics"]["pos"]["publisher_pos_labels"])
        self.assertFalse(out["metrics"]["certified_subject_object_agent_roles"])
        self.assertFalse(out["metrics"]["original_manuscript_heldout_gold"])
        self.assertEqual(0, out["raw_publisher_images_evaluated"])
        self.assertEqual(0.0, out["scientific_capability_points"])
        self.assertEqual(out, self.ev.evaluate())
        self.assertEqual(64, len(out["report_sha256"]))
        print("W12B_FRESH_EDITORIAL_POS_HELDOUT " + json.dumps(out, sort_keys=True,
                                                               ensure_ascii=False))


class W13PreCopticEgyptianDependencyTests(unittest.TestCase):
    """Original UD Egyptian-PC is Old Egyptian, not a later Hieratic reading."""

    @classmethod
    def setUpClass(cls):
        from ling.translation import w13_egyptian_pc as ud
        cls.ud = ud
        cls.train, cls.dev = ud.load_project()

    def test_genuine_original_publisher_census_and_strict_rights(self):
        self.assertEqual("CC-BY-SA-4.0", self.train["rights"])
        self.assertEqual("CC-BY-SA-4.0", self.train["rights"])
        self.assertEqual(1619, self.train["sentence_count"])
        self.assertEqual(19486, self.train["token_count"])
        self.assertEqual(230, len(self.dev))
        self.assertEqual(3167, sum(len(x["rows"]) for x in self.dev))
        self.assertEqual("fca8538287cb69fd07b811eb55dcfd25584f3006",
                         self.ud.REVISION_TREE)
        self.assertEqual(40, len(self.ud.TRAIN_BLOB))
        self.assertEqual(40, len(self.ud.DEV_BLOB))

    def test_source_tampering_rejected_including_byte_append(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "corrupted.json"
            path.write_bytes(self.ud.TRAIN_FILE.read_bytes() + b" ")
            with self.assertRaisesRegex(tr.TranslationError, "Git blob identity"):
                self.ud._load(path, self.ud.TRAIN_BLOB, 150000)

    def test_publisher_gold_root_cycle_and_head_validation(self):
        sample = [[1,"VERB",0,"root"],[2,"NOUN",1,"obj"]]
        self.ud._check_gold(sample)
        for invalid in (
            [[1,"VERB",0,"root"],[2,"NOUN",0,"obj"]],
            [[1,"VERB",2,"root"],[2,"NOUN",1,"obj"]],
            [[1,"VERB",0,"root"],[2,"NOUN",4,"obj"]],
            [[1,"VERB",0,"root"],[2,"NOUN",2,"obj"]],
        ):
            with self.subTest(invalid=invalid), self.assertRaises(tr.TranslationError):
                self.ud._check_gold(invalid)

    def test_model_never_consumes_dev_gold_for_prediction(self):
        model = self.ud.FixedOraclePosSyntax(self.train)
        sample = self.dev[0]
        pos = [x[1] for x in sample["rows"]]
        a = model.predict(pos)
        forged = copy.deepcopy(sample)
        for token in forged["rows"]:
            token[2] = 99999
            token[3] = "FORGED_REFERENCE"
        b = model.predict([x[1] for x in forged["rows"]])
        self.assertEqual(a, b)

    def test_fixed_oracle_pos_predictor_always_outputs_one_root_and_acyclic(self):
        model = self.ud.FixedOraclePosSyntax(self.train)
        for sample in self.dev:
            pos = [row[1] for row in sample["rows"]]
            for p in (model.predict, model.baseline):
                heads, rels = p(pos)
                self.assertEqual(len(pos), len(heads))
                self.assertEqual(len(pos), len(rels))
                self.assertEqual(1, heads.count(0))
                self.assertIsNone(self.ud.has_cycle(heads))

    def test_explicitly_no_manuscript_accuracy_certification(self):
        report = self.ud.evaluate(self.train, self.dev)
        self.assertTrue(report["oracle_dev_UPOS_exposed"])
        self.assertFalse(report["gold_dev_HEAD_DEPREL_used_for_prediction"])
        self.assertFalse(report["official_test_split_opened"])
        self.assertTrue(report["no_original_hieratic_image"])
        self.assertFalse(report["ling003_scientific_milestone_accepted"])
        self.assertEqual(0.0, report["scientific_capability_points"])
        self.assertEqual(3167, report["metrics"]["model"]["tokens"])
        self.assertEqual(230, report["metrics"]["model"]["sentences"])
        self.assertEqual(0, report["metrics"]["model"]["invalid_predicted_trees"])
        self.assertEqual(report, self.ud.evaluate(self.train, self.dev))
        print("W13_EGYPTIAN_PC_DEPENDENCY " + json.dumps({
            "report_sha256": report["report_sha256"],
            "train": report["training_token_count"],
            "dev": report["development_sentence_count"],
            "metrics": {name: {k: x[k] for k in
                ("correct_head", "correct_head_relation", "UAS", "LAS",
                 "invalid_predicted_trees")} for name, x in report["metrics"].items()},
        }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    unittest.main()


"""W14 train-only nonoracle grammatical inference, actual original Egyptian-PC."""
import copy
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ling.translation import w14_oracle_free as w14
from tools.translation_layer import TranslationError


class W14OriginalTrainGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = w14.load_dataset()
        cls.train = [s for s in cls.bundle["sentences"] if s["group"] in w14.TRAIN_GROUPS]
        cls.eval_rows = [s for s in cls.bundle["sentences"] if s["group"] == w14.HELDOUT_GROUP]
        cls.model = w14.TrainOnlyOracleFree(cls.train)

    def test_original_train_only_source_rights_population_and_split(self):
        b = self.bundle
        self.assertEqual("CC-BY-SA-4.0", b["rights"])
        self.assertEqual(w14.ORIGINAL_TREE, b["source_tree"])
        self.assertEqual(w14.ORIGINAL_TRAIN_BLOB, b["original_train_git_blob"])
        self.assertEqual(1619, b["sentence_count"])
        self.assertEqual(19486, b["token_count"])
        self.assertEqual(790, len(self.train))
        self.assertEqual(829, len(self.eval_rows))
        self.assertEqual(9157, sum(len(s["rows"]) for s in self.train))
        self.assertEqual(10329, sum(len(s["rows"]) for s in self.eval_rows))
        self.assertTrue(b["original_dev_labels_exposed_elsewhere"])
        self.assertFalse(b["official_test_accessed"])

    def test_exact_source_derivative_rejects_single_byte_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / w14.DATA.relative_to(w14.ROOT)
            destination.parent.mkdir(parents=True)
            destination.write_bytes(w14.DATA.read_bytes() + b" ")
            with self.assertRaisesRegex(TranslationError, "identity mismatch"):
                w14.load_dataset(Path(directory))

    def test_original_source_gold_graph_rejects_invalid_edges_and_multiple_roots(self):
        sample = copy.deepcopy(self.train[0])
        sample["rows"][1][2] = 0
        with self.assertRaisesRegex(TranslationError, "single-rooted"):
            w14._valid_sentence(sample)
        sample = copy.deepcopy(self.train[0])
        sample["rows"][0][2] = 1
        with self.assertRaisesRegex(TranslationError, "Invalid original"):
            w14._valid_sentence(sample)

    def test_no_heldout_group_can_enter_training(self):
        with self.assertRaisesRegex(TranslationError, "mixing refused"):
            w14.TrainOnlyOracleFree(self.train + [self.eval_rows[0]])

    def test_inference_refuses_gold_rows_or_dict_labels(self):
        forms = [row[0] for row in self.eval_rows[0]["rows"]]
        original = self.model.predict(forms)
        self.assertNotIn("gold", json.dumps(original).casefold())
        for forged in ([r[:] for r in self.eval_rows[0]["rows"]],
                       [{"form": forms[0], "UPOS": "SECRET"}], [], [""]):
            with self.subTest(forged=forged):
                with self.assertRaises(TranslationError):
                    self.model.predict(forged)

    def test_target_upos_head_relation_modification_does_not_affect_nonoracle(self):
        sentence = copy.deepcopy(self.eval_rows[0])
        forms = [row[0] for row in sentence["rows"]]
        prediction = self.model.predict(forms)
        weak = self.model.weak_baseline(forms)
        for row in sentence["rows"]:
            row[1], row[3] = "FORGED_UPOS", "FORGED_REFERENCE_RELATION"
        self.assertEqual(prediction, self.model.predict([r[0] for r in sentence["rows"]]))
        self.assertEqual(weak, self.model.weak_baseline([r[0] for r in sentence["rows"]]))
        self.assertFalse(any(tag == "FORGED_UPOS" for tag in prediction["UPOS"]))

    def test_all_original_heldout_sentences_have_valid_predictions(self):
        for sentence in self.eval_rows:
            forms = [r[0] for r in sentence["rows"]]
            for pred in (self.model.predict(forms), self.model.weak_baseline(forms)):
                self.assertEqual(1, pred["heads"].count(0))
                self.assertIsNone(w14.has_cycle(pred["heads"]))
                self.assertEqual(len(forms), len(pred["UPOS"]))
                self.assertEqual(len(forms), len(pred["relations"]))

    def test_real_full_population_deterministic_report_and_denominators(self):
        first = w14.evaluate(self.bundle)
        second = w14.evaluate(self.bundle)
        self.assertEqual(first, second)
        self.assertEqual("CC-BY-SA-4.0", first["license"])
        self.assertEqual(10329, first["evaluation_tokens"])
        self.assertEqual(829, first["evaluation_sentences"])
        self.assertEqual(0, first["train_heldout_sentence_id_overlap"])
        self.assertEqual(10329, sum(first["predicted_POS_evidence_counts"].values()))
        self.assertEqual(10329, sum(x["tokens"] for x in first["true_UPOS_errors"].values()))
        self.assertEqual(10329, sum(x["tokens"] for x in first["true_relation_errors"].values()))
        self.assertGreater(first["predicted_UPOS_correct"], 0)
        self.assertLess(first["predicted_UPOS_correct"], 10329)
        self.assertGreater(first["models"]["nonoracle"]["correct_head"], 0)
        self.assertTrue(first["training_corpus_aggregate_statistics_previously_exposed_in_W13"])
        self.assertFalse(first["source_witness_and_editor_genealogy_independence_verified"])
        self.assertFalse(first["original_official_TEST_opened"])
        self.assertFalse(first["nonoracle_gold_UPOS_used_for_predictions"])
        self.assertEqual(0.0, first["LING003_capability_points_earned"])
        from hashlib import sha256
        from tools.translation_layer import _canonical
        self.assertEqual(
            sha256(_canonical({k: v for k, v in first.items() if k != "report_sha256"})).hexdigest(),
            first["report_sha256"],
        )
        for metric in first["models"].values():
            self.assertEqual(10329, metric["tokens"])
            self.assertEqual(829, metric["sentences"])
            self.assertEqual(0, metric["invalid_trees"])
            self.assertGreaterEqual(metric["correct_head"], metric["correct_head_and_relation"])

    def test_cli_verify_and_only_explicit_form_predict(self):
        for action, args in (("verify", ["verify"]), ("predict", ["predict", "--form", "m", "--form", "n"])):
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                self.assertEqual(0, w14.main(args))
            result = json.loads(buffer.getvalue())
            if action == "verify":
                self.assertTrue(result["test_not_opened"])
            else:
                self.assertEqual(2, len(result["UPOS"]))
                self.assertTrue(result["no_reference_gold_accessed"])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(1, w14.main(["predict"]))
            self.assertEqual(1, w14.main(["evaluate", "--form", "MUTATION"]))


if __name__ == "__main__":
    unittest.main()
