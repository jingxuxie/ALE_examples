# C3-G2-v1 exact protocol: independent replication

This is generation 2 (ratchet 1) of concept_3, Mode B COUNTEREXAMPLE/FALSIFICATION.
Paths refer to `participant/` unless stated otherwise. All numeric physics,
field admissibility, proxy definitions, and discrepancy thresholds are fixed.

## Seed and claim

Pal and Huse, *The many-body localization phase transition*, arXiv:1010.1992v1,
Sections II–III, supplies the periodic random-field Heisenberg model, complete
zero-magnetization sector, adjacent-gap ratio, and middle rank-third reference.
The following uniform proxy-accuracy claim is task-authored, not attributed to
that paper. Structured adversarial fields are allowed. This is a finite-size
counterexample problem, not an IID-disorder average or thermodynamic claim.

**Claim C3-G2-v1:** for every admissible base field profile and every family
in the fixed, committed private replication bank,

`abs(mean_(h' in family) [P(h') - R(h')]) <= 0.050`.

Find a single field profile violating this claim with the stronger robustness
certificate below. The public bank is calibration data only; it does not enter
the grading score. Public and private banks are generated independently by
the same disclosed law. They are not adaptively chosen after submission.

## Hamiltonian and exact reference

Use twelve spin-1/2 sites, periodic boundaries, exchange `J=1`, and

`H = sum_j [Sx_j Sx_(j+1) + Sy_j Sy_(j+1) + Sz_j Sz_(j+1) + h_j Sz_j]`.

Use only the complete `sum_j Sz_j=0` sector, dimension `C(12,6)=924`. Up and
down bits have `Sz=+1/2` and `-1/2`; allowed neighboring spin exchange has
matrix element `1/2`. Do not mix sectors. Sort all 924 eigenvalues increasingly.

For consecutive energies, form adjacent gaps and average
`min(gap[k],gap[k+1])/max(gap[k],gap[k+1])`. Only triplets entirely within the
selected energy list count. With zero-based, stop-exclusive indexing,
`R(h)=r(E[308:616])`: 308 energies, 307 gaps, and exactly 306 ratios.
No unfolding, eigenvectors, missing levels, clipping, or approximate eigensolver
is involved. Every adjacent gap in every full spectrum must exceed `1e-10`.

## Exact proxy

For each target `t` in `(0.49,0.50,0.51)`, set
`e_t=E[0]+t*(E[923]-E[0])`. Choose rank `j_t` minimizing `abs(E[j]-e_t)`, with
ties resolved to the smaller rank. Let `a_t=max(0,min(796,j_t-64))`. Compute
`r_t=r(E[a_t:a_t+128])`, using exactly 126 ratios. Set
`P(h)=(r_0.49+r_0.50+r_0.51)/3`.

The windows may overlap; each receives equal weight even when triplets recur.
They are not three independent statistical samples. Targets, widths, rank
masks, signs, and weights cannot be supplied or modified by a witness.

## Field constraints

The twelve base fields are in site order. Require absolute mean ≤`1e-9`,
maximum absolute field ≤`8.0`, RMS ≥`0.65`, and minimum pairwise separation
≥`0.001`. Mean zero fixes the physically irrelevant uniform-field gauge.

Let `D(h)` be the smallest RMS distance between `h` and `s*g(h)`, over every
cyclic shift and reflected cyclic shift `g`, with `s in {-1,+1}`, excluding
only the identity with positive sign. Require `D(h) >= 0.12`. The negative
sign checks combined field/spin inversion and spatial symmetries as well.
This excludes zero fields and exact or nearly restored spatial symmetries.

Each private derived profile must have absolute mean ≤`1e-9`, maximum absolute
field ≤`8.5`, RMS ≥`0.55`, minimum pairwise separation ≥`1e-7`, and `D(h') >= 0.05`.
A violation in even one derived profile invalidates the witness. Public
calibration uses the same checks on its own profiles. Numerical degeneracy is
invalid, not a counterexample. There are no epsilon denominators.

## Public/private replication law

Each bank has exactly **four families, 32 members per family**, totaling 128
perturbations. For every member, `h'=scale*h+offset`.

| Family | Scale | Amplitude before centering |
|---|---:|---:|
| `jitter_004` | 1.00 | 0.04 |
| `jitter_012` | 1.00 | 0.12 |
| `scale_096` | 0.96 | 0.08 |
| `scale_104` | 1.04 | 0.08 |

