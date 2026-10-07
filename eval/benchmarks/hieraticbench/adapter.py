"""Read-only HieraticBench inventory and public-score aggregation verifier.

Reads upstream metadata and *numeric public run scores* in place.
Does not download images, score models, copy gold labels, inspect private inbox,
or write to any source/training directory. The upstream TypeScript scorer remains
the authority for individual response scoring.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import yaml


DEFAULT_MANIFEST = Path(__file__).with_name("manifest.yaml")
VALID_RUNGS = {"identify", "signs", "transliterate", "translate"}


class BenchmarkAuditError(ValueError):
    """Upstream snapshot, public result, or safety validation failed."""


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not payload.get("benchmark", {}).get("pinned_commit"):
        raise BenchmarkAuditError("Invalid or unpinned benchmark manifest")
    return payload


def assert_pinned_checkout(checkout: Path, manifest: dict[str, Any]) -> None:
    """Reject a moving checkout: audit only the upstream revision we verified."""
    proc = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        raise BenchmarkAuditError("Checkout must be a Git repository with a readable HEAD")
    actual = proc.stdout.strip()
    expected = manifest["benchmark"]["pinned_commit"]
    if actual != expected:
        raise BenchmarkAuditError(f"Upstream revision mismatch: expected {expected}, found {actual}")


def inspect_items(checkout: Path, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Inspect only allowed metadata keys; never output sign gold or image contents."""
    directory = checkout / "data" / "items"
    if not directory.is_dir():
        raise BenchmarkAuditError("Expected upstream data/items directory")
    items: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        item_id = raw.get("id")
        if not isinstance(item_id, str) or path.stem != item_id or item_id in items:
            raise BenchmarkAuditError(f"Invalid/duplicate item identity: {path.name}")
        split = raw.get("split")
        rungs = raw.get("rungs")
        if split not in {"public", "sealed"} or not isinstance(rungs, list):
            raise BenchmarkAuditError(f"Invalid split/rungs for {item_id}")
        if not rungs or any(r not in VALID_RUNGS for r in rungs) or len(rungs) != len(set(rungs)):
            raise BenchmarkAuditError(f"Invalid or duplicate rungs for {item_id}")
        if "identify" in rungs and not isinstance(raw.get("script"), str):
            raise BenchmarkAuditError(f"Missing script label on {item_id}")
        if split == "sealed" and ("gardiner" in raw or "transliteration" in raw or "translation" in raw):
            raise BenchmarkAuditError(f"Sealed answer-bearing field exposed on {item_id}")
        # Deliberately omit image, textual readings, sign gold, and license details.
        items[item_id] = {
            "id": item_id,
            "split": split,
            "rungs": tuple(rungs),
            "script": raw.get("script"),
            "source_prefix": item_id.split("-")[0],
        }
    expected = manifest["inventory"]
    counters = {
        "items": len(items),
        "public": sum(i["split"] == "public" for i in items.values()),
        "sealed": sum(i["split"] == "sealed" for i in items.values()),
        "by_source": dict(Counter(i["source_prefix"] for i in items.values())),
        "by_rung": dict(Counter(r for i in items.values() for r in i["rungs"])),
        "by_script": dict(Counter(i["script"] for i in items.values() if i["script"])),
    }
    for key, observed in counters.items():
        if observed != expected[key]:
            raise BenchmarkAuditError(f"Inventory mismatch for {key}: expected {expected[key]!r}, observed {observed!r}")
    return items


def mean(values: list[float]) -> float:
    if not values:
        raise BenchmarkAuditError("Cannot average an empty result set")
    return sum(values) / len(values)


