"""Dry-run policy planner and validator for data acquisition manifests."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import http.client
import ipaddress
import json
import os
import socket
import ssl
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

import yaml
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "sources" / "registry.yaml"
SCHEMA_PATH = ROOT / "schemas" / "acquisition_manifest.schema.json"
MET_API_HOST = "collectionapi.metmuseum.org"
MET_API_PREFIX = "/public/collection/v1/objects/"
MET_POLICY_URL = "https://www.metmuseum.org/hubs/open-access"
MET_CANDIDATES = {
    561345: "09.184.703", 561392: "09.184.751", 561361: "09.184.720",
    561391: "09.184.750", 561407: "09.184.766", 561409: "09.184.768",
    561410: "09.184.769", 561413: "09.184.772", 561621: "14.1.453",
}
MAX_MET_RESPONSE_BYTES = 256 * 1024
MET_TIMEOUT_SECONDS = 12


class AcquisitionError(Exception):
    """Input or schema error suitable for the CLI."""


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection pinned to a prevalidated public DNS answer."""

    def __init__(self, host: str, pinned_ip: str, timeout: float):
        super().__init__(host, 443, timeout=timeout, context=ssl.create_default_context())
        self.pinned_ip = pinned_ip

    def connect(self) -> None:
        raw = socket.create_connection((self.pinned_ip, self.port), self.timeout)
        peer_ip = ipaddress.ip_address(raw.getpeername()[0])
        if not peer_ip.is_global or str(peer_ip) != self.pinned_ip:
            raw.close()
            raise OSError("MET_PEER_NOT_PINNED_PUBLIC")
        self.sock = self._context.wrap_socket(raw, server_hostname=self.host)


def _met_get(path: str) -> tuple[int, str, bytes]:
    """Fetch one fixed-host API path with DNS pinning, no redirects and a hard cap."""
    answers = socket.getaddrinfo(MET_API_HOST, 443, type=socket.SOCK_STREAM)
    addresses = sorted({answer[4][0] for answer in answers})
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise OSError("MET_DNS_NOT_PUBLIC")
    connection = _PinnedHTTPSConnection(MET_API_HOST, addresses[0], MET_TIMEOUT_SECONDS)
    try:
        connection.request("GET", path, headers={
            "Accept": "application/json", "Accept-Encoding": "identity",
            "User-Agent": "Hieratic-AI-DATA-002-metadata-evidence/1.0",
            "Connection": "close",
        })
        response = connection.getresponse()
        content_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
        if response.status != 200:
            raise AcquisitionError(f"MET_HTTP_STATUS_{response.status}")
        if response.getheader("Content-Encoding", "identity").lower() not in {"", "identity"}:
            raise AcquisitionError("MET_CONTENT_ENCODING_UNSUPPORTED")
        content_length = response.getheader("Content-Length")
        if content_length and int(content_length) > MAX_MET_RESPONSE_BYTES:
            raise AcquisitionError("MET_RESPONSE_TOO_LARGE")
        body = response.read(MAX_MET_RESPONSE_BYTES + 1)
        if len(body) > MAX_MET_RESPONSE_BYTES:
            raise AcquisitionError("MET_RESPONSE_TOO_LARGE")
        return response.status, content_type, body
    finally:
        connection.close()


