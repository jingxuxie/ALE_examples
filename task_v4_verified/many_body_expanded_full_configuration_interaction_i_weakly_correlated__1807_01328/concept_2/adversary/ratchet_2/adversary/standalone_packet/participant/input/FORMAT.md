# Exact model, artifact, perturbations, and scoring

All energies and coefficients are in hartree (Eh); one microEh is 1e-6 Eh.
`target.json` is the nominal mathematical source of truth. `assay_spec.json`
overrides its legacy nominal-only resource fields for the two-family evaluator.

## 1. Fixed model and adjustable center

There are ten spatial orbitals, occupied labels O={0,1,2} and virtual labels
V={3,4,5,6,7,8,9}. The seven-by-seven submitted matrices use local virtual labels
0,...,6, corresponding to global labels 3,...,9. Exactly three electron pairs
(six electrons) occupy distinct orbitals. Only the seniority-zero subspace is
used: each orbital is either empty or doubly occupied. The full dimension is
binomial(10,3)=120. Unpaired sectors are not included in the gap test.

Let N_p count a pair on spatial orbital p and P_p^dagger create that pair. The
effective Hamiltonian is

    H = sum_p epsilon_p N_p
        + sum_{p<q} U_pq N_p N_q
        + sum_{p<q} t_pq (P_p^dagger P_q + P_q^dagger P_p).

The matrices t and U are real symmetric, with zero diagonals. In a three-pair
occupation state the diagonal energy is the sum of its three epsilon values
plus its three unordered density interactions. A single pair transfer has the
corresponding t coefficient; there is no extra factor of two. The epsilon
parameters are pair energies, not one-electron orbital energies to be doubled.

At the nominal center, epsilon, the 3-by-7 OV transfer block, and every density
coefficient with at least one occupied index are fixed by `target.json`. The OO
transfer block is zero. The submitted 21 upper-triangle VV transfers and 21 VV
density coefficients are the only adjustable nominal controls. Their bounds are
|t_pq| <= 0.45 Eh and |U_pq| <= 0.60 Eh. There is no positivity or Coulomb-integral
representability constraint beyond the specified effective model.

## 2. Subsystems, signed increments, and the precise gate

For each subset S of the seven virtual labels, restrict the available orbitals
to O union S while retaining exactly three pairs and all coefficients among the
retained orbitals. E(S) is the smallest eigenvalue in that subspace. E(empty) is
the energy of the reference occupation |0,1,2>. Define

    c(S) = E(S) - E(empty),
    Delta(S) = c(S) - sum_{nonempty T proper-subset S} Delta(T),
    E3 = E(empty) + sum_{1 <= |S| <= 3} Delta(S),
    tail = abs(E(V) - E3),
    parent = max_{|S|=3} abs(Delta(S)),
    ratio = tail / max(parent, 1e-10 Eh).

Increments are signed. E3 is not assumed variational. The gate discards a
four-virtual tuple if the largest absolute increment among its four triple
parents is <= 1e-6 Eh. Requiring all 35 triple increments <= this threshold
causes every four-virtual tuple to be discarded. Single and pair increments are
computed but are not required to be <= the triple threshold.

The nominal witness conditions are parent <= 1e-6 Eh, tail >= 50e-6 Eh, and
ratio >= 100. Every tested Hamiltonian must also satisfy:

- Squared ground-state amplitude of |0,1,2> >= 0.95.
- Difference between the lowest two full seniority-zero eigenvalues >= 0.4 Eh.
- Every other full occupation-state diagonal exceeds the reference diagonal by
  at least 0.6 Eh.

The same fixed reference occupation and orbital labels are used after noise;
the reference energy is recomputed, not held at its nominal value. No orbitals
are reoptimized or relabeled. Eigen residual, complete-MBE closure, nested-space
variational consistency and independent full-energy solver agreement must each
be <= 5e-10 Eh. Nonfinite values invalidate evaluation.

This supplied gate is an explicit model test inspired by max-parent screening
and signed increments, not a literal reproduction of every adaptive choice of
an ab initio algorithm. Neither the task nor a finite witness proves a universal
screening theorem or attributes such a theorem to the motivating paper.

## 3. Static JSON artifact

Write a regular UTF-8 file named `witness.json` at the writable work root. The
only allowed top-level keys are `schema_version`, `virtual_hopping`, and
`virtual_density`. `schema_version` must be integer 1, not boolean. Each matrix
must be a JSON array of seven rows, each containing seven finite JSON numbers.
Entries must be exactly symmetric after parsing; diagonals must be exactly
zero. Bounds apply to every entry. Duplicate keys, extra fields, booleans as
coefficients, NaN, Infinity, wrong dimensions, symlinks, nonregular files and
files larger than 32768 bytes are rejected. Do not include claimed energies,
scores, code, additional center controls, or perturbation directions.

`baseline_witness.json` is the exact zero-control example of this schema. It is
physically admissible but is not supplied as a passing witness.

## 4. Two independent finite robustness families

Both families use radius delta=0.001 Eh, 128 cases, and at least 122 successful
cases. The hidden VV and full pools are independent of one another and of all
public training directions. They are drawn once and frozen before a fresh
attempt. Their commitment is in `assay_spec.json`; their coordinates are private.

