# Matrix contract

The real, number-conserving Hamiltonian is

`H = sum(p,q) h[p,q] a†[p] a[q] + 1/2 sum(k) (sum(p,q) B[k,p,q] a†[p] a[q])²`.

Every `h` and `B[k]` is real symmetric. A submission chooses real orthogonal
matrices `U` (orbital, n by n) and `W` (auxiliary, r by r). The represented
Hamiltonian is unchanged up to a one-particle basis change when

`h_new = U.T @ h @ U`

`B_new[k] = sum(l) W[k,l] * U.T @ B[l] @ U`.

The coefficient-based LCU normalization proxy to minimize is exactly

`C(U,W) = sum(abs(h_new)) + 0.5 * sum(k) sum(abs(B_new[k]))**2`.

This is a representation cost, not the spectral norm or an energy error.
No tensor truncation, alteration of the Hamiltonian, or nonorthogonal change
is permitted. Orthogonality residuals must each be at most `1e-7` in Frobenius norm.

`python3 solver.py REQUEST.json RESPONSE.json` consumes an object with `cases`
and `seconds_per_case`. Each case has `id`, `family`, `one_body`, `factors`, and
`baseline_cost`. The output object contains `solutions`, exactly one per case,
each with `id`, `orbital`, and `auxiliary`. All numbers must be finite.

Dimensions are 10–16 orbitals and 8–14 auxiliary factors. Families contain
localized bond-charge operators, overlapping three-orbital charge clusters,
and four-orbital multiscale clusters with weak diffuse components. Each is
presented in an unrelated dense orbital and auxiliary basis. Public and hidden
instances have the same distributions and dimension range. Generating gauges
and hidden instances are not supplied.

Per-case ratio is `C / baseline_cost`. A family score is one minus its geometric
mean ratio; the core score is the same across all cases. Higher is better;
the unchanged baseline scores zero. Every case must be valid. The public
scorer computes these quality scores; the private evaluator additionally
enforces total inference wall time, CPU time, and memory.

The inference environment is Linux x86-64, system Python with NumPy and SciPy,
one CPU, and at most 2 GiB virtual address space. Runtime process/thread
creation and network access are disallowed. Precompiled native libraries are
allowed. Only participant assets, the submitted directory, system runtime,
and a temporary writable directory are available to the solver. Use the
provided response path for output. Eighteen hidden instances share a 180-second
wall and CPU budget. The wall clock includes interpreter startup.
