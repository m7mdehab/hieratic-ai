"""Validate and assemble DATA-008 corpus release packets from accepted contracts.

The command is metadata-first: it never downloads source material. It publishes a
canonical index and audit packet that references immutable preprocessing outputs.
"""
from __future__ import annotations

import argparse
import copy
import ctypes
import errno
import hashlib
import json
import os
import secrets
import shutil
import stat
import sys
import tempfile
import base64
import subprocess
import datetime as dt
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from tools import acquisition, alignment, annotation_review, annotation_validation
from tools import preprocessing, sign_mappings, split_system, source_registry

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/dataset_release.schema.json"
ACQ_SCHEMA = ROOT / "schemas/acquisition_manifest.schema.json"
ANNOTATION_SCHEMA = ROOT / "schemas/annotation.schema.json"
ALIGN_SCHEMA = ROOT / "schemas/alignment_manifest.schema.json"
REVIEW_SCHEMA = ROOT / "schemas/annotation_review.schema.json"
MAPPING_SCHEMA = ROOT / "schemas/sign_mappings.schema.json"
SPLIT_SCHEMA = ROOT / "schemas/split_manifest.schema.json"
SPLIT_PROFILES = ROOT / "eval/splits/profiles.yaml"
REGISTRY = ROOT / "data/sources/registry.yaml"
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_ARTIFACT_BYTES = 256 * 1024 * 1024
MAX_RELEASE_BYTES = 512 * 1024 * 1024
GENERATOR = "hieratic-corpus-release/1.0.0"
# This repository does not yet have an independently protected trust-root or
# authenticated reviewer/document attestation service. No YAML value, key,
# signature, environment variable, or caller-supplied receipt may turn this on.
PRODUCTION_AUTHORIZATION_HARD_DISABLED = True
PRODUCTION_AUTHORIZATION_BLOCKER = (
    "production authorization is hard-disabled pending overseer-governed, "
    "independently protected trust-root and reviewer/document verification onboarding"
)
ADMISSION_SCHEMA = ROOT / "data/releases/admission.schema.json"
READINESS_SCHEMA = ROOT / "data/releases/readiness.schema.json"
TRUST_ANCHOR_SCHEMA = ROOT / "data/releases/trust_anchors.schema.json"
TRUST_ANCHORS = ROOT / "data/releases/trust_anchors.yaml"
R016_ROSTER = ROOT / "docs/research/R016_PRELIMINARY_CANDIDATE_ROSTER.yaml"
R017_CROSSWALK = ROOT / "docs/research/R017_R016_CANDIDATE_SOURCE_CROSSWALK.json"
R017_METADATA = ROOT / "docs/research/R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl"
REQUIRED_PROVENANCE_TYPES = ["institution", "collection", "object", "manuscript", "fragment", "side", "image_exposure", "acquisition", "original_image", "preprocessing", "annotation", "alignment", "expert_review", "split", "release"]
REQUIRED_CORPUS_RIGHTS = {
    *((component, use) for component in ("original_image", "derived_image", "diplomatic_transcription", "transliteration", "hieroglyphic_rendering", "sign_mapping", "expert_gold") for use in ("training", "development", "redistribution")),
    ("model_training", "training"),
}


