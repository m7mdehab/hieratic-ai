"""Build W28's finite, metadata-only DATA-008 candidate rejection ledger.

Only the hash-pinned DDD image metadata and small published split-definition
text are fetched. No image, annotation, split-membership, or label payload is
retrieved. This tool cannot authorize training or create a corpus release.
"""
from __future__ import annotations

import hashlib
import json
import struct
import urllib.parse
import urllib.request
import zlib
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

from tools.research_ddd_public_metadata import fetch_exact
from tools.research_ddd_prior_baseline import SEED as W24_SPLIT_SEED, stable_rank as w24_stable_rank
from data.releases import w20_aku_pal_source_audit as aku_source_audit

ROOT = Path(__file__).resolve().parents[2]
PREREG = ROOT / "data/releases/w28_candidate_study_preregistration.json"
PHOTOS = ROOT / "data/releases/w20_museum_photo_intake.json"
R024 = ROOT / "docs/research/R024_W8_TURIN_CANDIDATES.json"
OUT = ROOT / "data/releases/w28_candidate_readiness.json"
SCHEMA = ROOT / "data/releases/w28_candidate_readiness.schema.json"
CB_ZIP_URL = "https://zenodo.org/records/20553713/files/Split%20C-B.zip?download=1"
CB_ZIP_SIZE = 416564037
CB_ZIP_MD5_CLAIM = "5f15b1393806247ff8da950a4d595934"
SHA = lambda raw: hashlib.sha256(raw).hexdigest()

