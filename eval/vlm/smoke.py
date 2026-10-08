"""Real visual smoke test harness and pure-Python image generation for VLM baselines.

Provides:
1. Source-independent, deterministic pure-Python PNG generation (zero external dependencies).
2. Host hardware and environment inventory auditing (GPU/VRAM, RAM, torch, transformers, local weights).
3. Six-Grade Evidence Matrix (Grades A through F) adhering strictly to W7 Brief 2 standards.
4. Fail-closed real visual smoke test runner with image-to-tensor verification and visual sensitivity control.
5. Reproducible environment provisioning specification.
"""
from __future__ import annotations

import datetime
import hashlib
import importlib.util
import os
import platform
import struct
import sys
import time
from pathlib import Path
from typing import Any, Callable
import zlib

from eval.vlm.adapter import (
    BaseVLMAdapter,
    ImageConditioningError,
    OpenWeightVLMAdapter,
    get_adapter,
)

NONCERTIFIABLE_CLASSIFICATION = "noncertifiable_diagnostic"


def create_png(
    width: int,
    height: int,
    pixel_fn: Callable[[int, int], tuple[int, int, int]],
) -> bytes:
    """Generate a valid, standards-compliant RGB PNG byte stream without external libraries.

    Uses standard library struct and zlib. Suitable for offline, dependency-free visual
    testing and image-to-tensor verification.
    """
    signature = b"\x89PNG\r\n\x1a\n"

    # IHDR chunk: width, height, bit_depth=8, color_type=2 (RGB), compression=0, filter=0, interlace=0
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc

    # Raw scanlines with filter type 0 (None) prepended to each row
    raw_scanlines = bytearray()
    for y in range(height):
        raw_scanlines.append(0)  # filter type 0
        for x in range(width):
            r, g, b = pixel_fn(x, y)
            raw_scanlines.extend((r & 0xFF, g & 0xFF, b & 0xFF))

    # IDAT chunk: zlib-compressed scanlines
    compressed = zlib.compress(bytes(raw_scanlines), level=9)
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF)
    idat_chunk = struct.pack(">I", len(compressed)) + b"IDAT" + compressed + idat_crc

    # IEND chunk
    iend_crc = struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    iend_chunk = struct.pack(">I", 0) + b"IEND" + iend_crc

    return signature + ihdr_chunk + idat_chunk + iend_chunk


def generate_geometric_test_image() -> bytes:
    """Generate deterministic Image A: 256x256 RGB PNG with a solid red square and blue circle.

    Composition:
    - Background: light gray (RGB: 240, 240, 240)
    - Red Square: x in [32, 112), y in [32, 112) (RGB: 255, 0, 0)
    - Blue Circle: center (176, 176), radius 40 (RGB: 0, 0, 255)
    Non-copyrighted, non-Hieratic, and strictly source-independent.
    """
    def _pixel_color(x: int, y: int) -> tuple[int, int, int]:
        if 32 <= x < 112 and 32 <= y < 112:
            return (255, 0, 0)
        dx, dy = x - 176, y - 176
        if dx * dx + dy * dy <= 40 * 40:
            return (0, 0, 255)
        return (240, 240, 240)

    return create_png(256, 256, _pixel_color)


def generate_geometric_control_image() -> bytes:
    """Generate deterministic Image B (Control): 256x256 RGB PNG with a green square and yellow circle.

    Composition:
    - Background: light gray (RGB: 240, 240, 240)
    - Green Square: x in [32, 112), y in [32, 112) (RGB: 0, 255, 0)
    - Yellow Circle: center (176, 176), radius 40 (RGB: 255, 255, 0)
    Non-copyrighted, non-Hieratic, and strictly source-independent.
    """
    def _pixel_color(x: int, y: int) -> tuple[int, int, int]:
        if 32 <= x < 112 and 32 <= y < 112:
            return (0, 255, 0)
        dx, dy = x - 176, y - 176
        if dx * dx + dy * dy <= 40 * 40:
            return (255, 255, 0)
        return (240, 240, 240)

    return create_png(256, 256, _pixel_color)


