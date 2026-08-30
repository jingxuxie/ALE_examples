# Witness contract and workspace API

## Physical problem and normalization

There are six orthonormal spin-orbitals, indexed 0 through 5, and three fermions.
The reference occupies 0, 1, 2. No spin adaptation, spatial symmetry, Coulomb
representability, or locality is required. This is a general real,
number-conserving one-/two-body fermion Hamiltonian, not a molecular geometry
challenge. All arithmetic is double precision and all energy quantities use the
same dimensionless units.

The fixed canonical Fock eigenvalues are `[-1.2,-0.9,-0.5,0.5,0.9,1.2]`.
Consequently the canonical occupied–virtual gap is exactly one: neither an energy
shift nor overall scaling can trivialize the energy threshold. The search variable
is a symmetric real 15 by 15 matrix `pair_matrix`, in lexicographic unordered-pair
order `(0,1),(0,2),...,(4,5)`.

For ordered pairs `p<q` and `r<s`, set the antisymmetrized integral
`v[p,q,r,s] = pair_matrix[pair(p,q),pair(r,s)]`, extending by antisymmetry within
each pair. Define

```
h[p,q] = epsilon[p] delta[p,q] - sum(i=0,1,2) v[p,i,q,i]
H = sum(p,q) h[p,q] a_p^dagger a_q
    + sum(p<q,r<s) pair_matrix[pq,rs] a_p^dagger a_q^dagger a_s a_r
```

There is no extra factor of 1/4 in this unordered-pair expression. This is
equivalent to the usual factor of 1/4 with unrestricted antisymmetric indices.
The counterterm makes the reference Fock matrix canonical, but does **not**
guarantee its stability; that is tested separately.

## Exact amplitude convention and equations

Determinants are increasing integer bit masks with exactly three set bits.
For each excitation, form `a_a^dagger a_i` or
`a_a^dagger a_b^dagger a_j a_i` with `i<j` and `a<b`, then multiply by its sign on
the reference so its reference-column nonzero entry is **+1**. Call the resulting
signed generator `X_mu` and its determinant `D_mu`.

The 18 amplitudes follow this order: singles, with occupied index outermost and
virtual index innermost (9 entries); then doubles, lexicographic occupied pairs
outermost and virtual pairs innermost (9 entries). `oracle.labels`,
`oracle.targets`, and `oracle.generators` expose the convention explicitly.
These signed-determinant amplitudes need not have the same signs as an external
tensor implementation's amplitudes.

```
T = sum(mu) amplitudes[mu] X_mu
Hbar = exp(-T) H exp(T)
R_mu = <D_mu|Hbar|reference>
Ecc = <reference|Hbar|reference>
J_mu,nu = <D_mu|[Hbar,X_nu]|reference>
g_nu = <reference|[Hbar,X_nu]|reference>
J^T lambda = -g
right = exp(T)|reference>
left = (<reference| + sum(mu) lambda_mu <D_mu|) exp(-T)
gamma[p,q] = left a_p^dagger a_q right
```

CC stationarity is evaluated at the **submitted** amplitudes. The evaluator does
not repair them or accept energies, lambda amplitudes, RDMs, or claimed scores.
Since all generators excite the reference, the finite nilpotent exponential is
exact; the supplied oracle is not a low-order Taylor approximation. It includes
the full 20-determinant space, including triples outside the CCSD projection.

## Single target: real-orbital population violation

Let `S=(gamma+gamma.T)/2`. For every normalized **real** orbital coefficient vector
`u`, the lambda population is `u.T @ gamma @ u = u.T @ S @ u`. Define

```
delta = max(0, -eigvalsh(S)[0], eigvalsh(S)[-1] - 1)
```

The target is `delta >= 0.02`. Eigenvalues of nonsymmetric `gamma` are **not**
used as occupations. Merely exhibiting antisymmetry, complex RDM eigenvalues,
or complex EOM eigenvalues does not pass. The symmetrized spectrum is an
operational test of real orbital populations, not a claim that symmetrization
turns the lambda density into a valid many-body state. The exact FCI density and
the normalized right-state density are physical comparison objects.