For a bounded coefficient theta with bound B and uniform coordinate u in [0,1),
use exactly

    lower = max(-B, theta - delta),
    upper = min(+B, theta + delta),
    theta_prime = lower + u * (upper - lower).

This samples uniformly on the truncated interval. It does NOT clamp a draw from
the untruncated interval and create point masses at the bounds. Mirror the value
to the opposite triangle; both matrix diagonals remain zero. The same hopping
bound 0.45 and density bound 0.60 apply to all blocks, including formerly fixed
coefficients. Each epsilon independently becomes

    epsilon_prime = epsilon + delta * (2*u - 1).

Epsilon values have this bounded local interval and no additional absolute box.
Every coordinate and case is independently centered on the submitted nominal
Hamiltonian, never on an earlier draw. Physical failures are counted as failures,
not rejected or replaced. A numerical verification failure invalidates the
entire evaluation rather than becoming evidence of a physical effect.

### Family `vv`: 42 coordinates

Only VV t and U change; all other coefficients remain at their nominal values.
Coordinates 0,...,20 enumerate t on pairs of local virtual labels in
lexicographic order: (0,1),(0,2),...,(0,6),(1,2),...,(5,6).
Coordinates 21,...,41 enumerate U in the same order.

### Family `full`: 100 coordinates

Coordinates 0,...,9 are epsilon_0,...,epsilon_9. Coordinates 10,...,54 enumerate
all 45 t upper-triangle pairs of global labels in lexicographic order:
(0,1),(0,2),...,(0,9),(1,2),...,(8,9). Coordinates 55,...,99 enumerate all 45 U
pairs in the same order. Thus previously zero OO transfers can be perturbed.
All 100 coefficients means all coefficients of this restricted effective
Hamiltonian, not all integrals of a general molecular electronic Hamiltonian.

Passing these fixed finite assays is the objective. It is not a claim of
universal box robustness or a population-level 95-percent confidence guarantee.

## 5. Public tools and API

From the writable work root, with `participant/` read-only:

    python -B participant/workspace/baseline.py --output witness.json
    python -B participant/workspace/check.py witness.json --report diagnostic.json
    python -B participant/workspace/check.py witness.json --seed 12345 --samples 64

Run subprocesses with stdin closed when applicable. A checker call evaluates the
nominal center and both public families. `--samples` is the count PER family.
Defaults use the stored 64-row-per-family public pools. Custom nonnegative
integer seeds and 1 through 512 samples per family are supported. Public pools
are generated using `numpy.random.SeedSequence(seed).spawn(2)`, assigning the
first child to `vv` and the second to `full`; each child drives
`numpy.random.Generator(numpy.random.PCG64(child)).random((count,dimension))`.

With `participant/workspace` on the import path:

- `model.load_witness(path)` loads the strict JSON object.
- `model.decode_witness(candidate)` validates the schema and creates nominal
  full hopping and density matrices.
- `model.full_coefficients(candidate)` returns `(epsilon, hopping, density)`.
- `model.compute(candidate, complete=True)` returns nominal full diagnostics.
- `model.compute_coefficients(coefficients, complete=True)` evaluates a full
  perturbed effective Hamiltonian. `complete=False` computes only orders <=3
  plus the full ground state and does not provide a closure diagnostic.
- `assay.training_uniforms(seed=None, samples=None)` returns a dict with `vv`
  and `full` NumPy arrays of shapes `(count,42)` and `(count,100)`.
- `assay.perturb(candidate, uniform_row, family)` returns the corresponding full
  coefficient tuple, without mutating the candidate.
- `assay.evaluate(candidate, pools)` reports nominal and both public assays.

Only the static artifact is official input. These tools neither select the
hidden directions nor guarantee that a public success will pass privately.

## 6. Scores, validity, and limits

For a physically and numerically valid nominal case, let

    nominal_score = min(1, 1e-6/max(parent,1e-10), tail/50e-6, ratio/100),
    vv_score = min(1, vv_successes/(0.95*128)),
    full_score = min(1, full_successes/(0.95*128)),
    core_score = (nominal_score + vv_score + full_score)/3,
    worst_family_score = min(nominal_score, vv_score, full_score).

An invalid nominal or any unverified numerical case makes aggregate scores zero
and `valid=false`. A physically inadmissible perturbed case instead counts as an
unsuccessful case; up to six unsuccessful cases per family are permitted.
`passed=true` requires nominal success AND at least 122 successes in EACH family,
not an average across families. Reported family counts include physical validity,
numerical validity, nonexclusive failures, joint failure clusters, metric ranges,
and maximum numerical error. `resource_score=1` means numerical evaluation
completed; it does not mean the witness target passed. Malformed inputs and
worker/resource failures score zero and report the reason.

The evaluator uses only trusted code in an isolated one-thread subprocess with
stdin closed. Limits are 90 seconds wall, 60 seconds CPU, and 512 MiB address
space. No submitted code is executed. The complete packet is self-contained;
NumPy and SciPy are the only numerical dependencies.
