# Best-found candidate: full task not solved

`witness.json` is the static artifact. It contains only schema version 1 and the
two symmetric, zero-diagonal 7-by-7 VV control matrices. It is a regular UTF-8
file of 2,308 bytes, within the 32 KiB limit.

**No fully passing witness was found.** This candidate meets the nominal
conditions and exhibits VV-only persistence in the public tests below, but
fails the required full-coefficient robustness family.

## Exact nominal results

| Metric | Value | Required |
|---|---:|---:|
| Largest absolute triple increment | 0.81134751 microEh | <= 1 microEh |
| Missing correlation-energy tail | 99.75437463 microEh | >= 50 microEh |
| Tail-to-parent ratio | 122.94901165 | >= 100 |
| Squared reference amplitude | 0.981008625 | >= 0.95 |
| Paired-sector gap | 0.781880640 Eh | >= 0.4 Eh |
| Diagonal reference margin | 0.965714015 Eh | >= 0.6 Eh |

All 35 nominal triple increments satisfy the gate. The complete nominal MBE
and its closure diagnostics are recorded in `nominal_metrics.json`.

## Exact public perturbation checks

| Pool | Cases per family | Required successes | VV successes | Full successes |
|---|---:|---:|---:|---:|
| Supplied public training pool | 64 | 61 | 61 | 3 |
| Three fresh diagnostic pools combined | 1,536 | 1,460 | 1,499 | 67 |
| Resource-bounded public check | 128 | 122 | 122 | 5 |

The three fresh pools use seeds 594503, 890371, and 114227, with 512 cases per
family per seed. Every case in these pools is physically and numerically valid.
Their largest numerical verification error is below 2.9e-15 Eh. The shortfall
is in the screening/tail conditions, not the physical or numerical checks.

The resource-bounded check uses seed 704932, closed stdin, one BLAS thread,
a 90-second wall limit, a 60-second CPU limit, and a 512 MiB address-space limit.
It exits normally; the supplied checker reports about 3.39 seconds. Its
`passed` field is false because the full family has only 5 of the required
122 successes.

These are public diagnostics, not the hidden assay. No hidden artifacts or
network resources were accessed, and no official pass is claimed. Results
apply only to the supplied seniority-zero effective model.

## Files

- `witness.json`: the sole artifact consumed by evaluation.
- `diagnostic.json`: the supplied checker's default public-pool assessment.
- `nominal_metrics.json`: complete nominal subset energies and signed increments.
- `resource_check.json`: the resource-bounded 128-case-per-family public assessment.
- `validation.json`: artifact hash, independent counts, and resource-check metadata.
- `scratch/`: construction scripts, search candidates, logs, and detailed checks.

Artifact SHA-256:
`d301ccf60516a7d4648e43db96461d476f005c8b8f28de5704c90f3d6d7bbd33`.
