from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import yaml

from tools import preprocessing, release_corpus, split_system
from tools.source_registry import load_yaml

ROOT = Path(__file__).resolve().parents[2]


def _yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def make_bundle(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    base = tmp_path / "bundle"
    base.mkdir()
    (base / "fixtures").mkdir()
    (base / "artifacts").mkdir()

    shutil.copyfile(ROOT / "data/preprocessing/fixtures/synthetic-2x2.ppm", base / "fixtures/input.ppm")
    acquisition = _yaml(ROOT / "data/alignment/examples/acquisition.synthetic.yaml")
    acquisition["items"][0]["source_object_id"] = "SYNTHETIC-OBJECT-002"
    registry = _yaml(ROOT / "data/sources/registry.yaml")
    acquisition["items"][0]["required_attribution"] = next(s["attribution_requirements"] for s in registry["sources"] if s["source_id"] == "SRC-HPDB")
    (base / "acquisition.yaml").write_text(yaml.safe_dump(acquisition, sort_keys=False), encoding="utf-8")

    request = _yaml(ROOT / "data/preprocessing/examples/synthetic.yaml")
    request["items"][0]["asset_path"] = "fixtures/input.ppm"
    (base / "preprocessing.yaml").write_text(yaml.safe_dump(request, sort_keys=False), encoding="utf-8")
    preprocessing.run(base / "preprocessing.yaml", base / "artifacts")

    annotation = _yaml(ROOT / "data/examples/annotation_ambiguous.yaml")
    (base / "annotation.yaml").write_text(yaml.safe_dump(annotation, sort_keys=False, allow_unicode=True), encoding="utf-8")
    mapping = _yaml(ROOT / "data/mappings/examples/synthetic.yaml")
    (base / "mapping.yaml").write_text(yaml.safe_dump(mapping, sort_keys=False), encoding="utf-8")
    alignment = _yaml(ROOT / "data/alignment/examples/synthetic.yaml")
    alignment["acquisition_item_source_object_id"] = "SYNTHETIC-OBJECT-002"
    alignment["annotation_id"] = annotation["annotation_id"]
    alignment["alignments"][0].update({"page_id": "page-2", "region_ids": ["region-2-line-block"], "targets": [{"target_type": "line", "target_id": "line-2"}]})
    uncovered = copy.deepcopy(alignment["alignments"][0])
    uncovered.update({"alignment_id": "alignment-region-2", "region_ids": ["region-2"], "targets": [], "relation": "unresolved", "status": "unresolved"})
    alignment["alignments"].append(uncovered)
    (base / "alignment.yaml").write_text(yaml.safe_dump(alignment, sort_keys=False), encoding="utf-8")
    review = _yaml(ROOT / "data/review/examples/disagreement.synthetic.yaml")
    (base / "review.yaml").write_text(yaml.safe_dump(review, sort_keys=False), encoding="utf-8")

    source_meta = _yaml(ROOT / "eval/splits/examples/synthetic_metadata.yaml")
    row = copy.deepcopy(next(item for item in source_meta["items"] if item["source_id"] == "SRC-HPDB"))
    row.update({"item_id": "release-item-1", "document_id": "synthetic-doc-2", "page_id": "page-2", "source_object_id": "SYNTHETIC-OBJECT-002"})
    source_meta["items"] = [row]
    source_meta["near_duplicate_candidates"] = []
    (base / "split-metadata.yaml").write_text(yaml.safe_dump(source_meta, sort_keys=False), encoding="utf-8")
    profiles = _yaml(ROOT / "eval/splits/profiles.yaml")
    split = split_system.generate_manifest(source_meta, profiles, "PROFILE-DOC-HOLDOUT", 7,
                                           generated_at="2026-10-08T00:00:00Z", registry=load_yaml(ROOT / "data/sources/registry.yaml"))
    (base / "split.yaml").write_text(yaml.safe_dump(split, sort_keys=False), encoding="utf-8")

    bundle = {
        "schema_version": "1.0.0", "release_id": "synthetic-release-test", "release_kind": "synthetic_test_release",
        "split_metadata_path": "split-metadata.yaml", "split_manifest_path": "split.yaml",
        "items": [{
            "item_id": "release-item-1", "document_id": "synthetic-doc-2", "page_id": "page-2", "split_item_id": "release-item-1",
            "acquisition_path": "acquisition.yaml", "preprocessing_request_path": "preprocessing.yaml",
            "preprocessing_artifact_manifest_path": "artifacts/dataset-manifest.json", "preprocessing_artifact_root": "artifacts",
            "annotation_path": "annotation.yaml", "mapping_path": "mapping.yaml", "alignment_path": "alignment.yaml", "review_path": "review.yaml",
            "preprocessing_item_id": "synthetic-page-1", "alignment_ids": ["alignment-line-1", "alignment-region-2"], "review_case_ids": ["synthetic-case-1"],
            "annotation_training_permission": "unknown", "annotation_redistribution_permission": "unknown", "annotation_rights_evidence_ref": "synthetic:fixture-only",
            "mapping_training_permission": "unknown", "mapping_redistribution_permission": "unknown", "mapping_rights_evidence_ref": "synthetic:fixture-only"
        }]
    }
    bundle_path = base / "bundle.yaml"
    bundle_path.write_text(yaml.safe_dump(bundle, sort_keys=False), encoding="utf-8")
    return bundle_path


class CorpusReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def bundle(self, name="case"):
        return make_bundle(self.root / name)

    def test_synthetic_release_validation_and_build_are_deterministic(self):
        path = self.bundle()
        bundle = release_corpus.read_document(path)
        result, errors = release_corpus.validate_bundle(bundle, path)
        self.assertEqual([], errors)
        record = result["release"]["items"][0]
        self.assertTrue(record["synthetic"])
        self.assertEqual("uncertain_with_alternatives", record["target_annotations"][0]["targets"][0]["annotation"]["grapheme_sequence"]["gold_status"])
        self.assertTrue(record["review_cases"][0]["decisions"])
        self.assertEqual("synthetic_test_release", result["release"]["release_kind"])
        output_a, output_b = self.root / "published-a", self.root / "published-b"
        release_corpus.publish(result, output_a, path)
        first = {p.name: p.read_bytes() for p in output_a.iterdir()}
        with self.assertRaisesRegex(release_corpus.ReleaseError, "already exists"):
            release_corpus.publish(result, output_a, path)
        again, errors = release_corpus.validate_bundle(bundle, path)
        self.assertEqual([], errors)
        release_corpus.publish(again, output_b, path)
        self.assertEqual(first, {p.name: p.read_bytes() for p in output_b.iterdir()})
        self.assertEqual({"release-manifest.json", "export.jsonl", "dataset-card.md", "rejection-report.json", "audit-trail.json"}, set(first))
        manifest_a = json.loads(first["release-manifest.json"])
        manifest_b = json.loads((output_b / "release-manifest.json").read_bytes())
        self.assertEqual(manifest_a["dataset_version_id"], manifest_b["dataset_version_id"])
        self.assertIn("not a licensed production corpus", first["dataset-card.md"].decode())

    def test_mutated_unsafe_upstream_states_are_rejected(self):
        cases = {
            "benchmark": "benchmark-quarantined",
            "rights": "rights_class snapshot does not match",
            "source_identity": "annotation/acquisition source identity differs",
            "preprocessed_hash": "preprocessed output hash mismatch",
        }
        for mutation, expected in cases.items():
            with self.subTest(mutation=mutation):
                path = self.bundle(mutation)
                base = path.parent
                if mutation in {"benchmark", "rights"}:
                    acq = _yaml(base / "acquisition.yaml")
                    if mutation == "benchmark":
                        acq["items"][0]["benchmark_quarantine"] = True
                    else:
                        acq["items"][0]["source_rights_snapshot"]["rights_class"] = "UNKNOWN"
                    (base / "acquisition.yaml").write_text(yaml.safe_dump(acq), encoding="utf-8")
                elif mutation == "source_identity":
                    ann = _yaml(base / "annotation.yaml")
                    ann["provenance"]["source_registry_id"] = "SRC-DDD"
                    (base / "annotation.yaml").write_text(yaml.safe_dump(ann), encoding="utf-8")
                else:
                    artifact = base / "artifacts/synthetic-page-1.png"
                    artifact.write_bytes(artifact.read_bytes() + b"tamper")
                result, errors = release_corpus.validate_bundle(release_corpus.read_document(path), path)
                self.assertEqual({}, result)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_production_label_rejects_synthetic_fixture_and_insufficient_gold(self):
        path = self.bundle()
        bundle = release_corpus.read_document(path)
        bundle["release_kind"] = "corpus_v1_release"
        result, errors = release_corpus.validate_bundle(bundle, path)
        self.assertEqual({}, result)
        self.assertTrue(any("synthetic fixture cannot be labeled" in error for error in errors), errors)
        self.assertTrue(any("no expert-reviewed" in error for error in errors), errors)

    def test_bundle_rejects_symlinked_input(self):
        path = self.bundle()
        base = path.parent
        linked = base / "linked.yaml"
        try:
            linked.symlink_to(base / "annotation.yaml")
        except (OSError, NotImplementedError):
            self.skipTest("this Windows account cannot create symlinks")
        bundle = release_corpus.read_document(path)
        bundle["items"][0]["annotation_path"] = "linked.yaml"
        result, errors = release_corpus.validate_bundle(bundle, path)
        self.assertEqual({}, result)
        self.assertTrue(any("symlink input path is forbidden" in error for error in errors), errors)

    def test_bundle_rejects_path_traversal(self):
        path = self.bundle()
        bundle = release_corpus.read_document(path)
        bundle["items"][0]["annotation_path"] = "../../outside.yaml"
        result, errors = release_corpus.validate_bundle(bundle, path)
        self.assertEqual({}, result)
        self.assertTrue(any("path escapes bundle directory" in error for error in errors), errors)

    def test_existing_output_is_not_overwritten(self):
        path = self.bundle()
        result, errors = release_corpus.validate_bundle(release_corpus.read_document(path), path)
        self.assertEqual([], errors)
        target = self.root / "exists"
        target.mkdir()
        marker = target / "keep.txt"
        marker.write_text("unchanged", encoding="utf-8")
        with self.assertRaisesRegex(release_corpus.ReleaseError, "already exists"):
            release_corpus.publish(result, target, path)
        self.assertEqual("unchanged", marker.read_text(encoding="utf-8"))
        self.assertEqual([], list(self.root.glob(".exists.staging-*")))

    def test_existing_empty_output_is_not_replaced(self):
        path = self.bundle()
        result, errors = release_corpus.validate_bundle(release_corpus.read_document(path), path)
        self.assertEqual([], errors)
        target = self.root / "empty-existing"
        target.mkdir()
        with self.assertRaisesRegex(release_corpus.ReleaseError, "already exists"):
            release_corpus.publish(result, target, path)
        self.assertEqual([], list(target.iterdir()))
        self.assertEqual([], list(self.root.glob(".empty-existing.staging-*")))

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux renameat2 race regression runs in hosted CI")
    def test_simultaneous_publishers_have_one_complete_winner(self):
        path = self.bundle()
        result, errors = release_corpus.validate_bundle(release_corpus.read_document(path), path)
        self.assertEqual([], errors)
        target = self.root / "concurrent"
        barrier = threading.Barrier(2)
        original = release_corpus._rename_linux_noreplace

        def synchronized_rename(parent_fd, staging_name, output_name):
            barrier.wait(timeout=10)
            return original(parent_fd, staging_name, output_name)

        def attempt():
            try:
                release_corpus.publish(result, target, path)
                return "published"
            except release_corpus.ReleaseError:
                return "refused"

        with patch.object(release_corpus, "_rename_linux_noreplace", new=synchronized_rename):
            with ThreadPoolExecutor(max_workers=2) as executor:
                outcomes = list(executor.map(lambda _: attempt(), range(2)))
        self.assertCountEqual(["published", "refused"], outcomes)
        self.assertEqual({"release-manifest.json", "export.jsonl", "dataset-card.md", "rejection-report.json", "audit-trail.json"}, {p.name for p in target.iterdir()})
        self.assertEqual([], list(self.root.glob(".concurrent.staging-*")))

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux no-replace race regression runs in hosted CI")
    def test_empty_destination_created_at_finalize_is_not_clobbered(self):
        path = self.bundle()
        result, errors = release_corpus.validate_bundle(release_corpus.read_document(path), path)
        self.assertEqual([], errors)
        target = self.root / "race-empty"
        original = release_corpus._rename_linux_noreplace

        def create_empty_then_rename(parent_fd, staging_name, output_name):
            target.mkdir()
            return original(parent_fd, staging_name, output_name)

        with patch.object(release_corpus, "_rename_linux_noreplace", new=create_empty_then_rename):
            with self.assertRaisesRegex(release_corpus.ReleaseError, "already exists"):
                release_corpus.publish(result, target, path)
        self.assertEqual([], list(target.iterdir()))
        self.assertEqual([], list(self.root.glob(".race-empty.staging-*")))

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux symlink-swap regression runs in hosted CI")
    def test_symlink_swap_at_finalize_is_not_followed(self):
        path = self.bundle()
        result, errors = release_corpus.validate_bundle(release_corpus.read_document(path), path)
        self.assertEqual([], errors)
        target = self.root / "symlink-race"
        protected = self.root / "protected"
        protected.mkdir()
        sentinel = protected / "keep.txt"
        sentinel.write_text("untouched", encoding="utf-8")
        original = release_corpus._rename_linux_noreplace

        def swap_symlink_then_rename(parent_fd, staging_name, output_name):
            target.symlink_to(protected, target_is_directory=True)
            return original(parent_fd, staging_name, output_name)

        with patch.object(release_corpus, "_rename_linux_noreplace", new=swap_symlink_then_rename):
            with self.assertRaisesRegex(release_corpus.ReleaseError, "already exists"):
                release_corpus.publish(result, target, path)
        self.assertTrue(target.is_symlink())
        self.assertEqual("untouched", sentinel.read_text(encoding="utf-8"))
        self.assertEqual([], list(self.root.glob(".symlink-race.staging-*")))

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux parent-swap regression runs in hosted CI")
    def test_parent_path_swap_at_finalize_is_detected_and_rolled_back(self):
        path = self.bundle()
        result, errors = release_corpus.validate_bundle(release_corpus.read_document(path), path)
        self.assertEqual([], errors)
        parent = self.root / "parent"
        parent.mkdir()
        moved_parent = self.root / "parent-moved"
        other = self.root / "other"
        other.mkdir()
        target = parent / "release"
        original = release_corpus._rename_linux_noreplace

        def swap_parent_then_rename(parent_fd, staging_name, output_name):
            parent.rename(moved_parent)
            parent.symlink_to(other, target_is_directory=True)
            return original(parent_fd, staging_name, output_name)

        with patch.object(release_corpus, "_rename_linux_noreplace", new=swap_parent_then_rename):
            with self.assertRaisesRegex(release_corpus.ReleaseError, "parent path changed"):
                release_corpus.publish(result, target, path)
        self.assertFalse((moved_parent / "release").exists())
        self.assertFalse((other / "release").exists())
        self.assertEqual([], list(moved_parent.glob(".release.staging-*")))

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux symlink policy is checked in hosted CI")
    def test_output_parent_symlink_is_rejected(self):
        path = self.bundle()
        result, errors = release_corpus.validate_bundle(release_corpus.read_document(path), path)
        self.assertEqual([], errors)
        real_parent = self.root / "real-parent"
        real_parent.mkdir()
        linked_parent = self.root / "linked-parent"
        linked_parent.symlink_to(real_parent, target_is_directory=True)
        with self.assertRaisesRegex(release_corpus.ReleaseError, "symlink"):
            release_corpus.publish(result, linked_parent / "release", path)
        self.assertFalse((real_parent / "release").exists())

    def test_failed_midwrite_cleans_staging_and_publishes_nothing(self):
        path = self.bundle()
        result, errors = release_corpus.validate_bundle(release_corpus.read_document(path), path)
        self.assertEqual([], errors)
        output = self.root / "never-published"
        original = release_corpus._write_staging_file

        def fail_on_export(staging, staging_fd, name, content):
            if name == "export.jsonl":
                raise OSError("synthetic injected disk failure")
            return original(staging, staging_fd, name, content)

        with patch.object(release_corpus, "_write_staging_file", new=fail_on_export):
            with self.assertRaisesRegex(OSError, "injected disk failure"):
                release_corpus.publish(result, output, path)
        self.assertFalse(output.exists())
        self.assertEqual([], list(self.root.glob(".never-published.staging-*")))


if __name__ == "__main__":
    unittest.main()
