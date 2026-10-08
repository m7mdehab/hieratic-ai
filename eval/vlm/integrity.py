"""Trust-boundary helpers for the VLM evaluation harness.

This module is deliberately conservative. Nothing here can *grant* scientific
status; it can only verify internal consistency, or refuse.

* ``write_bytes_no_clobber`` / ``write_json_no_clobber`` publish immutable
  outputs with an exclusive, no-replace commit (hard link), never ``replace``.
* ``PINNED_PREFLIGHT_UNIVERSE_SHA256`` anchors the *synthetic* preflight
  universe in code, so editing ``universe.yaml`` and recomputing the hash that
  lives inside the same YAML is detected. It is a regression anchor for a
  synthetic fixture, NOT an independent scientific population.
* ``verify_attempts_against_universe`` checks every attempt's item, rung,
  document and image SHA-256 against the per-item pinned records.
* ``verify_external_authorization`` is a fail-closed stub: no trusted external
  authorization authority (signed DATA-008 receipt, experiment authorization,
  model-inference receipt) is integrated, so it never returns success.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any

# Anchor for eval/vlm/universe.yaml (synthetic preflight only).
PINNED_PREFLIGHT_UNIVERSE_ID = "hieratic_vlm_synthetic_preflight_universe_v1"
PINNED_PREFLIGHT_UNIVERSE_SHA256 = "fd72f77473b0c07074a18ceafbddc40449f4f9690be99e522100b313e3b0780d"

# No trusted external authority is integrated. Flip only when a verifier exists.
EXTERNAL_AUTHORIZATION_INTEGRATED = False

NONCERTIFIABLE_CLASSIFICATION = "noncertifiable_diagnostic"


class ImmutableOutputError(OSError):
    """Raised when an immutable output already exists or cannot be published safely."""


def write_bytes_no_clobber(path: Path, payload: bytes) -> None:
    """Publish ``payload`` at ``path`` iff nothing exists there; never replace.

    Writes to an exclusively created temp file in the same directory, fsyncs,
    then commits with ``os.link`` which fails atomically if the target exists.
    Concurrent writers: exactly one wins; the rest raise ImmutableOutputError.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(path):
        raise ImmutableOutputError(f"Refusing to overwrite existing immutable output: {path}")

    tmp_handle = tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", suffix=".part", delete=False
    )
    tmp_path = Path(tmp_handle.name)
    try:
        with tmp_handle:
            tmp_handle.write(payload)
            tmp_handle.flush()
            os.fsync(tmp_handle.fileno())
        try:
            os.link(tmp_path, path)
        except FileExistsError as exc:
            raise ImmutableOutputError(
                f"Refusing to overwrite existing immutable output (concurrent writer?): {path}"
            ) from exc
        except (OSError, NotImplementedError, AttributeError) as exc:
            if os.path.lexists(path):
                raise ImmutableOutputError(f"Refusing to overwrite existing immutable output: {path}") from exc
            raise ImmutableOutputError(
                f"Filesystem does not support no-replace publication for {path}; refusing to write: {exc}"
            ) from exc
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def write_json_no_clobber(path: Path, data: Any, indent: int = 2) -> None:
    write_bytes_no_clobber(Path(path), json.dumps(data, indent=indent).encode("utf-8"))


def verify_universe_anchor(universe_data: dict[str, Any]) -> list[str]:
    """Check the universe against the code-pinned synthetic anchor.

    A universe edited and re-hashed in place fails here. A universe that is not
    the pinned one is *unanchored*: it is rejected rather than trusted.
    """
    errors: list[str] = []
    uid = universe_data.get("universe_id")
    if uid != PINNED_PREFLIGHT_UNIVERSE_ID:
        errors.append(
            f"Universe '{uid}' is not the anchored preflight universe '{PINNED_PREFLIGHT_UNIVERSE_ID}'; "
            "no external immutable universe anchor is available, so it is unanchored and rejected."
        )
        return errors
    # Local import avoids a cycle at import time.
    from eval.vlm.universe import compute_universe_sha256

    computed = compute_universe_sha256(universe_data)
    if computed != PINNED_PREFLIGHT_UNIVERSE_SHA256:
        errors.append(
            "Universe content hash does not match the code-pinned anchor "
            f"({computed[:12]} != {PINNED_PREFLIGHT_UNIVERSE_SHA256[:12]}); universe edited and re-hashed in place."
        )
    if universe_data.get("universe_tier") != "synthetic_preflight_universe":
        errors.append("Anchored universe must remain tier 'synthetic_preflight_universe'.")
    return errors


def verify_attempts_against_universe(manifest: dict[str, Any], universe_data: dict[str, Any]) -> list[str]:
    """Bind every attempt to the pinned per-item identity, lineage and image hash."""
    errors: list[str] = []
    items = {it["item_id"]: it for it in universe_data.get("items", [])}
    for i, a in enumerate(manifest.get("attempts", [])):
        iid = a.get("item_id")
        pinned = items.get(iid)
        if pinned is None:
            errors.append(f"Attempt {i}: item_id '{iid}' is not in the pinned universe.")
            continue
        if a.get("rung") != pinned.get("rung"):
            errors.append(f"Attempt {i} ({iid}): rung '{a.get('rung')}' != pinned '{pinned.get('rung')}'.")
        if a.get("document_id") != pinned.get("document_id"):
            errors.append(
                f"Attempt {i} ({iid}): document lineage '{a.get('document_id')}' != pinned '{pinned.get('document_id')}'."
            )
        if a.get("image_sha256") != pinned.get("image_sha256"):
            errors.append(
                f"Attempt {i} ({iid}): image SHA-256 does not match pinned item image (image swap under same item ID)."
            )
    return errors


def verify_external_authorization(manifest: dict[str, Any]) -> tuple[bool, str]:
    """Resolve and verify external authorization. Fail-closed: no authority is integrated."""
    ref = manifest.get("authorization_receipt_ref")
    if not EXTERNAL_AUTHORIZATION_INTEGRATED:
        return False, (
            f"authorization_receipt_ref {ref!r} cannot be verified: no trusted external authorization authority "
            "(signed DATA-008 rights receipt, experiment authorization, source-evidence record, and "
            "model-inference receipt) is integrated. Self-declared fields are never evidence."
        )
    return False, "External authorization verifier not implemented."  # pragma: no cover
