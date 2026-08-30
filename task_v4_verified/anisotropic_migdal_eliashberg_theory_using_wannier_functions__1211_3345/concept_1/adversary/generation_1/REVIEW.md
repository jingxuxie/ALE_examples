# Generation 1: ready for parent review, inactive

The pending task is `package/concept_1/`, relative to this directory. Its sibling
`package/authoring/sandbox_runner.py` is included at the evaluator's unchanged
relative location. No active task files were overwritten and no new fresh-agent
trial was launched. Activation remains a parent decision.

## Privacy and fixed objective

The participant receives only the original public damped baseline and supplied
physics operator, plus documentation and public inputs. No previous fresh code,
reference solution, or private label is shipped. The actual successful fresh
solver is archived verbatim at `../../champions/generation_1/`, outside the
participant package, and is adversarial evidence rather than the public anchor.

The objective is fixed: core score at least **0.90** (18/20), worst-family score
at least **0.75** (3/4 in every family), and worst-family improvement at least
**0.25** over the original public baseline. That anchor is **0.00**, so the
improvement threshold is feasible. Each case must satisfy normalized gap
residual **2e-8**, Z residual **2e-9**, full-frequency per-patch branch distance
**0.002**, and correct low-frequency relative signs, up to one global sign.

Resources remain **12 parent-measured child CPU seconds**, **2048 MiB** address
space, **one process and one thread**, and an **1800-second wall safety ceiling**
per invocation. There is no wall-speed score. Output allowance is now 32 MiB
because two 40-by-32768 float64 arrays legitimately exceed the old 16 MiB limit.

## Measured evidence

| Solver | Accepted | Core | Worst family | Target |
| --- | ---: | ---: | ---: | --- |
| Original public baseline | 10/20 | 0.50 | 0.00 | Fails |
| Actual previous successful fresh | 16/20 | 0.80 | 0.50 | Fails |

The broader 12-case original/4096/8192 pool was insufficient: the actual fresh
solver passed every case. The pending suite retains 16 original cases and
replaces two critical and two combined instances. Every replacement is an
independently anisotropic 40-patch, 32768-frequency material with
Omega_max/T = 12000, upper frequency/Omega_max = 17.157, four positive modes
spanning 1000 or 4000, and a normal pairing eigenvalue of 1.00003 or 1.0001.
These are exact finite-cutoff synthetic materials, not ab initio mesh-convergence
claims or duplicated-patch padding. Combined cases have induced-gap ratios
above 1e7. Full generation parameters and fixed seeds are private and recorded.

| Replacement | Family | Extended identical-fresh CPU seconds |
| --- | --- | ---: |
| case_08 | critical | 51.70 |
| case_09 | critical | 40.50 |
| case_16 | combined | 94.79 |
| case_17 | combined | 49.70 |

All four fail again under the actual 12-CPU policy. Extended runs use the same
solver and memory limit, not an adapted algorithm, and return accurate outputs.
The failure cluster is repeated dense patch-pair/frequency work plus nonlinear
scale sensitivity at low temperature, not paths, output shape, or wall jitter.

Each new reference has two starting-amplitude checks, all-frequency residuals
from an independently written full-signed linear convolution, and independent
direct signed sums on distributed rows. The convolution is also checked against
full direct sums on small grids. Maximum new reference gap residual is
1.51e-13; maximum new cross-start branch discrepancy is 5.69e-10. The hardest
combined reference additionally uses a separately authored eigenmode/Newton
oracle. Offline probe/reference work totals 1025.23 CPU seconds. These are
quality certificates only: **joint 12-CPU attainability is not established**.
Difficulty status remains provisional until the parent runs the new fresh trial.

## Audits, archive, and handoff

- 23/23 tests pass: 12 physics/package/privacy tests and 11 sandbox/output tests.
- Exact normal solutions, missing weak gaps, and relative-sign errors fail.
- Private reads, network, processes, and threads are denied; output symlinks,
  hardlinks, object arrays, oversized headers, and expanded-NPZ bombs are rejected.
- `package/concept_1/evaluator/hidden/prelaunch_seal.json` seals 92 files,
  including participant TASK, baseline, policy, references, reports, and runner.
- `generation_0_runnable_snapshot.tar.gz` contains `concept_1/` and sibling
  `authoring/sandbox_runner.py`; all original bytes match its manifest. The
  archived evaluator successfully runs its public baseline on case_00.
- `ratchet_evidence.json` contains structured private evidence; pending status is
  `package/concept_1/status.json`. Detailed reports are in pending `attempts/`.

Recommend **3600 seconds for the next fresh trial**, plus **900 seconds typical
evaluation allowance** on the loaded host; retain CPU-based case limits and the
generous per-case wall ceiling. Measured full evaluations took 78.35 seconds
(public baseline) and 60.63 seconds (previous fresh) on this host. Do not activate
or launch until parent review; do not copy the private champion into participant.
