"""W30 prospectively frozen original publisher Amarna; no target answers in tests."""
import unittest
from tools.translation_layer import TranslationError
from ling.translation import w30_amarna_phrase as p

class W30AmarnaPhraseTests(unittest.TestCase):
    def test_original_publication_pinned_before_first_source_read(self):
        self.assertEqual(p.SOURCE_BYTES,14683204)
        self.assertEqual(p.SOURCE_BLOB,"5e512681dc0d1ac7177a62531582b3473a0a11f2")
        self.assertEqual(p.GROUP_COUNT,32)

    def test_source_group_selection_invariant_to_reference_target(self):
        rows={str(j):{"text":f"text-{j}","sentence_translation":"foo"} for j in range(48)}
        before=p.frozen_ids(rows)
        for x in rows.values():x["sentence_translation"]="hidden reference"
        self.assertEqual(before,p.frozen_ids(rows))
        self.assertEqual(len(before),32)

    def test_forged_publisher_bytes_fail_closed(self):
        with self.assertRaises(TranslationError):p.source_rows(b"not the original")

    def test_genuinely_trained_phrase_model_and_unknown(self):
        tr=[
          {"forms":("a","b"),"german":"Haus Pferd","text_id":"x"},
          {"forms":("a","b"),"german":"Haus Pferd","text_id":"y"},
          {"forms":("a","b"),"german":"Haus Pferd","text_id":"z"},
          {"forms":("c","d"),"german":"Wasser Brot","text_id":"w"},
          {"forms":("c","d"),"german":"Wasser Brot","text_id":"q"},
        ]
        learner=p.PhraseIBM1(tr)
        self.assertGreater(learner.base.sentence_count,0)
        self.assertGreaterEqual(len(learner.pair_support),2)
        emitted,unknown,replacements=learner.emit(("a","b","missing"),2,0.5)
        self.assertIn(p.prior.UNKNOWN,emitted)
        self.assertGreaterEqual(unknown,1)
        self.assertGreaterEqual(replacements,0)

    def test_german_bigram_f1_counts_order(self):
        self.assertEqual(p.bigram_counts("a b c","a b d"),(1,2,2))
        self.assertEqual(p.bigram_counts("b a c","a b c"),(0,2,2))
        self.assertEqual(p.metric((1,2,2)),.5)

    def test_train_only_group_selection_has_no_overlap(self):
        rows=[{"text_id":f"d{i}","forms":("x",),"german":"hello"} for i in range(39)]
        tr,dev=p.dev_split(rows)
        self.assertEqual(len(tr)+len(dev),len(rows))
        self.assertFalse({x["text_id"] for x in tr}&{x["text_id"] for x in dev})

    def test_missing_gold_or_predictions_rejected(self):
        with self.assertRaises(TranslationError):
            p.score([{"sentence_id":"1","text_id":"a","forms":["x"]}],[],[])

if __name__=="__main__":unittest.main()
