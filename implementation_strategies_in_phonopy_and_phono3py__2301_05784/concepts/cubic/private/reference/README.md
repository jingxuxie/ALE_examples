# Cubic pilot: private author notes

Only `participant/` is public. `attempt/` must remain empty until the runner
launches a participant. This directory, all measurements, the challenge manifest,
and all reference/baseline archives are author-only. No fresh agent was launched
while constructing this pilot. The participant starter is an original restricted
NumPy wrapper, not an upstream checkout and not a claim about an exact historical
release's Python behavior.

## Ground truth and provenance

The oracle calls **the installed official C functions**, not the upstream Python
`RealToReciprocal` implementation:

- `r2r_real_to_reciprocal`, with `AtomTriplets.make_r0_average=1`, supplies the
  complex tensor. Its compound atom/Cartesian layout is transposed only for the
  public archive convention.
- `reciprocal_to_normal_squared` supplies the reduced, mass/eigenvector/frequency
  contracted squared matrix element. Its all-band output has no unit conversion,
  occupation, mesh normalization, or transport integration added.
- `phono3py._phono3py.interaction` crosschecks **both flags on each private case**,
  including the actual rational noncommensurate triplets and supplied modes.
- Independent `Phono3py(..., make_r0_average=False/True)` instances, using a real
  5x5x5 grid and `Interaction.run(lang="C")`, check flag propagation, numerical
  distinction, and agreement with the direct tensor/normal-mode C functions.
  The high-level interaction's recorded unit conversion is divided out.

The runtime is `author/runtime`: phono3py **3.19.2**, phonopy **2.43.4**, spglib
**2.5.0**. Actual imported versions are asserted; the runtime contains an old
spglib dist-info directory as well, so package metadata alone is not trusted.
The oracle library SHA256 is recorded in the audit.

Exact release source commits:

- phono3py v3.19.2: `5a4fd11f713ee1457fe4eabea84f1dfa89a685df`.
- phonopy v2.43.4: `aedd2502d98f8e5c4e881c6d6b4edd20f2d00f44`.

The source worktrees used for the official datasets are newer and are **not**
misrepresented as those runtime releases:

- `author/source/phono3py`: `49e7d7225a8931df59ed2f4603344ea8d89846f2`.
- `author/source/phonopy`: `435b32225a26446a3b2b5e2a63c7bfd700583219`.

The audit records source commits, exact paths, dataset/check-out SHA256 values,
and the separately retrieved pinned `c/real_to_reciprocal.c` SHA256. The latter
is retained privately as `real_to_reciprocal-3.19.2.c`; it is not compiled or
exposed. Its immutable source location is
`https://raw.githubusercontent.com/phonopy/phono3py/5a4fd11f713ee1457fe4eabea84f1dfa89a685df/c/real_to_reciprocal.c`.
ABI declarations were checked against the release's
`c/real_to_reciprocal.h` and `c/reciprocal_to_normal.h`. Additional relevant files
are `c/reciprocal_to_normal.c`, `c/interaction.c`, `c/_phono3py.cpp`,
`phono3py/phonon3/interaction.py`, `phono3py/api_phono3py.py`, and phonopy's
`phonopy/structure/cells.py`, `phonopy/harmonic/dynamical_matrix.py`, and
`phonopy/harmonic/force_constants.py`.

The release history is documented at
`https://phonopy.github.io/phono3py/changelog.html`: the three-origin behavior was
introduced in 2.9.0 (December 25, 2023), became the actual default in 3.0.2
(April 21, 2024), was accidentally disabled from 3.16.0, and was restored in
3.23.0 (January 5, 2026). That command-line history is **not** used as evidence
that the 3.19.2 explicit API flag works; the numerical on/off tests provide that
evidence. The relevant gap is interpolation, not a full thermal-transport task.

## Cases and physics

The initial manifest is a JSON **list**, with six `pool` and six independent
`heldout` cases: NaCl, AlN, and Si, each in compact and full storage. Each case
contains ten triplets. The underlying supercells are 64 atoms (NaCl and Si) and
72 atoms (AlN), realistic order-100 cells, **not** artificially padded 100-atom
tensors. All three families have tied shortest images and nonconsecutive
representative mappings. AlN has a four-atom non-cubic primitive cell; the other
two have two-atom FCC-derived primitive cells.

Exact official datasets in the phono3py source checkout:

- NaCl: `test/phono3py_params_NaCl222.yaml.xz`.
- AlN: `test/phono3py_params_AlN332.yaml.xz`.
- Si: `test/phono3py_si_pbesol.yaml` and `test/FORCES_FC3_si_pbesol`.

The pinned `phono3py.load` traditional finite-displacement solver and force-
constant symmetrization reconstruct both orders from these real force datasets.
Full cubic arrays are expanded from compact arrays using the official primitive
atomic translation permutations; representative rows, both independent atom/
Cartesian swaps, and compact/full reciprocal outputs are checked. No random
force tensors are generated. Harmonic eigenpairs are computed from the same
official model, with NAC explicitly disabled. Randomness is limited to seeded
wavevectors and arbitrary unit-modulus eigenvector column phases.

The two splits use independent seed sequences (730201 and 918427), not a slice
of one shared triplet batch. They share the physical models deliberately, but
not the challenge inputs or mode gauges. Every batch includes noncommensurate
momentum-conserving triplets, conjugate/permuted geometry, a nonzero reciprocal
sum, and a Gamma leg. The full-layout cases additionally place a real frequency
exactly at the cutoff. The single public smoke input has no output label and
uses its own seed.

