# Grid pilot author notes

Everything in this pilot is under `concepts/grid/`. Public files are only the
concise task, a read-only starter workspace, and one unlabeled input. The attempt
directory is intentionally empty. No model attempts are part of this build.

## Scope and provenance

This is an author-built **capability ablation**, not a claimed bug in an old
checkout. The starting implementation ignores the off-diagonal grid geometry,
keeps one component-rounded image, and approximates spectra with a histogram.
The private oracle uses the official full integer-grid/BZ and tetrahedron
modules. Geometry and spectral integration remain independently scored.

Official source revisions:

- phonopy: `435b32225a26446a3b2b5e2a63c7bfd700583219`
- phono3py: `49e7d7225a8931df59ed2f4603344ea8d89846f2`

The source checkout is not assumed identical to the wheel implementations.
`provenance.json` records exact runtime versions and SHA256s of the Python
modules and compiled extensions actually used. `requirements.txt` pins the
private numerical runtime. The participant sandbox instead uses the installed
system NumPy 1.21.5 and SciPy 1.8.0. No private scientific package is mounted.

AlN frequencies use the official `phono3py_params_AlN332.yaml.xz` force dataset
and harmonic force-constant production. SnO2 uses official
`phonopy_disp_SnO2.yaml` and `FORCE_SETS_SnO2`. Non-analytical corrections are
disabled consistently. Integer unimodular changes of direct basis produce
genuinely skew representations of the same material, with q transformed back
before harmonic diagonalization. No random energies or simulator forces are
used. Each case records the fixture hashes, force-constant hash, rebase,
selected physical bands, ranges, near-degeneracy statistics, and exact ties.

The initial build has independently seeded pool and heldout halves, four
families, and five cases per half: non-diagonal skew grids, exact BZ boundary
ties, narrow/close optical branches plus a physical one-point flat-interpolant
limit, and dense grids. Dense cases have 110592 and 105600 points. Public grid
rows are shuffled; topology is the integer quotient, not array adjacency.
The flat limit is actual zone-center data on a one-point periodic grid and is
explicitly disclosed in the contract, not misrepresented as physical dispersion.

## Reproduction

Commands are relative to the task target, not the concept directory. Set
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1` for every
command. The scripts bootstrap the private runtime without installation.

```
python -B concepts/grid/private/reference/build.py
python -B concepts/grid/private/reference/validate.py
python -B concepts/grid/private/reference/validate_runtime4.py
python -B concepts/grid/private/evaluator.py --submission concepts/grid/participant/workspace/solve.py --split all --output concepts/grid/private/reference/baseline_evaluation.json
python -B concepts/grid/private/evaluator.py --submission concepts/grid/participant/workspace/solve.py --split all --stored-reference --output concepts/grid/private/reference/reference_selfcheck.json
```

The build calls shared `author/evaluation.py::sandbox_run` for every baseline.
An outer sandbox that disallows bubblewrap network-namespace initialization
needs approval to launch this same isolated runner outside that outer sandbox;
there is no unisolated submission fallback. The initial blocked run is retained
in `runs/pool_skew_17029/baseline_failure.json`. Measurements include harness
startup and filesystem/scheduler effects and are actual single-run observations,
not simulated timings. Official oracle subprocess timings and peak RSS are
separately recorded in each case's metadata; they are not participant timings.

`validate.py` independently certifies closest images using a singular-value
bounded exhaustive search. It checks quotient coverage, exact ties, all output
shapes through the scorer, CDF endpoints and monotonicity, nonnegative DOS,
flat-band point-mass limits, separation of thresholds from energy knots,
independent component failure behavior, smooth score changes, hashes, and
pool/heldout disjointness. On the smoke lattice it independently clips the
barycentric simplex and uses convex-hull volumes plus numerical derivatives to
check both official spectral outputs. `validation.json` is written only after
all these checks pass. Stored-reference self-checks are explicitly marked and
must not be reported as measured solver executions.

The separate `validate_runtime4.py` cross-checks three representative spectra
with phonopy 4.1.0's Rust integration implementation from `author/runtime4`.
Its dependencies are pinned in `requirements-runtime4.txt`.
It records module hashes and differences in `runtime4_validation.json` only
on success; runtime4 is not used to build the primary strong references.

## Fresh heldout generation and integration

For a ratchet, choose a previously unused seed, for example:

```
python -B concepts/grid/private/reference/build.py --split heldout --seed 981721
```

This generates fresh integer grids, basis choices, row permutations, translated
queries, physical frequencies, and thresholds and appends new references and
measured baselines. It does not reveal heldout labels publicly or overwrite
existing IDs. `--family skew` optionally limits a generation smoke check.
`--measure-baseline-only` refreshes actual resource/error records. Ordinary
reruns skip already completed case IDs; the initial heldout seed is 79043 and
the pool seed is 17029.

`private/challenge_pool/manifest.json` is a list with filenames relative to
`private/`, timeout/memory limits, component `keys`, and explicit `core_keys`.
Import `private/evaluator.py::score_case(actual, reference, baseline, case,
input_data)` from the shared main evaluator. Each result has `geometry` and
`spectral` component dictionaries containing `score`, raw `error`, and
`baseline_error`. Quality is `1/(1+error/max(baseline_error,1e-8))`: ordinary
baseline 0.5, perfect reference 1, no tolerance plateau, explicit floor for
baseline-exact components. Canonical sorted CSR makes image order unambiguous.
The local CLI delegates execution to the shared helper and augments its report
with family-balanced/worst-family quality and actual runtime/RSS ratios.
Resource statistics are reported, not folded into tournament core scores.
