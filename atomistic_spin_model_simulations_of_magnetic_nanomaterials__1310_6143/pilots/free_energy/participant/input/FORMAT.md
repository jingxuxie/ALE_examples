# Physical and I/O contract

## Input

A UTF-8 JSON object has `version: 1`, `case_id`, `family`, `n_spins`,
`temperature`, `seed`, `shape`, `periodic`, `angles`, `onsite`, and `bonds`.
`n_spins` is 2,048 for slabs or 2,744 for particles in the frozen pilot.
Future reserved cases can be larger; do not special-case identifiers or sizes.
All indices are zero-based. The graph and coefficients, not the family label,
are authoritative. `shape` and `periodic` describe the simple-cubic geometry.
Site index is `x + nx*(y + ny*z)`. The lattice spacing is one.

Each spin is a three-component real unit vector with identical fixed atomic
moment one. All energies are in units of the bulk exchange; k_B=1, so temperature
has the same units as energy. These are classical model magnets, not calibrated
predictions for named materials. There is no applied field or dipolar term.

`onsite[i]` is `[Qxx,Qyy,Qzz,Qxy,Qxz,Qyz,c]`. Q is a real symmetric tensor.
`bonds` consists of `[i,j,J,b]`, each undirected bond listed exactly once.

    H = -sum_bonds [J*(s_i dot s_j) + b*s_iz*s_jz]
        -sum_i [s_i^T Q_i s_i + c_i*(s_ix^4+s_iy^4+s_iz^4)]

Thus off-diagonal Q entries enter twice. Positive J is ferromagnetic, positive
Qzz favors z, positive b favors axial alignment, and positive c favors cubic axes.
Do not insert a one-half factor into the supplied bond list.

The three families are: a periodic film with easy-z bulk and easy-plane surfaces;
an exchange-spring bilayer with orthogonal local easy axes, reduced interlayer
exchange and axial two-ion interface anisotropy; and an open cubic particle with
bulk cubic anisotropy and competing facet-normal surface anisotropies.

## Statistical ensemble and observables

For angle theta (radians), n=(sin(theta),0,cos(theta)). Constrain the direction
of M=sum_i s_i to n with M dot n > 0, but do not constrain |M| or individual spins.
The partition function is the **directional probability density per unit solid
angle** of M, using product uniform solid-angle measure for microscopic spins:

    Z(n) = integral product_i dOmega_i exp(-H/T) delta_on_sphere(M/|M| - n).

This is not the ensemble defined by a flat Cartesian delta(Mx) delta(My).
Configurations with zero M have measure zero. Let f(theta)=-T*log(Z(n))/N.
With B_i=-partial H/partial s_i, the requested torque is

    torque(theta) = <sum_i (s_i cross B_i)_y>/N = -df/dtheta.
    free_energy(theta) = f(theta)-f(0) = -integral_0^theta torque(u) du.

No single-harmonic angular form is assumed. All cases have reflection symmetry:
torque(-theta)=-torque(theta), torque(0)=torque(pi/2)=0, and f(theta+pi)=f(theta).
Symmetry applies to equilibrium averages, not individual noisy configurations.
Finite system size is part of the target. The only physical approximation is
the stated classical Hamiltonian; statistical and angular quadrature errors
remain the solver's responsibility. Error bars are informative, not a way to
reduce the accuracy penalty.

## Output

Write a UTF-8 JSON object with `version:1`, the exact `case_id`, and finite numeric
arrays `torque` and `free_energy`, each in the order and length of `angles`.
Set `free_energy[0]=0`. Optional same-length `torque_sem` and `free_energy_sem`
must be nonnegative. Unknown keys are ignored. Alternatively write an NPZ file
with numeric float64 arrays `torque` and `free_energy` and optional uncertainty
arrays. Pickled/object arrays, infinities, and NaNs are forbidden. The evaluator
passes an output filename ending in `.json`; if writing NPZ, write `OUTPUT.npz`
instead, where OUTPUT is that exact filename (for example `result.json.npz`).
Output size and uncompressed archive size must each be below 2 MiB.

## Execution

Place the entry point at `SUBMISSION/solve.py`. It is run, never imported:

    python solve.py CASE.json OUTPUT.json

The submission and provided `workspace/` are read-only. `/tmp` and the output
directory are writable. Use `/tmp` for native compilation or scratch files.
The supplied workspace and, when present, `workspace/vendor` are on PYTHONPATH.
Only Python's standard library and the supplied runtime are guaranteed;
g++ is available for native helpers. No network or other pilots/private files
are available. Each case has 600 wall seconds, 602 CPU seconds, 4 GiB address
space, and a 2 MiB output limit. Runtime includes compilation and startup.
Use at most one computational thread. Seed selection is under solver control;
`seed` provides a reproducible suggestion, not a hidden-reference noise stream.

## Score

For each observable the evaluator uses RMS error relative to the stored
coherent-rotation baseline's RMS error, with a reference-uncertainty resolution
floor (20 times reference RMS standard error, at least 1e-5 energy units).
If e is normalized RMS error, quality is `1/(1+e)`; it has no perfect-score
threshold or tolerance plateau. Case quality is 0.65 torque + 0.35 free energy.
Family means, mean of family means, worst-family mean, and wall runtime are
reported separately. A baseline at the normalization scale scores 0.5, not zero.
Errors, missing outputs, sandbox failures, and timeouts score zero.
