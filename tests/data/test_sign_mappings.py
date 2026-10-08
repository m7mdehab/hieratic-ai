import copy, unittest
from pathlib import Path
from tools.sign_mappings import ROOT, load, validate

class SignMappingTests(unittest.TestCase):
    def setUp(self): self.payload=load(ROOT/"data/mappings/examples/synthetic.yaml")
    def test_synthetic_unresolved_record_is_valid_and_keeps_layers_separate(self):
        self.assertEqual([],validate(self.payload))
        rec=self.payload["records"][0]
        self.assertIsNone(rec["observed_hieratic"]["value"])
        self.assertIsNone(rec["hieroglyphic_correspondence"]["value"])
        self.assertIsNone(rec["transliteration_value"]["value"])
    def test_duplicate_identity_and_variant_ids_rejected(self):
        bad=copy.deepcopy(self.payload);bad["records"].append(copy.deepcopy(bad["records"][0]))
        self.assertTrue(any("duplicate identity ID" in e for e in validate(bad)))
        bad=copy.deepcopy(self.payload);bad["records"][0]["variants"]=[{"variant_id":"v1","variant_status":"candidate","description":"synthetic","provenance":[]},{"variant_id":"v1","variant_status":"candidate","description":"synthetic","provenance":[]}]
        self.assertTrue(any("duplicate variant ID" in e for e in validate(bad)))
    def test_supported_claim_requires_citation_and_reference_integrity(self):
        bad=copy.deepcopy(self.payload);claim=bad["records"][0]["observed_hieratic"];claim.update(value="asserted",status="supported")
        self.assertTrue(any("supported claim requires" in e for e in validate(bad)))
        bad=copy.deepcopy(self.payload);bad["relations"]=[{"relation_id":"r1","from_identity_id":"missing","to_identity_id":"SYNTHETIC-OBS-001","relation_type":"variant_of","status":"proposed","confidence":None,"provenance":[]}]
        self.assertTrue(any("unknown identity" in e for e in validate(bad)))
    def test_supported_historical_claim_requires_verified_metadata_not_just_text(self):
        bad=copy.deepcopy(self.payload)
        claim=bad["records"][0]["observed_hieratic"]
        claim.update(value="synthetic-not-history",status="supported",citations=[{
            "citation_id":"synthetic-citation-1","reference":"fictional-book","claim_scope":"synthetic-only",
            "verified_metadata":False
        }])
        self.assertTrue(any("verified citation metadata" in e for e in validate(bad)))
        claim["citations"][0]["verified_metadata"]=True
        self.assertEqual([],validate(bad))

    def test_accepted_variant_must_have_verified_provenance(self):
        bad=copy.deepcopy(self.payload)
        bad["records"][0]["variants"]=[{"variant_id":"synthetic-v-1","variant_status":"accepted_variant","description":"synthetic","provenance":[]}]
        self.assertTrue(any("accepted variant requires verified provenance" in e for e in validate(bad)))

    def test_hierarchy_cycles_and_duplicate_edges_rejected(self):
        bad=copy.deepcopy(self.payload);bad["records"].append(copy.deepcopy(bad["records"][0]));bad["records"][1]["identity_id"]="SYNTHETIC-OBS-002"
        rel=lambda rid,a,b:{"relation_id":rid,"from_identity_id":a,"to_identity_id":b,"relation_type":"subclass_of","status":"proposed","confidence":None,"provenance":[]}
        bad["relations"]=[rel("r1","SYNTHETIC-OBS-001","SYNTHETIC-OBS-002"),rel("r2","SYNTHETIC-OBS-002","SYNTHETIC-OBS-001")]
        self.assertTrue(any("cycle" in e for e in validate(bad)))
        bad["relations"].append(rel("r3","SYNTHETIC-OBS-001","SYNTHETIC-OBS-002"))
        self.assertTrue(any("duplicate relation edge" in e for e in validate(bad)))



