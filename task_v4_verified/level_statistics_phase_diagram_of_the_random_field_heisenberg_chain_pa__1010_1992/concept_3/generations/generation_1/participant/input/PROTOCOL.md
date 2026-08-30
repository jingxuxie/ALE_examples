# C3-v1: exact spectral-center falsification protocol

Paths below are relative to `participant/` unless the package root is specified.

Produce a **static `witness.json`**, not an estimator or executable submission.
Find one bounded, generic field profile whose spectral-center estimate of the
adjacent-gap ratio systematically disagrees with the exact middle-rank-third
value across the fixed perturbation families. Implementing the supplied formula
alone does not solve the inverse search problem.

## Paper seed and scope

Arijeet Pal and David A. Huse, *The many-body localization phase transition*,
arXiv:1010.1992v1 (October 11, 2010), Sections II–III, supplies the periodic
random-field Heisenberg model, zero-magnetization sector, adjacent-gap ratio,
and middle one-third of the energy-ordered states. **The uniform proxy-accuracy
claim below is authored for this task; it is not a claim made by that paper.**
This is a finite-size counterexample, not a refutation of the paper's disorder
averages or a thermodynamic localization result. Adversarial structured fields
are allowed; this is not an IID-disorder average estimation task.

## Frozen model and reference

Use twelve spin-1/2 sites, periodic boundary conditions, exchange `J=1`, and

`H = sum_j (Sx_j Sx_(j+1) + Sy_j Sy_(j+1) + Sz_j Sz_(j+1) + h_j Sz_j)`.

Only the complete `sum_j Sz_j = 0` sector is used, of dimension `C(12,6)=924`.
In the bit basis an up spin has `Sz=+1/2`, a down spin has `Sz=-1/2`, and an
allowed neighboring exchange has matrix element `1/2`. Never mix sectors.
Sort the full real eigenvalue list `E[0] < ... < E[923]`. For any consecutive
list of at least three energies, `r` is the arithmetic mean of
`min(gap[k],gap[k+1])/max(gap[k],gap[k+1])`. Only triplets fully inside the
chosen list contribute. The reference `R(h)` uses `E[308:616]`: 308 levels,
307 gaps, exactly 306 ratios. All indices here are zero-based and stops are
exclusive. No unfolding, eigenvectors, approximate eigensolvers, missing
levels, or sector changes are part of the definition.

## Exact proxy and frozen claim

For each `t` in `(0.49, 0.50, 0.51)`, target energy
`e_t = E[0] + t*(E[923]-E[0])`. Let `j_t` minimize `abs(E[j]-e_t)`, breaking
ties by the smaller rank. Set `a_t = max(0, min(796, j_t-64))`. Compute `r_t`
on the 128 consecutive energies `E[a_t:a_t+128]`, giving 126 ratios. The
proxy is `P(h) = (r_0.49 + r_0.50 + r_0.51)/3`.

These are three relatively large, potentially overlapping windows. Overlap
is intentional: each window gets equal weight, even when some triplets are
repeated. They are not three statistically independent samples. There is no
permission to choose targets, window widths, rank masks, or per-window signs.

**Claim C3-v1:** for every admissible base field profile `h` and every public
perturbation family `F`,

`abs(mean_(h' in F(h)) [P(h') - R(h')]) <= 0.050`.

This is a deliberately strong, precisely falsifiable uniform accuracy claim
about replacing a rank prescription with energy-target sampling. The output
must satisfy the stronger robustness certificate below, rather than exploiting
one unusually small spectral sample.

## Admissible fields and perturbations

The witness supplies exactly twelve real field values, in site order. Base
fields must have absolute mean at most `1e-9`, maximum absolute value at most
`8.0`, RMS at least `0.65`, and pairwise separation at least `0.001`.
Mean zero fixes the physically irrelevant uniform-field gauge in this sector.

Define `D(h)` as the smallest RMS distance between `h` and `s*g(h)`, for every
cyclic shift and reflected cyclic shift `g` and sign `s in {-1,+1}`, excluding
only the identity with positive sign. Require `D(h) >= 0.12`. The negative
sign checks combined spin inversion and spatial symmetries as well. This
excludes the zero-field integrable limit and exact or nearly restored spatial
symmetries; it is not permission to combine unresolved symmetry sectors.

There are four families, **eight members each**, all listed explicitly in
`input/protocol.json`:

| Family | Field scale | Jitter amplitude before centering |
|---|---:|---:|
| `jitter_004` | 1.00 | 0.04 |
| `jitter_012` | 1.00 | 0.12 |
| `scale_096` | 0.96 | 0.08 |
| `scale_104` | 1.04 | 0.08 |

