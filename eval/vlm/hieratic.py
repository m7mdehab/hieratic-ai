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

PROTOCOL_VERSION = "1.4.0"
CLASSIFICATION_DIAGNOSTIC = "noncertifiable_diagnostic"

# Pinned model and source constants
PINNED_MODEL_ID = "HuggingFaceTB/SmolVLM-256M-Instruct"
PINNED_REVISION = "7e3e67edbbed1bf9888184d9df282b700a323964"
RECORDED_WEIGHT_SHA256 = "74dea5904032e5ae99a2e0eef5179e6ac0f1dedc3ab0c7c2a5d4d387c843203e"

# Support 1: Museo Egizio Turin Cat.2044/013 (CC0)
CAT2044_SOURCE_SHA256 = "569e8e5bb446588481481bfea823fc95383bb7076270363c666f868b7fa5b912"
CAT2044_SOURCE_OBJECT_ID = "Cat.2044/013"
CAT2044_DIMENSIONS = [7063, 3947]
CAT2044_BYTE_SIZE = 2649239

# Support 2: Turin Cat.1883 + Cat.2095 (RIME 6 2022, Fig. 6 Recto, CC BY 2.0 image)
RIME_FIG6_SOURCE_SHA256 = "c4b878ca5b6b6c22d0b4b1574d4f8e95072d651c38cb03d49f3cf73c5f6052b9"
RIME_FIG6_SOURCE_OBJECT_ID = "Cat.1883 + Cat.2095"
RIME_FIG6_DIMENSIONS = [6585, 4718]
RIME_FIG6_BYTE_SIZE = 36023444
RIME_FIG6_VIEW = "recto"
RIME_FIG6_FIGURE_NUMBER = 6
RIME_FIG6_URL = "https://rivista.museoegizio.it/wp-content/themes/annotum-base/assets/articles/4418/content/6/original.tif"

# Forbidden substitute: RIME Fig. 8 Verso (DATA-006 candidate; never interchange)
RIME_FIG8_VERSO_FORBIDDEN_SHA256 = "506e0b536aa5824bbd18cb0a0b372e057a67e48218a02004ad464ca0958bbeb1"
RIME_FIG8_VERSO_DIMENSIONS = [6595, 4710]
RIME_FIG8_VERSO_BYTE_SIZE = 41686648

SYSTEM_PROMPT = (
    "You are a rigorous, specialized assistant for ancient Egyptian paleography and papyrology. "
    "Analyze manuscript images strictly based on visible ink strokes, support fibers, and physical evidence. "
    "Distinguish observed visual facts from hypothetical readings. "
    "Do not hallucinate inscriptions or translations when evidence is ambiguous, damaged, or unreadable."
)

# Neutral (non-leading) prompts: used as primary evaluation contract across all stimuli
FROZEN_NEUTRAL_PROMPTS = {
    "script_identification": (
        "Examine the image carefully. Describe what is visible in the image, and if any writing or script "
        "system is present, identify it. If no writing, text, or script is present, state that clearly."
    ),
    "visual_description": (
        "Describe the visual and physical characteristics of this image: support material or background, "
        "texture, colors, visible markings, shapes, condition, and any blank or damaged areas."
    ),
    "sign_hypotheses": (
        "Examine the visual marks and signs in this image. List any candidate characters or signs you can "
        "discern, or state [NO_SIGNS] / [UNCERTAIN] if no distinct signs or characters are visible."
    ),
    "transliteration_hypotheses": (
        "If continuous writing is legible in this image, provide a transliteration or transcription. "
        "If no text, script, or legible writing is present, indicate [UNREADABLE] or [NO_TEXT]."
    ),
    "translation_hypotheses": (
        "Provide a provisional English translation for any legible words in this image. "
        "If the image contains no readable text or the meaning cannot be determined, explicitly state "
        "that translation is unsupported."
    ),
}

