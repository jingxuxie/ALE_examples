# Acceptance investigation: phase-engineered rotating superfluids

## Commission

Our group is migrating a GPU/MATLAB vortex-lattice workflow to an offline CPU
environment. The current port runs, but its plots are scientifically suspect:
removing a phase singularity sometimes looks like removing atoms; sound is
reported as extra vortices; and the lattice-order measurement changes much less
than the density images suggest. We cannot tell whether the intervention physics,
the integrator, or the measurements are responsible.

Take ownership of the migration. Deliver an executable, numerically validated
system and an evidence-backed assessment of this question: **does a localized
phase erasure preserve bulk orientational order better than reversal or removal
of a seven-core cluster, over the supplied observation window?** Do not force a
preferred answer. Separate genuine dynamics, finite-window limitations, and
measurement/numerical artifacts. A correct short-time result does not establish
indefinite vacancy stability.

The supplied campaign contains control, one-core erasure, circulation reversal,
and cluster erasure from the same relaxed rotating state. An isolated-condensate
calibration lets you investigate density healing and sound without lattice
geometry. You must also make the system reliable for additional initial states
with a rectangular driven elliptic trap, an annular current, and separated bulk
domains. These are acceptance/transfer cases, not additional target conclusions.

## Available workspace

- `workspace/`: runnable but scientifically inadequate CPU migration. The file
  boundaries separate geometry/units, propagation, cores, order, current, and
  experiment recording. Repair or replace components, not just the plots.
- `input/campaign.json`, `input/calibration.json`: experiment manifests.
- `input/*_state.npz`: independently prepared, normalized complex initial states;
  these are reconstructed numerical data, not archived experimental measurements.
- `input/CONTRACT.md`: physical and measurement contract, including array axes.
- `input/upstream/`: selected unchanged GPUE source artifacts and its license.
  They document the migration's ancestry, **not a tested answer**. In particular,
  historical scripts may disagree internally and assume obsolete environments.
- `workspace/diagnose.py`: partial diagnostics independent of reported tables.
- `workspace/test_calibration.py`: a very small analytic calibration, not a
  validator for the supplied experiments.

Run the calibration checks with `python workspace/test_calibration.py`. They
use Python's standard-library unittest runner; pytest is not installed in the
isolated environment.

Start by running the existing campaign or calibration and recording a diagnosis.
Use experiments to distinguish plausible explanations, revise the implementation,
and rerun. At least one documented run/inspect/revise/rerun comparison is required.
The supplied CPU modules are the supported starting point; CUDA and MATLAB are
not installed. No network or additional downloads are needed.

## Deliver a research handoff

Write the following into the output directory given in your launch prompt:

```
workspace/                  repaired executable modules
run.sh                      entry point described below
config.json                 primary numerical/method settings
ablation_config.json        a genuinely different method/numerical design
refinement_config.json      a finer temporal or spatial accuracy check
results.csv                 primary campaign measurements
ablation.csv                alternative campaign measurements
scaling.csv                 measured runtime/memory, including refinement
experiments/primary/         raw fields and diagnostics from the campaign
experiments/ablation/        raw fields and diagnostics for the comparison
experiments/refinement/      raw fields and diagnostics for convergence
figures/primary_result.png   intervention comparison, regenerated from tables
figures/robustness_or_scaling.png
claims.json                 quantitative claims with evidence row references
report.md                   diagnosis, revisions, convergence, scientific limits
```

Figures need no particular appearance; retain their plotting code and cite the
table columns used. Tables and claims must be derived from actual saved runs.
Do not manufacture timings. At least one claim must compare intervention outcomes
and one must quantify numerical sensitivity. `claims.json` is a list of objects
with `id`, `statement`, `evidence`, `comparison`, and `value`. `evidence` is a list
of `{table, case, frame, column}` objects. Use `comparison: "difference"` for the
first cited value minus the second, or `"ratio"` for their ratio. Include the
interpretation and limitations in `statement`/the report rather than inventing a
categorical conclusion that the numbers do not support.

The entry point is:

```
bash output/run.sh /absolute/path/to/manifest.json /new/result/directory /absolute/path/to/config.json
```

It must consume *new* manifests and states of the documented form, never infer
answers from case names, and write `results.csv`, `scaling.csv`,
`configuration.json`, and one `<case>.npz` and `<case>.json` per case. The existing
experiment writer illustrates the required fields. Run without the third
argument using your primary configuration. Paths must remain relocatable.

For the handoff, `results.csv` and `ablation.csv` copy the corresponding campaign
tables. `scaling.csv` combines the three runs' scaling tables and adds `variant`
(`primary`, `ablation`, `refinement`). Record the baseline investigation separately
in the report or an extra table. Use distinct, substantive configurations; merely
renaming the same run is not an ablation.

## Numerical and scientific acceptance

We rerun your system on held-out initial states and interventions across the
listed geometries. We independently assess wavefunctions modulo global phase,
density evolution, signed vortex positions, coordination/order, and kinetic
energy partition, as well as consistency between raw fields and measurements.
The principal score combines mean and worst-family accuracy; near-converged
results score better than merely plausible ones. Runtime and memory are additional
competing objectives. Evidence quality is scored separately from core physics.

The hidden runs use 96–192 samples per axis, repulsive interactions up to 900,
rotation magnitude below 0.99, and observation times up to 6 in the units below.
Use the provided CPU environment (Python 3, NumPy, SciPy, Pillow).
No GPU is available. Aim for the entire five-case hidden campaign within 180 CPU
seconds and 1 GiB; generous safety limits are 300 seconds and 2 GiB. Limit numerical
library threads to one for comparable measurements. An accurate, efficient
alternative method is welcome. There is no required integrator or fitting method.

The construction has been checked with a working reference. Your one-hour work
budget is for diagnosis and experiments, not for running an unbounded simulation.
Make a scientifically useful submission even if some transfer case remains weak.
Do not read outside this participant directory and your designated attempt
directory. Put all edits and temporary files in the attempt directory; preserve
the supplied assets.
