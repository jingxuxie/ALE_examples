# Qualified open-system dynamics service

Run from the submission root:

```sh
bash run.sh solve input/noisy_gate.json scratch/gate --config production
bash run.sh solve input/spectroscopy_spin.json scratch/spin --config refined
bash run.sh solve input/coupled_spins.json scratch/local --config ablation
bash run.sh campaign input regenerated
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python workspace/validate.py regenerated
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python workspace/audit.py regenerated
```

The wrapper also works from within `workspace/`. Input NPZ paths resolve relative
to the supplied JSON, not the working directory. No quantum package is needed.
The dependencies are Python 3, NumPy, SciPy, Pillow, and psutil. Tests use unittest
and also execute the two original lightweight checks; pytest is optional.

## Models

- `lindblad`: explicit absolute-time controls; collapse coefficients are complex
  amplitudes, squared in the dissipator. DOP853 splits all step edges and resolves
  Gaussian pulses. Structured operator actions avoid large dense Liouvillians.
- `redfield`: static Born–Markov generator with no Lamb shift. Nonsecular terms
  are retained unless `secular` is true. Equal-frequency transitions interfere
  within each bath; independent baths never merge.
- `floquet`: fully secular physical-frequency Floquet–Markov generator, including
  drive sidebands, diagonal dephasing, coherences, and laboratory micromotion.
  One-period integration and small matrix exponentials avoid long-time ODE work.

All states return in the supplied laboratory basis. Process outputs use column
vectorization and an unnormalized, input-first Choi matrix. No state or process
output is positivity-projected or trace-normalized.

## Configurations

`production` uses tight ODE tolerances and adaptive harmonic refinement. `refined`
tightens the state tolerances 100-fold and the unitary/harmonic tolerances.
`ablation` retains accurate integration but uses the original Hermitian local
noise approximation for spectral jobs, or unsquared collapse amplitudes for
explicit-collapse jobs. It is a deliberate alternative equation, not a cheaper
implementation of the production equation.

The harmonic refinement cap emits a warning and records a false convergence flag
if reached. Fixed-cutoff controlled runs record generator delta -1 (unmeasured).
Large density-matrix absolute tolerances are scaled by Hilbert dimension to
control aggregate Frobenius errors rather than just per-entry RMS errors.

## Evidence and timing

The campaign regenerates the main, ablation, cutoff/resource, and controlled
tables; raw runs and their executable input manifests; table-derived figures;
claims; validation results; and the report. Each case is solved in an isolated
worker with a 60-second campaign watchdog. Solve timings exclude startup and
serialization. RSS is sampled every 2 ms through the run, including serialization.
The audit recomputes table diagnostics and distances, checks process conventions,
and evaluates every machine-readable claim.

`resource_check.py DESTINATION` reruns the archived large-basis tolerance/step-size
calibration. `baseline/` and `revision/` in the submitted output preserve historical
evidence; they are not imported by the repaired solver. The detailed scientific
interpretation, limits, and measured results are in the generated `report.md`.
