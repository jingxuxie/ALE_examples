# Predict held-out quantum-memory failure rates

Build a predictor of logical failure probability using the recorded Monte Carlo experiments in `input/train.csv`. Predict every configuration in `input/queries.csv`. The queries include larger code distances and smaller physical-noise rates absent from training, across honeycomb and surface memories, several noise models, two decoders, and separate preserved observables.

The target is the named decoder's probability of failing the named observable over the **entire supplied experiment**, not a per-round rate or a new decoder. Experiments last three times their code distance in rounds. Training provides shot and correct-decoding counts; held-out counts and runtimes are private. Zero observed failures do not establish zero probability.

Submit a directory containing `solve.py`. It receives three positional paths:

```text
python solve.py TRAIN_CSV QUERY_CSV OUTPUT_CSV
```

Write exactly `query_id,p_failure` CSV, one finite probability per query. The detailed schema, allowed probability range, execution contract, and scoring equations are in `workspace/INTERFACE.md`. A runnable starter is supplied in `baseline/solve.py`.

The primary score measures the worst of 20 predeclared family/extrapolation cells, after accounting for count-likelihood uncertainty. Success requires **score >= 0.5**, meaning no cell exceeds a factor-two RMS multiplicative discrepancy beyond that uncertainty. Of 692 queries, 612 affect this score; 80 extreme low-noise/large-size cases are upper-bound diagnostics only.

Execution allows 120 seconds and 2 GiB memory, with no network and only allowlisted files. Use the supplied training data, not retrieved or precomputed held-out labels. You may choose any prediction method; no report, ablation, or investigation sequence is required.
