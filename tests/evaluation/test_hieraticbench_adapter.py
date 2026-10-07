"""Synthetic, offline tests: no real HieraticBench images, answers or model outputs."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from eval.benchmarks.hieraticbench import adapter


class HieraticBenchAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.checkout = Path(self.temp.name)
        self.items_dir = self.checkout / "data" / "items"
        self.runs_dir = self.checkout / "results" / "runs"
        self.items_dir.mkdir(parents=True)
        self.runs_dir.mkdir(parents=True)

        self.items = [
            {"id": "foo-0001", "split": "public", "rungs": ["identify"], "script": "hieratic"},
            {"id": "foo-0002", "split": "public", "rungs": ["identify", "signs"], "script": "demotic"},
            {"id": "hb-0001", "split": "sealed", "rungs": ["identify", "signs", "transliterate", "translate"], "script": "hieratic"},
        ]
        for item in self.items:
            (self.items_dir / f"{item['id']}.json").write_text(json.dumps(item), encoding="utf-8")
        self.manifest = {
            "benchmark": {"pinned_commit": "synthetic-test-revision"},
            "inventory": {
                "items": 3, "public": 2, "sealed": 1,
                "by_source": {"foo": 2, "hb": 1},
                "by_rung": {"identify": 3, "signs": 2, "transliterate": 1, "translate": 1},
                "by_script": {"hieratic": 2, "demotic": 1},
            },
        }

    def record(self, item_id: str, rung: str, score: float | None, sample: int = 0, response: str = "") -> dict:
        return {
            "model": {"key": "mock-model", "label": "Mock (synthetic)", "provider": "synthetic", "id": "mock"},
            "itemId": item_id, "rung": rung, "sample": sample,
            "score": score, "response": response,
            "createdAt": "2026-01-01T00:00:00Z",
        }

    def write_runs(self, records: list[dict]) -> None:
        (self.runs_dir / "synthetic.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
        )

    def metadata(self) -> dict:
        return adapter.inspect_items(self.checkout, self.manifest)

    def write_official_board(self) -> None:
        board = {
            "dataset": {
                "items": 3, "sealed": 1,
                "bySource": {"foo": 2, "hb": 1},
                "byScript": {"hieratic": 2, "demotic": 1},
                "byRung": {"identify": 3, "signs": 2, "transliterate": 1, "translate": 1},
            },
            "entries": [{
                "key": "mock-model",
                "rungs": {
                    "identify": {"score": 1 / 3, "items": 3, "samples": 4, "coverage": 1},
                    "signs": {"score": 1, "items": 1, "samples": 1, "coverage": 0.5},
                },
            }],
            "perItem": {
                "foo-0001": {"mock-model": {"identify": 0.5}},
                "foo-0002": {"mock-model": {"identify": 0, "signs": 1}},
                "hb-0001": {"mock-model": {"identify": 0.5}},
            },
        }
        (self.checkout / "results" / "leaderboard.json").write_text(
            json.dumps(board), encoding="utf-8"
        )

    def sample_records(self) -> list[dict]:
        return [
            self.record("foo-0001", "identify", 1, 0),
            self.record("foo-0001", "identify", 0, 1),
            self.record("foo-0002", "identify", 0),
            self.record("foo-0002", "signs", 1),
            self.record("hb-0001", "identify", 0.5, response=""),
            self.record("hb-0001", "signs", None, response=""),
        ]

    def test_inventory_is_metadata_only_and_counts_correctly(self) -> None:
        self.assertEqual(3, len(self.metadata()))
        self.assertNotIn("gardiner", self.metadata()["foo-0002"])
        self.assertNotIn("image", self.metadata()["foo-0001"])

    def test_inventory_mismatch_is_rejected(self) -> None:
        self.manifest["inventory"]["items"] = 4
        with self.assertRaisesRegex(adapter.BenchmarkAuditError, "Inventory mismatch"):
            self.metadata()

    def test_sealed_answer_field_in_metadata_is_rejected(self) -> None:
        item = dict(self.items[-1], translation=["synthetic answer"])
        (self.items_dir / "hb-0001.json").write_text(json.dumps(item), encoding="utf-8")
        with self.assertRaisesRegex(adapter.BenchmarkAuditError, "Sealed answer-bearing"):
            self.metadata()

    def test_exact_upstream_style_aggregation_with_item_means(self) -> None:
        self.write_runs(self.sample_records())
        groups, per_item, count = adapter.aggregate_public_scores(self.checkout, self.metadata())
        self.assertEqual(6, count)
        self.assertAlmostEqual(1 / 3, groups["mock-model"]["identify"]["score"])
        self.assertEqual(4, groups["mock-model"]["identify"]["samples"])
        self.assertEqual(3, groups["mock-model"]["identify"]["items"])
        self.assertEqual(0.5, per_item["foo-0001"]["mock-model"]["identify"])
        self.assertEqual(1, groups["mock-model"]["signs"]["score"])
        self.assertEqual(0.5, groups["mock-model"]["signs"]["coverage"])

    def test_public_leaderboard_numbers_reproduce(self) -> None:
        self.write_runs(self.sample_records())
        self.write_official_board()
        result = adapter.verify_leaderboard(self.checkout, self.metadata())
        self.assertEqual(3, result["item_records"])
        self.assertEqual(6, result["public_run_records_examined"])
        self.assertEqual(2, result["rung_aggregates_verified"])
        self.assertEqual(4, result["item_rung_model_means_verified"])

    def test_modified_leaderboard_fails_closed(self) -> None:
        self.write_runs(self.sample_records())
        self.write_official_board()
        path = self.checkout / "results" / "leaderboard.json"
        board = json.loads(path.read_text(encoding="utf-8"))
        board["entries"][0]["rungs"]["identify"]["score"] = 0.9
        path.write_text(json.dumps(board), encoding="utf-8")
        with self.assertRaisesRegex(adapter.BenchmarkAuditError, "Published score mismatch"):
            adapter.verify_leaderboard(self.checkout, self.metadata())

    def test_sealed_response_text_in_public_runs_rejected(self) -> None:
        records = self.sample_records()
        records[-1]["response"] = "synthetic secret placeholder"
        self.write_runs(records)
        with self.assertRaisesRegex(adapter.BenchmarkAuditError, "sealed response"):
            adapter.aggregate_public_scores(self.checkout, self.metadata())

    def test_private_copy_in_public_runs_rejected(self) -> None:
        records = self.sample_records()
        records[0]["privateCopy"] = True
        self.write_runs(records)
        with self.assertRaisesRegex(adapter.BenchmarkAuditError, "sealed response"):
            adapter.aggregate_public_scores(self.checkout, self.metadata())

    def test_unknown_item_in_public_results_rejected(self) -> None:
        self.write_runs([self.record("missing-9999", "identify", 1)])
        with self.assertRaisesRegex(adapter.BenchmarkAuditError, "unknown item"):
            adapter.aggregate_public_scores(self.checkout, self.metadata())

    def test_missing_or_invalid_rung_rejected(self) -> None:
        self.write_runs([self.record("foo-0001", "signs", 1)])
        with self.assertRaisesRegex(adapter.BenchmarkAuditError, "invalid item rung"):
            adapter.aggregate_public_scores(self.checkout, self.metadata())

    def test_unscored_sealed_output_is_not_fabricated_into_score(self) -> None:
        self.write_runs([self.record("hb-0001", "translate", None)])
        groups, _per_item, count = adapter.aggregate_public_scores(self.checkout, self.metadata())
        self.assertEqual(1, count)
        self.assertEqual({}, groups)

    def test_invalid_numeric_score_rejected(self) -> None:
        self.write_runs([self.record("foo-0001", "identify", 1.1)])
        with self.assertRaisesRegex(adapter.BenchmarkAuditError, "invalid public score"):
            adapter.aggregate_public_scores(self.checkout, self.metadata())

    def test_no_source_or_training_files_created(self) -> None:
        before = {str(p) for p in self.checkout.rglob("*")}
        self.write_runs(self.sample_records())
        adapter.aggregate_public_scores(self.checkout, self.metadata())
        after = {str(p) for p in self.checkout.rglob("*")}
        self.assertEqual(before | {str(self.runs_dir / "synthetic.jsonl")}, after)


if __name__ == "__main__":
    unittest.main()