The canonical C tensor explicitly sums all three origins (the `all_shortest`
shortcut mask is zero). The optimized mask from the official `Interaction`
object is independently checked to give the same result on these symmetric
force constants. This avoids defining a target by a shortcut's roundoff.

## Validation and scoring

`manifest.audit.json` contains per-case measurements and numerical residuals:

- Direct C-on versus C-off; NumPy baseline versus C-off.
- Direct C tensor contraction versus monolithic C interaction, both flags.
- Literal mathematical amplitude average versus the C tensor, and independent
  NumPy contraction versus the C strength.
- Conjugation/time reversal; cyclic and transposition leg covariance; eigenmode
  phase invariance; reciprocal-lattice gauge covariance and strength invariance.
- Uniform mass and force-constant scaling; compact/full equivalence;
  optimized/unoptimized shortest-image handling.
- Physical dynamical-matrix eigenpair residuals and eigenvector unitarity;
  actual low-frequency masking plus negative/zero/equal-cutoff edge probes.
- Component-isolated invalid-output checks and a continuous score-response curve.

For each output, error is the root mean over triplets of squared relative RMS
error, using each reference triplet's RMS scale (a global relative `1e-12` RMS
floor handles exactly zero reference triplets). The component quality is
`1/(1 + actual_error/measured_weak_error)`. There is no accuracy-tolerance
plateau or binary success decision. The weak reference scores exactly 0.5;
stored truth scores exactly 1.0. Invalid outputs score zero in only that
component. `private/evaluator.py` exports
`score_case(actual, reference, baseline, case, input_data)` and the common
`author/evaluation.py` can import it directly. Manifest filenames are relative
to `private/`; `keys` names the two separate outputs.

## Reproduction

Run from the task target directory. All generated files stay under
`concepts/cubic/`; no source or shared directory needs modification.

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  python -B concepts/cubic/private/reference/build.py \
  > concepts/cubic/private/reference/build.log 2>&1

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  python -B concepts/cubic/private/evaluator.py --split all \
  --output concepts/cubic/private/reference/baseline-evaluation.json
```

`build.py` privately prepends `author/runtime` to its own import path; it runs
the public baseline with a clean `PYTHONPATH`. NumPy 1.21.5 from system Python is
sufficient for the participant. The audit lists exact oracle dependencies;
measurement additionally requires GNU time and sandbox evaluation requires the
main helper and bubblewrap. Limits are 180 seconds, 8192 MiB, one BLAS/OpenMP
thread per case. Direct trusted CLI measurements and sandbox timings are labeled
separately; there is no claim that direct timing alone establishes isolation.

Fresh heldout generation, retaining the original manifest and pool:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  python -B concepts/cubic/private/reference/build.py --split heldout \
  --heldout-seed 271828 --manifest challenge_pool/fresh-heldout-271828.json \
  > concepts/cubic/private/reference/fresh-heldout-271828.log 2>&1
```

Use a new heldout seed rather than tuning against the initial heldout. This
command does not rewrite the public smoke input. To run a trusted oracle CLI
directly (never as a participant sandbox submission):

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="$PWD/author/runtime" python -B \
  concepts/cubic/private/reference/solve.py INPUT.npz OUTPUT.npz
```

Both solver entry points use the required positional input/output interface.
The retained `probe.py` is an author diagnostic, not a starter or a solution
intended for the participant. The `attempt/` directory is intentionally empty.

## Resolved build issues and limits

The partial source checkout did not contain every release-tag blob; provenance
does not lazily fetch into or modify that checkout. The needed pinned C body was
retrieved into this private directory instead. Upstream primitive maps in this
runtime are int32, while the phono3py C ABI requires int64: the builder explicitly
normalizes both maps, which also enforces the public input contract. The initial
private monolithic-API probe crashed before that normalization; subsequent
successful validation, not that failed probe, is the oracle evidence.

The task intentionally omits NAC, transport, fitting, isotope scattering, and
arbitrary material families. It uses 64/72-atom official supercells rather than
claiming a 100+ atom force calculation that is not present in the source data.

## Recorded initial measurements

The initial 12-case build took 65.480 seconds with 326912 KiB peak resident
memory. Trusted baseline CLIs took 0.251–6.452 seconds per case, with 114576 KiB
maximum RSS; trusted oracle CLIs took 0.260–1.334 seconds, with 126568 KiB maximum
RSS. The separate bubblewrap evaluation completed all 12 cases successfully,
scoring exactly 0.5 for each component in every case. Its per-case wall times
and RSS are recorded in `baseline-evaluation.json`. The public smoke CLI also
produced finite outputs with the specified shapes and dtypes.

The largest direct-tensor versus literal-average relative residual was
`1.665e-15`; direct C contraction versus monolithic C interaction was at most
`2.304e-15`. The independent explicit high-level API off/on relative strength
differences were NaCl `0.0182063`, AlN `0.00963703`, and Si `0.00249335`.
Stored reference self-scores are exactly 1.0 in the manifest.

The first attempt to nest bubblewrap inside the coding sandbox failed before
executing any solver (`NETLINK_ROUTE: Operation not permitted`). That report is
retained as `baseline-evaluation-outer-sandbox.json`, not presented as a baseline
numerical failure. The successful evaluation was rerun outside the outer coding
sandbox, preserving the common helper's own bubblewrap isolation and limits.
Run the documented evaluation command in a normal host shell, or approve the
outer-sandbox escalation when using the coding environment.
