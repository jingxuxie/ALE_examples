# Adaptive Cascade under uncertain QBER

Improve a working information-reconciliation policy, not its implementation.
The reference is a strong, paper-inspired 14-pass Cascade schedule with
power-of-two blocks, cached and inferred parities, parallel searches, and
subblock reuse. Your job is to reduce its joint leakage, communication-round,
and finite-frame failure cost when the QBER estimate is noisy or stale.

Submit **`policy.json`**, a bounded declarative policy. The trusted simulator
chooses each pass from observable prepass metrics; your Python is never
imported by the evaluator. You may use any local optimization method to
produce the JSON. Do not implement or replace the simulator.

## Objective

Beat the reference by **at least 8% overall and at least 3% in every family**.
The overall score equally averages the four family cost ratios. Also satisfy
the published FER and collision-tail reliability gates. The target is fixed;
an improvement that misses any gate is not a solution.

The four families emphasize bandwidth, latency, estimator drift, and short
frames. Hidden cases use the same public distributions, independent frame
seeds, and held-out operating tuples. No hidden API or scoring convention is
part of the challenge.

## Start

Task assets are read-only. Replace `/path/to/output` with the writable output
directory supplied by your runner. From this task directory:

```sh
python3 baseline.py --output /path/to/output/policy.json
python3 scoring.py --policy /path/to/output/policy.json --split train --output /path/to/output/train_report.json
python3 scoring.py --policy /path/to/output/policy.json --split dev --output /path/to/output/dev_report.json
```

`policy.json` already contains the reference. `cascade_sim.py` is the complete
public simulator; `scoring.py` is the exact scoring implementation.
`input/train.json` and `input/dev.json` contain reproducible cases and seeds.
`input/distribution.json` declares the operating grid. `workspace/` provides
the simulator/scoring entry point; `baseline/` contains the baseline artifact
and generator entry point. Do not write into these read-only directories.

Read `INTERFACE.md` for the exact policy grammar, observables, protocol model,
scoring equation, reliability gates, and evaluation contract. The small
training split cannot certify the confidence-bound gate, even with zero
failures. Use development results, not training success alone.

Basis: Martinez-Mateo et al., *Demystifying the Information Reconciliation
Protocol Cascade*, arXiv:1407.3257v2, sections 3.1–3.3 and 4.2–4.5. This task
extends that work with explicit latency costs and uncertain finite-sample
estimates; it is not a reproduction of its numerical tables.
