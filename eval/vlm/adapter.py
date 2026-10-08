"""Configurable Vision-Language Model adapter interface for Hieratic reading.

Enforces genuine image conditioning across zero-shot and few-shot evaluation.
Text-only shortcuts, unconditioned guessing, and hardcoded mock answers that bypass
image input are strictly rejected.

Real few-shot inference fails closed if demonstration records are unreviewed or lack
authentic image files on disk. Live open-weight inference requires verified local weights,
CUDA GPU hardware, and genuine image-tensor conditioning.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import importlib
import io
from pathlib import Path
import time
from typing import Any


class VLMAdapterError(Exception):
    """Base exception for VLM adapter errors."""
    pass


class ImageConditioningError(VLMAdapterError):
    """Raised when evaluation is attempted without valid image conditioning."""
    pass


class UnverifiedDemonstrationError(VLMAdapterError):
    """Raised when real few-shot inference is attempted with unverified or synthetic demonstration fixtures."""
    pass


class LiveFewShotBlockedError(VLMAdapterError):
    """Raised when live few-shot inference is attempted without verified multi-image vision templates and audited exemplar pixels."""
    pass


class InferenceHardwareBarrierError(VLMAdapterError):
    """Raised when open-weight model inference is blocked by missing local hardware or unprovisioned weights."""
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

    execution_tier: str = "base"
    scientific_validity: str = "unspecified"

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
        demonstrations_meta: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> VLMResponse:
        """Execute image-conditioned prediction."""
        pass


class MockVLMAdapter(BaseVLMAdapter):
    """Deterministic synthetic VLM adapter strictly for CI pipeline testing and test fixtures.

    Produces reproducible, image-hash-conditioned responses for offline validation.
    Marked with execution_tier='synthetic_ci_fixture'; manifests produced by this adapter
    cannot be promoted into certified scientific baseline results.
    """

    execution_tier = "synthetic_ci_fixture"
    scientific_validity = "non_scientific_test_fixture"

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
            reason="Mock adapter is fully operational offline as a synthetic CI fixture.",
            hardware_info={"mode": "synthetic_ci_fixture", "device": "cpu", "promotable": False},
        )

    def predict(
        self,
        image_bytes: bytes,
        prompt: str,
        system_prompt: str,
        shot_mode: str,
        rung: str,
        item_id: str,
        demonstrations_meta: dict[str, Any] | None = None,
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

        # Deterministic conditioned synthetic output (CI fixture only)
        img_hash = hashlib.sha256(image_bytes).hexdigest()
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        combined_seed = int(img_hash[:8], 16) ^ int(prompt_hash[:8], 16)

        if rung == "identify":
            choices = ["Hieratic", "Hieroglyphic", "Demotic", "Coptic"]
            ans = choices[combined_seed % len(choices)]
            raw = f"SCRIPT: {ans.lower()}"
            cleaned = ans
        elif rung == "signs":
            gardiner_codes = ["A1", "G43", "M17", "O34", "D21", "N35", "V31", "X1"]
            ans = gardiner_codes[combined_seed % len(gardiner_codes)]
            raw = f"SIGNS: {ans}"
            cleaned = ans
        elif rung == "transliterate":
            translit_samples = [
                "jrj.n=f m mnw=f",
                "ḏd-mdw jn Wsjr",
                "ḥꜣ.t-ꜥ m sšr",
                "jw=f hr sḏm r-gs nswt",
            ]
            ans = translit_samples[combined_seed % len(translit_samples)]
            raw = f"TRANSLITERATION: {ans}"
            cleaned = ans
        elif rung == "translate":
            translations = [
                "He made it as his monument.",
                "Words spoken by Osiris.",
                "Beginning of the good remedy.",
                "He was listening beside the King.",
            ]
            ans = translations[combined_seed % len(translations)]
            raw = f"TRANSLATION: {ans}"
            cleaned = ans
        else:
            raw = f"Processed {item_id}"
            cleaned = raw

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0 + self.simulated_latency_ms
        prompt_tokens = len(prompt.split()) + 256
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

    Executes genuine local image-conditioned forward passes when local weights and CUDA hardware exist.
    Fails closed when prerequisites are missing, reporting the barrier without fabricating claims.
    Few-shot inference strictly requires verified demonstration image files on disk.
    """

    execution_tier = "live_local_open_weight"
    scientific_validity = "candidate_baseline"

    def __init__(
        self,
        model_config: dict[str, Any],
        weights_dir: Path | None = None,
    ) -> None:
        super().__init__(model_config)
        self.weights_dir = Path(weights_dir) if weights_dir else None
        self._torch_available = importlib.util.find_spec("torch") is not None
        self._transformers_available = importlib.util.find_spec("transformers") is not None
        self._model = None
        self._processor = None

    def check_availability(self) -> AvailabilityStatus:
        if not self._torch_available:
            return AvailabilityStatus(
                available=False,
                reason="PyTorch (torch) is not installed in the local environment.",
                hardware_info={"torch_installed": False},
            )
        if not self._transformers_available:
            return AvailabilityStatus(
                available=False,
                reason="Hugging Face Transformers is not installed in the local environment.",
                hardware_info={"transformers_installed": False},
            )

        import torch
        cuda_ok = torch.cuda.is_available()
        device_count = torch.cuda.device_count() if cuda_ok else 0
        device_name = torch.cuda.get_device_name(0) if cuda_ok else None

        if self.model_config.get("requires_cuda", True) and not cuda_ok:
            return AvailabilityStatus(
                available=False,
                reason=f"Model '{self.model_key}' requires NVIDIA CUDA GPU acceleration, but no CUDA device is present.",
                hardware_info={
                    "cuda_available": False,
                    "device_count": 0,
                    "device_name": None,
                },
            )

        # Check local weights availability
        model_id = self.model_config["provider_model_id"]
        weights_path = self.weights_dir
        if not weights_path:
            # Check default local cache or relative path
            candidate_path = Path.home() / ".cache" / "huggingface" / "hub" / f"models--{model_id.replace('/', '--')}"
            if candidate_path.is_dir():
                weights_path = candidate_path

        if not weights_path or not weights_path.exists():
            return AvailabilityStatus(
                available=False,
                reason=(
                    f"Model weights for '{model_id}' are not found locally on disk. "
                    "Pre-downloaded weights directory is required for offline execution."
                ),
                hardware_info={
                    "cuda_available": cuda_ok,
                    "device_name": device_name,
                    "weights_found": False,
                },
            )

        return AvailabilityStatus(
            available=True,
            reason="Local runtime meets GPU acceleration and offline weights prerequisites.",
            hardware_info={
                "cuda_available": cuda_ok,
                "device_count": device_count,
                "device_name": device_name,
                "weights_path": str(weights_path),
            },
        )

    def _load_model_if_needed(self) -> None:
        if self._model is not None and self._processor is not None:
            return

        import torch
        from transformers import AutoProcessor, AutoModelForVision2Seq

        model_path = str(self.weights_dir) if self.weights_dir else self.model_config["provider_model_id"]
        self._processor = AutoProcessor.from_pretrained(model_path, local_files_only=True)
        self._model = AutoModelForVision2Seq.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else "cpu",
            local_files_only=True,
        )
        self._model.eval()

    def predict(
        self,
        image_bytes: bytes,
        prompt: str,
        system_prompt: str,
        shot_mode: str,
        rung: str,
        item_id: str,
        demonstrations_meta: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> VLMResponse:
        self.validate_image_input(image_bytes)

        # Enforce strict few-shot clearance: live inference cannot use synthetic fixtures or unverified templates
        if shot_mode == "few_shot":
            raise LiveFewShotBlockedError(
                "Live few-shot evaluation on open-weight backbones is unconditionally blocked. "
                "Authentic multi-image vision/chat template integration and verified on-disk exemplar "
                "images with audited rights clearance are not yet available. "
                "Synthetic fixture banks cannot be used for live open-weight evaluation."
            )

        # Check local hardware/weights availability
        status = self.check_availability()
        if not status.available:
            return VLMResponse(
                status="failed",
                raw_output=None,
                cleaned_prediction=None,
                error_message=f"Inference blocked by hardware/weights barrier: {status.reason}",
                latency_ms=None,
                token_usage=None,
            )

        # Execute genuine model inference
        try:
            start_time = time.perf_counter()
            self._load_model_if_needed()

            from PIL import Image
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            full_prompt = f"{system_prompt}\n\n{prompt}"
            inputs = self._processor(
                images=pil_image,
                text=full_prompt,
                return_tensors="pt",
            )
            if hasattr(self._model, "device"):
                inputs = {k: v.to(self._model.device) for k, v in inputs.items()}

            import torch
            with torch.no_grad():
                generated_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=self.model_config.get("max_new_tokens", 256),
                    do_sample=False,
                    temperature=0.0,
                )

            # Strip input tokens from output
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs["input_ids"], generated_ids)
            ]
            raw_output = self._processor.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0].strip()

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return VLMResponse(
                status="success",
                raw_output=raw_output,
                cleaned_prediction=raw_output,
                error_message=None,
                latency_ms=round(elapsed_ms, 2),
                token_usage={
                    "prompt_tokens": int(inputs["input_ids"].shape[-1]),
                    "completion_tokens": int(len(generated_ids_trimmed[0])),
                    "total_tokens": int(inputs["input_ids"].shape[-1] + len(generated_ids_trimmed[0])),
                },
            )

        except Exception as exc:
            return VLMResponse(
                status="failed",
                raw_output=None,
                cleaned_prediction=None,
                error_message=f"Live inference execution failure: {type(exc).__name__}: {exc}",
                latency_ms=None,
                token_usage=None,
            )


def get_adapter(model_config: dict[str, Any], **kwargs: Any) -> BaseVLMAdapter:
    """Factory creating an appropriate adapter based on model configuration."""
    model_type = model_config.get("model_type")
    if model_type == "mock":
        return MockVLMAdapter(model_config, **kwargs)
    elif model_type == "open_weight":
        return OpenWeightVLMAdapter(model_config, **kwargs)
    else:
        raise VLMAdapterError(f"Unsupported model type '{model_type}' for model '{model_config.get('key')}'")
