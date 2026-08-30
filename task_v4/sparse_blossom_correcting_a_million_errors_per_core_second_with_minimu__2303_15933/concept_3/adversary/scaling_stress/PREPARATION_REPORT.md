# Private large-active-graph preparation, not a new generation

Prepared August 28, 2026, during the bounded resumed sidecar window starting
17:41:15 UTC. All jobs finished before this report. No fresh agent was launched,
no pending v2 submission was inspected, and no task, target, episode, or status
was changed. Original participant/evaluator files are checksum-checked against
`frozen_snapshot.json`. Supplementary results do not turn official v1 into a pass.

## Conclusion

There is a measured dense-outcome representation failure, separate from the
original noisy bulk-family failure. Both byte-identical first-frozen and robust
reference policies run on the original small instance, but exhaust the 3 GiB
address-space allowance on connected 16/18/20-detector ladder instances. At 18
and 20 detectors they fail before requesting any shots, so dense response JSON
cannot explain those failures. A latent-blind local composite-likelihood control
recovers all 12 larger instances with 40,000 shots and at most 2.403 CPU seconds.
Thus these cases are not evidence that calibration itself requires exponential
resources, nor evidence of a hard-open problem.

## Models and scientific checks

`cases.py` constructs ladder, patch, and triangular connected sparse graphs at
14, 16, 18, and 20 detectors. The respective channel counts are:

| Detectors | Ladder | Patch | Triangular |
| --- | --- | --- | --- |
| 14 | 43 | 45 | 52 |
| 16 | 49 | 53 | 59 |
| 18 | 55 | 59 | 69 |
| 20 | 62 | 68 | 77 |

Every detector participates in actual fault channels; the least expected detector
click count under uniform 40,000-shot exposure is 1,147.27. Maximum graph degree
is six. Each channel's primary/alternate union has graph diameter at most two;
local inference patches have at most four detectors. These are not padded or
disconnected copies of the original small problems.

The synthetic mechanism retains shared unobserved hot/cold shot mode,
action-dependent exposures and categorical alternate footprints, overlapping
channels, XOR syndromes, positive rates, and primary-footprint aliases broken by
interventions. It is an explicit synthetic benchmark, not a physical-device
claim. Both the direct Bernoulli-parity and independent Poisson-parity samplers
were compared against analytical moments. Independent local XOR-convolution PMFs
and finite-difference derivatives also agree; see `science_report.json`.

All 12 local-parity log-rate Jacobians have full column rank (43 through 77).
Reference-only rank is deficient by four or five, demonstrating a genuine need
for interventions. This establishes local identifiability, not a theorem of
global uniqueness over the entire parameter box.

`information_report.json` uses the exact within-shot covariance of all selected
parity features, including overlapping supports and shared-mode correlations.
It does not incorrectly add marginal Fishers as if patches were independent.
All information matrices are full rank: minimum eigenvalue 4.01785, maximum
condition number 160.923. The minimum feature-covariance eigenvalue is 0.000308629,
so the numerical floor of 1e-10 is nonbinding. Under uniform 40,000-shot exposure,
the largest asymptotic family log-standard-deviation across cases is 0.164450.
This is optimal-moment asymptotic information, not full-likelihood Fisher, a
finite-sample guarantee, or a latent-blind solution witness. The executed local
control supplies separate empirical achievability evidence.

## Unchanged dense policy controls

`controls.py` creates a separate exact-leaf runtime copy for each policy/case.
Sources are hashed before and after. The first-frozen source SHA256 is
`7c1d6f3f3d69c4a6a6b8595f2ee95fb8590b27d330a5197b26e29d12a08c8a69`.
The robust source is `adversary/portfolio/reference/solution.py --policy robust`.

| Ladder size | First frozen | Robust reference |
| --- | --- | --- |
| 14 | Nonzero exit, 59.376622 CPU s; 40,000 shots | Nonzero exit, 59.363003 CPU s; 4,640 shots |
| 16 | Allocation failure, 2.383931 CPU s; 910 shots | Allocation failure, 28.733521 CPU s; 4,640 shots |
| 18 | Allocation failure, 1.291100 CPU s; zero shots | Allocation failure, 3.262241 CPU s; zero shots |
| 20 | Allocation failure, 7.385739 CPU s; zero shots | Allocation failure, 2.038080 CPU s; zero shots |

At D20, each constructor requests a float64 array `(33,62,1048576)` of
15.984375 GiB. D18 requests `(29,55,262144)`, 3.115234375 GiB, before accounting
for other arrays. D16 fits/Fishers require 1.24/1.39 GiB temporaries in addition
to the already-resident dense tables. This is the concrete `actions * channels *
2**detectors` allocation bottleneck. The two D14 exits occur near the CPU limit,
but the bridge did not preserve the solver's terminating signal: the reports
correctly retain `worker_nonzero_exit`, not a definitively diagnosed CPU failure.
No accuracy is assigned to invalid runs.

