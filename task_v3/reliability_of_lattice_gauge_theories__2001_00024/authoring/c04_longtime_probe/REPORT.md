# c04 late-time probe: completed, strict worker budget

**Disposition:** T=1000 is solved and is not a counterexample. T=10000 is a
validated **runtime counterexample to the unchanged initial submission**, not an
observed physics-accuracy failure. The efficient reference is validated and scores
1.000 on both. Retain this only as a candidate runtime lead pending selection;
no ratchet participant, new concept, or fresh agent was created.

All local paths in this report are relative to
`tasks_v3/reliability_of_lattice_gauge_theories__2001_00024/`.

## Final fair-run evidence

Calls use the landed common API
`run_solver(..., timeout=60, memory_gib=6, startup_grace=30)`. Worker wall alarm:
60 seconds; CPU soft/hard limits: 61/62 seconds. The parent's 90-second watchdog
only absorbs namespace startup. Each reference/submission pair used the same
single CPU affinity. Preliminary startup-inclusive runs remain in the parent
`runs/` directory but do not determine this conclusion.

| Case / solver | Worker seconds | Process CPU seconds | Parent wall seconds | Result / score |
| --- | ---: | ---: | ---: | --- |
| T=1000, accelerated reference | 1.040175 | 1.063661 | 1.357886 | success, 1.000 |
| T=1000, original submission | 13.866931 | 13.885598 | 14.296140 | success, 1.000 |
| T=10000, accelerated reference | 0.799293 | 0.821799 | 7.088689 | success, 1.000 |
| T=10000, original submission | 60.001431 | 60.190340 | 61.669691 | **worker timeout, 0** |

Decisive artifact:
`authoring/c04_longtime_probe/runs/strict_worker60_grace30/weak_brown_T10000_original.json:1`.
It reports `TimeoutError: case worker wall-time limit exceeded`, `timeout=true`,
and `failure_class=worker_wall_timeout`, not a parent/startup watchdog failure.
The corresponding `_cpu.json` independently sampled the Python worker in state R
with 60.15 CPU seconds and 69044 KiB RSS. The worker itself reports 60.190340 CPU
seconds and the same RSS, far below 6 GiB. Process CPU includes interpreter startup
before the worker's solve timer, explaining its small excess over timed wall.

The other exact run reports use the same directory and filenames
`weak_brown_T10000_reference.json`, `weak_pink_T1000_reference.json`, and
`weak_pink_T1000_original.json`; every successful output is retained in its
`_output.json`, and every run has `_cpu.json` samples and isolation-code hashes.

**Scoring qualification:** successful scores use the unchanged public component
formulas with the public positive anchor floors, against the independently
cross-checked target. These are conservative lower bounds for any valid
weak-baseline-anchored score, not newly fabricated official pool scores. No
late-time weak baseline or normalization was invented. The protocol assigns zero
to the timeout regardless of anchors. The solved T=1000 submission has maximum
scored-observable discrepancy 1.6502e-12; raw calibration/audit/dynamics errors are
9.2793e-22 / 2.6657e-29 / 9.8616e-26, and decision regret is zero. The timed-out
case returns no solution, so numerical component errors there are **unmeasured**.

## Cases and source-grounded physical regime

Inputs were fixed in `authoring/c04_longtime_probe/PLAN.md:1` before submission
runs. They are stored in `cases/weak_pink_T1000.json` and
`cases/weak_brown_T10000.json` under that authoring directory; generating parameters
and seeds are separate in `case_metadata/` and are not solver inputs.

| Parameter | T=1000 | T=10000 |
| --- | ---: | ---: |
| beta | 1 | 2 |
| generating amplitude | 2.5e-5 | 1.5e-5 |
| cutoff / floor | 0.45 / 0 | 0.45 / 0 |
| generating eta | 0.45 | 0.65 |
| lambda = sqrt(2.6/T) | 0.0509901951 | 0.0161245155 |
| amplitude*T/2.6^beta | 0.00961538 | 0.02218935 |

Dimension remains 64. Seven uniformly spaced times include zero and the stated
endpoint; the public contract specifies no Tmax. Actions, budget, initial state,
Hamiltonian coefficients, and independent audit bath are retained from the
prespecified base cases. Kappa is set to zero to remove actuator detuning as a
confounder. All public amplitude/cutoff/floor/eta bounds are respected, including
amplitude >=1e-5. Calibration retains the finite-band model, using fixed Gaussian
draws and stated positive sigmas. Reference outputs use the fitted bath, not the
generating parameters. No frequency convention or physical generator is changed.

