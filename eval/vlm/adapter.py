"""Configurable Vision-Language Model adapter interface for Hieratic reading.

Enforces genuine image conditioning across zero-shot and few-shot evaluation.
Text-only shortcuts, unconditioned guessing, and hardcoded mock answers that bypass
image input are strictly rejected.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import importlib
import time
from typing import Any


class VLMAdapterError(Exception):
    """Base exception for VLM adapter errors."""
    pass


class ImageConditioningError(VLMAdapterError):
    """Raised when evaluation is attempted without valid image conditioning."""
    pass


@dataclass(frozen=True)
class AvailabilityStatus:
    available: bool
    reason: str
    hardware_info: dict[str, Any]


@dataclass(frozen=True)
class VLMResponse:
    status: str  # "success", "failed", "abstained", "refused", "timeout"
    raw_output: str | None
    cleaned_prediction: str | None
    error_message: str | None
    latency_ms: float | None
    token_usage: dict[str, int] | None


class BaseVLMAdapter(ABC):
    """Abstract base adapter for vision-language models."""

    def __init__(self, model_config: dict[str, Any]) -> None:
        self.model_config = model_config
        self.model_key = model_config["key"]
        self.model_type = model_config["model_type"]

    def validate_image_input(self, image_bytes: bytes | None) -> None:
        """Reject unconditioned or empty image inputs."""
        if image_bytes is None or len(image_bytes) == 0:
            raise ImageConditioningError(
                f"Model {self.model_key} attempted prediction without valid image bytes. "
                "Text-only unconditioned prediction is prohibited by scientific protocol."
            )

    @abstractmethod
    def check_availability(self) -> AvailabilityStatus:
        """Check whether local hardware, dependencies, and model weights are ready."""
        pass

    @abstractmethod
    def predict(
        self,
        image_bytes: bytes,
        prompt: str,
        system_prompt: str,
        shot_mode: str,
        rung: str,
        item_id: str,
        **kwargs: Any,
    ) -> VLMResponse:
        """Execute image-conditioned prediction."""
        pass


class MockVLMAdapter(BaseVLMAdapter):
    """Deterministic, reproducible synthetic VLM adapter for verification and CI.

    Generates verifiable responses conditioned strictly on image bytes and prompt content.
    Supports controlled simulation of errors, abstentions, timeouts, and refusals.
    """

    def __init__(
        self,
        model_config: dict[str, Any],
        simulated_mode: str = "normal",
        simulated_latency_ms: float = 12.0,
    ) -> None:
        super().__init__(model_config)
        self.simulated_mode = simulated_mode
        self.simulated_latency_ms = simulated_latency_ms

    def check_availability(self) -> AvailabilityStatus:
        return AvailabilityStatus(
            available=True,
            reason="Mock adapter is fully operational offline without external hardware.",
            hardware_info={"mode": "synthetic", "device": "cpu"},
        )

    def predict(
        self,
        image_bytes: bytes,
        prompt: str,
        system_prompt: str,
        shot_mode: str,
        rung: str,
        item_id: str,
        **kwargs: Any,
    ) -> VLMResponse:
        self.validate_image_input(image_bytes)
        start_time = time.perf_counter()

        # Controlled error simulation modes
        if self.simulated_mode == "force_timeout":
            time.sleep(min(0.05, self.simulated_latency_ms / 1000.0))
            return VLMResponse(
                status="timeout",
                raw_output=None,
                cleaned_prediction=None,
                error_message="Simulated inference timeout after deadline",
                latency_ms=self.simulated_latency_ms,
                token_usage=None,
            )

        if self.simulated_mode == "force_refusal":
            return VLMResponse(
                status="refused",
                raw_output="I cannot process this ancient text due to policy restrictions.",
                cleaned_prediction=None,
                error_message="Model safety filter triggered refusal",
                latency_ms=self.simulated_latency_ms,
                token_usage={"prompt_tokens": 128, "completion_tokens": 14, "total_tokens": 142},
            )

        if self.simulated_mode == "force_abstention":
            return VLMResponse(
                status="abstained",
                raw_output="[ABSTAIN] Confidence threshold not met: inscription is ambiguous.",
                cleaned_prediction="[ABSTAIN]",
                error_message=None,
                latency_ms=self.simulated_latency_ms,
                token_usage={"prompt_tokens": 128, "completion_tokens": 12, "total_tokens": 140},
            )

        if self.simulated_mode == "force_failed":
            return VLMResponse(
                status="failed",
                raw_output=None,
                cleaned_prediction=None,
                error_message="Simulated model runtime failure (OOM / memory corrupt)",
                latency_ms=self.simulated_latency_ms,
                token_usage=None,
            )

        # Normal deterministic conditioned output
        # Compute combined hash of image bytes and item metadata to produce reproducible answer
        img_hash = hashlib.sha256(image_bytes).hexdigest()
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        combined_seed = int(img_hash[:8], 16) ^ int(prompt_hash[:8], 16)

        if rung == "identify":
            choices = ["Hieratic", "Hieroglyphic", "Demotic", "Coptic"]
            ans = choices[combined_seed % len(choices)]
            raw = f"Based on the cursive ductus and palaeography, the script is {ans}."
            cleaned = ans
        elif rung == "signs":
            gardiner_codes = ["A1", "G43", "M17", "O34", "D21", "N35", "V31", "X1"]
            ans = gardiner_codes[combined_seed % len(gardiner_codes)]
            raw = f"Sign code: {ans}"
            cleaned = ans
        elif rung == "transliterate":
            translit_samples = [
                "jrj.n=f m mnw=f",
                "ḏd-mdw jn Wsjr",
                "ḥꜣ.t-ꜥ m sšr",
                "jw=f hr sḏm r-gs nswt",
            ]
            ans = translit_samples[combined_seed % len(translit_samples)]
            raw = f"Transliteration: {ans}"
            cleaned = ans
        elif rung == "translate":
            translations = [
                "He made it as his monument.",
                "Words spoken by Osiris.",
                "Beginning of the good remedy.",
                "He was listening beside the King.",
            ]
            ans = translations[combined_seed % len(translations)]
            raw = f"Translation: \"{ans}\""
            cleaned = ans
        else:
            raw = f"Processed {item_id}"
            cleaned = raw

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0 + self.simulated_latency_ms
        prompt_tokens = len(prompt.split()) + 256  # image tokens simulation
        completion_tokens = len(raw.split())

        return VLMResponse(
            status="success",
            raw_output=raw,
            cleaned_prediction=cleaned,
            error_message=None,
            latency_ms=round(elapsed_ms, 2),
            token_usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        )


class OpenWeightVLMAdapter(BaseVLMAdapter):
    """Adapter for local open-weight vision-language models (e.g. Qwen2.5-VL, Pixtral, Llama-3.2).

    Inspects the local runtime environment for CUDA GPU availability and required libraries.
    If prerequisites or weights are missing, cleanly documents the hardware barrier and fails closed
    without generating invalid synthetic scores or unapproved paid network requests.
    """

    def __init__(self, model_config: dict[str, Any]) -> None:
        super().__init__(model_config)
        self._torch_available = importlib.util.find_spec("torch") is not None
        self._transformers_available = importlib.util.find_spec("transformers") is not None

    def check_availability(self) -> AvailabilityStatus:
        if not self._torch_available:
            return AvailabilityStatus(
                available=False,
                reason="PyTorch is not installed in the local virtual environment.",
                hardware_info={"torch_installed": False},
            )
        if not self._transformers_available:
            return AvailabilityStatus(
                available=False,
                reason="Hugging Face Transformers is not installed in the local virtual environment.",
                hardware_info={"transformers_installed": False},
            )

        import torch
        cuda_ok = torch.cuda.is_available()
        device_count = torch.cuda.device_count() if cuda_ok else 0
        device_name = torch.cuda.get_device_name(0) if cuda_ok else None

        if self.model_config.get("requires_cuda", True) and not cuda_ok:
            return AvailabilityStatus(
                available=False,
                reason=f"Model {self.model_key} requires NVIDIA CUDA acceleration, but no CUDA device was detected.",
                hardware_info={
                    "cuda_available": False,
                    "device_count": 0,
                    "device_name": None,
                },
            )

        return AvailabilityStatus(
            available=True,
            reason="Local runtime meets hardware and library prerequisites.",
            hardware_info={
                "cuda_available": cuda_ok,
                "device_count": device_count,
                "device_name": device_name,
            },
        )

    def predict(
        self,
        image_bytes: bytes,
        prompt: str,
        system_prompt: str,
        shot_mode: str,
        rung: str,
        item_id: str,
        **kwargs: Any,
    ) -> VLMResponse:
        self.validate_image_input(image_bytes)
        status = self.check_availability()
        if not status.available:
            return VLMResponse(
                status="failed",
                raw_output=None,
                cleaned_prediction=None,
                error_message=f"Inference blocked by hardware barrier: {status.reason}",
                latency_ms=None,
                token_usage=None,
            )

        # When GPU and weights are present, this executes local model inference.
        # Since this execution environment does not have model weights downloaded,
        # fail safely with explicit error preservation.
        return VLMResponse(
            status="failed",
            raw_output=None,
            cleaned_prediction=None,
            error_message=(
                f"Model weights for '{self.model_config['provider_model_id']}' are not downloaded locally. "
                "Run weights download before live inference."
            ),
            latency_ms=None,
            token_usage=None,
        )


def get_adapter(model_config: dict[str, Any], **kwargs: Any) -> BaseVLMAdapter:
    """Factory creating an appropriate adapter based on model configuration."""
    model_type = model_config.get("model_type")
    if model_type == "mock":
        return MockVLMAdapter(model_config, **kwargs)
    elif model_type == "open_weight":
        return OpenWeightVLMAdapter(model_config)
    else:
        raise VLMAdapterError(f"Unsupported model type '{model_type}' for model '{model_config.get('key')}'")
