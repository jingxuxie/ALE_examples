# Correlated Hubbard gap prediction

## Mission
Predict paired **charge and fixed-spin-sector energy gaps**, in hopping units,
for disordered, dimerized and frustrated Fermi–Hubbard clusters. Four geometry
families independently mix ten and twelve spatial sites. Training, validation
and hidden test follow the same disclosed distribution, without instance IDs.
Conventions and sector definitions: `input/SCHEMA.md`.

## Assets and interface
All supplied assets, including `workspace/`, are **read-only**. `input/` contains
1,536 labelled training examples, 256 labelled validation examples, the generator,
schema and examples. `baseline/` provides trained kernel weights and training code;
`baseline_exact/` provides a native solver's source and binary.
`input/DEVELOPMENT.md` gives file-interface examples.

Place your self-contained submission under the supplied **`OUTPUT_DIR`**.
The evaluator invokes `python3 solver.py REQUEST_JSON PREDICTIONS_JSON` once
for all 256 hidden instances. Read the numeric NPZ named by `request["inputs"]`;
write `{"schema_version":1,"predictions":[[charge,spin],...]}` in received row order.
No private labels enter the child process.

## Objective and resources
All four accuracy bounds must hold:

| RMSE | Overall | Every family |
|---|---:|---:|
| Charge | ≤0.030 | ≤0.050 |
| Spin-sector | ≤0.020 | ≤0.035 |

Development: one-hour deadline; four-thread/8-GiB budget is advisory, not kernel-enforced.
Inference: **25 seconds wall
and CPU**, one CPU, 2 GiB address space, including startup and loading.
Runtime threads, process creation and network are denied. Precompiled code is
allowed. Write inference scratch only to `TMPDIR`; see `input/ENVIRONMENT.md`.

## Scoring
`core_score = 1/(1+max(charge_RMSE/0.030,spin_RMSE/0.020))`.
`worst_family_score` uses the worst family ratio against its limits.
Both must reach 0.5 with resource-valid output. `resource_score=max(0,1-runtime/25)`
is diagnostic. Malformed output or resource violations invalidate the batch.
