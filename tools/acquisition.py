"""Dry-run policy planner and validator for data acquisition manifests."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import sys
import tempfile
import secrets
import stat
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode, urlsplit

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
COMMONS_CANDIDATES = {
    "CAT2044": {
        "title": "File:Journal of year 1 of Ramesses VI on recto and verso - Museo Egizio Turin C 2044 p01.jpg",
        "page_url": "https://commons.wikimedia.org/wiki/File:Journal_of_year_1_of_Ramesses_VI_on_recto_and_verso_-_Museo_Egizio_Turin_C_2044_p01.jpg",
        "object_url": "https://collezioni.museoegizio.it/en-GB/material/Cat_2044/",
        "papyrus_record_url": "https://collezionepapiri.museoegizio.it/en-GB/document/173/",
        "accession": "Cat.2044/013",
        "filename": "CAT2044-013-commons-original.jpg",
        "original_path": "/wikipedia/commons/e/e5/Journal_of_year_1_of_Ramesses_VI_on_recto_and_verso_-_Museo_Egizio_Turin_C_2044_p01.jpg",
        "sha1": "752747405048f358147a7b1f0f697720c338394b",
        "size": 2649239,
        "width": 7063,
        "height": 3947,
        "timestamp": "2024-02-08T16:25:22Z",
        "source_revision": "https://commons.wikimedia.org/w/index.php?title=File:Journal_of_year_1_of_Ramesses_VI_on_recto_and_verso_-_Museo_Egizio_Turin_C_2044_p01.jpg&oldid=900807568",
        "allowed_local_research_inspection": True,
    },
    "CAT1880": {
        "title": "File:The so-called 'Strike Papyrus' written by Amunnakht, papyurs - Museo Egizio (Turin) C 1880 p01.jpg",
        "page_url": "https://commons.wikimedia.org/wiki/File:The_so-called_%27Strike_Papyrus%27_written_by_Amunnakht%2C_papyurs_-_Museo_Egizio_%28Turin%29_C_1880_p01.jpg",
        "object_url": "https://collezioni.museoegizio.it/en-GB/material/Cat_1880/",
        "papyrus_record_url": "https://collezionepapiri.museoegizio.it/en-GB/document/131/",
        "accession": "Cat.1880",
        "filename": "CAT1880-commons-original.jpg",
        "original_path": None,
        "sha1": None,
        "size": None,
        "width": 6941,
        "height": 3431,
        "timestamp": None,
        "source_revision": "https://commons.wikimedia.org/w/index.php?title=File:The_so-called_%27Strike_Papyrus%27_written_by_Amunnakht%2C_papyurs_-_Museo_Egizio_%28Turin%29_C_1880_p01.jpg&oldid=1114729465",
        "allowed_local_research_inspection": False,
    },
}
COMMONS_API_HOST = "commons.wikimedia.org"
COMMONS_FILE_HOST = "upload.wikimedia.org"
COMMONS_API_TIMEOUT_SECONDS = 20
MAX_COMMONS_IMAGE_BYTES = 8 * 1024 * 1024
RIME_FIGURE_HOST = "rivista.museoegizio.it"
RIME_FIGURE_PATH = "/wp-content/themes/annotum-base/assets/articles/4418/content/6/original.tif"
RIME_FIGURE_URL = f"https://{RIME_FIGURE_HOST}{RIME_FIGURE_PATH}"
RIME_FIGURE_SHA256 = "c4b878ca5b6b6c22d0b4b1574d4f8e95072d651c38cb03d49f3cf73c5f6052b9"
RIME_FIGURE_BYTES = 36_023_444
MAX_RIME_FIGURE_BYTES = 40 * 1024 * 1024


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


def _public_https_get(host: str, path: str, byte_limit: int) -> tuple[int, str, bytes, dict[str, str]]:
    """Single bounded HTTPS GET to a fixed caller-allowlisted public host; never follows redirects."""
    if host not in {COMMONS_API_HOST, COMMONS_FILE_HOST, RIME_FIGURE_HOST} or not path.startswith("/") or byte_limit <= 0:
        raise AcquisitionError("COMMONS_REQUEST_OUTSIDE_ALLOWLIST")
    if host == RIME_FIGURE_HOST and (path != RIME_FIGURE_PATH or byte_limit != MAX_RIME_FIGURE_BYTES):
        raise AcquisitionError("RIME_REQUEST_OUTSIDE_ALLOWLIST")
    answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    addresses = sorted({answer[4][0] for answer in answers})
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise AcquisitionError("COMMONS_DNS_NOT_PUBLIC")
    connection = _PinnedHTTPSConnection(host, addresses[0], COMMONS_API_TIMEOUT_SECONDS)
    try:
        connection.request("GET", path, headers={
            "Accept": "application/json, image/jpeg, image/tiff",
            "Accept-Encoding": "identity",
            "User-Agent": "Hieratic-AI/0.1 (https://github.com/m7mdehab/hieratic-ai; bounded source-specific research acquisition)",
            "Connection": "close",
        })
        response = connection.getresponse()
        headers = {key.lower(): value for key, value in response.getheaders()}
        if response.status != 200:
            raise AcquisitionError(f"COMMONS_HTTP_STATUS_{response.status}")
        if headers.get("content-encoding", "identity").lower() not in {"", "identity"}:
            raise AcquisitionError("COMMONS_CONTENT_ENCODING_UNSUPPORTED")
        declared = headers.get("content-length")
        if declared and int(declared) > byte_limit:
            raise AcquisitionError("COMMONS_RESPONSE_TOO_LARGE")
        body = response.read(byte_limit + 1)
        if len(body) > byte_limit:
            raise AcquisitionError("COMMONS_RESPONSE_TOO_LARGE")
        return response.status, headers.get("content-type", "").split(";", 1)[0].strip().lower(), body, headers
    finally:
        connection.close()


def _commons_imageinfo(candidate_id: str, transport: Callable[..., tuple[int, str, bytes, dict[str, str]]] | None = None) -> tuple[dict[str, Any], str]:
    candidate = COMMONS_CANDIDATES.get(candidate_id)
    if candidate is None:
        raise AcquisitionError("COMMONS_CANDIDATE_NOT_ALLOWLISTED")
    if not candidate["allowed_local_research_inspection"]:
        raise AcquisitionError("COMMONS_CANDIDATE_HELD_FOR_BENCHMARK_QUARANTINE_REVIEW")
    params = urlencode({
        "action": "query", "format": "json", "formatversion": "2", "prop": "imageinfo",
        "titles": candidate["title"],
        "iiprop": "url|size|width|height|sha1|timestamp|mime|user|comment|extmetadata",
    })
    request = transport or _public_https_get
    status, content_type, body, _headers = request(COMMONS_API_HOST, f"/w/api.php?{params}", 512 * 1024)
    if status != 200 or content_type != "application/json":
        raise AcquisitionError("COMMONS_METADATA_RESPONSE_INVALID")
    response_sha256 = hashlib.sha256(body).hexdigest()
    try:
        payload = json.loads(body)
        pages = payload["query"]["pages"]
        page = pages[0] if isinstance(pages, list) and len(pages) == 1 else None
        image = page["imageinfo"][0] if page and len(page.get("imageinfo", [])) == 1 else None
    except (KeyError, TypeError, json.JSONDecodeError, IndexError) as exc:
        raise AcquisitionError("COMMONS_METADATA_RESPONSE_MALFORMED") from exc
    if not page or page.get("title") != candidate["title"] or page.get("ns") != 6 or page.get("missing") is True or not image:
        raise AcquisitionError("COMMONS_FILE_IDENTITY_MISMATCH")
    license_meta = image.get("extmetadata", {})
    short_name = re.sub(r"<[^>]*>", "", str(license_meta.get("LicenseShortName", {}).get("value", ""))).strip()
    license_url = str(license_meta.get("LicenseUrl", {}).get("value", "")).strip()
    credit = re.sub(r"<[^>]*>", " ", str(license_meta.get("Credit", {}).get("value", "")))
    credit = " ".join(credit.split())
    if short_name not in {"CC0", "CC0 1.0"} or "creativecommons.org/publicdomain/zero/1.0" not in license_url.lower():
        raise AcquisitionError("COMMONS_EXACT_FILE_LICENSE_NOT_CC0")
    if "Museo Egizio" not in credit:
        raise AcquisitionError("COMMONS_FILE_CREDIT_DOES_NOT_IDENTIFY_MUSEO_EGIZIO")
    image_url = image.get("url")
    parts = urlsplit(image_url or "")
    if (
        parts.scheme != "https" or parts.hostname != COMMONS_FILE_HOST or parts.path != candidate["original_path"]
        or parts.username or parts.password or parts.fragment
    ):
        raise AcquisitionError("COMMONS_ORIGINAL_URL_MISMATCH")
    expected = {
        "size": candidate["size"], "width": candidate["width"], "height": candidate["height"],
        "sha1": candidate["sha1"], "mime": "image/jpeg", "timestamp": candidate["timestamp"],
    }
    for field, expected_value in expected.items():
        if image.get(field) != expected_value:
            raise AcquisitionError(f"COMMONS_PINNED_FILE_{field.upper()}_MISMATCH")
    return {"pageid": page["pageid"], **{key: image[key] for key in expected}, "url": image_url,
            "license_short_name": short_name, "license_url": license_url, "credit": credit}, response_sha256


def _has_reparse_component(path: Path) -> bool:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            return True
    return False


def _default_private_vault(wave: str = "W8") -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        raise AcquisitionError("COMMONS_PRIVATE_VAULT_REQUIRES_LOCALAPPDATA")
    if wave not in {"W8", "W9"}:
        raise AcquisitionError("COMMONS_PRIVATE_VAULT_WAVE_NOT_ALLOWLISTED")
    root = Path(local) / "HieraticAI" / "private-artifacts" / wave
    repo = ROOT.resolve()
    if root.resolve(strict=False) == repo or repo in root.resolve(strict=False).parents:
        raise AcquisitionError("COMMONS_PRIVATE_VAULT_MUST_BE_OUTSIDE_REPOSITORY")
    return root


def _publish_private_file(root: Path, filename: str, data: bytes) -> Path:
    """Publish once into a private vault, without following swapped POSIX parents.

    POSIX uses an open O_NOFOLLOW directory handle for staging, link and cleanup;
    Windows retains a conservative local-vault path, validating directory identity
    before and after publication (Windows Python lacks POSIX dir_fd hard-link APIs).
    """
    root = root.absolute()
    if filename not in {"CAT2044-013-commons-original.jpg", "CAT1883-CAT2095-RIME-fig6-recto-original.tif"}:
        raise AcquisitionError("COMMONS_PRIVATE_FILENAME_NOT_ALLOWLISTED")
    root.mkdir(parents=True, exist_ok=True)
    if _has_reparse_component(root) or not root.is_dir():
        raise AcquisitionError("COMMONS_PRIVATE_VAULT_HAS_REPARSE_COMPONENT")
    resolved_root = root.resolve(strict=True)
    if resolved_root != root:
        raise AcquisitionError("COMMONS_PRIVATE_VAULT_RESOLVED_PATH_CHANGED")
    target = root / filename
    if target.exists() or target.is_symlink():
        raise AcquisitionError("COMMONS_PRIVATE_TARGET_EXISTS_OR_ESCAPES_VAULT")

    if os.name == "posix" and hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NOFOLLOW"):
        directory_fd: int | None = None
        prefix = ".w9-" if filename.startswith("CAT1883-") else ".w8-"
        temporary_name = f"{prefix}{secrets.token_hex(16)}.part"
        published = False
        succeeded = False
        try:
            directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            identity = os.fstat(directory_fd)
            if not stat.S_ISDIR(identity.st_mode):
                raise AcquisitionError("COMMONS_PRIVATE_VAULT_NOT_DIRECTORY")
            opened_fd = os.open(
                temporary_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600, dir_fd=directory_fd,
            )
            with os.fdopen(opened_fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(
                temporary_name, filename, src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd, follow_symlinks=False,
            )
            published = True
            try:
                current = os.stat(root, follow_symlinks=False)
                if not stat.S_ISDIR(current.st_mode) or (
                    current.st_dev, current.st_ino
                ) != (identity.st_dev, identity.st_ino):
                    raise AcquisitionError("COMMONS_PRIVATE_VAULT_CHANGED_DURING_WRITE")
            except OSError as exc:
                raise AcquisitionError("COMMONS_PRIVATE_VAULT_CHANGED_DURING_WRITE") from exc
            os.fsync(directory_fd)
            succeeded = True
            return target
        except FileExistsError as exc:
            raise AcquisitionError("COMMONS_PRIVATE_TARGET_EXISTS_OR_ESCAPES_VAULT") from exc
        except OSError as exc:
            raise AcquisitionError(f"COMMONS_PRIVATE_PUBLISH_FAILED:{type(exc).__name__}") from exc
        finally:
            if directory_fd is not None:
                if published and not succeeded:
                    try:
                        os.unlink(filename, dir_fd=directory_fd)
                    except OSError:
                        pass
                try:
                    os.unlink(temporary_name, dir_fd=directory_fd)
                except FileNotFoundError:
                    pass
                finally:
                    os.close(directory_fd)

    # Windows local-private-vault fallback: preserve original functionality
    # and verify immutable destination directory identity on either side.
    before = root.stat()
    temporary = None
    published = False
    succeeded = False
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=root,
            prefix=".w9-" if filename.startswith("CAT1883-") else ".w8-",
            suffix=".part", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        current = root.stat()
        if (before.st_dev, before.st_ino) != (current.st_dev, current.st_ino):
            raise AcquisitionError("COMMONS_PRIVATE_VAULT_CHANGED_DURING_WRITE")
        os.link(temporary, target)
        published = True
        current = root.stat()
        if (before.st_dev, before.st_ino) != (current.st_dev, current.st_ino):
            raise AcquisitionError("COMMONS_PRIVATE_VAULT_CHANGED_DURING_WRITE")
        succeeded = True
        return target
    except FileExistsError as exc:
        raise AcquisitionError("COMMONS_PRIVATE_TARGET_EXISTS_OR_ESCAPES_VAULT") from exc
    except OSError as exc:
        raise AcquisitionError(f"COMMONS_PRIVATE_PUBLISH_FAILED:{type(exc).__name__}") from exc
    finally:
        if published and not succeeded:
            try:
                current = root.stat()
                if (before.st_dev, before.st_ino) == (current.st_dev, current.st_ino):
                    target.unlink(missing_ok=True)
            except OSError:
                pass
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def acquire_commons_candidate(
    candidate_id: str,
    *,
    transport: Callable[..., tuple[int, str, bytes, dict[str, str]]] | None = None,
    vault_root: Path | None = None,
    now: dt.datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    """Acquire one fixed CC0 image into the user-local vault; never admits or labels it as training data."""
    candidate_id = candidate_id.upper()
    candidate = COMMONS_CANDIDATES.get(candidate_id)
    if candidate is None or not candidate["allowed_local_research_inspection"]:
        raise AcquisitionError("COMMONS_CANDIDATE_NOT_AUTHORIZED_FOR_LOCAL_INSPECTION")
    request = transport or _public_https_get
    info, api_digest = _commons_imageinfo(candidate_id, request)
    image_parts = urlsplit(info["url"])
    # The API may append cache-busting/tracking query parameters. The immutable
    # original is identified by its pinned upload.wikimedia.org path and SHA1;
    # request only that path and keep the API's full URL as provenance.
    status, content_type, image_bytes, headers = request(COMMONS_FILE_HOST, image_parts.path, MAX_COMMONS_IMAGE_BYTES)
    if status != 200 or content_type != "image/jpeg":
        raise AcquisitionError("COMMONS_IMAGE_RESPONSE_INVALID")
    if len(image_bytes) != info["size"] or len(image_bytes) > MAX_COMMONS_IMAGE_BYTES:
        raise AcquisitionError("COMMONS_IMAGE_BYTE_SIZE_MISMATCH")
    if hashlib.sha1(image_bytes).hexdigest() != info["sha1"]:
        raise AcquisitionError("COMMONS_IMAGE_SHA1_MISMATCH")
    if not image_bytes.startswith(b"\xff\xd8") or not image_bytes.endswith(b"\xff\xd9"):
        raise AcquisitionError("COMMONS_IMAGE_JPEG_MAGIC_OR_END_MARKER_INVALID")
    digest = hashlib.sha256(image_bytes).hexdigest()
    vault = (vault_root or _default_private_vault()).absolute()
    if vault.resolve(strict=False) == ROOT.resolve() or ROOT.resolve() in vault.resolve(strict=False).parents:
        raise AcquisitionError("COMMONS_PRIVATE_VAULT_MUST_BE_OUTSIDE_REPOSITORY")
    private_path = _publish_private_file(vault, candidate["filename"], image_bytes)
    retrieved = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    source_title_note = "Commons file title says Ramesses VI; official TPOP Cat.2044/013 metadata identifies the writing as Ramesses V. Stable catalogue identity is accession-only; historical attribution is unresolved here."
    record = {
        "record_schema_version": "1.0.0", "evidence_id": f"W8-COMMONS-{candidate_id}-ORIGINAL-v1",
        "candidate_id": candidate_id, "institution": "Museo Egizio, Turin",
        "source_object_id": candidate["accession"], "physical_support_group": candidate["accession"],
        "official_object_url": candidate["object_url"], "official_papyrus_record_url": candidate["papyrus_record_url"],
        "commons_file_page_url": candidate["page_url"], "commons_file_revision_url": candidate["source_revision"],
        "exact_original_file_url": info["url"], "commons_pageid": info["pageid"],
        "commons_api_response_sha256": api_digest, "commons_file_sha1": info["sha1"],
        "source_sha256": digest, "source_byte_size": len(image_bytes), "mime_type": content_type,
        "declared_dimensions": [info["width"], info["height"]], "retrieved_at": retrieved,
        "license": {"identifier": info["license_short_name"], "url": info["license_url"],
                    "file_credit_observation": info["credit"], "official_museum_policy_url": "https://collezioni.museoegizio.it/en-GB/",
                    "papyrus_database_image_policy_url": "https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/Policy-on-access-and-publication-of-papyri/"},
        "source_attribution": "Museo Egizio, Turin; Wikimedia Commons file imported by Marco Chemello (WMIT). Attribution retained for provenance although CC0 does not require it.",
        "historical_identity_note": source_title_note,
        "private_storage": {"storage_class": "user_local_private_artifact_vault", "asset_filename": candidate["filename"], "path_published": False},
        "use_boundary": {"purpose": "unlabelled local image-processing research only", "source_registry_status": "NOT_REGISTERED", "benchmark_overlap_status": "UNRESOLVED_QUARANTINED", "training_admission": "BLOCKED", "development_admission": "BLOCKED", "evaluation_admission": "NOT_AUTHORIZED", "gold_or_transcription": "NONE"},
        "response_headers": {key: headers.get(key) for key in ("etag", "last-modified", "content-length")},
    }
    return record, private_path


def acquire_rime_cat1883_2095_figure6(
    *, transport: Callable[..., tuple[int, str, bytes, dict[str, str]]] | None = None,
    vault_root: Path | None = None, now: dt.datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    """Acquire only the pinned RIME Fig. 6 recto TIFF to a private local vault.

    The figure image license is evidenced by the RIME author guidelines and
    figure credit; the article's transcription/text license is not inferred.
    This packet is research evidence only and never corpus admission.
    """
    request = transport or _public_https_get
    status, content_type, image_bytes, headers = request(
        RIME_FIGURE_HOST, RIME_FIGURE_PATH, MAX_RIME_FIGURE_BYTES
    )
    if status != 200 or content_type != "image/tiff":
        raise AcquisitionError("RIME_FIGURE_RESPONSE_INVALID")
    if len(image_bytes) != RIME_FIGURE_BYTES or len(image_bytes) > MAX_RIME_FIGURE_BYTES:
        raise AcquisitionError("RIME_FIGURE_BYTE_SIZE_MISMATCH")
    if not (image_bytes.startswith((b"II*\x00", b"MM\x00*"))):
        raise AcquisitionError("RIME_FIGURE_TIFF_MAGIC_INVALID")
    digest = hashlib.sha256(image_bytes).hexdigest()
    if digest != RIME_FIGURE_SHA256:
        raise AcquisitionError("RIME_FIGURE_PINNED_SHA256_MISMATCH")
    vault = (vault_root or _default_private_vault("W9")).absolute()
    if vault.resolve(strict=False) == ROOT.resolve() or ROOT.resolve() in vault.resolve(strict=False).parents:
        raise AcquisitionError("COMMONS_PRIVATE_VAULT_MUST_BE_OUTSIDE_REPOSITORY")
    filename = "CAT1883-CAT2095-RIME-fig6-recto-original.tif"
    private_path = _publish_private_file(vault, filename, image_bytes)
    retrieved = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    record = {
        "record_schema_version": "1.0.0", "evidence_id": "W9-RIME-CAT1883-CAT2095-FIG6-RECTO-v1",
        "candidate_id": "CAT1883-CAT2095-RIME-FIG6-RECTO",
        "institution": "Museo Egizio, Turin", "source_object_id": "Cat.1883 + Cat.2095",
        "physical_support_group": "Cat.1883 + Cat.2095 (one joined five-fragment support)",
        "article_url": "https://rivista.museoegizio.it/article/papyrus-turin-cat-1883-cat-2095-a-new-edition-of-an-already-known-papyrus/",
        "exact_original_file_url": RIME_FIGURE_URL,
        "figure_caption": "Figure 6: recto, as currently mounted; scan by Museo Egizio, Turin; digital processing by Martina Landrino.",
        "source_sha256": digest, "source_byte_size": len(image_bytes), "mime_type": content_type,
        "declared_dimensions": [6585, 4718], "retrieved_at": retrieved,
        "response_headers": {key: headers.get(key) for key in ("etag", "last-modified", "content-length")},
        "license": {
            "identifier": "CC BY 2.0", "url": "https://creativecommons.org/licenses/by/2.0/",
            "evidence_url": "https://rivista.museoegizio.it/wp-content/themes/annotum-base/assets/pdf/Guidelines_for_authors.pdf",
            "scope": "RIME image reuse terms plus exact Fig. 6 Museo Egizio scan credit; article transcription/text license is not verified",
            "attribution": "Museo Egizio, Turin; scan by Museo Egizio; digital processing by Martina Landrino; RIME 6 (2022), Fig. 6",
        },
        "private_storage": {"storage_class": "user_local_private_artifact_vault", "asset_filename": filename, "path_published": False},
        "use_boundary": {
            "purpose": "private research inspection and geometry-only diagnostics",
            "source_registry_status": "NOT_REGISTERED", "article_text_license_status": "UNVERIFIED",
            "benchmark_overlap_status": "UNRESOLVED_QUARANTINED", "training_admission": "BLOCKED",
            "development_admission": "BLOCKED", "evaluation_admission": "NOT_AUTHORIZED",
            "gold_or_transcription": "NONE",
        },
    }
    return record, private_path


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
            if not isinstance(url, str):
                raise AcquisitionError("MET_IMAGE_URL_NOT_STRING")
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
        observed = (packet or {}).get("observed")
        if not isinstance(observed, dict):
            observed = {}
        extra_views = observed.get("additionalImages")
        if not isinstance(extra_views, list):
            extra_views = []
        api_accession = observed.get("accessionNumber")
        comparisons.append({
            "candidate_id": candidate["candidate_id"], "institution": candidate["institution"],
            "candidate_accession": accession, "met_api_accession": api_accession,
            "api_identity_verified": bool(packet and packet["verification_status"] == "verified_api_response_identity_and_schema"),
            "r017_crosswalk_exact_public_source_metadata_matches": candidate["exact_public_source_metadata_matches"],
            "literal_accession_substring_matches_in_pinned_R017_public_metadata": [row["id"] for row in literal_rows],
            "normalized_accession_string_matches_in_pinned_R017_public_metadata": [row["id"] for row in normalized_rows],
            "nearby_collection_witness_count_from_R017": candidate["nearby_collection_witness_count"],
            "r017_source_lineage_status": candidate["source_lineage_status"],
            "image_view_count": len(extra_views) + (1 if observed.get("primaryImage") else 0),
            "photo_frame_multi_accession_unresolved": bool(
                object_id == 561345 and any("09.184.728-09.184.703" in url for url in
                [observed.get("primaryImage"), *extra_views] if isinstance(url, str))
            ),
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
    """Publish through an anchored directory FD, never through re-resolved parent symlinks.

    The POSIX dirfd + O_NOFOLLOW chain protects against a parent swapped after
    _validate_metadata_output. On unsupported operating systems fail closed;
    callers can use the hosted Linux workflow for metadata publication.
    """
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise AcquisitionError("MET_SECURE_PUBLICATION_PLATFORM_UNSUPPORTED")
    root = (ROOT / "data" / "acquisition").resolve(strict=True)
    try:
        relative = output.absolute().relative_to(root)
        if not relative.parts or any(x in {"", ".", ".."} for x in relative.parts):
            raise AcquisitionError("metadata packet output path is invalid")
    except ValueError as exc:
        raise AcquisitionError("metadata packet output must remain under data/acquisition") from exc

    dir_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent_fd: int | None = None
    open_fds: list[int] = []
    staging_name: str | None = None
    published = False
    try:
        parent_fd = os.open(root, dir_flags)
        open_fds.append(parent_fd)
        for segment in relative.parts[:-1]:
            parent_fd = os.open(segment, dir_flags, dir_fd=parent_fd)
            open_fds.append(parent_fd)
        original = os.fstat(parent_fd)
        if not stat.S_ISDIR(original.st_mode):
            raise AcquisitionError("MET_OUTPUT_PARENT_NOT_DIRECTORY")
        if output.is_symlink() or output.exists():
            raise AcquisitionError("refusing to overwrite existing metadata packet")
        staging_name = f".met-packet-{secrets.token_hex(16)}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        fd = os.open(staging_name, flags, 0o600, dir_fd=parent_fd)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(packet, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(staging_name, relative.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd, follow_symlinks=False)
        published = True
        # A rename/replacement of the original parent must not report success.
        try:
            current = os.stat(output.parent, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino) or not stat.S_ISDIR(current.st_mode):
                raise AcquisitionError("MET_OUTPUT_PARENT_CHANGED_DURING_PUBLICATION")
        except OSError as exc:
            raise AcquisitionError("MET_OUTPUT_PARENT_CHANGED_DURING_PUBLICATION") from exc
        os.fsync(parent_fd)
    except FileExistsError as exc:
        raise AcquisitionError(f"refusing to overwrite metadata packet: {output}") from exc
    except AcquisitionError:
        if published and parent_fd is not None:
            os.unlink(relative.name, dir_fd=parent_fd)
        raise
    except OSError as exc:
        if published and parent_fd is not None:
            os.unlink(relative.name, dir_fd=parent_fd)
        raise AcquisitionError(f"cannot securely publish metadata packet: {type(exc).__name__}") from exc
    finally:
        if staging_name is not None and parent_fd is not None:
            try:
                os.unlink(staging_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
        for opened_fd in reversed(open_fds):
            os.close(opened_fd)


def _publish_commons_evidence(output: Path, packet: dict[str, Any]) -> None:
    """Publish only redacted metadata under data/acquisition/commons using atomic no-clobber linking."""
    root = (ROOT / "data" / "acquisition" / "commons").resolve(strict=True)
    absolute = output.absolute()
    try:
        relative = absolute.relative_to(root)
    except ValueError as exc:
        raise AcquisitionError("COMMONS_EVIDENCE_OUTPUT_OUTSIDE_ALLOWLIST") from exc
    if len(relative.parts) != 1 or absolute.parent.resolve(strict=True) != root:
        raise AcquisitionError("COMMONS_EVIDENCE_OUTPUT_PARENT_INVALID")
    if absolute.exists() or absolute.is_symlink() or (hasattr(absolute, "is_junction") and absolute.is_junction()):
        raise AcquisitionError("COMMONS_EVIDENCE_OUTPUT_EXISTS")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=root, prefix=".commons-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(packet, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if absolute.parent.resolve(strict=True) != root:
            raise AcquisitionError("COMMONS_EVIDENCE_OUTPUT_PARENT_CHANGED")
        os.link(temporary, absolute)
        temporary.unlink()
    except FileExistsError as exc:
        raise AcquisitionError("COMMONS_EVIDENCE_OUTPUT_EXISTS") from exc
    except OSError as exc:
        raise AcquisitionError(f"COMMONS_EVIDENCE_PUBLISH_FAILED:{type(exc).__name__}") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
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
    parser.add_argument("command", choices=["plan", "validate", "metadata-fetch-met", "commons-image-fetch", "rime-figure-fetch"])
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--object-id", type=int, help="one allowlisted Met collection object ID")
    parser.add_argument("--candidate-id", help="one pinned Museo Egizio Commons candidate (CAT2044 only)")
    args = parser.parse_args(argv)
    if args.command == "rime-figure-fetch":
        expected_output = ROOT / "data" / "acquisition" / "rime" / "CAT1883-CAT2095-FIG6.json"
        if args.manifest.absolute() != expected_output.absolute():
            parser.error("rime-figure-fetch requires the fixed redacted evidence output path under data/acquisition/rime")
        private_path: Path | None = None
        try:
            target = _validate_metadata_output(expected_output)
            record, private_path = acquire_rime_cat1883_2095_figure6()
            _publish_metadata_packet(target, record)
        except (AcquisitionError, OSError) as exc:
            if private_path is not None:
                try:
                    private_path.unlink(missing_ok=True)
                except OSError:
                    pass
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({"evidence_output": str(target.relative_to(ROOT)), "candidate_id": record["candidate_id"],
                          "source_sha256": record["source_sha256"], "source_byte_size": record["source_byte_size"],
                          "dimensions": record["declared_dimensions"], "license": record["license"]["identifier"],
                          "local_private_asset": str(private_path), "training_admission": "BLOCKED",
                          "article_text_license_status": "UNVERIFIED"}, sort_keys=True))
        return 0
    if args.command == "commons-image-fetch":
        if not args.candidate_id:
            parser.error("commons-image-fetch requires --candidate-id")
        candidate_id = args.candidate_id.upper()
        expected_output = ROOT / "data" / "acquisition" / "commons" / f"{candidate_id}.json"
        if args.manifest.absolute() != expected_output.absolute():
            parser.error("commons-image-fetch requires the fixed redacted evidence output path under data/acquisition/commons")
        target = _validate_metadata_output(expected_output)
        private_path: Path | None = None
        try:
            record, private_path = acquire_commons_candidate(candidate_id)
            _publish_commons_evidence(target, record)
        except (AcquisitionError, OSError) as exc:
            if private_path is not None:
                try:
                    private_path.unlink(missing_ok=True)
                except OSError:
                    pass
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({"evidence_output": str(target.relative_to(ROOT)), "candidate_id": candidate_id,
                          "source_sha256": record["source_sha256"], "source_byte_size": record["source_byte_size"],
                          "dimensions": record["declared_dimensions"], "license": record["license"]["identifier"],
                          "local_private_asset": str(private_path), "training_admission": "BLOCKED",
                          "benchmark_overlap_status": "UNRESOLVED_QUARANTINED"}, sort_keys=True))
        return 0
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
