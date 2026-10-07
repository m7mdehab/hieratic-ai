# HieraticBench external-evaluation adapter

**EVAL-002** — pinned, read-only reproduction of public metadata and *published scored run aggregates*.

This is an **external benchmark only**. Do not use its images, item-level sign gold, metadata, outputs or near-duplicates for any Hieratic AI training/development corpus.

## What the adapter does

- Verifies an independent upstream Git checkout is at exactly the pinned commit in `manifest.yaml`.
- Inspects **item metadata only**, checking the full inventory against the pinned manifest.
- Reads upstream **public** `results/runs/*.jsonl` in place and computes per-sample → per-item → per-rung averages as the official `bench/src/leaderboard.ts` does.
- Compares *every* published per-item scored mean and rung score/coverage/sample count against the pinned `results/leaderboard.json`.
- Rejects sealed response text/private copies in public run logs; it never emits text answers or gold labels.
- Produces counts and PASS/FAIL only. It writes **no files**.

It does **not**:
- download data;
- read image files;
- open `results/inbox/`, `data/private/` or secret keys;
- run provider/model API calls;
- recompute individual answer scores (the official TypeScript scorer does that);
- copy upstream result/gold records to our repository;
- synthesize scores for unscored sealed readings.

## Pinned upstream revision

`d587dc990013f18007f1e7a8f56f96ff2f7127e2` (HieraticBench harness 0.1.0).

The immutable revision is mandatory. Audits of moving `main` must first produce a new reviewed manifest, not quietly reinterpret historical results.

## Running a reproduction

Run in a clean environment, outside Hieratic AI's source/data directories:

```bash
git clone https://github.com/alymoursy/hieraticbench.git /tmp/hieraticbench-eval
git -C /tmp/hieraticbench-eval checkout --detach d587dc990013f18007f1e7a8f56f96ff2f7127e2

python -m pip install -r requirements-projectctl.txt
python -m eval.benchmarks.hieraticbench.adapter inventory --checkout /tmp/hieraticbench-eval
python -m eval.benchmarks.hieraticbench.adapter verify-leaderboard --checkout /tmp/hieraticbench-eval

# Official benchmark scorer parity tests (Node >=22; external checkout only):
cd /tmp/hieraticbench-eval
npm ci
npm test
```

No API keys are needed for any step above. None of these commands reruns a frontier model. To run a model with the upstream harness, follow upstream README and use private credentials/cost controls; **never commit sealed inbox outputs**.

If a checkout's `HEAD` does not match the pinned revision, the adapter fails closed.

## CI and synthetic tests

```bash
python -m unittest discover -s tests/evaluation -v
```

All adapter unit fixtures are synthetic. They contain no real Hieratic sign readings, source images, benchmark response text, or commissioned sentence answers.

## Exact reporting boundary

| Component | Reproducibility |
|---|---|
| Public item counts and rung/source/script breakdowns | Verified from pinned upstream item metadata |
| Published *numeric* run aggregation | Recomputed by adapter from public logs |
| Public per-item/rung model aggregates | Compared against official leaderboard JSON |
| Individual answer parsing/scoring | Official open TypeScript scorer/test suite is the authority |
| Provider model answers | Not rerun here; time/provider/API/effort dependent |
| Sealed sentence sign/transliteration/translation | **Not scored** without an answer key; no scores invented |
| Sealed script identification | Public numeric scores; full response text withheld |

The Method/README source of truth and scientific limitations are documented in `docs/evaluation/HIERATICBENCH_REPRODUCTION.md`.

## License/quarantine

HieraticBench code MIT; publicly committed result logs CC BY 4.0; public images have per-item source licenses; commissioned images are © Aly Moursy and evaluation-only. This project commits only original adapter code, an upstream-source manifest, and synthetic tests. No upstream assets/results/labels are vendored.
