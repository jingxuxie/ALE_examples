# Private polar pilot

`build.py` reads v4.1.0 fixture blobs from the supplied official phonopy clone
and imports the verified `author/runtime4`. Nothing in the author tree is
modified. Generated `provenance_initial.json` records the exact solution
commits, fixture hashes, Python version, and every installed dependency spec.

From `concepts/polar`:

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python private/reference/build.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python private/reference/build.py --seed 884209 --fresh-heldout
PYTHONPATH=../../author/runtime4 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python private/evaluator.py --submission participant/workspace/solve.py --split all --output attempt/sandbox-baseline.json
```

The initial pool has 12 cases, six with split `pool` and six independently sampled
heldout, across real NaCl, rutile SnO2 and anatase TiO2. Each family includes
ordinary and near-Gamma cases; the latter are in rotated Cartesian frames with
unimodular oblique primitive-basis changes. Larger batches contain 96 or 128
derivative queries, 40 response packets, up to 18 modes, and about 300 reciprocal
vectors. No forces or material parameters are randomly invented.

Near-Gamma queries start at 2.2e-5 cycles/Angstrom, outside the pinned oracle's
1e-5 Gamma guard. Do not force unrealistic queries inside that guard to defeat
finite differences. A sufficiently accurate finite difference is permitted;
the audit must report whether a generic small step succeeds.

`--fresh-heldout` writes six cases below `challenge_pool/fresh_SEED/`, preserving
the initial pool and smoke. It requires a different seed. Family, split, seeds,
hashes and paths relative to `private/` are in each LIST-format manifest.
The initial pool IDs retain the opaque `development` filename label; split
selection uses metadata `pool`, never that filename label. Fresh IDs include
their seed to avoid collisions when combining ratchet generations.
`--no-measure` exports only inputs/references; a normal build is needed to
populate baseline files before scoring. Rebuild determinism concerns numerical
inputs/targets, not nondeterministic timing/RSS diagnostic fields.

Stored derivative targets use the official Rust implementation, with three
Python-path parity checks per case. A standalone private solution recomputes
from the raw exports and is required to exceed 0.90. Mode-reference spectra and
direction-selected Cartesian vectors use the official degenerate perturbation
helper; unresolved directional ties are averaged exactly as the public contract
specifies. Packet mixing norms are recorded to expose a trivial diagonal test.

`score_case(actual, reference, baseline, case, input_data)` accepts NPZ paths or
array mappings. It returns two component scores and raw errors. Errors are RMS
across packets of relative Frobenius errors. Mode response equally combines
operator, directional-spectrum, and direction-selected Cartesian-vector errors.
For each component, `scale=max(baseline_error,1e-10)` and
`score=1/(1+error/scale)`. Thus the measured baseline scores 0.5 unless its error
is at the documented numerical floor. Scores weight components and cases equally, with no
binary accuracy plateau. Runtime and memory are reported, not hidden multipliers.

Trusted calibration executes both solvers and stores their actual outputs,
external times/RSS and branch diagnostics in `attempt/initial/calibration.json`.
RSS diagnostics after branches are cumulative process peaks, not isolated
branch allocations and not trusted submitted metrics. The common sandbox helper
enforces case time/memory limits for submissions. Do not expose `private/` or
`attempt/` to participants.

## Initial measured result and limitation

The 12-case local calibration gives reference mean 0.9999999918 and baseline
mean 0.5000000000. Raw derivative reference error is below 1.7e-15; mode-response
reference error is below 2.2e-9. Reference acceptance also checks raw errors
independently of normalized scores; the score scale cannot be inflated by a
bad reference. Real off-diagonal degenerate-response norms range from about
10 to 81, so diagonal-only mode handling is genuinely tested.

`attempt/audit/report.json` records isolated per-branch process RSS/time,
wrong-coordinate ablations, bitwise numerical rebuild checks for each family,
and fresh-seed query checks. Run `python private/reference/audit.py` with the
same thread environment to regenerate it. Exact input/reference arrays rebuilt
identically for all three families; fresh heldout seeds change the queries.

**FD shortcut remains viable:** the existing public value evaluator with a
universal Cartesian finite-difference step of 1e-7 scores 0.995278 on outcome 1
across all 12 cases; 1e-6 scores 0.989735 and 1e-8 scores 0.957380. These are
derivative-only audit scores, not a claim that the response task was solved.
All derivative audit outputs are stored. No thresholds were tightened to hide
this result. The main pilot should reject the derivative concept if this shortcut
disqualifies it; additional genuine degeneracy work does not make that finding
disappear.
