"""Bounded, source-exact AKU-PAL sign census and in-memory media audit.

The public API is used only for individually identified Hieratogram records.
Source metadata and licensed media are never written to disk by this tool; the
output contains hashes, rights links, public provenance fields and exclusions.
Every candidate remains benchmark-quarantined, unreviewed and unadmitted.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIGIN = "https://aku-pal.uni-mainz.de"
INDEX_URL = ORIGIN + "/api/graphemes"
MAX_INDEX_BYTES = 32 * 1024 * 1024
MAX_RECORD_BYTES = 256 * 1024
MAX_MEDIA_BYTES = 4 * 1024 * 1024
MAX_ASSETS_PER_RECORD = 5
MIN_REQUEST_INTERVAL_SECONDS = 1.0  # sequential requests with headroom for the public API
USER_AGENT = "HieraticAI-W20-licensed-sign-source-census/1.0 (bounded public metadata audit)"
LICENSES = {
    "https://creativecommons.org/licenses/by/4.0/": "CC-BY-4.0",
    "https://creativecommons.org/publicdomain/zero/1.0/": "CC0-1.0",
    "https://creativecommons.org/publicdomain/zero/1.0": "CC0-1.0",
}
ASSET_PATH = re.compile(r"^/(?:img/data/ht/(?:svg|scan)/ht_[0-9]+(?:_[0-9]+)?\.(?:svg|webp|png|jpe?g)|api/svg/ht_[0-9]+\.svg/outline)$", re.I)
ID_IN_ASSET = re.compile(r"(?:ht_|ht_)([0-9]+)", re.I)
HTML_TAG = re.compile(r"<[^>]*>")


class AuditError(ValueError):
    pass


class SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old = urllib.parse.urlsplit(req.full_url)
        new = urllib.parse.urlsplit(urllib.parse.urljoin(req.full_url, newurl))
        if new.scheme != "https" or new.hostname != old.hostname or new.port is not None or new.username or new.password:
            raise AuditError("redirect outside the exact HTTPS publisher origin refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(SameHostRedirect())
_LAST_REQUEST = 0.0


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def bounded_get(url: str, limit: int, accept: str) -> tuple[bytes, str, str]:
    global _LAST_REQUEST
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "aku-pal.uni-mainz.de" or parsed.port is not None or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise AuditError("request URL outside exact publisher HTTPS origin/path refused")
    delay = MIN_REQUEST_INTERVAL_SECONDS - (time.monotonic() - _LAST_REQUEST)
    if delay > 0:
        time.sleep(delay)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    for attempt in range(4):
        try:
            with _OPENER.open(request, timeout=30) as response:
                _LAST_REQUEST = time.monotonic()
                if response.status != 200:
                    raise AuditError(f"HTTP status {response.status}")
                final = urllib.parse.urlsplit(response.geturl())
                if final.scheme != "https" or final.hostname != "aku-pal.uni-mainz.de" or final.port is not None:
                    raise AuditError("final source URL differs from publisher origin")
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                body = response.read(limit + 1)
            break
        except urllib.error.HTTPError as exc:
            _LAST_REQUEST = time.monotonic()
            if exc.code != 429 or attempt == 3:
                raise AuditError(f"source request HTTP {exc.code}") from exc
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            try:
                delay = min(60.0, max(2.0, float(retry_after))) if retry_after else 5.0 * (attempt + 1)
            except ValueError:
                delay = 5.0 * (attempt + 1)
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError) as exc:
            _LAST_REQUEST = time.monotonic()
            raise AuditError(f"source request failed: {type(exc).__name__}: {str(exc)[:140]}") from exc
    if not body or len(body) > limit:
        raise AuditError(f"source body empty or exceeds bounded {limit}-byte read")
    return body, content_type, response.geturl()


def text_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        vals = [text_value(part) for part in value]
        return " | ".join(x for x in vals if x) or None
    if isinstance(value, dict):
        if "value" in value:
            return text_value(value["value"])
        return None
    return HTML_TAG.sub(" ", html.unescape(str(value))).strip() or None


def _details(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for group in record.get("details", []):
        if not isinstance(group, dict):
            continue
        for item in group.get("items", []):
            if isinstance(item, dict) and isinstance(item.get("key"), str):
                found[item["key"]] = item
    return found


def _license(item: dict[str, Any] | None) -> dict[str, str | None]:
    if not item:
        return {"label": None, "url": None, "license_id": None}
    vals = item.get("values", [])
    if not isinstance(vals, list):
        vals = [vals]
    for value in vals:
        if not isinstance(value, str):
            continue
        hrefs = re.findall(r"href=['\"]([^'\"]+)['\"]", value, re.I)
        label = text_value(value)
        for href in hrefs:
            href = html.unescape(href)
            license_id = LICENSES.get(href.rstrip("/")) or LICENSES.get(href)
            if license_id:
                return {"label": label, "url": href, "license_id": license_id}
    return {"label": text_value(vals), "url": None, "license_id": None}


def discover_index(raw: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"public grapheme index is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(payload, list):
        raise AuditError("public grapheme index shape is not an array")
    rows: dict[int, dict[str, Any]] = {}
    grapheme_count = len(payload)
    for grapheme in payload:
        if not isinstance(grapheme, dict) or not isinstance(grapheme.get("data"), dict):
            continue
        grapheme_id = grapheme.get("id")
        data = grapheme["data"]
        for dating in (data.get("datingCollection", {}).get("values", []) or []):
            for sign in (dating.get("hieratograms", []) or []):
                if not isinstance(sign, dict) or not isinstance(sign.get("id"), int):
                    continue
                sid = sign["id"]
                row = rows.setdefault(sid, {"sign_id": sid, "index_grapheme_ids": [], "text_ids": [], "text_labels": [], "index_asset_paths": []})
                if isinstance(grapheme_id, int) and grapheme_id not in row["index_grapheme_ids"]:
                    row["index_grapheme_ids"].append(grapheme_id)
                text = sign.get("text") if isinstance(sign.get("text"), dict) else {}
                text_id = text.get("id")
                if isinstance(text_id, int) and text_id not in row["text_ids"]:
                    row["text_ids"].append(text_id)
                label = text_value(text.get("values"))
                if label and label not in row["text_labels"]:
                    row["text_labels"].append(label)
                filename = sign.get("filename")
                if isinstance(filename, str) and filename not in row["index_asset_paths"]:
                    row["index_asset_paths"].append(filename)
    candidates = sorted(rows.values(), key=lambda row: row["sign_id"])
    return candidates, {"grapheme_records": grapheme_count, "unique_indexed_sign_ids": len(candidates), "index_sha256": digest(raw), "index_bytes": len(raw)}


def select_ids(rows: list[dict[str, Any]], target_count: int, target_text_groups: int) -> tuple[list[int], dict[str, Any]]:
    """Deterministically spread sample across API text identities; not witness adjudication."""
    groups: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        keys = row.get("text_ids") or []
        key = str(keys[0]) if keys else "unknown-text"
        groups[key].append(row["sign_id"])
    ordered = sorted(groups, key=lambda key: (key == "unknown-text", key))
    chosen: list[int] = []
    selected_groups = ordered[:target_text_groups]
    # Round-robin limits concentration in large text records while retaining a
    # sizeable, reproducible group when the public source does not expose more.
    depth = 0
    while len(chosen) < target_count:
        added = False
        for group in selected_groups:
            ids = groups[group]
            if depth < len(ids) and len(chosen) < target_count:
                chosen.append(ids[depth]); added = True
        if not added:
            break
        depth += 1
    return chosen, {"index_text_identity_groups": len(groups), "selected_text_identity_groups": selected_groups, "target_items": target_count, "target_groups": target_text_groups, "selected_items": len(chosen)}


def media_path_allowed(path: str, sign_id: int) -> bool:
    if not isinstance(path, str) or not ASSET_PATH.fullmatch(path):
        return False
    ids = ID_IN_ASSET.findall(path)
    return bool(ids) and all(int(value) == sign_id for value in ids)


def _svg_check(body: bytes) -> tuple[bool, str | None, list[int] | None]:
    prefix = body[:8192].lower()
    if b"<!doctype" in prefix or b"<!entity" in prefix:
        return False, "doctype_or_entity_refused", None
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return False, "malformed_svg", None
    allowed_ns = {"http://www.w3.org/2000/svg", ""}
    for element in root.iter():
        tag = element.tag.split("}")[-1].lower()
        if tag in {"script", "foreignobject", "iframe", "object", "embed"}:
            return False, f"active_or_external_element:{tag}", None
        for key, value in element.attrib.items():
            attr = key.split("}")[-1].lower()
            if attr.startswith("on"):
                return False, "event_handler_attribute_refused", None
            if attr in {"href", "src"} and value and not value.startswith("#"):
                return False, "external_resource_reference_refused", None
            if "url(" in value.lower() and not re.fullmatch(r"\s*url\(\s*#[A-Za-z0-9_.:-]+\s*\)\s*", value, re.I):
                return False, "external_css_resource_reference_refused", None
    if root.tag.split("}")[0].lstrip("{") not in allowed_ns or root.tag.split("}")[-1].lower() != "svg":
        return False, "root_is_not_svg", None
    view = root.attrib.get("viewBox") or root.attrib.get("viewbox")
    dims = None
    if view:
        try:
            parts = [float(x) for x in re.split(r"[ ,]+", view.strip())]
            if len(parts) == 4 and parts[2] > 0 and parts[3] > 0:
                dims = [round(parts[2]), round(parts[3])]
        except ValueError:
            pass
    return True, None, dims


def inspect_media(url: str, sign_id: int, *, fetch: bool = True) -> dict[str, Any]:
    path = urllib.parse.urlsplit(url).path
    result: dict[str, Any] = {"url": url, "asset_role": None, "status": "NOT_FETCHED", "sha256": None, "byte_size": None, "content_type": None, "dimensions": None, "safe_svg": None}
    if not media_path_allowed(path, sign_id):
        result.update({"status": "REJECTED_URL_OR_SIGN_ID_MISMATCH", "reason": "media path is not a known sign-specific HT asset on the publisher origin"})
        return result
    if "/api/svg/" in path:
        result["asset_role"] = "outline_derivative"
    elif "/scan/" in path:
        result["asset_role"] = "publication_scan_reproduction"
    else:
        result["asset_role"] = "publisher_sign_svg"
    if not fetch:
        return result
    try:
        body, ctype, final_url = bounded_get(url, MAX_MEDIA_BYTES, "image/svg+xml,image/webp,image/png,image/jpeg")
        if final_url != url:
            raise AuditError("media redirect changes exact source URL")
        result.update({"status": "BYTES_HASHED_IN_MEMORY", "sha256": digest(body), "byte_size": len(body), "content_type": ctype})
        ext = Path(path).suffix.lower()
        if ext == ".svg":
            safe, why, dimensions = _svg_check(body)
            result["safe_svg"] = safe
            result["dimensions"] = dimensions
            if not safe:
                result.update({"status": "REJECTED_UNSAFE_SVG", "reason": why})
        else:
            expected = {".webp": ("image/webp", body[:4] == b"RIFF" and body[8:12] == b"WEBP"), ".png": ("image/png", body.startswith(b"\x89PNG\r\n\x1a\n")), ".jpg": ("image/jpeg", body.startswith(b"\xff\xd8")), ".jpeg": ("image/jpeg", body.startswith(b"\xff\xd8"))}.get(ext)
            if not expected or ctype != expected[0] or not expected[1]:
                result.update({"status": "REJECTED_MEDIA_SIGNATURE_MISMATCH", "reason": "content type or file magic does not match source URL extension"})
            else:
                try:
                    from PIL import Image
                    import io
                    with Image.open(io.BytesIO(body)) as image:
                        image.verify()
                    with Image.open(io.BytesIO(body)) as image:
                        result["dimensions"] = [int(image.width), int(image.height)]
                except ImportError:
                    result["dimensions"] = None
                    result["dimension_status"] = "decoder_unavailable"
                except Exception as exc:
                    result.update({"status": "REJECTED_UNDECODABLE_IMAGE", "reason": type(exc).__name__})
    except (AuditError, urllib.error.URLError, TimeoutError) as exc:
        result.update({"status": "FETCH_FAILED", "reason": str(exc)[:180]})
    return result


def _image_links(record: dict[str, Any], sign_id: int) -> list[dict[str, str]]:
    result = []
    seen = set()
    for item in record.get("images", []):
        if not isinstance(item, dict):
            continue
        role = str(item.get("type", ""))
        # Generic HG comparison drawings and unrelated publication links are not
        # additional Hieratic sign specimens.
        if role.lower() == "hieroglyph":
            continue
        for value in item.get("values", []) if isinstance(item.get("values"), list) else []:
            if not isinstance(value, str) or not media_path_allowed(value, sign_id):
                continue
            url = ORIGIN + value
            if url not in seen:
                result.append({"url": url, "publisher_image_type": role})
                seen.add(url)
    return result[:MAX_ASSETS_PER_RECORD]


def _record_summary(raw: bytes, index_row: dict[str, Any], *, fetch_media: bool) -> dict[str, Any]:
    sid = index_row["sign_id"]
    url = f"{ORIGIN}/api/signs/{sid}"
    out: dict[str, Any] = {"sign_id": sid, "record_url": url, "record_sha256": digest(raw), "record_bytes": len(raw), "metadata_state": "VERIFIED_SOURCE_RECORD", "license_id": None, "license_label": None, "license_url": None, "media": [], "rights_status": "unlicensed_or_unknown", "training_admission": False, "gold_admission": False, "benchmark_overlap": "unknown_quarantined", "expert_review": "none"}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        out.update({"metadata_state": "INVALID_JSON", "exclusion_reasons": ["individual API response is not valid UTF-8 JSON"]}); return out
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict) or payload[0].get("id") != sid:
        out.update({"metadata_state": "IDENTITY_MISMATCH", "rights_status": "blocked_missing_or_incompatible_item_rights_or_identity", "exclusion_reasons": ["individual API response does not contain exactly the requested stable HT ID"]}); return out
    details = _details(payload[0])
    license_record = _license(details.get("licenseTxt"))
    out.update({"license_id": license_record["license_id"], "license_label": license_record["label"], "license_url": license_record["url"],
                "creator": text_value(details.get("facsimileCreator", {}).get("values")) if details.get("facsimileCreator") else None,
                "source_text_record_id": index_row.get("text_ids", [None])[0] if index_row.get("text_ids") else None,
                "source_text_label": index_row.get("text_labels", [None])[0] if index_row.get("text_labels") else None,
                "index_grapheme_ids": index_row.get("index_grapheme_ids", []),
                "source_inventory_label": text_value(details.get("invNumbers", {}).get("values")) if details.get("invNumbers") else None,
                "line_locator": text_value(details.get("line", {}).get("values")) if details.get("line") else None,
                "column_locator": text_value(details.get("column", {}).get("values")) if details.get("column") else None,
                "side": text_value(details.get("roVo", {}).get("values")) if details.get("roVo") else None,
                "script_type": text_value(details.get("scriptType", {}).get("values")) if details.get("scriptType") else None,
                "facsimile_type": text_value(details.get("facsimileTyp", {}).get("values")) if details.get("facsimileTyp") else None,
                "facsimile_origin": text_value(details.get("facsimileHerkunft", {}).get("values")) if details.get("facsimileHerkunft") else None,
                "dating": text_value(details.get("dating", {}).get("values")) if details.get("dating") else None,
                "source_place": text_value(details.get("place", {}).get("values")) if details.get("place") else None})
    allowed_rights = out["license_id"] in {"CC-BY-4.0", "CC0-1.0"} and bool(out["creator"]) and bool(out["source_inventory_label"]) and bool(out["side"])
    out["rights_status"] = "per_item_license_and_public_provenance_screened_not_institutionally_admitted" if allowed_rights else "blocked_missing_or_incompatible_item_rights_or_identity"
    if out.get("script_type") not in {"Hieratisch", "Hieratic"}:
        out["rights_status"] = "blocked_nonhieratic_or_unresolved_script_type"
    media_links = _image_links(payload[0], sid)
    if allowed_rights and out["script_type"] in {"Hieratisch", "Hieratic"}:
        for link in media_links:
            media = inspect_media(link["url"], sid, fetch=fetch_media)
            media["publisher_image_type"] = link["publisher_image_type"]
            media["source_record_license_id"] = out["license_id"]
            out["media"].append(media)
        if fetch_media and not any(asset.get("status") == "BYTES_HASHED_IN_MEMORY" and asset.get("safe_svg") is not False for asset in out["media"]):
            out["rights_status"] = "blocked_no_verified_safe_sign_media"
    else:
        out["media"] = [{"url": ORIGIN + value, "publisher_image_type": "source-linked-but-not-fetched", "status": "NOT_FETCHED_RIGHTS_OR_IDENTITY_BLOCKED", "sha256": None} for link in media_links for value in [urllib.parse.urlsplit(link["url"]).path]]
    return out


def benchmark_registry(root: Path | None = None) -> tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]], dict[str, Any]]:
    """Read only the approved public R-017 metadata and prior W19 source receipts."""
    repository = root or Path(__file__).resolve().parents[2]
    public_path = repository / "docs/research/R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl"
    w19_path = repository / "data/releases/w19_aku_pal_original_image_receipts.json"
    public_raw = public_path.read_bytes()
    w19_raw = w19_path.read_bytes()
    public_rows = []
    for line in public_raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        public_rows.append(row)
    if len(public_rows) != 266:
        raise AuditError(f"pinned public R-017 census expected 266 rows, got {len(public_rows)}")
    index: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in public_rows:
        found = set()
        for field in ("source_url", "source_file_url"):
            value = str(row.get(field) or "")
            found.update(int(match) for match in re.findall(r"(?:/signs/|ht_)([0-9]+)", value))
        for sid in found:
            index[sid].append({"item_id": row.get("id"), "object_name": row.get("object_name"), "source_group": row.get("source_group"), "corpus_status": row.get("corpus_status")})
    w19 = json.loads(w19_raw.decode("utf-8"))
    w19_ids = {int(item["id"]) for item in w19.get("items", []) if isinstance(item, dict) and str(item.get("id", "")).isdigit()}
    for sid in w19_ids:
        index[sid].append({"item_id": "W19-verified-source-register", "object_name": next((item.get("physical_witness") for item in w19.get("items", []) if item.get("id") == sid), None), "source_group": "w19", "corpus_status": "UNRESOLVED_QUARANTINED"})
    return index, public_rows, {"public_r017_row_count": len(public_rows), "public_r017_sha256": digest(public_raw), "w19_receipt_sha256": digest(w19_raw), "sealed_records_read": 0}


def apply_benchmark_screen(report: dict[str, Any], *, root: Path | None = None) -> dict[str, Any]:
    benchmark, public_rows, receipt = benchmark_registry(root)
    for item in report.get("items", []):
        matches = [{**match, "match_type": "exact_publisher_sign_id"} for match in benchmark.get(item.get("sign_id"), [])]
        inventory_tokens = tuple(re.findall(r"[a-z]+|[0-9]+", str(item.get("source_inventory_label") or "").lower()))
        for public in public_rows:
            object_tokens = tuple(re.findall(r"[a-z]+|[0-9]+", str(public.get("object_name") or "").lower()))
            if inventory_tokens and any(object_tokens[offset:offset + len(inventory_tokens)] == inventory_tokens for offset in range(max(0, len(object_tokens) - len(inventory_tokens) + 1))):
                match = {"item_id": public.get("id"), "object_name": public.get("object_name"), "source_group": public.get("source_group"), "corpus_status": public.get("corpus_status"), "match_type": "exact_inventory_token_sequence"}
                if match not in matches:
                    matches.append(match)
        if matches:
            item["benchmark_screen"] = {"state": "POSITIVE_PUBLIC_METADATA_ID_OVERLAP_QUARANTINED", "matches": matches}
        else:
            item["benchmark_screen"] = {"state": "NO_LITERAL_MATCH_PUBLIC_METADATA_ONLY_STILL_UNKNOWN_QUARANTINED", "matches": []}
        item["benchmark_overlap"] = "unknown_quarantined"
        item["training_admission"] = False
        item["gold_admission"] = False
    report["benchmark_screen"] = {**receipt, "screened_sign_ids": len(report.get("items", [])), "positive_public_metadata_overlaps": sum(bool(i["benchmark_screen"]["matches"]) for i in report.get("items", [])), "no_literal_match_is_clearance": False}
    items = report.get("items", [])
    from collections import Counter
    report["strata"] = {
        "license_id": dict(sorted(Counter(str(i.get("license_id") or "unknown") for i in items).items())),
        "script_type": dict(sorted(Counter(str(i.get("script_type") or "unknown") for i in items).items())),
        "facsimile_type": dict(sorted(Counter(str(i.get("facsimile_type") or "unknown") for i in items).items())),
        "dating": dict(sorted(Counter(str(i.get("dating") or "unknown") for i in items).items())),
        "media_role": dict(sorted(Counter(str(m.get("asset_role") or "not_fetched") for i in items for m in i.get("media", [])).items())),
        "rights_screen": dict(sorted(Counter(str(i.get("rights_status") or "unknown") for i in items).items())),
        "physical_inventory_labels_all_lower_bound": len({str(i.get("source_inventory_label")) for i in items if i.get("source_inventory_label")}),
        "physical_inventory_labels_identity_screened_lower_bound": len({str(i.get("source_inventory_label")) for i in items if i.get("source_inventory_label") and i.get("rights_status") == "per_item_license_and_public_provenance_screened_not_institutionally_admitted"}),
    }
    report.pop("evidence_sha256", None)
    report["evidence_sha256"] = digest(canonical({key: value for key, value in report.items() if key != "retrieved_at_utc"}))
    return report


def validate_schema(report: dict[str, Any], *, root: Path | None = None) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise AuditError("jsonschema is required to validate the W20 evidence receipt") from exc
    repository = root or Path(__file__).resolve().parents[2]
    schema = json.loads((repository / "data/releases/w20_source_evidence.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return [error.message for error in Draft202012Validator(schema).iter_errors(report)]


def validate_report(report: dict[str, Any]) -> list[str]:
    errors = []
    items = report.get("items")
    if report.get("schema_version") != "w20-akupal-source-census/1.0.0" or not isinstance(items, list):
        return ["invalid W20 AKU-PAL receipt identity or item list"]
    summary = report.get("summary", {})
    ids = [item.get("sign_id") for item in items]
    if len(ids) != len(set(ids)):
        errors.append("duplicate sign IDs in census")
    if summary.get("distinct_sign_ids_screened") != len(items):
        errors.append("screened sign count differs from item receipts")
    if summary.get("record_fetch_failures") != len(report.get("attempt_ledger", [])) - len(items):
        errors.append("attempt failure count differs from attempt ledger")
    verified = [media for item in items for media in item.get("media", []) if media.get("status") == "BYTES_HASHED_IN_MEMORY" and media.get("safe_svg") is not False]
    hashes = {media.get("sha256") for media in verified if media.get("sha256")}
    if summary.get("verified_sign_media_files") != len(verified) or summary.get("unique_media_byte_hashes") != len(hashes):
        errors.append("media counts do not agree with verified per-file evidence")
    if summary.get("training_admissions") != 0 or summary.get("gold_labels") != 0 or summary.get("production_corpus") is not False:
        errors.append("research receipt cannot claim gold, production or training admission")
    if any(item.get("benchmark_overlap") != "unknown_quarantined" or item.get("training_admission") is not False or item.get("gold_admission") is not False for item in items):
        errors.append("a census item escaped benchmark quarantine or admission boundary")
    material = {key: value for key, value in report.items() if key not in {"retrieved_at_utc", "evidence_sha256"}}
    if report.get("evidence_sha256") != digest(canonical(material)):
        errors.append("census evidence digest mismatch")
    return errors


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.parent.is_symlink():
        raise AuditError("receipt output or parent must not be a symlink")
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def audit(target_count: int = 240, target_text_groups: int = 32, *, fetch_media: bool = True, output: Path | None = None) -> dict[str, Any]:
    raw_index, index_type, index_final = bounded_get(INDEX_URL, MAX_INDEX_BYTES, "application/json")
    if index_type != "application/json" or index_final != INDEX_URL:
        raise AuditError("publisher grapheme index content type or exact URL differs")
    index_rows, index_report = discover_index(raw_index)
    selected_ids, plan = select_ids(index_rows, target_count, target_text_groups)
    by_id = {row["sign_id"]: row for row in index_rows}
    records = []
    attempts = []
    for sid in selected_ids:
        url = f"{ORIGIN}/api/signs/{sid}"
        try:
            raw, ctype, final = bounded_get(url, MAX_RECORD_BYTES, "application/json")
            if ctype != "application/json" or final != url:
                raise AuditError("record response content type or exact URL mismatch")
            row = _record_summary(raw, by_id[sid], fetch_media=fetch_media)
            records.append(row)
            attempts.append({"sign_id": sid, "status": row["metadata_state"], "record_sha256": row.get("record_sha256"), "exclusion_reasons": row.get("exclusion_reasons", [])})
        except AuditError as exc:
            attempts.append({"sign_id": sid, "status": "FETCH_OR_VALIDATION_FAILED", "record_sha256": None, "exclusion_reasons": [str(exc)[:200]]})
    # Deduplicate by exact original media bytes; alternatives and derivatives
    # remain linked to a single stable sign/source identity.
    media_by_hash: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for record in records:
        for media in record.get("media", []):
            if media.get("sha256"):
                media_by_hash[media["sha256"]].append((record["sign_id"], media.get("asset_role", "unknown")))
    witness_labels = {str(row.get("source_inventory_label")) for row in records if row.get("source_inventory_label")}
    licensed = [row for row in records if row.get("rights_status") == "per_item_license_and_public_provenance_screened_not_institutionally_admitted"]
    verified_assets = [m for row in records for m in row.get("media", []) if m.get("status") == "BYTES_HASHED_IN_MEMORY" and m.get("safe_svg") is not False]
    assessment = {
        "schema_version": "w20-akupal-source-census/1.0.0", "source": "AKU-PAL Academy Mainz public API", "source_policy_url": "https://aku-pal.uni-mainz.de/faq",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "classification": "RESEARCH_INVENTORY_ONLY_NOT_CORPUS_ADMISSION",
        "discovery": {"endpoint": INDEX_URL, **index_report, "content_type": index_type, "retrieved_url": index_final}, "selection": plan,
        "scan_limits": {"api_record_requests_sequential": True, "minimum_interval_seconds": MIN_REQUEST_INTERVAL_SECONDS, "maximum_concurrency": 1, "maximum_record_bytes": MAX_RECORD_BYTES, "maximum_media_bytes": MAX_MEDIA_BYTES, "maximum_assets_per_record": MAX_ASSETS_PER_RECORD, "media_bytes_written_to_disk": False},
        "summary": {"distinct_sign_ids_screened": len(records), "record_fetch_failures": len(attempts)-len(records), "exact_item_permissive_license_and_provenance_screened": len(licensed), "rights_or_identity_blocked": len(records)-len(licensed), "unique_publisher_inventory_labels_lower_bound": len(witness_labels), "unique_source_text_ids": len({row.get("source_text_record_id") for row in records if row.get("source_text_record_id")}), "unique_media_byte_hashes": len(media_by_hash), "verified_sign_media_files": len(verified_assets), "duplicate_media_hash_groups": sum(len(v)>1 for v in media_by_hash.values()), "training_admissions": 0, "gold_labels": 0, "benchmark_state": "UNKNOWN_QUARANTINED_ALL_RECORDS", "production_corpus": False},
        "media_hash_groups": [{"sha256": key, "references": [{"sign_id": sid, "asset_role": role} for sid, role in refs]} for key, refs in sorted(media_by_hash.items()) if len(refs)>1],
        "attempt_ledger": attempts, "items": records,
        "caveats": ["AKU-PAL record licenses apply only to the exact individually licensed images under the published FAQ; repository inventory is not independently protected authority onboarding.", "The publisher's annotations and grapheme associations are not independent gold.", "Sign-level publisher graphics and digitized publication scans are not original complete manuscript photographs or line-transliteration pairs.", "Inventory labels/text IDs are source-provided identity clues, not proof of distinct physical supports; aliases, joined fragments and benchmark lineage require independent review.", "Every record remains benchmark-quarantined and training/gold admission is false."]
    }
    assessment = apply_benchmark_screen(assessment)
    return assessment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="write metadata/hash receipt JSON; never source media")
    parser.add_argument("--target-items", type=int, default=240)
    parser.add_argument("--text-groups", type=int, default=32)
    parser.add_argument("--metadata-only", action="store_true", help="screen per-item rights/identity without retrieving media bytes")
    args = parser.parse_args(argv)
    if not 1 <= args.target_items <= 500 or not 1 <= args.text_groups <= args.target_items:
        parser.error("target items must be 1..500 and text groups 1..target items")
    try:
        result = audit(args.target_items, args.text_groups, fetch_media=not args.metadata_only, output=args.output)
        report_errors = validate_report(result)
        if report_errors:
            raise AuditError("report invariant failure: " + "; ".join(report_errors[:8]))
        schema_errors = validate_schema(result)
        if schema_errors:
            raise AuditError("evidence schema violation: " + "; ".join(schema_errors[:8]))
        write_json_atomic(args.output, result)
    except (AuditError, OSError, ValueError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"source_records_screened": result["summary"]["distinct_sign_ids_screened"], "eligible_screened": result["summary"]["exact_item_permissive_license_and_provenance_screened"], "source_text_ids": result["summary"]["unique_source_text_ids"], "inventory_label_lower_bound": result["summary"]["unique_publisher_inventory_labels_lower_bound"], "verified_media_files": result["summary"]["verified_sign_media_files"], "unique_media_hashes": result["summary"]["unique_media_byte_hashes"], "rights_blocked": result["summary"]["rights_or_identity_blocked"], "output": str(args.output), "training_admissions": 0, "gold": 0}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