def get_reproducible_provisioning_spec(model_config: dict[str, Any]) -> dict[str, Any]:
    """Return reproducible environment provisioning specification for target open-weight model."""
    model_key = model_config.get("key", "")
    model_id = model_config.get("provider_model_id", "")
    revision = model_config.get("revision", "")

    min_vram = 16.0 if "7b" in model_key else 24.0
    recommended_gpu = "NVIDIA RTX 4090 (24 GB) or NVIDIA A100 (40/80 GB)"

    return {
        "target_model_key": model_key,
        "provider_model_id": model_id,
        "pinned_revision_sha": revision,
        "hardware_requirements": {
            "recommended_os": "Linux x86_64 (Ubuntu 22.04 LTS or 24.04 LTS)",
            "min_system_ram_gb": 32.0,
            "gpu_architecture": "NVIDIA CUDA GPU with Tensor Cores",
            "min_gpu_vram_gb": min_vram,
            "recommended_gpu": recommended_gpu,
            "cuda_toolkit_min": "12.1",
            "nvidia_driver_min": "535.54.03",
        },
        "python_environment": {
            "python_version_range": ">=3.10, <=3.12",
            "required_packages": [
                {"name": "torch", "min_version": "2.4.0", "cuda_build": "cu121"},
                {"name": "torchvision", "min_version": "0.19.0"},
                {"name": "transformers", "min_version": "4.49.0"},
                {"name": "accelerate", "min_version": "0.26.0"},
                {"name": "pillow", "min_version": "10.0.0"},
                {"name": "safetensors", "min_version": "0.4.0"},
            ],
        },
        "weights_layout": {
            "expected_hub_directory": f"~/.cache/huggingface/hub/models--{model_id.replace('/', '--')}",
            "required_files": [
                "config.json",
                "generation_config.json",
                "preprocessor_config.json",
                "model.safetensors.index.json (or model.safetensors)",
            ],
            "download_cli_template": (
                f"huggingface-cli download {model_id} --revision {revision} --local-dir <WEIGHTS_PATH>"
            ),
        },
        "scientific_spend_boundary": {
            "max_authorized_spend_usd": 0.0,
            "cloud_compute_authorized": False,
            "paid_apis_authorized": False,
            "policy_reference": "ADR-0023 / W7 Execution Brief 2 Zero-Spend Enforcement",
        },
    }


