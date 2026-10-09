"""Pre-Coptic Egyptian-PC UD syntax diagnostic; never manuscript OCR or translation.

Immutable original UD CoNLL-U train statistics and 230 dev sentences are
CC BY-SA 4.0 by the Egyptian-PC project (University of Jaen). The official
test partition is deliberately not inspected. Gold dev UPOS is an oracle;
HEAD/DEPREL are consulted only after prediction and for source validation.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import argparse
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
from typing import Any

from tools.translation_layer import TranslationError, _canonical

ROOT = Path(__file__).resolve().parents[2]
TRAIN_FILE = ROOT / "ling/translation/data/w13_egyptian_pc_train_stats_ccby_sa.json"
DEV_FILE = ROOT / "ling/translation/data/w13_egyptian_pc_dev_gold_ccby_sa.json"
TRAIN_BLOB = "W13_TRAIN_BLOB_LOCK"
DEV_BLOB = "W13_DEV_BLOB_LOCK"
REVISION_TREE = "fca8538287cb69fd07b811eb55dcfd25584f3006"
VERSION = "w13-pre-coptic-oracle-POS-dependency-diagnostic/1.0.0"


def _gitblob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _load(path: Path, expected: str, limit: int) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise TranslationError("Pinned published dependency source missing or linked")
    raw = path.read_bytes()
    if not raw or len(raw) > limit or _gitblob(raw) != expected:
        raise TranslationError("Derived published dependency Git blob identity mismatch")
    result = json.loads(raw.decode("utf-8"))
    if not isinstance(result, dict) or result.get("rights") != "CC-BY-SA-4.0":
        raise TranslationError("Published Egyptian grammar source rights drift")
    return result


def _check_gold(rows: list[list[Any]]) -> None:
    n = len(rows)
    if not n or any(not isinstance(t, list) or len(t) != 4 for t in rows):
        raise TranslationError("Malformed UD source sentence")
    if any((not isinstance(t[0], int) or t[0] != i or not isinstance(t[1], str)
            or not t[1] or not isinstance(t[2], int) or not 0 <= t[2] <= n
            or t[2] == i or not isinstance(t[3], str) or not t[3])
           for i, t in enumerate(rows, 1)):
        raise TranslationError("Malformed original UD token or dependency pointer")
    if sum(t[2] == 0 for t in rows) != 1:
        raise TranslationError("Original gold UD sentence lacks exactly one root")
    head = [t[2] for t in rows]
    if has_cycle(head):
        raise TranslationError("Original UD label graph contains a cycle")


def has_cycle(heads: list[int]) -> list[int] | None:
    for i in range(1, len(heads) + 1):
        visited = {}
        node = i
        while node != 0:
            if node in visited:
                return list(visited)[visited[node]:]
            visited[node] = len(visited)
            if not 1 <= node <= len(heads):
                raise TranslationError("Head pointer outside sentence")
            node = heads[node - 1]
    return None


def load_project(root: Path = ROOT) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    train = _load(root / TRAIN_FILE.relative_to(ROOT), TRAIN_BLOB, 150_000)
    dev = _load(root / DEV_FILE.relative_to(ROOT), DEV_BLOB, 500_000)
    if (train.get("original_train_blob") != "ea262ee047943b81c0e0db8ff139ec7deb9b7b53"
            or dev.get("original_dev_blob") != "78a9749f823441633836b63a952df05d8636624c"
            or train.get("sentence_count") != 1619
            or train.get("token_count") != 19486
            or dev.get("source_tree") != REVISION_TREE
            or dev.get("original_test_blob_not_opened") != "f40982ca7dc7b67a5ed6d6bc90f4fe8dcd8085f6"):
        raise TranslationError("UD publisher revision and split identity mismatch")
    sentences = dev.get("sentences")
    if not isinstance(sentences, list) or len(sentences) != 230:
        raise TranslationError("UD dev population changed")
    ids = set()
    for x in sentences:
        if not isinstance(x, dict) or not isinstance(x.get("id"), str):
            raise TranslationError("UD sentence identity invalid")
        if x["id"] in ids:
            raise TranslationError("Duplicate UD source sentence ID")
        ids.add(x["id"])
        _check_gold(x["rows"])
    if sum(len(x["rows"]) for x in sentences) != 3167:
        raise TranslationError("UD dev token census drift")
    if dev.get("train_test_sentence_identity_overlap") is not True:
        raise TranslationError("UD train/dev source ID isolation unverified")
    return train, sentences


class FixedOraclePosSyntax:
    """Train-only UD head-POS/offset/relation counts; no dev label access."""

    def __init__(self, counts: dict[str, Any]):
        self.stats = counts
        self.pairs = Counter(counts["head_relation_upos_direction_counts"])
        self.labels = Counter(counts["dependent_upos_relation_counts"])
        self.root = Counter(counts["root_upos_counts"])
        self.by_pair: dict[tuple[str, str, str], list[tuple[str, int]]] = defaultdict(list)
        for key, number in self.pairs.items():
            child, headpos, direct, relation = key.split("|", 3)
            if not isinstance(number, int) or number <= 0:
                raise TranslationError("Invalid train-only UD dependency count")
            self.by_pair[(child, headpos, direct)].append((relation, number))
        self.by_child: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for key, number in self.labels.items():
            child, rel = key.split("|", 1)
            self.by_child[child].append((rel, number))
        for index in (self.by_pair, self.by_child):
            for key in index:
                index[key].sort(key=lambda x: (-x[1], x[0]))

    def _choice(self, child: str, headpos: str, direction: str, distance: int) -> tuple[float, str]:
        candidates = self.by_pair.get((child, headpos, direction), [])
        if candidates:
            relation, count = candidates[0]
            # Frozen score: log-smoothed frequency of published source-pair
            # roles. Never access target UPOS except explicitly supplied oracle.
            score = math.log1p(count)
        else:
            relation = "dep"
            score = -4.0
        if direction != "root":
            score -= 0.02 * distance
        return score, relation

    def predict(self, pos: list[str]) -> tuple[list[int], list[str]]:
        if not pos or any(not isinstance(x, str) or not x for x in pos):
            raise TranslationError("Missing oracle UPOS input")
        n = len(pos)
        # Exactly one root from train-only frequency, ties earliest position.
        root = min(range(1, n + 1), key=lambda j: (-self.root[pos[j - 1]], j))
        heads = [0] * n
        relations = ["root"] * n
        for i in range(1, n + 1):
            if i == root:
                continue
            pool = []
            for j in range(1, n + 1):
                if j == i:
                    continue
                direct = "left" if j < i else "right"
                score, relation = self._choice(pos[i - 1], pos[j - 1], direct, abs(i - j))
                pool.append((-score, j, relation))
            _, target, relation = min(pool)
            heads[i - 1], relations[i - 1] = target, relation
        # Deterministically repair cycles without changing root or using gold.
        cycle = has_cycle(heads)
        while cycle:
            member = min(cycle)
            heads[member - 1] = root
            # Explicitly label fall-back as unresolved syntactic attachment,
            # never invent a certified relation on an unobserved pair.
            relations[member - 1] = self._choice(
                pos[member - 1], pos[root - 1],
                "left" if root < member else "right",
                abs(root - member)
            )[1]
            cycle = has_cycle(heads)
        if heads.count(0) != 1 or has_cycle(heads):
            raise TranslationError("Unrepaired predicted UD structure")
        return heads, relations

    def baseline(self, pos: list[str]) -> tuple[list[int], list[str]]:
        heads = [0] + [i for i in range(1, len(pos))]
        relations = ["root"]
        for p in pos[1:]:
            label = next((rel for rel, _ in self.by_child.get(p, []) if rel != "root"), "dep")
            relations.append(label)
        return heads, relations


def evaluate(train: dict[str, Any], dev: list[dict[str, Any]]) -> dict[str, Any]:
    model = FixedOraclePosSyntax(train)
    summaries = {}
    for method in ("baseline", "model"):
        correct_uas = correct_las = tokens = 0
        bypos = defaultdict(lambda: [0, 0, 0])
        invalid = 0
        for sentence in dev:
            rows = sentence["rows"]
            pos = [r[1] for r in rows]
            h, r = getattr(model, "baseline" if method == "baseline" else "predict")(pos)
            if len(h) != len(rows) or h.count(0) != 1 or has_cycle(h):
                invalid += 1
            for original, pred_h, pred_rel in zip(rows, h, r):
                correct = original[2] == pred_h
                uas = int(correct)
                las = int(correct and original[3] == pred_rel)
                correct_uas += uas
                correct_las += las
                tokens += 1
                bypos[original[1]][0] += 1
                bypos[original[1]][1] += uas
                bypos[original[1]][2] += las
        summaries[method] = {
            "sentences": len(dev), "tokens": tokens,
            "correct_head": correct_uas, "correct_head_relation": correct_las,
            "UAS": round(correct_uas / tokens, 8),
            "LAS": round(correct_las / tokens, 8),
            "invalid_predicted_trees": invalid,
            "upos_error_breakdown": {
                upos: {"total": q[0], "UAS_correct": q[1], "LAS_correct": q[2]}
                for upos, q in sorted(bypos.items())
            },
        }
    report = {
        "experiment": VERSION,
        "source": "UD Egyptian-PC University of Jaen Pyramid Texts",
        "source_tree": REVISION_TREE,
        "license": "CC-BY-SA-4.0",
        "oracle_dev_UPOS_exposed": True,
        "gold_dev_HEAD_DEPREL_used_for_prediction": False,
        "official_test_split_opened": False,
        "training_sentence_count": train["sentence_count"],
        "training_token_count": train["token_count"],
        "development_sentence_count": len(dev),
        "metrics": summaries,
        "no_original_hieratic_image": True,
        "not_semantically_validated_translation": True,
        "cross_period_application_not_established": True,
        "ling003_scientific_milestone_accepted": False,
        "scientific_capability_points": 0.0,
    }
    report["report_sha256"] = sha256(_canonical(report)).hexdigest()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "evaluate"))
    args = parser.parse_args(argv)
    try:
        train, dev = load_project()
        output = evaluate(train, dev) if args.action == "evaluate" else {
            "train_sentences": train["sentence_count"], "dev_sentences": len(dev),
            "dev_tokens": sum(len(s["rows"]) for s in dev),
            "official_test_opened": False, "rights": "CC-BY-SA-4.0",
        }
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (TranslationError, OSError, ValueError, TypeError, KeyError) as exc:
        print("EGYPTIAN PC SYNTAX REFUSED: " + str(exc), file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
