# Input, mathematics, and API

## Scientific scope

This is a finite-cutoff, constant-density-of-states Fermi-surface-patch reduction
of Margine and Giustino, arXiv:1211.3345v1, Eqs. (18), (21)–(23), published as
Phys. Rev. B 87, 024505 (2013), DOI `10.1103/PhysRevB.87.024505`.
The EPW follow-up is Lee et al., *Electron–phonon physics from first principles
using the EPW code*, npj Computational Materials 9, 156 (August 25, 2023),
DOI `10.1038/s41524-023-01107-3`, superconductivity/computational considerations.
These sources motivate self-consistent numerical imaginary-axis solutions;
the benchmark is an independently written synthetic discretization, not EPW
output or a claim of ab initio predictions for specific materials.

Wannier interpolation and electronic/phononic preprocessing are out of scope.
The input contains the resulting model interaction and Fermi-surface weights.
We retain anisotropy within and between bands. Finite positive sums below are
the exact problem: do not replace the cutoff, quadrature, kernel, or interaction.
Convergence to the infinite-cutoff continuum is not what is scored.

## Public instance NPZ

Load with `numpy.load(path, allow_pickle=False)`. There are exactly seven fields:

| Key | Shape | Meaning |
| --- | --- | --- |
| `temperature` | scalar float | Temperature in energy units, k_B = 1 |
| `n_freq` | scalar integer | Number N of positive Matsubara frequencies |
| `weights` | (P,) | Strictly positive patch quadrature weights, sum = 1 |
| `omega` | (S,) | Strictly positive Einstein-mode energies |
| `coupling` | (S,P,P) | Symmetric, nonnegative, dimensionless unweighted A[s,a,b] |
| `coulomb` | (P,P) | Symmetric nonnegative effective repulsion mu[a,b] |
| `initial_delta` | (P,N) | Public starting guess, not a solution or certificate |

The weight for the incoming patch is **not** absorbed in A or mu. Energy units
are consistent within each instance and arbitrary; there is no Kelvin conversion.
Only public parameters enter the candidate process. Family identifiers, random
seeds, band groupings, eigenvalues, and reference solutions are not inputs.

## Exact finite nonlinear equations

Indices a,b enumerate patches, n,m = 0,...,N-1. Let

    w[n] = pi*T*(2*n+1)
    h[s,n,m,-] = Omega[s]^2 / (Omega[s]^2 + (w[n]-w[m])^2)
    h[s,n,m,+] = Omega[s]^2 / (Omega[s]^2 + (w[n]+w[m])^2)
    Kminus[a,b,n,m] = sum_s A[s,a,b]*(h[s,n,m,-]-h[s,n,m,+])
    Kplus [a,b,n,m] = sum_s A[s,a,b]*(h[s,n,m,-]+h[s,n,m,+])
    R[b,m] = sqrt(w[m]^2 + delta[b,m]^2)
    Z[delta][a,n] = 1 + pi*T/w[n] * sum_bm weights[b]*Kminus[a,b,n,m]*w[m]/R[b,m]
    Phi[delta][a,n] = pi*T * sum_bm weights[b]*(Kplus[a,b,n,m]-2*mu[a,b])*delta[b,m]/R[b,m]
    F[delta] = Phi[delta]/Z[delta]

Solve `delta = F[delta]`, and return `z = Z[delta]`. These are the full signed
Matsubara sums folded using even delta and Z and odd w/R. In particular the
normal equation contains a difference, the anomalous equation a sum, and the
Coulomb term is doubled. The only Coulomb cutoff is the common N-frequency
cutoff, applied to both signed halves. There is no analytic tail correction.
The corresponding spectrum is
`alpha2F[a,b,Omega] = sum_s A[s,a,b]*Omega[s]/2 * delta_Dirac(Omega-Omega[s])`.

The target has positive delta[a,0] on every patch in one common gauge. High
frequency sign changes from retardation/repulsion are allowed. Delta = 0 with
normal-state Z solves the equations but is not the requested branch. Each
private instance has a normal-state pairing eigenvalue greater than one and
a certified nonzero solution reached independently from two starting amplitudes.
This is a specified branch test, not a proof that no other stationary solution
exists or a general free-energy minimization problem.

## Executable API (all physics supplied)

