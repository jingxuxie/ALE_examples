# Release audit: transient transport that looks converged

Your group must decide whether its portable open-quantum-transport pipeline can be used for a pulse-response study. The release candidate produces smooth, plausible plots on a simple wire, but current and density results change when the reservoir representation is altered. The team has not established whether the discrepancies are physical transients, state preparation, time evolution, boundary contamination, or a combination. Qualify a repaired or replacement executable system, not just one plot.

## Professional outcome

Diagnose the failure, repair the connected workflow, and support a scientifically defensible release recommendation. The system must calculate local fermion densities and oriented bond currents for all supplied physical models and transfer to unseen members of the documented model envelope. Establish what your public convergence checks do and do not demonstrate. Reconcile apparently stable traces with independent controls. Use at least one run–diagnose–revise–rerun loop and retain its evidence in your report.

The benchmark-authored release candidate is a portability implementation of an established scattering-region/reservoir workflow. `workspace/upstream/` contains authentic source examples and an optional quadrature utility retained under their original license. Those historical examples are provenance, not executable dependencies or a reference answer. The active workspace uses only the installed numerical Python stack. No upstream simulation package is required or installed.

## Supplied assets

- `input/development.json`: six unlabeled development experiments. They cover a voltage-driven cavity, side branches with localized sectors, an interference ring with independently occupied contacts, spin mixing, a gated honeycomb flake, and dimerized reservoirs.
- `input/controls.json`: a stationary control and two time-horizon scaling experiments.
- `workspace/transport/`: physical-model loading, drive construction, reservoir primitives, initial preparation, boundary representation, propagation, observation, and simulation configuration. Every active numerical component may be repaired or replaced.
- `workspace/driver.py` and `run.sh`: executable batch interface and summary-table writer.
- `workspace/diagnose.py`: non-oracular stationarity and convergence diagnostics.
- `workspace/tests/`: tiny convention tests, not sufficient qualification.
- `workspace/experiment.py` and `plotting.py`: optional experiment/table/figure infrastructure. You still choose the numerical methods, comparison, claims and conclusions.
- `input/incident_notes.md` and `input/FORMAT.md`: observations from the failed release and the complete physical/input/output contract.

Start by reproducing the candidate's behavior. Useful starting commands, from a writable copy of `workspace/`, are:

```
bash run.sh --cases /absolute/path/to/input/controls.json --output baseline --config production
python3 diagnose.py baseline
python3 -m pytest tests -q
```

Do not regard passing tiny tests, current conservation alone, agreement between two coupled resolution changes, or resemblance to a smooth curve as an accuracy certificate. Public diagnostics deliberately contain no target transient traces.

## Physical scope

All Hamiltonians are quadratic and noninteracting, with units ħ = |e| = 1. The central region is connected to truly semi-infinite periodic leads, already coupled before time zero. Each incoming reservoir channel has its own specified Fermi occupation. Normalizable eigenstates of the fully coupled initial infinite system have the separate Fermi occupation specified by `bound_mu` and `bound_temperature`; there is no coherence imposed within that sector. The preparation is not a sudden connection of finite isolated reservoirs. Drives begin at zero and are specified completely in the input contract. Output absolute densities and absolute currents, including any pre-existing stationary current.

Unseen tests may combine: 1–3 reservoirs; 1–4 orbitals per lead cell; real or complex hoppings; singular intercell hopping; band gaps; bound or dark states; unequal lead occupations; zero or finite temperature; noncommuting local drives; flux and contact phases; repeated/uneven observation times are not used. Central dimensions are at most 56, observation horizons at most 80, and local energy scales at most 3.5. The development set represents the physical families but is not a labeled training set. Preserve the full input semantics rather than recognizing family names or experiment IDs.

## Required executable and experimental evidence

Write the following inside the empty output directory assigned to your session:

```
output/
  workspace/                  repaired, self-contained active code
  run.sh                      batch entry point, any working directory
  results.csv                 production development experiments
  ablation.csv                same experiments: conservative and ablation
  scaling.csv                 production controls/time-horizon experiments
  runs/                       actual .npz traces and metadata behind tables
  figures/
    primary_result.png
    robustness_or_scaling.png
    primary_result.csv
    robustness_or_scaling.csv
  claims.json
  report.md
```

`run.sh --cases FILE --output DIR --config NAME` must accept arbitrary conforming suites. The supported names must include `production`, `conservative` (a genuine accuracy refinement), and `ablation` (one meaningful scientific/numerical design change, chosen by you). Never make the production result depend on a case ID. Keep outputs and diagnostics finite. The exact NPZ keys and table/claim contracts are in `FORMAT.md`.

Run all development cases with all three configurations. Run the controls with production. The ablation must isolate a substantive choice, not just rename a configuration or perturb reported numbers. Explain what evidence discriminates your competing diagnoses; if a comparison is not identifiable, say so. A refinement is not automatically an ablation. Source every plot from the retained trace/table data, with CSV source data. The report should be concise, explain the before/after failure and remaining limitations, and link its principal conclusions to `claims.json` and table rows. Unsupported global accuracy claims are worse than an honest limitation.

## Evaluation and resources

The evaluator reruns the executable on heterogeneous withheld systems and checks absolute initial states, time-dependent density/current traces, worst-family behavior, runtime, and memory. Numerical scores are continuous: near-reference results are worth more than merely plausible ones. Typical useful accuracy is approximately 10⁻⁴–10⁻³ in absolute local observables, including small currents; accuracy in only large density offsets is insufficient. The grading distinguishes scientific/numerical failure from missing decorative deliverables. No particular algorithm is required.

It also recomputes public summary values from your raw traces, replays production and your ablation, verifies that configurations differ, checks claims against their referenced table cells, and verifies figure source data. A fabricated or unrerunnable evidence package is invalid even if a few traces happen to match.

Environment: Python 3.10; NumPy 1.21, SciPy 1.8, Pillow, pytest, and numba are available from system Python. Matplotlib is not installed; a Pillow plotter is supplied. Do not depend on network downloads or files outside your task and output directories. CPU only, one numerical thread, 2 GiB peak resident memory. A six-case evaluation batch has a 240-second limit, deliberately allowing multiple times the working system's numerical runtime. This is a throughput/resource requirement, not a request to finish the research work in 240 seconds. Your fresh session has up to one hour. Algorithms based on sufficiently controlled finite embeddings are allowed; no representation is forbidden merely because it differs from the intended workflow.