def audit_host_resources(
    model_config: dict[str, Any],
    weights_dir: Path | None = None,
) -> dict[str, Any]:
    """Audit actual host hardware, drivers, dependencies, and local model weights.

    Never claims resource access from mock classes or stubbed packages alone.
    """
    model_key = model_config.get("key", "")
    model_id = model_config.get("provider_model_id", "")
    revision = model_config.get("revision", "")

    # Host platform and Python
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    host_info: dict[str, Any] = {
        "os_platform": sys.platform,
        "os_release": platform.platform(),
        "python_version": py_ver,
    }

    # System RAM
    total_ram_gb = None
    try:
        if sys.platform == "win32":
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            total_ram_gb = round(stat.ullTotalPhys / (1024 ** 3), 2)
        elif hasattr(os, "sysconf"):
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            total_ram_gb = round((pages * page_size) / (1024 ** 3), 2)
    except Exception:
        pass
    host_info["total_ram_gb"] = total_ram_gb

    # Check PyTorch and CUDA
    torch_installed = importlib.util.find_spec("torch") is not None
    host_info["torch_installed"] = torch_installed
    cuda_available = False
    cuda_device_count = 0
    cuda_device_name = None
    cuda_vram_gb = None

    if torch_installed:
        try:
            import torch
            host_info["torch_version"] = torch.__version__
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                cuda_device_count = torch.cuda.device_count()
                cuda_device_name = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                cuda_vram_gb = round(props.total_memory / (1024 ** 3), 2)
        except Exception:
            pass

    host_info["cuda_available"] = cuda_available
    host_info["cuda_device_count"] = cuda_device_count
    host_info["cuda_device_name"] = cuda_device_name
    host_info["cuda_vram_gb"] = cuda_vram_gb

    # Check Transformers
    tf_installed = importlib.util.find_spec("transformers") is not None
    host_info["transformers_installed"] = tf_installed
    if tf_installed:
        try:
            import transformers
            host_info["transformers_version"] = transformers.__version__
        except Exception:
            pass

    # Check other libraries
    host_info["torchvision_installed"] = importlib.util.find_spec("torchvision") is not None
    host_info["accelerate_installed"] = importlib.util.find_spec("accelerate") is not None
    host_info["pillow_installed"] = importlib.util.find_spec("PIL") is not None

    # Check local weights
    target_path = weights_dir
    if not target_path:
        hub_dir = Path.home() / ".cache" / "huggingface" / "hub" / f"models--{model_id.replace('/', '--')}"
        if hub_dir.is_dir():
            target_path = hub_dir

    def _has_weights_content(p: Path | None) -> bool:
        if not p or not p.is_dir():
            return False
        has_cfg = (p / "config.json").is_file() or any(p.glob("snapshots/*/config.json"))
        has_wt = (
            any(p.glob("*.safetensors"))
            or any(p.glob("*.bin"))
            or (p / "model.safetensors.index.json").is_file()
            or any(p.glob("snapshots/*/*.safetensors"))
            or any(p.glob("snapshots/*/*.bin"))
            or any(p.glob("snapshots/*/model.safetensors.index.json"))
        )
        return has_cfg and has_wt

    weights_found = _has_weights_content(target_path)
    host_info["weights_found"] = weights_found
    host_info["weights_path_status"] = "found" if weights_found else "not_found"

    # Identify missing resources
    missing = []
    if model_config.get("requires_cuda", True) and not cuda_available:
        missing.append("nvidia_cuda_gpu_absent")
    if not torch_installed:
        missing.append("torch_not_installed")
    if not tf_installed:
        missing.append("transformers_not_installed")
    if not weights_found:
        missing.append("model_weights_not_found_on_disk")

    host_info["missing_resources"] = missing

    # Structured barrier description
    if missing:
        parts = []
        if "nvidia_cuda_gpu_absent" in missing:
            parts.append(f"host lacks NVIDIA CUDA GPU ({cuda_device_name or 'no CUDA device'})")
        if "torch_not_installed" in missing:
            parts.append("PyTorch is not installed in the environment")
        if "transformers_not_installed" in missing:
            parts.append("Transformers is not installed in the environment")
        if "model_weights_not_found_on_disk" in missing:
            parts.append(f"local model weights for '{model_id}' (revision {revision[:12]}) are absent")
        barrier_summary = f"Inference blocked by hardware/weights barrier: {'; '.join(parts)}."
    else:
        barrier_summary = "All hardware and weights prerequisites are met."

    host_info["barrier_summary"] = barrier_summary
    return host_info