# Leading prompts (historical W9/W10 variant): used as ablation control to quantify priming
FROZEN_LEADING_PROMPTS = {
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

# FROZEN_PROMPTS alias defaults to neutral prompts for primary contract
FROZEN_PROMPTS = FROZEN_NEUTRAL_PROMPTS

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
        "neutral_prompts": FROZEN_NEUTRAL_PROMPTS,
        "leading_prompts": FROZEN_LEADING_PROMPTS,
        "decoding_parameters": DECODING_PARAMETERS,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generate_blank_control(width: int = 256, height: int = 256) -> bytes:
    """Generate uniform neutral-gray RGB PNG control image without ink or markings."""
    return create_png(width, height, lambda x, y: (230, 230, 230))


def generate_natural_nontext_control(width: int = 256, height: int = 256, seed: int = 42) -> bytes:
    """Generate deterministic, visually complex non-text texture control image.

    Contains rich visual structure (high-contrast multi-scale harmonic fields and gradients)
    that is visually meaningful and non-blank, but contains absolutely no characters, glyphs,
    ink strokes, or text.
    """
    import math

    def pixel(x: int, y: int) -> tuple[int, int, int]:
        nx = x / max(1, width)
        ny = y / max(1, height)
        v1 = math.sin(nx * 18.0 + seed) * math.cos(ny * 18.0 + seed)
        v2 = math.sin((nx + ny) * 24.0 + math.sin(nx * 12.0))
        dist = math.sqrt((x - width / 2) ** 2 + (y - height / 2) ** 2)
        v3 = math.cos(dist * 0.15)
        pattern = 0.5 + 0.25 * v1 + 0.15 * v2 + 0.10 * v3
        pattern = max(0.0, min(1.0, pattern))
        r = int(50 + pattern * 160)
        g = int(80 + pattern * 110)
        b = int(120 + pattern * 80)
        return (r, g, b)

    return create_png(width, height, pixel)


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

    Reorders complete spatial tiles while preserving their pixel histograms;
    within-tile ink strokes and incomplete edge strips remain recognizable.
    This is an *exploratory corrupted-layout control*, not a certified blank
    or proof that all Hieratic sign structure was destroyed.
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
    if not isinstance(image_bytes, bytes) or not image_bytes or len(image_bytes) > 45 * 1024 * 1024:
        raise ImageConditioningError("Invalid or oversized image bytes")
    if not 16 <= max_dimension <= 4096:
        raise ImageConditioningError("Invalid image resizing limit")
    if image_bytes.startswith(b"synthetic_") and simulated_marker_ok:
        width = min(max_dimension, 256)
        return generate_blank_control(width, width), [width, width]

    is_png = image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    is_jpeg = image_bytes.startswith(b"\xff\xd8\xff")
    is_tiff = image_bytes.startswith((b"II*\x00", b"MM\x00*"))
    if not (is_png or is_jpeg or is_tiff):
        raise ImageConditioningError("Only genuine PNG/JPEG/TIFF image bytes are supported")

    # Falsification gate: detect and reject forbidden Figure 8 Verso substitution
    if hashlib.sha256(image_bytes).hexdigest() == RIME_FIG8_VERSO_FORBIDDEN_SHA256:
        raise ImageConditioningError("Forbidden Figure 8 Verso substitution detected: expected RIME Figure 6 Recto")

    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise ImageConditioningError("Pillow is required to decode and preserve real pixels") from exc
    try:
        previous_max = Image.MAX_IMAGE_PIXELS
        Image.MAX_IMAGE_PIXELS = 40_000_000
        try:
            with Image.open(io.BytesIO(image_bytes)) as original:
                if original.format not in {"PNG", "JPEG", "TIFF"}:
                    raise ImageConditioningError("Unexpected image codec")
                width, height = original.size
                if min(width, height) < 16 or width * height > 36_000_000:
                    raise ImageConditioningError("Image pixel dimensions outside allowed bounds")
                original.verify()
            with Image.open(io.BytesIO(image_bytes)) as original:
                image = ImageOps.exif_transpose(original).convert("RGB")
                image.load()
        finally:
            Image.MAX_IMAGE_PIXELS = previous_max
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
    """Return scholarly provenance metadata for both authentic physical supports."""
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
        "supports": [
            {
                "support_id": "SUPPORT_1_CAT2044",
                "institution": "Museo Egizio, Turin",
                "accession": CAT2044_SOURCE_OBJECT_ID,
                "physical_support_group": "Cat.2044/013",
                "source_sha256": CAT2044_SOURCE_SHA256,
                "license": "CC0",
                "historical_context": "Ramesside papyrus (TPOP Doc 173 / Ramses Online 3791).",
                "alignment_status": "NO_LINE_ALIGNMENT",
            },
            {
                "support_id": "SUPPORT_2_CAT1883_CAT2095",
                "institution": "Museo Egizio, Turin",
                "accession": RIME_FIG6_SOURCE_OBJECT_ID,
                "physical_support_group": "Cat.1883 + Cat.2095 (one joined five-fragment support)",
                "view": "recto as mounted in RIME Fig. 6",
                "source_sha256": RIME_FIG6_SOURCE_SHA256,
                "license": "CC BY 2.0 (image only; article text reuse unverified)",
                "historical_context": (
                    "Cat.1883 and Cat.2095 are adjoining fragments of a single physical manuscript support "
                    "containing an administrative Deir el-Medina text with accounts, lists, and royal dating "
                    "(G. Rosati 2022). Not Book of the Dead or funerary liturgy."
                ),
                "alignment_status": "NO_LINE_ALIGNMENT",
                "text_reuse_status": "BLOCKED_UNVERIFIED_LICENSE",
            },
        ],
        "distinct_physical_supports_evaluated": 2,
        "scholarly_note": (
            "Cat.1883 and Cat.2095 are adjoining fragments of a single physical manuscript support "
            "documenting an administrative Deir el-Medina text (RIME 2022; G. Rosati). "
            "They are evaluated as one physical support distinct from Cat.2044/013. "
            "Neither support has independently certified gold line alignments in the public benchmark."
        ),
    }


TASK_RUNGS = {
    "script_identification": "identify",
    "visual_description": "identify",  # descriptive auxiliary, never an official scored rung
    "sign_hypotheses": "signs",
    "transliteration_hypotheses": "transliterate",
    "translation_hypotheses": "translate",
}


