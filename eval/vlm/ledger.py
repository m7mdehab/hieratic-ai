"""Durable Write-Ahead Attempt Ledger for VLM Experimental Evaluations.

Provides fault-tolerant, append-only disk logging with immediate fsync
guarantees before and after model dispatch, protecting against crashes,
interrupted runs, and silent attempt loss.

Enforces:
- Write-ahead dispatch recording (status: "dispatched") before model forward pass
- Immediate completion/failure recording (status: "succeeded" | "failed" | "skipped")
- Immediate fsync to disk on every transaction
- Strict accounting invariants:
    planned = attempted + explicitly_skipped
    attempted = succeeded + failed
- Idempotency and deterministic resume without overwriting previous outputs
- Tamper and corruption detection
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any


class LedgerError(Exception):
    """Base exception for ledger operations."""
    pass


class LedgerAccountingError(LedgerError):
    """Raised when ledger accounting invariants are violated."""
    pass


class LedgerIntegrityError(LedgerError):
    """Raised when ledger file is corrupted, truncated, or tampered with."""
    pass


class LedgerDuplicateAttemptError(LedgerError):
    """Raised when an attempt ID is duplicated in an invalid context."""
    pass


class LedgerLockError(LedgerError):
    """Raised when ledger cannot be locked due to concurrent writer access."""
    pass


try:
    import msvcrt
except ImportError:
    msvcrt = None

try:
    import fcntl
except ImportError:
    fcntl = None


def _acquire_exclusive_lock(lock_path: Path) -> Any:
    """Acquire non-blocking exclusive lock on dedicated lock file, raising LedgerLockError if held."""
    handle = open(lock_path, "a+")
    fileno = handle.fileno()
    try:
        if msvcrt is not None:
            handle.seek(0)
            msvcrt.locking(fileno, msvcrt.LK_NBLCK, 1)
        elif fcntl is not None:
            fcntl.flock(fileno, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, IOError) as exc:
        handle.close()
        raise LedgerLockError(f"Concurrent ledger access rejected: file is locked by another writer ({exc})") from exc
    return handle


def _release_exclusive_lock(handle: Any, lock_path: Path | None = None) -> None:
    """Release exclusive file lock and clean up handle."""
    if handle is not None and not handle.closed:
        try:
            fileno = handle.fileno()
            if msvcrt is not None:
                handle.seek(0)
                msvcrt.locking(fileno, msvcrt.LK_UNLCK, 1)
            elif fcntl is not None:
                fcntl.flock(fileno, fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            handle.close()
        except Exception:
            pass
    # A stable lockfile must remain after unlocking. Unlinking permits another
    # process to hold an old inode lock while a third writer locks a new inode.


def validate_ledger_path(path: Path | str) -> Path:
    """Validate ledger path and ensure it is not a directory or escaping path."""
    p = Path(path).resolve()
    if p.is_dir():
        raise LedgerError(f"Ledger path must be a file, got directory: {p}")
    return p


def iso_utc_now() -> str:
    """Return ISO 8601 UTC timestamp ending in 'Z'."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


