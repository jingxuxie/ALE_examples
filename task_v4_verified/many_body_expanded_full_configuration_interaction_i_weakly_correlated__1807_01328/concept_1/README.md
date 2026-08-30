# Retained active-experiment task

**Status: hard_verified_achievable. Generation 2; one ratchet.**

The canonical `participant/` and `evaluator/` are byte-identical copies of the
selected generation under `adversary/ratchet_1/`. Only the canonical lifecycle
metadata is current; the versioned packet's frozen status records prelaunch
readiness. The original generation remains in `champions/generation_1/` and
`adversary/canonical_history/generation_1/`.

## Evidence

All errors below are RMSE in microhartree on the fixed 120-system generation-2
suite. Targets are at most **10 overall and 25 in every stratum**.

| Artifact | Overall | Worst stratum | Aggregate CPU | Passed |
| --- | ---: | ---: | ---: | --- |
| Supplied weak baseline | 58.0536 | 116.7488 | 0.24 s | No |
| Original fresh champion | 49.4178 | 113.0614 | 104.07 s | No |
| Fresh generation-2 attempt | 18.1089 | 31.7704 | 104.06 s | No |
| Privileged passing policy, main replay | 7.8011 | 14.8330 | 61.40 s | Yes |

The fresh attempt uses its complete one-hour construction budget and produces
a runnable, protocol-valid, resource-valid policy. It improves the baseline
substantially but misses both accuracy requirements; the mixed stratum is its
worst. Failure is not inferred from construction timeout or wall-clock noise.
An independent replay through the promoted canonical evaluator again fails:
18.1165 overall and the identical 31.7704 worst-stratum RMSE, CPU 104.18 s.
The private passing policy also passes a separate untuned 120-case holdout at
6.2062 overall and 11.3977 worst-stratum microhartree. Its runtime reads only
observations, permitted query responses, and submitted model files. Main's
code/provenance review is in
`adversary/ratchet_1/adversary/portfolio/MAIN_REVIEW.md`.

The substantive challenge is accurate adaptive CAS-tail estimation under
signed cancellation and heterogeneous correlations within fixed query and
aggregate CPU budgets. These are effective seniority-zero Hamiltonians, not
ab initio molecular FCI. The conditioned cases and holdout include two
seed-derived neighborhoods; no universal or IID-population guarantee is made.

## Participant boundary

Expose **only `participant/` read-only and a separate initially empty writable
attempt directory**. Every other path is privileged, especially prior attempts,
hidden Hamiltonians/energies, this README/status, and the known passing policy.
Use the supplied allowlisted runner through the root `research/launch.py`.

## Privileged reproduction

Run from this concept directory with Python 3, NumPy, SciPy, and bubblewrap
namespace permissions. No participant code receives hidden filesystem access.

```bash
OPENBLAS_NUM_THREADS=1 python -B evaluator/evaluate.py --submission participant/baseline --output /tmp/c1_baseline.json
OPENBLAS_NUM_THREADS=1 python -B evaluator/evaluate.py --submission attempts/v_2 --output /tmp/c1_fresh.json
OPENBLAS_NUM_THREADS=1 python -B evaluator/evaluate.py --submission adversary/ratchet_1/adversary/portfolio/candidate_a --output /tmp/c1_passing.json
python -B adversary/ratchet_1/evaluator/verify_freeze.py
```

The full historical freeze is checked at the immutable versioned packet, not
against current canonical lifecycle metadata. Aggregate limits are CPU 120 s,
wall 600 s, memory 2 GiB, submission 128 MiB, and query 160 per system. The larger
wall allowance was declared before generation-2 launch; accuracy, CPU, query,
and memory targets were not relaxed.