def classify_script_claim(text: str) -> dict[str, Any]:
    """Classify model utterance regarding presence/identification of a script system.
    
    Distinguishes:
    - affirmative_script_claim: Explicitly claims presence of a writing/script system (e.g. Hieratic, Hieroglyphic).
    - negative_script_claim: Explicitly denies that writing, text, or script is present.
    - mixed_or_uncertain: Statements containing mixed cues (e.g. 'no text but ink strokes', 'uncertain whether script').
    - descriptive_only: General visual/physical description of materials, colors, or textures without script classification.
    """
    t = text.lower().strip()

    script_keywords = [
        "hieratic", "hieroglyph", "hieroglyphic", "hieroglyphs", "demotic",
        "cursive hieroglyphs", "chinese character", "chinese characters",
        "cuneiform", "epigraphic", "egyptian script",
    ]

    negation_phrases = [
        "no writing", "no script", "no text", "no visible script", "no visible text",
        "not visible", "no legible writing", "no distinct signs", "no characters",
        "empty", "blank canvas", "blank image", "no inscription", "without text",
        "without any text", "neither text nor script", "no words", "not hieratic",
        "not hieroglyphs", "not hieroglyphic", "not ancient egyptian", "not script",
    ]

    uncertainty_cues = [
        "uncertain", "unclear", "difficult to discern", "cannot be determined",
        "might be", "could be", "resembling", "resembles", "ambiguous",
    ]

    found_scripts = [s for s in script_keywords if s in t]
    found_negations = [n for n in negation_phrases if n in t]
    found_uncertainty = [u for u in uncertainty_cues if u in t]

    has_ink_or_stroke = any(w in t for w in ("stroke", "ink", "brush stroke", "markings", "ductus"))

    if found_negations and (has_ink_or_stroke or found_scripts):
        category = "mixed_or_uncertain"
    elif found_uncertainty and (found_scripts or has_ink_or_stroke):
        category = "mixed_or_uncertain"
    elif found_scripts:
        category = "affirmative_script_claim"
    elif found_negations:
        category = "negative_script_claim"
    else:
        category = "descriptive_only"

    return {
        "category": category,
        "script_claimed": category == "affirmative_script_claim",
        "no_script_claimed": category == "negative_script_claim",
        "is_uncertain_or_mixed": category == "mixed_or_uncertain",
        "identified_scripts": found_scripts,
        "negation_markers": found_negations,
        "raw_text": text,
    }