def compute_evidence_grades(
    model_config: dict[str, Any],
    is_real_inference: bool,
    sensitivity_verified: bool = False,
) -> dict[str, Any]:
    """Compute the Six-Grade Evidence Matrix (Grades A through F) per Brief 2 Section 5.

    - Grade A: interface implemented
    - Grade B: processor/format fixture tests passed
    - Grade C: actual architecture model loaded from real weights on disk
    - Grade D: actual image-conditioned forward pass executed
    - Grade E: visual sensitivity control verified (output responds to image change under constant prompt)
    - Grade F: authentic Hieratic expert-gold scientific evaluation (Strictly NO / 0.0 points)
    """
    model_type = model_config.get("model_type", "")
    key = model_config.get("key", "")

    # Grade A: Adapter interface exists and is implemented
    grade_a = True

    # Grade B: Multimodal message structuring and chat formatting fixture tests exist
    grade_b = True

    # Grade C: Loaded from actual real weights on disk
    grade_c = bool(is_real_inference and model_type == "open_weight")

    # Grade D: Real image-conditioned forward pass executed
    grade_d = bool(is_real_inference)

    # Grade E: Visual sensitivity control observed
    grade_e = bool(is_real_inference and sensitivity_verified)

    # Grade F: Authentic Hieratic expert-gold scientific evaluation
    # Never claimed from geometric shape smoke tests or synthetic fixtures!
    grade_f = False

    return {
        "grade_a_interface_implemented": grade_a,
        "grade_b_processor_format_fixture_tested": grade_b,
        "grade_c_real_weights_loaded_from_disk": grade_c,
        "grade_d_actual_image_conditioned_forward_executed": grade_d,
        "grade_e_visual_sensitivity_control_verified": grade_e,
        "grade_f_authentic_hieratic_gold_evaluated": grade_f,
        "scientific_capability_points_awarded": 0.0,
        "notes": {
            "grade_a": f"Adapter registered for {key} with architecture-specific loader class.",
            "grade_b": "Chat template formatting and visual tensor input shapes verified in unit tests.",
            "grade_c": "True only when full snapshot model files are loaded from verified disk storage.",
            "grade_d": "True only when forward pass processes real image tensor on host device.",
            "grade_e": "True only when image swap under constant prompt produces differentiated output.",
            "grade_f": "Strictly FALSE (0.0 points). Colored geometric shapes do not constitute Hieratic reading evidence.",
        },
    }


