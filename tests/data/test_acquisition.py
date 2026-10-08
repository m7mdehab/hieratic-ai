from __future__ import annotations

import copy
import hashlib
import json
import os
import socket
import tempfile
import threading
import unittest
import unittest.mock
from pathlib import Path

import yaml

from tools import acquisition


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "data" / "acquisition" / "examples"


class AcquisitionManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = yaml.safe_load((ROOT / "data/sources/registry.yaml").read_text(encoding="utf-8"))
        self.schema = json.loads((ROOT / "schemas/acquisition_manifest.schema.json").read_text(encoding="utf-8"))

    def load_example(self, name: str) -> dict:
        return yaml.safe_load((EXAMPLES / name).read_text(encoding="utf-8"))

    def check(self, manifest: dict, registry: dict | None = None):
        return acquisition.validate_data(copy.deepcopy(manifest), copy.deepcopy(registry or self.registry), self.schema)

    def synthetic_reviewed_aku_manifest(self) -> dict:
        manifest = self.load_example("aku-pal-conditional.yaml")
        item = manifest["items"][0]
        item["is_synthetic_fixture"] = True
        item["review_conditions"] = [
            {"condition_id": condition_id, "satisfied": True, "evidence_urls": ["https://example.invalid/mock-review"], "notes": "synthetic fixture evidence"}
            for condition_id in sorted(
                set(next(source for source in self.registry["sources"] if source["source_id"] == "SRC-AKU-PAL")["automated_access_constraints"])
                | set(next(source for source in self.registry["sources"] if source["source_id"] == "SRC-AKU-PAL")["project_review_markers"])
            )
        ]
        item["item_rights_review"] = {
            "item_url": "synthetic://aku-pal/item-001",
            "license_identifier": "SYNTHETIC-LICENSE-REVIEWED",
            "rightsholder": "Synthetic rightsholder fixture",
            "reviewer_id": "synthetic-reviewer-001",
            "approval_status": "approved",
            "evidence_ref": "synthetic:rights-review-001",
            "reviewed_at": "2026-10-08T10:00:00Z",
        }
        item["benchmark_overlap_review"] = {
            "status": "clear",
            "reviewer_id": "synthetic-reviewer-001",
            "evidence_ref": "synthetic:overlap-review-001",
            "overlap_check_version": "synthetic-overlap-check/1",
            "reviewed_at": "2026-10-08T10:00:00Z",
        }
        return manifest

    def test_canonical_example_manifests_validate_or_fail_as_documented(self) -> None:
        allowed, plan = self.check(self.load_example("hieraticbench-evaluation.yaml"))
        self.assertEqual([], allowed)
        self.assertEqual("ALLOWED", plan[0]["decision"])
        reference, _ = self.check(self.load_example("hpdb-reference.yaml"))
        self.assertEqual([], reference)
        for name in ("hieraticbench-training-blocked.yaml", "papyrus-blocked.yaml", "aku-pal-conditional.yaml"):
            errors, plan = self.check(self.load_example(name))
            self.assertTrue(errors, name)
            self.assertEqual("REFUSED", plan[0]["decision"], name)

    def test_unknown_source_id_fails(self) -> None:
        manifest = self.load_example("hpdb-reference.yaml")
        manifest["items"][0]["source_id"] = "SRC-UNKNOWN"
        errors, _ = self.check(manifest)
        self.assertTrue(any("unknown source_id SRC-UNKNOWN" in error for error in errors), errors)

    def test_missing_source_id_fails_schema_validation(self) -> None:
        manifest = self.load_example("hpdb-reference.yaml")
        del manifest["items"][0]["source_id"]
        errors, _ = self.check(manifest)
        self.assertTrue(any("source_id" in error and "required" in error for error in errors), errors)

    def test_hieraticbench_training_fails_even_if_manifest_snapshot_claims_allowed(self) -> None:
        errors, _ = self.check(self.load_example("hieraticbench-training-blocked.yaml"))
        self.assertTrue(any("EVALUATION-ONLY" in error for error in errors), errors)
        self.assertTrue(any("benchmark-quarantined" in error for error in errors), errors)

    def test_tla_training_and_bulk_mode_fail(self) -> None:
        manifest = self.load_example("papyrus-blocked.yaml")
        item = manifest["items"][0]
        item.update({
            "source_id": "SRC-TLA",
            "canonical_object_url": "https://thesaurus-linguae-aegyptiae.de/info/text-corpus?lang=en",
            "intended_use": "training",
            "source_rights_snapshot": {"rights_class": "RESTRICTED", "use_decision": "prohibited"},
            "required_attribution": "Follow the official license page and source-specific attribution for any individually permitted academic quotation",
            "benchmark_quarantine": False,
            "benchmark_overlap_risk": "unknown",
            "provenance_urls": ["https://thesaurus-linguae-aegyptiae.de/info/licenses"],
            "evidence_urls": ["https://thesaurus-linguae-aegyptiae.de/info/licenses"],
            "acquisition_mode": "api",
        })
        errors, _ = self.check(manifest)
        self.assertTrue(any("refuses training use" in error for error in errors), errors)

    def test_not_approved_sources_fail_closed(self) -> None:
        manifest = self.load_example("papyrus-blocked.yaml")
        errors, _ = self.check(manifest)
        self.assertTrue(any("not_approved" in error for error in errors), errors)
        for source_id in ("SRC-ISUT", "SRC-HIERATICAI"):
            with self.subTest(source_id=source_id):
                isut_registry = copy.deepcopy(self.registry)
                source = next(source for source in isut_registry["sources"] if source["source_id"] == source_id)
                candidate = copy.deepcopy(manifest)
                candidate["items"][0].update({
                    "source_id": source_id,
                    "canonical_object_url": source["canonical_url"],
                    "source_rights_snapshot": {"rights_class": source["rights_class"], "use_decision": source["training_use"]},
                    "required_attribution": source["attribution_requirements"],
                    "benchmark_quarantine": source["benchmark_quarantine"],
                    "benchmark_overlap_risk": source["benchmark_overlap_risk"],
                    "provenance_urls": [source["canonical_url"]],
                    "evidence_urls": [source["canonical_url"]],
                })
                errors, _ = self.check(candidate, isut_registry)
                self.assertTrue(any("not_approved" in error for error in errors), errors)

    def test_conditional_aku_pal_requires_item_review_conditions_and_evidence(self) -> None:
        errors, _ = self.check(self.load_example("aku-pal-conditional.yaml"))
        self.assertTrue(any("lacks explicit conditions" in error for error in errors), errors)
        self.assertTrue(any("item-specific license" in error for error in errors), errors)
        self.assertTrue(any("benchmark-overlap" in error for error in errors), errors)

    def test_synthetic_reviewed_aku_is_only_a_plan_and_never_admitted(self) -> None:
        manifest = self.synthetic_reviewed_aku_manifest()
        registry = copy.deepcopy(self.registry)
        aku = next(source for source in registry["sources"] if source["source_id"] == "SRC-AKU-PAL")
        errors, plans = self.check(manifest, registry)
        self.assertEqual([], errors)
        self.assertEqual("CONDITIONAL PLAN READY", plans[0]["decision"])
        self.assertEqual("NOT ADMITTED — synthetic fixture only", plans[0]["admission_status"])
        self.assertNotIn("ALLOWED", plans[0]["decision"])
        changed_registry = copy.deepcopy(registry)
        changed_aku = next(source for source in changed_registry["sources"] if source["source_id"] == "SRC-AKU-PAL")
        changed_aku["training_use"] = "prohibited"
        errors, plans = self.check(manifest, changed_registry)
        self.assertTrue(any("refuses training use" in error for error in errors), errors)
        self.assertEqual("REFUSED", plans[0]["decision"])

    def test_placeholder_evidence_cannot_satisfy_real_item_review(self) -> None:
        manifest = self.synthetic_reviewed_aku_manifest()
        item = manifest["items"][0]
        item["is_synthetic_fixture"] = False
        item["item_rights_review"].update({
            "item_url": "https://aku-pal.uni-mainz.de/hieratogram/123",
            "evidence_ref": "https://example.invalid/review/rights",
        })
        item["benchmark_overlap_review"]["evidence_ref"] = "https://example.invalid/review/overlap"
        errors, plans = self.check(manifest)
        self.assertTrue(any("placeholder evidence" in error for error in errors), errors)
        self.assertEqual("REFUSED", plans[0]["decision"])

    def test_arbitrary_non_url_review_evidence_cannot_approve_real_item(self) -> None:
        for evidence_ref in ("reviewed by me", "artifact:unclear", "https://", "https://example.invalid/review", "https://github.com/"):
            with self.subTest(evidence_ref=evidence_ref):
                manifest = self.synthetic_reviewed_aku_manifest()
                item = manifest["items"][0]
                item["is_synthetic_fixture"] = False
                item["item_rights_review"].update({
                    "item_url": "https://aku-pal.uni-mainz.de/hieratogram/123",
                    "evidence_ref": evidence_ref,
                })
                item["benchmark_overlap_review"]["evidence_ref"] = evidence_ref
                errors, plans = self.check(manifest)
                self.assertTrue(any("non-placeholder evidence reference" in error for error in errors), errors)
                self.assertEqual("REFUSED", plans[0]["decision"])

    def test_missing_accountable_rights_reviewer_is_refused(self) -> None:
        manifest = self.synthetic_reviewed_aku_manifest()
        manifest["items"][0]["item_rights_review"]["reviewer_id"] = None
        errors, plans = self.check(manifest)
        self.assertTrue(any("item rights review requires an accountable reviewer" in error for error in errors), errors)
        self.assertEqual("REFUSED", plans[0]["decision"])

    def test_unknown_item_license_or_rightsholder_is_refused(self) -> None:
        for field in ("license_identifier", "rightsholder"):
            with self.subTest(field=field):
                manifest = self.synthetic_reviewed_aku_manifest()
                manifest["items"][0]["item_rights_review"][field] = "unknown"
                errors, plans = self.check(manifest)
                self.assertTrue(any("requires a known item-specific license" in error or "requires an identified rightsholder" in error for error in errors), errors)
                self.assertEqual("REFUSED", plans[0]["decision"])

    def test_missing_clear_benchmark_review_is_refused(self) -> None:
        manifest = self.synthetic_reviewed_aku_manifest()
        manifest["items"][0]["benchmark_overlap_review"]["status"] = "not_assessed"
        errors, plans = self.check(manifest)
        self.assertTrue(any("requires a clear benchmark-overlap assessment" in error for error in errors), errors)
        self.assertEqual("REFUSED", plans[0]["decision"])

    def test_complete_download_requires_actual_sha256_and_retrieval_time(self) -> None:
        manifest = self.load_example("hieraticbench-evaluation.yaml")
        item = manifest["items"][0]
        item.update({"acquisition_mode": "direct_download", "acquisition_status": "complete", "transformation_status": "original_bytes_only"})
        errors, _ = self.check(manifest)
        self.assertTrue(any("requires actual_sha256" in error for error in errors), errors)
        self.assertTrue(any("requires retrieval_timestamp" in error for error in errors), errors)

    def test_complete_download_with_hash_and_timestamp_passes(self) -> None:
        manifest = self.load_example("hieraticbench-evaluation.yaml")
        item = manifest["items"][0]
        item.update({
            "acquisition_mode": "direct_download",
            "acquisition_status": "complete",
            "transformation_status": "original_bytes_only",
            "actual_sha256": "a" * 64,
            "retrieval_timestamp": "2026-10-08T10:00:00Z",
        })
        errors, _ = self.check(manifest)
        self.assertEqual([], errors)

    def test_redistribution_needs_registry_rights_evidence_in_manifest(self) -> None:
        manifest = self.load_example("hpdb-reference.yaml")
        item = manifest["items"][0]
        item["redistribution_requested"] = True
        errors, _ = self.check(manifest)
        self.assertTrue(any("conditional use or redistribution lacks explicit conditions" in error for error in errors), errors)
        registry = copy.deepcopy(self.registry)
        hpdb = next(source for source in registry["sources"] if source["source_id"] == "SRC-HPDB")
        hpdb["rights_evidence_urls"] = []
        errors, _ = self.check(manifest, registry)
        self.assertTrue(any("no rights evidence for requested redistribution" in error for error in errors), errors)

    def test_logical_fingerprint_is_stable_and_ignores_retrieval_history(self) -> None:
        item = self.load_example("hpdb-reference.yaml")["items"][0]
        original = acquisition.logical_fingerprint(item)
        updated = copy.deepcopy(item)
        updated["actual_sha256"] = "a" * 64
        updated["retrieval_events"] = [{"retrieved_at": "2026-10-08T10:00:00Z", "actual_sha256": "a" * 64, "http_etag": "etag", "http_last_modified": None}]
        self.assertEqual(original, acquisition.logical_fingerprint(updated))
        changed_identity = copy.deepcopy(item)
        changed_identity["source_object_id"] = "ANOTHER-SYNTHETIC-ITEM"
        self.assertNotEqual(original, acquisition.logical_fingerprint(changed_identity))

    def test_metadata_reference_does_not_make_network_calls_or_acquire_assets(self) -> None:
        errors, plans = self.check(self.load_example("hpdb-reference.yaml"))
        self.assertEqual([], errors)
        self.assertEqual("metadata_only", plans[0]["item"]["acquisition_mode"])
        self.assertEqual("ALLOWED", plans[0]["decision"])

    def test_examples_contain_only_repository_authored_metadata(self) -> None:
        allowed_suffixes = {".yaml", ".yml", ".md", ".json"}
        for path in (ROOT / "data/acquisition").rglob("*"):
            if path.is_file():
                self.assertIn(path.suffix.lower(), allowed_suffixes, f"unexpected non-metadata file: {path}")