class ReleaseError(ValueError):
    """Input failed a DATA-008 release gate."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_document(path: Path) -> Any:
    try:
        raw = path.read_bytes()
        if len(raw) > MAX_INPUT_BYTES:
            raise ReleaseError(f"input exceeds {MAX_INPUT_BYTES} byte limit: {path}")
        if path.suffix.lower() == ".json":
            return json.loads(raw.decode("utf-8"))
        return yaml.safe_load(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ReleaseError(f"cannot read {path}: {exc}") from exc


def safe_path(base: Path, relative: str, *, must_exist: bool = True) -> Path:
    """Resolve a bundle-relative path while refusing symlinks and root escape."""
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ReleaseError(f"absolute input path is forbidden: {relative}")
    root = base.resolve(strict=True)
    current = root
    for part in candidate.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            current = current.parent
            if not current.is_relative_to(root):
                raise ReleaseError(f"input path escapes bundle directory: {relative}")
            continue
        current = current / part
        if current.is_symlink():
            raise ReleaseError(f"symlink input path is forbidden: {relative}")
    result = current.resolve(strict=must_exist)
    if not result.is_relative_to(root):
        raise ReleaseError(f"input path escapes bundle directory: {relative}")
    if must_exist and not result.is_file() and not result.is_dir():
        raise ReleaseError(f"input path is not a file or directory: {relative}")
    return result


def _schema_errors(value: Any, path: Path, label: str) -> list[str]:
    schema = read_document(path)
    found = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value), key=lambda e: str(e.absolute_path))
    return [f"{label}{''.join(f'[{part!r}]' for part in err.absolute_path)}: {err.message}" for err in found]


def _read_checked(base: Path, relative: str, audit: list[dict[str, str]]) -> tuple[Any, Path]:
    path = safe_path(base, relative)
    if not path.is_file():
        raise ReleaseError(f"expected a manifest file: {relative}")
    raw = path.read_bytes()
    if len(raw) > MAX_INPUT_BYTES:
        raise ReleaseError(f"input exceeds {MAX_INPUT_BYTES} byte limit: {relative}")
    audit.append({"path": relative.replace("\\", "/"), "sha256": digest(raw), "size_bytes": len(raw)})
    return read_document(path), path


def _map_by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {row[key]: row for row in items}


def _utc(value: str, label: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone is required")
        return parsed.astimezone(dt.timezone.utc)
    except (ValueError, AttributeError) as exc:
        raise ReleaseError(f"{label} must be a timezone-aware ISO-8601 timestamp") from exc


def _verify_ed25519(public_key: bytes, signature: bytes, message: bytes) -> bool:
    """Verify a receipt using installed crypto support, with OpenSSL as fallback."""
    if len(public_key) != 32 or len(signature) != 64:
        return False
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
        return True
    except ImportError:
        pass
    except Exception:
        return False
    openssl = shutil.which("openssl")
    if not openssl:
        return False
    # RFC 8410 SubjectPublicKeyInfo prefix for Ed25519; no external key is created.
    public_der = bytes.fromhex("302a300506032b6570032100") + public_key
    with tempfile.TemporaryDirectory(prefix="hieratic-receipt-") as temp:
        root = Path(temp)
        pub_der, msg, sig = root / "key.der", root / "payload.bin", root / "signature.bin"
        pub_der.write_bytes(public_der); msg.write_bytes(message); sig.write_bytes(signature)
        try:
            converted = subprocess.run([openssl, "pkey", "-pubin", "-inform", "DER", "-in", str(pub_der), "-out", str(root / "key.pem")], capture_output=True, timeout=10)
            if converted.returncode:
                return False
            verified = subprocess.run([openssl, "pkeyutl", "-verify", "-pubin", "-inkey", str(root / "key.pem"), "-rawin", "-in", str(msg), "-sigfile", str(sig)], capture_output=True, timeout=10)
            return verified.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False


def validate_provenance_graph(graph: Any, graph_schema: dict[str, Any], *, item_id: str,
                              source_id: str, source_object_id: str, expected_hashes: dict[str, str],
                              object_identity: dict[str, Any] | None = None) -> list[str]:
    fragment = {"$schema": graph_schema["$schema"], "$defs": graph_schema["$defs"], **graph_schema["$defs"]["provenanceGraph"]}
    errors = _schema_errors_against(graph, fragment, "provenance graph")
    if errors:
        return errors
    if graph["item_id"] != item_id:
        errors.append("provenance graph item_id differs from release item")
    nodes: dict[str, dict[str, Any]] = {}
    asset_keys: set[tuple[str, str]] = set()
    for node in graph["nodes"]:
        node_id = node["node_id"]
        if node_id in nodes:
            errors.append(f"duplicate provenance node_id: {node_id}")
        nodes[node_id] = node
        if node["source_registry_id"] != source_id:
            errors.append(f"provenance node {node_id} source_registry_id differs from admitted source")
        if node["source_object_id"] != source_object_id:
            errors.append(f"provenance node {node_id} source-object inheritance mismatch")
        pair = (node["node_type"], node["asset_id"])
        if pair in asset_keys:
            errors.append(f"duplicate provenance asset identity: {pair[0]}/{pair[1]}")
        asset_keys.add(pair)
        expected = expected_hashes.get(node["node_type"])
        if expected and node.get("sha256") != expected:
            errors.append(f"provenance node {node_id} hash does not match its upstream artifact")
        attributes = node.get("attributes", {})
        if node["node_type"] == "object" and object_identity:
            for field in ("institutional_accession", "manuscript_group_id"):
                if attributes.get(field) != object_identity.get(field):
                    errors.append(f"provenance object node {node_id} {field} does not match signed institutional identity")
        if node["node_type"] == "manuscript" and object_identity and attributes.get("manuscript_group_id") != object_identity.get("manuscript_group_id"):
            errors.append(f"provenance manuscript node {node_id} does not match signed manuscript group")
        if node["node_type"] == "fragment" and object_identity and attributes.get("fragment_id") not in object_identity.get("fragment_ids", []):
            errors.append(f"provenance fragment node {node_id} is outside signed fragment identity")
        if node["node_type"] == "side" and object_identity and attributes.get("side_id") not in object_identity.get("side_ids", []):
            errors.append(f"provenance side node {node_id} is outside signed recto/verso identity")
    edges = graph["edges"]
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    reverse: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    edge_keys: set[tuple[str, str, str]] = set()
    for edge in edges:
        left, right = edge["from_node_id"], edge["to_node_id"]
        if left not in nodes or right not in nodes:
            errors.append(f"provenance edge references missing node: {left} -> {right}")
            continue
        key = (left, right, edge["relation"])
        if key in edge_keys:
            errors.append(f"duplicate provenance edge: {left} -> {right}")
        edge_keys.add(key); adjacency[left].add(right); reverse[right].add(left)
        if edge["relation"] == "derived_from" and not edge.get("transformation_id"):
            errors.append(f"provenance derivation {left} -> {right} lacks a transformation identity")
    indegree = {node_id: len(reverse[node_id]) for node_id in nodes}
    ready = [node_id for node_id, count in indegree.items() if count == 0]
    visited = 0
    while ready:
        current = ready.pop(); visited += 1
        for child in adjacency[current]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if visited != len(nodes):
        errors.append("provenance graph contains a cycle")
    by_type = {kind: [key for key, row in nodes.items() if row["node_type"] == kind] for kind in REQUIRED_PROVENANCE_TYPES}
    missing = [kind for kind, ids in by_type.items() if not ids]
    if missing:
        errors.append("provenance graph lacks required lineage stages: " + ", ".join(missing))
    else:
        def reachable(starts: list[str], target: str) -> bool:
            pending, seen = list(starts), set()
            while pending:
                current = pending.pop()
                if current == target:
                    return True
                if current in seen:
                    continue
                seen.add(current); pending.extend(adjacency.get(current, ()))
            return False
        for prior, following in zip(REQUIRED_PROVENANCE_TYPES, REQUIRED_PROVENANCE_TYPES[1:]):
            if not any(reachable([start], end) for start in by_type[prior] for end in by_type[following]):
                errors.append(f"provenance lineage is broken between {prior} and {following}")
    for kind, expected in expected_hashes.items():
        if kind in by_type and by_type[kind] and all(nodes[node].get("sha256") != expected for node in by_type[kind]):
            errors.append(f"provenance graph has no {kind} node with the verified upstream hash")
    return errors


def _schema_errors_against(value: Any, schema: dict[str, Any], label: str) -> list[str]:
    found = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value), key=lambda e: str(e.absolute_path))
    return [f"{label}{''.join(f'[{part!r}]' for part in err.absolute_path)}: {err.message}" for err in found]


def validate_trust_store(trust_store: Any) -> list[str]:
    """Check trust-store syntax only; this does not establish authority."""
    errors = _schema_errors_against(trust_store, read_document(TRUST_ANCHOR_SCHEMA), "trust-anchor store")
    if errors:
        return errors
    for anchor in trust_store["anchors"]:
        try:
            public_key = base64.b64decode(anchor["public_key_ed25519_base64"], validate=True)
            if len(public_key) != 32:
                errors.append(f"trust anchor {anchor['key_id']} has an invalid Ed25519 public key")
            start, end = _utc(anchor["valid_from"], "trust anchor valid_from"), _utc(anchor["valid_until"], "trust anchor valid_until")
            if end <= start:
                errors.append(f"trust anchor {anchor['key_id']} has a non-positive validity interval")
        except (ValueError, KeyError, TypeError, ReleaseError):
            errors.append(f"trust anchor {anchor.get('key_id', 'unknown')} is malformed")
    return errors


def validate_admission_evidence(evidence: Any, trust_store: Any, *, source_id: str, source_object_id: str,
                                item_id: str, expected_assets: dict[str, tuple[str, str]],
                                expected_hashes: dict[str, str] | None = None,
                                expected_roster_version: str | None = None,
                                expected_source_record_sha256: str | None = None,
                                as_of: dt.datetime | None = None) -> list[str]:
    schema = read_document(ADMISSION_SCHEMA)
    errors = _schema_errors_against(evidence, schema, "authorization evidence")
    if errors:
        return errors
    # The function remains useful for structural/security regression checks.
    # A cryptographically valid signature is not an authenticated institutional
    # identity, reviewer role, permission document, or protected trust root.
    errors.append(PRODUCTION_AUTHORIZATION_BLOCKER)
    trust_errors = validate_trust_store(trust_store)
    if trust_errors:
        return trust_errors
    if trust_store.get("status") == "synthetic_test_fixture":
        return ["synthetic trust anchors cannot authorize a production corpus release"]
    anchors = trust_store.get("anchors", [])
    if trust_store.get("status") not in {"no_external_authorities_configured", "externally_verified_authorities_configured", "synthetic_test_fixture"}:
        errors.append("trust-anchor store status is invalid")
    if trust_store.get("status") == "no_external_authorities_configured" and anchors:
        errors.append("trust-anchor store claims no configured authorities but contains keys")
    if trust_store.get("status") == "externally_verified_authorities_configured" and not anchors:
        errors.append("trust-anchor store claims configured authorities but has no keys")
    if not isinstance(anchors, list) or not anchors:
        errors.append("no signing key is listed in trust-store metadata; this metadata is not an external trust root")
    anchor_ids = [row.get("key_id") for row in anchors if isinstance(row, dict)]
    if len(anchor_ids) != len(anchors) or len(anchor_ids) != len(set(anchor_ids)):
        errors.append("trust-anchor store has malformed or duplicate key identities")
    if evidence["decision"]["source_registry_id"] != source_id or evidence["decision"]["source_object_id"] != source_object_id:
        errors.append("authorization decision is not bound to the admitted source and object")
    decision = evidence["decision"]
    if expected_source_record_sha256 and decision.get("source_registry_record_sha256") != expected_source_record_sha256:
        errors.append("source-registry rights record changed after authorization review")
    if decision["status"] != "allowed":
        errors.append(f"authorization decision claim is {decision['status']}; a claimed allowed value does not establish permission")
    if as_of is None:
        as_of = dt.datetime.now(dt.timezone.utc)
    reviewed_at = _utc(decision["reviewed_at"], "authorization review timestamp")
    if reviewed_at > as_of:
        errors.append("authorization review timestamp is in the future")
    if decision.get("expires_at"):
        expiry = _utc(decision["expires_at"], "authorization expiry")
        if expiry <= as_of:
            errors.append("authorization decision has expired")
        if expiry <= reviewed_at:
            errors.append("authorization expiry does not follow the accountable review")
    receipt = evidence["receipt"]
    receipt_id = receipt["receipt_id"]
    if receipt_id in trust_store.get("revoked_receipt_ids", []):
        errors.append(f"authorization receipt {receipt_id} has been revoked")
    if receipt_id in trust_store.get("superseded_receipt_ids", []):
        errors.append(f"authorization receipt {receipt_id} has been superseded")
    if decision.get("status") == "revoked":
        errors.append(f"authorization receipt {receipt_id} records a revoked decision")
    if receipt.get("signed_by") != decision.get("reviewer_id"):
        errors.append("signed receipt identity does not match accountable authorization reviewer")
    payload = {key: copy.deepcopy(value) for key, value in evidence.items() if key != "receipt"}
    payload_bytes = canonical(payload)
    payload_hash = digest(payload_bytes)
    if receipt.get("payload_sha256") != payload_hash:
        errors.append("signed authorization payload hash does not match evidence content")
    trust = next((row for row in anchors if isinstance(row, dict) and row.get("key_id") == receipt.get("key_id")), None)
    signature_ok = False
    if trust is None:
        errors.append(f"authorization signing key is not listed in caller-controlled trust metadata: {receipt.get('key_id')}")
    else:
        if trust.get("reviewer_id") != receipt.get("signed_by"):
            errors.append("trust anchor reviewer identity does not match receipt signer")
        if source_id not in trust.get("source_ids", []) or trust.get("authority_role") not in {"rights_holder_representative", "institutional_steward", "legal_reviewer", "corpus_overseer"}:
            errors.append("trust anchor is not authorized for this source-rights decision")
        try:
            valid_from, valid_until = _utc(trust["valid_from"], "trust anchor valid_from"), _utc(trust["valid_until"], "trust anchor valid_until")
            if not valid_from <= as_of <= valid_until:
                errors.append("authorization signing trust anchor is outside its validity period")
            signed_at = _utc(receipt["signed_at"], "authorization receipt signed_at")
            if not valid_from <= signed_at <= valid_until or signed_at > as_of:
                errors.append("authorization receipt was signed outside its trust-anchor validity period")
            signature = base64.b64decode(receipt["signature_ed25519_base64"], validate=True)
            public_key = base64.b64decode(trust["public_key_ed25519_base64"], validate=True)
            signature_ok = _verify_ed25519(public_key, signature, payload_bytes)
        except (ValueError, KeyError, TypeError):
            signature_ok = False
        if not signature_ok:
            errors.append("authorization receipt signature is invalid or cannot be verified")

    evidence_by_id = {row["evidence_id"]: row for row in evidence["submitted_evidence"]}
    if len(evidence_by_id) != len(evidence["submitted_evidence"]):
        errors.append("duplicate submitted evidence identity")
    claimant_ids = {row["claimant_id"] for row in evidence["contributor_assertions"]}
    if not evidence["contributor_assertions"]:
        errors.append("no contributor assertions are preserved separately from review decisions")
    for assertion in evidence["contributor_assertions"]:
        unknown = set(assertion["evidence_refs"]) - evidence_by_id.keys()
        if unknown:
            errors.append(f"contributor assertion {assertion['assertion_id']} references missing evidence: {', '.join(sorted(unknown))}")
    reviews = evidence["independent_reviews"]
    reviewers = {row["reviewer_id"] for row in reviews}
    if reviewers & claimant_ids:
        errors.append("claimed reviewer is also a contributor and cannot be treated as independent")
    # These role strings are submitter claims. Keep checking their shape and
    # conflicts, but never interpret them as independent identity proof.
    required_roles = {"rights_holder_representative", "egyptologist", "benchmark_auditor"}
    present_roles = {row["reviewer_role"] for row in reviews if row["decision"] == "allowed" and row["subject_id"] == source_object_id}
    if "institutional_steward" in present_roles or "legal_reviewer" in present_roles:
        required_roles.discard("rights_holder_representative")
    if required_roles - present_roles:
        errors.append("missing claimed role-review rows: " + ", ".join(sorted(required_roles - present_roles)))
    by_role = {row["reviewer_role"]: row for row in reviews if row["decision"] == "allowed" and row["subject_id"] == source_object_id}
    rights_role = by_role.get("rights_holder_representative") or by_role.get("institutional_steward") or by_role.get("legal_reviewer")
    if rights_role and not {"training", "development", "redistribution"} <= set(rights_role["intended_use"]):
        errors.append("rights reviewer did not explicitly review training, development, and redistribution scopes")
    expert_role = by_role.get("egyptologist")
    if expert_role and "training" not in expert_role["intended_use"]:
        errors.append("Egyptologist review does not cover expert-gold training use")
    if not {"training", "development", "redistribution"} <= set(decision["intended_uses"]):
        errors.append("authorization decision omits training, development, or redistribution intended use")
    accountable_reviewers = [row["reviewer_id"] for role in ("rights_holder_representative", "institutional_steward", "legal_reviewer", "egyptologist", "benchmark_auditor")
                             for row in [by_role.get(role)] if row]
    if len(accountable_reviewers) != len(set(accountable_reviewers)):
        errors.append("claimed rights, scholarly-gold, and benchmark-clearance roles must use distinct reviewer IDs; identities remain unverified")
    for review in reviews:
        unknown = set(review["evidence_refs"]) - evidence_by_id.keys()
        if unknown:
            errors.append(f"review {review['review_id']} references missing evidence: {', '.join(sorted(unknown))}")
        if review["reviewer_id"] in claimant_ids:
            errors.append(f"review {review['review_id']} is not independent of a contributor assertion")
    evidence_items = evidence["bound_assets"]
    actual: dict[str, tuple[str, str]] = {}
    for bound in evidence_items:
        if bound["source_registry_id"] != source_id or bound["source_object_id"] != source_object_id:
            errors.append(f"bound asset {bound['asset_id']} has conflicting source/object identity")
        key = bound["component"]
        if key in actual:
            errors.append(f"duplicate bound asset component: {key}")
        actual[key] = (bound["asset_id"], bound["sha256"])
    for component, pair in expected_assets.items():
        if actual.get(component) != pair:
            errors.append(f"bound {component} asset identity/hash does not match release inputs")

    terms = evidence["license_terms"]
    term_map = {(term["component"], term["use"]): term for term in terms}
    if len(term_map) != len(terms):
        errors.append("duplicate component/use rights terms are ambiguous")
    for component, use in sorted(REQUIRED_CORPUS_RIGHTS):
        term = term_map.get((component, use))
        if term is None:
            errors.append(f"missing rights term for {component}/{use}")
        elif term["decision"] != "allowed":
            errors.append(f"{component}/{use} permission is {term['decision']}, not allowed")
        elif not term["attribution"].strip():
            errors.append(f"{component}/{use} lacks required attribution")
        elif term["conditions"]:
            errors.append(f"{component}/{use} is conditional and its conditions are not independently satisfied")
        if term and term["terms_evidence_ref"] not in evidence_by_id:
            errors.append(f"{component}/{use} references missing submitted license evidence")
        elif term:
            if actual.get(component) != (term["asset_id"], term["asset_sha256"]):
                errors.append(f"{component}/{use} terms do not apply to the exact admitted asset hash")
            ref = evidence_by_id[term["terms_evidence_ref"]]
            if ref["kind"] not in {"license_terms", "permission_letter", "institutional_policy", "annotation_agreement", "mapping_agreement", "expert_agreement"}:
                errors.append(f"{component}/{use} references evidence of the wrong type")
            if ref["component"] not in {component, "all"}:
                errors.append(f"{component}/{use} references evidence scoped to a different material component")

    overlap = evidence["benchmark_overlap"]
    if overlap["state"] != "independently_cleared":
        errors.append(f"benchmark overlap state is {overlap['state']}; unresolved metadata cannot authorize training")
    if expected_roster_version and overlap["roster_version"] != expected_roster_version:
        errors.append("benchmark overlap decision uses a stale or different pinned roster version")
    required_screening_methods = {"institutional_object_ids", "alternate_accession_identifiers", "recto_verso_identity", "joined_fragment_identity", "editions_facsimiles_reproductions", "source_document_and_scribe", "original_sha256", "derived_sha256", "reviewed_perceptual_hashes"}
    if required_screening_methods - set(overlap["methods"]):
        errors.append("benchmark overlap review omits required screens: " + ", ".join(sorted(required_screening_methods - set(overlap["methods"]))))
    scope = overlap["scope"]
    required_scope = {
        "object_ids": {source_object_id},
        "accessions": {decision.get("institutional_accession")},
        "sides": set(decision.get("side_ids", [])),
        "fragments": set(decision.get("fragment_ids", [])),
        "original_hashes": {asset[1] for name, asset in expected_assets.items() if name == "original_image"},
        "derived_hashes": {asset[1] for name, asset in expected_assets.items() if name == "derived_image"},
        "scribe_groups": {decision.get("scribe_group")} if decision.get("scribe_group") else set(),
    }
    for key, required_values in required_scope.items():
        required_values.discard(None)
        if not required_values <= set(scope.get(key, [])):
            errors.append(f"benchmark overlap evidence scope omits source identity values for {key}")
    if not overlap["reviewer_id"] or overlap["reviewer_id"] in claimant_ids:
        errors.append("benchmark overlap clearance lacks a claimed reviewer; reviewer authority remains unverified")
    elif not any(row["reviewer_id"] == overlap["reviewer_id"] and row["reviewer_role"] == "benchmark_auditor" and row["decision"] == "allowed" for row in reviews):
        errors.append("benchmark overlap reviewer lacks a signed benchmark-auditor decision")
    if not overlap["evidence_refs"] or set(overlap["evidence_refs"]) - evidence_by_id.keys():
        errors.append("benchmark overlap evidence references are missing or invalid")
    elif any(evidence_by_id[eid]["kind"] != "benchmark_check" for eid in overlap["evidence_refs"]):
        errors.append("benchmark overlap references are not benchmark-check evidence")

    history = evidence["review_history"]
    history_ids = [row["event_id"] for row in history]
    if len(history_ids) != len(set(history_ids)):
        errors.append("duplicate authorization review-history event identity")
    known_history: set[str] = set()
    for event in history:
        prior = event["supersedes_event_id"]
        if prior and prior not in known_history:
            errors.append(f"review-history event {event['event_id']} supersedes a missing or later event")
        known_history.add(event["event_id"])
    if any(row["event"] in {"revoked", "expired"} for row in history):
        errors.append("authorization review history contains a revoked or expired state")
    if decision.get("supersedes_receipt_id") and decision["supersedes_receipt_id"] == receipt_id:
        errors.append("authorization receipt cannot supersede itself")
    if decision.get("supersedes_receipt_id") and decision["supersedes_receipt_id"] not in trust_store.get("superseded_receipt_ids", []):
        errors.append("superseded receipt is not recorded in the trust-store revocation history")

    graph = evidence.get("provenance_graph")
    if graph is None:
        errors.append("complete source-to-release provenance graph is missing")
    else:
        graph_errors = validate_provenance_graph(graph, schema, item_id=item_id, source_id=source_id,
                                                 source_object_id=source_object_id,
                                                 expected_hashes=expected_hashes or {},
                                                 object_identity=decision)
        errors.extend(graph_errors)
        for edge in graph.get("edges", []):
            unknown = set(edge.get("evidence_refs", [])) - evidence_by_id.keys()
            if unknown:
                errors.append(f"provenance edge references missing evidence: {', '.join(sorted(unknown))}")
    return sorted(set(errors))


def production_authority_gate(trust_store: Any, evidence: Any) -> list[str]:
    """Fail closed until protected external authority onboarding exists.

    Inputs are deliberately ignored: mutable repository trust files and signed
    self-assertions cannot satisfy an independent trust-root requirement.
    """
    del trust_store, evidence
    if PRODUCTION_AUTHORIZATION_HARD_DISABLED:
        return [PRODUCTION_AUTHORIZATION_BLOCKER]
    return []


def _public_authorization_summary(evidence: dict[str, Any] | None) -> dict[str, Any] | None:
    """Emit only a non-sensitive receipt digest and explicitly unverified state."""
    if evidence is None:
        return None
    receipt = evidence.get("receipt", {})
    payload = {key: copy.deepcopy(value) for key, value in evidence.items() if key != "receipt"}
    return {
        "receipt_payload_sha256": digest(canonical(payload)),
        "declared_receipt_id_sha256": digest(str(receipt.get("receipt_id", "")).encode("utf-8")),
        "status": "unverified_claims_not_production_authorization",
        "private_evidence_included": False,
        "independent_reviewer_authority": "unverified",
        "document_bytes_and_substantive_rights": "not_independently_verified",
    }


def _public_provenance_summary(graph: dict[str, Any] | None) -> dict[str, Any] | None:
    if graph is None:
        return None
    return {
        "graph_id": graph.get("graph_id"),
        "item_id": graph.get("item_id"),
        "graph_payload_sha256": digest(canonical(graph)),
        "node_count": len(graph.get("nodes", [])),
        "edge_count": len(graph.get("edges", [])),
        "nodes": [{key: copy.deepcopy(node[key]) for key in (
            "node_id", "node_type", "source_registry_id", "source_object_id", "asset_id", "sha256", "review_status"
        ) if key in node} for node in graph.get("nodes", [])],
        "edges": [{key: copy.deepcopy(edge[key]) for key in (
            "from_node_id", "to_node_id", "relation", "transformation_id"
        ) if key in edge} | {"evidence_reference_count": len(edge.get("evidence_refs", []))}
            for edge in graph.get("edges", [])],
        "status": "structurally_checked_claims_not_independently_verified",
    }


def _public_review_case(case: dict[str, Any]) -> dict[str, Any]:
    """Keep aggregate QA state while excluding reviewer-level private material."""
    public_fields = ("case_id", "target_type", "target_id", "annotation_layer",
                     "annotation_gold_status", "issue_flags", "case_state")
    public = {key: copy.deepcopy(case[key]) for key in public_fields if key in case}
    public["decision_count"] = len(case.get("decisions", []))
    public["adjudication_present"] = case.get("adjudication") is not None
    public["disagreement"] = bool(case.get("disagreement") or case.get("case_state") == "needs_adjudication")
    return public


def _target_annotation(annotation: dict[str, Any], target_type: str, target_id: str) -> dict[str, Any] | None:
    if target_type == "line":
        value = next((x for x in annotation.get("lines", []) if x.get("line_id") == target_id), None)
        if value is None:
            return None
        fields = ("region_id", "parent_line_id", "reading_order", "reading_direction", "geometry", "sequence_id", "grapheme_sequence", "hieroglyphic_rendering", "transliteration", "normalized_representation", "lemma_analysis", "morphology", "syntax", "translations")
        return {"line_id": target_id, "page_id": value.get("page_id"), **{field: copy.deepcopy(value.get(field)) for field in fields}}
    if target_type == "sign":
        value = next((x for x in annotation.get("signs", []) if x.get("sign_id") == target_id), None)
        return copy.deepcopy(value) if value else None
    if target_type == "token":
        for line in annotation.get("lines", []):
            for value in line.get("normalized_representation", {}).get("tokens", []):
                if value.get("token_id") == target_id:
                    return {"token": copy.deepcopy(value), "line_id": line.get("line_id"), "page_id": line.get("page_id")}
    return None


def _validate_source(bundle: dict[str, Any], row: dict[str, Any], base: Path, registry: dict[str, Any],
                     split_metadata: dict[str, Any], split_manifest: dict[str, Any], profile_set: dict[str, Any],
                     audit: list[dict[str, str]], release_kind: str) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    iid = row["item_id"]
    try:
        acq, _ = _read_checked(base, row["acquisition_path"], audit)
        request, request_path = _read_checked(base, row["preprocessing_request_path"], audit)
        artifact_manifest, _ = _read_checked(base, row["preprocessing_artifact_manifest_path"], audit)
        annotation, _ = _read_checked(base, row["annotation_path"], audit)
        mappings, _ = _read_checked(base, row["mapping_path"], audit)
        alignments, _ = _read_checked(base, row["alignment_path"], audit)
        reviews, _ = _read_checked(base, row["review_path"], audit)
        authorization_evidence = None
        if row.get("authorization_evidence_path"):
            authorization_evidence, _ = _read_checked(base, row["authorization_evidence_path"], audit)
            # The authorization envelope can contain private permission-letter
            # locations and reviewer identities. Its public summary below binds
            # the canonical payload digest; do not expose the private path/hash.
            audit[:] = [entry for entry in audit if entry["path"] != row["authorization_evidence_path"].replace("\\", "/")]
    except ReleaseError as exc:
        return {}, [f"{iid}: {exc}"]

    errors += [f"{iid}: {e}" for e in _schema_errors(acq, ACQ_SCHEMA, "DATA-002")]
    acquisition_errors, _ = acquisition.validate_data(acq, registry, read_document(ACQ_SCHEMA))
    if all(item.get("is_synthetic_fixture") is True for item in acq.get("items", [])):
        # Structural fixtures are not permission requests. Preserve every identity,
        # registry, quarantine, and schema error while ignoring only conditional
        # approval completeness that cannot be satisfied by a synthetic fixture.
        acquisition_errors = [e for e in acquisition_errors if "conditional use or redistribution lacks explicit conditions" not in e]
    errors += [f"{iid}: {e}" for e in acquisition_errors]
    errors += [f"{iid}: {e}" for e in annotation_validation.validate_data(annotation, read_document(ANNOTATION_SCHEMA), registry)]
    errors += [f"{iid}: {e}" for e in sign_mappings.validate(mappings, read_document(MAPPING_SCHEMA))]
    alignment_errors, eligibility = alignment.validate(alignments, acq, annotation, registry)
    errors += [f"{iid}: {e}" for e in alignment_errors]
    review_errors, review_report = annotation_review.validate(reviews, annotation, registry)
    errors += [f"{iid}: {e}" for e in review_errors]
    errors += [f"{iid}: {e}" for e in preprocessing.validate_request(request, registry, request_path.parent, acq)]
    if (artifact_manifest.get("generator") != "hieratic-preprocessing/1.0.0"
            or not isinstance(artifact_manifest.get("dataset_version_id"), str)
            or not isinstance(artifact_manifest.get("items"), list)):
        errors.append(f"{iid}: malformed DATA-003 artifact manifest")

    acq_matches = [x for x in acq.get("items", []) if x.get("source_object_id") == annotation.get("provenance", {}).get("source_object_id")]
    if len(acq_matches) != 1:
        errors.append(f"{iid}: annotation source object must match exactly one acquisition item")
        acquired = {}
    else:
        acquired = acq_matches[0]
    source_id = annotation.get("provenance", {}).get("source_registry_id")
    if acquired and source_id != acquired.get("source_id"):
        errors.append(f"{iid}: annotation/acquisition source identity differs")
    source_map = _map_by(registry.get("sources", []), "source_id")
    source = source_map.get(source_id, {})
    if not source:
        errors.append(f"{iid}: unknown DATA-001 source identity {source_id}")
    if acquired and (acquired.get("benchmark_quarantine") or source.get("benchmark_quarantine") or source.get("rights_class") == "EVALUATION-ONLY"):
        errors.append(f"{iid}: benchmark-quarantined or evaluation-only source is excluded")
    if acquired and acquired.get("benchmark_overlap_review", {}).get("status") != "clear" and not acquired.get("is_synthetic_fixture"):
        errors.append(f"{iid}: unresolved DATA-002 benchmark overlap review")

    if artifact_manifest.get("acquisition_manifest_id") != request.get("acquisition_manifest_id"):
        errors.append(f"{iid}: preprocessing artifact manifest/request acquisition identity differs")
    request_bytes_total = 0
    for request_item in request.get("items", []):
        try:
            input_asset = safe_path(request_path.parent, request_item.get("asset_path", ""))
            if not input_asset.is_file():
                errors.append(f"{iid}: DATA-003 input asset is not a file")
                continue
            asset_size = input_asset.stat().st_size
            request_bytes_total += asset_size
            if asset_size > MAX_ARTIFACT_BYTES:
                errors.append(f"{iid}: DATA-003 input asset exceeds {MAX_ARTIFACT_BYTES} byte limit")
        except ReleaseError as exc:
            errors.append(f"{iid}: {exc}")
    if request_bytes_total > MAX_RELEASE_BYTES:
        errors.append(f"{iid}: combined DATA-003 inputs exceed {MAX_RELEASE_BYTES} byte limit")
    req_items = _map_by(request.get("items", []), "item_id")
    art_items = _map_by(artifact_manifest.get("items", []), "item_id")
    pre_item = req_items.get(row["preprocessing_item_id"])
    art_item = art_items.get(row["preprocessing_item_id"])
    if pre_item is None or art_item is None:
        errors.append(f"{iid}: preprocessing request/artifact item reference is broken")
    elif (pre_item.get("source_id"), pre_item.get("source_object_id")) != (source_id, acquired.get("source_object_id")) and not acquired.get("is_synthetic_fixture"):
        errors.append(f"{iid}: preprocessing provenance identity differs from acquisition/annotation")

    artifact_root = safe_path(base, row["preprocessing_artifact_root"])
    if not artifact_root.is_dir():
        errors.append(f"{iid}: preprocessing_artifact_root must name a directory")
    if art_item:
        rel = art_item.get("output_path", "")
        try:
            artifact_path = safe_path(artifact_root, rel)
            if not artifact_path.is_file():
                errors.append(f"{iid}: preprocessed artifact is missing")
            else:
                size = artifact_path.stat().st_size
                if size > MAX_ARTIFACT_BYTES:
                    errors.append(f"{iid}: artifact exceeds {MAX_ARTIFACT_BYTES} byte limit")
                blob = artifact_path.read_bytes()
                if digest(blob) != art_item.get("output_sha256"):
                    errors.append(f"{iid}: preprocessed output hash mismatch")
        except ReleaseError as exc:
            errors.append(f"{iid}: {exc}")

    page = next((p for p in annotation.get("pages", []) if p.get("page_id") == row["page_id"]), None)
    if page is None:
        errors.append(f"{iid}: page_id does not resolve in DATA-004 annotation")
    if annotation.get("document", {}).get("metadata", {}).get("document_id") not in {None, row["document_id"]}:
        errors.append(f"{iid}: document identity differs from DATA-004 metadata")
    if annotation.get("provenance", {}).get("source_object_id") != acquired.get("source_object_id"):
        errors.append(f"{iid}: annotation source object differs from acquisition")

    mapping_ids = {record.get("identity_id") for record in mappings.get("records", [])}
    for sign in annotation.get("signs", []):
        ref = sign.get("allograph_ref")
        if ref and ref not in mapping_ids:
            errors.append(f"{iid}: DATA-004 allograph reference {ref} is absent from DATA-005")

    alignment_map = _map_by(alignments.get("alignments", []), "alignment_id")
    if not set(row["alignment_ids"]) <= alignment_map.keys():
        errors.append(f"{iid}: DATA-006 alignment ID reference is broken")
    selected_alignments = [alignment_map[x] for x in row["alignment_ids"] if x in alignment_map]
    if any(x.get("page_id") != row["page_id"] for x in selected_alignments):
        errors.append(f"{iid}: selected DATA-006 alignment belongs to another page")
    gold_alignments = [x for x in selected_alignments if eligibility.get(x["alignment_id"], False)]
    if not gold_alignments and release_kind == "corpus_v1_release":
        errors.append(f"{iid}: no expert-reviewed, unambiguous, scoring-eligible gold alignment")

    review_map = _map_by(reviews.get("cases", []), "case_id")
    if not set(row["review_case_ids"]) <= review_map.keys():
        errors.append(f"{iid}: DATA-007 review case reference is broken")
    selected_cases = [review_map[x] for x in row["review_case_ids"] if x in review_map]
    if any(case.get("target_id") not in {t["target_id"] for a in selected_alignments for t in a.get("targets", [])} for case in selected_cases):
        errors.append(f"{iid}: DATA-007 review case target is inconsistent with selected alignment targets")
    if release_kind == "corpus_v1_release" and any(case.get("case_state") not in {"consensus", "adjudicated", "closed"} for case in selected_cases):
        errors.append(f"{iid}: unresolved DATA-007 disagreement is excluded from production gold")
    if release_kind == "corpus_v1_release":
        scored_targets = {target["target_id"] for item in gold_alignments for target in item.get("targets", [])}
        reviewed_targets = {case.get("target_id") for case in selected_cases if case.get("case_state") in {"consensus", "adjudicated", "closed"}}
        if not scored_targets <= reviewed_targets:
            errors.append(f"{iid}: expert-review coverage is insufficient for scoring-eligible gold targets")

    split_rows = _map_by(split_manifest.get("assignments", []), "item_id")
    split_row = split_rows.get(row["split_item_id"])
    metadata_rows = _map_by(split_metadata.get("items", []), "item_id")
    metadata_row = metadata_rows.get(row["split_item_id"])
    if split_row is None or metadata_row is None:
        errors.append(f"{iid}: EVAL-004 split assignment or metadata item is missing")
    else:
        if split_row.get("partition") not in {"train", "dev", "test"}:
            errors.append(f"{iid}: EVAL-004 item is not assigned to train/dev/test")
        if split_row.get("document_id") != row["document_id"] or split_row.get("page_id") != row["page_id"]:
            errors.append(f"{iid}: document/page identity disagrees with EVAL-004")
        if (split_row.get("source_id"), split_row.get("source_object_id")) != (source_id, acquired.get("source_object_id")):
            errors.append(f"{iid}: source identity disagrees with EVAL-004")
        if split_row.get("benchmark_quarantine") or metadata_row.get("benchmark_quarantine"):
            errors.append(f"{iid}: EVAL-004 benchmark-quarantined item cannot be released")
        if release_kind == "corpus_v1_release":
            errors.extend(production_authority_gate(None, None))
            for field in ("document_id", "page_id", "source_object_id", "image_sha256", "normalized_sha256"):
                if not metadata_row.get(field):
                    errors.append(f"{iid}: production split metadata lacks required leakage identity {field}")
            if metadata_row.get("benchmark_overlap_review", {}).get("status") != "clear":
                errors.append(f"{iid}: production split metadata requires reviewed clear benchmark overlap")
            if acquired.get("redistribution_requested") is not True or source.get("redistribution_use") != "allowed":
                errors.append(f"{iid}: production release lacks a source-registry record marked allowed for redistribution")
            if source.get(f"{acquired.get('intended_use')}_use") != "allowed" or acquired.get("source_rights_snapshot", {}).get("use_decision") != "allowed":
                errors.append(f"{iid}: production training use is not marked allowed in the source-rights snapshot")
            if acquired.get("acquisition_status") != "complete":
                errors.append(f"{iid}: production input is not a completed DATA-002 acquisition")
            for label, permission, evidence in (
                ("annotation training", row["annotation_training_permission"], row["annotation_rights_evidence_ref"]),
                ("annotation redistribution", row["annotation_redistribution_permission"], row["annotation_rights_evidence_ref"]),
                ("mapping training", row["mapping_training_permission"], row["mapping_rights_evidence_ref"]),
                ("mapping redistribution", row["mapping_redistribution_permission"], row["mapping_rights_evidence_ref"]),
            ):
                if permission != "allowed" or evidence.startswith(("synthetic:", "synthetic://")):
                    errors.append(f"{iid}: {label} permission lacks an allowed claim and a non-synthetic evidence reference")
            if authorization_evidence is None:
                errors.append(f"{iid}: signed independent authorization evidence is missing")
            else:
                try:
                    annotation_path = safe_path(base, row["annotation_path"])
                    mapping_path = safe_path(base, row["mapping_path"])
                    alignment_path = safe_path(base, row["alignment_path"])
                    review_path = safe_path(base, row["review_path"])
                    split_path = safe_path(base, bundle["split_manifest_path"])
                    annotation_hash = digest(annotation_path.read_bytes())
                    mapping_hash = digest(mapping_path.read_bytes())
                    alignment_hash = digest(alignment_path.read_bytes())
                    review_hash = digest(review_path.read_bytes())
                    split_hash = digest(split_path.read_bytes())
                    source_object = acquired.get("source_object_id")
                    expected_assets = {
                        "original_image": (str(row["item_id"]), str(acquired.get("actual_sha256") or "")),
                        "derived_image": (str(row["preprocessing_item_id"]), str(art_item.get("output_sha256") or "") if art_item else ""),
                        "diplomatic_transcription": (str(annotation.get("annotation_id") or ""), annotation_hash),
                        "transliteration": (str(annotation.get("annotation_id") or ""), annotation_hash),
                        "hieroglyphic_rendering": (str(annotation.get("annotation_id") or ""), annotation_hash),
                        "sign_mapping": (str(mappings.get("mapping_set_id") or ""), mapping_hash),
                        "expert_gold": (str(alignments.get("alignment_set_id") or "") + ":" + str(reviews.get("review_set_id") or ""), digest(canonical([alignment_hash, review_hash]))),
                    }
                    expected_graph_hashes = {
                        "image_exposure": str(acquired.get("actual_sha256") or ""),
                        "original_image": str(acquired.get("actual_sha256") or ""),
                        "preprocessing": str(art_item.get("output_sha256") or "") if art_item else "",
                        "annotation": annotation_hash,
                        "alignment": alignment_hash,
                        "expert_review": review_hash,
                        "split": split_hash,
                    }
                    trust_store = read_document(TRUST_ANCHORS)
                    pinned_roster = split_manifest.get("benchmark_overlap_policy", {}).get("roster", {}).get("version")
                    authorization_errors = validate_admission_evidence(
                        authorization_evidence, trust_store, source_id=str(source_id),
                        source_object_id=str(source_object), item_id=str(iid),
                        expected_assets=expected_assets, expected_hashes=expected_graph_hashes,
                        expected_roster_version=pinned_roster,
                        expected_source_record_sha256=digest(canonical(source)),
                    )
                    errors.extend(f"{iid}: {message}" for message in authorization_errors)
                except (OSError, ReleaseError, KeyError, TypeError, ValueError) as exc:
                    errors.append(f"{iid}: authorization evidence could not be bound to exact inputs: {exc}")

    if split_row and art_item:
        if split_row.get("image_sha256") and acquired.get("actual_sha256") and split_row["image_sha256"].lower() != acquired["actual_sha256"].lower():
            errors.append(f"{iid}: EVAL-004 original image hash differs from DATA-002")
        if split_row.get("normalized_sha256") and art_item.get("output_sha256") and split_row["normalized_sha256"].lower() != art_item["output_sha256"].lower():
            errors.append(f"{iid}: EVAL-004 normalized hash differs from DATA-003")

    if acquired.get("is_synthetic_fixture") and release_kind != "synthetic_test_release":
        errors.append(f"{iid}: synthetic fixture cannot be labeled a production corpus_v1_release")
    if not acquired.get("is_synthetic_fixture") and release_kind == "synthetic_test_release":
        errors.append(f"{iid}: synthetic_test_release cannot disguise real source assets")

    target_annotations = []
    for alignment_record in selected_alignments:
        target_rows = []
        for target in alignment_record.get("targets", []):
            data = _target_annotation(annotation, target["target_type"], target["target_id"])
            if data is None:
                errors.append(f"{iid}: unable to export annotation target {target['target_type']}:{target['target_id']}")
            target_rows.append({**target, "annotation": data})
        target_annotations.append({"alignment": copy.deepcopy(alignment_record), "targets": target_rows})
    artifact_hash = art_item.get("output_sha256") if art_item else None
    record = {
        "item_id": iid,
        "document_id": row["document_id"],
        "page_id": row["page_id"],
        "partition": split_row.get("partition") if split_row else None,
        "source_id": source_id,
        "source_object_id": acquired.get("source_object_id"),
        "institutional_accession": (authorization_evidence or {}).get("decision", {}).get("institutional_accession"),
        "manuscript_group_id": (authorization_evidence or {}).get("decision", {}).get("manuscript_group_id"),
        "fragment_ids": copy.deepcopy((authorization_evidence or {}).get("decision", {}).get("fragment_ids", [])),
        "side_ids": copy.deepcopy((authorization_evidence or {}).get("decision", {}).get("side_ids", [])),
        "scribe_group": (authorization_evidence or {}).get("decision", {}).get("scribe_group"),
        "rights_class": source.get("rights_class"),
        "training_permission": source.get("training_use"),
        "redistribution_permission": source.get("redistribution_use"),
        "intended_use": acquired.get("intended_use"),
        "required_attribution": source.get("attribution_requirements"),
        "source_rights_evidence_urls": source.get("rights_evidence_urls", []),
        "rights_provenance": {"source_registry_record": copy.deepcopy(source), "acquisition_record": copy.deepcopy(acquired)},
        "authorization_evidence_summary": _public_authorization_summary(authorization_evidence),
        "provenance_graph_summary": _public_provenance_summary((authorization_evidence or {}).get("provenance_graph")),
        "benchmark_overlap_state": (authorization_evidence or {}).get("benchmark_overlap", {}).get("state", "not_yet_reviewed"),
        "annotation_training_permission": row["annotation_training_permission"],
        "annotation_redistribution_permission": row["annotation_redistribution_permission"],
        "annotation_rights_evidence_ref": row["annotation_rights_evidence_ref"],
        "mapping_training_permission": row["mapping_training_permission"],
        "mapping_redistribution_permission": row["mapping_redistribution_permission"],
        "mapping_rights_evidence_ref": row["mapping_rights_evidence_ref"],
        "original_sha256": acquired.get("actual_sha256"),
        "preprocessed_sha256": artifact_hash,
        "preprocessed_artifact_ref": {"artifact_manifest": row["preprocessing_artifact_manifest_path"],
                                      "dataset_version_id": artifact_manifest.get("dataset_version_id"),
                                      "path": art_item.get("output_path") if art_item else None,
                                      "sha256": artifact_hash},
        "annotation_id": annotation.get("annotation_id"),
        "annotation_provenance": {"provenance": copy.deepcopy(annotation.get("provenance")), "document": copy.deepcopy(annotation.get("document"))},
        "mapping_set_id": mappings.get("mapping_set_id"),
        "mapping_records": copy.deepcopy(mappings.get("records", [])),
        "mapping_relations": copy.deepcopy(mappings.get("relations", [])),
        "alignment_set_id": alignments.get("alignment_set_id"),
        "review_set_id": reviews.get("review_set_id"),
        "gold_alignment_ids": sorted(x["alignment_id"] for x in gold_alignments),
        "target_annotations": target_annotations,
        "review_case_ids": sorted(row["review_case_ids"]),
        "review_cases": [_public_review_case(case) for case in selected_cases],
        "split_assignment": copy.deepcopy(split_row),
        "gold_statuses": sorted({
            target.get("gold_status", "unknown")
            for target in annotation.get("lines", []) if target.get("line_id") in {t.get("target_id") for a in selected_alignments for t in a.get("targets", [])}
        }),
        "review_disagreement_count": sum(bool(case.get("disagreement")) for case in review_report.get("cases", [])) if isinstance(review_report, dict) else 0,
        "synthetic": bool(acquired.get("is_synthetic_fixture")),
    }
    return record, errors


def validate_bundle(bundle: Any, bundle_path: Path) -> tuple[dict[str, Any], list[str]]:
    errors = _schema_errors(bundle, SCHEMA, "bundle")
    if errors:
        return {}, errors
    base = bundle_path.resolve(strict=True).parent
    registry = source_registry.load_yaml(REGISTRY)
    registry_errors = source_registry.validate_registry_data(registry, read_document(ROOT / "schemas/data_sources.schema.json"))
    errors.extend(f"DATA-001 registry: {e}" for e in registry_errors)
    audit: list[dict[str, str]] = []
    try:
        metadata, _ = _read_checked(base, bundle["split_metadata_path"], audit)
        split_manifest, _ = _read_checked(base, bundle["split_manifest_path"], audit)
    except ReleaseError as exc:
        return {}, [str(exc)]
    profiles = read_document(SPLIT_PROFILES)
    errors.extend(f"EVAL-004 metadata: {e}" for e in split_system._validate_metadata(metadata, registry, profiles))
    errors.extend(f"EVAL-004 split: {e}" for e in split_system.validate_manifest(split_manifest, metadata, profiles, read_document(SPLIT_SCHEMA), registry))
    seen: set[str] = set()
    records = []
    for row in bundle["items"]:
        if row["item_id"] in seen:
            errors.append(f"duplicate release item_id: {row['item_id']}")
        seen.add(row["item_id"])
        record, row_errors = _validate_source(bundle, row, base, registry, metadata, split_manifest, profiles, audit, bundle["release_kind"])
        if record:
            records.append(record)
        errors.extend(row_errors)

    included_ids = {record["item_id"] for record in records}
    split_map = _map_by(split_manifest.get("assignments", []), "item_id")
    for partition in ("train", "dev", "test"):
        split_ids = {iid for iid, row in split_map.items() if row.get("partition") == partition}
        if not split_ids <= included_ids:
            errors.append(f"release omits EVAL-004 {partition} assignments: {', '.join(sorted(split_ids - included_ids))}")
        if bundle["release_kind"] == "corpus_v1_release" and not any(row.get("partition") == partition for row in records):
            errors.append(f"production release has an empty {partition} partition")
    if bundle["release_kind"] == "corpus_v1_release" and any(record.get("synthetic") for record in records):
        errors.append("synthetic input cannot be represented as a real corpus_v1_release")
    if bundle["release_kind"] == "corpus_v1_release" and not records:
        errors.append("production corpus has no items passing the configured rights gates")

    # Leakage checks are repeated at release time, including reviewed near duplicates.
    active = [r for r in records if r.get("partition") in {"train", "dev", "test"}]
    for field in ("source_object_id", "document_id", "page_id", "institutional_accession", "manuscript_group_id", "original_sha256", "preprocessed_sha256"):
        places: dict[str, set[str]] = {}
        for record in active:
            value = record.get(field)
            if value:
                places.setdefault(str(value).lower(), set()).add(record["partition"])
        for value, partitions in places.items():
            if len(partitions) > 1:
                errors.append(f"release leakage: {field} {value} crosses partitions {sorted(partitions)}")
    for field in ("fragment_ids", "side_ids"):
        memberships: dict[str, set[str]] = {}
        for record in active:
            for identity_value in record.get(field, []):
                memberships.setdefault(str(identity_value), set()).add(record["partition"])
        for identity_value, partitions in memberships.items():
            if len(partitions) > 1:
                errors.append(f"release leakage: {field} identity {identity_value} crosses partitions {sorted(partitions)}")
    queue = split_manifest.get("near_duplicate_review_queue", [])
    for pair in queue:
        if pair.get("review_status") == "pending":
            errors.append(f"release blocked by unresolved near-duplicate review: {pair.get('left_item_id')} / {pair.get('right_item_id')}")
        if pair.get("review_status") == "same_content":
            left, right = split_map.get(pair.get("left_item_id"), {}), split_map.get(pair.get("right_item_id"), {})
            if left.get("partition") != right.get("partition"):
                errors.append("release leakage: reviewed near-duplicate pair crosses partitions")

    unique_inputs = sorted({x["path"]: x for x in audit}.values(), key=lambda x: x["path"])
    if sum(item["size_bytes"] for item in unique_inputs) > MAX_RELEASE_BYTES:
        errors.append(f"combined unique release inputs exceed {MAX_RELEASE_BYTES} byte limit")
    excluded_items = sorted(({"item_id": row["item_id"], "reason": row.get("exclusion_reason")} for row in split_manifest.get("assignments", []) if row.get("partition") == "excluded"), key=lambda x: x["item_id"])
    identity = {"release_id": bundle["release_id"], "release_kind": bundle["release_kind"], "generator": GENERATOR,
                "inputs": unique_inputs, "items": sorted(records, key=lambda x: x["item_id"]), "excluded_items": excluded_items,
                "split_statistics": copy.deepcopy(split_manifest.get("statistics", {})), "split_warnings": sorted(split_manifest.get("warnings", [])),
                "split_version": split_manifest.get("split_version"), "split_profile_id": split_manifest.get("profile_id")}
    release = {"schema_version": "1.0.0", **identity,
               "dataset_version_id": "corpus-" + digest(canonical(identity)),
               "partition_counts": {p: sum(r.get("partition") == p for r in records) for p in ("train", "dev", "test")}
               | {"excluded": len(excluded_items)}}
    output_schema = read_document(SCHEMA)["$defs"]["releaseManifest"]
    output_errors = sorted(Draft202012Validator(output_schema, format_checker=FormatChecker()).iter_errors(release), key=lambda e: str(e.absolute_path))
    errors.extend(f"release{''.join(f'[{part!r}]' for part in err.absolute_path)}: {err.message}" for err in output_errors)
    errors = sorted(set(errors))
    if errors:
        return {}, errors
    return {"release": release, "errors": [], "audit": unique_inputs}, []


def _candidate_benchmark_state(candidate: dict[str, Any], crosswalk: dict[str, Any] | None) -> tuple[str, list[str]]:
    """Use R-017 literal metadata crosswalk as risk evidence, never as clearance."""
    if not crosswalk:
        return "not_yet_reviewed", ["R-017 candidate crosswalk is missing; benchmark/source independence is unreviewed"]
    exact = crosswalk.get("exact_public_source_metadata_matches", [])
    nearby = int(crosswalk.get("nearby_collection_witness_count", 0))
    reasons = ["R-017 covers pinned public metadata only; no direct string match does not establish independence",
               "institutional alias, joined-fragment, edition, image-hash and perceptual-duplicate reviews remain pending"]
    if exact:
        reasons.append(f"R-017 reports {len(exact)} literal source metadata match(es); independent exclusion review required")
        return "confirmed_overlap", reasons
    if nearby:
        reasons.append(f"R-017 identifies {nearby} nearby benchmark witnesses in this institutional collection")
        return "potential_overlap", reasons
    return "not_yet_reviewed", reasons


def build_readiness_assessment(bundle_path: Path, roster_path: Path = R016_ROSTER,
                               benchmark_path: Path = ROOT / "eval/benchmarks/hieraticbench/manifest.yaml") -> tuple[dict[str, Any], str]:
    """Report evidence readiness without inventing adequacy thresholds."""
    bundle_path = bundle_path.resolve(strict=True)
    roster_path = roster_path.resolve(strict=True)
    bundle = read_document(bundle_path)
    result, validation_errors = validate_bundle(bundle, bundle_path)
    roster = read_document(roster_path)
    benchmark = read_document(benchmark_path) if benchmark_path.exists() else {}
    crosswalk_path = R017_CROSSWALK
    metadata_path = R017_METADATA
    crosswalk_doc = read_document(crosswalk_path) if crosswalk_path.exists() else {}
    crosswalk_rows = crosswalk_doc.get("candidates", []) if isinstance(crosswalk_doc, dict) else []
    crosswalk_by_id = {row.get("candidate_id"): row for row in crosswalk_rows if isinstance(row, dict)}
    crosswalk_errors = []
    if not crosswalk_doc:
        crosswalk_errors.append("R-017 public benchmark candidate crosswalk is missing")
    elif crosswalk_doc.get("upstream_revision") != roster.get("benchmark_version"):
        crosswalk_errors.append("R-017 candidate crosswalk is not pinned to the R-016 benchmark revision")
    if len(crosswalk_by_id) != len(crosswalk_rows) or set(crosswalk_by_id) != {row.get("candidate_id") for row in roster.get("candidates", [])}:
        crosswalk_errors.append("R-017 candidate crosswalk has duplicate, missing, or extra R-016 candidate identities")
    if any(row.get("training_admission") != "BLOCKED" or row.get("rights_status") != "NOT_CLEARED" for row in crosswalk_rows if isinstance(row, dict)):
        crosswalk_errors.append("R-017 candidate status no longer fails closed for training and rights admission")
    if not isinstance(crosswalk_doc.get("excluded_sealed_files_count"), int) or crosswalk_doc.get("excluded_sealed_files_count", 0) < 1 or not crosswalk_doc.get("strong_caveat"):
        crosswalk_errors.append("R-017 sealed-answer exclusion count or non-clearance caveat is missing")
    metadata_rows: list[dict[str, Any]] = []
    try:
        raw_metadata = metadata_path.read_bytes()
        if len(raw_metadata) > MAX_INPUT_BYTES:
            raise ReleaseError("R-017 public metadata register exceeds input size limit")
        metadata_rows = [json.loads(line) for line in raw_metadata.decode("utf-8").splitlines() if line.strip()]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ReleaseError) as exc:
        crosswalk_errors.append(f"R-017 public metadata register cannot be read safely: {exc}")
    permitted_metadata_fields = {"id", "upstream_path", "object_name", "object_holder", "source_url", "source_file_url", "license_claim", "source_group", "provenance_review", "corpus_status"}
    if not metadata_rows or len(metadata_rows) != crosswalk_doc.get("public_sources_screened"):
        crosswalk_errors.append("R-017 public metadata register row count differs from its crosswalk census")
    if any(not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row.get("id") for row in metadata_rows) or len({row.get("id") for row in metadata_rows}) != len(metadata_rows):
        crosswalk_errors.append("R-017 public metadata register contains duplicate or missing item identities")
    if any(not isinstance(row, dict) or set(row) - permitted_metadata_fields or row.get("provenance_review") != "metadata_only" or row.get("corpus_status") != "QUARANTINE_EVAL_ONLY" or str(row.get("id", "")).startswith("hb-") for row in metadata_rows):
        crosswalk_errors.append("R-017 metadata contains unapproved fields or a non-quarantined/non-metadata-only record")
    family_counts: dict[str, int] = {}
    for row in metadata_rows:
        if not isinstance(row, dict):
            continue
        family = str(row.get("id", "")).split("-", 1)[0]
        family_counts[family] = family_counts.get(family, 0) + 1
    registry = read_document(REGISTRY)
    rights_inventory_path = ROOT / "data/releases/rights-readiness.yaml"
    rights_inventory = read_document(rights_inventory_path)
    release = result.get("release", {})
    records = release.get("items", [])
    real = [item for item in records if not item.get("synthetic")]
    synthetic = [item for item in records if item.get("synthetic")]
    split_counts = {part: len({item.get("document_id") for item in real if item.get("partition") == part}) for part in ("train", "dev", "test")}
    def counts(field: str) -> dict[str, int]:
        values: dict[str, int] = {}
        for item in real:
            provenance = item.get("annotation_provenance", {}).get("document", {})
            value = provenance.get(field) or "unknown"
            values[str(value)] = values.get(str(value), 0) + 1
        return dict(sorted(values.items()))
    candidate_rows = []
    common_gates = list(roster.get("common_unresolved_gates", []))
    for candidate in roster.get("candidates", []):
        crosswalk_row = crosswalk_by_id.get(candidate.get("candidate_id"))
        overlap_state, overlap_reasons = _candidate_benchmark_state(candidate, crosswalk_row)
        blockers = ["candidate roster is metadata-only and does not grant use or acquisition permission", *common_gates, *overlap_reasons]
        if not candidate.get("image_pixels_verified"):
            blockers.append("exact institutional image bytes and original hash have not been verified")
        if not candidate.get("editorial_text_rights_verified"):
            blockers.append("diplomatic/transliteration/editorial-text rights are not verified")
        if not candidate.get("full_source_lineage_checked"):
            blockers.append("object, manuscript, fragment, side and exposure lineage is incomplete")
        if not candidate.get("expert_gold_verified"):
            blockers.append("independent expert-reviewed line/sign gold is unavailable")
        candidate_rows.append({"candidate_id": candidate["candidate_id"], "overlap_state": overlap_state, "admission_status": "blocked",
                               "exact_public_source_metadata_match_count": len((crosswalk_row or {}).get("exact_public_source_metadata_matches", [])),
                               "nearby_collection_witness_count": int((crosswalk_row or {}).get("nearby_collection_witness_count", 0)),
                               "source_lineage_status": (crosswalk_row or {}).get("source_lineage_status", "UNREVIEWED"),
                               "rights_status": (crosswalk_row or {}).get("rights_status", "UNREVIEWED"),
                               "image_equivalence_status": (crosswalk_row or {}).get("image_equivalence_status", "UNREVIEWED"),
                               "blockers": sorted(set(blockers))})
    trust_errors = validate_trust_store(read_document(TRUST_ANCHORS))
    blockers = [*validation_errors, *trust_errors, *crosswalk_errors, PRODUCTION_AUTHORIZATION_BLOCKER]
    if not real:
        blockers.append("no real items passed corpus admission; the accepted example is synthetic infrastructure evidence only")
    trust = read_document(TRUST_ANCHORS)
    if not trust.get("anchors"):
        blockers.append("no signing-key metadata is configured; repository metadata cannot establish an external trust root")
    if any(row["admission_status"] == "blocked" for row in candidate_rows):
        blockers.append(f"{sum(row['admission_status'] == 'blocked' for row in candidate_rows)} R-016 discovery candidates remain blocked")
    statuses = set()
    for item in real:
        statuses.update(item.get("gold_statuses", []))
    dimension_report = {
        "source_registry_rights": [{"source_id": source.get("source_id"), "name": source.get("name"),
                                    "rights_class": source.get("rights_class"), "training_use": source.get("training_use"),
                                    "development_use": source.get("development_use"), "redistribution_use": source.get("redistribution_use"),
                                    "benchmark_quarantine": source.get("benchmark_quarantine"),
                                    "rights_evidence_urls": source.get("rights_evidence_urls", [])}
                                   for source in registry.get("sources", [])],
        "rights_readiness_inventory": {"production_corpus_status": rights_inventory.get("production_corpus_status"),
                                       "rights_granted": rights_inventory.get("rights_granted"),
                                       "assets_downloaded": rights_inventory.get("assets_downloaded"),
                                       "production_corpus_exists": rights_inventory.get("production_corpus_exists"),
                                       "global_missing_evidence": rights_inventory.get("global_missing_evidence", [])},
        "benchmark_source_metadata_screen": {"upstream_revision": crosswalk_doc.get("upstream_revision"),
                                              "public_metadata_records": len(metadata_rows),
                                              "unique_public_source_ids": len({row.get("id") for row in metadata_rows}),
                                              "excluded_sealed_files_count": crosswalk_doc.get("excluded_sealed_files_count"),
                                              "source_family_counts": dict(sorted(family_counts.items())),
                                              "records_admitted_for_training": 0,
                                              "gold_or_images_copied": False},
        "period": counts("period"),
        "writing_media": counts("material_support"),
        "genres": counts("genre_register"),
        "annotation_granularity": {"sign_level_items": sum(any(target.get("target_type") == "sign" for group in x.get("target_annotations", []) for target in group.get("targets", [])) for x in real), "line_level_items": sum(any(target.get("target_type") == "line" for group in x.get("target_annotations", []) for target in group.get("targets", [])) for x in real)},
        "reviewer_coverage": {"items": len(real), "reviewed_items": sum(bool(x.get("review_cases")) for x in real),
                              "unique_reviewers": None, "reviewer_identity_visibility": "redacted_from_public_release"},
        "ambiguity": {"items_with_uncertain_gold": sum(any(v in {"uncertain_with_alternatives", "adjudication_pending"} for v in x.get("gold_statuses", [])) for x in real)},
        "disagreement": {"review_cases_with_disagreement": sum(x.get("review_disagreement_count", 0) for x in real)},
        "missing_or_illegible_gold": {"items": sum(any(v in {"missing_annotation", "illegible_unscorable"} for v in x.get("gold_statuses", [])) for x in real), "observed_statuses": sorted(statuses & {"missing_annotation", "illegible_unscorable"})},
        "missing_provenance": {"items": sum(not x.get("source_object_id") or not x.get("original_sha256") for x in real)},
        "incomplete_rights": {"items": sum(not x.get("authorization_receipt_id") for x in real)},
        "unresolved_overlap": {"items": sum(x.get("benchmark_overlap_state") != "independently_cleared" for x in real)},
        "cross_partition_source_or_group_overlap": {"items": 0 if not validation_errors else None, "validation_errors": [e for e in validation_errors if "leakage" in e or "overlap" in e]},
    }
    identity = {"bundle_sha256": digest(bundle_path.read_bytes()), "roster_sha256": digest(roster_path.read_bytes()),
                "r017_crosswalk_sha256": digest(crosswalk_path.read_bytes()) if crosswalk_path.exists() else None,
                "r017_metadata_sha256": digest(metadata_path.read_bytes()) if metadata_path.exists() else None,
                "registry_sha256": digest(REGISTRY.read_bytes()), "rights_inventory_sha256": digest(rights_inventory_path.read_bytes()),
                "benchmark_pinned_commit": roster.get("benchmark_version"), "generator": "hieratic-corpus-readiness/1.0.0"}
    assessment = {
        "schema_version": "1.0.0", "assessment_id": "readiness-" + digest(canonical(identity)), "as_of": str(roster.get("as_of", "1970-01-01")),
        "software_integrity": "PASS" if not validation_errors and not trust_errors and not crosswalk_errors else "FAIL", "evidence_admission": "BLOCKED", "scientific_corpus_adequacy": "INDEPENDENT_REVIEW_REQUIRED",
        "cohort": {"real_items": len(real), "synthetic_items": len(synthetic), "unique_manuscript_groups": len({x.get("document_id") for x in real}), "unique_source_objects": len({x.get("source_object_id") for x in real}), "partition_document_group_counts": split_counts},
        "dimensions": dimension_report, "benchmark_candidates": candidate_rows, "blockers": sorted(set(blockers)), "thresholds_invented": False,
        "source_references": ["data/sources/registry.yaml", "data/releases/rights-readiness.yaml", "docs/research/R017_PUBLIC_BENCHMARK_LINEAGE_AUDIT.md",
                              "docs/research/R017_R016_CANDIDATE_SOURCE_CROSSWALK.json",
                              "docs/research/R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl",
                              str(roster_path.relative_to(ROOT)) if roster_path.is_relative_to(ROOT) else "external metadata roster",
                              str(benchmark_path.relative_to(ROOT)) if benchmark_path.is_relative_to(ROOT) else "pinned benchmark metadata"],
    }
    schema = read_document(READINESS_SCHEMA)
    errors = _schema_errors_against(assessment, schema, "readiness assessment")
    if errors:
        raise ReleaseError("\n".join(errors))
    report = ["# DATA-008 corpus readiness assessment", "", f"- Assessment: `{assessment['assessment_id']}`", f"- As of: {assessment['as_of']}", f"- Software integrity: **{assessment['software_integrity']}**", f"- Evidence admission: **{assessment['evidence_admission']}**", f"- Scientific adequacy: **{assessment['scientific_corpus_adequacy']}**", "", "## Cohort", "", f"- Real admitted items: {assessment['cohort']['real_items']}", f"- Synthetic fixture items: {assessment['cohort']['synthetic_items']}", f"- Unique real manuscript groups: {assessment['cohort']['unique_manuscript_groups']}", f"- Unique real source objects: {assessment['cohort']['unique_source_objects']}", "- Real partition document groups: " + ", ".join(f"{p}={n}" for p, n in split_counts.items()), "", "## R-016 candidates screened against R-017", "", f"R-017 screened {len(metadata_rows)} pinned public source metadata records; sealed records excluded: {crosswalk_doc.get('excluded_sealed_files_count', 0)}. This is a literal metadata comparison only; zero direct matches do not establish source independence, image equivalence, or permission. Every candidate remains blocked.", "", "| Candidate | Overlap state | Nearby collection witnesses | Exact metadata matches | Rights / image | Admission | Open gates |", "|---|---|---:|---:|---|---|---|"]
    for row in candidate_rows:
        report.append(f"| {row['candidate_id']} | {row['overlap_state']} | {row['nearby_collection_witness_count']} | {row['exact_public_source_metadata_match_count']} | {row['rights_status']} / {row['image_equivalence_status']} | {row['admission_status']} | {len(row['blockers'])} |")
    report.extend(["", "## Readiness dimensions", "", "```json", json.dumps(dimension_report, ensure_ascii=False, sort_keys=True, indent=2), "```", "", "## Blockers", ""])
    report.extend(f"- {reason}" for reason in assessment["blockers"])
    report.extend(["", "No minimum sample-size threshold was invented. Software integrity, evidence admission, and scientific adequacy are separate decisions. This report is not a rights determination or corpus release.", ""])
    return assessment, "\n".join(report)


def _write_report_no_clobber(path: Path, content: bytes) -> None:
    path = Path(os.path.abspath(path))
    parent = path.parent
    cursor = parent
    while cursor != cursor.parent:
        if cursor.is_symlink():
            raise ReleaseError("report output cannot traverse a symlink")
        cursor = cursor.parent
    if path.exists() or path.is_symlink():
        raise ReleaseError(f"report destination already exists: {path}")
    parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=parent, delete=False) as stream:
            temp_name = stream.name; stream.write(content); stream.flush(); os.fsync(stream.fileno())
        try:
            os.link(temp_name, path)
        except FileExistsError as exc:
            raise ReleaseError("report destination appeared during write; refusing overwrite") from exc
        Path(temp_name).unlink(); temp_name = None
    finally:
        if temp_name and Path(temp_name).exists():
            Path(temp_name).unlink()


def _dataset_card(release: dict[str, Any]) -> str:
    synthetic = release["release_kind"] == "synthetic_test_release"
    return "\n".join([
        "# Hieratic AI corpus release card", "", f"- Release ID: `{release['release_id']}`",
        f"- Dataset version: `{release['dataset_version_id']}`", f"- Release kind: `{release['release_kind']}`",
        f"- Items indexed: {len(release['items'])}", f"- Partitions: train {release['partition_counts']['train']}, dev {release['partition_counts']['dev']}, test {release['partition_counts']['test']}, excluded {release['partition_counts']['excluded']}",
        f"- Data status: {'synthetic structural fixture only; not a licensed production corpus' if synthetic else 'production release; each item has passed release-time rights and leakage checks'}",
        "- Included source bytes: none; artifacts are referenced by immutable hash and remain in their DATA-003 artifact store.",
        "- Gold: only reviewed, unambiguous DATA-006 alignments are included in the gold ID index; missing, uncertain, disputed, damaged, restored, or unreviewed readings remain metadata and are not coerced.",
        "- Rights: item-level evidence, permissions, and required attribution are preserved in the release manifest; this card does not grant permission.",
        "- Exclusions: evaluation-only, quarantined, unknown-rights, unresolved-overlap, and unresolved near-duplicate items are refused.",
        "- Limitations: no model training or performance claim is made by corpus assembly.", ""
    ])


def _write_staging_file(staging: Path, staging_fd: int | None, name: str, content: bytes) -> None:
    """Write one exclusive staging file, refusing symlink or pre-existing entries."""
    if staging_fd is None:
        # Windows has no dir_fd support in Python's os.open. The staging name is
        # private and newly-created; os.rename below supplies the no-clobber commit.
        with (staging / name).open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        return
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(name, flags, 0o600, dir_fd=staging_fd)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _open_linux_directory_without_symlinks(path: Path) -> int:
    """Open each absolute path component without following symlinks (Linux)."""
    absolute = Path(os.path.abspath(path))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    current_fd = os.open(absolute.anchor, flags)
    try:
        for component in absolute.parts[1:]:
            try:
                next_fd = os.open(component, flags, dir_fd=current_fd)
            except OSError as exc:
                try:
                    mode = os.stat(component, dir_fd=current_fd, follow_symlinks=False).st_mode
                except OSError:
                    raise exc
                if stat.S_ISLNK(mode):
                    raise ReleaseError("release output cannot traverse a symlink") from exc
                raise
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def _rename_linux_noreplace(parent_fd: int, staging_name: str, output_name: str) -> None:
    """Atomically rename a complete directory only if the name is still absent."""
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise ReleaseError("Linux renameat2(RENAME_NOREPLACE) is required for safe release publication")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    # Linux UAPI: include/uapi/linux/fs.h
    rename_noreplace = 1
    result = renameat2(parent_fd, os.fsencode(staging_name), parent_fd, os.fsencode(output_name), rename_noreplace)
    if result == 0:
        return
    error = ctypes.get_errno()
    if error in (errno.EEXIST, errno.ENOTEMPTY):
        raise ReleaseError("release destination already exists; immutable releases are never replaced")
    if error in (errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP):
        raise ReleaseError("filesystem does not support atomic no-replace directory publication")
    raise OSError(error, os.strerror(error), output_name)


def _verify_linux_parent_path(path: Path, parent_fd: int) -> None:
    """Fail if the caller's parent path was replaced after its fd was pinned."""
    opened = os.fstat(parent_fd)
    try:
        named = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise ReleaseError("release output parent path changed during publication") from exc
    if not stat.S_ISDIR(named.st_mode) or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
        raise ReleaseError("release output parent path changed during publication")


