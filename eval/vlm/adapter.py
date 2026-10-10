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
import importlib.util
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



def validate_revision_pinning(revision: str | None) -> None:
    """Validate that an open-weight model revision is an explicit, full 40-character commit SHA."""
    if not revision:
        raise VLMAdapterError("Open-weight model must specify an explicit pinned revision.")
    clean = str(revision).strip()
    if len(clean) != 40 or not all(c in "0123456789abcdefABCDEF" for c in clean):
        raise VLMAdapterError(
            f"Open-weight model revision '{revision}' is not a full 40-character commit SHA git hash. "
            "Short or branch-based revisions are forbidden for scientific reproducibility."
        )


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
        is_png = image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        is_jpeg = image_bytes.startswith(b"\xff\xd8\xff")
        is_synth = image_bytes.startswith(b"synthetic_")

        if not (is_png or is_jpeg or is_synth):
            raise ImageConditioningError(
                f"Corrupted or invalid image input for model {self.model_key}: "
                "bytes do not match PNG or JPEG signature."
            )

        if is_synth:
            # Never allow a fabricated placeholder to enter a real-weight
            # inference run. Synthetic markers are supported solely by
            # explicitly injected CI test doubles, which are non-scientific.
            if self.scientific_validity != "non_scientific_test_fixture":
                raise ImageConditioningError(
                    "Synthetic image marker is prohibited for real open-weight inference."
                )
            if Image is not None:
                return Image.new("RGB", (min_dim, min_dim), color=(128, 128, 128))
            return None

        if Image is None:
            # Fallback binary magic byte and dimension checks when PIL is absent
            if is_png and len(image_bytes) >= 24:
                import struct
                w, h = struct.unpack(">II", image_bytes[16:24])
                if w < min_dim or h < min_dim:
                    raise ImageConditioningError(
                        f"Image dimensions ({w}x{h}) smaller than minimum allowed {min_dim}px."
                    )
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
    # Specific Hugging Face model class used to load this family (never generic AutoModelForVision2Seq)
    loader_class_name: str | None = None
    # Specific Hugging Face processor class or AutoProcessor
    processor_class_name: str = "AutoProcessor"
    # Minimum required libraries
    min_transformers_version: str = "4.45.0"
    min_torch_version: str = "2.4.0"
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
        if self.model_type == "open_weight":
            validate_revision_pinning(self.model_config.get("revision"))
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

    def get_environment_provisioning_spec(self) -> dict[str, Any]:
        """Return reproducible environment provisioning specification for this model."""
        from eval.vlm.smoke import get_reproducible_provisioning_spec
        return get_reproducible_provisioning_spec(self.model_config)

    def check_weights_on_disk(self) -> bool:
        """Check whether local snapshot directory exists and contains valid config and weights."""
        model_id = self.model_config.get("provider_model_id", "")
        target_path = self.weights_dir
        if not target_path:
            candidate_path = Path.home() / ".cache" / "huggingface" / "hub" / f"models--{model_id.replace('/', '--')}"
            if candidate_path.is_dir():
                target_path = candidate_path

        if not target_path or not target_path.is_dir():
            return False

        has_cfg = (target_path / "config.json").is_file() or any(target_path.glob("snapshots/*/config.json"))
        has_wt = (
            any(target_path.glob("*.safetensors"))
            or any(target_path.glob("*.bin"))
            or (target_path / "model.safetensors.index.json").is_file()
            or (target_path / "pytorch_model.bin.index.json").is_file()
            or any(target_path.glob("snapshots/*/*.safetensors"))
            or any(target_path.glob("snapshots/*/*.bin"))
            or any(target_path.glob("snapshots/*/model.safetensors.index.json"))
        )
        return bool(has_cfg and has_wt)

    def get_runtime_metadata(self) -> dict[str, Any]:
        """Return structured runtime metadata for auditing without leaking sensitive paths."""
        weights_status = "unspecified"
        if self._processor_override is not None and self._model_override is not None:
            weights_status = "test_double_injected"
        elif self.weights_dir is not None:
            weights_status = "custom_weights_dir_provided"
        else:
            weights_status = "hub_cache_or_default"

        meta: dict[str, Any] = {
            "model_key": self.model_key,
            "provider_model_id": self.model_config.get("provider_model_id"),
            "revision": self.model_config.get("revision"),
            "loader_class_name": self.loader_class_name,
            "processor_class_name": self.processor_class_name,
            "min_transformers_version": self.min_transformers_version,
            "min_torch_version": self.min_torch_version,
            "runtime_verification": self.runtime_verification,
            "execution_tier": self.execution_tier,
            "scientific_validity": self.scientific_validity,
            "weights_status": weights_status,
            "weights_found": self.check_weights_on_disk(),
        }

        if self._torch_available:
            try:
                import torch
                meta["torch_version"] = torch.__version__
                meta["cuda_available"] = torch.cuda.is_available()
                if torch.cuda.is_available():
                    meta["cuda_device_count"] = torch.cuda.device_count()
                    meta["cuda_device_name"] = torch.cuda.get_device_name(0)
            except Exception:
                pass

        if self._transformers_available:
            try:
                import transformers
                meta["transformers_version"] = transformers.__version__
            except Exception:
                pass

        return meta

    def check_availability(self) -> AvailabilityStatus:
        base_hw_info = self.get_runtime_metadata()

        if self._processor_override is not None and self._model_override is not None:
            info = dict(base_hw_info)
            info.update({"mode": "injected_test_interface", "promotable": False})
            return AvailabilityStatus(
                available=True,
                reason="Adapter configured with injected processor/model test doubles (unit-test harness; not real inference).",
                hardware_info=info,
            )

        if self.loader_class_name is None:
            info = dict(base_hw_info)
            info["loader_class"] = None
            return AvailabilityStatus(
                available=False,
                reason=(
                    f"Unsupported architecture path for model '{self.model_key}': no verified Hugging Face loader is "
                    f"registered for this family ({type(self).__name__}). Runtime status: {self.runtime_verification}."
                ),
                hardware_info=info,
            )

        model_id = self.model_config["provider_model_id"]
        if not self.check_weights_on_disk():
            info = dict(base_hw_info)
            info["weights_found"] = False
            return AvailabilityStatus(
                available=False,
                reason=(
                    f"Model weights for '{model_id}' are not found locally on disk or snapshot directory is incomplete. "
                    "Pre-downloaded weights directory with config.json and weights files is required for offline execution."
                ),
                hardware_info=info,
            )

        if not self._torch_available:
            info = dict(base_hw_info)
            info["torch_installed"] = False
            return AvailabilityStatus(
                available=False,
                reason="PyTorch (torch) is not installed in the local environment.",
                hardware_info=info,
            )
        if not self._transformers_available:
            info = dict(base_hw_info)
            info["transformers_installed"] = False
            return AvailabilityStatus(
                available=False,
                reason="Hugging Face Transformers is not installed in the local environment.",
                hardware_info=info,
            )

        import torch
        import transformers

        # Check library versions against minimums
        current_tf_ver = getattr(transformers, "__version__", "0.0.0")
        current_torch_ver = getattr(torch, "__version__", "0.0.0")

        def _ver_tuple(v: str) -> tuple[int, ...]:
            try:
                clean = v.split("+")[0].split(".dev")[0]
                return tuple(int(x) for x in clean.split(".") if x.isdigit())
            except Exception:
                return (0, 0, 0)

        if _ver_tuple(current_tf_ver) < _ver_tuple(self.min_transformers_version):
            info = dict(base_hw_info)
            info.update({"current_transformers_version": current_tf_ver, "required_min": self.min_transformers_version})
            return AvailabilityStatus(
                available=False,
                reason=(
                    f"Hugging Face transformers version {current_tf_ver} is older than required "
                    f"{self.min_transformers_version} for loader {self.loader_class_name}."
                ),
                hardware_info=info,
            )

        # Check architecture loader class exists in transformers
        if not hasattr(transformers, self.loader_class_name):
            info = dict(base_hw_info)
            info.update({"missing_loader_class": self.loader_class_name})
            return AvailabilityStatus(
                available=False,
                reason=(
                    f"Loader class '{self.loader_class_name}' is not present in installed transformers {current_tf_ver}."
                ),
                hardware_info=info,
            )

        cuda_ok = torch.cuda.is_available()
        device_count = torch.cuda.device_count() if cuda_ok else 0
        device_name = torch.cuda.get_device_name(0) if cuda_ok else None

        requires_cuda = self.model_config.get("requires_cuda", True)
        min_vram_gb = 16.0 if "7b" in self.model_key else 24.0
        if requires_cuda and not cuda_ok:
            info = dict(base_hw_info)
            info.update({
                "cuda_available": False,
                "device_count": 0,
                "device_name": None,
            })
            return AvailabilityStatus(
                available=False,
                reason=f"Model '{self.model_key}' requires NVIDIA CUDA GPU acceleration (>= {min_vram_gb} GB VRAM), but no CUDA device is present.",
                hardware_info=info,
            )

        info = dict(base_hw_info)
        info.update({
            "cuda_available": cuda_ok,
            "device_count": device_count,
            "device_name": device_name,
            "weights_found": True,
        })
        reason = (
            "Local runtime meets GPU acceleration and offline weights prerequisites."
            if cuda_ok
            else "Local runtime meets CPU execution and offline weights prerequisites."
        )
        return AvailabilityStatus(
            available=True,
            reason=reason,
            hardware_info=info,
        )

    def _load_model_if_needed(self) -> None:
        if self._model is not None and self._processor is not None:
            return

        if self.loader_class_name is None:
            raise VLMAdapterError(
                f"Cannot load model '{self.model_key}': loader_class_name is None for {type(self).__name__}."
            )

        import torch
        import transformers

        loader_cls = getattr(transformers, self.loader_class_name, None)
        if loader_cls is None:
            raise VLMAdapterError(
                f"Architecture loader class '{self.loader_class_name}' is not found in transformers library."
            )

        processor_cls = getattr(transformers, self.processor_class_name, getattr(transformers, "AutoProcessor", None))
        if processor_cls is None:
            raise VLMAdapterError(
                f"Processor class '{self.processor_class_name}' not found in transformers library."
            )

        model_path = str(self.weights_dir) if self.weights_dir else self.model_config["provider_model_id"]
        revision = self.model_config.get("revision")

        load_kwargs: dict[str, Any] = {"local_files_only": True}
        if revision:
            load_kwargs["revision"] = revision

        self._processor = processor_cls.from_pretrained(model_path, **load_kwargs)
        self._model = loader_cls.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else "cpu",
            **load_kwargs,
        )
        self._model.eval()

    def format_multimodal_inputs(
        self,
        system_prompt: str,
        prompt: str,
        pil_image: Any,
    ) -> dict[str, Any]:
        """Format inputs appropriately for the underlying processor, strictly ensuring image conditioning.

        Base class implementation requires explicit chat template or processor conditioning;
        never falls back silently to unconditioned text-only prompts.
        """
        if hasattr(self._processor, "apply_chat_template"):
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
            except Exception as exc:
                raise ImageConditioningError(
                    f"Chat template application failed for {self.model_key}: {exc}. "
                    "Text-only fallback is prohibited by multimodal conditioning protocol."
                ) from exc

        return self._processor(images=pil_image, text=f"{system_prompt}\n\n{prompt}", return_tensors="pt")

    def format_few_shot_multimodal_inputs(
        self,
        system_prompt: str,
        prompt: str,
        pil_image: Any,
        demonstration_items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Prospective multi-image formatting helper for future cleared few-shot evaluation.

        Unconditionally raises LiveFewShotBlockedError in live execution because verified
        multi-image vision templates and audited exemplar pixels are not yet certified.
        """
        raise LiveFewShotBlockedError(
            f"Multi-image few-shot formatting for '{self.model_key}' is prospective and blocked. "
            "Authentic multi-image vision templates and audited rights-cleared exemplar image assets "
            "are not certified on disk."
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

            # Ensure image tensors exist in inputs: check pixel_values or image feature tensors
            # A processor attribute cannot certify visual conditioning. Require a
            # concrete nonempty image payload in the actual generated model inputs.
            visual_values = [inputs.get(name) for name in ("pixel_values", "images")]
            def _has_visual_payload(value: Any) -> bool:
                if value is None:
                    return False
                if hasattr(value, "numel"):
                    return bool(value.numel() > 0)
                if hasattr(value, "shape"):
                    return bool(getattr(value, "size", 0) or len(value))
                if isinstance(value, (list, tuple)):
                    return bool(value) and any(_has_visual_payload(v) for v in value)
                # Synthetic test doubles use nested numeric Python lists rather
                # than torch tensors. Permit these ONLY in an explicitly marked
                # non-scientific fixture; live model inputs must supply actual
                # tensor-like visual features with a nonzero element count.
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    return self.scientific_validity == "non_scientific_test_fixture"
                return False
            has_visual_features = any(_has_visual_payload(value) for value in visual_values)
            if not has_visual_features:
                raise ImageConditioningError(
                    f"Processor output for {self.model_key} lacks visual features (pixel_values). "
                    "Multimodal image conditioning could not be established."
                )

            # Place inputs on model device
            target_device = getattr(self._model, "device", None)
            if target_device is not None:
                inputs = {
                    k: (v.to(target_device) if hasattr(v, "to") else v)
                    for k, v in inputs.items()
                }

            # Deterministic greedy forward decoding
            max_new_tokens = self.model_config.get("max_new_tokens", 256)
            gen_kwargs: dict[str, Any] = {
                "max_new_tokens": max_new_tokens,
                "do_sample": False,
                "temperature": 0.0,
            }
            if "eos_token_id" in self.model_config:
                gen_kwargs["eos_token_id"] = self.model_config["eos_token_id"]
            elif hasattr(self, "get_eos_token_ids"):
                gen_kwargs["eos_token_id"] = self.get_eos_token_ids()

            if "stop_sequences" in self.model_config:
                gen_kwargs["stop_strings"] = self.model_config["stop_sequences"]

            try:
                generated_ids = self._model.generate(**inputs, **gen_kwargs)
            except TypeError as te:
                if "stop_strings" in gen_kwargs and "stop_strings" in str(te):
                    gen_kwargs_no_stop = dict(gen_kwargs)
                    del gen_kwargs_no_stop["stop_strings"]
                    generated_ids = self._model.generate(**inputs, **gen_kwargs_no_stop)
                else:
                    raise

            # Extract completion tokens, stripping prompt input IDs
            in_ids = inputs.get("input_ids")
            if in_ids is not None and hasattr(generated_ids, "__getitem__"):
                generated_ids_trimmed = []
                for i, out_ids in enumerate(generated_ids):
                    if len(in_ids) > i:
                        prompt_len = len(in_ids[i])
                        if len(out_ids) >= prompt_len:
                            generated_ids_trimmed.append(out_ids[prompt_len:])
                        else:
                            generated_ids_trimmed.append(out_ids)
                    else:
                        generated_ids_trimmed.append(out_ids)
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
                raw_output = str(generated_ids_trimmed).strip()

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            in_len = int(in_ids.shape[-1]) if (in_ids is not None and hasattr(in_ids, "shape")) else 256
            out_len = int(len(raw_output.split()))

            if not raw_output:
                return VLMResponse(
                    status="failed",
                    raw_output=None,
                    cleaned_prediction=None,
                    error_message=f"Model '{self.model_key}' returned empty or whitespace-only prediction.",
                    latency_ms=round(elapsed_ms, 2),
                    token_usage={
                        "prompt_tokens": in_len,
                        "completion_tokens": 0,
                        "total_tokens": in_len,
                    },
                )

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
    processor_class_name = "AutoProcessor"
    min_transformers_version = "4.49.0"
    min_torch_version = "2.4.0"
    runtime_verification = "untested_blocked_no_weights_gpu_runtime_smoke"

    def format_multimodal_inputs(
        self,
        system_prompt: str,
        prompt: str,
        pil_image: Any,
    ) -> dict[str, Any]:
        """Format inputs for Qwen2.5-VL using its required chat template and vision processor call."""
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
                return self._processor(images=[pil_image], text=formatted, return_tensors="pt")
            except Exception as exc:
                raise ImageConditioningError(
                    f"Chat template application failed for Qwen2.5-VL: {exc}. Multimodal conditioning cannot proceed."
                ) from exc

        raise ImageConditioningError(
            f"Processor for '{self.model_key}' lacks apply_chat_template. Cannot establish multimodal chat conditioning."
        )


class PixtralVLMAdapter(OpenWeightVLMAdapter):
    """Specialized adapter for Mistral Pixtral 12B architecture."""

    loader_class_name = "LlavaForConditionalGeneration"
    processor_class_name = "AutoProcessor"
    min_transformers_version = "4.45.0"
    min_torch_version = "2.4.0"
    runtime_verification = "untested_blocked_no_weights_gpu_runtime_smoke"

    def format_multimodal_inputs(
        self,
        system_prompt: str,
        prompt: str,
        pil_image: Any,
    ) -> dict[str, Any]:
        """Format inputs for Pixtral 12B using its Llava-compatible multimodal message structure."""
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
                return self._processor(images=[pil_image], text=formatted, return_tensors="pt")
            except Exception as exc:
                raise ImageConditioningError(
                    f"Chat template application failed for Pixtral: {exc}. Multimodal conditioning cannot proceed."
                ) from exc

        raise ImageConditioningError(
            f"Processor for '{self.model_key}' lacks apply_chat_template. Cannot establish multimodal chat conditioning."
        )


class Llama3_2_VisionAdapter(OpenWeightVLMAdapter):
    """Specialized adapter for Meta Llama 3.2 11B Vision architecture."""

    loader_class_name = "MllamaForConditionalGeneration"
    processor_class_name = "AutoProcessor"
    min_transformers_version = "4.45.0"
    min_torch_version = "2.4.0"
    runtime_verification = "untested_blocked_no_weights_gpu_runtime_smoke"

    def format_multimodal_inputs(
        self,
        system_prompt: str,
        prompt: str,
        pil_image: Any,
    ) -> dict[str, Any]:
        """Format inputs for Llama 3.2 Vision using official chat template structure."""
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
                    f"Chat template application failed for Llama 3.2 Vision: {exc}. Multimodal conditioning cannot proceed."
                ) from exc

        raise ImageConditioningError(
            f"Processor for '{self.model_key}' lacks apply_chat_template. "
            "Cannot establish trusted Llama Vision image conditioning."
        )


class SmolVLMAdapter(OpenWeightVLMAdapter):
    """Specialized adapter for HuggingFace SmolVLM lightweight vision-language models."""

    loader_class_name = "Idefics3ForConditionalGeneration"
    processor_class_name = "AutoProcessor"
    min_transformers_version = "4.46.0"
    min_torch_version = "2.4.0"
    runtime_verification = "cpu_lightweight_open_weight_verified"

    def get_eos_token_ids(self) -> list[int]:
        """Official Idefics3 / SmolVLM end-of-utterance and text EOS token IDs."""
        return [2, 49279]

    def format_multimodal_inputs(
        self,
        system_prompt: str,
        prompt: str,
        pil_image: Any,
    ) -> dict[str, Any]:
        """Format inputs for SmolVLM using official Idefics3 chat template structure."""
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({
                "role": "system",
                "content": [{"type": "text", "text": system_prompt}],
            })
        messages.append({
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": prompt},
            ],
        })
        if hasattr(self._processor, "apply_chat_template"):
            try:
                formatted = self._processor.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True,
                )
                if not isinstance(formatted, str) or not formatted.strip():
                    raise ImageConditioningError(
                        "SmolVLM chat template did not return a nonempty text prompt."
                    )
                return self._processor(images=[pil_image], text=formatted, return_tensors="pt")
            except Exception as exc:
                raise ImageConditioningError(
                    f"Chat template application failed for SmolVLM: {exc}. Multimodal conditioning cannot proceed."
                ) from exc

        raise ImageConditioningError(
            f"Processor for '{self.model_key}' lacks apply_chat_template. "
            "Cannot establish trusted SmolVLM image conditioning."
        )


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
        elif "smolvlm" in key:
            return SmolVLMAdapter(model_config, **kwargs)
        return OpenWeightVLMAdapter(model_config, **kwargs)
    else:
        raise VLMAdapterError(f"Unsupported model type '{model_type}' for model '{model_config.get('key')}'")
