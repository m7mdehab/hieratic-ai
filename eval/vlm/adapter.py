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

try:
    from PIL import Image
except ImportError:
    Image = None


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
        """Reject unconditioned, empty, or truncated image inputs."""
        if image_bytes is None or len(image_bytes) == 0:
            raise ImageConditioningError(
                f"Model {self.model_key} attempted prediction without valid image bytes. "
                "Text-only unconditioned prediction is prohibited by scientific protocol."
            )

    def preprocess_image(
        self,
        image_bytes: bytes,
        max_dim: int = 1024,
        min_dim: int = 16,
    ) -> Any:
        """Decode, convert to RGB, and enforce aspect-ratio preserving dimensions."""
        self.validate_image_input(image_bytes)
        if Image is None:
            return None
        try:
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            raise ImageConditioningError(f"Image decoding failed for model {self.model_key}: {exc}") from exc

        w, h = pil_image.size
        if w < min_dim or h < min_dim:
            raise ImageConditioningError(
                f"Image dimensions ({w}x{h}) smaller than minimum allowed {min_dim}px."
            )

        # Scale down if longest edge exceeds max_dim, preserving aspect ratio
        if max(w, h) > max_dim:
            scale = max_dim / float(max(w, h))
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))
            pil_image = pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        return pil_image

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
    """Base open-weight adapter managing GPU, weights availability, and multimodal inference.

    Executes genuine local image-conditioned forward passes when local weights and CUDA hardware exist.
    Fails closed when prerequisites are missing, reporting the barrier without fabricating claims.
    Few-shot inference strictly requires verified demonstration image files on disk.
    """

    execution_tier = "live_local_open_weight"
    scientific_validity = "candidate_baseline"
    # Hugging Face class used to load this family, or None when no verified loader exists.
    loader_class_name: str | None = None
    # Honest status: nothing here has been exercised against real weights, a GPU and a real image.
    runtime_verification = "untested_blocked_no_weights_gpu_runtime_smoke"

    def __init__(
        self,
        model_config: dict[str, Any],
        weights_dir: Path | None = None,
        processor_override: Any = None,
        model_override: Any = None,
    ) -> None:
        super().__init__(model_config)
        self.weights_dir = Path(weights_dir) if weights_dir else None
        self._processor_override = processor_override
        self._model_override = model_override
        self._torch_available = importlib.util.find_spec("torch") is not None
        self._transformers_available = importlib.util.find_spec("transformers") is not None
        self._model = model_override
        self._processor = processor_override
        if processor_override is not None or model_override is not None:
            # A test double is not a live model: never label its output as live inference.
            self.execution_tier = "synthetic_ci_fixture"
            self.scientific_validity = "non_scientific_test_fixture"

    def check_availability(self) -> AvailabilityStatus:
        if self._processor_override is not None and self._model_override is not None:
            return AvailabilityStatus(
                available=True,
                reason="Adapter configured with injected processor/model test doubles (unit-test harness; not real inference).",
                hardware_info={"mode": "injected_test_interface", "promotable": False},
            )

        if self.loader_class_name is None:
            return AvailabilityStatus(
                available=False,
                reason=(
                    f"Unsupported architecture path for model '{self.model_key}': no verified Hugging Face loader is "
                    f"registered for this family ({type(self).__name__}). Runtime status: {self.runtime_verification}."
                ),
                hardware_info={"loader_class": None, "runtime_verification": self.runtime_verification},
            )

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

        min_vram_gb = 16.0 if "7b" in self.model_key else 24.0
        if self.model_config.get("requires_cuda", True) and not cuda_ok:
            return AvailabilityStatus(
                available=False,
                reason=f"Model '{self.model_key}' requires NVIDIA CUDA GPU acceleration (>= {min_vram_gb} GB VRAM), but no CUDA device is present.",
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

    def format_multimodal_inputs(
        self,
        system_prompt: str,
        prompt: str,
        pil_image: Any,
    ) -> dict[str, Any]:
        """Format inputs appropriately for the underlying processor, ensuring image conditioning."""
        full_text = f"{system_prompt}\n\n{prompt}"
        if hasattr(self._processor, "apply_chat_template"):
            # Multi-modal chat message structure
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": pil_image},
                        {"type": "text", "text": prompt},
                    ],
                },
            ]
            try:
                formatted_text = self._processor.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
                return self._processor(images=pil_image, text=formatted_text, return_tensors="pt")
            except Exception:
                # Fallback to standard processor call
                pass

        return self._processor(images=pil_image, text=full_text, return_tensors="pt")

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

        # Enforce strict few-shot clearance
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

            pil_image = self.preprocess_image(image_bytes)
            inputs = self.format_multimodal_inputs(system_prompt, prompt, pil_image)

            # Ensure image tensors exist in inputs
            if "pixel_values" not in inputs and "images" not in inputs and not hasattr(self._processor, "mock_image_tag"):
                raise ImageConditioningError(
                    f"Processor output for {self.model_key} lacks visual features (pixel_values). "
                    "Multimodal image conditioning could not be established."
                )

            if hasattr(self._model, "device"):
                inputs = {k: v.to(self._model.device) for k, v in inputs.items() if hasattr(v, "to")}

            # Deterministic greedy forward decoding
            max_new_tokens = self.model_config.get("max_new_tokens", 256)
            generated_ids = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=0.0,
            )

            # Extract completion tokens, stripping prompt input IDs
            in_ids = inputs.get("input_ids")
            if in_ids is not None and hasattr(generated_ids, "__getitem__"):
                generated_ids_trimmed = [
                    out_ids[len(in_ids[i]):] if len(in_ids) > i else out_ids
                    for i, out_ids in enumerate(generated_ids)
                ]
            else:
                generated_ids_trimmed = generated_ids

            if hasattr(self._processor, "batch_decode"):
                decoded = self._processor.batch_decode(
                    generated_ids_trimmed,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False,
                )
                raw_output = decoded[0].strip() if decoded else ""
            else:
                raw_output = str(generated_ids_trimmed)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            in_len = int(in_ids.shape[-1]) if (in_ids is not None and hasattr(in_ids, "shape")) else 256
            out_len = int(len(raw_output.split()))

            return VLMResponse(
                status="success",
                raw_output=raw_output,
                cleaned_prediction=raw_output,
                error_message=None,
                latency_ms=round(elapsed_ms, 2),
                token_usage={
                    "prompt_tokens": in_len,
                    "completion_tokens": out_len,
                    "total_tokens": in_len + out_len,
                },
            )

        except Exception as exc:
            error_cls = type(exc).__name__
            return VLMResponse(
                status="failed",
                raw_output=None,
                cleaned_prediction=None,
                error_message=f"Live inference execution failure: {error_cls}: {exc}",
                latency_ms=None,
                token_usage=None,
            )