def _remove_published_linux_directory(parent_fd: int, name: str, published_fd: int) -> None:
    """Remove only our just-published inode, never a replacement at its name."""
    try:
        entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        inode = os.fstat(published_fd)
        if not stat.S_ISDIR(entry.st_mode) or (entry.st_dev, entry.st_ino) != (inode.st_dev, inode.st_ino):
            return
        for child in os.listdir(published_fd):
            os.unlink(child, dir_fd=published_fd)
        os.rmdir(name, dir_fd=parent_fd)
    except OSError:
        # A concurrent replacement is not ours to remove.
        return


def _publish_linux(files: dict[str, bytes], output: Path) -> None:
    """Stage through a pinned parent fd, then atomically publish without clobbering."""
    output_name = output.name
    if output_name in ("", ".", "..") or os.sep in output_name:
        raise ReleaseError("release output must name a new directory")
    parent_fd = _open_linux_directory_without_symlinks(output.parent)
    staging_name = f".{output_name}.staging-{secrets.token_hex(12)}"
    staging_fd: int | None = None
    staging_exists = False
    try:
        os.mkdir(staging_name, mode=0o700, dir_fd=parent_fd)
        staging_exists = True
        staging_fd = os.open(staging_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
        staging_path = output.parent / staging_name
        for name, content in files.items():
            _write_staging_file(staging_path, staging_fd, name, content)
        os.fsync(staging_fd)
        _verify_linux_parent_path(output.parent, parent_fd)
        # This is the single commit point. It is atomic, rejects every existing
        # entry (including an empty directory or symlink), and exposes only a
        # complete five-file release.
        _rename_linux_noreplace(parent_fd, staging_name, output_name)
        staging_exists = False
        try:
            _verify_linux_parent_path(output.parent, parent_fd)
        except ReleaseError:
            _remove_published_linux_directory(parent_fd, output_name, staging_fd)
            raise
        os.fsync(parent_fd)
    finally:
        if staging_fd is not None:
            if staging_exists:
                for name in os.listdir(staging_fd):
                    try:
                        os.unlink(name, dir_fd=staging_fd)
                    except OSError:
                        pass
            os.close(staging_fd)
        if staging_exists:
            try:
                os.rmdir(staging_name, dir_fd=parent_fd)
            except OSError:
                # Never follow or recursively remove a path that may have been
                # swapped by another process. A leftover private staging dir is
                # safer than touching an untrusted destination.
                pass
        os.close(parent_fd)


def _publish_windows(files: dict[str, bytes], output: Path) -> None:
    """Windows rename fails if the destination exists; stage beside the target."""
    parent = output.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ReleaseError("release output parent must already exist")
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=parent))
    try:
        for name, content in files.items():
            _write_staging_file(staging, None, name, content)
        # Unlike POSIX rename, Windows MoveFile semantics do not replace an
        # existing destination. This remains a no-clobber atomic directory move.
        os.rename(staging, parent / output.name)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _release_files(result: dict[str, Any], bundle_path: Path) -> dict[str, bytes]:
    if result.get("release", {}).get("release_kind") == "corpus_v1_release" and PRODUCTION_AUTHORIZATION_HARD_DISABLED:
        raise ReleaseError(PRODUCTION_AUTHORIZATION_BLOCKER)
    total = 0
    encoded_records = []
    for record in result["release"]["items"]:
        encoded_records.append(canonical(record) + b"\n")
    files = {
        "release-manifest.json": json.dumps(result["release"], ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n",
        "export.jsonl": b"".join(encoded_records),
        "dataset-card.md": _dataset_card(result["release"]).encode("utf-8"),
        "rejection-report.json": json.dumps({"excluded_split_items": result["release"]["excluded_items"], "reason": "excluded items retain EVAL-004 exclusion reasons and are absent from train/dev/test exports"}, sort_keys=True, indent=2).encode("utf-8") + b"\n",
        "audit-trail.json": json.dumps({"generator": GENERATOR, "bundle_sha256": digest(bundle_path.read_bytes()), "inputs": result["audit"], "release_sha256": digest(canonical(result["release"]))}, sort_keys=True, indent=2).encode("utf-8") + b"\n",
    }
    for content in files.values():
        total += len(content)
    if total > MAX_RELEASE_BYTES:
        raise ReleaseError(f"release output exceeds {MAX_RELEASE_BYTES} byte limit")
    return files


def audit_release(result: dict[str, Any], release_dir: Path, bundle_path: Path) -> list[str]:
    """Compare a published immutable release byte-for-byte with current inputs."""
    expected = _release_files(result, bundle_path)
    release_dir = Path(os.path.abspath(release_dir))
    errors: list[str] = []
    if release_dir.is_symlink() or not release_dir.is_dir():
        return ["release directory is missing, not a directory, or a symlink"]
    probe = release_dir
    while probe != probe.parent:
        if probe.is_symlink():
            return ["release path traverses a symlink"]
        probe = probe.parent
    try:
        found = {path.name for path in release_dir.iterdir()}
    except OSError as exc:
        return [f"cannot inspect release directory: {exc}"]
    if found != set(expected):
        errors.append(f"release file set differs: expected {sorted(expected)}, found {sorted(found)}")
    for name, content in expected.items():
        path = release_dir / name
        try:
            if path.is_symlink() or not path.is_file():
                errors.append(f"release artifact {name} is missing or is not a regular file")
            elif path.stat().st_size != len(content) or path.read_bytes() != content:
                errors.append(f"release artifact {name} differs from the deterministic build")
        except OSError as exc:
            errors.append(f"cannot read release artifact {name}: {exc}")
    return errors


def publish(result: dict[str, Any], output: Path, bundle_path: Path) -> None:
    if result.get("release", {}).get("release_kind") == "corpus_v1_release" and PRODUCTION_AUTHORIZATION_HARD_DISABLED:
        raise ReleaseError(PRODUCTION_AUTHORIZATION_BLOCKER)
    if result["errors"]:
        raise ReleaseError("release validation failed:\n" + "\n".join(result["errors"]))
    output = Path(os.path.abspath(output))
    if output.name in ("", ".", ".."):
        raise ReleaseError("release output must name a new directory")
    if not output.parent.exists() or not output.parent.is_dir():
        raise ReleaseError("release output parent must already exist")
    if sys.platform.startswith("linux"):
        if output.exists() or output.is_symlink():
            raise ReleaseError("release destination already exists; immutable releases are never replaced")
    elif os.name == "nt":
        probe = output.parent
        while probe != probe.parent:
            if probe.is_symlink():
                raise ReleaseError("release output cannot traverse a symlink")
            probe = probe.parent
        if output.exists() or output.is_symlink():
            raise ReleaseError("release destination already exists; immutable releases are never replaced")
    else:
        raise ReleaseError("safe no-clobber directory publication is unsupported on this platform")
    files = _release_files(result, bundle_path)
    if sys.platform.startswith("linux"):
        _publish_linux(files, output)
    else:
        _publish_windows(files, output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate"); check.add_argument("bundle", type=Path)
    run = sub.add_parser("build"); run.add_argument("bundle", type=Path); run.add_argument("--output", type=Path, required=True)
    audit = sub.add_parser("audit"); audit.add_argument("bundle", type=Path); audit.add_argument("--release-dir", type=Path, required=True)
    assess = sub.add_parser("assess"); assess.add_argument("bundle", type=Path); assess.add_argument("--json-out", type=Path, required=True); assess.add_argument("--report-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        bundle_path = args.bundle.resolve(strict=True)
        bundle = read_document(bundle_path)
        result, errors = validate_bundle(bundle, bundle_path)
        if errors:
            raise ReleaseError("\n".join(errors))
        release = result["release"]
        if args.command == "validate":
            print(f"PASS: {release['release_kind']} {release['dataset_version_id']} ({len(release['items'])} items); no files written")
        elif args.command == "audit":
            audit_errors = audit_release(result, args.release_dir, bundle_path)
            if audit_errors:
                raise ReleaseError("published release audit failed:\n" + "\n".join(audit_errors))
            print(f"PASS: audited {release['dataset_version_id']} at {args.release_dir}; all five artifacts match byte-for-byte")
        elif args.command == "assess":
            assessment, report = build_readiness_assessment(bundle_path)
            _write_report_no_clobber(args.json_out, json.dumps(assessment, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")
            _write_report_no_clobber(args.report_out, report.encode("utf-8"))
            print(f"PASS: readiness {assessment['assessment_id']} software={assessment['software_integrity']} evidence={assessment['evidence_admission']} real-items={assessment['cohort']['real_items']} candidates={len(assessment['benchmark_candidates'])}; no rights granted")
        else:
            publish(result, args.output, bundle_path)
            print(f"PASS: published {release['dataset_version_id']} to {args.output}")
        return 0
    except (ReleaseError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