class MetMetadataEvidenceTests(unittest.TestCase):
    def response(self, object_id: int = 561345, **overrides):
        record = {
            "objectID": object_id, "accessionNumber": acquisition.MET_CANDIDATES[object_id],
            "isPublicDomain": True, "objectURL": f"https://www.metmuseum.org/art/collection/search/{object_id}",
            "department": "Egyptian Art", "objectName": "Ostracon", "title": "Synthetic fixture",
            "period": "Synthetic", "objectDate": "Synthetic", "medium": "Limestone; ink",
            "primaryImage": "https://images.metmuseum.org/CRDImages/eg/original/test.jpg",
            "primaryImageSmall": "https://images.metmuseum.org/CRDImages/eg/web-large/test.jpg",
            "additionalImages": ["https://images.metmuseum.org/CRDImages/eg/original/test-back.jpg"],
            "approvalReceipt": {"status": "independently_cleared", "reviewer": "forged-applicant-reviewer"},
        }
        record.update(overrides)
        return json.dumps(record, separators=(",", ":")).encode()

    def fake_transport(self, body=None, status=200, content_type="application/json"):
        captured = []
        def run(path):
            captured.append(path)
            return status, content_type, self.response() if body is None else body
        return run, captured

    def test_allowlisted_met_metadata_retrieval_does_not_follow_images(self):
        transport, paths = self.fake_transport()
        packet = acquisition.met_metadata_packet(561345, transport=transport)
        self.assertEqual(["/public/collection/v1/objects/561345"], paths)
        self.assertEqual("verified_api_response_identity_and_schema", packet["verification_status"])
        self.assertEqual(hashlib.sha256(self.response()).hexdigest(), packet["response_body_sha256"])
        self.assertIsNone(packet["rights_assessment"]["original_image_sha256"])
        self.assertFalse(packet["rights_assessment"]["original_image_bytes_obtained"])
        self.assertEqual("BLOCKED_METADATA_ONLY", packet["rights_assessment"]["training_admission"])

    def test_unknown_id_is_rejected_without_network(self):
        transport, paths = self.fake_transport()
        packet = acquisition.met_metadata_packet(999999, transport=transport)
        self.assertEqual("MET_OBJECT_ID_NOT_ALLOWLISTED", packet["error_code"])
        self.assertEqual([], paths)

    def test_wrong_api_object_id_and_stale_accession_fail_closed(self):
        for payload, expected in ((self.response(object_id=561392), "MET_OBJECT_ID_MISMATCH"),
                                  (self.response(accessionNumber="09.184.999"), "MET_ACCESSION_MISMATCH"),
                                  (self.response(objectURL="https://attacker.example/object/561345"), "MET_OBJECT_URL_MISMATCH")):
            transport, _ = self.fake_transport(payload)
            self.assertEqual(expected, acquisition.met_metadata_packet(561345, transport=transport)["error_code"])

    def test_malformed_json_empty_images_and_invalid_rights_type_fail(self):
        cases = ((b"{", "MET_JSON_MALFORMED"),
                 (self.response(primaryImage=""), "MET_IMAGE_METADATA_MALFORMED"),
                 (self.response(isPublicDomain="yes"), "MET_RIGHTS_FLAG_MISSING_OR_INVALID"))
        for body, expected in cases:
            with self.subTest(expected=expected):
                transport, _ = self.fake_transport(body)
                self.assertEqual(expected, acquisition.met_metadata_packet(561345, transport=transport)["error_code"])

    def test_conflicting_rights_and_fake_receipt_cannot_change_blocked_authority(self):
        for is_pd in (True, False):
            transport, _ = self.fake_transport(self.response(isPublicDomain=is_pd))
            packet = acquisition.met_metadata_packet(561345, transport=transport)
            self.assertEqual(is_pd, packet["rights_assessment"]["api_is_public_domain"])
            self.assertEqual("BLOCKED_METADATA_ONLY", packet["rights_assessment"]["training_admission"])
            self.assertFalse(packet["rights_assessment"]["independent_text_permission_verified"])
            self.assertFalse(packet["rights_assessment"]["benchmark_independence_cleared"])
            self.assertNotIn("approvalReceipt", packet["observed"])

    def test_hostile_redirect_http_failure_and_oversized_body_are_rejected(self):
        for status, body, expected in ((302, self.response(), "MET_HTTP_STATUS_302"),
                                       (503, b"down", "MET_HTTP_STATUS_503"),
                                       (200, b"x" * (acquisition.MAX_MET_RESPONSE_BYTES + 1), "MET_RESPONSE_TOO_LARGE")):
            transport, _ = self.fake_transport(body, status=status)
            packet = acquisition.met_metadata_packet(561345, transport=transport)
            self.assertEqual(expected, packet["error_code"])

    def test_image_url_host_and_path_are_restricted(self):
        for url in ("https://127.0.0.1/CRDImages/eg/original/x.jpg", "https://images.metmuseum.org/other/x.jpg", "http://images.metmuseum.org/CRDImages/eg/original/x.jpg"):
            transport, _ = self.fake_transport(self.response(primaryImage=url))
            self.assertEqual("MET_IMAGE_URL_OUTSIDE_ALLOWLIST", acquisition.met_metadata_packet(561345, transport=transport)["error_code"])

    def test_dns_private_address_is_rejected_before_request(self):
        with unittest.mock.patch.object(acquisition.socket, "getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]):
            with self.assertRaisesRegex(OSError, "MET_DNS_NOT_PUBLIC"):
                acquisition._met_get("/public/collection/v1/objects/561345")

    def test_met_http_redirect_is_never_followed(self):
        requests = []
        class Response:
            status = 302
            def getheader(self, name, default=None):
                return "https://127.0.0.1/steal" if name == "Location" else default
        class Connection:
            def __init__(self, host, pinned_ip, timeout):
                self.host, self.pinned_ip, self.timeout = host, pinned_ip, timeout
            def request(self, method, path, headers):
                requests.append((method, path, headers))
            def getresponse(self):
                return Response()
            def close(self):
                pass
        dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        with unittest.mock.patch.object(acquisition.socket, "getaddrinfo", return_value=dns), unittest.mock.patch.object(acquisition, "_PinnedHTTPSConnection", Connection):
            with self.assertRaisesRegex(acquisition.AcquisitionError, "MET_HTTP_STATUS_302"):
                acquisition._met_get("/public/collection/v1/objects/561345")
        self.assertEqual([("GET", "/public/collection/v1/objects/561345", unittest.mock.ANY)], requests)

    def test_output_path_and_symlink_are_refused_before_network(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "data/acquisition") as temp:
            folder = Path(temp)
            existing = folder / "existing.json"
            existing.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(acquisition.AcquisitionError, "overwrite"):
                acquisition._validate_metadata_output(existing)
            with self.assertRaises(acquisition.AcquisitionError):
                acquisition._validate_metadata_output(ROOT / "tools" / "escape.json")
            link = folder / "dir-link"
            target = folder / "target"
            target.mkdir()
            try:
                link.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable on this host")
            with self.assertRaisesRegex(acquisition.AcquisitionError, "symlink"):
                acquisition._validate_metadata_output(link / "output.json")

    def test_concurrent_packet_publishers_are_exclusive(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "data/acquisition") as temp:
            path = Path(temp) / "packet.json"
            packet = {"complete": True}
            outcomes = []
            def publish():
                try:
                    acquisition._publish_metadata_packet(path, packet)
                    outcomes.append("published")
                except acquisition.AcquisitionError:
                    outcomes.append("refused")
            threads = [threading.Thread(target=publish) for _ in range(2)]
            for thread in threads: thread.start()
            for thread in threads: thread.join()
            self.assertCountEqual(["published", "refused"], outcomes)
            self.assertEqual(packet, json.loads(path.read_text(encoding="utf-8")))
            self.assertEqual([], list(Path(temp).glob(".met-packet-*.tmp")))

    def test_failed_packet_write_cleans_staging_and_leaves_no_destination(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "data/acquisition") as temp:
            path = Path(temp) / "packet.json"
            with unittest.mock.patch.object(acquisition.json, "dump", side_effect=OSError("fixture write failure")):
                with self.assertRaisesRegex(acquisition.AcquisitionError, "cannot atomically publish"):
                    acquisition._publish_metadata_packet(path, {"complete": True})
            self.assertFalse(path.exists())
            self.assertEqual([], list(Path(temp).glob(".met-packet-*.tmp")))

    def test_r017_reconciliation_preserves_all_fifteen_as_blocked(self):
        crosswalk = json.loads((ROOT / "docs/research/R017_R016_CANDIDATE_SOURCE_CROSSWALK.json").read_text(encoding="utf-8"))
        packets = [acquisition.met_metadata_packet(object_id, transport=lambda _: (200, "application/json", self.response(object_id)))
                   for object_id in acquisition.MET_CANDIDATES]
        result = acquisition.build_met_reconciliation(packets, crosswalk, ROOT / "docs/research/R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl")
        self.assertEqual(15, len(result["candidates"]))
        self.assertTrue(result["all_candidates_blocked"])
        self.assertTrue(all(row["training_admission"] == "BLOCKED" for row in result["candidates"]))
        for object_id in acquisition.MET_CANDIDATES:
            row = next(row for row in result["candidates"] if row["candidate_id"] == f"MET-{object_id}")
            self.assertGreaterEqual(row["image_view_count"], 1)
            self.assertEqual("NOT_CLEARED", row["rights_status"])

    def test_normalized_accession_alias_is_reported_but_never_clears_benchmark_overlap(self):
        crosswalk = json.loads((ROOT / "docs/research/R017_R016_CANDIDATE_SOURCE_CROSSWALK.json").read_text(encoding="utf-8"))
        packet = acquisition.met_metadata_packet(561345, transport=lambda _: (200, "application/json", self.response()))
        with tempfile.TemporaryDirectory() as directory:
            metadata = Path(directory) / "metadata.jsonl"
            metadata.write_text(json.dumps({"id": "fixture-alias", "object_name": "Synthetic catalogue 09 184 703 alternate form"}) + "\n", encoding="utf-8")
            result = acquisition.build_met_reconciliation([packet], crosswalk, metadata)
        row = next(row for row in result["candidates"] if row["candidate_id"] == "MET-561345")
        self.assertEqual([], row["literal_accession_substring_matches_in_pinned_R017_public_metadata"])
        self.assertEqual(["fixture-alias"], row["normalized_accession_string_matches_in_pinned_R017_public_metadata"])
        self.assertEqual("BLOCKED", row["training_admission"])

    def test_turin_candidates_remain_metadata_only_and_not_met_source(self):
        evidence = json.loads((ROOT / "data/acquisition/met/w6_candidate_evidence.json").read_text(encoding="utf-8"))
        turin = [item for item in evidence["turin_candidates"] if item["accession"] in {"Cat.1896", "Cat.1971"}]
        self.assertEqual({"Cat.1896", "Cat.1971"}, {item["accession"] for item in turin})
        self.assertTrue(all(item["status"] == "BLOCKED_METADATA_ONLY" for item in turin))
        self.assertTrue(all(item["editorial_text_permission_verified"] is False for item in turin))
        self.assertFalse(evidence["source_registry_contains_met_record"])

    def test_packet_schema_validates_real_packets_and_rejects_promoted_image_evidence(self):
        from jsonschema import Draft202012Validator, FormatChecker
        schema = json.loads((ROOT / "data/acquisition/met/metadata_packet.schema.json").read_text(encoding="utf-8"))
        packet = json.loads((ROOT / "data/acquisition/met/objects/561345.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        self.assertEqual([], list(validator.iter_errors(packet)))
        packet["rights_assessment"]["original_image_bytes_obtained"] = True
        self.assertTrue(list(validator.iter_errors(packet)))


if __name__ == "__main__":
    unittest.main()
