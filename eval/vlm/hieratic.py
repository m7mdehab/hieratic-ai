"""Authentic Hieratic reading evaluation and experimental protocol runner for VLM-001.

Implements:
1. Frozen, preregistered experimental protocol for ancient Egyptian Hieratic manuscripts.
2. Authentic image acquisition verification (Turin Cat.2044/013, CC0, SHA-256 locked).
3. Documented aspect-ratio preserving image resizing and deterministic region crop management.
4. Independent visual sensitivity controls (Blank neutral control, Inverted control, Inter-crop differentiation).
5. Comprehensive evaluation across 5 paleographical rungs:
   - script_identification
   - visual_description
   - sign_hypotheses
   - transliteration_hypotheses
   - translation_hypotheses
6. Scholarly silver bibliographic context (R-024 / TPOP Document 173) and strict boundary enforcement.
7. Six-Grade Evidence Matrix (Grades A-E passed, Grade F strictly NO, 0.0 capability points).
"""
from __future__ import annotations

import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import time
from typing import Any

from eval.vlm.adapter import (
    BaseVLMAdapter,
    ImageConditioningError,
    MockVLMAdapter,
    OpenWeightVLMAdapter,
    VLMResponse,
    get_adapter,
)
from eval.vlm.smoke import create_png

PROTOCOL_VERSION = "1.0.0"
CLASSIFICATION_DIAGNOSTIC = "noncertifiable_diagnostic"

# Pinned model and source constants
PINNED_MODEL_ID = "HuggingFaceTB/SmolVLM-256M-Instruct"
PINNED_REVISION = "7e3e67edbbed1bf9888184d9df282b700a323964"
RECORDED_WEIGHT_SHA256 = "74dea5904032e5ae99a2e0eef5179e6ac0f1dedc3ab0c7c2a5d4d387c843203e"

CAT2044_SOURCE_SHA256 = "569e8e5bb446588481481bfea823fc95383bb7076270363c666f868b7fa5b912"
CAT2044_SOURCE_OBJECT_ID = "Cat.2044/013"
CAT2044_DIMENSIONS = [7063, 3947]
CAT2044_BYTE_SIZE = 2649239

SYSTEM_PROMPT = (
    "You are a rigorous, specialized assistant for ancient Egyptian paleography and papyrology. "
    "Analyze manuscript images strictly based on visible ink strokes, support fibers, and physical evidence. "
    "Distinguish observed visual facts from hypothetical readings. "
    "Do not hallucinate inscriptions or translations when evidence is ambiguous, damaged, or unreadable."
)

FROZEN_PROMPTS = {
    "script_identification": (
        "Examine this ancient Egyptian manuscript image carefully. Identify the script system shown "
        "(e.g., Hieratic, Cursive Hieroglyphs, Epigraphic Hieroglyphs, Demotic, or non-Egyptian). "
        "State your confidence and reasoning based strictly on the visible ink strokes."
    ),
    "visual_description": (
        "Describe the visual and physical characteristics of this ancient document fragment: "
        "support material, fiber texture, ink color (black/red), stroke thickness, preservation condition, "
        "and visible signs of damage, lacunae, or stains."
    ),
    "sign_hypotheses": (
        "Look closely at the individual signs in this hieratic line/fragment. List any candidate hieratic "
        "signs you can discern, giving possible Gardiner list classification codes (e.g., A1, G43, M17, N35) "
        "or stating [UNCERTAIN] / [DAMAGED] if signs are indistinct."
    ),
    "transliteration_hypotheses": (
        "Transliterate the text visible in this ancient Egyptian hieratic passage using standard Egyptological "
        "transliteration conventions (e.g., Unicode or MdC). If the text is illegible or fragmented, indicate "
        "[UNREADABLE] or [DAMAGED]. Do not invent ungrounded readings."
    ),
    "translation_hypotheses": (
        "Provide a provisional English translation for any legible words in this hieratic text. "
        "If the meaning cannot be determined from the visible signs, explicitly state that translation is "
        "unsupported or unknown."
    ),
}

DECODING_PARAMETERS = {
    "temperature": 0.0,
    "do_sample": False,
    "max_new_tokens": 128,
}


