from __future__ import annotations

import copy
import base64
import hashlib
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
from data.releases import w20_aku_pal_source_audit as akupal_w20
from data.releases import w20_museum_photo_intake as museum_w20
from data.releases import w20_build_receipt_manifest as w20_manifest
from data.releases import w28_candidate_readiness as w28_readiness

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


def minimal_admission_evidence() -> dict:
    """Schema-valid synthetic evidence envelope with deliberately untrusted claims."""
    source_id, object_id, item_id = "SRC-HPDB", "SYNTHETIC-OBJECT-UNTRUSTED", "synthetic-admission-test"
    nodes = [{"node_id": f"node-{index}", "node_type": "institution", "source_registry_id": source_id,
              "source_object_id": object_id, "asset_id": f"asset-{index}", "sha256": None,
              "creator_id": "synthetic-fixture", "created_at": "2026-10-08T00:00:00Z",
              "review_status": "synthetic", "attributes": {}} for index in range(2)]
    evidence = {
        "schema_version": "1.1.0", "evidence_id": "synthetic-evidence",
        "contributor_assertions": [{"assertion_id": "assertion-1", "claimant_id": "contributor-1",
                                     "claimed_at": "2026-10-08T00:00:00Z", "subject_id": object_id,
                                     "claim": "synthetic-only claim", "evidence_refs": []}],
        "submitted_evidence": [], "license_terms": [], "independent_reviews": [], "bound_assets": [],
        "benchmark_overlap": {"state": "not_yet_reviewed", "reviewer_id": None, "reviewed_at": None,
                              "evidence_refs": [], "roster_version": "synthetic-roster-v1",
                              "methods": [], "scope": {"object_ids": [], "accessions": [], "sides": [], "fragments": [],
                                                          "edition_ids": [], "scribe_groups": [], "original_hashes": [],
                                                          "derived_hashes": [], "perceptual_hashes": []}},
        "decision": {"status": "allowed", "source_registry_id": source_id, "source_object_id": object_id,
                     "intended_uses": ["training"], "reviewer_id": "untrusted-reviewer",
                     "reviewed_at": "2026-10-08T00:00:00Z", "rationale": "synthetic test only",
                     "limitations": [], "expires_at": None, "supersedes_receipt_id": None,
                     "institutional_accession": "SYNTH-ACC", "manuscript_group_id": "SYNTH-MS",
                     "fragment_ids": ["SYNTH-FRAG"], "side_ids": ["recto"], "scribe_group": None,
                     "source_registry_record_sha256": "1" * 64},
        "review_history": [],
        "provenance_graph": {"schema_version": "1.0.0", "graph_id": "synthetic-graph", "item_id": item_id,
                             "nodes": nodes, "edges": []},
        "receipt": {"receipt_id": "untrusted-receipt", "key_id": "not-configured", "signed_by": "untrusted-reviewer",
                    "signed_at": "2026-10-08T00:00:00Z", "payload_sha256": "0" * 64,
                    "signature_ed25519_base64": "AA=="},
    }
    payload = {key: copy.deepcopy(value) for key, value in evidence.items() if key != "receipt"}
    evidence["receipt"]["payload_sha256"] = release_corpus.digest(release_corpus.canonical(payload))
    return evidence


