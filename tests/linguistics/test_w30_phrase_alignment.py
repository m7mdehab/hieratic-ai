import unittest
from ling.translation import w30_phrase_alignment as w
from tools.translation_layer import TranslationError

class W30PhraseTests(unittest.TestCase):
 def test_frozen_new_pub_source(self):
  self.assertEqual(w.ORIGINAL_SIZE,20565872)
  self.assertEqual(w.ORIGINAL_SHA1,"f1281cf5fec5bc8cbcf4a6dde574d8482815658f")
  self.assertEqual(w.GROUPS,32)
 def test_training_only_bigram_phrase_learner(self):
  training=[{"forms":("a","b"),"german":"haus","text_id":f"doc{i}"} for i in range(4)]
  un=w.IBM1(training)
  p=w.BigramLexicon(training,un)
  self.assertIn(("a","b"),p.best)
  text,unknown,hits=p.predict(("a","b"))
  self.assertEqual(hits,1)
  self.assertEqual(unknown,0)
  self.assertIn("haus",text)
 def test_unseen_pair_does_not_get_spurious_phrase(self):
  training=[{"forms":("x","y"),"german":"haus","text_id":"doc"}]
  p=w.BigramLexicon(training,w.IBM1(training))
  self.assertNotIn(("x","y"),p.best)
 def test_wrong_original_cannot_open(self):
  with self.assertRaises(TranslationError):w.original_rows(b"not original")
 def test_no_label_dependent_ranking(self):
  x={str(i):{"text":f"original{i}","sentence_translation":"target"} for i in range(44)}
  rank=w.choose(x)
  for v in x.values():v["sentence_translation"]="new target"
  self.assertEqual(w.choose(x),rank)
if __name__=="__main__":unittest.main()
