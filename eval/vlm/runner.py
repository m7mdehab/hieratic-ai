"""Evaluation runner for reproducible zero-shot and few-shot VLM benchmarking.

Orchestrates prompt formatting, quarantined demonstration assembly, image verification,
and complete attempt preservation without sample dropouts.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any

from eval.vlm.adapter import BaseVLMAdapter, ImageConditioningError, VLMResponse


class RunnerError(Exception):
    """Raised when evaluation runner encounters a fatal pipeline failure."""
    pass


class VLMRunner:
    """Executes evaluation across benchmark items and builds immutable run manifests."""

    def __init__(
        self,
        suite_config: dict[str, Any],
        demonstration_bank: dict[str, Any] | None,
        adapter: BaseVLMAdapter,
        suite_path: Path | None = None,
        demos_path: Path | None = None,
    ) -> None:
        self.suite = suite_config
        self.demos = demonstration_bank
        self.adapter = adapter
        self.suite_path = suite_path
        self.demos_path = demos_path

        # Compute suite SHA-256
        if suite_path and suite_path.is_file():
            self.suite_sha256 = hashlib.sha256(suite_path.read_bytes()).hexdigest()
        else:
            self.suite_sha256 = hashlib.sha256(json.dumps(suite_config, sort_keys=True).encode("utf-8")).hexdigest()

        # Compute demonstrations SHA-256
        if self.demos:
            if demos_path and demos_path.is_file():
                self.demos_sha256 = hashlib.sha256(demos_path.read_bytes()).hexdigest()
            else:
                self.demos_sha256 = hashlib.sha256(json.dumps(self.demos, sort_keys=True).encode("utf-8")).hexdigest()
        else:
            self.demos_sha256 = None

    def build_few_shot_context(self, rung: str, max_demos: int = 3) -> str:
        """Format quarantined demonstrations into few-shot context for the specified rung."""
        if not self.demos:
            raise RunnerError("Few-shot evaluation requires an approved demonstration bank.")

        relevant = [d for d in self.demos.get("items", []) if d.get("rung") == rung]
        if not relevant:
            raise RunnerError(f"No quarantined demonstrations available for rung '{rung}'.")

        selected = relevant[:max_demos]
        demo_blocks: list[str] = []
        for i, d in enumerate(selected, 1):
            block = (
                f"--- Exemplar {i} ({d['demo_id']}) ---\n"
                f"Source: {d['source_provenance']}\n"
                f"Instruction: {d['prompt_instruction']}\n"
                f"Expected Output: {d['exemplar_output']}\n"
                f"Palaeographical Note: {d['commentary']}"
            )
            demo_blocks.append(block)

        return "\n\n".join(demo_blocks)

    def format_prompt(self, rung: str, shot_mode: str) -> tuple[str, str, str]:
        """Retrieve system prompt, build user prompt, and calculate prompt SHA-256."""
        rung_prompts = self.suite["prompts"].get(rung)
        if not rung_prompts:
            raise RunnerError(f"Rung '{rung}' is not configured in evaluation suite prompts.")

        prompt_spec = rung_prompts.get(shot_mode)
        if not prompt_spec:
            raise RunnerError(f"Shot mode '{shot_mode}' not configured for rung '{rung}'.")

        system_prompt = prompt_spec["system_prompt"]
        template = prompt_spec["user_template"]

        if shot_mode == "few_shot":
            demos_text = self.build_few_shot_context(rung)
            user_prompt = template.replace("{demonstrations}", demos_text)
        else:
            user_prompt = template

        combined_text = f"{system_prompt}\n{user_prompt}"
        computed_sha256 = hashlib.sha256(combined_text.encode("utf-8")).hexdigest()

        return system_prompt, user_prompt, computed_sha256

    def evaluate_item(
        self,
        item: dict[str, Any],
        shot_mode: str,
        sample_index: int = 0,
    ) -> dict[str, Any]:
        """Execute evaluation for a single item attempt, guaranteeing complete attempt record."""
        item_id = item["item_id"]
        rung = item["rung"]
        image_bytes: bytes = item.get("image_bytes", b"")
        timestamp = datetime.now(timezone.utc).isoformat()

        # Strict image conditioning validation
        if not image_bytes:
            # Check if image_path is provided
            img_path = item.get("image_path")
            if img_path and Path(img_path).is_file():
                image_bytes = Path(img_path).read_bytes()

        if not image_bytes:
            raise ImageConditioningError(
                f"Item '{item_id}' lacks image bytes or valid image file. "
                "Prediction cannot proceed without genuine image conditioning."
            )

        image_sha256 = hashlib.sha256(image_bytes).hexdigest()
        system_prompt, user_prompt, prompt_sha256 = self.format_prompt(rung, shot_mode)

        try:
            resp: VLMResponse = self.adapter.predict(
                image_bytes=image_bytes,
                prompt=user_prompt,
                system_prompt=system_prompt,
                shot_mode=shot_mode,
                rung=rung,
                item_id=item_id,
            )
            attempt_record = {
                "item_id": item_id,
                "rung": rung,
                "shot_mode": shot_mode,
                "sample_index": sample_index,
                "status": resp.status,
                "prompt_sha256": prompt_sha256,
                "image_sha256": image_sha256,
                "raw_output": resp.raw_output,
                "cleaned_prediction": resp.cleaned_prediction,
                "error_message": resp.error_message,
                "latency_ms": resp.latency_ms,
                "token_usage": resp.token_usage,
                "timestamp": timestamp,
            }
        except Exception as exc:
            attempt_record = {
                "item_id": item_id,
                "rung": rung,
                "shot_mode": shot_mode,
                "sample_index": sample_index,
                "status": "failed",
                "prompt_sha256": prompt_sha256,
                "image_sha256": image_sha256,
                "raw_output": None,
                "cleaned_prediction": None,
                "error_message": f"Execution exception: {type(exc).__name__}: {exc}",
                "latency_ms": None,
                "token_usage": None,
                "timestamp": timestamp,
            }

        return attempt_record

    def run_suite(
        self,
        items: list[dict[str, Any]],
        shot_mode: str = "zero_shot",
        manifest_id: str | None = None,
    ) -> dict[str, Any]:
        """Run evaluation over items, generating an immutable run manifest."""
        if not items:
            raise RunnerError("Cannot run evaluation with zero items.")

        if shot_mode not in {"zero_shot", "few_shot", "both"}:
            raise RunnerError(f"Invalid shot_mode '{shot_mode}'.")

        modes = ["zero_shot", "few_shot"] if shot_mode == "both" else [shot_mode]
        attempts: list[dict[str, Any]] = []

        now_str = datetime.now(timezone.utc).isoformat()
        if not manifest_id:
            time_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            manifest_id = f"vlm_run_{self.adapter.model_key}_{shot_mode}_{time_slug}"

        for mode in modes:
            for item in items:
                attempt = self.evaluate_item(item, shot_mode=mode)
                attempts.append(attempt)

        total_attempts = len(attempts)
        successes = sum(1 for a in attempts if a["status"] == "success")
        failures = sum(1 for a in attempts if a["status"] == "failed")
        abstentions = sum(1 for a in attempts if a["status"] == "abstained")
        refusals = sum(1 for a in attempts if a["status"] == "refused")
        timeouts = sum(1 for a in attempts if a["status"] == "timeout")
        coverage_rate = round(successes / total_attempts, 4) if total_attempts > 0 else 0.0

        # Inspect hardware environment
        avail = self.adapter.check_availability()
        cuda_ok = bool(avail.hardware_info.get("cuda_available", False))
        gpu_name = avail.hardware_info.get("device_name")

        manifest: dict[str, Any] = {
            "doc_type": "vlm_run_manifest",
            "schema_version": "1.0.0",
            "manifest_id": manifest_id,
            "suite_id": self.suite["suite_id"],
            "suite_sha256": self.suite_sha256,
            "demonstrations_sha256": self.demos_sha256 if ("few_shot" in modes) else None,
            "model_key": self.adapter.model_key,
            "model_id": self.suite["models"][0]["provider_model_id"] if self.adapter.model_key == self.suite["models"][0]["key"] else self.adapter.model_config["provider_model_id"],
            "shot_mode": shot_mode,
            "execution_timestamp": now_str,
            "environment": {
                "os": platform.platform(),
                "python_version": platform.python_version(),
                "cuda_available": cuda_ok,
                "gpu_device": gpu_name,
            },
            "coverage_summary": {
                "total_items": len(items),
                "total_attempts": total_attempts,
                "success_count": successes,
                "failure_count": failures,
                "abstention_count": abstentions,
                "refusal_count": refusals,
                "timeout_count": timeouts,
                "coverage_rate": coverage_rate,
            },
            "attempts": attempts,
        }

        return manifest
