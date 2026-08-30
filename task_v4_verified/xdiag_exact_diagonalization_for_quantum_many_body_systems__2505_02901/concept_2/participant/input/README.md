# Public physical and numerical contract

## Assets and conventions

The system has eight spin-1/2 sites, four up spins, and a 70-dimensional Hilbert
space. Set hbar = 1. Site 0 is the least significant bit; bit 1 denotes up.
The basis is the increasing integer order of bitstrings with exactly four set
bits. There is no translation or reflection quotient. All site additions are
modulo 8. Spin operators have eigenvalues +/-1/2, not +/-1.

`model.json` supplies every coefficient below. `hamiltonians.npz` contains
`basis` (70,), `drifts` (4,70,70), `controls` (3,70,70), and `initial` (70,6).
The six columns are the computational states in `initial_bitstrings` order.
`targets.npz` contains only `targets` (4,70,6), in calibration order from
`model.json`. These are complex128 arrays. All NPZ files load with
`numpy.load(path, allow_pickle=False)`. The matrices, model, and conventions
agree to floating-point roundoff; all are public.

For sites p,q define

    XY(p,q) = Sx_p Sx_q + Sy_p Sy_q
    ZZ(p,q) = Sz_p Sz_q
    CUR(p,q) = Sx_p Sy_q - Sy_p Sx_q.

For calibration member m the drift is

    D_m = J1 sum_p [XY(p,p+1) + (Delta1 + d_m) ZZ(p,p+1)]
        + J2 (1 + f_m) sum_p [XY(p,p+2) + Delta2 ZZ(p,p+2)]
        + sum_p (h_p + b_m g_p) Sz_p.

Here `nearest_exchange`, `nearest_anisotropy`, `next_exchange`, and
`next_anisotropy` are J1, Delta1, J2, Delta2. `static_field` is h and
`field_error_profile` is g. Each calibration provides d_m, f_m, b_m as
`anisotropy_shift`, `next_exchange_fraction`, and `field_offset`.
Each displayed bond is included exactly once for each p. The next-neighbor
exchange is an interacting, frustrating term, not an approximation to the
nearest-neighbor model.

The three fixed control operators, in submission column order, are

    C0 = sum_p staggered_profile[p] Sz_p
    C1 = sum_p bond_profile[p] [XY(p,p+1) + bond_control_anisotropy ZZ(p,p+1)]
    C2 = sum_p current_profile[p] CUR(p,p+1).

In the one-site basis (down,up), Sy = [[0,i/2],[-i/2,0]]. Thus CUR(p,q)
has matrix element -i/2 for flipping an up spin at p and a down spin at q.
These controls conserve magnetization but do not mutually commute.

## Pulse and hardware limits

The real array a has shape (24,3), and its first row is applied first. Every
slice lasts dt = 0.85, for a total time of 20.4. For every calibration,

    H_m,k = D_m + sum_c a[k,c] C_c
    X_m = exp(-i dt H_m,23) ... exp(-i dt H_m,0) initial.

All calibrations receive exactly the same a. No feedback, extra waits, free
unitaries, calibration-dependent pulses, or change of time discretization is
allowed. The target action can differ between calibrations: this is compilation
of a calibrated family of register actions, not a claim of calibration-invariant
dynamics. A physically admissible common pulse is known to exist; finding that
specific pulse is unnecessary.

`spec.json` fixes |a[k,c]| <= `amplitude_limits[c]` and
|a[k+1,c]-a[k,c]| <= `adjacent_jump_limits[c]`. The jump test also includes
the transitions from zero to row 0 and from row 23 to zero. These are discrete
amplitude-jump limits, not continuous ramp segments inserted into the dynamics.
The integrated normalized exposure is

    E = dt sum_{k,c} (a[k,c] / amplitude_limits[c])**2 <= 13.5.

A 1e-10 absolute tolerance applies separately to these physical inequalities.
No fidelity tolerance is added to the thresholds. All numbers must be finite
JSON numbers, not strings, booleans, NaN, or infinity. The JSON object has exactly
the two keys `schema_version` (integer 1) and `amplitudes`.

## Coherence-sensitive acceptance

Let Y_m be the target isometry and M_m = Y_m^dagger X_m. Define

    F_iso,m = |trace(M_m)/6|**2
    F_col,m = min_j |M_m[j,j]|**2
    phi_m = arg(trace(M_m)), taking phi_m = 0 for an exactly zero trace
    B_m = [exp(-i phi_m) M_m + exp(i phi_m) M_m^dagger] / 2
    L_m = max(0, smallest_eigenvalue(B_m))**2.

Numerical fidelity values are clipped to [0,1]. One global phase per calibration
is irrelevant, but relative register-column phases are physical. For every
normalized coefficient vector v, |(Y_m v)^dagger (X_m v)|**2 >= L_m.
Consequently L_m is a conservative, explicitly specified certificate for all
superpositions in the six-dimensional register, not a random hidden state test.

Acceptance requires mean_m F_iso,m >= 0.999995, min_m L_m >= 0.99999,
min_m F_col,m >= 0.99999, and all hardware limits. `core_score` is the first
quantity and `worst_family_score` is min_m L_m. The evaluator also reports
each calibration separately. `resource_score` is 1-E/13.5, clipped to [0,1],
for physically admissible submissions and zero otherwise; it is diagnostic,
not an extra objective that can trade off accuracy. `runtime_score` is 1 when
validation finishes within 120 seconds and zero otherwise. Construction time
and memory are enforced by the surrounding agent runner, not inferred from
claims in pulse.json.

There are no hidden physical systems, extrapolation cases, target labels, or
phase conventions. The private checker uses independent Hamiltonian assembly
and dense segment eigendecomposition. It reads no submitted Python code and
never compares a pulse with the known witness. It rejects malformed artifacts
and reports invalid physics before doing expensive propagation.

The public forward checker is

```sh
/usr/bin/python3 -B workspace/simulate.py --input input --pulse /your/output/pulse.json
```

## Scientific source

This constructed compilation problem is seeded by *XDiag: Exact Diagonalization
for Quantum Many-Body Systems*, arXiv:2505.02901, particularly fixed-Spinhalf
blocks, real-time evolution, and XXZ domain-wall dynamics. The public XDiag examples
`spinhalf_chain_domain_wall_dynamics` and `spinhalf_chain_level_statistics`
provide the underlying spin-chain and interacting-dynamics context. This task
adds a periodic frustrated ring and a pulse-compilation contract; it is not a
result or a benchmark claimed by the paper. XDiag is not required at runtime.