def met_metadata_packet(object_id: int, *, transport: Callable[[str], tuple[int, str, bytes]] | None = None) -> dict[str, Any]:
    """Retrieve metadata for one allowlisted Met object; never requests image bytes."""
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    expected_accession = MET_CANDIDATES.get(object_id)
    packet: dict[str, Any] = {
        "packet_schema_version": "1.0.0", "retrieved_at": now,
        "candidate_id": f"MET-{object_id}", "institution": "The Metropolitan Museum of Art",
        "endpoint": f"https://{MET_API_HOST}{MET_API_PREFIX}{object_id}",
        "requested_object_id": object_id, "expected_accession_from_R017": expected_accession,
        "http_status": None, "content_type": None, "response_body_bytes": None,
        "response_body_sha256": None, "verification_status": "failed", "error_code": None,
        "observed": None,
        "field_verification": {key: "not_observed" for key in (
            "objectID", "accessionNumber", "isPublicDomain", "objectURL", "primaryImage", "primaryImageSmall", "additionalImages"
        )},
        "rights_assessment": {
            "api_is_public_domain": None, "museum_policy_url": MET_POLICY_URL,
            "policy_scope_observation": "Met states public-domain artwork images and basic collection data are CC0; this is not independent item-rights adjudication",
            "exact_original_image_eligibility": "unresolved_until_exact_view_bytes_and_asset_scope_are_verified",
            "original_image_bytes_obtained": False, "original_image_sha256": None,
            "diplomatic_hieratic_gold_present": False, "independent_text_permission_verified": False,
            "benchmark_independence_cleared": False, "training_admission": "BLOCKED_METADATA_ONLY",
        },
        "identity_review": {
            "accession_aliases_adjudicated": False, "physical_support_confirmed": False,
            "face_and_writing_identity_confirmed": False, "source_registry_record": None,
            "r017_literal_metadata_match_count": None,
            "caveat": "No direct registered source identity or image-level, alias, edition, side, or pretraining-overlap clearance is inferred.",
        },
    }
    if expected_accession is None:
        packet["error_code"] = "MET_OBJECT_ID_NOT_ALLOWLISTED"
        return packet
    path = f"{MET_API_PREFIX}{object_id}"
    try:
        status, content_type, body = (transport or _met_get)(path)
        packet.update({"http_status": status, "content_type": content_type, "response_body_bytes": len(body), "response_body_sha256": hashlib.sha256(body).hexdigest()})
        if len(body) > MAX_MET_RESPONSE_BYTES:
            raise AcquisitionError("MET_RESPONSE_TOO_LARGE")
        if status != 200:
            raise AcquisitionError(f"MET_HTTP_STATUS_{status}")
        if content_type != "application/json":
            raise AcquisitionError("MET_CONTENT_TYPE_NOT_JSON")
        try:
            record = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AcquisitionError("MET_JSON_MALFORMED") from exc
        if not isinstance(record, dict):
            raise AcquisitionError("MET_JSON_NOT_OBJECT")
        if record.get("objectID") != object_id:
            raise AcquisitionError("MET_OBJECT_ID_MISMATCH")
        if record.get("accessionNumber") != expected_accession:
            raise AcquisitionError("MET_ACCESSION_MISMATCH")
        expected_object_url = f"https://www.metmuseum.org/art/collection/search/{object_id}"
        if record.get("objectURL") != expected_object_url:
            raise AcquisitionError("MET_OBJECT_URL_MISMATCH")
        primary = record.get("primaryImage")
        small = record.get("primaryImageSmall")
        additional = record.get("additionalImages")
        if not isinstance(primary, str) or not primary or not isinstance(small, str) or not isinstance(additional, list):
            raise AcquisitionError("MET_IMAGE_METADATA_MALFORMED")
        image_urls = [primary, small, *additional]
        for url in image_urls:
            parts = urlsplit(url)
            if url and (parts.scheme != "https" or parts.hostname != "images.metmuseum.org" or not parts.path.startswith("/CRDImages/eg/" ) or parts.username or parts.password or parts.query or parts.fragment):
                raise AcquisitionError("MET_IMAGE_URL_OUTSIDE_ALLOWLIST")
        observed = {key: record.get(key) for key in (
            "objectID", "accessionNumber", "isPublicDomain", "objectURL", "department", "objectName",
            "title", "period", "objectDate", "medium", "primaryImage", "primaryImageSmall", "additionalImages"
        )}
        if not isinstance(observed["isPublicDomain"], bool):
            raise AcquisitionError("MET_RIGHTS_FLAG_MISSING_OR_INVALID")
        packet["observed"] = observed
        packet["field_verification"] = {key: "api_observed" for key in packet["field_verification"]}
        packet["rights_assessment"]["api_is_public_domain"] = observed["isPublicDomain"]
        packet["verification_status"] = "verified_api_response_identity_and_schema"
    except AcquisitionError as exc:
        packet["error_code"] = str(exc)
    except (OSError, TimeoutError, ssl.SSLError, http.client.HTTPException, ValueError) as exc:
        packet["error_code"] = f"MET_TRANSPORT_ERROR:{type(exc).__name__}"
    return packet