Original D6 protocol sanity runs are valid for both controls. The first-frozen
original episode reproduces the official per-family squared errors exactly,
including the original bulk error. This tests compatibility, not a new pass.
Detailed stacks and metrics are in `runs/first_frozen_control_report.json` and
`runs/robust_control_report.json`.

## Runnable scalable accuracy controls

Both controls in `workers/baselines/solution.py` use only public specifications
and received syndromes; no true rates, model-generation seed, or scoring result
is available to them. Each uses all 40,000 shots, 29 or 33 queries, and the same
limits. `--policy prior` deliberately ignores observations at estimation time.
`--policy composite` fits exact small-patch marginal distributions while
retaining the shared-mode mixture in each marginal. Overlap makes the estimator
composite likelihood rather than the full joint likelihood.

Aggregate metrics below first RMS over the four sizes within each
topology/family cell, then average/max the 12 cells; no thresholds are applied.

| Control | Mean cell log RMSE | Worst cell | Worst single case/family | Max CPU s |
| --- | --- | --- | --- | --- |
| Prior midpoint | 1.084185345 | 1.893696469 | 2.250198122 | 0.706362 |
| Uniform local composite | 0.092506640 | 0.121211766 | 0.188256733 | 2.402012 |

All 24 runs are valid. Maximum single-case mean for the composite control is
0.125442759. Largest observation message is 11,647 bytes. Reports are
`runs/resumed_prior_report.json` and `runs/resumed_composite_report.json`.
These are one private parameter/noise fixture per size/topology, not repeated
held-out qualification. The control is feasible empirical evidence, not a
predeclared official passing portfolio.

## Protocol, secrets, isolation, and runtime

Queries and final rates use the original JSON-lines protocol and budgets:
40,000 shots, 64 queries, at most 4,000 shots/query, 60 CPU seconds, 3 GiB
address space, 900-second wall watchdog plus 300-second initialization allowance.
The parent sends a lossless sparse histogram (syndrome codes and multiplicities)
instead of a giant dense list. For unchanged controls,
`worker_support/legacy_bridge.py` restores the original protocol identifier and
dense `counts` list *inside the isolated worker*. The worker itself therefore
sees its original API. For native local controls the sparse wire is explicit.
This is a proposed representation change for a future task, not a silent change
to the frozen evaluator.

Parent rates and seeds are outside all worker mounts. The trusted parent never
imports participant code. `run.py` uses the frozen evaluator's bwrap command and
authenticated CPU supervisor, adding only read-only mathematical support at
`/stress_public`. System roots and original participant are read-only, proc is
private, tmp is tmpfs, and only the exact runtime submission leaf is writable.
Private `cases.py`, reports, candidates' siblings, and scoring data are not
mounted. The supervisor includes bridge and solver-descendant CPU usage.

Dependencies remain `/usr/bin/python3`, NumPy and SciPy from
`/usr/lib/python3/dist-packages`, and `/usr/bin/bwrap`; no sklearn/torch required.
Run the private native baseline from an escalated isolation-capable parent:

```
/usr/bin/python3 adversary/scaling_stress/run.py --submission adversary/scaling_stress/workers/baselines --output adversary/scaling_stress/runs/new_control_report.json -- /usr/bin/python3 /submission/solution.py --policy composite
```

Paths in this command are relative to `concept_3`. Do not expose this private
harness to fresh participants. An eventual public development tester must use
ordinary subprocesses on public examples, not nested bwrap.

## Proposal and limits: await actual v2 score

If v2 actually passes, run its frozen unmodified policy on these controls before
deciding on any ratchet. The demonstrated root cause is global dense likelihood
and Fisher enumeration; a substantive extension would require local inference
on connected detector graphs while preserving correlated channels, action
selection, and regime/family recovery. It is not merely changing an A-optimal
design constant. Sparse observations avoid an artificial exponential I/O tax.

A conservative *exploratory* mean/worst accuracy envelope of 0.15/0.25 appears
statistically plausible here, but the uniform composite control already clears
it on this fixture. Those numbers are neither proposed frozen targets nor a
claim of a hard task. Publishing that control with such targets would produce
a solved starter. Conversely, there is no evidence yet that original 0.055/0.095
targets are feasible on these larger cases. Do not copy them blindly or call
the problem hard-open because dense controls fail.

Before any authorized generation: independently resample parameters and noise,
test the actual champion, qualify a latent-blind efficient portfolio under the
same budget, and measure a real active-design advantage over uniform local
fitting. If that gap is absent, do not promote this as an active-design task.
No generation, freeze, official qualification, or change to original status is
performed by this preparation.