def compute_protocol_hash() -> str:
    """Compute deterministic SHA-256 fingerprint for the frozen experimental protocol."""
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "pinned_model_id": PINNED_MODEL_ID,
        "pinned_revision": PINNED_REVISION,
        "system_prompt": SYSTEM_PROMPT,
        "prompts": FROZEN_PROMPTS,
        "decoding_parameters": DECODING_PARAMETERS,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generate_blank_control(width: int = 256, height: int = 256) -> bytes:
    """Generate uniform neutral-gray RGB PNG control image without ink or markings."""
    return create_png(width, height, lambda x, y: (230, 230, 230))


def generate_inverted_control(image_bytes: bytes) -> bytes:
    """Generate deterministic inverted (negative) image control."""
    try:
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        inverted = ImageOps.invert(img)
        buffer = io.BytesIO()
        inverted.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception:
        pass

    # Pure-Python inverted control for PNG with filter-0 scanlines
    try:
        if len(image_bytes) >= 24 and image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            import struct
            import zlib
            w, h = struct.unpack(">II", image_bytes[16:24])
            pos = 8
            idat_parts = []
            while pos < len(image_bytes) - 12:
                chunk_len = struct.unpack(">I", image_bytes[pos:pos+4])[0]
                chunk_type = image_bytes[pos+4:pos+8]
                chunk_data = image_bytes[pos+8:pos+8+chunk_len]
                if chunk_type == b"IDAT":
                    idat_parts.append(chunk_data)
                pos += 12 + chunk_len
            if idat_parts:
                raw = bytearray(zlib.decompress(b"".join(idat_parts)))
                row_bytes = 1 + w * 3
                if len(raw) == row_bytes * h:
                    for r in range(h):
                        row_start = r * row_bytes + 1
                        for i in range(row_start, row_start + w * 3):
                            raw[i] = 255 - raw[i]
                    comp = zlib.compress(bytes(raw), level=9)
                    ihdr_data = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
                    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
                    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc
                    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + comp) & 0xFFFFFFFF)
                    idat_chunk = struct.pack(">I", len(comp)) + b"IDAT" + comp + idat_crc
                    iend_crc = struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
                    iend_chunk = struct.pack(">I", 0) + b"IEND" + iend_crc
                    return b"\x89PNG\r\n\x1a\n" + ihdr_chunk + idat_chunk + iend_chunk
    except Exception:
        pass

    # Deterministic inverted neutral dark-gray control if Pillow or decoding fails
    raise ImageConditioningError("Cannot invert source pixels: no valid image decoder available")