def _attacker_ed25519_keypair(seed: bytes) -> tuple[bytes, object]:
    """Tiny deterministic test signer; deliberately not a production dependency."""
    q = 2**255 - 19
    order = 2**252 + 27742317777372353535851937790883648493
    d = (-121665 * pow(121666, q - 2, q)) % q
    i = pow(2, (q - 1) // 4, q)

    def point_add(p, r):
        x1, y1 = p
        x2, y2 = r
        product = d * x1 * x2 * y1 * y2 % q
        x = (x1 * y2 + y1 * x2) * pow(1 + product, q - 2, q) % q
        y = (y1 * y2 + x1 * x2) * pow(1 - product, q - 2, q) % q
        return x, y

    def scalar_mult(scalar, point):
        result = (0, 1)
        while scalar:
            if scalar & 1:
                result = point_add(result, point)
            point = point_add(point, point)
            scalar >>= 1
        return result

    def encode(point):
        x, y = point
        return int(y | ((x & 1) << 255)).to_bytes(32, "little")

    base_y = 4 * pow(5, q - 2, q) % q
    x2 = (base_y * base_y - 1) * pow(d * base_y * base_y + 1, q - 2, q) % q
    base_x = pow(x2, (q + 3) // 8, q)
    if base_x * base_x % q != x2:
        base_x = base_x * i % q
    if base_x & 1:
        base_x = q - base_x
    base = (base_x, base_y)

    hashed = hashlib.sha512(seed).digest()
    secret = bytearray(hashed[:32])
    secret[0] &= 248
    secret[31] &= 63
    secret[31] |= 64
    scalar = int.from_bytes(secret, "little")
    public_key = encode(scalar_mult(scalar, base))
    prefix = hashed[32:]

    def sign(message: bytes) -> bytes:
        nonce = int.from_bytes(hashlib.sha512(prefix + message).digest(), "little") % order
        encoded_r = encode(scalar_mult(nonce, base))
        challenge = int.from_bytes(hashlib.sha512(encoded_r + public_key + message).digest(), "little") % order
        s = (nonce + challenge * scalar) % order
        return encoded_r + s.to_bytes(32, "little")

    return public_key, sign


class CorpusReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def bundle(self, name="case"):
        return make_bundle(self.root / name)

    def test_ed25519_receipt_verifier_accepts_rfc8032_vector_and_rejects_mutation(self):
        # RFC 8032 test vector 2: public test material, not an authority key.
        public_key = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
        signature = bytes.fromhex("92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
                                 "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00")
        message = bytes.fromhex("72")
        self.assertTrue(release_corpus._verify_ed25519(public_key, signature, message))
        self.assertFalse(release_corpus._verify_ed25519(public_key, signature, b"changed"))
        self.assertFalse(release_corpus._verify_ed25519(public_key, signature[:-1], message))

    def test_empty_trust_store_is_valid_but_cannot_claim_unconfigured_authorities(self):
        trust_store = release_corpus.read_document(release_corpus.TRUST_ANCHORS)
        self.assertEqual("no_external_authorities_configured", trust_store["status"])
        self.assertEqual([], trust_store["anchors"])
        self.assertEqual([], release_corpus.validate_trust_store(trust_store))
        forged = copy.deepcopy(trust_store)
        forged["anchors"].append({"key_id": "unverified-self-added-key"})
        self.assertTrue(release_corpus.validate_trust_store(forged))

    def test_untrusted_synthetic_receipt_cannot_bypass_source_registry_or_rights_gates(self):
        evidence = minimal_admission_evidence()
        trust_store = release_corpus.read_document(release_corpus.TRUST_ANCHORS)
        errors = release_corpus.validate_admission_evidence(
            evidence, trust_store, source_id="SRC-HPDB", source_object_id="SYNTHETIC-OBJECT-UNTRUSTED",
            item_id="synthetic-admission-test", expected_assets={"original_image": ("image-1", "a" * 64)},
            expected_roster_version="pinned-roster-v2", expected_source_record_sha256="2" * 64,
            as_of=release_corpus.dt.datetime(2026, 10, 8, tzinfo=release_corpus.dt.timezone.utc))
        self.assertTrue(any("source-registry rights record changed" in error for error in errors), errors)
        self.assertTrue(any("not an external trust root" in error for error in errors), errors)
        self.assertTrue(any("benchmark overlap state is not_yet_reviewed" in error for error in errors), errors)
        self.assertTrue(any("missing rights term for original_image/development" in error for error in errors), errors)

    def test_attacker_generated_root_and_fabricated_roles_never_authorize_production(self):
        evidence = minimal_admission_evidence()
        evidence["submitted_evidence"] = [{
            "evidence_id": "permission-1", "kind": "permission_letter",
            "uri": "https://attacker.invalid/private/letter.pdf", "sha256": "a" * 64,
            "verification_status": "reference_only_unverified", "verified_content_sha256": None,
            "verification_receipt_ref": None, "substantive_rights_determination": "not_assessed",
            "submitted_by": "attacker", "submitted_at": "2026-10-08T00:00:00Z", "component": "all",
        }]
        evidence["independent_reviews"] = [
            {"review_id": "fake-rights", "reviewer_id": "invented-rights-officer", "reviewer_role": "rights_holder_representative",
             "reviewed_at": "2026-10-08T00:00:00Z", "version": "1", "subject_id": "SYNTHETIC-OBJECT-UNTRUSTED",
             "intended_use": ["training", "development", "redistribution"], "evidence_refs": ["permission-1"],
             "decision": "allowed", "rationale": "forged role assertion", "limitations": [], "supersedes_review_id": None},
            {"review_id": "fake-scholar", "reviewer_id": "invented-egyptologist", "reviewer_role": "egyptologist",
             "reviewed_at": "2026-10-08T00:00:00Z", "version": "1", "subject_id": "SYNTHETIC-OBJECT-UNTRUSTED",
             "intended_use": ["training"], "evidence_refs": ["permission-1"], "decision": "allowed",
             "rationale": "forged scholarly approval", "limitations": [], "supersedes_review_id": None},
            {"review_id": "fake-benchmark", "reviewer_id": "invented-auditor", "reviewer_role": "benchmark_auditor",
             "reviewed_at": "2026-10-08T00:00:00Z", "version": "1", "subject_id": "SYNTHETIC-OBJECT-UNTRUSTED",
             "intended_use": ["training"], "evidence_refs": ["permission-1"], "decision": "allowed",
             "rationale": "forged overlap approval", "limitations": [], "supersedes_review_id": None},
        ]
        seed = hashlib.sha256(b"attacker-controlled signing seed").digest()
        public_key, sign = _attacker_ed25519_keypair(seed)
        payload = {key: copy.deepcopy(value) for key, value in evidence.items() if key != "receipt"}
        payload_bytes = release_corpus.canonical(payload)
        evidence["receipt"].update({
            "receipt_id": "attacker-self-signed-1", "key_id": "attacker-root",
            "signed_by": "attacker", "signed_at": "2026-10-08T00:00:00Z",
            "payload_sha256": release_corpus.digest(payload_bytes),
            "signature_ed25519_base64": base64.b64encode(sign(payload_bytes)).decode("ascii"),
        })
        trust_store = {
            "schema_version": "1.0.0", "status": "externally_verified_authorities_configured",
            "anchors": [{"key_id": "attacker-root", "public_key_ed25519_base64": base64.b64encode(public_key).decode("ascii"),
                         "reviewer_id": "attacker", "authority_role": "corpus_overseer", "source_ids": ["SRC-HPDB"],
                         "valid_from": "2026-01-01T00:00:00Z", "valid_until": "2027-01-01T00:00:00Z",
                         "verification_record": "self-authored fake institutional approval"}],
            "revoked_receipt_ids": [], "superseded_receipt_ids": [],
        }
        self.assertEqual([], release_corpus.validate_trust_store(trust_store), "attacker record is syntactically valid")
        self.assertTrue(release_corpus._verify_ed25519(public_key, base64.b64decode(evidence["receipt"]["signature_ed25519_base64"]), payload_bytes))
        errors = release_corpus.validate_admission_evidence(
            evidence, trust_store, source_id="SRC-HPDB", source_object_id="SYNTHETIC-OBJECT-UNTRUSTED",
            item_id="synthetic-admission-test", expected_assets={}, as_of=release_corpus.dt.datetime(2026, 10, 8, tzinfo=release_corpus.dt.timezone.utc))
        self.assertIn(release_corpus.PRODUCTION_AUTHORIZATION_BLOCKER, errors)
        self.assertIn(release_corpus.PRODUCTION_AUTHORIZATION_BLOCKER, release_corpus.production_authority_gate(trust_store, evidence))
        self.assertEqual("reference_only_unverified", evidence["submitted_evidence"][0]["verification_status"])

        # Changing claimed authority metadata cannot change the independent gate.
        altered = copy.deepcopy(trust_store)
        altered["anchors"][0]["verification_record"] = "different forged proof"
        altered["anchors"][0]["authority_role"] = "legal_reviewer"
        altered["status"] = "synthetic_test_fixture"
        self.assertIn(release_corpus.PRODUCTION_AUTHORIZATION_BLOCKER, release_corpus.production_authority_gate(altered, evidence))

    def test_invalid_document_claim_cannot_be_labeled_verified(self):
        evidence = minimal_admission_evidence()
        schema = release_corpus.read_document(release_corpus.ADMISSION_SCHEMA)
        evidence["submitted_evidence"] = [{
            "evidence_id": "claimed-verified", "kind": "permission_letter", "uri": "https://example.invalid/letter",
            "sha256": "a" * 64, "verification_status": "verified", "verified_content_sha256": "a" * 64,
            "verification_receipt_ref": "signed-by-self", "substantive_rights_determination": "permission_confirmed",
            "submitted_by": "attacker", "submitted_at": "2026-10-08T00:00:00Z", "component": "all",
        }]
        errors = release_corpus._schema_errors_against(evidence, schema, "authorization evidence")
        self.assertTrue(any("verification_status" in error for error in errors), errors)

    def test_reviewer_disagreement_is_preserved_as_unresolved_without_exposing_reviewer_evidence(self):
        evidence = minimal_admission_evidence()
        evidence["independent_reviews"] = [
            {"review_id": "review-allow", "reviewer_id": "person-a", "reviewer_role": "egyptologist",
             "reviewed_at": "2026-10-08T00:00:00Z", "version": "1", "subject_id": "SYNTHETIC-OBJECT-UNTRUSTED",
             "intended_use": ["training"], "evidence_refs": [], "decision": "allowed", "rationale": "private yes",
             "limitations": [], "supersedes_review_id": None},
            {"review_id": "review-deny", "reviewer_id": "person-b", "reviewer_role": "egyptologist",
             "reviewed_at": "2026-10-08T00:00:00Z", "version": "1", "subject_id": "SYNTHETIC-OBJECT-UNTRUSTED",
             "intended_use": ["training"], "evidence_refs": [], "decision": "denied", "rationale": "private no",
             "limitations": [], "supersedes_review_id": None},
        ]
        errors = release_corpus.validate_admission_evidence(
            evidence, release_corpus.read_document(release_corpus.TRUST_ANCHORS), source_id="SRC-HPDB",
            source_object_id="SYNTHETIC-OBJECT-UNTRUSTED", item_id="synthetic-admission-test", expected_assets={},
            as_of=release_corpus.dt.datetime(2026, 10, 8, tzinfo=release_corpus.dt.timezone.utc))
        self.assertIn(release_corpus.PRODUCTION_AUTHORIZATION_BLOCKER, errors)
        public_case = release_corpus._public_review_case({
            "case_id": "dispute-1", "target_type": "line", "target_id": "line-1", "annotation_layer": "reading",
            "annotation_gold_status": "uncertain_with_alternatives", "issue_flags": ["disputed_reading"],
            "case_state": "needs_adjudication", "decisions": [
                {"reviewer_id": "person-a", "rationale": "private yes"}, {"reviewer_id": "person-b", "rationale": "private no"}],
            "adjudication": None,
        })
        self.assertTrue(public_case["disagreement"])
        self.assertEqual(2, public_case["decision_count"])
        rendered = json.dumps(public_case)
        self.assertNotIn("person-a", rendered)
        self.assertNotIn("private yes", rendered)

    def test_revoked_receipt_is_rejected_even_as_untrusted_claim(self):
        evidence = minimal_admission_evidence()
        trust_store = release_corpus.read_document(release_corpus.TRUST_ANCHORS)
        trust_store["revoked_receipt_ids"] = ["untrusted-receipt"]
        errors = release_corpus.validate_admission_evidence(
            evidence, trust_store, source_id="SRC-HPDB", source_object_id="SYNTHETIC-OBJECT-UNTRUSTED",
            item_id="synthetic-admission-test", expected_assets={}, as_of=release_corpus.dt.datetime(2026, 10, 8, tzinfo=release_corpus.dt.timezone.utc))
        self.assertTrue(any("has been revoked" in error for error in errors), errors)
        self.assertIn(release_corpus.PRODUCTION_AUTHORIZATION_BLOCKER, errors)

    def test_receipt_binding_and_source_object_inheritance_fail_closed(self):
        evidence = minimal_admission_evidence()
        trust_store = release_corpus.read_document(release_corpus.TRUST_ANCHORS)
        evidence["decision"]["source_object_id"] = "SYNTHETIC-OBJECT-OTHER"
        errors = release_corpus.validate_admission_evidence(
            evidence, trust_store, source_id="SRC-HPDB", source_object_id="SYNTHETIC-OBJECT-UNTRUSTED",
            item_id="synthetic-admission-test", expected_assets={},
            as_of=release_corpus.dt.datetime(2026, 10, 8, tzinfo=release_corpus.dt.timezone.utc))
        self.assertTrue(any("not bound to the admitted source and object" in error for error in errors), errors)
        self.assertTrue(any("payload hash does not match" in error for error in errors), errors)
        self.assertIn(release_corpus.PRODUCTION_AUTHORIZATION_BLOCKER, errors)

    def test_synthetic_build_succeeds_but_production_promotion_is_hard_blocked(self):
        path = self.bundle()
        result, errors = release_corpus.validate_bundle(_yaml(path), path)
        self.assertEqual([], errors)
        self.assertEqual("synthetic_test_release", result["release"]["release_kind"])
        bundle = _yaml(path)
        bundle["release_kind"] = "corpus_v1_release"
        _, production_errors = release_corpus.validate_bundle(bundle, path)
        self.assertTrue(any(release_corpus.PRODUCTION_AUTHORIZATION_BLOCKER in error for error in production_errors), production_errors)
        forged_result = copy.deepcopy(result)
        forged_result["release"]["release_kind"] = "corpus_v1_release"
        forged_result["errors"] = []
        with self.assertRaisesRegex(release_corpus.ReleaseError, "production authorization is hard-disabled"):
            release_corpus._release_files(forged_result, path)
        with self.assertRaisesRegex(release_corpus.ReleaseError, "production authorization is hard-disabled"):
            release_corpus.publish(forged_result, self.root / "forged-production", path)
        self.assertFalse((self.root / "forged-production").exists())

    def test_private_authorization_and_reviewer_evidence_are_not_published(self):
        path = self.bundle()
        base = path.parent
        private_evidence = minimal_admission_evidence()
        private_evidence["receipt"]["signature_ed25519_base64"] = "PRIVATE_SIGNATURE_CANARY"
        private_evidence["submitted_evidence"] = [{
            "evidence_id": "private-evidence", "kind": "permission_letter", "uri": "file:///private/permission-letter.pdf",
            "sha256": "b" * 64, "verification_status": "reference_only_unverified", "verified_content_sha256": None,
            "verification_receipt_ref": None, "substantive_rights_determination": "not_assessed",
            "submitted_by": "PRIVATE_REVIEWER_CANARY", "submitted_at": "2026-10-08T00:00:00Z", "component": "all",
        }]
        private_path = base / "private-authorization.json"
        private_path.write_text(json.dumps(private_evidence), encoding="utf-8")
        bundle = _yaml(path)
        bundle["items"][0]["authorization_evidence_path"] = private_path.name
        path.write_text(yaml.safe_dump(bundle, sort_keys=False), encoding="utf-8")
        result, errors = release_corpus.validate_bundle(bundle, path)
        self.assertEqual([], errors)
        public_bytes = b"\n".join(release_corpus._release_files(result, path).values())
        for secret in (b"PRIVATE_SIGNATURE_CANARY", b"PRIVATE_REVIEWER_CANARY", b"file:///private/permission-letter.pdf", private_path.name.encode()):
            self.assertNotIn(secret, public_bytes)
        item = result["release"]["items"][0]
        self.assertEqual("unverified_claims_not_production_authorization", item["authorization_evidence_summary"]["status"])
        self.assertNotIn("reviewer-a", json.dumps(item["review_cases"]))

    def test_provenance_graph_rejects_cycles_missing_fragment_and_hash_drift(self):
        schema = release_corpus.read_document(release_corpus.ADMISSION_SCHEMA)
        source_id, object_id, item_id = "SRC-HPDB", "SYNTHETIC-OBJECT", "synthetic-item"
        kinds = release_corpus.REQUIRED_PROVENANCE_TYPES
        nodes = []
        for index, kind in enumerate(kinds):
            attrs = {}
            if kind == "object":
                attrs = {"institutional_accession": "SYNTH-1", "manuscript_group_id": "MS-1"}
            elif kind == "manuscript":
                attrs = {"manuscript_group_id": "MS-1"}
            elif kind == "fragment":
                attrs = {"fragment_id": "F-1"}
            elif kind == "side":
                attrs = {"side_id": "recto"}
            nodes.append({"node_id": f"n{index}", "node_type": kind, "source_registry_id": source_id,
                          "source_object_id": object_id, "asset_id": f"asset-{kind}", "sha256": None,
                          "creator_id": "synthetic-fixture", "created_at": "2026-10-08T00:00:00Z",
                          "review_status": "synthetic", "attributes": attrs})
        edges = [{"from_node_id": f"n{i}", "to_node_id": f"n{i+1}", "relation": "derived_from",
                  "transformation_id": f"synthetic-transform-{i}", "evidence_refs": []} for i in range(len(nodes) - 1)]
        graph = {"schema_version": "1.0.0", "graph_id": "synthetic-graph", "item_id": item_id,
                 "nodes": nodes, "edges": edges}
        identity = {"institutional_accession": "SYNTH-1", "manuscript_group_id": "MS-1",
                    "fragment_ids": ["F-1"], "side_ids": ["recto"]}
        self.assertEqual([], release_corpus.validate_provenance_graph(
            graph, schema, item_id=item_id, source_id=source_id, source_object_id=object_id,
            expected_hashes={}, object_identity=identity))
        cyclic = copy.deepcopy(graph)
        cyclic["edges"].append({"from_node_id": f"n{len(nodes)-1}", "to_node_id": "n0",
                                "relation": "derived_from", "transformation_id": None, "evidence_refs": []})
        errors = release_corpus.validate_provenance_graph(
            cyclic, schema, item_id=item_id, source_id=source_id, source_object_id=object_id,
            expected_hashes={}, object_identity=identity)
        self.assertTrue(any("cycle" in error for error in errors), errors)
        missing_fragment = copy.deepcopy(graph)
        missing_fragment["nodes"] = [node for node in nodes if node["node_type"] != "fragment"]
        missing_fragment["edges"] = [{**edge} for edge in edges if edge["from_node_id"] != "n4" and edge["to_node_id"] != "n4"]
        errors = release_corpus.validate_provenance_graph(
            missing_fragment, schema, item_id=item_id, source_id=source_id, source_object_id=object_id,
            expected_hashes={}, object_identity=identity)
        self.assertTrue(any("fragment" in error for error in errors), errors)
        drift = copy.deepcopy(graph)
        drift["nodes"][7]["sha256"] = "0" * 64
        errors = release_corpus.validate_provenance_graph(
            drift, schema, item_id=item_id, source_id=source_id, source_object_id=object_id,
            expected_hashes={"original_image": "1" * 64}, object_identity=identity)
        self.assertTrue(any("hash" in error for error in errors), errors)

    def test_readiness_assessment_is_deterministic_and_keeps_all_candidates_blocked(self):
        path = self.bundle()
        assessment1, report1 = release_corpus.build_readiness_assessment(path)
        assessment2, report2 = release_corpus.build_readiness_assessment(path)
        self.assertEqual(assessment1, assessment2)
        self.assertEqual(report1, report2)
        self.assertEqual(15, len(assessment1["benchmark_candidates"]))
        self.assertEqual(0, assessment1["cohort"]["real_items"])
        self.assertEqual(1, assessment1["cohort"]["synthetic_items"])
        self.assertTrue(all(item["admission_status"] == "blocked" for item in assessment1["benchmark_candidates"]))
        self.assertTrue(all(item["overlap_state"] == "potential_overlap" for item in assessment1["benchmark_candidates"]))
        self.assertTrue(all(item["exact_public_source_metadata_match_count"] == 0 for item in assessment1["benchmark_candidates"]))
        self.assertEqual({12, 18}, {item["nearby_collection_witness_count"] for item in assessment1["benchmark_candidates"]})
        self.assertIn("docs/research/R017_R016_CANDIDATE_SOURCE_CROSSWALK.json", assessment1["source_references"])
        self.assertFalse(assessment1["thresholds_invented"])
        self.assertEqual("BLOCKED", assessment1["evidence_admission"])

    def test_candidate_metadata_no_match_never_counts_as_independent_clearance(self):
        candidate = {"candidate_id": "synthetic-candidate"}
        state, reasons = release_corpus._candidate_benchmark_state(candidate, {
            "exact_public_source_metadata_matches": [], "nearby_collection_witness_count": 1,
        })
        self.assertEqual("potential_overlap", state)
        self.assertTrue(any("does not establish independence" in reason for reason in reasons))
        state, _ = release_corpus._candidate_benchmark_state(candidate, {
            "exact_public_source_metadata_matches": [{"benchmark_id": "synthetic-public-id"}],
            "nearby_collection_witness_count": 1,
        })
        self.assertEqual("confirmed_overlap", state)
        state, _ = release_corpus._candidate_benchmark_state(candidate, None)
        self.assertEqual("not_yet_reviewed", state)

    def test_synthetic_release_validation_and_build_are_deterministic(self):
        path = self.bundle()
        bundle = release_corpus.read_document(path)
        result, errors = release_corpus.validate_bundle(bundle, path)
        self.assertEqual([], errors)
        record = result["release"]["items"][0]
        self.assertTrue(record["synthetic"])
        self.assertEqual("uncertain_with_alternatives", record["target_annotations"][0]["targets"][0]["annotation"]["grapheme_sequence"]["gold_status"])
        self.assertGreater(record["review_cases"][0]["decision_count"], 0)
        self.assertNotIn("decisions", record["review_cases"][0])
        self.assertEqual("synthetic_test_release", result["release"]["release_kind"])
        output_a, output_b = self.root / "published-a", self.root / "published-b"
        release_corpus.publish(result, output_a, path)
        first = {p.name: p.read_bytes() for p in output_a.iterdir()}
        self.assertEqual([], release_corpus.audit_release(result, output_a, path))
        (output_a / "dataset-card.md").write_bytes(b"tampered")
        self.assertTrue(any("differs" in error for error in release_corpus.audit_release(result, output_a, path)))
        (output_a / "dataset-card.md").write_bytes(first["dataset-card.md"])
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

    def test_destination_stays_absent_while_artifacts_are_staged(self):
        path = self.bundle()
        result, errors = release_corpus.validate_bundle(release_corpus.read_document(path), path)
        self.assertEqual([], errors)
        target = self.root / "not-visible-until-complete"
        original = release_corpus._write_staging_file
        observed = []

        def observe_staging(staging, staging_fd, name, content):
            self.assertFalse(target.exists(), "incomplete destination became visible during staging")
            observed.append(name)
            return original(staging, staging_fd, name, content)

        with patch.object(release_corpus, "_write_staging_file", new=observe_staging):
            release_corpus.publish(result, target, path)
        self.assertEqual(5, len(observed))
        self.assertEqual({"release-manifest.json", "export.jsonl", "dataset-card.md", "rejection-report.json", "audit-trail.json"}, {p.name for p in target.iterdir()})

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

    def test_w20_aku_pal_exact_identity_and_source_asset_path_gates(self):
        self.assertTrue(akupal_w20.media_path_allowed("/img/data/ht/svg/ht_1234.svg", 1234))
        self.assertFalse(akupal_w20.media_path_allowed("/img/data/ht/svg/ht_9999.svg", 1234))
        self.assertFalse(akupal_w20.media_path_allowed("https://evil.example/img/data/ht/svg/ht_1234.svg", 1234))
        self.assertFalse(akupal_w20.media_path_allowed("/img/data/ht/svg/ht_1234.svg/../ht_9999.svg", 1234))

    def test_w20_aku_pal_missing_noncommercial_and_wrong_license_are_excluded(self):
        self.assertIsNone(akupal_w20._license(None)["license_id"])
        for value in [
            "<a href='https://creativecommons.org/licenses/by-nc/4.0/'>CC BY-NC 4.0</a>",
            "CC BY 4.0",
            "<a href='https://example.org/cc-by/4.0'>CC BY 4.0</a>",
        ]:
            with self.subTest(value=value):
                parsed = akupal_w20._license({"values": [value]})
                self.assertIsNone(parsed["license_id"])

    def test_w20_aku_pal_api_record_identity_and_content_drift_are_detected(self):
        row = {"sign_id": 1234, "text_ids": [77], "text_labels": ["synthetic"], "index_grapheme_ids": [9]}
        mismatch = json.dumps([{"id": 9999}]).encode("utf-8")
        result = akupal_w20._record_summary(mismatch, row, fetch_media=False)
        self.assertEqual("IDENTITY_MISMATCH", result["metadata_state"])
        self.assertEqual("blocked_missing_or_incompatible_item_rights_or_identity", result["rights_status"])
        self.assertNotEqual(akupal_w20.digest(b"record revision 1"), akupal_w20.digest(b"record revision 2"))

    def test_w20_aku_pal_svg_active_content_is_rejected(self):
        bad_svgs = [
            b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil.example/a.png"/></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
            b'<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]><svg/>',
        ]
        for body in bad_svgs:
            with self.subTest(body=body[:40]):
                safe, reason, _ = akupal_w20._svg_check(body)
                self.assertFalse(safe)
                self.assertTrue(reason)
        safe, reason, dimensions = akupal_w20._svg_check(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 12 8"><path d="M0 0"/></svg>')
        self.assertTrue(safe)
        self.assertIsNone(reason)
        self.assertEqual([12, 8], dimensions)

    def test_w20_photo_accession_does_not_accept_wrong_support_or_fuzzy_match(self):
        candidate = {"accession": "Cat.1880"}
        correct = {"commons_title": "File:Photo - Museo Egizio Turin C 1880 p01.jpg", "categories": []}
        wrong = {"commons_title": "File:Photo C 2169 p01.jpg", "categories": ["Category:Cat.2169"]}
        self.assertTrue(museum_w20.accession_evidence(candidate, correct)["matched"])
        self.assertFalse(museum_w20.accession_evidence(candidate, wrong)["matched"])
        self.assertFalse(museum_w20.accession_evidence({"accession": "S.6759"}, {"commons_title": "File:SA63451.tif", "categories": []})["matched"])
        category_evidence = museum_w20.accession_evidence({"accession": "S.6759"}, {"commons_title": "File:SA63451.tif", "categories": ["Category:Hieratic ostracon Museo Egizio S 6759"]})
        self.assertTrue(category_evidence["matched"])
        self.assertEqual("Category:Hieratic ostracon Museo Egizio S 6759", category_evidence["matching_accession_category"])

    def test_w20_benchmark_screen_reports_positive_and_keeps_negative_quarantined(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "docs/research").mkdir(parents=True)
            (root / "data/releases").mkdir(parents=True)
            public_rows = [{"id": f"aku-{i:04d}", "source_url": "", "source_file_url": "", "object_name": "unrelated", "source_group": "aku", "corpus_status": "QUARANTINE_EVAL_ONLY"} for i in range(266)]
            public_rows[0].update({"source_url": "https://aku-pal.uni-mainz.de/signs/1234", "object_name": "British Museum EA 100"})
            (root / "docs/research/R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl").write_text("".join(json.dumps(row) + "\n" for row in public_rows), encoding="utf-8")
            (root / "data/releases/w19_aku_pal_original_image_receipts.json").write_text(json.dumps({"items": [{"id": 5678, "physical_witness": "Petrie UC 1"}]}), encoding="utf-8")
            registry, _, receipt = akupal_w20.benchmark_registry(root)
            self.assertIn(1234, registry)
            self.assertIn(5678, registry)
            self.assertEqual(266, receipt["public_r017_row_count"])
            report = {"items": [{"sign_id": 1234}, {"sign_id": 9999}]}
            screened = akupal_w20.apply_benchmark_screen(report, root=root)
            self.assertEqual("POSITIVE_PUBLIC_METADATA_ID_OVERLAP_QUARANTINED", screened["items"][0]["benchmark_screen"]["state"])
            self.assertEqual("NO_LITERAL_MATCH_PUBLIC_METADATA_ONLY_STILL_UNKNOWN_QUARANTINED", screened["items"][1]["benchmark_screen"]["state"])
            self.assertTrue(all(item["benchmark_overlap"] == "unknown_quarantined" for item in screened["items"]))

    def test_w20_schema_rejects_training_and_gold_promotion(self):
        photo = {"schema_version": "w20-museum-photo-intake/1.0.0", "classification": "SOURCE_PHOTO_EVIDENCE_ONLY_NOT_DATA002_ADMISSION",
            "candidate_count": 7, "distinct_physical_support_groups": 3, "bytes_hashed": 0, "media_bytes_written_to_disk": False,
            "items": [], "grouping": {}}
        self.assertTrue(museum_w20.validate_schema(photo))

    def test_w20_checked_receipts_validate_and_timestamp_is_not_identity(self):
        census = json.loads((ROOT / "data/releases/w20_aku_pal_sign_census.json").read_text(encoding="utf-8"))
        photos = json.loads((ROOT / "data/releases/w20_museum_photo_intake.json").read_text(encoding="utf-8"))
        self.assertEqual([], akupal_w20.validate_report(census))
        self.assertEqual([], akupal_w20.validate_schema(census))
        self.assertEqual([], museum_w20.validate_report(photos))
        self.assertEqual([], museum_w20.validate_schema(photos))
        timestamp_mutation = copy.deepcopy(census)
        timestamp_mutation["retrieved_at_utc"] = "2099-01-01T00:00:00+00:00"
        self.assertEqual([], akupal_w20.validate_report(timestamp_mutation))
        tampered = copy.deepcopy(census)
        tampered["items"][0]["record_sha256"] = "f" * 64
        self.assertTrue(akupal_w20.validate_report(tampered))

    def test_w20_combined_item_receipt_contains_r026_crosscheck_and_never_promotes(self):
        manifest = json.loads((ROOT / "data/releases/w20_item_receipt_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual([], w20_manifest.validate_manifest(manifest))
        self.assertEqual([], w20_manifest.validate_input(manifest))
        self.assertTrue(manifest["summary"]["cat1880_p01_r026_byte_crossmatch"])
        self.assertEqual(0, manifest["summary"]["sealed_benchmark_records_read"])
        self.assertEqual(0, manifest["summary"]["training_admissions"])
        self.assertEqual(0, manifest["summary"]["gold_labels"])
        self.assertEqual(0, manifest["summary"]["raw_media_files_committed"])
        self.assertGreater(manifest["summary"]["benchmark_screen_results"]["POSITIVE_PUBLIC_METADATA_ID_OVERLAP_QUARANTINED"], 0)
        tampered = copy.deepcopy(manifest)
        tampered["items"][0]["source_identity"]["record_sha256"] = "f" * 64
        tampered["evidence_sha256"] = w20_manifest.digest({key: value for key, value in tampered.items() if key != "evidence_sha256"})
        self.assertEqual([], w20_manifest.validate_manifest(tampered))
        tampered["items"][0]["disposition"]["training_admission"] = True
        self.assertTrue(w20_manifest.validate_manifest(tampered))

    def test_w20_item_manifest_binds_inputs_and_cannot_promote_candidates(self):
        census = {"schema_version": "w20-akupal-source-census/1.0.0", "source": "AKU-PAL Academy Mainz public API",
            "classification": "RESEARCH_INVENTORY_ONLY_NOT_CORPUS_ADMISSION", "discovery": {"index_sha256": "a" * 64, "unique_indexed_sign_ids": 2, "grapheme_records": 1},
            "selection": {"selected_items": 1}, "scan_limits": {"maximum_concurrency": 1, "media_bytes_written_to_disk": False},
            "summary": {"distinct_sign_ids_screened": 1, "exact_item_permissive_license_and_provenance_screened": 1, "verified_sign_media_files": 1,
                "training_admissions": 0, "gold_labels": 0, "production_corpus": False, "benchmark_state": "UNKNOWN_QUARANTINED_ALL_RECORDS",
                "unique_media_byte_hashes": 1, "duplicate_media_hash_groups": 0, "unique_publisher_inventory_labels_lower_bound": 1},
            "items": [{"sign_id": 1234, "record_url": "https://aku-pal.uni-mainz.de/api/signs/1234", "record_sha256": "b" * 64,
                "source_text_record_id": 9, "source_inventory_label": "Synthetic witness X1", "side": "recto", "line_locator": "1", "script_type": "Hieratisch",
                "rights_status": "per_item_license_and_public_provenance_screened_not_institutionally_admitted", "license_id": "CC-BY-4.0",
                "license_url": "https://creativecommons.org/licenses/by/4.0/", "media": [{"url": "https://aku-pal.uni-mainz.de/img/data/ht/svg/ht_1234.svg",
                    "asset_role": "publisher_sign_svg", "publisher_image_type": "sign", "status": "BYTES_HASHED_IN_MEMORY", "sha256": "c" * 64,
                    "byte_size": 120, "content_type": "image/svg+xml", "dimensions": [10, 10], "safe_svg": True}],
                "training_admission": False, "gold_admission": False, "benchmark_overlap": "unknown_quarantined", "source_inventory_label": None,
                "benchmark_screen": {"state": "NO_LITERAL_MATCH_PUBLIC_METADATA_ONLY_STILL_UNKNOWN_QUARANTINED", "matches": []}}],
            "benchmark_screen": {"public_r017_sha256": "d" * 64, "w19_receipt_sha256": "e" * 64}}
        photo_item = {"accession": "Cat.1880", "group_id": "MUSEO:CAT1880", "rights_status": "FILE_PAGE_CC0",
            "text_rights": "NOT_VERIFIED_OR_NOT_ASSUMED", "benchmark_overlap": "UNKNOWN_QUARANTINED", "training_admission": False, "gold_admission": False,
            "original_sha256": None, "metadata": {}, "object_url": "https://example.invalid/object", "intended_role": "synthetic test"}
        photos = {"schema_version": "w20-museum-photo-intake/1.0.0", "classification": "SOURCE_PHOTO_EVIDENCE_ONLY_NOT_DATA002_ADMISSION",
            "candidate_count": 7, "distinct_physical_support_groups": 3, "bytes_hashed": 0, "media_bytes_written_to_disk": False,
            "items": [dict(photo_item, candidate_id=f"photo-{i}") for i in range(7)], "grouping": {}}
        photos["evidence_sha256"] = hashlib.sha256(w20_manifest.canonical(photos)).hexdigest()
        census["benchmark_screen"].update({"screened_sign_ids": 1, "positive_public_metadata_overlaps": 0, "no_literal_match_is_clearance": False})
        census["evidence_sha256"] = hashlib.sha256(w20_manifest.canonical({key: value for key, value in census.items() if key != "evidence_sha256"})).hexdigest()
        photos["evidence_sha256"] = hashlib.sha256(w20_manifest.canonical({key: value for key, value in photos.items() if key != "evidence_sha256"})).hexdigest()
        manifest = w20_manifest.build_manifest(census, photos)
        self.assertEqual([], w20_manifest.validate_manifest(manifest))
        manifest["items"][0]["disposition"]["training_admission"] = True
        self.assertIn("AKU-PAL-HT-1234: promotion flag must remain false", w20_manifest.validate_manifest(manifest))

    def test_w20_photo_original_bytes_require_mime_magic_and_publisher_hash(self):
        raw = b"\xff\xd8synthetic-jpeg-bytes"
        info = {"original_url": "https://upload.wikimedia.org/file.jpg", "mime": "image/jpeg", "file_sha1_publisher_claim": hashlib.sha1(raw).hexdigest()}
        self.assertTrue(museum_w20.original_bytes_match(raw, "image/jpeg", info))
        self.assertFalse(museum_w20.original_bytes_match(raw + b"altered", "image/jpeg", info))
        self.assertFalse(museum_w20.original_bytes_match(raw, "image/png", info))
        self.assertFalse(museum_w20.original_bytes_match(b"not-an-image", "image/jpeg", info))

    def test_w20_report_validator_refuses_admission_and_text_rights_escalation(self):
        report = {"schema_version": "w20-museum-photo-intake/1.0.0", "media_bytes_written_to_disk": False, "candidate_count": 1,
            "bytes_hashed": 0, "items": [{"candidate_id": "x", "training_admission": False, "gold_admission": False,
            "benchmark_overlap": "UNKNOWN_QUARANTINED", "text_rights": "NOT_VERIFIED_OR_NOT_ASSUMED", "group_id": "g"}],
            "distinct_physical_support_groups": 1, "grouping": {"g": ["x"]}}
        self.assertEqual([], museum_w20.validate_report(report))
        report["items"][0]["training_admission"] = True
        report["items"][0]["text_rights"] = "CLEARED"
        self.assertEqual(2, len(museum_w20.validate_report(report)))

    def test_w20_source_selection_is_deterministic_and_deduplicates_ids(self):
        rows = [
            {"sign_id": 1, "text_ids": [10]}, {"sign_id": 2, "text_ids": [10]},
            {"sign_id": 3, "text_ids": [20]}, {"sign_id": 4, "text_ids": [20]},
        ]
        selected_a, plan_a = akupal_w20.select_ids(rows, 4, 2)
        selected_b, plan_b = akupal_w20.select_ids(rows, 4, 2)
        self.assertEqual([1, 3, 2, 4], selected_a)
        self.assertEqual(selected_a, selected_b)
        self.assertEqual(plan_a, plan_b)
        self.assertEqual(len(set(selected_a)), len(selected_a))

    def test_w20_registry_hashes_use_git_blob_not_windows_checkout_newlines(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "docs/research").mkdir(parents=True)
            path = root / "docs/research/public.jsonl"
            path.write_bytes(b'{"id":1}\r\n')
            self.assertEqual(b'{"id":1}\r\n', akupal_w20.repository_evidence_bytes(path, root=root))
            (root / ".git").write_text("fixture", encoding="utf-8")
            with patch.object(akupal_w20.subprocess, "check_output", return_value=b'{"id":2}\n'):
                with self.assertRaisesRegex(akupal_w20.AuditError, "drift detected"):
                    akupal_w20.repository_evidence_bytes(path, root=root)
        _, _, receipt = akupal_w20.benchmark_registry()
        public_path = ROOT / "docs/research/R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl"
        pinned_public = akupal_w20.repository_evidence_bytes(public_path)
        self.assertEqual(akupal_w20.digest(pinned_public), receipt["public_r017_sha256"])
        self.assertEqual(266, receipt["public_r017_row_count"])

    def test_w28_preregistered_source_manifest_and_full_candidate_denominators(self):
        prereg = json.loads((ROOT / "data/releases/w28_candidate_study_preregistration.json").read_text(encoding="utf-8"))
        report = json.loads((ROOT / "data/releases/w28_candidate_readiness.json").read_text(encoding="utf-8"))
        self.assertEqual("PREREGISTERED_BEFORE_NEW_IMAGE_OR_LABEL_RETRIEVAL", prereg["state"])
        self.assertEqual(159, report["ddd"]["images"])
        self.assertEqual(50, report["ddd"]["physical_supports"])
        self.assertEqual(17885, report["ddd"]["publisher_annotations"])
        self.assertEqual(504, report["ddd"]["publisher_classes"])
        self.assertEqual(0, report["ddd"]["raw_polygon_annotations_loaded"])
        self.assertEqual(0, report["retrieval_limits"]["image_bytes_retrieved"])
        self.assertEqual(0, report["retrieval_limits"]["annotation_payloads_retrieved"])
        self.assertEqual(1, report["retrieval_limits"]["published_split_membership_payloads_retrieved"])
        self.assertEqual(2, report["retrieval_limits"]["sample_class_metadata_payloads_retrieved"])
        cb = report["publisher_c_b_reproduction"]
        self.assertEqual("REPLAYED_DOCUMENT_SAMPLE_SUPPORT_MEMBERSHIP_PASS_LABEL_SET_DRIFT", cb["reproduction_state"])
        self.assertEqual([5009, 4623, 5123], [cb["partitions"][key]["sample_count"] for key in ("train", "val", "test")])
        self.assertEqual([9, 11, 12], [cb["partitions"][key]["physical_support_count"] for key in ("train", "val", "test")])
        self.assertTrue(cb["document_ids_partition_disjoint"])
        self.assertTrue(cb["sample_ids_partition_disjoint"])
        self.assertTrue(cb["physical_supports_partition_disjoint"])
        self.assertFalse(cb["class_list_matches_sample_metadata"])
        self.assertEqual(2, cb["class_membership_diagnostic"]["split_only_label_count"])
        self.assertEqual(2, cb["class_membership_diagnostic"]["sample_only_label_count"])
        self.assertEqual(32, cb["w24_crosswalk"]["c_b_supports_covered"])
        self.assertEqual(18, cb["w24_crosswalk"]["c_b_physical_supports_not_in_published_split"])
        self.assertEqual(report["candidate_count"], len(report["candidate_rows"]))
        self.assertEqual([], w28_readiness.validate_report(report))
        ids = {row["candidate_id"] for row in report["candidate_rows"]}
        self.assertIn("TURIN-CAT2044-013-P01", ids)
        self.assertIn("TURIN-S6759-ORACLE-TIFF", ids)
        self.assertIn("TURIN-CAT2169-P01-TIFF", ids)
        self.assertIn("TOKYO-IIIF-MOLLER-PRINTED-STRIPS", ids)
        aku = next(row for row in report["candidate_rows"] if row["candidate_id"] == "AKU-PAL-COMPARISON-ONLY")
        self.assertEqual(240, aku["source_records"])
        self.assertEqual(63, aku["positive_public_benchmark_overlaps"])
        self.assertEqual(177, aku["records_rights_or_identity_blocked"])
        self.assertIsNone(aku["physical_support_group"])

    def test_w28_readiness_rejects_rights_label_promotion_fake_hash_and_source_variant_split(self):
        report = json.loads((ROOT / "data/releases/w28_candidate_readiness.json").read_text(encoding="utf-8"))
        ddd_row = next(row for row in report["candidate_rows"] if row["candidate_id"].startswith("DDD-IMAGE-"))
        tampered = copy.deepcopy(report)
        row = next(row for row in tampered["candidate_rows"] if row["candidate_id"] == ddd_row["candidate_id"])
        row["gate_state"]["image_rights"] = "CLEARED"  # dataset CC BY-NC-SA is not photo permission
        row["admissible_for_training"] = True
        self.assertTrue(w28_readiness.validate_report(tampered))

        tampered = copy.deepcopy(report)
        row = next(row for row in tampered["candidate_rows"] if row["candidate_id"] == ddd_row["candidate_id"])
        row["original_sha256"] = "a" * 64  # no W28 original bytes were retrieved
        self.assertTrue(any("hash asserted without W28 byte retrieval" in error for error in w28_readiness.validate_report(tampered)))

        tampered = copy.deepcopy(report)
        related = [row for row in tampered["candidate_rows"] if row.get("accession") == "Cat.1880"]
        self.assertGreaterEqual(len(related), 2)
        related[-1]["physical_support_group"] = "MUSEO-EGIZIO:CAT-1880-ROTATED-NEW-SUPPORT"
        self.assertTrue(any("physical-object variants split" in error for error in w28_readiness.validate_report(tampered)))

        tampered = copy.deepcopy(report)
        ddd = [row for row in tampered["candidate_rows"] if row["candidate_id"].startswith("DDD-IMAGE-")]
        same_support = next(group for group in {row["physical_support_group"] for row in ddd}
                            if sum(row["physical_support_group"] == group for row in ddd) > 1)
        siblings = [row for row in ddd if row["physical_support_group"] == same_support]
        siblings[1]["published_split_membership"] = "test" if siblings[0]["published_split_membership"] != "test" else "train"
        self.assertTrue(any("same physical support crosses publisher partitions" in error for error in w28_readiness.validate_report(tampered)))

    def test_w28_readiness_rejects_label_without_crop_binding_and_production_promotion(self):
        report = json.loads((ROOT / "data/releases/w28_candidate_readiness.json").read_text(encoding="utf-8"))
        tampered = copy.deepcopy(report)
        row = next(row for row in tampered["candidate_rows"] if row["candidate_id"].startswith("DDD-IMAGE-"))
        row["publisher_polygon_annotation_loaded"] = True
        self.assertTrue(any("polygon payload without pixel binding" in error for error in w28_readiness.validate_report(tampered)))

        tampered = copy.deepcopy(report)
        tampered["aggregate"]["corpus_v1_release_created"] = True
        tampered["aggregate"]["production_release_enabled"] = True
        tampered["aggregate"]["data008_capability_points_claimed"] = 3
        self.assertTrue(w28_readiness.validate_report(tampered))

    def test_w28_readiness_rejects_benchmark_ancestry_unknown_as_clearance_and_print_as_photo(self):
        report = json.loads((ROOT / "data/releases/w28_candidate_readiness.json").read_text(encoding="utf-8"))
        row = next(row for row in report["candidate_rows"] if row["candidate_id"] == "TOKYO-IIIF-MOLLER-PRINTED-STRIPS")
        self.assertIn("not original manuscript photograph", row["photo_type"])
        self.assertEqual("UNKNOWN_QUARANTINED", row["benchmark_state"])
        tampered = copy.deepcopy(report)
        row = next(row for row in tampered["candidate_rows"] if row["candidate_id"].startswith("DDD-IMAGE-"))
        row["benchmark_state"] = "CLEARED"
        self.assertTrue(w28_readiness.validate_report(tampered))

    def test_w28_readiness_digest_detects_source_ledger_drift(self):
        report = json.loads((ROOT / "data/releases/w28_candidate_readiness.json").read_text(encoding="utf-8"))
        report["candidate_rows"][0]["rejection_reasons"].append("silently changed")
        self.assertIn("readiness evidence digest mismatch", w28_readiness.validate_report(report))


if __name__ == "__main__":
    unittest.main()
