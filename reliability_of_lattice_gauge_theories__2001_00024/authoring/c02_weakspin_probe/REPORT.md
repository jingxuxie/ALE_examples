# c02 weak-spin probe: closed without a validated counterexample

## Disposition

**Neither proposed reference label is validated. No participant grading was
performed, and these results provide no participant-failure or hardness
evidence.** Both physically admissible cases fail the unchanged normalized
reference-convergence gate of 0.97. The existing T10 fine job completed normally;
there are no remaining probe jobs. No 384-bond refinement, participant call,
fresh agent, or ratchet was launched.

Main reports that all 15 original fresh cases completed, with screening
mean/worst-family 0.9996068118 / 0.9992930262 and challenge
0.9997763208 / 0.9996915405. Those are main's results, not reruns by this probe.
The unvalidated sidecar does not overturn that solved evidence.
The regime is source-grounded, but no private-reference-quality advantage over
the participant has been established on these harder cases.

## Frozen construction and reference gate

Both cases reuse `make_case(18334, "inhomogeneous_weak", 0)`, including its
calibration experiments, private true parameters, inhomogeneous profile, and
observable pairs. The prediction experiment changes to spin one at L=32:
V=0.5 through T=8, or V=1 through T=10. Both pass the recorded public-contract
checks. Their source-grounded construction and author-reimplementation
provenance remain in `README.md` and `manifest.json`. This is not an official
paper or software bug fix.

Case inputs, true parameters, original-submission snapshot, source hashes, and
reference settings were frozen before any candidate evaluation. No case was
retuned after observing results. References use the existing charge-conserving
`charge_engine.predict`, with fourth-order evolution: coarse step 0.1 / bond 96 /
cutoff 1e-9, versus fine step 0.05 / bond 192 / cutoff 1e-12.

For each dynamical output block, the convergence diagnostic exponentiates the
maximum absolute coarse/fine difference divided by the existing weak-baseline
scale. The fourth-root product includes an exact parameter component of one.
This is a numerical convergence diagnostic, not a rigorous exact-solution bound.

| Candidate | Normalized max-difference diagnostic | RMS geometric comparison | Physical checks | Accepted |
|---|---:|---:|---|---|
| V=0.5, T=8 | 0.888478489755398 | 0.9652107438860102 | false | **no** |
| V=1, T=10 | 0.7897868202677478 | 0.9394693065086372 | false | **no** |

| Candidate | Max density difference | Max violation difference | Max correlation difference |
|---|---:|---:|---:|
| V=0.5, T=8 | 0.015815191111453 | 0.004981442562523 | 0.001033211884954 |
| V=1, T=10 | 0.026093158242730 | 0.014435639715131 | 0.001715099626334 |

Both fine runs retain algebraic MPS sector Q=0 and a zero Hamiltonian
charge-commutator residual. Their returned density sums nevertheless have
maximum absolute alternating-sign Q residuals 4.598802116184686e-5 and
9.081781874265005e-5, respectively, exceeding the sidecar observable-charge check
of 1e-8. This is a readout-consistency concern, not evidence of actual physical
charge breaking. The normalized convergence gate fails independently of it.
The T10 fine run is a successful computation of an **unvalidated** target, not
an accepted reference merely because its process exited normally.

## Canonical-readout finding and remaining state error

The one additional bounded diagnostic reran only the frozen coarse T8 evolution.
At every requested measurement time it copied the MPS, called
`canonical_form(cutoff=0)` on the copy, and measured the copy. The evolving state
was never replaced or canonicalized. The source engine remained unchanged.

At T=8 the direct coarse maximum `norm_test` entry was 1.420340495060673e-4;
on the canonical copy it was 2.801711029165142e-15. The summed Q changed from
-2.9228061843511455e-4 to -3.552713678800501e-15. Across all times the largest
post-canonicalization absolute Q residual was 1.687538997430238e-14.

The evolving tensor/singular-value fingerprints matched before and after
every copy measurement. Copy bond sizes were unchanged. All direct output
arrays reproduced the original coarse reference **exactly**, and accumulated
discarded weight remained exactly 0.2109619011385299. This establishes a
canonical-environment measurement artifact on the same truncated coarse state,
not charge breaking or altered dynamics. The installed TeNPy API provenance and
copy/canonicalization semantics are documented in `CHECKPOINT.md`.

Maximum readout changes were density 1.4916647017010343e-4, violation
8.243987525458074e-5, and correlation 1.7420098669618245e-5. These are respectively
0.9432%, 1.6549%, and 1.6860% of the original blockwise coarse/fine maximum gaps.
Thus the measured coarse-side repair does not close the reference gap or repair
the already truncated state. Fine canonical readout was not tested. Because
both timestep and bond cap changed between reference levels, the remaining
state-approximation gap is not separated into bond truncation versus time
discretization. No corrected convergence claim is inferred from the diagnostic.

## Observed author costs

| Run | Wall seconds | CPU seconds | Peak RSS KiB | Accumulated discarded weight |
|---|---:|---:|---:|---:|
| T8 coarse | 251.466251 | 251.265845 | 270400 | 0.210961901 |
| T8 fine | 2496.605652 | 2343.326035 | 328436 | 0.034092589 |
| T10 coarse | 350.840968 | 351.137843 | 269332 | 0.626892171 |
| T10 fine | 3958.553289 | 3042.778777 | 332456 | 0.165480730 |
| T8 copy-only coarse diagnostic | 234.291844 | 235.033592 | 271384 | 0.210961901 |

All reference runs reached their bond cap. They ran concurrently, so their wall
times are not additive elapsed turnaround. These are author-reference costs,
not participant runtimes or timeouts. The diagnostic had a 900s wall cap and
completed normally. The earlier T8-only 384 / 0.025 cost projection of roughly
5.5–11.1 hours was an untested scaling estimate; no such refinement ran.

## Evidence, integrity, and closure

- `SUMMARY.json` records final machine-readable outcomes, measurements, audits,
  hashes, and integrity checks. Earlier checkpoint files remain historical.
- `references/<case>/coarse.json` and `fine.json` retain full raw predictions;
  `convergence_coarse_fine.json` retains all normalized components and scales.
- `diagnostics/canonical_coarse_T8/result.json` and its per-time JSONs retain
  full direct/copy predictions, `norm_test`, Q, and tensor fingerprints.
- Frozen source, original submission, copied submission, and case hashes were
  rechecked at closure and match. All writes are inside this probe directory.
  Original engines, public contract, attempt, pools, and frozen labels were not
  modified by this probe; no original evaluation was duplicated.
- There are **zero accepted-reference files and zero participant evaluations**.
- Reference parent session **9140** returned exit 0 after the existing T10 child
  (host PID 3382962) finished. Copy diagnostic session **41310** returned exit 0.
  No further job remains active and no further run is planned.

**Closure recommendation:** reject these candidate labels at the measured
reference quality; record the lead as reference-inconclusive, not as a failed
participant or a justified ratchet. Keep the original solved disposition.