For each member, `h' = scale*h + offset`. Offsets have zero mean; centering
can make an individual offset as large as twice the pre-centering amplitude.
For provenance, each uncentered component is `2*n/(2^64-1)-1`, where `n` is
the big-endian integer from the first eight SHA-256 bytes of the ASCII string
`ale-c3-v1|FAMILY|MEMBER|SITE`, using indices `0..7` and `0..11`. Multiply
the centered vector by the family's amplitude. The literal JSON offsets,
not a platform-specific random-number generator, are authoritative.

Every derived profile must also have absolute mean at most `1e-9`, maximum
absolute field at most `8.5`, RMS at least `0.55`, pair separation at least
`1e-7`, and signed symmetry distance at least `0.05`. Every adjacent gap of
every complete spectrum, including the base, must exceed `1e-10`. A violated
constraint or unresolved numerical degeneracy makes the witness invalid,
not a successful counterexample. No gap clipping or epsilon denominators.

## Fixed pass targets

Choose a single orientation `s in {-1,+1}` and define
`d(h') = s*(P(h')-R(h'))`. Let `B_F` be its mean over the eight members of
family `F`. All of these conditions are mandatory and use inclusive `>=`:

- `core = mean_F B_F >= 0.060`.
- `worst_family = min_F B_F >= 0.050`.
- The unperturbed base has `d(h) >= 0.055`.
- In **each** family at least six of its eight members have `d(h') >= 0.025`.
- Every schema, field, spectrum, and resource constraint passes.

There is no absolute value taken separately for different members, no
sign switching, and no hidden choice of the best family. A core above 0.05
already contradicts Claim C3-v1 for at least one family; the other criteria
require a systematic, same-direction discrepancy. Do not infer statistical
independence or a probability guarantee from these deterministic probes.

## Submission and exact helper

The only accepted keys are `schema_version`, `fields`, and `orientation`:

```json
{"schema_version":1,"fields":[-1.31,0.72,-2.16,1.93,-0.54,2.48,-1.87,0.19,1.04,-0.93,0.38,0.07],"orientation":-1}
```

This is a schema example, not a claimed passing witness. Values must be
finite JSON numbers, not strings or booleans; the orientation and version
must be integers. Duplicate or extra keys, `NaN`, `Infinity`, malformed or
oversized JSON, symlinks, directories, and pipes are rejected. The byte
limit is 16,384. Submitted code, paths, eigenvalues, and claimed scores
are never executed or trusted.

`workspace/exact.py` supplies `hamiltonian`, `spectrum`, `proxy_statistics`,
`validate_witness`, `family_fields`, and `assess(witness, protocol)`. Load
the protocol with the standard-library JSON parser. It computes exactly
the same quantities as the trusted evaluator. The evaluator has its own
copy and never imports participant workspace code or a submitted module.

From the participant directory, run the baseline with:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python baseline/solve.py --output witness.json
```

It performs a reproducible unstructured search, emits a valid-format
witness plus `witness.search.json`, and is not promised to pass. Its
defaults are 128 initial profiles, eight full-protocol finalists, and at
most eight workers. You may replace its search strategy; only your JSON
witness is graded. Keep generator concurrency at most eight and BLAS
threads at one. The participant search allowance is 3,600 seconds; search
code and search time are not fields that a static witness can certify.

The independent evaluator command, from the package root, is:

```bash
python -I -B evaluator/evaluate.py participant/witness.json --output report.json
```

The runner uses Python isolated mode (`-I`) so participant-controlled working
directories and `PYTHONPATH` cannot inject modules; `-B` disables bytecode
writes. The interpreter, installed dependencies, and evaluator directory are
trusted and must not be participant-writable. It performs 33 full float64
symmetric diagonalizations with SciPy `evr`
(base plus 32 perturbations), one worker and one BLAS thread, with a
180-second wall limit and 2-GiB address-space ceiling. JSON results always
include `core`, `worst_family`, `resource`, `pass`, `valid`, and `reason`.
Numeric thresholds are fixed; there is no runtime ranking bonus. Resources
are evaluator observations, never participant assertions. A valid result
below target is distinguished from an invalid witness. Tested versions
and reproducibility hashes are recorded by the author outside participant
materials. No private search results are needed to use this helper.

The report also exposes `core_score = core`, `worst_family_score = worst_family`,
and `passed = pass`. `runtime_seconds` equals `resource.wall_seconds`.
`evaluator_valid` is true for a completed grading decision, including rejection
of invalid input, and false for an internal `evaluator_error`. `resource_score`
is 1.0 for a valid witness evaluated within the prescribed resource limits and
0.0 otherwise; it does not change any scientific acceptance criterion. These
keys are present on error reports too, with null scientific scores when no
score can be computed. The CLI takes a positional witness-file path, not a
submission directory; the runner should pass `SUBMISSION_DIR/witness.json`.