class DurableAttemptLedger:
    """Durable append-only write-ahead ledger with fsync durability."""

    def __init__(
        self,
        ledger_path: Path | str,
        run_id: str,
        protocol_fingerprint: str,
        *,
        read_only: bool = False,
    ) -> None:
        self.ledger_path = validate_ledger_path(ledger_path)
        self.run_id = run_id
        self.protocol_fingerprint = protocol_fingerprint
        self.read_only = read_only

        self._dispatches: dict[str, dict[str, Any]] = {}
        self._completions: dict[str, dict[str, Any]] = {}
        self._skips: dict[str, dict[str, Any]] = {}
        self._finalized_attempts: dict[str, dict[str, Any]] = {}
        self._attempt_order: list[str] = []

        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_handle = None
        self._lock_handle = None
        self._lock_path = self.ledger_path.with_name(self.ledger_path.name + ".lock")
        # Lock before reading/auditing existing content. Snapshotting before
        # acquiring the lock races with a second writer's append.
        if not self.read_only:
            self._lock_handle = _acquire_exclusive_lock(self._lock_path)
        try:
            if self.ledger_path.is_file():
                audit = verify_ledger_file_integrity(self.ledger_path, allow_incomplete=True)
                if not audit["valid"]:
                    raise LedgerIntegrityError("Existing attempt ledger failed verification: " + "; ".join(audit["errors"][:4]))
                self._load_existing_records()
            if not self.read_only:
                self._file_handle = open(self.ledger_path, "a", encoding="utf-8")
        except Exception:
            _release_exclusive_lock(self._lock_handle, self._lock_path)
            self._lock_handle = None
            raise

    def _load_existing_records(self) -> None:
        """Parse existing records and populate state."""
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    record = json.loads(clean_line)
                except json.JSONDecodeError as exc:
                    raise LedgerIntegrityError(
                        f"Ledger parse error at line {line_no} in {self.ledger_path}: {exc}"
                    ) from exc

                rec_type = record.get("record_type")
                att_id = record.get("attempt_id")
                if record.get("run_id") != self.run_id:
                    raise LedgerIntegrityError(f"Run ID mismatch at ledger line {line_no}")
                if rec_type in ("dispatch", "skip") and record.get("protocol_fingerprint") != self.protocol_fingerprint:
                    raise LedgerIntegrityError(f"Protocol fingerprint mismatch at ledger line {line_no}")
                if not att_id:
                    raise LedgerIntegrityError(f"Missing attempt_id at line {line_no}")

                if rec_type == "dispatch":
                    self._dispatches[att_id] = record
                    if att_id not in self._attempt_order:
                        self._attempt_order.append(att_id)
                elif rec_type == "completion":
                    if att_id not in self._dispatches:
                        raise LedgerIntegrityError(
                            f"Orphan completion without prior dispatch at line {line_no}: {att_id}"
                        )
                    status = record.get("status")
                    if status not in ("success", "failed"):
                        raise LedgerIntegrityError(f"Invalid completion status at line {line_no}: {status}")
                    if status == "success" and record.get("error_category", "none") != "none":
                        raise LedgerIntegrityError(f"Success completion with error category at line {line_no}")
                    self._completions[att_id] = record
                    disp = self._dispatches[att_id]
                    self._finalized_attempts[att_id] = self._merge_attempt(disp, record)
                elif rec_type == "skip":
                    self._skips[att_id] = record
                    if att_id not in self._attempt_order:
                        self._attempt_order.append(att_id)
                    self._finalized_attempts[att_id] = record
                else:
                    raise LedgerIntegrityError(f"Unknown record_type '{rec_type}' at line {line_no}")

    def _write_record(self, record: dict[str, Any]) -> None:
        """Append record to ledger file and synchronously flush and fsync."""
        if self.read_only or self._file_handle is None:
            raise LedgerError("Cannot write to read-only or closed ledger")
        line = json.dumps(record, sort_keys=True) + "\n"
        self._file_handle.write(line)
        self._file_handle.flush()
        os.fsync(self._file_handle.fileno())

    def _merge_attempt(self, dispatch: dict[str, Any], completion: dict[str, Any]) -> dict[str, Any]:
        """Merge dispatch and completion records into canonical attempt format."""
        merged = dict(dispatch)
        merged.pop("record_type", None)
        merged.update({
            "status": completion.get("status", "success"),
            "completed_at": completion.get("completed_at"),
            "latency_ms": completion.get("latency_ms", 0.0),
            "token_usage": completion.get("token_usage", {}),
            "output_text": completion.get("output_text", ""),
            "output_sha256": completion.get("output_sha256", hashlib.sha256(b"").hexdigest()),
            "classification": completion.get("classification"),
            "error_message": completion.get("error_message"),
            "error_category": completion.get("error_category", "none"),
            "runtime_info": completion.get("runtime_info", {}),
            "retry_lineage": completion.get("retry_lineage", []),
        })
        return merged

    def is_attempt_completed(self, attempt_id: str) -> bool:
        """Check if attempt is already completed (for idempotent resume)."""
        return attempt_id in self._finalized_attempts

    def get_completed_attempt(self, attempt_id: str) -> dict[str, Any] | None:
        """Get already completed attempt record if present."""
        return self._finalized_attempts.get(attempt_id)

    def record_dispatch(
        self,
        attempt_id: str,
        attempt_index: int,
        target_or_control_id: str,
        physical_witness: str,
        source_raw_sha256: str,
        stimulus_sha256: str,
        stimulus_dimensions: list[int],
        task: str,
        rung: str,
        prompt_variant: str,
        prompt_text: str,
        prompt_sha256: str,
        model_id: str,
        model_revision: str,
        model_weight_sha256: str,
        decoding_parameters: dict[str, Any],
        attempt_category: str = "media",
    ) -> dict[str, Any]:
        """Write-ahead log an attempt before dispatching to model."""
        if attempt_id in self._dispatches or attempt_id in self._skips:
            raise LedgerDuplicateAttemptError(
                f"Attempt ID '{attempt_id}' already dispatched or skipped; reuse is forbidden"
            )

        dispatch_record = {
            "record_type": "dispatch",
            "run_id": self.run_id,
            "protocol_fingerprint": self.protocol_fingerprint,
            "attempt_id": attempt_id,
            "attempt_index": attempt_index,
            "attempt_category": attempt_category,
            "target_or_control_id": target_or_control_id,
            "physical_witness": physical_witness,
            "source_raw_sha256": source_raw_sha256,
            "stimulus_sha256": stimulus_sha256,
            "stimulus_dimensions": stimulus_dimensions,
            "task": task,
            "rung": rung,
            "prompt_variant": prompt_variant,
            "prompt_text": prompt_text,
            "prompt_sha256": prompt_sha256,
            "model_id": model_id,
            "model_revision": model_revision,
            "model_weight_sha256": model_weight_sha256,
            "decoding_parameters": decoding_parameters,
            "status": "dispatched",
            "dispatched_at": iso_utc_now(),
        }

        # Disk must be durable before memory claims an attempt was dispatched.
        self._write_record(dispatch_record)
        self._dispatches[attempt_id] = dispatch_record
        self._attempt_order.append(attempt_id)
        return dispatch_record

    def record_completion(
        self,
        attempt_id: str,
        status: str,
        output_text: str,
        latency_ms: float = 0.0,
        token_usage: dict[str, Any] | None = None,
        classification: dict[str, Any] | None = None,
        error_message: str | None = None,
        error_category: str = "none",
        runtime_info: dict[str, Any] | None = None,
        retry_lineage: list[str] | None = None,
    ) -> dict[str, Any]:
        """Log completion of a dispatched attempt and return the finalized attempt."""
        if attempt_id not in self._dispatches:
            raise LedgerError(f"Cannot complete attempt '{attempt_id}': no dispatch recorded")
        if attempt_id in self._completions:
            raise LedgerDuplicateAttemptError(f"Attempt '{attempt_id}' already has completion recorded")
        if status not in ("success", "failed"):
            raise LedgerError(f"Invalid completion status: '{status}'; must be 'success' or 'failed'")
        if status == "success" and error_category != "none":
            raise LedgerError(f"Cannot record success status with error category '{error_category}'")
        if status == "success" and error_message is not None:
            raise LedgerError(f"Cannot record success status with error message: '{error_message}'")
        if status == "failed" and (not error_category or error_category == "none"):
            raise LedgerError("Failed status requires an explicit error category")

        out_sha = hashlib.sha256(output_text.encode("utf-8")).hexdigest()

        completion_record = {
            "record_type": "completion",
            "run_id": self.run_id,
            "attempt_id": attempt_id,
            "status": status,
            "completed_at": iso_utc_now(),
            "latency_ms": latency_ms,
            "token_usage": token_usage or {},
            "output_text": output_text,
            "output_sha256": out_sha,
            "classification": classification,
            "error_message": error_message,
            "error_category": error_category if status == "failed" else "none",
            "runtime_info": runtime_info or {},
            "retry_lineage": retry_lineage or [],
        }

        # Never mark complete in memory until the completion event is fsynced.
        self._write_record(completion_record)
        self._completions[attempt_id] = completion_record
        finalized = self._merge_attempt(self._dispatches[attempt_id], completion_record)
        self._finalized_attempts[attempt_id] = finalized
        return finalized

    def record_skip(
        self,
        attempt_id: str,
        attempt_index: int,
        target_or_control_id: str,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an explicit skipped attempt."""
        if attempt_id in self._dispatches or attempt_id in self._skips:
            raise LedgerDuplicateAttemptError(f"Attempt '{attempt_id}' was already dispatched or skipped")

        skip_record = {
            "record_type": "skip",
            "run_id": self.run_id,
            "protocol_fingerprint": self.protocol_fingerprint,
            "attempt_id": attempt_id,
            "attempt_index": attempt_index,
            "target_or_control_id": target_or_control_id,
            "status": "skipped",
            "skipped_at": iso_utc_now(),
            "skip_reason": reason,
            "metadata": metadata or {},
        }

        self._write_record(skip_record)
        self._skips[attempt_id] = skip_record
        self._attempt_order.append(attempt_id)
        self._finalized_attempts[attempt_id] = skip_record
        return skip_record

    def resolve_interrupted_attempts(self) -> list[str]:
        """Conservatively finalize orphan dispatches as failures, never silently rerun them.

        A process may have sent the call but lost its output before fsync, so
        recovered attempts are explicitly UNKNOWN_OUTCOME failures. Resume
        proceeds with other frozen IDs, without modifying previous events.
        """
        unresolved = [
            aid for aid in self._attempt_order
            if aid in self._dispatches and aid not in self._completions
        ]
        for attempt_id in unresolved:
            self.record_completion(
                attempt_id=attempt_id,
                status="failed",
                output_text="",
                error_message="Interrupted after durable dispatch; model execution outcome unknown",
                error_category="interrupted_unknown_outcome",
            )
        return unresolved

    def audit_accounting(self, planned_count: int) -> dict[str, int]:
        """Verify the mandatory accounting equations:

        planned = attempted + explicitly_skipped
        attempted = succeeded + failed
        """
        succeeded = sum(1 for a in self._finalized_attempts.values() if a.get("status") == "success")
        failed = sum(1 for a in self._finalized_attempts.values() if a.get("status") == "failed")
        skipped = len(self._skips)
        attempted = succeeded + failed
        total_finalized = len(self._finalized_attempts)

        # Check for uncompleted dispatches (interrupted run)
        uncompleted_dispatches = set(self._dispatches.keys()) - set(self._completions.keys())
        if uncompleted_dispatches:
            raise LedgerAccountingError(
                f"Interrupted run detected: {len(uncompleted_dispatches)} attempts dispatched "
                f"without completion: {sorted(list(uncompleted_dispatches))[:3]}"
            )

        if total_finalized != (attempted + skipped):
            raise LedgerAccountingError(
                f"Accounting equation violation: total_finalized ({total_finalized}) != "
                f"attempted ({attempted}) + skipped ({skipped})"
            )

        if planned_count != (attempted + skipped):
            raise LedgerAccountingError(
                f"Accounting equation violation: planned ({planned_count}) != "
                f"attempted ({attempted}) + skipped ({skipped})"
            )

        return {
            "planned_forward_passes": planned_count,
            "total_attempts_recorded": total_finalized,
            "successful_actual_passes": succeeded,
            "failed_attempts": failed,
            "skipped_attempts": skipped,
        }

    def export_attempt_ledger(self) -> list[dict[str, Any]]:
        """Return finalized attempts in arrival order."""
        return [self._finalized_attempts[aid] for aid in self._attempt_order if aid in self._finalized_attempts]

    def close(self) -> None:
        """Flush, unlock, and close ledger file."""
        if self._file_handle is not None and not self._file_handle.closed:
            self._file_handle.flush()
            os.fsync(self._file_handle.fileno())
            self._file_handle.close()
            self._file_handle = None
        if getattr(self, "_lock_handle", None) is not None:
            _release_exclusive_lock(self._lock_handle, getattr(self, "_lock_path", None))
            self._lock_handle = None

    def __enter__(self) -> DurableAttemptLedger:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


def verify_ledger_file_integrity(ledger_path: Path | str, *, allow_incomplete: bool = False) -> dict[str, Any]:
    """Audit ledger file for tampering, truncation, invalid JSON, or broken hashes."""
    p = Path(ledger_path).resolve()
    if not p.is_file():
        return {"valid": False, "errors": [f"Ledger file does not exist: {p}"]}

    errors: list[str] = []
    dispatches: dict[str, dict[str, Any]] = {}
    completions: dict[str, dict[str, Any]] = {}
    skips: dict[str, dict[str, Any]] = {}
    expected_run_id: str | None = None
    expected_fingerprint: str | None = None
    expected_model_weight: str | None = None
    target_source_hashes: dict[str, str] = {}

    with open(p, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            cl = line.strip()
            if not cl:
                continue
            try:
                rec = json.loads(cl)
            except Exception as e:
                errors.append(f"Line {idx}: JSON parse error: {e}")
                continue

            rec_type = rec.get("record_type")
            att_id = rec.get("attempt_id")
            if not isinstance(rec.get("run_id"), str) or not rec.get("run_id"):
                errors.append(f"Line {idx}: Missing run identity")
            elif expected_run_id is None:
                expected_run_id = rec["run_id"]
            elif rec["run_id"] != expected_run_id:
                errors.append(f"Line {idx}: Run identity changed within ledger")
            if rec_type in ("dispatch", "skip"):
                fp = rec.get("protocol_fingerprint")
                if not isinstance(fp, str) or not fp:
                    errors.append(f"Line {idx}: Missing protocol fingerprint")
                elif expected_fingerprint is None:
                    expected_fingerprint = fp
                elif fp != expected_fingerprint:
                    errors.append(f"Line {idx}: Mixed protocol fingerprints")

            if not att_id:
                errors.append(f"Line {idx}: Missing attempt_id")
                continue

            if rec_type == "dispatch":
                if att_id in dispatches or att_id in skips:
                    errors.append(f"Line {idx}: Duplicate/conflicting dispatch for attempt '{att_id}'")
                dispatches[att_id] = rec

                # Model weight signature consistency across dispatches
                mw = rec.get("model_weight_sha256")
                if not isinstance(mw, str) or not mw:
                    errors.append(f"Line {idx}: Missing model_weight_sha256 in dispatch '{att_id}'")
                elif expected_model_weight is None:
                    expected_model_weight = mw
                elif mw != expected_model_weight:
                    errors.append(f"Line {idx}: Mixed model weight signatures ({mw} != {expected_model_weight})")

                # Source consistency per target
                tgt = rec.get("target_or_control_id")
                raw_sha = rec.get("source_raw_sha256")
                if tgt and raw_sha:
                    if tgt in target_source_hashes and target_source_hashes[tgt] != raw_sha:
                        errors.append(f"Line {idx}: Inconsistent source raw hash for target '{tgt}'")
                    target_source_hashes[tgt] = raw_sha

            elif rec_type == "completion":
                status = rec.get("status")
                if status not in ("success", "failed"):
                    errors.append(f"Line {idx}: Invalid completion status for '{att_id}': {status}")
                if status == "success":
                    if rec.get("error_category", "none") != "none":
                        errors.append(f"Line {idx}: Error category '{rec.get('error_category')}' recorded with success status for '{att_id}'")
                    if rec.get("error_message") is not None:
                        errors.append(f"Line {idx}: Error message recorded with success status for '{att_id}'")
                elif status == "failed":
                    if not rec.get("error_category") or rec.get("error_category") == "none":
                        errors.append(f"Line {idx}: Failed completion without error category for '{att_id}'")

                if att_id not in dispatches:
                    errors.append(f"Line {idx}: Completion without prior dispatch for '{att_id}'")
                if att_id in completions:
                    errors.append(f"Line {idx}: Duplicate completion for attempt '{att_id}'")
                completions[att_id] = rec

                # Output hash verification
                out_txt = rec.get("output_text", "")
                exp_sha = rec.get("output_sha256")
                actual_sha = hashlib.sha256(out_txt.encode("utf-8")).hexdigest()
                if exp_sha != actual_sha:
                    errors.append(
                        f"Line {idx}: Output SHA-256 mismatch for '{att_id}': recorded {exp_sha} != actual {actual_sha}"
                    )
            elif rec_type == "skip":
                if att_id in skips or att_id in dispatches:
                    errors.append(f"Line {idx}: Duplicate skip or conflict for '{att_id}'")
                skips[att_id] = rec
            else:
                errors.append(f"Line {idx}: Unknown record_type '{rec_type}'")

    # Check for incomplete dispatches
    if not allow_incomplete:
        for d_id in dispatches:
            if d_id not in completions:
                errors.append(f"Unfinished attempt: dispatch '{d_id}' has no matching completion record")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "dispatches_count": len(dispatches),
        "completions_count": len(completions),
        "skips_count": len(skips),
        "total_lines_read": idx if 'idx' in locals() else 0,
    }