Source basis: arXiv:2001.00024 Fig. 3 and the energy-protection discussion describe
observable drift near V/lambda^2 despite small gauge leakage; its methods paragraph
explicitly motivates direct exponentiation for extremely long simulations.
arXiv:2210.06489 Appendix B, Eqs. B1--B4, supplies the secular structure and the
protected early incoherent gamma*t/V^beta guide. These motivate the regime, not
exact prefactors in this modified model. Full PDFs:
`https://arxiv.org/pdf/2001.00024`, `https://arxiv.org/pdf/2210.06489` (12 pages).

The computed physics is not merely a large time argument with trivial dynamics.
For `flat_high` at the endpoint:

| Diagnostic | T=1000 | T=10000 |
| --- | ---: | ---: |
| noisy gauge leakage | 0.015972 | 0.082881 |
| noisy fidelity to intended dynamics | 0.368384 | 0.304024 |
| closed-system gauge leakage | 0.000346 | 0.00004066 |
| closed-system fidelity | 0.379334 | 0.391817 |

The closed-system values are an analytical diagnostic of the same Hs, not extra
scored cases. They demonstrate coherent fidelity loss while gauge leakage remains
small; the weak bath adds further errors. The objective remains the original
seven-sample trapezoidal objective, not a claim of converged continuous-time
averages over all fast oscillations. The unchanged fully secular, regularized
Markov model is being tested, not exact non-Markovian classical 1/f trajectories.

## Superior reference mechanism and validation

`pilots/c04_colored_noise/private/reference/longtime/accelerated.py:9` uses the
frozen engine's unchanged frequency-resolved generator. Its exact nonzero
connected components have maximum dimension 64, rather than exponentiating the
whole 4096-dimensional oscillatory Liouvillian. No additional matrix entries are
dropped. For each block, a scalar Bohr phase is removed before dense SciPy `expm`.
This centered-block method retains all within-block frequency differences.

A second propagator diagonalizes the Hermitian dissipator with `eigh` and applies
the Hamiltonian phases separately, guarded by measured Hermiticity and commutator
residuals. The two methods share the frozen generator, but independently evaluate
its exponential. This is a numerical reimplementation, **not official author
code**, a new master equation, or a hidden-model shortcut.

- Five short cases (three original families plus short versions of both probes)
  agree with the byte-identical original full-`expm_multiply` engine to at most
  1.399e-14 in scored observable channels. Evidence: `short_reference_checks.json`.
- For both full late cases, centered block `expm` and commuting `eigh` agree to
  2.411e-13 in scored channels (electric divided by two as in the public score)
  and 1.466e-13 in density entries. Offline centered propagation completes in
  1.816 seconds or less; the isolated reference uses the validated `eigh` path.
- Across all twelve late action trajectories and all seven samples: maximum
  trace error 3.553e-15, maximum Hermiticity error 7.195e-16, and minimum density
  eigenvalue -5.144e-15 (roundoff). No state renormalization or positivity clipping.
- With C=-i[Hs,.], maximum Frobenius norm of [D,C] is 4.828e-18. The largest
  T^2*||[D,C]||/2 indicator is 2.414e-10; the Hermiticity-defect-times-T indicator
  is below 2.899e-14. The discarded off-block norm is exactly zero.

Complete precomputed outputs, per-action diagnostics, independent-method errors,
and closed controls are in `authoring/c04_longtime_probe/labels/`. This validates
the accelerated reference before interpreting the candidate timeout. The initial
algorithm's full oscillatory `expm_multiply` call is at
`pilots/c04_colored_noise/attempt/solver.py:242`; the failure is a resource-bound
propagation limitation, not evidence of wrong inferred parameters or rates.

## Integrity, artifacts, reproduction

- Machine summary: `authoring/c04_longtime_probe/SUMMARY.json:1`.
- Orchestrator: `authoring/c04_longtime_probe/run_probe.py:195` records CPU and
  exact fairness parameters; `run_probe.py:122` performs reference cross-checks.
- The execution copy is byte-identical to the completed submission (SHA-256
  `fd39c5839fc836dc67761970a0657528b012d01e44119d6544c379d6835b33c4`).
  `original_submission/` is staging only, not a new participant or edited solver.
- `source_hashes.json` verifies both copied sources; `protected_integrity.json`
  verifies originals unchanged; `frozen_manifest_integrity.json` verifies **all
  67 original frozen hashes**. Only the two authorized new directories were written.

From the task root, reproduction is:

```
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python authoring/c04_longtime_probe/run_probe.py --phase prepare
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python authoring/c04_longtime_probe/run_probe.py --phase evaluate --startup-grace 30
```

No additional evaluation is needed for this disposition. No original task,
attempt source, evaluator, pool, or c02/c03 artifact was changed.