class RealHPDBConcordanceTests(unittest.TestCase):
    """Tests use genuine publisher CC BY metadata; no Tokyo image pixels."""

    @classmethod
    def setUpClass(cls):
        from tools.sign_mappings import load_hpdb_concordance
        cls.reference = load_hpdb_concordance()

    def _temporary_root(self):
        import tempfile
        import shutil
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        for sub in ("data/mappings/hpdb", "data/references/hpdb"):
            shutil.copytree(ROOT / sub, root / sub)
        return tmp, root

    def test_exact_original_publisher_git_blob_and_all_937_rows(self):
        from tools.sign_mappings import HPDB_CONCORDANCE_BLOB
        import hashlib
        original = ROOT / "data/mappings/hpdb/id_correspondence_ccby4.json"
        blob = original.read_bytes()
        observed = hashlib.sha1(b"blob " + str(len(blob)).encode("ascii") + b"\0" + blob).hexdigest()
        self.assertEqual("9de1829304fcb2c3b5ee054fd7bd0e6f1dea964b", observed)
        self.assertEqual(observed, HPDB_CONCORDANCE_BLOB)
        self.assertEqual(937, self.reference["counts"]["concordance_rows"])
        self.assertEqual(937, len({r["moller_no"] for r in self.reference["rows"]}))
        self.assertEqual({"matched": 628, "compound": 158, "unmatched": 124,
                          "unknown": 27}, self.reference["counts"]["match_types"])
        self.assertEqual("BLOCKED_REFERENCE_METADATA_ONLY",
                         self.reference["manifest"]["training_admission"])

    def test_real_index_join_and_twelve_documented_notation_discrepancies(self):
        from tools.sign_mappings import HPDB_EXPECTED_DISCREPANCIES
        counts = self.reference["counts"]
        self.assertEqual(2065, counts["sign_index_rows"])
        self.assertEqual(2053, counts["literal_exact_matches"])
        self.assertEqual(12, counts["literal_disagreements"])
        discrepant_ids = {x["item_id"] for x in self.reference["discrepancies"]}
        self.assertEqual(HPDB_EXPECTED_DISCREPANCIES, discrepant_ids)
        self.assertTrue(all(
            x["status"] == "PUBLISHED_METADATA_DISAGREEMENT_NOT_RESOLVED"
            and x["index_gardiner"] != x["concordance_gardiner"]
            for x in self.reference["discrepancies"]))

    def test_exact_moller_lookup_returns_published_not_original_source(self):
        from tools.sign_mappings import hpdb_query
        out = hpdb_query(self.reference, "moller_no", "1")
        self.assertEqual(1, out["total_concordance_matches"])
        self.assertTrue(out["not_gold_or_scientific_result"])
        first = out["results"][0]
        self.assertEqual("A26", first["concordance"]["gardiner_no"])
        self.assertEqual("matched", first["concordance"]["match_type"])
        self.assertEqual("PUBLISHED_PRINTED_NOTATION_LINK_ONLY_NOT_ORIGINAL_WITNESS",
                         first["link_status"])
        self.assertTrue(first["publisher_index_candidates"])
        self.assertTrue(all(x["printed_moller"] == "1" for x in first["publisher_index_candidates"]))

    def test_duplicate_gardiner_and_unicode_queries_preserve_all_competing_moller_ids(self):
        from tools.sign_mappings import hpdb_query
        matches = hpdb_query(self.reference, "gardiner_no", "D50", limit=100)
        self.assertGreater(matches["total_concordance_matches"], 1)
        self.assertEqual(matches["total_concordance_matches"], matches["returned_matches"])
        self.assertEqual(matches["total_concordance_matches"], len({
            x["concordance"]["moller_no"] for x in matches["results"]}))
        self.assertFalse(matches["truncated"])
        short = hpdb_query(self.reference, "gardiner_no", "D50", limit=1)
        self.assertEqual(1, short["returned_matches"])
        self.assertTrue(short["truncated"])
        self.assertEqual(matches["results"][0], short["results"][0])
        self.assertEqual([], hpdb_query(self.reference, "gardiner_no", "d50")["results"])
        self.assertEqual([], hpdb_query(self.reference, "gardiner_no", "D5")["results"])

    def test_nonmatched_row_never_becomes_verified_glyph(self):
        from tools.sign_mappings import hpdb_query
        out = hpdb_query(self.reference, "moller_no", "3")
        row = out["results"][0]["concordance"]
        self.assertEqual("unknown", row["match_type"])
        self.assertEqual("A??", row["gardiner_no"])
        self.assertEqual("", row["unicode_cp"])
        self.assertTrue(out["not_gold_or_scientific_result"])

    def test_different_publisher_notations_never_autocorrected(self):
        from tools.sign_mappings import hpdb_query
        out = hpdb_query(self.reference, "moller_no", "683")
        first = out["results"][0]
        self.assertEqual("V2", first["concordance"]["gardiner_no"])
        mismatched = [x for x in first["publisher_index_candidates"]
                      if x["item_id"] == "165017"]
        self.assertEqual(1, len(mismatched))
        self.assertEqual("O39", mismatched[0]["printed_gardiner"])
        self.assertFalse(mismatched[0]["printed_notation_agrees"])

    def test_query_rejects_fuzzy_or_unbounded_input(self):
        from tools.sign_mappings import hpdb_query, MappingError
        for field, value, limit in [
            ("missing", "A26", 20), ("gardiner_no", "", 20),
            ("gardiner_no", "A26", 0), ("gardiner_no", "A26", 101),
        ]:
            with self.subTest(field=field, value=value, limit=limit):
                with self.assertRaises(MappingError):
                    hpdb_query(self.reference, field, value, limit=limit)

    def test_source_bytes_tamper_rejected_even_with_valid_json(self):
        from tools.sign_mappings import load_hpdb_concordance, MappingError
        tmp, root = self._temporary_root()
        try:
            original = root / "data/mappings/hpdb/id_correspondence_ccby4.json"
            data = original.read_text(encoding="utf-8")
            original.write_text(data.replace('"A26"', '"A27"', 1), encoding="utf-8")
            with self.assertRaisesRegex(MappingError, "blob drift"):
                load_hpdb_concordance(root=root)
        finally:
            tmp.cleanup()

    def test_manifest_cannot_self_authorize_training(self):
        from tools.sign_mappings import load_hpdb_concordance, MappingError
        import json
        tmp, root = self._temporary_root()
        try:
            p = root / "data/mappings/hpdb/concordance_manifest.json"
            data = json.loads(p.read_text(encoding="utf-8"))
            data["training_admission"] = "APPROVED"
            p.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(MappingError, "training_admission"):
                load_hpdb_concordance(root=root)
        finally:
            tmp.cleanup()

    def test_source_index_drift_rejected_without_falsely_resolving_disagreements(self):
        from tools.sign_mappings import load_hpdb_concordance, MappingError
        import json
        tmp, root = self._temporary_root()
        try:
            p = root / "data/references/hpdb/moller_v1_ccby4_metadata.jsonl"
            lines = p.read_text(encoding="utf-8").splitlines()
            for ix, line in enumerate(lines):
                row = json.loads(line)
                if row["id"] == "165017":
                    row["gardiner_printed"] = "V2"
                    lines[ix] = json.dumps(row)
                    break
            p.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(MappingError, "consistency audit changed"):
                load_hpdb_concordance(root=root)
        finally:
            tmp.cleanup()

    def test_cli_offline_verify_and_search(self):
        from tools.sign_mappings import main
        from contextlib import redirect_stdout, redirect_stderr
        import io, json
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, main(["hpdb-verify", "--disagreements"]))
        actual = json.loads(output.getvalue())
        self.assertEqual(12, len(actual["disagreements"]))
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, main([
                "hpdb-search", "--field", "moller_no", "--exact", "1"]))
        self.assertEqual("A26", json.loads(output.getvalue())["results"][0]["concordance"]["gardiner_no"])
        with redirect_stderr(io.StringIO()):
            self.assertEqual(1, main([
                "hpdb-search", "--field", "gardiner_no", "--exact", "D50", "--limit", "0"]))

    def test_no_external_media_fetch_or_new_corpus_admission_in_lookup(self):
        from tools import sign_mappings
        source = Path(sign_mappings.__file__).read_text(encoding="utf-8")
        self.assertNotIn("requests.get(", source)
        self.assertNotIn("urlopen(", source)
        self.assertEqual(0, self.reference["counts"]["physical_original_manuscripts_verified"])
        self.assertEqual(0, self.reference["counts"]["expert_gold_lines"])

if __name__=="__main__":unittest.main()