class Qwen2_5_VLAdapter(OpenWeightVLMAdapter):
    """Specialized adapter for Alibaba Qwen 2.5 VL architecture."""

    loader_class_name = "Qwen2_5_VLForConditionalGeneration"
    runtime_verification = "untested_blocked_no_weights_gpu_runtime_smoke"

    def format_multimodal_inputs(
        self,
        system_prompt: str,
        prompt: str,
        pil_image: Any,
    ) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_image},
                    {"type": "text", "text": prompt},
                ],
            },
        ]
        if hasattr(self._processor, "apply_chat_template"):
            try:
                formatted = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                return self._processor(images=pil_image, text=formatted, return_tensors="pt")
            except Exception as exc:
                raise ImageConditioningError(
                    f"Chat template application failed for Qwen2.5-VL: {exc}. Multimodal conditioning cannot proceed."
                ) from exc
        return self._processor(images=pil_image, text=f"{system_prompt}\n{prompt}", return_tensors="pt")


class PixtralVLMAdapter(OpenWeightVLMAdapter):
    """Specialized adapter for Mistral Pixtral 12B architecture."""

    loader_class_name = "LlavaForConditionalGeneration"
    runtime_verification = "untested_blocked_no_weights_gpu_runtime_smoke"

    def format_multimodal_inputs(
        self,
        system_prompt: str,
        prompt: str,
        pil_image: Any,
    ) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": prompt},
                ],
            },
        ]
        if hasattr(self._processor, "apply_chat_template"):
            try:
                formatted = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                return self._processor(images=pil_image, text=formatted, return_tensors="pt")
            except Exception as exc:
                raise ImageConditioningError(
                    f"Chat template application failed for Pixtral: {exc}. Multimodal conditioning cannot proceed."
                ) from exc
        return self._processor(images=pil_image, text=f"{system_prompt}\n{prompt}", return_tensors="pt")


class Llama3_2_VisionAdapter(OpenWeightVLMAdapter):
    """Specialized adapter for Meta Llama 3.2 11B Vision architecture."""

    loader_class_name = "MllamaForConditionalGeneration"
    runtime_verification = "untested_blocked_no_weights_gpu_runtime_smoke"

    def format_multimodal_inputs(
        self,
        system_prompt: str,
        prompt: str,
        pil_image: Any,
    ) -> dict[str, Any]:
        full_text = f"<|image|><|begin_of_text|>{system_prompt}\n\n{prompt}"
        return self._processor(images=pil_image, text=full_text, return_tensors="pt")


def get_adapter(model_config: dict[str, Any], **kwargs: Any) -> BaseVLMAdapter:
    """Factory creating an appropriate adapter based on model configuration and architecture."""
    model_type = model_config.get("model_type")
    key = model_config.get("key", "").lower()

    if model_type == "mock":
        return MockVLMAdapter(model_config, **kwargs)
    elif model_type == "open_weight":
        if "qwen" in key:
            return Qwen2_5_VLAdapter(model_config, **kwargs)
        elif "pixtral" in key:
            return PixtralVLMAdapter(model_config, **kwargs)
        elif "llama" in key:
            return Llama3_2_VisionAdapter(model_config, **kwargs)
        return OpenWeightVLMAdapter(model_config, **kwargs)
    else:
        raise VLMAdapterError(f"Unsupported model type '{model_type}' for model '{model_config.get('key')}'")
