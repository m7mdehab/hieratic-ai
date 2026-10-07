# Experiment Registry

No validated model experiments have been run yet.

## Rules

Every experiment receives a stable ID, e.g. `EXP-HTR-001`.

Minimum record:
- hypothesis;
- linked task;
- Git commit;
- dataset/manifests and split version;
- model/checkpoint;
- configuration and seed(s);
- execution environment;
- command/entry point;
- metrics;
- artifacts;
- result;
- interpretation;
- decision caused by the result;
- known caveats.

A failed experiment remains in the registry. Negative results may increase research coverage but do not automatically earn capability points.

## Template

```yaml
id: EXP-...
task_id: ...
status: planned
hypothesis: ...
code_commit: ...
data_version: ...
split_version: ...
model: ...
config: ...
seeds: []
metrics: {}
artifacts: []
result: ...
decision: ...
caveats: []
```