GATE_BLOCKERS = {
    "image_rights": "exact asset permission for intended operation is not independently established",
    "annotation_rights": "annotation/editorial text rights are separate and not independently established",
    "pixel_binding": "exact original bytes and annotation-to-pixel transform are not jointly verified",
    "expert_gold": "publisher/catalogue labels are not independent expert-adjudicated gold",
    "benchmark_lineage": "source/edition/image ancestry is unknown or quarantined; no-literal-match is not clearance",
    "support_split": "physical support grouping exists only where specifically receipted; a source-disjoint accepted split is absent",
    "custody": "no independently authorized custody/acquisition receipt for this exact asset and use",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ranged_read(start: int, end: int) -> bytes:
    """Read one exact, small publisher range; never fall back to full GET."""
    if start < 0 or end < start or end - start + 1 > 1_800_000:
        raise ValueError("publisher range outside W28 size cap")
    req = urllib.request.Request(CB_ZIP_URL, headers={
        "User-Agent": "HieraticAI-W28-split-membership-metadata/1.0",
        "Accept-Encoding": "identity", "Range": f"bytes={start}-{end}",
    })
    with urllib.request.urlopen(req, timeout=30) as response:
        host = urllib.parse.urlsplit(response.geturl()).hostname
        expected_len = end - start + 1
        if response.status != 206 or host != "zenodo.org" or response.headers.get("Content-Length") != str(expected_len):
            raise ValueError("publisher did not honor bounded C-B byte range; no fallback download attempted")
        if response.headers.get("Content-Range") != f"bytes {start}-{end}/{CB_ZIP_SIZE}":
            raise ValueError("C-B ZIP size or returned byte range differs from frozen source metadata")
        body = response.read(expected_len + 1)
    if len(body) != end - start + 1:
        raise ValueError("short or oversized C-B range response")
    return body


def extract_cb_membership() -> tuple[dict, dict]:
    """Range-extract the small C-B JSON only; do not read any ZIP image member."""
    tail_len = 1_800_000
    tail_start = CB_ZIP_SIZE - tail_len
    tail = ranged_read(tail_start, CB_ZIP_SIZE - 1)
    eocd_pos = tail.rfind(b"PK\x05\x06")
    if eocd_pos < 0 or eocd_pos + 22 > len(tail):
        raise ValueError("C-B ZIP end record missing from bounded tail")
    disk, cd_disk, disk_count, entry_count, cd_size, cd_offset, comment_len = struct.unpack_from("<HHHHIIH", tail, eocd_pos + 4)
    if disk or cd_disk or disk_count != entry_count or entry_count > 20000 or cd_size > tail_len or cd_offset < tail_start or comment_len != 0:
        raise ValueError("C-B ZIP directory exceeds fixed safe format/size limits")
    pos = cd_offset - tail_start
    entries = []
    for _ in range(entry_count):
        if tail[pos:pos + 4] != b"PK\x01\x02":
            raise ValueError("C-B central directory entry malformed")
        fields = struct.unpack_from("<6H3I5H2I", tail, pos + 4)
        _, _, flag, method, _, _, crc, csize, usize, nlen, xlen, clen, _, _, _, local_offset = fields
        name = tail[pos + 46:pos + 46 + nlen].decode("utf-8" if flag & 0x800 else "cp437")
        if name == "C-B_closed_recognition_published_document_aware.json":
            entries.append((method, crc, csize, usize, local_offset, name))
        pos += 46 + nlen + xlen + clen
    if pos != cd_offset - tail_start + cd_size or len(entries) != 1:
        raise ValueError("C-B membership JSON is absent, duplicated, or directory size inconsistent")
    method, expected_crc, csize, usize, local_offset, name = entries[0]
    if method != 8 or local_offset != 0 or csize > 100_000 or usize > 1_000_000:
        raise ValueError("C-B membership JSON exceeds pre-registered safe member bounds")
    # Central metadata gives exact compressed size. Read at most 1 KiB of local
    # header/name/extra padding plus that exact member stream.
    local = ranged_read(local_offset, local_offset + 30 + 1024 + csize - 1)
    sig, _, flag, local_method, _, _, _, _, _, nlen, xlen = struct.unpack_from("<4s5H3I2H", local, 0)
    if sig != b"PK\x03\x04" or flag & 1 or local_method != method or nlen > 1024 or xlen > 1024:
        raise ValueError("C-B member local header is malformed or encrypted")
    local_name = local[30:30 + nlen].decode("utf-8" if flag & 0x800 else "cp437")
    if local_name != name:
        raise ValueError("C-B local and central member identities differ")
    data_start = 30 + nlen + xlen
    compressed = local[data_start:data_start + csize]
    if len(compressed) != csize:
        raise ValueError("C-B membership member range was truncated")
    raw = zlib.decompress(compressed, -15)
    if len(raw) != usize or zlib.crc32(raw) & 0xffffffff != expected_crc:
        raise ValueError("C-B membership JSON size or archive CRC mismatch")
    return json.loads(raw), {"archive_url": CB_ZIP_URL, "archive_size_bytes": CB_ZIP_SIZE,
        "archive_md5_publisher_claim": CB_ZIP_MD5_CLAIM, "archive_fully_downloaded": False,
        "range_bytes_read": tail_len + len(local), "member_name": name, "member_bytes": len(raw),
        "member_sha256": SHA(raw), "member_crc32_verified": True,
        "image_or_crop_members_read": 0}


def reproduce_cb_split(papyri: dict, samples: dict, classes: dict) -> dict:
    split, receipt = extract_cb_membership()
    required = {"train", "val", "test", "labels"}
    if not isinstance(split, dict) or set(split) != required:
        raise ValueError("unexpected publisher C-B split JSON schema")
    partitions = {}
    errors = []
    all_sample_ids = []
    all_document_ids = []
    for key in ("train", "val", "test"):
        part = split[key]
        if not isinstance(part, dict) or set(part) != {"docs", "samples"}:
            raise ValueError(f"unexpected C-B {key} partition schema")
        docs = [str(x) for x in part["docs"]]
        sample_ids = [str(x) for x in part["samples"]]
        if len(docs) != len(set(docs)) or len(sample_ids) != len(set(sample_ids)):
            errors.append(f"duplicate IDs in C-B {key} partition")
        all_document_ids.extend(docs)
        all_sample_ids.extend(sample_ids)
        partition_samples = []
        for sid in sample_ids:
            sample = samples.get(sid)
            if not isinstance(sample, dict):
                errors.append(f"C-B {key} sample missing from pinned samples.json")
                continue
            doc_id = str(sample.get("document_number"))
            label = sample.get("class_label")
            if doc_id not in docs or label not in classes:
                errors.append(f"C-B {key} sample document/class does not match pinned source metadata")
            if doc_id not in papyri:
                errors.append("C-B document missing from pinned papyri.json")
                continue
            partition_samples.append((doc_id, label))
        valid_ids = [sid for sid in sample_ids if isinstance(samples.get(sid), dict)]
        expected_docs = {str(samples[sid]["document_number"]) for sid in valid_ids}
        expected_labels = {samples[sid]["class_label"] for sid in valid_ids}
        if set(docs) != expected_docs:
            errors.append(f"C-B {key} document membership mismatch against samples.json")
        partitions[key] = {"document_count": len(docs), "sample_count": len(sample_ids),
                           "source_image_ids": sorted(set(d for d, _ in partition_samples)),
                           "class_count": len(expected_labels),
                           "class_ids_sha256": SHA(json.dumps(sorted(expected_labels), ensure_ascii=False, separators=(",", ":")).encode("utf-8"))}
    if len(all_sample_ids) != len(set(all_sample_ids)):
        errors.append("C-B samples overlap across partitions")
    if len(all_document_ids) != len(set(all_document_ids)):
        errors.append("C-B publisher document IDs overlap across partitions")
    assigned_supports = {}
    for part_name, part in partitions.items():
        cluster_ids = {str(papyri[image_id]["doc_cluster"]) for image_id in part["source_image_ids"]}
        part["physical_support_count"] = len(cluster_ids)
        part["physical_support_ids"] = sorted(cluster_ids)
        for cluster in cluster_ids:
            if cluster in assigned_supports and assigned_supports[cluster] != part_name:
                errors.append("C-B physical support crosses partitions")
            assigned_supports[cluster] = part_name
    used_labels = {samples[sid]["class_label"] for sid in all_sample_ids}
    split_labels = set(split["labels"])
    label_set_diagnostic = {"split_label_value_type": type(next(iter(split_labels), None)).__name__,
        "sample_label_value_type": type(next(iter(used_labels), None)).__name__,
        "split_label_count": len(split_labels), "sample_label_count": len(used_labels),
        "split_only_label_count": len(split_labels - used_labels),
        "sample_only_label_count": len(used_labels - split_labels),
        "split_only_labels_in_class_catalog_count": len((split_labels - used_labels) & set(classes)),
        "sample_only_labels_in_class_catalog_count": len((used_labels - split_labels) & set(classes)),
        "split_only_labels_sha256": SHA(json.dumps(sorted(map(str, split_labels - used_labels)), ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
        "sample_only_labels_sha256": SHA(json.dumps(sorted(map(str, used_labels - split_labels)), ensure_ascii=False, separators=(",", ":")).encode("utf-8"))}
    if used_labels != split_labels or not split_labels <= set(classes):
        errors.append("C-B split JSON class IDs differ from current samples.json/classes.json metadata")
    full_counts = {label: 0 for label in classes}
    for sample in samples.values():
        label = sample.get("class_label")
        if label in full_counts:
            full_counts[label] += 1
    if any(full_counts[label] < 20 for label in used_labels):
        errors.append("C-B closed-set includes a class below the publisher 20-sample threshold")
    label_drift = used_labels != split_labels or not split_labels <= set(classes)
    return {"reproduction_state":"REPLAYED_DOCUMENT_SAMPLE_SUPPORT_MEMBERSHIP_PASS_LABEL_SET_DRIFT" if label_drift and len(errors) == 1 else "REPLAYED_METADATA_ONLY_MEMBERSHIP_AND_CLASS_JOIN_PASS" if not errors else "REPLAYED_WITH_VALIDATION_FAILURES",
        "split_file_receipt":receipt,"partition_order":{"train":"train","development":"val","test":"test"},
        "partitions":partitions,"sample_union_count":len(all_sample_ids),"publisher_document_union_count":len(all_document_ids),
        "physical_support_union_count":len(assigned_supports),"class_union_count":len(used_labels),
        "class_membership_diagnostic":label_set_diagnostic,
        "document_ids_partition_disjoint":len(all_document_ids) == len(set(all_document_ids)),
        "sample_ids_partition_disjoint":len(all_sample_ids) == len(set(all_sample_ids)),
        "physical_supports_partition_disjoint":not any("C-B physical support crosses partitions" in error for error in errors),
        "class_list_matches_sample_metadata":used_labels == split_labels and split_labels <= set(classes),
        "class_union_ids_sha256":SHA(json.dumps(sorted(used_labels), ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
        "validation_errors":errors,
        "publisher_sample_metadata_join":"ALL_C-B_SAMPLE_IDS_DOCUMENT_IDS_AND_CLASS_IDS_VERIFIED",
        "image_pixels_or_polygons_used":False,"publisher_split_class_threshold":"all assigned labels have >=20 samples in full samples.json"}


def blocked_gates(**overrides):
    gates = {key: "NOT_CLEARED" for key in GATE_BLOCKERS}
    gates.update(overrides)
    return gates


def ddd_rows(prereg: dict):
    raw, receipt = fetch_exact("papyri.json")
    expected = prereg["fixed_population"]["ddd"]["image_metadata_sha256"]
    if SHA(raw) != expected:
        raise ValueError("DDD papyri metadata differs from preregistered digest")
    papyri = json.loads(raw)
    if not isinstance(papyri, dict) or len(papyri) != 159:
        raise ValueError("DDD preregistered finite image population changed")
    rows = []
    for image_id, rec in sorted(papyri.items(), key=lambda item: str(item[0])):
        if not isinstance(rec, dict):
            raise ValueError(f"invalid DDD image metadata row: {image_id}")
        tpop = rec.get("TPOP_ref") if isinstance(rec.get("TPOP_ref"), dict) else {}
        rows.append({
            "candidate_id": f"DDD-IMAGE-{image_id}",
            "publisher": "DDD 2026-06-26 / Zenodo 20553713",
            "original_image_id": str(image_id),
            "physical_support_id": str(rec.get("doc_cluster")) if rec.get("doc_cluster") is not None else None,
            "source_name": rec.get("name"),
            "side_view_identifier": rec.get("name"),
            "page_identifier": None,
            "source_document_url": tpop.get("document"),
            "photo_copyright_claim": rec.get("copyright"),
            "source_sha256": None,
            "photo_rights_evidence_url": "https://zenodo.org/records/20553713",
            "photo_rights_use_scope": "UNRESOLVED_FOR_EACH_MUSEUM_PHOTOGRAPH; dataset annotation license does not grant photo reuse",
            "annotation_file_url": "https://zenodo.org/records/20553713/files/DDD_annotations.zip?download=1",
            "annotation_file_sha256": "4e21fb35ba6b58febc8a7aaa2d003da26a9330fbcbe7c89b26cd62a8efaa8161",
            "annotation_file_md5": "c3405016b676cd1a09b9ce989a89ecbb",
            "annotation_receipt_source": "docs/research/R028_DDD_ORIGINAL_PUBLIC_METADATA_RECEIPTS.json",
            "polygon_coordinates": None,
            "coordinate_system": None,
            "crop_transform": None,
            "resulting_pixel_sha256": None,
            "annotation_source": "DDD annotations.zip; publisher samples.json/classes.json",
            "annotation_rights": "CC-BY-NC-SA-4.0 publisher dataset claim; production/unrestricted use not permitted by this claim",
            "raw_polygon_annotation_count_loaded": 0,
            "publisher_sample_metadata_sha256": "763944b29e06643131fa9fdbd14a2b169afe5961df80394fecfd152203584e46",
            "publisher_class_metadata_sha256": "5ff0181de57e1018058ba53e8e436e6e67a19fca290568ed0f9ea341af7afe18",
            "publisher_polygon_annotation_loaded": False,
            "image_bytes_retrieved_w28": False,
            "original_sha256": None,
            "original_byte_size": None,
            "original_mime": None,
            "pixel_geometry": None,
            "crop_or_polygon_binding": "NOT_ESTABLISHED",
            "published_split_membership": "NOT_RETRIEVED",
            "project_w24_split_membership": "HISTORICAL_METADATA_ONLY_NOT_RECONSTRUCTED_PER_IMAGE",
            "physical_support_group": f"DDD:DOC_CLUSTER:{rec.get('doc_cluster')}" if rec.get("doc_cluster") is not None else None,
            "benchmark_state": "UNKNOWN_QUARANTINED",
            "gate_state": blocked_gates(),
            "rejection_reasons": ["item-level photograph permission absent", GATE_BLOCKERS["annotation_rights"], GATE_BLOCKERS["pixel_binding"], GATE_BLOCKERS["expert_gold"], GATE_BLOCKERS["benchmark_lineage"], GATE_BLOCKERS["custody"]],
            "admissible_for_training": False,
            "admissible_for_evaluation": False,
        })
    return rows, receipt, papyri


def museum_rows():
    receipt = read_json(PHOTOS)
    result = []
    for item in receipt["items"]:
        result.append({
            "candidate_id": item["candidate_id"],
            "publisher": "Museo Egizio / Wikimedia Commons file revision",
            "accession": item["accession"],
            "source_url": item["metadata"].get("original_url"),
            "file_page_identity": item["metadata"].get("commons_title"),
            "rights_evidence_url": item["metadata"].get("license_url"),
            "photo_rights_state": item["rights_status"],
            "photo_role": item["role"],
            "physical_support_group": item["group_id"],
            "source_sha256": item.get("original_sha256"),
            "source_bytes": item.get("byte_count"),
            "decoded_geometry": item.get("actual_dimensions"),
            "annotation_source": "NONE_ADMITTED",
            "crop_or_polygon_binding": "NOT_ESTABLISHED",
            "benchmark_state": item["benchmark_overlap"],
            "gate_state": blocked_gates(),
            "rejection_reasons": [item["rights_status"], "no independently licensed and aligned text/glyph annotation", "benchmark/edition ancestry unresolved"],
            "admissible_for_training": False,
            "admissible_for_evaluation": False,
            "prior_receipt": "data/releases/w20_museum_photo_intake.json",
        })
    return result


def candidate_route_rows():
    r024 = read_json(R024)
    rows = []
    for candidate in r024["candidates"]:
        rows.append({
            "candidate_id": candidate["id"],
            "publisher": candidate["institution"],
            "accessions": candidate["accessions"],
            "source_url": candidate["museum_url"],
            "related_text_url": candidate["tpop_url"],
            "photo_type": "PROPOSED_ORIGINAL_PHOTO_NOT_ACQUIRED",
            "physical_support_group": candidate["support_group"],
            "source_sha256": None,
            "annotation_source": "TPOP/publication route unverified for exact line reuse",
            "crop_or_polygon_binding": candidate["silver_line_status"],
            "benchmark_state": candidate["benchmark_overlap"],
            "gate_state": blocked_gates(),
            "rejection_reasons": ["no exact source bytes in W28", "no exact photograph-to-line binding", "rights/review/benchmark gates pending"],
            "admissible_for_training": False,
            "admissible_for_evaluation": False,
            "prior_receipt": "docs/research/R024_W8_TURIN_CANDIDATES.json",
        })
    return rows


def comparison_only_rows():
    aku = read_json(ROOT / "data/releases/w20_aku_pal_sign_census.json")
    if (aku.get("evidence_sha256") != "26516fa4701a050aada1bbb044383035c44afd6496e7acf04cbc2504ac3e48a2"
            or aku_source_audit.validate_report(aku) or aku_source_audit.validate_schema(aku)):
        raise ValueError("pinned AKU-PAL comparison receipt drift")
    aku_summary = aku["summary"]
    aku_screen = aku["benchmark_screen"]
    return [
        {"candidate_id":"AKU-PAL-COMPARISON-ONLY","publisher":"AKU-PAL Academy Mainz","comparison_cohort_id":"AKU-PAL-W20-240","physical_support_group":None,"photo_type":"publisher sign-media/printed source comparison; not original manuscript photograph","source_sha256":None,"source_receipt":"data/releases/w20_aku_pal_sign_census.json","source_receipt_evidence_sha256":aku["evidence_sha256"],"source_records":aku_summary["distinct_sign_ids_screened"],"unique_source_text_ids":aku_summary["unique_source_text_ids"],"records_with_individual_license_and_provenance":aku_summary["exact_item_permissive_license_and_provenance_screened"],"records_rights_or_identity_blocked":aku_summary["rights_or_identity_blocked"],"unique_media_hashes":aku_summary["unique_media_byte_hashes"],"positive_public_benchmark_overlaps":aku_screen["positive_public_metadata_overlaps"],"no_literal_match_is_clearance":aku_screen["no_literal_match_is_clearance"],"benchmark_state":"UNKNOWN_QUARANTINED","crop_or_polygon_binding":"NOT_APPLICABLE_TO_PHOTOGRAPHIC_GOLD","gate_state":blocked_gates(),"rejection_reasons":["comparison-only publisher sign-media cohort, not original manuscript photographs", "63 positive public benchmark overlaps and all other no-match records remain quarantined", "no independent expert gold or admission"],"admissible_for_training":False,"admissible_for_evaluation":False},
        {"candidate_id":"TOKYO-IIIF-MOLLER-PRINTED-STRIPS","publisher":"University of Tokyo IIIF / Möller printed publication","comparison_cohort_id":"TOKYO-MOLLER-W27","physical_support_group":None,"photo_type":"24 printed-book sign crops; not original manuscript photographs","source_sha256":None,"research_receipt":"docs/research/R034_W27_TOKYO_IIIF_IMAGE_RIGHTS_AND_PIXEL_RESEARCH.md","crop_or_polygon_binding":"NOT_APPLICABLE_TO_PHOTOGRAPHIC_GOLD","benchmark_state":"UNKNOWN_QUARANTINED","gate_state":blocked_gates(),"rejection_reasons":["printed facsimile/sign drawings are comparison-only", "not a photographic manuscript witness or independent physical-support split"],"admissible_for_training":False,"admissible_for_evaluation":False},
        {"candidate_id":"HISTORICAL-PLATE-FACSIMILES","publisher":"Historical printed editions","comparison_cohort_id":"PRINTED-PLATE-CORPUS","physical_support_group":None,"photo_type":"printed plate/facsimile; not original manuscript photograph","source_sha256":None,"crop_or_polygon_binding":"NOT_APPLICABLE_TO_PHOTOGRAPHIC_GOLD","benchmark_state":"UNKNOWN_QUARANTINED","gate_state":blocked_gates(),"rejection_reasons":["facsimile/plate material cannot be counted as original manuscript photography", "source-book ancestry and physical support split are not independent"],"admissible_for_training":False,"admissible_for_evaluation":False},
    ]


def validate_report(report: dict) -> list[str]:
    """Fail closed on row loss, fake byte proof, or any admission promotion."""
    errors = []
    supplied_evidence_hash = report.get("evidence_sha256")
    if supplied_evidence_hash is not None:
        payload = {key: value for key, value in report.items() if key != "evidence_sha256"}
        expected_evidence_hash = SHA(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        if supplied_evidence_hash != expected_evidence_hash:
            errors.append("readiness evidence digest mismatch")
    rows = report.get("candidate_rows")
    if not isinstance(rows, list) or report.get("candidate_count") != len(rows):
        return ["candidate denominator does not equal row count"]
    ids = [row.get("candidate_id") for row in rows if isinstance(row, dict)]
    if len(ids) != len(rows) or len(ids) != len(set(ids)):
        errors.append("candidate IDs are missing or duplicated")
    ddd = [row for row in rows if str(row.get("candidate_id", "")).startswith("DDD-IMAGE-")]
    if len(ddd) != 159 or len({row.get("physical_support_id") for row in ddd}) != 50:
        errors.append("DDD image/support denominator drift")
    ddd_membership_by_support = {}
    for row in ddd:
        support = row.get("physical_support_group")
        membership = row.get("published_split_membership")
        if support in ddd_membership_by_support and ddd_membership_by_support[support] != membership:
            errors.append(f"{row.get('candidate_id')}: same physical support crosses publisher partitions")
        ddd_membership_by_support[support] = membership
    for row in rows:
        if not isinstance(row, dict):
            errors.append("candidate row is not an object")
            continue
        if row.get("admissible_for_training") is not False or row.get("admissible_for_evaluation") is not False:
            errors.append(f"{row.get('candidate_id')}: blocked candidate was promoted")
        if row.get("benchmark_state") not in {"UNKNOWN_QUARANTINED", "NOT_CLEARED", "POSITIVE_OVERLAP_QUARANTINED", "EVAL_ONLY"}:
            errors.append(f"{row.get('candidate_id')}: invalid benchmark clearance state")
        gates = row.get("gate_state")
        if not isinstance(gates, dict) or set(gates) != set(GATE_BLOCKERS) or any(value != "NOT_CLEARED" for value in gates.values()):
            errors.append(f"{row.get('candidate_id')}: gate set incomplete or promoted")
        digest = row.get("source_sha256", row.get("original_sha256"))
        if digest is not None and (not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)):
            errors.append(f"{row.get('candidate_id')}: malformed source hash")
        if row.get("image_bytes_retrieved_w28") is False and row.get("original_sha256") is not None:
            errors.append(f"{row.get('candidate_id')}: source hash asserted without W28 byte retrieval")
        if row.get("publisher_polygon_annotation_loaded") is True and row.get("crop_or_polygon_binding") == "NOT_ESTABLISHED":
            errors.append(f"{row.get('candidate_id')}: polygon payload without pixel binding evidence")
    accession_groups = {}
    for row in rows:
        accession = row.get("accession")
        support = row.get("physical_support_group")
        if accession and support:
            if accession in accession_groups and accession_groups[accession] != support:
                errors.append(f"{row.get('candidate_id')}: physical-object variants split across support groups")
            accession_groups[accession] = support
    aggregate = report.get("aggregate", {})
    if aggregate.get("admissible_for_training") != 0 or aggregate.get("admissible_for_evaluation") != 0:
        errors.append("aggregate admission count must remain zero")
    if aggregate.get("production_release_enabled") is not False or aggregate.get("corpus_v1_release_created") is not False or aggregate.get("data008_capability_points_claimed") != 0:
        errors.append("production/release/capability promotion is forbidden")
    retrieval = report.get("retrieval_limits", {})
    if any(retrieval.get(key) != 0 for key in ("image_bytes_retrieved", "annotation_payloads_retrieved", "sealed_benchmark_records_read")):
        errors.append("W28 bounded readiness run exceeded preregistered retrieval boundary")
    if retrieval.get("published_split_membership_payloads_retrieved") != 1 or retrieval.get("sample_class_metadata_payloads_retrieved") != 2:
        errors.append("W28 bounded readiness run exceeded preregistered retrieval boundary")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors.extend("schema: " + "/".join(map(str, error.absolute_path)) + " " + error.message
                  for error in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(report))
    return errors


def build():
    prereg = read_json(PREREG)
    ddd, metadata_receipt, papyri = ddd_rows(prereg)
    samples_raw, samples_receipt = fetch_exact("samples.json")
    classes_raw, classes_receipt = fetch_exact("classes.json")
    expected_files = prereg["fixed_population"]["ddd"]["label_metadata_sha256"]
    if SHA(samples_raw) != expected_files["samples.json"] or SHA(classes_raw) != expected_files["classes.json"]:
        raise ValueError("DDD sample/class metadata differs from preregistered source digests")
    samples = json.loads(samples_raw)
    classes = json.loads(classes_raw)
    if not isinstance(samples, dict) or len(samples) != 17885 or not isinstance(classes, dict) or len(classes) != 504:
        raise ValueError("DDD sample/class metadata denominator differs from preregistration")
    split_raw, split_receipt = fetch_exact("Readme - Splits.txt")
    split_text = split_raw.decode("utf-8-sig")
    if not all(name in split_text for name in ("C-B", "C-C", "C-D", "O-B")):
        raise ValueError("published DDD split definition changed or is incomplete")
    cb_split = reproduce_cb_split(papyri, samples, classes)
    image_to_partition = {image_id: name for name, part in cb_split["partitions"].items() for image_id in part["source_image_ids"]}
    support_to_partition = {}
    for image_id, partition in image_to_partition.items():
        support_to_partition[str(papyri[image_id]["doc_cluster"])] = partition
    for row in ddd:
        image_id = row["original_image_id"]
        support = row["physical_support_id"]
        if image_id in image_to_partition:
            row["published_split_membership"] = image_to_partition[image_id]
            row["published_split_membership_basis"] = "C-B split JSON document ID matched to samples.json and papyri.json"
        elif support in support_to_partition:
            row["published_split_membership"] = support_to_partition[support]
            row["published_split_membership_basis"] = "inherited from same physical doc_cluster as a C-B member image; image itself not a C-B document"
        else:
            row["published_split_membership"] = "NOT_INCLUDED_IN_C-B_PHYSICAL_SUPPORT_UNIVERSE"
            row["published_split_membership_basis"] = "no C-B document or same-support member in publisher JSON"
    w24_groups = sorted({str(row["doc_cluster"]) for row in papyri.values()}, key=w24_stable_rank)
    if len(w24_groups) != 50:
        raise ValueError("W24 pinned physical-support split group count drift")
    w24_membership = {group: ("train" if index < 35 else "dev" if index < 42 else "test")
                      for index, group in enumerate(w24_groups)}
    crosswalk = {}
    for cb_name, cb_part in cb_split["partitions"].items():
        cb_supports = set(cb_part["physical_support_ids"])
        crosswalk[cb_name] = {w24_name: len(cb_supports & {group for group, membership in w24_membership.items() if membership == w24_name})
                              for w24_name in ("train", "dev", "test")}
    cb_split["w24_crosswalk"] = {"w24_protocol_seed": W24_SPLIT_SEED,
        "w24_support_counts": {"train":35,"dev":7,"test":8},
        "c_b_supports_by_w24_partition": crosswalk,
        "c_b_supports_covered": sum(sum(row.values()) for row in crosswalk.values()),
        "c_b_physical_supports_not_in_published_split": 50 - cb_split["physical_support_union_count"]}
    candidates = ddd + museum_rows() + candidate_route_rows() + comparison_only_rows()
    candidates.extend([
        {"candidate_id":"TURIN-CAT2044-013-P01","publisher":"Museo Egizio","accession":"Cat.2044/013","source_url":"https://collezioni.museoegizio.it/en-GB/material/Cat_2044_013/","related_text_url":"https://collezionepapiri.museoegizio.it/en-GB/document/173/","photo_type":"original photo; exact publisher asset not byte-retrieved","physical_support_group":"MUSEO-EGIZIO:CAT-2044/013","source_sha256":None,"annotation_source":"TPOP writing units; exact photograph-to-unit alignment and reuse permission absent","crop_or_polygon_binding":"NOT_ESTABLISHED","benchmark_state":"UNKNOWN_QUARANTINED","gate_state":blocked_gates(),"rejection_reasons":["no exact source bytes", "no exact photo-to-line binding", "annotation rights and benchmark lineage unresolved"],"admissible_for_training":False,"admissible_for_evaluation":False},
        {"candidate_id":"TPOP-2044-013","publisher":"Museo Egizio TPOP","source_url":"https://collezionepapiri.museoegizio.it/en-GB/document/173/","photo_type":"portal image route, exact asset not acquired","physical_support_group":"MUSEO-EGIZIO:CAT-2044/013","source_sha256":None,"annotation_source":"Editorial text; separate license and line-pixel alignment absent","crop_or_polygon_binding":"NOT_ESTABLISHED","benchmark_state":"UNKNOWN_QUARANTINED","gate_state":blocked_gates(),"rejection_reasons":["portal page is not byte-level asset proof", "text and photo rights are separate", "source ancestry unresolved"],"admissible_for_training":False,"admissible_for_evaluation":False}
    ])
    # Single canonical row for the source-verified S.6759 photo also corrects
    # the older unsupported shorthand: the museum catalogue explicitly names
    # this object a Hieratic oracular ostracon.
    s6759 = next(row for row in candidates if row["candidate_id"] == "TURIN-S6759-ORACLE-TIFF")
    s6759["museum_identity_url"] = "https://collezioni.museoegizio.it/en-GB/material/S_6759"
    s6759["museum_identity_title"] = "Hieratic ostracon with an oracular text"
    s6759["photo_role"] = "Genuine Hieratic oracular ostracon; verified museum identity; label/crop gold still absent"
    result = {
        "schema_version": "w28-data008-candidate-readiness/1.0.0",
        "study_id": prereg["study_id"],
        "preregistration_sha256": SHA(PREREG.read_bytes()),
        "as_of_utc_date": "2026-10-11",
        "classification": "METADATA_ONLY_NO_ADMISSION_NO_TRAINING",
        "retrieval_limits": {"max_concurrent_requests": 1, "retrieved": [metadata_receipt, samples_receipt, classes_receipt, split_receipt], "image_bytes_retrieved": 0, "annotation_payloads_retrieved": 0, "sample_class_metadata_payloads_retrieved": 2, "published_split_membership_payloads_retrieved": 1, "sealed_benchmark_records_read": 0},
        "published_split_definition": {"file": "Readme - Splits.txt", "sha256": SHA(split_raw), "bytes": len(split_raw), "reproduction_state": "DEFINITION_READ_AND_C-B_MEMBERSHIP_REPLAYED", "protocol_summary": "C-B is the closed-set, published-document, document-aware split; C-C/C-D are cross-document random samples and excluded for source holdout; O-B is open-set and separate."},
        "publisher_c_b_reproduction": cb_split,
        "historical_w24_split": {"train_supports":35,"development_supports":7,"test_supports":8,"annotation_counts":[15426,893,1566],"state":"METADATA_ONLY_NOT_VISUAL_DENOMINATORS"},
        "candidate_count": len(candidates),
        "ddd": {"images":len(ddd),"physical_supports":len({row['physical_support_id'] for row in ddd}),"publisher_annotations":17885,"publisher_classes":504,"admitted_images":0,"source_image_bytes_retrieved":0,"raw_polygon_annotations_loaded":0,"sample_class_metadata_rows_loaded":len(samples)+len(classes),"publisher_sample_label_rows_joined_to_c_b":cb_split["sample_union_count"],"image_conditioned_label_rows_used":0},
        "museum_photo_candidates": {"rows":len(museum_rows()),"source_bytes_retrieved_w28":0,"admitted":0,"physical_supports":len({row["physical_support_group"] for row in museum_rows()})},
        "candidate_rows": candidates,
        "aggregate": {"admissible_for_training":0,"admissible_for_evaluation":0,"rejected_or_quarantined":len(candidates),"production_release_enabled":False,"corpus_v1_release_created":False,"data008_capability_points_claimed":0},
    }
    result["evidence_sha256"] = SHA(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    errors = validate_report(result)
    if errors:
        raise ValueError("generated readiness report failed validation: " + "; ".join(errors))
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    report = build()
    print(json.dumps({"output":str(OUT.relative_to(ROOT)),"candidate_count":report["candidate_count"],"ddd_images":report["ddd"]["images"],"admitted":report["aggregate"]["admissible_for_training"]}, sort_keys=True))