The final unsymmetrized density must additionally pass the **density asymmetry
diagnostic (DAD)** screen:

```
DAD = np.linalg.norm(gamma - gamma.T, ord="fro") / np.sqrt(3)
DAD <= 0.001
```

This uses the complete Frobenius norm, not the largest matrix entry and not the
norm of the already symmetrized density. `rdm_dad` reports this value;
`rdm_antisymmetry` remains the separate legacy max-entry diagnostic. The DAD bound
is an endpoint screen only; the fixed path certificate is unchanged. The target
is still the single population-violation target, not an optimization of DAD.

## Fixed admissibility constraints

`constraints.json` is the machine-readable threshold reference. No conditions
are secret. Upper and lower bounds are inclusive, with no additional scoring
slack at scientific thresholds.

| Quantity | Requirement |
|---|---:|
| Maximum absolute pair-matrix entry | <= 1.5 |
| Pair-matrix Frobenius norm | <= 7 |
| Pair-matrix symmetry error | <= 1e-12 |
| Amplitude Euclidean norm | <= 1.25 |
| CC residual infinity norm | <= 2e-9 |
| Lambda stationarity infinity norm | <= 2e-9 |
| Absolute CCSD–FCI ground energy error | <= 1e-4 |
| Squared normalized CC-right/FCI-ground overlap | >= 0.999 |
| FCI-ground reference-determinant weight | >= 0.45 |
| Exact ground/first-excited gap | >= 0.1 |
| Minimum real-orbital HF Hessian eigenvalue | >= 0.05 |
| Minimum imaginary-orbital HF Hessian eigenvalue | >= 0.05 |
| Spectral condition number of CC Jacobian | <= 100 |
| Lambda Euclidean norm | <= 1.5 |
| Density asymmetry diagnostic `rdm_dad` | <= 0.001 |
| Minimum real part of any EOM Jacobian eigenvalue | >= 0.05 |

HF Hessians are second derivatives of the determinant energy under
`exp(sum(theta_mu K_mu))`, for the nine signed singles generators and respectively
`K_mu=X_mu-X_mu.T` and `K_mu=i(X_mu+X_mu.T)`. Both blocks are tested, covering real
and imaginary occupied–virtual rotations. The Fock matrix, reference gradient,
and Hamiltonian Hermiticity are recomputed to absolute tolerance 2e-10. These are
local stability conditions, not global-HF-optimality claims.

The evaluator also requires biorthogonal normalization and RDM particle number
within 2e-8, and physical exact-state RDMs within 2e-9. These are oracle consistency
checks, not alternative targets. An internally nonfinite result is always a failure.

## Ground-connected root certificate

At the 65 fixed points `s=k/64`, for `k=0,...,64`, use `pair_matrix(s)=s*pair_matrix`
and reconstruct `h(s)` with the **same** canonical energies. Independently solve
CCSD at `s=0` from zero amplitudes and use the preceding root as the initial
condition at each next point. At every point require:

- CC residual infinity norm <= 2e-9;
- squared exact-ground overlap >= 0.995;
- exact ground gap >= 0.08;
- smallest singular value of the CC Jacobian >= 0.02;
- consecutive amplitude-vector Euclidean displacement <= 0.25.

The final path amplitudes must match the submitted amplitudes within 5e-7 in
infinity norm. The evaluator uses deterministic analytic-Jacobian root solves,
`scipy.optimize.root(method='hybr', xtol=2e-11, maxfev=250)`, and fails closed on a
failed path. This finite certificate is the task's precise definition of
ground-connectedness; it is not a proof of an unsampled continuum property.
The endpoint fidelity and exact gap independently exclude accidental excited roots.

## JSON artifact

Exactly these four keys are accepted:

```
{
  "schema_version": 1,
  "orbital_energies": [-1.2, -0.9, -0.5, 0.5, 0.9, 1.2],
  "pair_matrix": [[15 finite numbers], ... 15 rows ...],
  "amplitudes": [18 finite numbers]
}
```