def build_met_reconciliation(packets: list[dict[str, Any]], crosswalk: dict[str, Any], public_metadata_path: Path) -> dict[str, Any]:
    """Join API-observed Met candidates conservatively; absence never clears independence."""
    public_rows = [json.loads(line) for line in public_metadata_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    def norm(value: str) -> str:
        import re
        import unicodedata
        return "".join(ch for ch in unicodedata.normalize("NFKC", value).casefold() if ch.isalnum())
    by_id = {packet["requested_object_id"]: packet for packet in packets}
    comparisons = []
    for candidate in crosswalk["candidates"]:
        accession = candidate["accession"]
        accession_key = norm(accession)
        literal_rows = [row for row in public_rows if accession.casefold() in row.get("object_name", "").casefold()]
        normalized_rows = [row for row in public_rows if accession_key and accession_key in norm(row.get("object_name", ""))]
        object_id = int(candidate["candidate_id"].removeprefix("MET-")) if candidate["candidate_id"].startswith("MET-") else None
        packet = by_id.get(object_id)
        api_accession = (packet or {}).get("observed", {}).get("accessionNumber")
        comparisons.append({
            "candidate_id": candidate["candidate_id"], "institution": candidate["institution"],
            "candidate_accession": accession, "met_api_accession": api_accession,
            "api_identity_verified": bool(packet and packet["verification_status"] == "verified_api_response_identity_and_schema"),
            "r017_crosswalk_exact_public_source_metadata_matches": candidate["exact_public_source_metadata_matches"],
            "literal_accession_substring_matches_in_pinned_R017_public_metadata": [row["id"] for row in literal_rows],
            "normalized_accession_string_matches_in_pinned_R017_public_metadata": [row["id"] for row in normalized_rows],
            "nearby_collection_witness_count_from_R017": candidate["nearby_collection_witness_count"],
            "r017_source_lineage_status": candidate["source_lineage_status"],
            "image_view_count": len((packet or {}).get("observed", {}).get("additionalImages", [])) + (1 if (packet or {}).get("observed", {}).get("primaryImage") else 0),
            "view_identity_group": f"{candidate['candidate_id']} (all API-listed views remain grouped; no pixel comparison performed)",
            "rights_status": "NOT_CLEARED", "image_equivalence_status": "NOT_TESTED",
            "training_admission": "BLOCKED",
            "unresolved": ["aliases", "physical support", "faces/writings", "joined fragments", "edition lineage", "pixel/perceptual duplicates", "pretraining overlap", "sealed benchmark overlap"],
        })
    return {
        "schema_version": "1.0.0", "source_crosswalk": "docs/research/R017_R016_CANDIDATE_SOURCE_CROSSWALK.json",
        "source_public_metadata": "docs/research/R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl",
        "public_metadata_rows_read": len(public_rows), "scope": "public metadata strings only; no pixels, gold, restricted/sealed rows, or images",
        "interpretation": "Literal and punctuation-normalized accession checks cover only object_name strings in this pinned public metadata snapshot; neither establishes source independence. The upstream R-017 crosswalk reported no exact public source metadata matches for all candidates.",
        "all_15_candidates_preserved": len(comparisons) == 15,
        "all_candidates_blocked": all(row["training_admission"] == "BLOCKED" for row in comparisons),
        "candidates": comparisons,
    }


def _validate_metadata_output(output: Path) -> Path:
    """Resolve a caller path under acquisition evidence and reject every symlink component."""
    root = (ROOT / "data" / "acquisition").resolve(strict=True)
    absolute = output.absolute()
    try:
        lexical_relative = absolute.relative_to(root)
    except ValueError as exc:
        raise AcquisitionError("metadata packet output must be under data/acquisition") from exc
    if not lexical_relative.parts or any(part in {".", ".."} for part in lexical_relative.parts):
        raise AcquisitionError("metadata packet output path is invalid")
    cursor = root
    for part in lexical_relative.parts[:-1]:
        cursor = cursor / part
        if cursor.is_symlink() or (hasattr(cursor, "is_junction") and cursor.is_junction()):
            raise AcquisitionError("metadata packet output path contains a symlink")
    resolved_parent = absolute.parent.resolve(strict=True)
    if resolved_parent != absolute.parent or not resolved_parent.is_dir():
        raise AcquisitionError("metadata packet output parent must be a real directory")
    if absolute.is_symlink() or (hasattr(absolute, "is_junction") and absolute.is_junction()) or absolute.exists():
        raise AcquisitionError("refusing to overwrite existing metadata packet")
    return absolute


def _publish_metadata_packet(output: Path, packet: dict[str, Any]) -> None:
    """Atomically publish a complete packet without replacing any existing path."""
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=output.parent, prefix=".met-packet-", suffix=".tmp", delete=False) as stream:
            temp_name = stream.name
            json.dump(packet, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp_name, output, follow_symlinks=False)
    except FileExistsError as exc:
        raise AcquisitionError(f"refusing to overwrite metadata packet: {output}") from exc
    except OSError as exc:
        raise AcquisitionError(f"cannot atomically publish metadata packet: {type(exc).__name__}") from exc
    finally:
        if temp_name:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def _load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise AcquisitionError(f"{path}: cannot read valid YAML: {exc}") from exc