def aggregate_public_scores(
    checkout: Path, items: dict[str, dict[str, Any]]
) -> tuple[dict[str, dict[str, dict[str, float | int]]], dict[str, dict[str, dict[str, float]]], int]:
    """Mirror upstream leaderboard.ts: samples -> per-item means -> per-rung means.

    This uses *upstream-stored numeric scores*. It intentionally does NOT rescore
    raw model text or reproduce provider API calls.
    """
    runs = checkout / "results" / "runs"
    if not runs.is_dir():
        raise BenchmarkAuditError("Expected upstream results/runs directory")
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    checked = 0
    for path in sorted(runs.glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                r = json.loads(line)
                item_id = r.get("itemId")
                item = items.get(item_id)
                if item is None:
                    raise BenchmarkAuditError(f"{path.name}:{line_no}: unknown item")
                rung = r.get("rung")
                if rung not in item["rungs"]:
                    raise BenchmarkAuditError(f"{path.name}:{line_no}: invalid item rung")
                if r.get("privateCopy") or (item["split"] == "sealed" and r.get("response")):
                    raise BenchmarkAuditError(f"{path.name}:{line_no}: sealed response in public results")
                model = r.get("model") or {}
                model_key = model.get("key")
                effort = model.get("effort")
                if not isinstance(model_key, str) or not model_key:
                    raise BenchmarkAuditError(f"{path.name}:{line_no}: invalid model key")
                entry_key = f"{model_key}@{effort}" if effort else model_key
                value = r.get("score")
                checked += 1
                if value is None:
                    continue
                if isinstance(value, bool) or not isinstance(value, (float, int)) or not (0 <= value <= 1):
                    raise BenchmarkAuditError(f"{path.name}:{line_no}: invalid public score")
                grouped[(entry_key, item_id, rung)].append(float(value))

    per_item: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    model_rung_scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    sample_counts: Counter[tuple[str, str]] = Counter()
    rung_population = Counter(r for item in items.values() for r in item["rungs"])

    for (model, item_id, rung), scores in grouped.items():
        avg = mean(scores)
        per_item[item_id][model][rung] = avg
        model_rung_scores[model][rung].append(avg)
        sample_counts[(model, rung)] += len(scores)

    result: dict[str, dict[str, dict[str, float | int]]] = {}
    for model, by_rung in model_rung_scores.items():
        result[model] = {}
        for rung, values in by_rung.items():
            result[model][rung] = {
                "score": mean(values),
                "items": len(values),
                "samples": sample_counts[(model, rung)],
                "coverage": len(values) / rung_population[rung],
            }
    return result, {k: dict(v) for k, v in per_item.items()}, checked


def verify_leaderboard(
    checkout: Path, items: dict[str, dict[str, Any]]
) -> dict[str, int]:
    """Verify published public aggregates, coverage, samples AND per-item means."""
    path = checkout / "results" / "leaderboard.json"
    upstream = json.loads(path.read_text(encoding="utf-8"))
    reference = upstream.get("dataset") or {}
    expected_inventory = {
        "items": len(items),
        "sealed": sum(i["split"] == "sealed" for i in items.values()),
        "bySource": dict(Counter(i["source_prefix"] for i in items.values())),
        "byScript": dict(Counter(i["script"] for i in items.values() if i["script"])),
        "byRung": dict(Counter(r for i in items.values() for r in i["rungs"])),
    }
    for key, expected in expected_inventory.items():
        if reference.get(key) != expected:
            raise BenchmarkAuditError(f"Published leaderboard dataset mismatch: {key}")

    generated, per_item, n_records = aggregate_public_scores(checkout, items)
    official = {entry["key"]: entry["rungs"] for entry in upstream["entries"]}
    if set(generated) != set(official):
        raise BenchmarkAuditError("Model/effort entries do not match published leaderboard")
    checked_groups = 0
    for model, by_rung in generated.items():
        if set(by_rung) != set(official[model]):
            raise BenchmarkAuditError(f"Different scored rung coverage for {model}")
        for rung, fields in by_rung.items():
            official_fields = official[model][rung]
            for field, value in fields.items():
                actual = official_fields.get(field)
                if field in {"score", "coverage"}:
                    if not isinstance(actual, (float, int)) or abs(actual - value) > 1e-10:
                        raise BenchmarkAuditError(f"Published score mismatch: {model}.{rung}.{field}")
                elif actual != value:
                    raise BenchmarkAuditError(f"Published count mismatch: {model}.{rung}.{field}")
            checked_groups += 1

    reference_per_item = upstream.get("perItem") or {}
    if set(reference_per_item) != set(per_item):
        raise BenchmarkAuditError("Published per-item keys do not match source runs")
    checked_items = 0
    for item_id, by_model in per_item.items():
        if set(by_model) != set(reference_per_item[item_id]):
            raise BenchmarkAuditError(f"Published model keys differ for {item_id}")
        for model, by_rung in by_model.items():
            if set(by_rung) != set(reference_per_item[item_id][model]):
                raise BenchmarkAuditError(f"Published item rungs differ for {item_id}/{model}")
            for rung, value in by_rung.items():
                if abs(value - reference_per_item[item_id][model][rung]) > 1e-10:
                    raise BenchmarkAuditError(f"Published per-item score mismatch: {item_id}/{model}/{rung}")
                checked_items += 1
    return {
        "item_records": len(items),
        "public_run_records_examined": n_records,
        "model_rows": len(generated),
        "rung_aggregates_verified": checked_groups,
        "item_rung_model_means_verified": checked_items,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only, pinned HieraticBench public aggregation audit")
    parser.add_argument("command", choices=["inventory", "verify-leaderboard"])
    parser.add_argument("--checkout", type=Path, required=True, help="External upstream checkout; not a training directory")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        assert_pinned_checkout(args.checkout, manifest)
        items = inspect_items(args.checkout, manifest)
        if args.command == "inventory":
            summary = {
                "pinned_revision": manifest["benchmark"]["pinned_commit"],
                "item_records": len(items),
                "sealed": sum(i["split"] == "sealed" for i in items.values()),
            }
        else:
            summary = verify_leaderboard(args.checkout, items)
        print("PASS: external benchmark audit (no images, gold answers or response text exported)")
        print(json.dumps(summary, sort_keys=True, indent=2))
        return 0
    except (BenchmarkAuditError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