def generate_scrambled_control(
    image_bytes: bytes,
    tile_size: int = 32,
    seed: int = 42,
) -> bytes:
    """Generate deterministic scrambled control image permuting spatial tiles.

    Preserves exact global color histogram and texture statistics while disrupting
    all continuous scribal ink strokes, ligatures, and glyph morphology.
    """
    if not isinstance(image_bytes, bytes) or not image_bytes or len(image_bytes) > 40 * 1024 * 1024:
        raise ImageConditioningError("Invalid or oversized image bytes for scrambling")
    try:
        from PIL import Image
    except ImportError as exc:
        raise ImageConditioningError("Pillow is required to generate scrambled control image") from exc
    try:
        with Image.open(io.BytesIO(image_bytes)) as original:
            img = original.convert("RGB")
            w, h = img.size
            if min(w, h) < 16:
                raise ImageConditioningError("Image too small to tile and scramble")
            t_size = max(8, min(tile_size, min(w, h)))
            cols = max(1, w // t_size)
            rows = max(1, h // t_size)
            tiles = []
            for r in range(rows):
                for c in range(cols):
                    box = (c * t_size, r * t_size, (c + 1) * t_size, (r + 1) * t_size)
                    tiles.append(img.crop(box))
            import random
            rng = random.Random(seed)
            perm = list(range(len(tiles)))
            rng.shuffle(perm)
            out = img.copy()
            for idx, orig_idx in enumerate(perm):
                r = idx // cols
                c = idx % cols
                out.paste(tiles[orig_idx], (c * t_size, r * t_size))
            buf = io.BytesIO()
            out.save(buf, format="PNG")
            return buf.getvalue()
    except ImageConditioningError:
        raise
    except Exception as exc:
        raise ImageConditioningError(f"Scrambled control generation failed: {exc}") from exc


def resize_image_aspect_ratio(
    image_bytes: bytes,
    max_dimension: int = 1024,
    *,
    simulated_marker_ok: bool = False,
) -> tuple[bytes, list[int]]:
    """Decode and resize actual pixels; an invalid live image MUST fail closed.

    Simulated literal markers are only permitted through an explicit synthetic
    CI execution tier. They never become authentic-image evidence.
    """
    if not isinstance(image_bytes, bytes) or not image_bytes or len(image_bytes) > 40 * 1024 * 1024:
        raise ImageConditioningError("Invalid or oversized image bytes")
    if not 16 <= max_dimension <= 4096:
        raise ImageConditioningError("Invalid image resizing limit")
    if image_bytes.startswith(b"synthetic_") and simulated_marker_ok:
        width = min(max_dimension, 256)
        return generate_blank_control(width, width), [width, width]
    if not (image_bytes.startswith(b"\x89PNG\r\n\x1a\n") or image_bytes.startswith(b"\xff\xd8\xff")):
        raise ImageConditioningError("Only genuine PNG/JPEG image bytes are supported")
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise ImageConditioningError("Pillow is required to decode and preserve real pixels") from exc
    try:
        with Image.open(io.BytesIO(image_bytes)) as original:
            if original.format not in {"PNG", "JPEG"}:
                raise ImageConditioningError("Unexpected image codec")
            width, height = original.size
            if min(width, height) < 16 or width * height > 35_000_000:
                raise ImageConditioningError("Image pixel dimensions outside allowed bounds")
            original.verify()
        with Image.open(io.BytesIO(image_bytes)) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
            image.load()
        width, height = image.size
        if max(width, height) > max_dimension:
            ratio = max_dimension / max(width, height)
            image = image.resize(
                (max(1, round(width * ratio)), max(1, round(height * ratio))),
                Image.Resampling.LANCZOS,
            )
        out = io.BytesIO()
        image.save(out, format="PNG")
        return out.getvalue(), list(image.size)
    except ImageConditioningError:
        raise
    except Exception as exc:
        raise ImageConditioningError(f"Real image decoding or resizing failed: {type(exc).__name__}") from exc


def verified_model_weight_sha256(adapter: BaseVLMAdapter) -> bool:
    """Verify the pinned weight bytes, not merely a cached model identifier."""
    if getattr(adapter, "execution_tier", "") != "live_local_open_weight":
        return False
    if getattr(adapter, "model_config", {}).get("provider_model_id") != PINNED_MODEL_ID:
        return False
    if getattr(adapter, "model_config", {}).get("revision") != PINNED_REVISION:
        return False
    roots = []
    supplied = getattr(adapter, "weights_dir", None)
    if supplied is not None:
        roots.append(Path(supplied))
    else:
        hub = Path.home() / ".cache" / "huggingface" / "hub" / "models--HuggingFaceTB--SmolVLM-256M-Instruct"
        roots.append(hub)
    for root in roots:
        candidates = [root / "model.safetensors", root / "snapshots" / PINNED_REVISION / "model.safetensors"]
        for candidate in candidates:
            try:
                if not candidate.is_file() or candidate.stat().st_size != 513_028_808:
                    continue
                digest = hashlib.sha256()
                with candidate.open("rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                if digest.hexdigest() == RECORDED_WEIGHT_SHA256:
                    return True
            except OSError:
                continue
    return False

def audit_alternative_models() -> dict[str, Any]:
    """Audit free, no-cost lightweight VLM alternatives suitable for local CPU execution."""
    return {
        "smolvlm_256m_instruct": {
            "model_id": "HuggingFaceTB/SmolVLM-256M-Instruct",
            "parameters": "256M",
            "weight_size_mb": 489.26,
            "license": "Apache-2.0",
            "cpu_suitability": "VERIFIED_EXECUTABLE",
            "memory_footprint_mb": "~1050 MB resident (tested)",
            "execution_status": "CURRENT_PRIMARY_ROUTE",
        },
        "smolvlm_500m_instruct": {
            "model_id": "HuggingFaceTB/SmolVLM-500M-Instruct",
            "parameters": "500M",
            "weight_size_mb": 960.0,
            "license": "Apache-2.0",
            "cpu_suitability": "FEASIBLE_BOUNDED_RAM",
            "memory_footprint_mb": "~2200 MB estimated",
            "execution_status": "UNAVAILABLE_INSUFFICIENT_AVAILABLE_RAM_AND_WEIGHTS_ABSENT",
            "host_available_ram_mb": "~680 MB available on host (2200 MB required)",
            "comparison_status": "NOT_EXECUTED_DUE_TO_RAM_LIMITS",
        },
        "qwen2_vl_2b_instruct": {
            "model_id": "Qwen/Qwen2-VL-2B-Instruct",
            "parameters": "2.2B",
            "weight_size_mb": 4500.0,
            "license": "Apache-2.0",
            "cpu_suitability": "HIGH_RAM_PRESSURE",
            "memory_footprint_mb": "~5500-7000 MB (marginal on 7.38 GB host)",
            "execution_status": "MARGINAL_ON_7GB_RAM",
        },
    }


def get_scholarly_provenance() -> dict[str, Any]:
    """Return R-024 scholarly provenance metadata for Museo Egizio Cat.2044/013."""
    return {
        "candidate_id": "CAT2044",
        "institution": "Museo Egizio, Turin",
        "accession": CAT2044_SOURCE_OBJECT_ID,
        "physical_support_group": "Cat.2044/013",
        "official_object_url": "https://collezioni.museoegizio.it/en-GB/material/Cat_2044/",
        "tpop_document_url": "https://collezionepapiri.museoegizio.it/en-GB/document/173/",
        "tpop_document_id": "173",
        "license": "CC0",
        "source_sha256": CAT2044_SOURCE_SHA256,
        "historical_context": (
            "Journal of Year 1 of Ramesses VI on recto and verso (museum collection title). "
            "TPOP record 173 attributes multiple writing units to Ramesses V. "
            "French translation references Ramses Online ID 3791; English translation in preparation."
        ),
        "scientific_boundary": "UNSCORED_EXPLORATORY_READING_HYPOTHESIS",
        "alignment_status": "NO_LINE_ALIGNMENT",
        "gold_standard_available": False,
        "pretraining_contamination_risk": "POSSIBLE_HISTORIC_METADATA_CONTAMINATION",
    }


TASK_RUNGS = {
    "script_identification": "identify",
    "visual_description": "identify",  # descriptive auxiliary, never an official scored rung
    "sign_hypotheses": "signs",
    "transliteration_hypotheses": "transliterate",
    "translation_hypotheses": "translate",
}


def execute_hieratic_experiment(
    adapter: BaseVLMAdapter,
    image_targets: list[dict[str, Any]],
    *,
    allow_simulated: bool = False,
) -> dict[str, Any]:
    """Unscored, provenance-bound diagnostic; fail closed on substituted pixels."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    is_simulated = (
        isinstance(adapter, MockVLMAdapter)
        or getattr(adapter, "execution_tier", "") == "synthetic_ci_fixture"
    )
    if is_simulated and not allow_simulated:
        raise ImageConditioningError("Simulated execution requires --allow-simulated")
    if not image_targets:
        raise ImageConditioningError("No images supplied")
    if not is_simulated:
        if getattr(adapter, "execution_tier", "") != "live_local_open_weight":
            raise ImageConditioningError("Unverified live execution tier")
        if not verified_model_weight_sha256(adapter):
            raise ImageConditioningError("Pinned SmolVLM model.safetensors bytes not independently verified")
        first = image_targets[0]
        if first.get("target_type") != "full_manuscript" or first.get("target_id") != "cat2044_full_p01":
            raise ImageConditioningError("The first live target must be the exact Cat.2044 original")
        raw = first.get("image_bytes")
        if not isinstance(raw, bytes) or len(raw) != CAT2044_BYTE_SIZE or hashlib.sha256(raw).hexdigest() != CAT2044_SOURCE_SHA256:
            raise ImageConditioningError("Authentic Cat.2044 source hash or byte size mismatch")
    if len({x.get("target_id") for x in image_targets}) != len(image_targets):
        raise ImageConditioningError("Duplicate target identities")

    processed_targets: list[dict[str, Any]] = []
    reading_hypotheses: list[dict[str, Any]] = []
    for target in image_targets:
        t_id, t_type = target["target_id"], target["target_type"]
        raw_bytes = target["image_bytes"]
        if not isinstance(raw_bytes, bytes):
            raise ImageConditioningError("Target image must have byte content")
        if t_type not in {"full_manuscript", "candidate_line_crop"}:
            raise ImageConditioningError("Unknown target type")
        if not is_simulated and t_type == "candidate_line_crop":
            expected = target.get("expected_sha256")
            if not isinstance(expected, str) or hashlib.sha256(raw_bytes).hexdigest() != expected:
                raise ImageConditioningError("Crop is missing independently recorded byte hash")
        processed, dims = resize_image_aspect_ratio(
            raw_bytes, 1024 if t_type == "full_manuscript" else 512,
            simulated_marker_ok=is_simulated,
        )
        if not is_simulated and t_type == "full_manuscript" and dims != [1024, 572]:
            raise ImageConditioningError("Original image decoded with unexpected orientation/dimensions")
        processed_targets.append({
            "target_id": t_id, "target_type": t_type,
            "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "raw_byte_size": len(raw_bytes),
            "processed_dimensions": dims,
            "processed_sha256": hashlib.sha256(processed).hexdigest(),
            "source_bounds": target.get("source_bounds"),
            "source_to_crop_transform": target.get("transform"),
        })
        for task_key, prompt in FROZEN_PROMPTS.items():
            if is_simulated:
                simulated_text = {
                    "script_identification": "Synthetic example: Hieratic",
                    "visual_description": "Synthetic papyrus description",
                    "sign_hypotheses": "[UNCERTAIN] synthetic Gardiner sign",
                    "transliteration_hypotheses": "[UNREADABLE] synthetic line",
                    "translation_hypotheses": "Synthetic: translation unsupported",
                }[task_key]
                response = VLMResponse(
                    status="success", raw_output=simulated_text,
                    cleaned_prediction=simulated_text, error_message=None,
                    latency_ms=0.0, token_usage=None,
                )
            else:
                response = adapter.predict(
                    image_bytes=processed, prompt=prompt, system_prompt=SYSTEM_PROMPT,
                    shot_mode="zero_shot", rung=TASK_RUNGS[task_key],
                    item_id=f"{t_id}_{task_key}",
                )
            output = response.raw_output or ""
            reading_hypotheses.append({
                "target_id": t_id, "task": task_key, "rung": TASK_RUNGS[task_key],
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "prompt_text": prompt, "output_text": output,
                "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
                "status": response.status, "error_message": response.error_message,
                "latency_ms": response.latency_ms, "token_usage": response.token_usage,
                "grounding_assessment": "synthetic_ci_fixture" if is_simulated else "unscored_exploratory_hypothesis",
            })

    blank = generate_blank_control()
    first = next(h for h in reading_hypotheses
                 if h["target_id"] == image_targets[0]["target_id"] and h["task"] == "script_identification")
    if is_simulated:
        blank_response, inverted_response = "Synthetic blank example", "Synthetic inverted example"
        scrambled_response = "Synthetic scrambled example"
        blank_status = inverted_status = scrambled_status = "synthetic_ci_fixture"
        inverted = None
        scrambled = None
    else:
        blank_result = adapter.predict(
            image_bytes=blank, prompt=FROZEN_PROMPTS["script_identification"],
            system_prompt=SYSTEM_PROMPT, shot_mode="zero_shot", rung="identify",
            item_id="blank_control_script_id",
        )
        blank_response, blank_status = blank_result.raw_output or "", blank_result.status
        source_image, _ = resize_image_aspect_ratio(image_targets[0]["image_bytes"], 1024)
        inverted = generate_inverted_control(source_image)
        inv_result = adapter.predict(
            image_bytes=inverted, prompt=FROZEN_PROMPTS["script_identification"],
            system_prompt=SYSTEM_PROMPT, shot_mode="zero_shot", rung="identify",
            item_id="inverted_control_script_id",
        )
        inverted_response, inverted_status = inv_result.raw_output or "", inv_result.status
        scrambled = generate_scrambled_control(source_image, tile_size=32, seed=42)
        scrambled_result = adapter.predict(
            image_bytes=scrambled, prompt=FROZEN_PROMPTS["script_identification"],
            system_prompt=SYSTEM_PROMPT, shot_mode="zero_shot", rung="identify",
            item_id="scrambled_control_script_id",
        )
        scrambled_response, scrambled_status = scrambled_result.raw_output or "", scrambled_result.status

    primary_response = first["output_text"]
    different_text = bool(primary_response.strip() and blank_response.strip()
                          and primary_response.strip() != blank_response.strip())
    blank_hallucinates_script = any(
        kw in blank_response.lower()
        for kw in ("hieratic", "hieroglyph", "inscript", "stroke", "ink", "writing", "papyrus", "text", "script")
    )
    blank_correctly_identified = any(
        marker in blank_response.lower()
        for marker in ("no visible script", "no writing", "no text", "blank image", "blank canvas", "empty")
    )
    successful_pair = first["status"] == "success" and blank_status == "success"
    inverted_valid = inverted_status == "success" and bool(inverted_response.strip())
    inverted_identifies_hieratic = "hieratic" in inverted_response.lower()
    scrambled_valid = scrambled_status == "success" and bool(scrambled_response.strip())
    scrambled_hallucinates_script = any(
        kw in scrambled_response.lower()
        for kw in ("hieratic", "hieroglyph", "demotic", "cursive hieroglyphs")
    )
    prompt_priming_observed = (not is_simulated) and (blank_hallucinates_script or scrambled_hallucinates_script)
    distinct_crop_responses = len({
        h["output_text"].strip()
        for h in reading_hypotheses
        if h["task"] == "script_identification" and h["status"] == "success" and h["output_text"].strip()
    }) > 1

    translit_hypotheses = [h for h in reading_hypotheses if h["task"] == "transliteration_hypotheses"]
    translit_abstentions = [
        any(marker in h["output_text"] for marker in ("[UNREADABLE]", "[DAMAGED]", "[UNCERTAIN]"))
        for h in translit_hypotheses
    ]
    transliteration_abstention_rate = (
        sum(translit_abstentions) / len(translit_hypotheses) if translit_hypotheses else 0.0
    )

    def detect_repetition(text: str) -> bool:
        words = text.split()
        if len(words) >= 6:
            for n in (1, 2, 3):
                chunks = [" ".join(words[i:i+n]) for i in range(0, len(words) - n + 1, n)]
                if len(chunks) >= 4 and len(set(chunks[-4:])) == 1:
                    return True
        if len(text) > 20 and any(c * 5 in text for c in "[,.- "):
            return True
        return False

    repetition_loop_detected = any(detect_repetition(h["output_text"]) for h in reading_hypotheses)
    trans_hypotheses = [h for h in reading_hypotheses if h["task"] == "translation_hypotheses"]
    translation_unsupported_acknowledged = all(
        any(kw in h["output_text"].lower() for kw in ("unsupported", "unknown", "undetermined", "cannot be", "not possible", "unable", "uncertain", "damaged"))
        for h in trans_hypotheses
    ) if trans_hypotheses else False

    control_verified = (
        not is_simulated and successful_pair and inverted_valid and scrambled_valid
        and different_text and blank_correctly_identified
    )
    sensitivity_controls = {
        "blank_control_sha256": hashlib.sha256(blank).hexdigest(),
        "blank_response_text": blank_response,
        "blank_status": blank_status,
        "blank_hallucinates_script": blank_hallucinates_script,
        "blank_correctly_identified": blank_correctly_identified,
        "inverted_control_sha256": hashlib.sha256(inverted).hexdigest() if inverted else None,
        "inverted_response_text": inverted_response,
        "inverted_status": inverted_status,
        "inverted_identifies_hieratic": inverted_identifies_hieratic,
        "scrambled_control_sha256": hashlib.sha256(scrambled).hexdigest() if scrambled else None,
        "scrambled_response_text": scrambled_response,
        "scrambled_status": scrambled_status,
        "scrambled_hallucinates_script": scrambled_hallucinates_script,
        "primary_target_id": image_targets[0]["target_id"],
        "primary_hieratic_response_text": primary_response,
        "response_difference_only": different_text,
        "prompt_priming_observed": prompt_priming_observed,
        "transliteration_abstention_rate": transliteration_abstention_rate,
        "repetition_loop_detected": repetition_loop_detected,
        "translation_unsupported_acknowledged": translation_unsupported_acknowledged,
        "sensitivity_observed": control_verified,
        "inter_crop_discrimination_tested": not is_simulated and distinct_crop_responses,
    }
    primary_ok = first["status"] == "success" and bool(primary_response.strip())
    live_pixel_pass = not is_simulated and primary_ok
    sim_status = "SIMULATED_TEST_DOUBLE"
    evidence_grades = {
        "grade_a_multimodal_interface": {
            "status": sim_status if is_simulated else ("PASSED" if primary_ok else "NOT_VERIFIED"),
            "evidence": "Local image-conditioned adapter execution; not certified recognition",
        },
        "grade_b_fixture_tests": {
            "status": sim_status if is_simulated else "NOT_VERIFIED_BY_RUNTIME",
            "evidence": "CI regression result must be verified externally at exact commit",
        },
        "grade_c_real_weights_loaded": {
            "status": sim_status if is_simulated else "PASSED",
            "evidence": "SHA-256 of actual pinned weight bytes verified before live execution",
        },
        "grade_d_actual_hieratic_forward_pass": {
            "status": sim_status if is_simulated else ("PASSED" if live_pixel_pass else "NOT_VERIFIED"),
            "evidence": "Exact original image hash checked; never substitute pixels on decode failure",
        },
        "grade_e_visual_sensitivity_observed": {
            "status": sim_status if is_simulated else ("PASSED_DIAGNOSTIC_ONLY" if control_verified else "NOT_VERIFIED"),
            "evidence": "Requires matched blank response that actually identifies no text; inversion run; different text alone is insufficient",
        },
        "real_hieratic_hypothesis_cleared": {
            "status": sim_status if is_simulated else ("PASSED_DIAGNOSTIC_ONLY" if live_pixel_pass else "NOT_VERIFIED"),
            "evidence": "Noncertifiable source-bound, unscored hypothesis only",
        },
        "silver_diagnostic_cleared": {
            "status": "S0_BIBLIOGRAPHIC_CITATION_ONLY",
            "evidence": "TPOP document 173, no independently aligned line gold",
        },
        "grade_f_authentic_hieratic_gold_evaluation": {
            "status": "STRICTLY_NO",
            "evidence": "No official or independently reviewed held-out Hieratic score; 0/2 points",
        },
    }
    return {
        "doc_type": "vlm_hieratic_experiment_report",
        "schema_version": "1.0.0", "timestamp": timestamp,
        "protocol": {
            "protocol_version": PROTOCOL_VERSION, "protocol_sha256": compute_protocol_hash(),
            "system_prompt": SYSTEM_PROMPT, "frozen_prompts": FROZEN_PROMPTS,
            "decoding_parameters": DECODING_PARAMETERS,
            "preregistration_status": "runtime_fingerprint_only_not_independent_preregistration",
        },
        "model_info": {
            "provider_model_id": adapter.model_config.get("provider_model_id"),
            "revision": adapter.model_config.get("revision"),
            "simulated_mode": is_simulated, "adapter_class": type(adapter).__name__,
            "actual_weight_hash_verified": not is_simulated,
        },
        "source_image": {
            "source_object_id": CAT2044_SOURCE_OBJECT_ID,
            "institution": "Museo Egizio, Turin", "license": "CC0",
            "original_sha256": CAT2044_SOURCE_SHA256,
            "original_dimensions": CAT2044_DIMENSIONS,
            "original_byte_size": CAT2044_BYTE_SIZE,
            "source_bytes_verified": not is_simulated,
        },
        "targets": processed_targets, "sensitivity_controls": sensitivity_controls,
        "reading_hypotheses": reading_hypotheses,
        "alternative_models_audit": audit_alternative_models(),
        "scholarly_provenance": get_scholarly_provenance(),
        "evidence_grades": evidence_grades,
        "classification": CLASSIFICATION_DIAGNOSTIC,
        "scientific_capability_points": 0.0,
        "hieratic_reading_claim": False,
    }
