# c02 completed pilot: solved initial task, unvalidated harder probes

## Actual fresh-agent results

The requested ultima-alpha attempt completed normally in 2938.705 seconds, with
the participant tree unchanged. All fifteen original scientific evaluations
completed within the published 3600-worker-second, one-CPU, 6-GiB budget.

| Split | Cases | Mean core | Worst family | Minimum case |
| --- | ---: | ---: | ---: | ---: |
| Screening | 6 | 0.9996068118 | 0.9992930262 | 0.9989475332 |
| Private challenge | 9 | 0.9997763208 | 0.9996915405 | 0.9993176071 |

The weakest screening component mean is violation, 0.9991005265; the weakest
challenge component mean is violation, 0.9994842748. No central component is
unsolved. Screening calls take 361.784--3126.748 worker seconds; challenge calls
take 102.328--2173.815 seconds. Maximum RSS is 812,816 KiB, below the limit.
These are actual isolated measurements, not the submission's own test claims.

## General method and valid reference

The submission combines noise-weighted bounded calibration fits, exact small
clusters, and parity-blocked canonical MPS for the full supplied chain. It uses
fourth-order sweeps, intact Gauss-square splitting, randomized SVD, and measured
cost-based bond adaptation. Observables are contracted from the evolved state;
there is no spatial tiling, case-ID lookup, external reference read, or missing
output scaffold. A single parameterized implementation covers all evaluated
valid physical families. Dense-state memory limits are real, but the fresh agent
successfully constructs an appropriate specialized method within one hour.

All 21 initial reference records are frozen. Their independent coarse/fine
normalized comparison diagnostics are at least 0.9822817945; all density,
positivity, covariance, and alternating-charge checks pass. The maximum charge
residual is 6.1394e-9. Small exact checks and a large cross-library comparison
provide additional evidence. Oracle self-scores of one are only interface checks.
Measured weak means are 0.1018091323 on screening and 0.1014664873 on challenge.

## Counterexample search and disposition

The natural additional direction is weak-protection spin-one dynamics at L=32,
T=8--10, rather than the initial strongly protected spin-one family. Cases were
frozen before attempting to score the completed submission. Existing tensor
software generated coarse/fine references, but their conservative convergence
diagnostics are only 0.8884784898 and 0.7897868203, below the precommitted 0.97
validation gate; observable-charge checks also fail. No submitted solution was
graded against these labels, and no participant failure is inferred from them.

A copy-only canonical-measurement diagnostic repairs the coarse readout's charge
identity without changing the evolving state, but explains only a small fraction
of the coarse/fine differences. State-truncation convergence remains unresolved.
Larger, unvalidated author computations are not silently substituted for an
established privileged solution. Details and raw arrays are in
`authoring/c02_weakspin_probe/`.

**Disposition: reject c02.** The validated original task is robustly solved; the
harder transfer region lacks a validated private reference and therefore does
not establish an eligible solution gap. No c02 ratchet or second fresh attempt
is justified by these data. This is not a claim that all possible many-body
regimes are easy.