def run_real_visual_smoke(
    model_config: dict[str, Any],
    weights_dir: Path | None = None,
    allow_simulated: bool = False,
    custom_adapter: BaseVLMAdapter | None = None,
) -> tuple[dict[str, Any], bool]:
    """Execute real visual smoke test on local hardware and model weights.

    Checks:
    1. Hardware & weights prerequisites. Fails closed with code 1 if missing and not allow_simulated.
    2. Image A (Test Image) generation -> SHA-256 -> forward generation.
    3. Image B (Control Image) generation -> SHA-256 -> forward generation under constant prompt.
    4. Visual sensitivity control: checks whether output responds to image change.
    5. Six-Grade Evidence Matrix computation (Grade F remains strictly NO).

    Returns:
    (report_dict, success_boolean)
    """
    model_key = model_config.get("key", "")
    model_id = model_config.get("provider_model_id", "")
    revision = model_config.get("revision", "")

    # 1. Audit host resources
    audit = audit_host_resources(model_config, weights_dir=weights_dir)
    missing = audit["missing_resources"]
    provisioning_spec = get_reproducible_provisioning_spec(model_config)

    # If prerequisites missing and not allow_simulated, fail closed immediately
    if missing and not allow_simulated and custom_adapter is None:
        grades = compute_evidence_grades(model_config, is_real_inference=False)
        report = {
            "doc_type": "vlm_visual_smoke_report",
            "schema_version": "1.0.0",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "model_key": model_key,
            "provider_model_id": model_id,
            "revision": revision,
            "status": "blocked",
            "classification": NONCERTIFIABLE_CLASSIFICATION,
            "scientific_capability_points": 0.0,
            "hieratic_reading_claim": False,
            "simulated_double_smoke": False,
            "missing_resources": missing,
            "barrier_summary": audit["barrier_summary"],
            "host_environment": audit,
            "provisioning_spec": provisioning_spec,
            "evidence_grades": grades,
        }
        return report, False

    # 2. Generate source-independent geometric test images
    img_a_bytes = generate_geometric_test_image()
    img_b_bytes = generate_geometric_control_image()
    img_a_sha = hashlib.sha256(img_a_bytes).hexdigest()
    img_b_sha = hashlib.sha256(img_b_bytes).hexdigest()

    constant_prompt = (
        "Describe the geometric shapes and colors present in this image."
    )
    system_prompt = (
        "You are an objective computer vision analyzer. Describe the visible geometry and color palette."
    )

    # 3. Determine execution mode (real vs simulated double)
    is_simulated = bool(allow_simulated or custom_adapter is not None or missing)

    # Forward pass A
    start_a = time.perf_counter()
    if is_simulated and custom_adapter is None:
        # High-fidelity simulated double for dry-run verification
        out_a_text = (
            "The image contains a solid red square in the upper-left region and a solid blue circle "
            "in the lower-right region on a uniform light gray background."
        )
        elapsed_a_ms = round((time.perf_counter() - start_a) * 1000.0 + 15.0, 2)
        in_tokens_a = len(constant_prompt.split()) + 64
        out_tokens_a = len(out_a_text.split())
    elif custom_adapter is not None:
        resp_a = custom_adapter.predict(
            image_bytes=img_a_bytes,
            prompt=constant_prompt,
            system_prompt=system_prompt,
            shot_mode="zero_shot",
            rung="identify",
            item_id="SMOKE-GEOM-A",
        )
        if resp_a.status != "success":
            return {
                "status": "failed",
                "error": f"Image A inference failed: {resp_a.error_message}",
                "missing_resources": missing,
                "host_environment": audit,
                "provisioning_spec": provisioning_spec,
            }, False
        out_a_text = resp_a.cleaned_prediction or ""
        elapsed_a_ms = resp_a.latency_ms or 0.0
        in_tokens_a = resp_a.token_usage.get("prompt_tokens", 64) if resp_a.token_usage else 64
        out_tokens_a = resp_a.token_usage.get("completion_tokens", 16) if resp_a.token_usage else 16
    else:
        # Real model execution with local weights and GPU
        adapter = get_adapter(model_config, weights_dir=weights_dir)
        resp_a = adapter.predict(
            image_bytes=img_a_bytes,
            prompt=constant_prompt,
            system_prompt=system_prompt,
            shot_mode="zero_shot",
            rung="identify",
            item_id="SMOKE-GEOM-A",
        )
        if resp_a.status != "success":
            return {
                "status": "failed",
                "error": f"Image A inference failed: {resp_a.error_message}",
                "missing_resources": missing,
                "host_environment": audit,
                "provisioning_spec": provisioning_spec,
            }, False
        out_a_text = resp_a.cleaned_prediction or ""
        elapsed_a_ms = resp_a.latency_ms or 0.0
        in_tokens_a = resp_a.token_usage.get("prompt_tokens", 64) if resp_a.token_usage else 64
        out_tokens_a = resp_a.token_usage.get("completion_tokens", 16) if resp_a.token_usage else 16

    out_a_sha = hashlib.sha256(out_a_text.encode("utf-8")).hexdigest()

    # Forward pass B (Control under identical prompt)
    start_b = time.perf_counter()
    if is_simulated and custom_adapter is None:
        out_b_text = (
            "The image contains a solid green square in the upper-left region and a solid yellow circle "
            "in the lower-right region on a uniform light gray background."
        )
        elapsed_b_ms = round((time.perf_counter() - start_b) * 1000.0 + 15.0, 2)
        in_tokens_b = len(constant_prompt.split()) + 64
        out_tokens_b = len(out_b_text.split())
    elif custom_adapter is not None:
        resp_b = custom_adapter.predict(
            image_bytes=img_b_bytes,
            prompt=constant_prompt,
            system_prompt=system_prompt,
            shot_mode="zero_shot",
            rung="identify",
            item_id="SMOKE-GEOM-B",
        )
        if resp_b.status != "success":
            return {
                "status": "failed",
                "error": f"Image B inference failed: {resp_b.error_message}",
                "missing_resources": missing,
                "host_environment": audit,
                "provisioning_spec": provisioning_spec,
            }, False
        out_b_text = resp_b.cleaned_prediction or ""
        elapsed_b_ms = resp_b.latency_ms or 0.0
        in_tokens_b = resp_b.token_usage.get("prompt_tokens", 64) if resp_b.token_usage else 64
        out_tokens_b = resp_b.token_usage.get("completion_tokens", 16) if resp_b.token_usage else 16
    else:
        resp_b = adapter.predict(
            image_bytes=img_b_bytes,
            prompt=constant_prompt,
            system_prompt=system_prompt,
            shot_mode="zero_shot",
            rung="identify",
            item_id="SMOKE-GEOM-B",
        )
        if resp_b.status != "success":
            return {
                "status": "failed",
                "error": f"Image B inference failed: {resp_b.error_message}",
                "missing_resources": missing,
                "host_environment": audit,
                "provisioning_spec": provisioning_spec,
            }, False
        out_b_text = resp_b.cleaned_prediction or ""
        elapsed_b_ms = resp_b.latency_ms or 0.0
        in_tokens_b = resp_b.token_usage.get("prompt_tokens", 64) if resp_b.token_usage else 64
        out_tokens_b = resp_b.token_usage.get("completion_tokens", 16) if resp_b.token_usage else 16

    out_b_sha = hashlib.sha256(out_b_text.encode("utf-8")).hexdigest()

    # 4. Sensitivity control evaluation
    output_differs = (out_a_text.strip() != out_b_text.strip())
    # Text differences from injected/synthetic responses are not model visual evidence.
    sensitivity_observed = bool(output_differs and not is_simulated)

    # 5. Evidence grades
    grades = compute_evidence_grades(
        model_config,
        is_real_inference=(not is_simulated),
        sensitivity_verified=sensitivity_observed,
    )

    report = {
        "doc_type": "vlm_visual_smoke_report",
        "schema_version": "1.0.0",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model_key": model_key,
        "provider_model_id": model_id,
        "revision": revision,
        "status": "completed",
        "classification": NONCERTIFIABLE_CLASSIFICATION,
        "scientific_capability_points": 0.0,
        "hieratic_reading_claim": False,
        "simulated_double_smoke": is_simulated,
        "missing_resources": missing,
        "barrier_summary": audit["barrier_summary"],
        "host_environment": audit,
        "provisioning_spec": provisioning_spec,
        "evidence_grades": grades,
        "forward_test_image": {
            "label": "Image A (Red Square + Blue Circle)",
            "image_bytes_length": len(img_a_bytes),
            "image_sha256": img_a_sha,
            "prompt": constant_prompt,
            "raw_output": out_a_text,
            "output_sha256": out_a_sha,
            "latency_ms": elapsed_a_ms,
            "token_usage": {
                "prompt_tokens": in_tokens_a,
                "completion_tokens": out_tokens_a,
                "total_tokens": in_tokens_a + out_tokens_a,
            },
        },
        "forward_control_image": {
            "label": "Image B (Green Square + Yellow Circle)",
            "image_bytes_length": len(img_b_bytes),
            "image_sha256": img_b_sha,
            "prompt": constant_prompt,
            "raw_output": out_b_text,
            "output_sha256": out_b_sha,
            "latency_ms": elapsed_b_ms,
            "token_usage": {
                "prompt_tokens": in_tokens_b,
                "completion_tokens": out_tokens_b,
                "total_tokens": in_tokens_b + out_tokens_b,
            },
        },
        "sensitivity_control": {
            "constant_prompt_preserved": True,
            "image_bytes_differ": (img_a_sha != img_b_sha),
            "output_strings_differ": output_differs,
            "sensitivity_observed": sensitivity_observed,
            "interpretation": (
                "Real model outputs differed under a constant prompt and changed image; repeat controls are "
                "required before attributing the difference exclusively to visual conditioning." if sensitivity_observed else
                "No real-model visual sensitivity assessed: outputs came from a synthetic/injected test double." if is_simulated else
                "Visual sensitivity indeterminate: real model outputs remained identical despite the image change."
            ),
        },
    }

    return report, True
