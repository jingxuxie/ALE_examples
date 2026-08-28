# Qualify a migrated open-system dynamics service

You are taking over a numerical-physics service before a release. Its migrated
experiment pipeline runs, but agreement between local-noise and microscopic-bath
simulations is suspiciously good, some results depend on representation, and
the large resonator jobs no longer meet the workstation resource envelope.
Decide which discrepancies are real physics and which are implementation or
convergence errors. Repair or replace the relevant components, then submit an
executable, evidence-backed qualification of the service.

The service supports prescribed time-dependent collapse operators, static
weak-coupling spectral baths, and periodically driven weak-coupling spectral
baths. These are different physical contracts, not interchangeable numerical
settings. The migration currently routes all three through a local-noise
approximation. The process-channel output has its own representation boundary.
The supplied code is a benchmark-authored migration of a scientific simulation
workflow, not an upstream release. You may replace components and use any
available numerical method; preserving this implementation is not a goal.

## Assets and scope

- `input/CONVENTIONS.md` defines physical meaning, input arrays, and output basis.
- `input/*.json` and matching NPZ files are six unlabeled development experiments.
  They include driven spin and multilevel spectroscopy, collective and coupled
  baths, a pulsed thermal resonator, and a noisy two-qubit gate.
- `workspace/oqs/` separates input/coefficient handling, bath models, propagation,
  process representation, diagnostics, and experiment aggregation.
- `workspace/configs.json` contains production, ablation, and refinement settings.
- `workspace/tests/` contains only tiny checks, not main-case expected outputs.
- `workspace/cli.py` can run individual cases or a campaign. The plotting helper
  uses Pillow so no plotting-package installation is necessary.

Run the supplied baseline before changing it. Use useful diagnostics, including
limits, representation equivalence, convergence, and experiments distinguishing
local-noise assumptions from microscopic dissipation. Do not treat trace,
Hermiticity, or positivity alone as evidence that a model is correct. A
nonsecular Redfield evolution need not be completely positive; silently
projecting its outputs changes the scientific question.

The scientific outcome is a defensible answer to: **when do model choice and
numerical implementation each explain the observed discrepancy, and how much
does reliable treatment cost?** Your ablation must test a meaningful physical
or numerical decision, not merely change an output label. Include a refinement
study and a size/resource study. Record at least one run/inspect/revise/rerun
cycle in the report, including the evidence that motivated the revision.

## Submission

Work in the provided writable output directory. Copy the workspace there before
editing; do not rely on modifications to the input task. Deliver:

```
output/
  workspace/           repaired standalone executable system
  run.sh
  results.csv
  ablation.csv
  scaling.csv
  runs/                per-case NPZ arrays and metadata underlying the tables
  figures/primary_result.png
  figures/robustness_or_scaling.png
  claims.json
  report.md
```

`bash run.sh solve CASE.json DESTINATION --config production` must load an
arbitrary supported manifest and write `DESTINATION/result.npz` and
`DESTINATION/metrics.json`. The same command must accept `ablation` and `refined`.
`bash run.sh campaign INPUT_DIRECTORY OUTPUT_DIRECTORY` must regenerate the
tables, raw runs, figures, and claims using the submitted code/configuration.
The supplied CLI implements these interfaces; you may retain it or replace it.

The NPZ contains `times`, `states` (time, laboratory row, laboratory column),
`expectations` (time, observable), and, for process jobs, `channel` and `choi`
at the last requested time. Do not normalize a channel as if it were a state.
The campaign helper documents table and claim fields through executable code.
Tables must agree with rerun arrays. Figures must be regenerated from tables;
claims must identify table rows and testable comparisons. Explain limitations,
not just favorable comparisons. A scientifically negative result is acceptable.

## Environment and evaluation

Python 3, NumPy, SciPy, Pillow, pytest, and psutil are installed. Internet access
and other task folders are unavailable. No external quantum package is needed.
Use one BLAS thread for reproducible timing. The screening attempt has one hour;
this is not the solver's physical-time horizon or a mandate to stop early.

Unseen cases use exactly the documented schema and six development physics
categories, with changes in drive waveform, spectrum, coupling geometry,
degeneracy, initial coherences, absolute starting time, basis, and scale.
Hilbert dimensions range from 2 to 112; only resonator explicit-collapse jobs
use large dimensions. Spectral jobs are at most dimension 6, gate channels
at most dimension 4. Output grids may be nonuniform. Periodic spectral jobs
can span thousands of periods; a final state alone is insufficient.

Evaluation is method-agnostic: full laboratory-state and process-channel
accuracy (aim for roughly 1e-5 absolute state/channel Frobenius error),
worst-family reliability, continuous runtime/memory efficiency, and
recomputed evidence. Near-reference accuracy receives more credit than merely
plausible curves. Each solve has a 60-second/1.5-GiB workstation envelope,
with speed and memory rewarded continuously within that envelope; a converged
implementation can finish the complete small screening suite within minutes.
Documentation or figure polish cannot compensate for an incorrect simulator.
