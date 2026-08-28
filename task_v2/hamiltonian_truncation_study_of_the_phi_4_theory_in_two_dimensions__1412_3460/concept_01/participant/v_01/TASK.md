# Rescue a finite-volume scalar-spectrum campaign

You are taking over a computational field-theory campaign whose low-energy
spectra change appreciably when the Fock-space energy cutoff changes. The
inherited production path was used in a homogeneous, large-circle setting. It
is now being used for a twisted circle, an explicitly biased field, and a
spatially modulated interaction. A small vacuum-energy correction appears to
help some plots, but the team cannot tell whether it repaired the physics or
merely made the plots look stable.

Deliver a defensible replacement for this pipeline. Reproduce its failure,
diagnose the relevant approximations and numerical issues, select and implement
an appropriate treatment of the omitted states, and demonstrate which
improvement claims survive the supplied changes of model and geometry. The
outcome is a reusable spectrum calculation and an evidence-backed technical
assessment, not a fit to a supplied answer table.

## Scientific contract

`input/PHYSICS.md` specifies the theory, energy convention, sector definitions,
and the archived operators. It is authoritative; the starter is not. The
operator archives are real finite-volume Fock-space matrix elements, not
random matrices. They are trusted within their stated projection. The
low-energy eigenvalues of an archive are **not** the target physical spectrum:
discarded higher-energy states still affect that spectrum.

For each requested case and cutoff, estimate the absolute vacuum energy and
the three lowest absolute energies in each named sector of the untruncated
finite-volume theory. Gaps must use the common physical vacuum, not a separate
vacuum for each sector. Keep multiplicities. The sectors in the source-broken
case are not field-parity sectors, and momentum is not conserved in the
modulated case. Finite circle effects are part of the target, not errors to
subtract indiscriminately.

There is no prescribed renormalization, extrapolation, eigensolver, or basis
strategy. Analytical special cases, explicit elimination, counterterms, and
hybrid strategies are permitted. Your production result for cutoff `C` may
use the supplied matrix elements and states only at free energy `<= C`.
Analytical knowledge of the theory and newly generated states are permitted,
but their cost must be reported; reading the larger supplied projection while
labelling the row with a smaller cutoff is not. Replay can supply a physically
trimmed archive. Methods must generalize to new couplings, circle lengths, and
operator archives within the five documented branches.

## Assets and useful starting points

- `input/campaign.json`: unlabelled development experiments and archive paths.
- `input/archives/`: free-energy diagonals, occupation states, and sparse
  normal-ordered operators, through free energy 16 in the supplied units.
- `input/calibration.json`: one small independent Gaussian calibration.
- `workspace/`: runnable multi-file inherited pipeline. `normal_order.py` and
  `cutoff.py` encode approximations, not validated contracts. Its other
  numerical decisions are also yours to assess.
- `workspace/legacy/`: occupation and ladder-operator components from the
  retired research implementation, retained as readable scientific artifacts.
- `workspace/tests/`: small oscillator and archive invariants. These are useful
  checks, not an oracle for the physical spectrum or the extension.

Start by copying `workspace/` into your output directory and running the
campaign. Keep a record of the initial result before revising the system.
Inspect vacuum and excitation drift separately. A useful workflow should
include at least one actual run–diagnose–revise–rerun comparison. You are
responsible for the experimental design: distinguish competing explanations
rather than assuming that a flatter cutoff curve proves accuracy.

## Reproducible interface

Your output root must contain `run.sh`. The evaluation invocation is:

```
bash /path/to/output/run.sh /path/to/request.json /path/to/new_results_directory
```

The request uses the same schema as `input/campaign.json`. Its `archive_root`
is resolved relative to the request file unless absolute. Each case's
`archive` is resolved relative to that root. Requests can select different
subsets of the documented cases/cutoffs and contain previously unseen archive
names. Never infer physical parameters from filenames. Treat inputs as
read-only. `run.sh` must work from an arbitrary working directory and create
its destination. All implementation files it needs must be in your output.

Python 3.10, NumPy, SciPy, Pillow, a C/C++ compiler, and shell utilities are
available without network access. Matplotlib is not assumed. The starter's
Pillow plotting helper is adequate. Do not depend on private files, another
checkout, a paper download, or internet services. Use one BLAS thread. A full
five-case replay should normally take well under 120 seconds and stay below
1.5 GiB; accuracy, worst-branch behavior, runtime and memory all matter. There
is a five-minute safety limit per evaluation replay, not a license to spend
five minutes on each matrix. The development session lasts at most one hour.

## Coupled deliverables

Place the following in the output root; replay regenerates the numerical
tables and figures in its destination:

- `workspace/`: the executable repaired/replaced system, including any tests.
- `run.sh`: the reproducible entry point above.
- `baseline/`: initial campaign tables or a saved, reproducible baseline.
- `results.csv`: one row per production case/cutoff/sector/level.
- `ablation.csv`: the same observables for at least two scientifically
  distinct configurations, including a genuinely uncorrected truncation.
- `scaling.csv`: actual dimension, elapsed seconds and process high-water
  memory for each case/cutoff/configuration; report any extra generated basis.
- `figures/primary_result.png` and `figures/robustness_or_scaling.png`, with
  `figures/source.csv` identifying the exact plotted table rows and quantities.
- `claims.json`: quantitative claims linked to table rows, including at least
  one comparison from each model branch. A conclusion that an improvement
  fails is acceptable when supported by evidence.
- `report.md`: concise diagnosis, methods considered, experiments and revision
  history, retained design, scope and limitations of the physical conclusions.

Use the table columns emitted by the starter. You may add columns, but preserve
the existing ones. `energy` is absolute; `gap` is relative to the common
vacuum. `row_id` must be unique across the two spectrum tables. `method` in
the primary table is `production`; ablations have distinct names.
`claims.json` follows `input/EVIDENCE.md`. The reporting helpers are convenience
code, not a required implementation strategy.

## Evaluation

The evaluator reruns your system on unseen instances of the five physical
branches, compares vacuum and excitation energies with independently checked
higher-cutoff calculations or exact Gaussian results, and includes the worst
branch in the core score. It uses continuous accuracy relative to a raw
baseline and a strong reference, with a numerical uncertainty floor. Merely
passing the tiny public tests or slightly improving raw results does not
saturate the score. Near-reference results score higher.

It also measures resource use; checks supplied tables against a fresh public
replay; checks that ablations really differ; verifies row-linked numerical
claims and figure source data; and examines whether the scientific report
supports its conclusions. Clerical completeness cannot compensate for
incorrect spectra, and missing cosmetics are not treated as a core physics
failure. Exact plot appearance is irrelevant.
