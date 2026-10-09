"""Screen and byte-hash selected Commons-hosted Museo Egizio manuscript photos.

This is a metadata/identity intake audit, not a DATA-002 acquisition or corpus
admission. Exact file-page CC0 evidence is checked before original file bytes
are streamed into a bounded in-memory buffer and discarded after hashing.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import time
import tempfile
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
UPLOAD_HOST = "upload.wikimedia.org"
USER_AGENT = "HieraticAI-W20-Museum-Photo-Provenance-Audit/1.0 (https://github.com/m7mdehab/hieratic-ai/issues/128; bounded memory-only SHA-256)"
MAX_PHOTO_BYTES = 80 * 1024 * 1024
MAX_PIXELS = 100_000_000
MIN_INTERVAL = 2.0
FILES = [
    {"file_title": "The so-called 'Strike Papyrus' written by Amunnakht - Museo Egizio Turin C 1880 p01.jpg", "candidate_id": "TURIN-CAT1880-P01", "accession": "Cat.1880", "object_url": "https://collezioni.museoegizio.it/en-GB/material/Cat_1880/", "group_id": "MUSEO-EGIZIO:CAT-1880", "role": "original_commons_jpeg_photo", "intended_role": "photographed manuscript support; face/line pairing unresolved"},
    {"file_title": "The so-called 'Strike Papyrus' written by Amunnakht - Museo Egizio Turin C 1880 p02.jpg", "candidate_id": "TURIN-CAT1880-P02", "accession": "Cat.1880", "object_url": "https://collezioni.museoegizio.it/en-GB/material/Cat_1880/", "group_id": "MUSEO-EGIZIO:CAT-1880", "role": "original_commons_jpeg_photo", "intended_role": "photographed manuscript support; face/line pairing unresolved"},
    {"file_title": "Ostrakon ieratico recante un inventario SA63894.tif", "candidate_id": "TURIN-CAT2169-P01-TIFF", "accession": "Cat.2169", "object_url": "https://collezioni.museoegizio.it/en-GB/material/Cat_2169/", "group_id": "MUSEO-EGIZIO:CAT-2169", "role": "museum_camera_tiff_photo", "intended_role": "monogram/inventory control image; not a line-transliteration target"},
    {"file_title": "Ostrakon ieratico recante un inventario SA63895.tif", "candidate_id": "TURIN-CAT2169-P02-TIFF", "accession": "Cat.2169", "object_url": "https://collezioni.museoegizio.it/en-GB/material/Cat_2169/", "group_id": "MUSEO-EGIZIO:CAT-2169", "role": "museum_camera_tiff_photo", "intended_role": "monogram/inventory control image; not a line-transliteration target"},
    {"file_title": "Hieratic ostracon with an inventory, limestone - Museo Egizio (Turin) C 2169 p01.jpg", "candidate_id": "TURIN-CAT2169-P01-JPEG", "accession": "Cat.2169", "object_url": "https://collezioni.museoegizio.it/en-GB/material/Cat_2169/", "group_id": "MUSEO-EGIZIO:CAT-2169", "role": "commons_jpeg_view_derivative", "intended_role": "monogram/inventory control image; derivative/view relation unverified"},
    {"file_title": "Hieratic ostracon with an inventory, limestone - Museo Egizio (Turin) C 2169 p02.jpg", "candidate_id": "TURIN-CAT2169-P02-JPEG", "accession": "Cat.2169", "object_url": "https://collezioni.museoegizio.it/en-GB/material/Cat_2169/", "group_id": "MUSEO-EGIZIO:CAT-2169", "role": "commons_jpeg_view_derivative", "intended_role": "monogram/inventory control image; derivative/view relation unverified"},
    {"file_title": "Ostrakon ieratico con un testo oracolare SA63451.tif", "candidate_id": "TURIN-S6759-ORACLE-TIFF", "accession": "S.6759", "object_url": "https://collezioni.museoegizio.it/en-GB/material/S_6759", "group_id": "MUSEO-EGIZIO:S6759", "role": "museum_camera_tiff_photo", "intended_role": "Hieratic ostracon photograph; no rights-cleared aligned edition text or reviewed line gold"},
]
_last = 0.0


class PhotoAuditError(ValueError):
    pass


def sha256_stream(url: str, limit: int) -> tuple[bytes, str]:
    global _last
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != UPLOAD_HOST or parsed.username or parsed.password or parsed.port:
        raise PhotoAuditError("original media URL is outside upload.wikimedia.org HTTPS")
    pause = MIN_INTERVAL - (time.monotonic() - _last)
    if pause > 0:
        time.sleep(pause)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "image/*"})
    with urllib.request.urlopen(request, timeout=45) as response:
        _last = time.monotonic()
        final = urllib.parse.urlsplit(response.geturl())
        requested = urllib.parse.urlsplit(url)
        if (response.status != 200 or final.scheme != "https" or final.hostname != UPLOAD_HOST or final.port is not None
                or final.username or final.password or final.path != requested.path):
            raise PhotoAuditError("media response status or host mismatch")
        length = response.headers.get("content-length")
        if length and int(length) > limit:
            raise PhotoAuditError(f"source is larger than bounded {limit}-byte custody limit")
        data = bytearray()
        while len(data) <= limit:
            chunk = response.read(min(1024 * 1024, limit + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if not data or len(data) > limit:
            raise PhotoAuditError(f"source is empty or exceeds bounded {limit}-byte custody limit")
        return bytes(data), response.headers.get("content-type", "").split(";", 1)[0].lower()


def commons_info(title: str) -> dict[str, Any]:
    global _last
    pause = MIN_INTERVAL - (time.monotonic() - _last)
    if pause > 0:
        time.sleep(pause)
    params = urllib.parse.urlencode({"action":"query", "format":"json", "formatversion":"2", "titles":"File:" + title,
        "prop":"imageinfo|revisions|categories", "cllimit":"max", "clprop":"title", "iiprop":"url|size|mime|sha1|timestamp|extmetadata", "iiextmetadatalanguage":"en",
        "iiextmetadatafilter":"LicenseShortName|LicenseUrl|UsageTerms|Artist|ImageDescription|DateTimeOriginal|Attribution|Source|Restrictions",
        "rvprop":"ids|timestamp", "rvlimit":"1"})
    url = COMMONS_API + "?" + params
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept":"application/json"})
    raw = b""
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                _last = time.monotonic()
                if response.status != 200:
                    raise PhotoAuditError(f"Commons API HTTP {response.status}")
                raw = response.read(2 * 1024 * 1024)
                if response.geturl().split("?",1)[0] != COMMONS_API:
                    raise PhotoAuditError("Commons metadata response URL mismatch")
            break
        except urllib.error.HTTPError as exc:
            _last = time.monotonic()
            if exc.code != 429 or attempt == 3:
                raise
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            try:
                delay = min(60.0, max(2.0, float(retry_after))) if retry_after else 4.0 * (attempt + 1)
            except ValueError:
                delay = 4.0 * (attempt + 1)
            time.sleep(delay)
    data = json.loads(raw.decode("utf-8"))
    pages = data.get("query", {}).get("pages", [])
    if len(pages) != 1 or pages[0].get("missing") is not None:
        raise PhotoAuditError("exact Commons file page missing or ambiguous")
    page = pages[0]
    infos = page.get("imageinfo", [])
    if len(infos) != 1:
        raise PhotoAuditError("current Commons file revision metadata missing")
    info = infos[0]
    revs = page.get("revisions", [])
    meta = info.get("extmetadata", {})
    def meta_val(key: str) -> str | None:
        value = meta.get(key)
        return value.get("value") if isinstance(value, dict) and isinstance(value.get("value"), str) else None
    def meta_source(key: str) -> str | None:
        value = meta.get(key)
        return value.get("source") if isinstance(value, dict) and isinstance(value.get("source"), str) else None
    return {"commons_title": page.get("title"), "categories": [row.get("title") for row in page.get("categories", []) if isinstance(row, dict) and isinstance(row.get("title"), str)], "description_url": page.get("canonicalurl"), "page_revision_id": (revs[0].get("revid") if revs else None),
        "page_revision_timestamp": (revs[0].get("timestamp") if revs else None), "file_revision_timestamp": info.get("timestamp"), "file_sha1_publisher_claim": info.get("sha1"),
        "original_url": info.get("url"), "mime": info.get("mime"), "width": info.get("width"), "height": info.get("height"), "file_size_bytes": info.get("size"),
        "license_short_name": meta_val("LicenseShortName"), "license_url": meta_val("LicenseUrl"), "license_metadata_source": meta_source("LicenseUrl"), "usage_terms": meta_val("UsageTerms"),
        "artist": meta_val("Artist"), "source": meta_val("Source"), "description": meta_val("ImageDescription"), "attribution": meta_val("Attribution"),
        "datetime_original": meta_val("DateTimeOriginal"), "restrictions": meta_val("Restrictions"), "metadata_response_sha256": hashlib.sha256(raw).hexdigest(), "metadata_response_bytes": len(raw)}


def decoded_dhash(raw: bytes, mime: str) -> str | None:
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(raw))
        if image.width * image.height > MAX_PIXELS:
            raise PhotoAuditError("decoded pixel count exceeds bounded image limit")
        image.verify()
        image = Image.open(io.BytesIO(raw)).convert("L").resize((9, 8))
        values = list(image.getdata())
        bits = [values[y * 9 + x] > values[y * 9 + x + 1] for y in range(8) for x in range(8)]
        return f"{sum((1 << i) for i,b in enumerate(bits) if b):016x}"
    except ImportError:
        return None


def accession_evidence(candidate: dict[str, Any], info: dict[str, Any]) -> dict[str, Any]:
    accession = candidate["accession"]
    aliases = {re.sub(r"[^A-Za-z0-9]", "", accession).lower()}
    if accession.startswith("Cat."):
        aliases.add("c" + accession[4:].lower())
    title_key = re.sub(r"[^A-Za-z0-9]", "", info.get("commons_title") or "").lower()
    categories = info.get("categories", []) if isinstance(info.get("categories", []), list) else []
    for category in categories:
        if not isinstance(category, str):
            continue
        category_key = re.sub(r"[^A-Za-z0-9]", "", category).lower()
        if any(alias and alias in category_key for alias in aliases):
            return {"matched": True, "matching_accession_category": category, "commons_file_title": info.get("commons_title")}
    title_match = any(alias and alias in title_key for alias in aliases)
    return {"matched": title_match, "matching_accession_category": None, "commons_file_title": info.get("commons_title")}


def original_bytes_match(raw: bytes, mime: str, info: dict[str, Any]) -> bool:
    ext = (info.get("original_url") or "").split("?", 1)[0].rsplit(".", 1)[-1].lower()
    magic_ok = ((ext in {"jpg", "jpeg"} and raw.startswith(b"\xff\xd8")) or
                (ext in {"tif", "tiff"} and raw[:4] in {b"II*\x00", b"MM\x00*"}))
    if mime != info.get("mime") or not magic_ok:
        return False
    expected_sha1 = info.get("file_sha1_publisher_claim")
    return isinstance(expected_sha1, str) and bool(re.fullmatch(r"[a-fA-F0-9]{40}", expected_sha1)) and hashlib.sha1(raw).hexdigest().lower() == expected_sha1.lower()


def validate_report(report: dict[str, Any]) -> list[str]:
    errors = []
    items = report.get("items")
    if report.get("schema_version") != "w20-museum-photo-intake/1.0.0" or not isinstance(items, list):
        return ["invalid W20 museum photo report identity or items"]
    if report.get("media_bytes_written_to_disk") is not False:
        errors.append("media bytes must remain memory-only")
    if report.get("candidate_count") != len(items):
        errors.append("candidate count differs from item records")
    candidate_ids = [item.get("candidate_id") for item in items]
    groups = report.get("grouping", {})
    if len(candidate_ids) != len(set(candidate_ids)):
        errors.append("photo candidate IDs are not unique")
    if not isinstance(groups, dict) or report.get("distinct_physical_support_groups") != len(groups):
        errors.append("physical support grouping count does not match group map")
    elif any(item.get("candidate_id") not in groups.get(item.get("group_id"), []) for item in items):
        errors.append("photo item is missing from its accession-level physical support group")
    if report.get("bytes_hashed") != sum(bool(i.get("original_sha256")) for i in items):
        errors.append("bytes hashed count differs from item hashes")
    for item in items:
        if item.get("training_admission") is not False or item.get("gold_admission") is not False or item.get("benchmark_overlap") != "UNKNOWN_QUARANTINED":
            errors.append(f"{item.get('candidate_id')}: admission or benchmark boundary violated")
        if item.get("text_rights") != "NOT_VERIFIED_OR_NOT_ASSUMED":
            errors.append(f"{item.get('candidate_id')}: image evidence cannot imply text rights")
        image_hash = item.get("original_sha256")
        if image_hash is not None and (not isinstance(image_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", image_hash)):
            errors.append(f"{item.get('candidate_id')}: invalid original SHA-256")
        sha1_state = item.get("publisher_sha1_verified")
        if sha1_state is not None and not isinstance(sha1_state, bool):
            errors.append(f"{item.get('candidate_id')}: publisher SHA-1 state is not boolean")
        if sha1_state is True and image_hash is None:
            errors.append(f"{item.get('candidate_id')}: publisher SHA-1 cannot be verified without byte hash")
    declared = report.get("evidence_sha256")
    if declared is not None:
        material = {key: value for key, value in report.items() if key not in {"retrieved_at_utc", "evidence_sha256"}}
        if declared != hashlib.sha256(json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest():
            errors.append("evidence digest does not match canonical report content")
    return errors


def validate_schema(report: dict[str, Any], *, root: Path | None = None) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise PhotoAuditError("jsonschema is required to validate the W20 evidence receipt") from exc
    repository = root or Path(__file__).resolve().parents[2]
    schema = json.loads((repository / "data/releases/w20_source_evidence.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return [error.message for error in Draft202012Validator(schema).iter_errors(report)]


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.parent.is_symlink():
        raise PhotoAuditError("receipt output or parent must not be a symlink")
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


def apply_benchmark_screen(items: list[dict[str, Any]], *, root: Path | None = None) -> dict[str, Any]:
    from data.releases.w20_aku_pal_source_audit import repository_evidence_bytes
    repository = root or Path(__file__).resolve().parents[2]
    public_path = repository / "docs/research/R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl"
    raw = repository_evidence_bytes(public_path, root=repository)
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if len(rows) != 266:
        raise PhotoAuditError(f"pinned public R-017 census expected 266 rows, got {len(rows)}")
    for item in items:
        accession = item["accession"]
        if accession.startswith("Cat."):
            number = accession[4:]
            pattern = re.compile(rf"(?<![A-Za-z0-9])(?:Cat\.?\s*{re.escape(number)}|C\s*{re.escape(number)})(?![0-9])", re.I)
        else:
            pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(accession)}(?![A-Za-z0-9])", re.I)
        matches = [{"item_id": row.get("id"), "object_name": row.get("object_name"), "source_group": row.get("source_group")}
                   for row in rows if isinstance(row.get("object_name"), str) and pattern.search(row["object_name"])]
        item["benchmark_screen"] = {"result": "POSITIVE_LITERAL_PUBLIC_METADATA_MATCH" if matches else "NO_LITERAL_MATCH_IN_PUBLIC_METADATA",
            "disposition": "QUARANTINED_PENDING_OBJECT_AND_IMAGE_LINEAGE_REVIEW", "matches": matches, "sealed_records_read": 0}
        item["benchmark_overlap"] = "UNKNOWN_QUARANTINED"
    return {"public_r017_row_count": len(rows), "public_r017_sha256": hashlib.sha256(raw).hexdigest(), "sealed_records_read": 0,
        "literal_match_count": sum(bool(i["benchmark_screen"]["matches"]) for i in items),
        "no_literal_match_count": sum(not i["benchmark_screen"]["matches"] for i in items),
        "no_literal_match_is_clearance": False}


def run(fetch_bytes: bool = True) -> dict[str, Any]:
    items = []
    for candidate in FILES:
        item = {**candidate, "metadata_status": "UNVERIFIED", "bytes_status": "NOT_ACQUIRED", "original_sha256": None,
            "actual_dimensions": None, "decoded_dhash64": None, "text_rights": "NOT_VERIFIED_OR_NOT_ASSUMED", "benchmark_overlap": "UNKNOWN_QUARANTINED", "training_admission": False, "gold_admission": False}
        try:
            info = commons_info(candidate["file_title"])
            item["metadata"] = info
            item["metadata_status"] = "COMMONS_REVISION_AND_ITEM_TERMS_READ"
            license_url = (info.get("license_url") or "").lower()
            cc0_url = license_url.startswith(("https://creativecommons.org/publicdomain/zero/1.0/", "http://creativecommons.org/publicdomain/zero/1.0/"))
            cc0 = info.get("license_short_name", "").strip().upper() in {"CC0", "CC0 1.0", "CC0 1.0 UNIVERSAL"} and cc0_url and info.get("license_metadata_source") == "commons-desc-page"
            identity = accession_evidence(candidate, info)
            source_exact = identity["matched"]
            item["identity_evidence"] = {**identity, "museum_object_reference": candidate["object_url"], "identity_method": "exact accession token in Commons file title or category; museum page is a separate corroborating reference"}
            if not cc0:
                item["rights_status"] = "BLOCKED_NOT_EXACT_CC0"
            elif not source_exact:
                item["rights_status"] = "BLOCKED_ACCESSION_NOT_VISIBLE_IN_FILE_EVIDENCE"
            else:
                item["rights_status"] = "FILE_PAGE_CC0_AND_ACCESSION_REFERENCE_SCREENED_NOT_INSTITUTIONALLY_ADMITTED"
            if cc0 and source_exact and fetch_bytes:
                if int(info["file_size_bytes"]) > MAX_PHOTO_BYTES:
                    item["bytes_status"] = "NOT_ACQUIRED_SIZE_LIMIT_EXCEEDED"
                else:
                    raw, mime = sha256_stream(info["original_url"], MAX_PHOTO_BYTES)
                    item["publisher_sha1_verified"] = bool(re.fullmatch(r"[a-fA-F0-9]{40}", info.get("file_sha1_publisher_claim") or "") and hashlib.sha1(raw).hexdigest().lower() == info["file_sha1_publisher_claim"].lower())
                    if not original_bytes_match(raw, mime, info):
                        item["bytes_status"] = "REJECTED_SOURCE_HASH_OR_MEDIA_MISMATCH"
                    else:
                        item["bytes_status"] = "CURRENT_ORIGINAL_FILE_BYTES_HASHED_IN_MEMORY"
                        item["original_sha256"] = hashlib.sha256(raw).hexdigest()
                        item["byte_count"] = len(raw)
                        item["actual_dimensions"] = None
                        try:
                            from PIL import Image
                            image = Image.open(io.BytesIO(raw))
                            if image.width * image.height > MAX_PIXELS:
                                raise PhotoAuditError("decoded pixel count exceeds bounded image limit")
                            image.verify()
                            item["actual_dimensions"] = [int(image.width), int(image.height)]
                            item["decoded_dhash64"] = decoded_dhash(raw, mime)
                            item["decode_status"] = "PIL_VERIFY_AND_DHASH_PASS"
                        except ImportError:
                            item["decode_status"] = "decoder_unavailable"
                        except PhotoAuditError as exc:
                            item["decode_status"] = "decode_blocked:PIXEL_LIMIT"
                            item["decode_detail"] = str(exc)[:120]
                            item["bytes_status"] = "HASHED_UNDECODED_PIXEL_LIMIT"
                        except Exception as exc:
                            item["decode_status"] = "decode_failed:" + type(exc).__name__
                            item["bytes_status"] = "HASHED_BUT_DECODE_FAILED"
                        del raw
        except (OSError, ValueError, KeyError, json.JSONDecodeError, PhotoAuditError) as exc:
            item["metadata_status"] = "SOURCE_SCREEN_FAILED"
            item["rights_status"] = "BLOCKED"
            item["failure"] = type(exc).__name__ + ":" + str(exc)[:160]
        items.append(item)
    benchmark_receipt = apply_benchmark_screen(items)
    # p01/p02 and all asset variants belong to one accession-level support even
    # when they have distinct file titles, revisions, hashes or pixel sizes.
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(item["group_id"], []).append(item)
    for rows in groups.values():
        hashes: dict[str, list[str]] = {}
        for row in rows:
            if row.get("decoded_dhash64"):
                hashes.setdefault(row["decoded_dhash64"], []).append(row["candidate_id"])
        for row in rows:
            if row.get("decoded_dhash64"):
                row["perceptual_exact_groups"] = hashes[row["decoded_dhash64"]]
    report = {"schema_version":"w20-museum-photo-intake/1.0.0", "retrieved_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "classification":"SOURCE_PHOTO_EVIDENCE_ONLY_NOT_DATA002_ADMISSION", "maximum_concurrency":1, "media_bytes_written_to_disk":False,
        "max_media_bytes":MAX_PHOTO_BYTES, "candidate_count":len(items), "distinct_physical_support_groups":len(groups), "bytes_hashed":sum(i.get("original_sha256") is not None for i in items),
        "items":items, "grouping":{key:[i["candidate_id"] for i in rows] for key,rows in sorted(groups.items())}, "benchmark_screen":benchmark_receipt,
        "global_boundaries":["No image bytes or TPOP partner text stored in the repository.","Commons file-page rights and museum accession references are item-specific evidence; they do not authorize the scholarly transcription.","Cat.2169 is a monogram/inventory control, not a standard text-line target.","S.6759 and Cat.1880 have no independently rights-cleared line-transliteration pair in this packet.","All candidates remain benchmark-quarantined, training=false, gold=false; no DATA-002 acquisition is claimed."]}
    report["evidence_sha256"] = hashlib.sha256(json.dumps({key: value for key, value in report.items() if key != "retrieved_at_utc"}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    errors = validate_report(report)
    if errors:
        raise PhotoAuditError("generated report failed invariants: " + "; ".join(errors))
    return report


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--output",type=Path,required=True);p.add_argument("--metadata-only",action="store_true");a=p.parse_args(argv)
    report=run(fetch_bytes=not a.metadata_only)
    schema_errors=validate_schema(report)
    if schema_errors: raise PhotoAuditError("evidence schema violation: " + "; ".join(schema_errors[:8]))
    write_json_atomic(a.output, report)
    print(json.dumps({"candidate_files":report["candidate_count"],"physical_support_groups":report["distinct_physical_support_groups"],"original_file_bytes_hashed":report["bytes_hashed"],"bytes_written_to_disk":False,"output":str(a.output),"gold":0,"training_admissions":0},sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