Draw a uniform 256-bit seed for each bank independently, and represent it as
64 lowercase hexadecimal characters. For family `FAMILY`, member `MEMBER`
in `0..31`, and site `SITE` in `0..11`, hash the ASCII string

`SEED_HEX|FAMILY|MEMBER|SITE`

with SHA-256. Interpret the first eight digest bytes as an unsigned big-endian
integer `n`, and compute `u=2.0*n/(2^64-1)-1.0` in float64. For that member,
`offset_j=amplitude*(u_j-mean(u))`. Centering can produce component magnitudes
up to twice the pre-centering amplitude. Family/member/site labels provide
separate pseudorandom draws; there is no witness-dependent randomness.

The literal public offsets and public seed are in `input/protocol.json`.
The private seed and offsets are not supplied to participants. They use the
same family counts, scales, amplitudes, conversion, and centering law, with
a different independent seed. `input/commitment.json` publishes the SHA-256
of the exact UTF-8 bytes of the private protocol JSON, including its trailing
newline. The evaluator compares those bytes with a trusted copy of this
commitment before any diagonalization. A mismatch is an evaluator error,
never a participant failure or a reason to resample. Neither bank is changed
after its commitment, and neither bank is the earlier generation's probes.

## Fixed objective and pass conditions

The witness chooses one integer orientation `s in {-1,+1}`. Define
`d(h')=s*(P(h')-R(h'))`. For each private family, `B_F` is the mean over all
32 members. All comparisons are inclusive and all conditions are mandatory:

- `core=mean_F B_F >= 0.060`.
- `worst_family=min_F B_F >= 0.050`.
- Unperturbed base `d(h) >= 0.055`.
- In every private family, at least 24/32 members have `d(h') >= 0.025`:
  coverage fraction at least 75%.
- Every schema, field, spectrum, and resource constraint passes.

The base is not included in the family mean. Do not take absolute values or
switch orientation per member. There is no selection of a favorable family
or subset of members. The core threshold forces at least one family to
contradict the 0.05 claim; the remaining criteria enforce replication.
No confidence interval or thermodynamic conclusion is claimed for this
deterministic finite certificate. Public scores are search diagnostics, not
an alternative acceptance route or an additional required grading gate.

## Static interface and resources

The witness must be a regular UTF-8 JSON file, at most 16,384 bytes, with
exactly `schema_version` (integer 1), `fields` (twelve finite JSON numbers),
and `orientation` (integer -1 or +1). Booleans and numeric strings do not
count as numbers. Extra or duplicate keys, nonfinite constants, malformed
JSON, symbolic links, pipes, directories, and code payloads are rejected.
No supplied code, paths, eigenvalues, or claimed scores are executed or trusted.

The public helper offers `spectrum`, `proxy_statistics`, `validate_witness`,
`family_fields`, `validate_protocol`, and `assess(witness, protocol)` using
the public protocol. It supports all 32 members in each family. The trusted
evaluator has its own physics copy and exclusively uses the committed private
protocol. Modifying public files cannot modify grading or reveal its probes.

From the participant directory:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python baseline/solve.py --output witness.json
```

The baseline is the original public unstructured-search algorithm, not a
previous champion or a witness-seeded solver. It screens 128 profiles and
checks eight finalists on the public bank. Its search report is explicitly
public-calibration feedback; success there does not establish a private pass.

The main runner invokes, from the generation_2 package root:

```bash
python -I -B evaluator/evaluate.py SUBMISSION_DIR/witness.json --output report.json
```

This is a positional witness-file CLI, not a directory or `--submission` CLI.
The interpreter, dependencies, and evaluator files are trusted; only
participant assets are exposed to solvers. Isolated mode ignores participant
`PYTHONPATH` and working-directory modules. The evaluator reports aggregate
private scores, not offsets, seeds, per-probe spectra, or per-probe diagnostics.

Reports include `core`, `worst_family`, `pass`, `valid`, `reason`, `resource`,
plus aliases `core_score`, `worst_family_score`, `passed`, and `runtime_seconds`.
`evaluator_valid` is true for a grading decision, including invalid input,
and false for an internal/commitment error. Uncomputed scientific scores are
null. `resource_score` is 1.0 for a valid witness evaluated within limits and
0.0 otherwise. All aliases are present on error reports too.

Search allowance is 3,600 seconds, maximum eight generator workers and one
BLAS thread each. Grading uses 129 full float64 SciPy `evr` diagonalizations
(base plus 128 private perturbations), one worker, one BLAS thread, a
180-second wall limit, and a 2-GiB address-space ceiling. Invalid inputs can
be rejected before any diagonalization. No target is adjusted at runtime.