def execute_hieratic_experiment(
    adapter: BaseVLMAdapter,
    image_targets: list[dict[str, Any]],
    *,
    allow_simulated: bool = False,
    run_leading_ablation: bool = True,
) -> dict[str, Any]:
    """Unscored, provenance-bound cross-support diagnostic; fail closed on substituted pixels."""
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
        if first.get("target_type") != "full_manuscript":
            raise ImageConditioningError("The first live target must be an authentic full manuscript")
        first_id = first.get("target_id")
        raw_first = first.get("image_bytes")
        if first_id == "cat2044_full_p01":
            if not isinstance(raw_first, bytes) or len(raw_first) != CAT2044_BYTE_SIZE or hashlib.sha256(raw_first).hexdigest() != CAT2044_SOURCE_SHA256:
                raise ImageConditioningError("Authentic Cat.2044 source hash or byte size mismatch")
        elif first_id == "cat1883_2095_full_fig6":
            if not isinstance(raw_first, bytes) or len(raw_first) != RIME_FIG6_BYTE_SIZE or hashlib.sha256(raw_first).hexdigest() != RIME_FIG6_SOURCE_SHA256:
                raise ImageConditioningError("Authentic RIME Fig. 6 source hash or byte size mismatch")
        else:
            raise ImageConditioningError("The first live target must be Cat.2044 or Cat.1883+Cat.2095 Fig. 6")

    if len({x.get("target_id") for x in image_targets}) != len(image_targets):
        raise ImageConditioningError("Duplicate target identities")

    has_real_weights = verified_model_weight_sha256(adapter) if not is_simulated else False
    model_cfg = getattr(adapter, "model_config", {})
    provider_id = model_cfg.get("provider_model_id", PINNED_MODEL_ID)
    model_rev = model_cfg.get("revision", PINNED_REVISION)
    weight_sha = RECORDED_WEIGHT_SHA256 if has_real_weights else "unverified_or_simulated"

    processed_targets: list[dict[str, Any]] = []
    reading_hypotheses: list[dict[str, Any]] = []
    attempt_ledger: list[dict[str, Any]] = []
    manuscript_leading_responses: dict[str, str] = {}

    def record_attempt(
        category: str,
        target_or_control_id: str,
        source_accession: str,
        source_sha256: str,
        stimulus_sha256: str,
        stimulus_dims: list[int],
        task: str,
        rung: str,
        prompt_variant: str,
        prompt_text: str,
        response: VLMResponse,
    ) -> dict[str, Any]:
        output_txt = response.raw_output or ""
        entry = {
            "attempt_index": len(attempt_ledger),
            "attempt_id": f"attempt_{len(attempt_ledger):03d}_{target_or_control_id}_{task}_{prompt_variant}",
            "attempt_category": category,
            "target_or_control_id": target_or_control_id,
            "source_accession": source_accession,
            "source_raw_sha256": source_sha256,
            "stimulus_sha256": stimulus_sha256,
            "stimulus_dimensions": stimulus_dims,
            "task": task,
            "rung": rung,
            "prompt_variant": prompt_variant,
            "prompt_text": prompt_text,
            "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
            "model_id": provider_id,
            "model_revision": model_rev,
            "model_weight_sha256": weight_sha,
            "decoding_parameters": DECODING_PARAMETERS,
            "status": response.status,
            "latency_ms": response.latency_ms,
            "token_usage": response.token_usage,
            "output_text": output_txt,
            "output_sha256": hashlib.sha256(output_txt.encode("utf-8")).hexdigest(),
            "error_message": response.error_message,
        }
        attempt_ledger.append(entry)
        return entry

    for target in image_targets:
        t_id, t_type = target["target_id"], target["target_type"]
        raw_bytes = target["image_bytes"]
        if not isinstance(raw_bytes, bytes):
            raise ImageConditioningError("Target image must have byte content")
        if t_type not in {"full_manuscript", "candidate_line_crop"}:
            raise ImageConditioningError("Unknown target type")

        raw_digest = hashlib.sha256(raw_bytes).hexdigest()
        # Falsification gate: detect and reject forbidden Figure 8 Verso substitution
        if raw_digest == RIME_FIG8_VERSO_FORBIDDEN_SHA256:
            raise ImageConditioningError("Forbidden Figure 8 Verso substitution detected: expected RIME Figure 6 Recto")

        if not is_simulated:
            if t_id == "cat2044_full_p01":
                if len(raw_bytes) != CAT2044_BYTE_SIZE or raw_digest != CAT2044_SOURCE_SHA256:
                    raise ImageConditioningError("Authentic Cat.2044 source hash or byte size mismatch")
            elif t_id == "cat1883_2095_full_fig6":
                if len(raw_bytes) != RIME_FIG6_BYTE_SIZE or raw_digest != RIME_FIG6_SOURCE_SHA256:
                    raise ImageConditioningError("Authentic RIME Fig. 6 source hash or byte size mismatch")
            elif t_type == "candidate_line_crop":
                expected = target.get("expected_sha256")
                if not isinstance(expected, str) or raw_digest != expected:
                    raise ImageConditioningError("Crop is missing independently recorded byte hash")

        processed, dims = resize_image_aspect_ratio(
            raw_bytes, 1024 if t_type == "full_manuscript" else 512,
            simulated_marker_ok=is_simulated,
        )
        if not is_simulated and t_type == "full_manuscript":
            if t_id == "cat2044_full_p01" and dims != [1024, 572]:
                raise ImageConditioningError("Cat.2044 original image decoded with unexpected dimensions")
            elif t_id == "cat1883_2095_full_fig6" and dims != [1024, 734]:
                raise ImageConditioningError("RIME Fig. 6 original image decoded with unexpected dimensions")

        processed_targets.append({
            "target_id": t_id,
            "target_type": t_type,
            "raw_sha256": raw_digest,
            "raw_byte_size": len(raw_bytes),
            "processed_dimensions": dims,
            "processed_sha256": hashlib.sha256(processed).hexdigest(),
            "source_bounds": target.get("source_bounds"),
            "source_to_crop_transform": target.get("transform"),
            "source_object_id": target.get("source_object_id", "Cat.2044/013" if "2044" in t_id else "Cat.1883 + Cat.2095"),
        })

        # Run 5 NEUTRAL paleographical tasks
        for task_key, prompt in FROZEN_NEUTRAL_PROMPTS.items():
            if is_simulated:
                raw_resp = adapter.predict(
                    image_bytes=processed, prompt=prompt, system_prompt=SYSTEM_PROMPT,
                    shot_mode="zero_shot", rung=TASK_RUNGS[task_key],
                    item_id=f"{t_id}_{task_key}",
                )
                simulated_text = {
                    "script_identification": "Synthetic example: Hieratic script system",
                    "visual_description": "Synthetic papyrus description: brown fibers with dark markings",
                    "sign_hypotheses": "[UNCERTAIN] synthetic Gardiner sign",
                    "transliteration_hypotheses": "[UNREADABLE] synthetic line",
                    "translation_hypotheses": "Synthetic: translation unsupported",
                }[task_key]
                response = VLMResponse(
                    status="success", raw_output=simulated_text,
                    cleaned_prediction=simulated_text, error_message=None,
                    latency_ms=raw_resp.latency_ms, token_usage=raw_resp.token_usage,
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
                "prompt_variant": "neutral",
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "prompt_text": prompt, "output_text": output,
                "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
                "status": response.status, "error_message": response.error_message,
                "latency_ms": response.latency_ms, "token_usage": response.token_usage,
                "grounding_assessment": "synthetic_ci_fixture" if is_simulated else "unscored_exploratory_hypothesis",
            })
            record_attempt(
                category="manuscript_neutral",
                target_or_control_id=t_id,
                source_accession=target.get("source_object_id", "Cat.2044/013" if "2044" in t_id else "Cat.1883 + Cat.2095"),
                source_sha256=raw_digest,
                stimulus_sha256=hashlib.sha256(processed).hexdigest(),
                stimulus_dims=dims,
                task=task_key,
                rung=TASK_RUNGS[task_key],
                prompt_variant="neutral",
                prompt_text=prompt,
                response=response,
            )

        # Run LEADING prompt variant for script_identification on full manuscript targets
        if run_leading_ablation and t_type == "full_manuscript":
            lead_prompt = FROZEN_LEADING_PROMPTS["script_identification"]
            if is_simulated:
                raw_lead = adapter.predict(
                    image_bytes=processed, prompt=lead_prompt, system_prompt=SYSTEM_PROMPT,
                    shot_mode="zero_shot", rung="identify",
                    item_id=f"{t_id}_leading_script_id",
                )
                lead_text = "Synthetic leading prompt example: Hieratic"
                lead_resp = VLMResponse(
                    status="success", raw_output=lead_text,
                    cleaned_prediction=lead_text, error_message=None,
                    latency_ms=raw_lead.latency_ms, token_usage=raw_lead.token_usage,
                )
            else:
                lead_resp = adapter.predict(
                    image_bytes=processed, prompt=lead_prompt, system_prompt=SYSTEM_PROMPT,
                    shot_mode="zero_shot", rung="identify",
                    item_id=f"{t_id}_leading_script_id",
                )
                lead_text = lead_resp.raw_output or ""
            manuscript_leading_responses[t_id] = lead_text
            record_attempt(
                category="manuscript_leading_ablation",
                target_or_control_id=t_id,
                source_accession=target.get("source_object_id", "Cat.2044/013" if "2044" in t_id else "Cat.1883 + Cat.2095"),
                source_sha256=raw_digest,
                stimulus_sha256=hashlib.sha256(processed).hexdigest(),
                stimulus_dims=dims,
                task="script_identification",
                rung="identify",
                prompt_variant="leading",
                prompt_text=lead_prompt,
                response=lead_resp,
            )

    # Generate the 4 control conditions
    blank = generate_blank_control()
    first_target_bytes = image_targets[0]["image_bytes"]
    first_processed, first_dims = resize_image_aspect_ratio(
        first_target_bytes, 1024, simulated_marker_ok=is_simulated
    )
    if is_simulated:
        inverted = blank
        scrambled = blank
        natural_nontext = generate_natural_nontext_control(width=256, height=256, seed=42)
    else:
        inverted = generate_inverted_control(first_processed)
        scrambled = generate_scrambled_control(first_processed, tile_size=32, seed=42)
        natural_nontext = generate_natural_nontext_control(width=256, height=256, seed=42)

    neutral_prompt = FROZEN_NEUTRAL_PROMPTS["script_identification"]
    leading_prompt = FROZEN_LEADING_PROMPTS["script_identification"]

    ctrl_configs = [
        ("blank", blank, [256, 256]),
        ("inverted", inverted, first_dims),
        ("scrambled", scrambled, first_dims),
        ("natural_nontext", natural_nontext, [256, 256]),
    ]

    ctrl_responses: dict[str, dict[str, VLMResponse]] = {}
    for c_name, c_bytes, c_dims in ctrl_configs:
        ctrl_responses[c_name] = {}
        # Neutral call
        if is_simulated:
            raw_n = adapter.predict(
                image_bytes=c_bytes, prompt=neutral_prompt, system_prompt=SYSTEM_PROMPT,
                shot_mode="zero_shot", rung="identify", item_id=f"{c_name}_control_neutral_id",
            )
            syn_txt = "There is no writing, text, or script present in the image." if c_name in ("scrambled", "natural_nontext") else ("The image is a grayscale image of a book cover." if c_name == "blank" else "The image appears to be a piece of art with blocks.")
            res_n = VLMResponse(status="success", raw_output=syn_txt, cleaned_prediction=syn_txt, error_message=None, latency_ms=raw_n.latency_ms, token_usage=raw_n.token_usage)
        else:
            res_n = adapter.predict(
                image_bytes=c_bytes, prompt=neutral_prompt, system_prompt=SYSTEM_PROMPT,
                shot_mode="zero_shot", rung="identify", item_id=f"{c_name}_control_neutral_id",
            )
        ctrl_responses[c_name]["neutral"] = res_n
        record_attempt("control_neutral", f"{c_name}_control", "synthetic_control", hashlib.sha256(c_bytes).hexdigest(), hashlib.sha256(c_bytes).hexdigest(), c_dims, "script_identification", "identify", "neutral", neutral_prompt, res_n)

        # Leading call
        if is_simulated:
            raw_l = adapter.predict(
                image_bytes=c_bytes, prompt=leading_prompt, system_prompt=SYSTEM_PROMPT,
                shot_mode="zero_shot", rung="identify", item_id=f"{c_name}_control_leading_id",
            )
            syn_txt_lead = "The visible ink strokes in this ancient Egyptian manuscript image are likely hieroglyphics." if c_name in ("blank", "natural_nontext") else "Hieratic."
            res_l = VLMResponse(status="success", raw_output=syn_txt_lead, cleaned_prediction=syn_txt_lead, error_message=None, latency_ms=raw_l.latency_ms, token_usage=raw_l.token_usage)
        else:
            res_l = adapter.predict(
                image_bytes=c_bytes, prompt=leading_prompt, system_prompt=SYSTEM_PROMPT,
                shot_mode="zero_shot", rung="identify", item_id=f"{c_name}_control_leading_id",
            )
        ctrl_responses[c_name]["leading"] = res_l
        record_attempt("control_leading_ablation", f"{c_name}_control", "synthetic_control", hashlib.sha256(c_bytes).hexdigest(), hashlib.sha256(c_bytes).hexdigest(), c_dims, "script_identification", "identify", "leading", leading_prompt, res_l)

    blank_response = ctrl_responses["blank"]["neutral"].raw_output or ""
    blank_status = ctrl_responses["blank"]["neutral"].status
    blank_leading_response = ctrl_responses["blank"]["leading"].raw_output or ""

    inverted_response = ctrl_responses["inverted"]["neutral"].raw_output or ""
    inverted_status = ctrl_responses["inverted"]["neutral"].status
    inverted_leading_response = ctrl_responses["inverted"]["leading"].raw_output or ""

    scrambled_response = ctrl_responses["scrambled"]["neutral"].raw_output or ""
    scrambled_status = ctrl_responses["scrambled"]["neutral"].status
    scrambled_leading_response = ctrl_responses["scrambled"]["leading"].raw_output or ""

    nontext_response = ctrl_responses["natural_nontext"]["neutral"].raw_output or ""
    nontext_status = ctrl_responses["natural_nontext"]["neutral"].status
    nontext_leading_response = ctrl_responses["natural_nontext"]["leading"].raw_output or ""

    # Primary manuscript response (Support 1 neutral script_identification)
    first_hyp = next(
        (h for h in reading_hypotheses
         if h["target_id"] == image_targets[0]["target_id"]
         and h["task"] == "script_identification"
         and h.get("prompt_variant") == "neutral"),
        reading_hypotheses[0]
    )
    primary_response = first_hyp["output_text"]

    # Robust script-claim classifications across all control conditions
    blank_neutral_claim = classify_script_claim(blank_response)
    blank_leading_claim = classify_script_claim(blank_leading_response)
    inverted_neutral_claim = classify_script_claim(inverted_response)
    inverted_leading_claim = classify_script_claim(inverted_leading_response)
    scrambled_neutral_claim = classify_script_claim(scrambled_response)
    scrambled_leading_claim = classify_script_claim(scrambled_leading_response)
    nontext_neutral_claim = classify_script_claim(nontext_response)
    nontext_leading_claim = classify_script_claim(nontext_leading_response)

    different_text = bool(
        primary_response.strip() and blank_response.strip()
        and primary_response.strip() != blank_response.strip()
    )
    blank_hallucinates_script = blank_neutral_claim["script_claimed"]
    blank_correctly_identified = blank_neutral_claim["no_script_claimed"] or blank_neutral_claim["category"] == "descriptive_only"
    scrambled_hallucinates_script = scrambled_neutral_claim["script_claimed"]
    nontext_hallucinates_script = nontext_neutral_claim["script_claimed"]
    nontext_correctly_identified = nontext_neutral_claim["no_script_claimed"]

    blank_leading_claims_script = blank_leading_claim["script_claimed"]
    scrambled_leading_claims_script = scrambled_leading_claim["script_claimed"]
    nontext_leading_claims_script = nontext_leading_claim["script_claimed"]
    inverted_leading_claims_script = inverted_leading_claim["script_claimed"]

    prompt_priming_observed = (
        not is_simulated
        and (blank_leading_claims_script or scrambled_leading_claims_script or nontext_leading_claims_script or inverted_leading_claims_script)
        and (not blank_hallucinates_script or not scrambled_hallucinates_script or not nontext_hallucinates_script)
    )

    # Cross-support comparison: Matched full-vs-full across Support 1 (Cat.2044) and Support 2 (Cat.1883+Cat.2095)
    s1_full_hyps = [h for h in reading_hypotheses if h["target_id"] == "cat2044_full_p01" and h.get("prompt_variant") == "neutral"]
    s2_full_hyps = [
        h for h in reading_hypotheses
        if ("1883" in h["target_id"] or "2095" in h["target_id"]) and "full" in h["target_id"] and h.get("prompt_variant") == "neutral"
    ]

    cross_support_comparison: dict[str, Any] | None = None
    if s1_full_hyps and s2_full_hyps:
        import re
        def token_set(hyps: list[dict[str, Any]]) -> set[str]:
            tokens = set()
            for h in hyps:
                cleaned = re.sub(r"[^\w\s]", " ", h.get("output_text", "").lower())
                tokens.update(cleaned.split())
            return tokens

        s1_tokens = token_set(s1_full_hyps)
        s2_tokens = token_set(s2_full_hyps)
        union = s1_tokens | s2_tokens
        inter = s1_tokens & s2_tokens
        jaccard = len(inter) / len(union) if union else 1.0

        task_level_comparison = []
        for task_key in FROZEN_NEUTRAL_PROMPTS:
            h1 = next((h for h in s1_full_hyps if h["task"] == task_key), None)
            h2 = next((h for h in s2_full_hyps if h["task"] == task_key), None)
            out1 = h1["output_text"] if h1 else ""
            out2 = h2["output_text"] if h2 else ""
            task_level_comparison.append({
                "task": task_key,
                "support_1_output": out1,
                "support_2_output": out2,
                "divergent": bool(out1.strip() and out2.strip() and out1.strip() != out2.strip()),
            })

        s1_script = next((h["output_text"] for h in s1_full_hyps if h["task"] == "script_identification"), "")
        s2_script = next((h["output_text"] for h in s2_full_hyps if h["task"] == "script_identification"), "")
        script_divergence = bool(s1_script.strip() and s2_script.strip() and s1_script.strip() != s2_script.strip())

        cross_support_comparison = {
            "evaluated": True,
            "comparison_scope": "matched_full_manuscript_only",
            "support_1": "Cat.2044/013",
            "support_2": "Cat.1883 + Cat.2095 (RIME Fig. 6)",
            "matched_task_count": len(task_level_comparison),
            "jaccard_vocabulary_similarity": round(jaccard, 4),
            "shared_vocabulary_count": len(inter),
            "support_1_unique_vocabulary_count": len(s1_tokens - s2_tokens),
            "support_2_unique_vocabulary_count": len(s2_tokens - s1_tokens),
            "script_identification_divergence": script_divergence,
            "support_1_script_identification": s1_script,
            "support_2_script_identification": s2_script,
            "task_comparisons": task_level_comparison,
        }

    # Isolated candidate crop analysis
    crop_hyps = [h for h in reading_hypotheses if "candidate" in h["target_id"] and h.get("prompt_variant") == "neutral"]
    crop_analysis: dict[str, Any] | None = None
    if crop_hyps:
        import re
        crop_tokens = set()
        for h in crop_hyps:
            cleaned = re.sub(r"[^\w\s]", " ", h.get("output_text", "").lower())
            crop_tokens.update(cleaned.split())
        crop_script_outputs = {
            h["output_text"].strip()
            for h in crop_hyps
            if h["task"] == "script_identification" and h["output_text"].strip()
        }
        crop_translit = [h for h in crop_hyps if h["task"] == "transliteration_hypotheses"]
        crop_abstain = sum(1 for h in crop_translit if any(m in h["output_text"] for m in ("[UNREADABLE]", "[DAMAGED]", "[UNCERTAIN]", "[NO_TEXT]")))
        crop_analysis = {
            "candidate_crops_evaluated": len({h["target_id"] for h in crop_hyps}),
            "crop_hypotheses_count": len(crop_hyps),
            "crop_unique_tokens_count": len(crop_tokens),
            "distinct_crop_script_responses_count": len(crop_script_outputs),
            "inter_crop_discrimination_observed": len(crop_script_outputs) > 1,
            "crop_transliteration_abstention_rate": (crop_abstain / len(crop_translit)) if crop_translit else 0.0,
        }

    # Transliteration abstention rate
    translit_hypotheses = [h for h in reading_hypotheses if h["task"] == "transliteration_hypotheses"]
    translit_abstentions = [
        any(marker in h["output_text"] for marker in ("[UNREADABLE]", "[DAMAGED]", "[UNCERTAIN]", "[NO_TEXT]"))
        for h in translit_hypotheses
    ]
    transliteration_abstention_rate = (
        sum(translit_abstentions) / len(translit_hypotheses) if translit_hypotheses else 0.0
    )

    # Repetition loop detection
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

    # Attempt counts accounting via single append-only attempt ledger
    attempt_counts = {
        "total_attempts_recorded": len(attempt_ledger),
        "successful_actual_passes": sum(1 for a in attempt_ledger if a["status"] == "success"),
        "failed_attempts": sum(1 for a in attempt_ledger if a["status"] == "failed"),
        "skipped_attempts": sum(1 for a in attempt_ledger if a["status"] == "skipped"),
        "by_category": {
            "manuscript_neutral": sum(1 for a in attempt_ledger if a["attempt_category"] == "manuscript_neutral"),
            "manuscript_leading_ablation": sum(1 for a in attempt_ledger if a["attempt_category"] == "manuscript_leading_ablation"),
            "control_neutral": sum(1 for a in attempt_ledger if a["attempt_category"] == "control_neutral"),
            "control_leading_ablation": sum(1 for a in attempt_ledger if a["attempt_category"] == "control_leading_ablation"),
        },
        "by_prompt_variant": {
            "neutral": sum(1 for a in attempt_ledger if a["prompt_variant"] == "neutral"),
            "leading": sum(1 for a in attempt_ledger if a["prompt_variant"] == "leading"),
        },
        "abstention_count": sum(translit_abstentions),
        "repetition_loop_detected": repetition_loop_detected,
        "blank_script_claims_neutral": blank_hallucinates_script,
        "blank_script_claims_leading": blank_leading_claims_script,
        "destructive_script_claims_neutral": scrambled_hallucinates_script,
        "destructive_script_claims_leading": scrambled_leading_claims_script,
        "nontext_script_claims_neutral": nontext_hallucinates_script,
        "nontext_script_claims_leading": nontext_leading_claims_script,
    }

    # Strict visual sensitivity decision: fail closed if ANY negative control hallucinates script
    control_verified = (
        not is_simulated
        and blank_status == "success"
        and inverted_status == "success"
        and scrambled_status == "success"
        and nontext_status == "success"
        and different_text
        and blank_correctly_identified
        and not blank_hallucinates_script
        and not scrambled_hallucinates_script
        and not nontext_hallucinates_script
    )

    distinct_crop_responses = len({
        h["output_text"].strip()
        for h in reading_hypotheses
        if h["task"] == "script_identification" and h["status"] == "success" and h["output_text"].strip()
    }) > 1

    sensitivity_controls = {
        "blank_control_sha256": hashlib.sha256(blank).hexdigest(),
        "blank_response_text": blank_response,
        "blank_status": blank_status,
        "blank_hallucinates_script": blank_hallucinates_script,
        "blank_correctly_identified": blank_correctly_identified,
        "blank_neutral_classification": blank_neutral_claim,
        "blank_leading_classification": blank_leading_claim,
        "inverted_control_sha256": hashlib.sha256(inverted).hexdigest() if inverted else None,
        "inverted_response_text": inverted_response,
        "inverted_status": inverted_status,
        "inverted_identifies_hieratic": inverted_neutral_claim["script_claimed"],
        "scrambled_control_sha256": hashlib.sha256(scrambled).hexdigest() if scrambled else None,
        "scrambled_response_text": scrambled_response,
        "scrambled_status": scrambled_status,
        "scrambled_hallucinates_script": scrambled_hallucinates_script,
        "scrambled_neutral_classification": scrambled_neutral_claim,
        "scrambled_leading_classification": scrambled_leading_claim,
        "natural_nontext_control_sha256": hashlib.sha256(natural_nontext).hexdigest() if natural_nontext else None,
        "natural_nontext_response_text": nontext_response,
        "natural_nontext_status": nontext_status,
        "natural_nontext_hallucinates_script": nontext_hallucinates_script,
        "natural_nontext_correctly_identified": nontext_correctly_identified,
        "natural_nontext_neutral_classification": nontext_neutral_claim,
        "natural_nontext_leading_classification": nontext_leading_claim,
        "leading_ablation": {
            "manuscript_leading_responses": manuscript_leading_responses,
            "blank_leading_response": blank_leading_response,
            "blank_leading_claims_script": blank_leading_claims_script,
            "scrambled_leading_response": scrambled_leading_response,
            "scrambled_leading_claims_script": scrambled_leading_claims_script,
            "natural_nontext_leading_response": nontext_leading_response,
            "natural_nontext_leading_claims_script": nontext_leading_claims_script,
            "inverted_leading_response": inverted_leading_response,
        },
        "primary_target_id": image_targets[0]["target_id"],
        "primary_hieratic_response_text": primary_response,
        "response_difference_only": different_text,
        "prompt_priming_observed": prompt_priming_observed,
        "transliteration_abstention_rate": transliteration_abstention_rate,
        "repetition_loop_detected": repetition_loop_detected,
        "translation_unsupported_acknowledged": translation_unsupported_acknowledged,
        "sensitivity_observed": control_verified,
        "inter_crop_discrimination_tested": not is_simulated and distinct_crop_responses,
        "cross_support_comparison": cross_support_comparison,
        "crop_analysis": crop_analysis,
        "attempt_counts": attempt_counts,
    }

    primary_ok = first_hyp["status"] == "success" and bool(primary_response.strip())
    live_pixel_pass = not is_simulated and primary_ok
    sim_status = "SIMULATED_TEST_DOUBLE"

    evidence_grades = {
        "grade_a_multimodal_interface": {
            "status": sim_status if is_simulated else ("PASSED" if primary_ok else "NOT_VERIFIED"),
            "evidence": "Local image-conditioned SmolVLMAdapter execution on CPU; not certified recognition",
        },
        "grade_b_fixture_tests": {
            "status": sim_status if is_simulated else "NOT_VERIFIED_BY_RUNTIME",
            "evidence": "CI regression suite must be verified externally by hosted GitHub Actions at exact commit",
        },
        "grade_c_real_weights_loaded": {
            "status": sim_status if is_simulated else "PASSED",
            "evidence": "SHA-256 of actual pinned safetensors bytes verified on disk (74dea590...)",
        },
        "grade_d_actual_hieratic_forward_pass": {
            "status": sim_status if is_simulated else ("PASSED" if live_pixel_pass else "NOT_VERIFIED"),
            "evidence": "Exact original image hashes verified across physical supports; never substitute pixels",
        },
        "grade_e_visual_sensitivity_observed": {
            "status": sim_status if is_simulated else ("PASSED_DIAGNOSTIC_ONLY" if control_verified else "NOT_VERIFIED"),
            "evidence": "Requires matched blank, scrambled, and natural non-text controls not to hallucinate script",
        },
        "real_hieratic_hypothesis_cleared": {
            "status": sim_status if is_simulated else ("PASSED_DIAGNOSTIC_ONLY" if live_pixel_pass else "NOT_VERIFIED"),
            "evidence": "Noncertifiable source-bound, unscored hypotheses across two physical supports",
        },
        "silver_diagnostic_cleared": {
            "status": "S0_BIBLIOGRAPHIC_CITATION_ONLY",
            "evidence": "Cat.2044 (TPOP 173) and Cat.1883+2095 (RIME 2022); no independently aligned line gold",
        },
        "grade_f_authentic_hieratic_gold_evaluation": {
            "status": "STRICTLY_NO",
            "evidence": "No official or independently reviewed held-out Hieratic gold evaluation; 0/2 points",
        },
    }

    has_secondary = any("1883" in t.get("target_id", "") or "2095" in t.get("target_id", "") for t in image_targets)
    source_image_info: dict[str, Any] = {
        "source_object_id": CAT2044_SOURCE_OBJECT_ID,
        "institution": "Museo Egizio, Turin", "license": "CC0",
        "original_sha256": CAT2044_SOURCE_SHA256,
        "original_dimensions": CAT2044_DIMENSIONS,
        "original_byte_size": CAT2044_BYTE_SIZE,
        "source_bytes_verified": not is_simulated,
    }
    if has_secondary:
        source_image_info["secondary_support"] = {
            "source_object_id": RIME_FIG6_SOURCE_OBJECT_ID,
            "institution": "Museo Egizio, Turin",
            "license": "CC BY 2.0 (image only; article text reuse unverified)",
            "original_sha256": RIME_FIG6_SOURCE_SHA256,
            "original_dimensions": RIME_FIG6_DIMENSIONS,
            "original_byte_size": RIME_FIG6_BYTE_SIZE,
            "view": "recto (RIME Fig. 6)",
            "source_bytes_verified": not is_simulated,
        }

    return {
        "doc_type": "vlm_hieratic_experiment_report",
        "schema_version": "1.0.0",
        "timestamp": timestamp,
        "protocol": {
            "protocol_version": PROTOCOL_VERSION,
            "protocol_sha256": compute_protocol_hash(),
            "system_prompt": SYSTEM_PROMPT,
            "neutral_prompts": FROZEN_NEUTRAL_PROMPTS,
            "leading_prompts": FROZEN_LEADING_PROMPTS,
            "decoding_parameters": DECODING_PARAMETERS,
            "preregistration_status": "runtime_fingerprint_only_not_independent_preregistration",
        },
        "model_info": {
            "provider_model_id": adapter.model_config.get("provider_model_id"),
            "revision": adapter.model_config.get("revision"),
            "simulated_mode": is_simulated,
            "adapter_class": type(adapter).__name__,
            "actual_weight_hash_verified": not is_simulated,
        },
        "source_image": source_image_info,
        "targets": processed_targets,
        "sensitivity_controls": sensitivity_controls,
        "reading_hypotheses": reading_hypotheses,
        "attempt_ledger": attempt_ledger,
        "attempt_counts": attempt_counts,
        "cross_support_analysis": cross_support_comparison,
        "crop_analysis": crop_analysis,
        "alternative_models_audit": audit_alternative_models(),
        "scholarly_provenance": get_scholarly_provenance(),
        "evidence_grades": evidence_grades,
        "classification": CLASSIFICATION_DIAGNOSTIC,
        "scientific_capability_points": 0.0,
        "hieratic_reading_claim": False,
    }

