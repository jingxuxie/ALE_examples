# Are the transport traces physical?

You are taking ownership of a small group's nonequilibrium many-body simulation
pipeline. The original impurity-chain workflow has been reused for ladder,
spin-orbit, superconducting and vibrational contacts. It emits smooth current
traces, but the group no longer trusts their physical interpretation. A clean
energy-convergence message and a nearly constant norm have not resolved the
discrepancies.

Deliver a repaired, reproducible research workspace and a bounded validation
study. Determine what is wrong with the legacy workflow, choose numerical and
representation policies appropriate to the supplied regimes, and establish
which transport conclusions are supported by controlled experiments. You may
repair or replace any scientific component. You need not retain its algorithm
or use a particular library.

## Assets

- `input/cases/`: five unlabeled development experiments, one per physical
  regime. They are small enough to investigate interactively.
- `input/MODELS.md`: authoritative physical definitions and file conventions.
- `input/incident.md`: the group's observations, not diagnoses.
- `workspace/legacy/`: the runnable migration-era pipeline, split into
  assembly, measurement, numerical configuration and orchestration components.
- `workspace/tools/diagnose.py`: invariants and finite-resolution continuity
  diagnostics. Passing them is necessary evidence, not an accuracy oracle.
- `workspace/tools/study.py`: optional experiment/table/figure scaffolding.
- `workspace/upstream/`: genuine source-workflow fragments and license.
- `workspace/runtime/`: pinned offline Python numerical runtime, including
  the tensor-network engine, NumPy, SciPy and Matplotlib. Python driver source
  and its API docstrings are included. You may inspect them.

The paper, reference solution and held-out trajectories are deliberately not
provided. No internet access or package installation is necessary or allowed.

## Starting point

From this directory, run:

```
source workspace/env.sh
python3 workspace/legacy/run.py input/cases/impurity_dev.json /YOUR_OUTPUT/baseline production
python3 workspace/tools/diagnose.py /YOUR_OUTPUT/baseline
```

`env.sh` handles the bundled MKL/OpenMP loading on this machine; retain that
initialization or an equivalent in your entry point. The numerical runtime
has been checked before delivery. The legacy scientific results have not been
certified for the extended models. Work in the empty output directory given
in your session prompt; do not alter these input assets.

## Research obligations

1. Reproduce a legacy discrepancy and diagnose competing causes using
   independently meaningful physical or numerical checks, not visual smoothness.
2. Produce accurate initial-state and post-quench observables for all five
   physical regimes. The same executable must accept unseen instances without
   case-name-specific answers. Resolve the relation between regional charge,
   transport current and local sources.
3. Run an actual refinement/ablation loop. Demonstrate at least two genuinely
   different configurations on at least three regimes, inspect the evidence,
   and revise your policy. Separate a representation/physics error from a
   finite-resource approximation. Explain what your experiment can and cannot
   establish; these short closed-system traces do not by themselves establish
   an infinite-lead steady state.
4. Quantify the quality/cost tradeoff and its worst-regime behavior. Include a
   size or resource scaling experiment and explain your resource choices.

## Executable contract

Submit `output/run.sh` and the executable sources in `output/workspace/`.
The evaluator invokes:

```
ALE_ASSETS=/absolute/path/to/this/directory bash output/run.sh CASE.json RUN_DIRECTORY PROFILE
```

`PROFILE` is `production` by default, or `baseline` / `refined` for your distinct
policies. These names describe your submitted configurations, not mandatory
methods. The run directory is initially empty. One process handles one case.
The evaluator may supply an arbitrary absolute input path and arbitrary case
identifier. Do not infer physics from identifiers. `ALE_ASSETS` always points
to these read-only assets. Reading its numerical runtime is permitted.

Write `trajectory.csv`, with one row per requested time and columns
`time,norm,charge,number,spin,phonon,current,source,energy`. Write `stats.json`
with `initial_energy`, `seconds`, `peak_rss_mb`, and a JSON `settings` object
describing the actual configuration. Extra diagnostics and checkpoint files
are welcome. Definitions of the physical columns are in `input/MODELS.md`.

## Coupled study artifacts

Also submit:

- `results.csv`: experiment ID, case ID, profile, time and physical observables;
- `ablation.csv`: distinct configuration comparisons and measured changes;
- `scaling.csv`: case, size, profile, measured time and peak memory;
- `runs/`: actual run outputs underlying the tables, each with its input case;
- `figures/primary_result.png`, `figures/robustness_or_scaling.png`, and the
  tabular source data used for each figure;
- `claims.json`: at least three supported quantitative claims, using the small
  comparison schema in `workspace/tools/study.py`, with table/row references;
- `report.md`: concise diagnosis, experiments, policy changes, limitations and
  supported conclusions. Do not claim accuracy solely from conservation.

Use the CSV column schemas emitted by `workspace/tools/study.py` (additional
columns and additional experiments are allowed). In particular each table row
has a unique `row_id`; ablation rows name their `left_run` and `right_run`;
and every run includes `case.json` and `profile.txt`. This lets the independent
audit follow a figure or claim back to an executable experiment.

The optional study tool handles repetitive packaging; it does not supply a
correct physical method or judge the truth of your conclusions. You may
replace it, preserving the stated contracts. Reporting aesthetics are unscored.

## Resources and evaluation

Use at most two numerical CPU threads per simulation and 4 GiB resident
memory. A held-out production run has a 180-second safety timeout; the target
is substantially faster, with continuous cost scoring. Development cases have
4--6 electronic sites; held-out cases include up to 14 electronic sites and up
to six truncated oscillators (2--6 levels each), and the same five physical
regimes. Couplings, fillings, regions, graph layouts, phases, local Hilbert
spaces and sampling grids can change within the documented model class.
The physical time span is at most 2.0, in the stated units. Dense enumeration
of every many-body state will generally not fit the production budget.

Evaluation reruns the executable on unseen cases, measures errors against
independently checked converged calculations, considers the worst regime and
measures actual resource consumption. Accuracy is continuous over several
orders of magnitude: near-reference performance earns more than merely
qualitative agreement. Missing regimes cannot be compensated by one perfect
regime. Evidence is checked against fresh runs, including whether different
profiles actually differ and whether quantitative claims follow from tables.
Any valid physical/numerical method is acceptable. Scientific correctness is
scored separately from completion of reports and figures.