def _validate_https_urls(item: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    synthetic = item.get("is_synthetic_fixture", False)

    def valid_evidence_url(url: str) -> bool:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        placeholder = host in {"example.com", "example.org", "example.net"} or host.endswith((".invalid", ".example", ".test"))
        return parts.scheme == "https" and bool(parts.netloc) and not parts.username and not parts.password and (synthetic or not placeholder)

    for field in ("canonical_object_url", "exact_access_url"):
        url = item.get(field)
        if url is None:
            continue
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
            errors.append(f"items[{index}].{field}: expected an absolute HTTPS URL")
    for field in ("provenance_urls", "evidence_urls"):
        for url_index, url in enumerate(item.get(field, [])):
            if not valid_evidence_url(url):
                errors.append(f"items[{index}].{field}[{url_index}]: expected an absolute HTTPS URL with non-placeholder evidence")
    return errors


def _review_reference_is_valid(reference: str | None, synthetic: bool) -> bool:
    if not reference or not reference.strip():
        return False
    if synthetic:
        return reference.startswith("synthetic:")
    parts = urlsplit(reference)
    host = (parts.hostname or "").lower()
    placeholder = host in {"example.com", "example.org", "example.net"} or host.endswith(
        (".invalid", ".example", ".test")
    )
    return (
        parts.scheme == "https"
        and bool(host)
        and not parts.username
        and not parts.password
        and parts.path not in {"", "/"}
        and not placeholder
    )


def _review_value_is_known(value: str | None) -> bool:
    return bool(value and value.strip() and value.strip().lower() not in {"unknown", "unresolved", "n/a", "none"})


def logical_fingerprint(item: dict[str, Any]) -> str:
    """Hash stable identity fields; retrieval-event data intentionally does not affect it."""
    identity = {
        "source_id": item["source_id"],
        "source_object_id": item["source_object_id"],
        "canonical_object_url": item["canonical_object_url"],
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_data(manifest: Any, registry: Any, schema: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    schema_errors = sorted(validator.iter_errors(manifest), key=lambda error: list(map(str, error.absolute_path)))
    errors = [f"manifest{''.join(f'[{part!r}]' for part in error.absolute_path)}: {error.message}" for error in schema_errors]
    if errors:
        return errors, []

    source_by_id = {source["source_id"]: source for source in registry["sources"]}
    plans: list[dict[str, Any]] = []
    seen_fingerprints: set[str] = set()
    for index, item in enumerate(manifest["items"]):
        item_errors = _validate_https_urls(item, index)
        source_id = item["source_id"]
        source = source_by_id.get(source_id)
        if source is None:
            errors.append(f"items[{index}].source_id: unknown source_id {source_id}")
            plans.append({
                "item": item,
                "decision": "REFUSED",
                "planning_status": "REFUSED",
                "admission_status": "NOT ADMITTED — planner performs no acquisition or corpus admission",
                "reasons": ["unknown source_id"],
            })
            continue

        use = item["intended_use"]
        if item["source_rights_snapshot"]["rights_class"] != source["rights_class"]:
            item_errors.append("rights_class snapshot does not match the source registry")
        if source["benchmark_quarantine"] != item["benchmark_quarantine"]:
            item_errors.append("benchmark_quarantine snapshot does not match the source registry")
        if source["benchmark_overlap_risk"] != item["benchmark_overlap_risk"]:
            item_errors.append("benchmark_overlap_risk snapshot does not match the source registry")
        if item["required_attribution"] != source["attribution_requirements"]:
            item_errors.append("required_attribution must preserve the source registry requirement")

        if use == "reference":
            if item["acquisition_mode"] != "metadata_only":
                item_errors.append("reference use must use metadata_only mode")
            if item["acquisition_status"] == "complete":
                item_errors.append("reference-only metadata records cannot declare acquisition complete")
            if item["source_rights_snapshot"]["use_decision"] != "metadata_only":
                item_errors.append("reference use snapshot must be metadata_only")
            decision = "ALLOWED"
            reasons = ["metadata-only reference; no source content is acquired"]
        else:
            decision = source[f"{use}_use"].upper()
            reasons = []
            if item["source_rights_snapshot"]["use_decision"] != source[f"{use}_use"]:
                item_errors.append("use_decision snapshot does not match the source registry")
            if source["rights_class"] == "EVALUATION-ONLY" and use in {"training", "development"}:
                item_errors.append("EVALUATION-ONLY sources cannot be used for training or development")
            if source["benchmark_quarantine"] and use in {"training", "development"}:
                item_errors.append("benchmark-quarantined sources cannot be used for training or development")
            if source[f"{use}_use"] in {"prohibited", "not_approved", "metadata_only"}:
                item_errors.append(f"source registry decision {source[f'{use}_use']} refuses {use} use")
        conditions_required = (
            use != "reference" and source[f"{use}_use"] == "conditional"
        ) or (
            item["redistribution_requested"] and source["redistribution_use"] == "conditional"
        )
        if conditions_required:
            required_conditions = set(source["automated_access_constraints"]) | set(source["project_review_markers"])
            condition_map = {condition["condition_id"]: condition for condition in item["review_conditions"]}
            missing_conditions = sorted(required_conditions - condition_map.keys())
            if missing_conditions:
                item_errors.append(f"conditional use or redistribution lacks explicit conditions: {', '.join(missing_conditions)}")
            for condition_id in sorted(required_conditions & condition_map.keys()):
                condition = condition_map[condition_id]
                if not condition["satisfied"]:
                    item_errors.append(f"condition {condition_id} is not satisfied")
                if not condition["evidence_urls"]:
                    item_errors.append(f"condition {condition_id} lacks evidence URLs")
                elif not item["is_synthetic_fixture"] and any(
                    not _review_reference_is_valid(url, False) for url in condition["evidence_urls"]
                ):
                    item_errors.append(f"condition {condition_id} uses placeholder evidence")
            reasons.append("conditional registry use; all registry conditions must be evidenced")

        item_rights_required = (
            use in {"training", "development"}
            and source["rights_class"] == "PER-ITEM"
            and source[f"{use}_use"] == "conditional"
        )
        overlap_review_required = use in {"training", "development"} and source["benchmark_overlap_risk"] == "high"
        if item_rights_required:
            review = item["item_rights_review"]
            synthetic = item["is_synthetic_fixture"]
            if not _review_value_is_known(review["license_identifier"]):
                item_errors.append("item rights review requires a known item-specific license identifier")
            if not _review_value_is_known(review["rightsholder"]):
                item_errors.append("item rights review requires an identified rightsholder")
            if review["approval_status"] != "approved":
                item_errors.append("item rights review lacks reviewer approval")
            if not _review_value_is_known(review["reviewer_id"]):
                item_errors.append("item rights review requires an accountable reviewer")
            if not _review_reference_is_valid(review["evidence_ref"], synthetic):
                item_errors.append("item rights review requires non-placeholder evidence reference")
            if not review["reviewed_at"]:
                item_errors.append("item rights review requires a review date")
            item_url = review["item_url"]
            if synthetic:
                if not item_url or not item_url.startswith("synthetic://"):
                    item_errors.append("synthetic fixture item rights review requires a synthetic:// item URL")
            else:
                item_host = (urlsplit(item_url or "").hostname or "").lower()
                source_host = (urlsplit(source["canonical_url"]).hostname or "").lower()
                if not item_url or urlsplit(item_url).scheme != "https" or item_host != source_host or urlsplit(item_url).path in {"", "/"}:
                    item_errors.append("item rights review requires an item-specific HTTPS URL on the registered source host")

        if overlap_review_required:
            review = item["benchmark_overlap_review"]
            synthetic = item["is_synthetic_fixture"]
            if review["status"] != "clear":
                item_errors.append("high-risk training/development use requires a clear benchmark-overlap assessment")
            if not _review_value_is_known(review["reviewer_id"]):
                item_errors.append("benchmark-overlap assessment requires an accountable reviewer")
            if not _review_reference_is_valid(review["evidence_ref"], synthetic):
                item_errors.append("benchmark-overlap assessment requires non-placeholder evidence reference")
            if not _review_value_is_known(review["overlap_check_version"]):
                item_errors.append("benchmark-overlap assessment requires a versioned check")
            if not review["reviewed_at"]:
                item_errors.append("benchmark-overlap assessment requires a review date")
        if item["redistribution_requested"] and source["redistribution_use"] not in {"allowed", "conditional"}:
            item_errors.append(f"source registry decision {source['redistribution_use']} refuses redistribution")
        if item["redistribution_requested"]:
            rights_evidence = set(source["rights_evidence_urls"])
            if not rights_evidence:
                item_errors.append("source registry has no rights evidence for requested redistribution")
            if not rights_evidence <= set(item["evidence_urls"]):
                item_errors.append("manifest evidence_urls must include source rights_evidence_urls for redistribution")
        if use != "reference":
            reasons.append(f"source registry {use} decision: {source[f'{use}_use']}")

        if item["acquisition_status"] == "complete" and item["acquisition_mode"] in {"direct_download", "iiif", "api"}:
            if not item["actual_sha256"]:
                item_errors.append("complete downloaded artifact requires actual_sha256")
            if not item["retrieval_timestamp"]:
                item_errors.append("complete downloaded artifact requires retrieval_timestamp")
        fingerprint = logical_fingerprint(item)
        if fingerprint in seen_fingerprints:
            item_errors.append(f"duplicate logical acquisition fingerprint {fingerprint}")
        seen_fingerprints.add(fingerprint)
        if item_errors:
            decision = "REFUSED"
            reasons.extend(item_errors)
            errors.extend(f"items[{index}]: {message}" for message in item_errors)
        elif decision == "CONDITIONAL":
            decision = "CONDITIONAL PLAN READY"
        admission_status = "NOT ADMITTED — planner performs no acquisition or corpus admission"
        if item["is_synthetic_fixture"]:
            admission_status = "NOT ADMITTED — synthetic fixture only"
        plans.append({
            "item": item,
            "decision": decision,
            "planning_status": decision,
            "admission_status": admission_status,
            "reasons": reasons,
            "fingerprint": fingerprint,
        })
    return errors, plans


def load_and_validate(manifest_path: Path, registry_path: Path = REGISTRY_PATH, schema_path: Path = SCHEMA_PATH):
    manifest = _load_yaml(manifest_path)
    registry = _load_yaml(registry_path)
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcquisitionError(f"{schema_path}: cannot read valid JSON Schema: {exc}") from exc
    return validate_data(manifest, registry, schema)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.acquisition")
    parser.add_argument("command", choices=["plan", "validate", "metadata-fetch-met"])
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--object-id", type=int, help="one allowlisted Met collection object ID")
    args = parser.parse_args(argv)
    if args.command == "metadata-fetch-met":
        if args.object_id is None:
            parser.error("metadata-fetch-met requires --object-id")
        try:
            output = _validate_metadata_output(args.manifest)
            packet = met_metadata_packet(args.object_id)
            _publish_metadata_packet(output, packet)
        except AcquisitionError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({"output": str(output.relative_to(ROOT)), "verification_status": packet["verification_status"], "error_code": packet["error_code"], "response_body_sha256": packet["response_body_sha256"]}, sort_keys=True))
        return 0 if packet["verification_status"] == "verified_api_response_identity_and_schema" else 1
    try:
        errors, plans = load_and_validate(args.manifest, args.registry, args.schema)
    except AcquisitionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for plan in plans:
        item = plan["item"]
        print(f"PLAN: {plan['planning_status']} — {item['source_id']} / {item['source_object_id']} ({item['intended_use']})")
        print(f"ADMISSION: {plan['admission_status']}")
        print(f"  target: {item['expected_path']}")
        print(f"  fingerprint: {plan.get('fingerprint', 'unavailable')}")
        for reason in plan["reasons"]:
            print(f"  - {reason}")
    if errors:
        print("Acquisition manifest validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"PASS: {len(plans)} acquisition manifest item(s) validated; no network calls made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