The runtime sets `ALE_PUBLIC_INPUT` to the read-only input directory. For example:

```python
import os
import sys
sys.path.insert(0, os.environ["ALE_PUBLIC_INPUT"])
from eliashberg import Model, load_instance
instance = load_instance(input_path)
model = Model(instance)
z, mapped_delta = model.map(delta)
residual = model.residual(delta)
jacobian_vector_product = model.linearize(delta)
residual_change = jacobian_vector_product(direction)
```

`Model.shape` is (P,N); `frequencies`, `weights`, `omega`, `temperature`,
`weighted_coupling`, and `weighted_coulomb` are available. `fields(delta)` returns
Z and Phi; `convolve(values, parity)` applies the weighted phonon kernel to an
even (+1) or odd (-1) extension. `linearize` differentiates `delta-F(delta)`;
its callable takes and returns (P,N) arrays. `residual_norms(delta,z)` returns
the two public residual norms. Arrays use float64. The supplied FFT implementation
is algebraically the finite sum, not a low-frequency approximation.
Participant code may use or replace these routines; private scoring uses its
own blocked direct sums, not the submitted module or claimed residuals.

## Output and validation

Write exactly `numpy.savez(output_path, delta=delta, z=z)`, with both arrays of
shape (P,N), dtype float64 or float32, finite and real. No pickle, object arrays,
additional NPZ members, symlinks, hard links, or external paths. The file and
total expanded NPZ data must each be at most 16 MiB. Float32 is permitted by the
interface but does not relax the quality criteria.

The parent recomputes Z and F from the returned delta. With

    scale[a] = max(max_n abs(delta[a,n]), pi*T*1e-10)
    r_delta = max_an abs(delta[a,n]-F[delta][a,n])/scale[a]
    r_z = max_an abs(z[a,n]-Z[delta][a,n])/max(1,Z[delta][a,n])

acceptance requires `r_delta <= 2e-8` and `r_z <= 2e-9`. To test the branch,
choose the single global sign making `sum_a weights[a]*delta[a,0] >= 0` and let
`aligned` denote the signed array. If D is the private certified solution:

    reference_scale[a] = max(max_n abs(D[a,n]), pi*T*1e-10)
    branch_error = max_an abs(aligned[a,n]-D[a,n])/reference_scale[a]

Every `aligned[a,0]` must be strictly positive and `branch_error <= 0.002`.
This all-frequency, per-patch normalization protects tiny induced gaps, rejects
partially normal bands, and avoids confusing a small residual near criticality
with an accurate nonzero solution. References have direct-sum normalized
residuals below `5e-11` and two-start agreement below `2e-6` in this same norm.

## Family and runtime contract

There are five families with four hidden draws each: multiband anisotropy;
separated phonon scales with long frequency tails; near-critical amplitude;
weak interband coupling with induced small gaps; and a combination of the last
three. Parameters, quadrature weights, patch order, energy scale, mode weights,
and interaction strengths vary continuously using fixed private seeds. There
are 9–25 patches, 3–4 modes, and 192–2048 positive frequencies. Phonon scale
ratios reach 55.6; weak-interband factors are between about 3e-8 and 3e-5;
near-critical leading eigenvalues are 1 + 2e-5 through 1 + 3e-3. These are
numerical materials, not hidden trivia or material-name lookup questions.

One invocation gets 12 total child CPU seconds, 2048 MiB address space, one
thread, and an 1800-second wall safety timeout. Parent-measured CPU includes
startup and imports; candidate-reported timers are ignored. Only single-process
Python/NumPy/SciPy code is allowed. No external processes or parallel workers.
Thread/process/network restrictions are enforced by the shared sandbox. The
candidate sees a fresh scratch directory, its copied submission, and public
input assets; no evaluator, certificates, private filenames, or prior outputs.

Run a public example from the concept root with:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python workspace/solve.py --input input/examples/multiband.npz --output "$OUTPUT_DIR/eliashberg_solution.npz"
```

The scored entry is `solve.py`; additional Python modules in the submission
directory are allowed, within 512 entries, depth 8, and 32 MiB total. Imports
must not depend on the original baseline directory. The five public examples
are development inputs, not scored instances. The frozen baseline score is
published in `baseline_result.json` after the builder measures it.