The complete runnable zero-interaction example is `example.json`; it is valid but
does not meet the violation target. Files must be UTF-8 JSON, at most 65536 bytes.
Missing/extra/duplicate keys, booleans used as numbers, strings used as numbers,
wrong dimensions, NaN, infinity, and changed canonical energies are rejected.
Values within the symmetry tolerance are averaged with their transpose before
evaluation. No executable artifact or pickle format is accepted.

## Public numerical API

Use Python 3.10 or later with NumPy and SciPy; no pdaggerq compilation is needed.
For many small solves set `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, and
`MKL_NUM_THREADS=1` **before** starting Python. This avoids thread-launch overhead.

From `participant/`:

```
bash baseline/run.sh --trials 10000 --seed 20260828 --output submission.json
python workspace/probe.py submission.json --continuation
```

Add `workspace/` to Python's import path. The principal calls are:

- `DeterminantCC(orbitals=6, electrons=3)`: initialize cached operators.
- `.hamiltonian(epsilon,V)`: return `(H,h,v)` in the stated convention.
- `.solve(H,initial=None)`: solve stationary CCSD; check `.converged` and `.residual`.
- `.equations(H,t)`: return `(residual,J,Hbar,exp(T),exp(-T))` at any `t`.
- `.lambda_state(result)`: return `(lambda,left,stationarity_error)`.
- `.rdm(left,right)`: return the unsymmetrized one-particle density.
- `.hf_stability(H)`: return the real and imaginary Hessian blocks.
- `.diagnostics(H,result)`: compute exact-state and CC diagnostics.
- `.continuation(epsilon,V,steps=64)`: numerical path solver; its low-level default
  is 12 steps, so explicitly pass 64. It returns `(result,history)`.
- `api.screen(V,initial=None,oracle=None)`: solve and apply endpoint screens.
- `api.check_continuation(V,t,oracle=None)`: check the complete public path certificate.
- `api.artifact(V,t)`: construct the JSON-serializable artifact object.

The low-level oracle is a search aid, not a strict parser or official evaluator.
`screen` checks endpoint constraints only; a successful `screen` is not a pass.
You may change or replace your workspace code, but doing so cannot change the
trusted evaluator, its thresholds, or its independent operator construction.

## Scoring and evaluation

The evaluator reports `core_score=delta` for an admissible artifact and zero
otherwise, `score=min(1,core_score/0.02)`, `passed`, `reason`, `runtime_seconds`,
the worst normalized constraint margin, and detailed recomputed diagnostics.
Passing requires all admissibility constraints and `delta>=0.02`. Diagnostics
report the raw violation even for failed endpoint screens when it can be safely
computed. A malformed input or timeout has score zero. Evaluation has a 45-second
wall-clock worker limit and never executes submitted code.

## Scientific provenance and sanity checks

The seed is N. C. Rubin and A. E. DePrince III, arXiv:2106.06850v3, Section II.B,
the CC Lagrangian and unrelaxed RDMs. The associated official `edeprince3/pdaggerq`
source snapshot is commit `843b11aad9cbea253b233c2fcdb7049c1fec7266`.
This challenge's screening heuristic, thresholds, and domain are supplied by the
task author, not stated or proved by that paper.

The DAD screen is motivated by Weflen et al., arXiv:2503.20006v2 (May 7, 2025),
*Exploiting a Shortcoming of Coupled-Cluster Theory: The Extent of non-Hermiticity
as a Diagnostic Indicator of Computational Accuracy*, Eq. (4). Its Frobenius
normalization uses the number of correlated electrons, here all three. This
challenge tests a task-supplied stronger heuristic combining that diagnostic with
the other screens; it does not attribute a representability theorem or the
numerical cutoff 0.001 to either source.

The oracle was checked on two-electron systems where CCSD spans FCI, including
energy, density, and EOM spectra; against finite-difference energy derivatives
for lambda; against finite differences for real and imaginary HF stability;
and against positivity of exact-state RDMs. The trusted evaluator instead builds
full 64-dimensional Fock-space operator products, projects the particle sector,
and uses matrix exponentials, providing an independent numerical cross-check.
