# Private fitting pilot

Only `participant/` and one selected input may enter the solver sandbox. This
directory, the reference targets, heldout observations, baseline calibration,
and the source/runtime installations are evaluator-only. Do not copy the
private manifest into the public input directory.

## Rebuild

From the target directory:

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  python -B concepts/fitting/private/reference/build.py
```

The builder asserts phonopy 2.43.4, phono3py 3.19.2, symfc 1.5.4 and spglib
2.5.0 in `author/runtime`. It never installs packages or modifies sources.
Every source data file and fixture is hashed; the source repository commits
are recorded separately from the actual installed oracle versions. The
symfc 1.5.4 tag is commit `7b774611f10a5930c9e760a759e304020217c087`.

The builder runs one reference worker per case. It saves compact fc2/fc3 and
private unseen original displacement/force observations in each reference
NPZ. It never saves or publishes an invariant basis. `*.build.json` records
reference-worker wall time and Linux `ru_maxrss` in KiB, including reference
data loading, fitting, geometry generation, and invariant checking. Package
import startup precedes that internal timer; the peak RSS includes imports.

The seed and chosen snapshot indices are recorded. `--heldout-seed INTEGER`
changes heldout selections without changing initial selections. `--case ID`
can be repeated. For example, rebuild only the three hidden cases with:

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  python -B concepts/fitting/private/reference/build.py --heldout-seed 901337 \
    --case heldout_mgo_64_512 --case heldout_sno2_72 --case heldout_gan_128
```

Recalibrate affected baseline outputs after rebuilding. Initial and heldout
cases use different source datasets/supercell sizes; within every case,
training and force-test snapshot indices are disjoint. The public smoke
contains six training snapshots of the small initial silicon case and no
targets or force-test observations.

## Evaluate and calibrate

The common evaluator runs submissions in its sandbox. From the target:

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  python -B concepts/fitting/private/evaluator.py \
    --calibrate-baseline --validate-reference
```

`--direct` is an explicit bootstrap alternative if the common runner is not
yet available. Its record states that isolation and the memory limit were
not enforced; `/usr/bin/time` still measures child peak RSS. A direct result
is not evidence that the sandbox accepted the program. The normal path calls
`author/evaluation.py:sandbox_run` with the exact supplied signature.

`private/reference/author_measurements/validation.json` contains measured outcomes, execution times,
memory, component errors, and whether failure was substantive or clerical.
The manifest is a JSON LIST with `id`, `family`, `split`, `input`, `reference`,
`baseline`, `timeout`, `memory_mb`, `keys`, `files`, and `core`. File paths are
relative to `private/`. Its calibration metrics are private. All author-run
outputs and measurements remain under `private/reference/author_measurements`;
`attempt/` is empty before handing the task to a solver.

## Scoring API

`private/evaluator.py` exports
`score_case(actual, reference, baseline, case, input_data)`.
Arguments containing arrays can be dictionaries or loaded NPZ mappings.
The returned dictionary has exactly two scored entries, `fc2` and `fc3`.
Each contains `score`, raw physical errors and its measured baseline error,
matching the common evaluator's nested-component interface. Only those two
branch scores enter the common core mean. `score_details` returns the full
flat diagnostics used by this pilot's validation runner.

Each component has the continuously varying, non-thresholded form
`1 / (1 + error / baseline_error)`. Explicit 1e-10 dimensionless and 1e-12
force floors handle baseline-exact components. There is no success tolerance
or flat acceptance band. Tensor errors are relative to reference tensor norms;
physical residuals are normalized tensor norms. Force predictions are compared
with real unseen forces, not reference-generated observations.

Core scoring averages only two nontrivial branches, `fc2_branch` and
`fc3_branch`. Each branch error sums its tensor-relative error, acoustic,
permutation and space-group residuals, and a real heldout force RMSE normalized
by the observed force RMS. Cubic support error also enters the cubic branch.
The harmonic branch uses unseen harmonic forces when available; otherwise it
uses unseen mixed forces. No easy exact-zero invariant scores are averaged
into the core as bonuses. The measured baseline is exactly 0.5 in each branch.
Oracle scores can be slightly below one because the true DFT forces contain
irreducible truncation/numerical error; each must exceed 0.90.

The same-cell cases require simultaneous harmonic/cubic estimation. The
different-cell cases deliberately use a two-stage objective, fitting the
512-atom harmonic tensor first and a finite-range cubic residual on 64 atoms
second. This avoids silently substituting a small harmonic cell or scoring
inconsistent independent harmonic fits. Raw forces are not cleaned,
resampled from fitted tensors, or replaced with synthetic labels.
