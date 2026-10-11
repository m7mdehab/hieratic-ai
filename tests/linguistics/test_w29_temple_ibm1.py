import json
import unittest
from tools.translation_layer import TranslationError
from ling.translation import w29_temple_ibm1 as w

class W29PublisherTempleIBM1Tests(unittest.TestCase):
    def test_exact_original_publisher_tree_freeze(self):
        self.assertEqual(w.ORIGINAL_FILE,"_aes_bbawtempelbib.json")
        self.assertEqual(w.ORIGINAL_SIZE,9679845)
        self.assertEqual(w.ORIGINAL_SHA1,"f8135fee93c0ed27b5d6a110605f1a842fb6d8b6")
        self.assertIn(w.ORIGINAL_REV,w.URL)

    def test_new_32_group_selection_does_not_depend_on_any_german_label(self):
        group={f"id{i}":{"text":f"doc{i}","sentence_translation":"confidential"}
               for i in range(50)}
        frozen=w.choose(group)
        for x in group.values():x["sentence_translation"]="changed fake target gold"
        self.assertEqual(w.choose(group),frozen)
        self.assertEqual(len(set(frozen)),32)

    def test_original_source_wrong_hash_is_refused(self):
        with self.assertRaises(TranslationError):
            w.original_rows(b'{"made_up":["not original"]}')

    def test_new_source_predictor_cannot_receive_german_target_text(self):
        with self.assertRaises(TranslationError):
            w.previous.project_input({"sentence_id":"s","text_id":"t",
                                      "forms":["nfr"],"german":"secret"})

    def test_train_donor_only_ibm1_genuinely_learns_from_pairs(self):
        train=[
          {"forms":("x",),"german":"Pferd","text_id":"doc0"},
          {"forms":("x",),"german":"Pferd","text_id":"doc1"},
          {"forms":("y",),"german":"Haus","text_id":"doc2"},
          {"forms":("y",),"german":"Haus","text_id":"doc3"},
        ]
        model=w.IBM1(train)
        self.assertEqual(model.sentence_count,4)
        self.assertEqual(model.support["x"],2)
        translation,unknown=model.predict(("x","missing","y"))
        self.assertEqual(unknown,1)
        self.assertIn("[?]",translation)
        self.assertIn("pferd",translation)
        self.assertIn("haus",translation)

    def test_single_observation_cannot_be_emitted(self):
        model=w.IBM1([{"forms":("x",),"german":"einzig","text_id":"first"}])
        self.assertEqual(model.predict(("x",)),("[?]",1))

    def test_heldout_score_requires_all_ids_and_32_group_population(self):
        src=[{"sentence_id":"s","text_id":"doc","forms":["x"]}]
        with self.assertRaises(TranslationError):
            w.score(src,[],[])

    def test_micro_f1_denominator_zero_abstention(self):
        self.assertEqual(w.f1((0,0,0)),0.0)
        self.assertEqual(w.f1((1,1,1)),1.0)
        self.assertEqual(w.f1((1,2,2)),0.5)

if __name__=="__main__":
    unittest.main()
