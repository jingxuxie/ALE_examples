# Contract v2

## Request and output

The CLI is `python solve.py --request REQUEST.json --output STATE.npz`.
The JSON has `version: 1`, opaque `case_id`, `seed`, `n_sites`, `local_dim`,
`bond_cap`, `sector` (`"any"`, `"even"`, or `"odd"`), `omega`, `mass2`,
`lambda4`, `field`, `coupling`, `budget_seconds`, and `wall_seconds`.
The first four coefficient lists have length `n_sites`; `coupling` has length
`n_sites - 1`. `omega` and `lambda4` are positive; `coupling` is nonnegative.
`sector != "any"` implies every `field` is zero. All numbers are finite.
The advertised range is 32 <= n_sites <= 64, 8 <= local_dim <= 14,
and 12 <= bond_cap <= 24. Coefficients satisfy -0.20 <= mass2 <= 0.03,
0.05 <= lambda4 <= 0.30, 0.05 <= coupling <= 1.50,
0.55 <= omega <= 1.85, and abs(field) <= 0.004. Examples need not cover
hidden instances. These are finite projected Hamiltonians; no externally known
critical mass or continuum-limit answer is assumed.

The only required output is an NPZ with exactly keys `A0`, ..., `A{n_sites-1}`.
`Ai` is float64 or complex128, with axes `(left_bond, physical, right_bond)`.
Boundary bonds are one, adjacent bonds agree, physical dimension is `local_dim`,
and all internal bonds are between one and `bond_cap`. Tensors must be finite
and describe a nonzero state. No canonical gauge or normalization is required.
All tensor entries must have magnitude <= 1e100. The contractor rescales and QR
canonicalizes before contraction, but pathologically ill-conditioned gauges can
still fail numerical validation. The NPZ must be a regular file, <= 8 MiB on disk
and uncompressed, with no pickle/object arrays, duplicate keys, or extra arrays.
There is no accepted field for a claimed energy. Write the file and exit zero
within both budgets; a timeout is invalid even if a partial answer exists.

## Exact finite Hamiltonian

Use hbar = lattice spacing = 1. The objective is

    H = sum_i [p2_i/2 + mass2_i*q2_i/2 + lambda4_i*q4_i/24 - field_i*q_i]
        + sum_i coupling_i/2 * [q2_i + q2_{i+1} - 2*q_i*q_{i+1}].

Each site's oscillator frequency is `omega[i]`. In a **padded dimension d+4**,
`a[n-1,n] = sqrt(n)`, `q = (a + a.T)/sqrt(2*omega)` and
`p = -1j*sqrt(omega/2)*(a - a.T)`. Form `q@q`, `q@q@q@q`, and `p@p`
in this padded space, THEN take their upper-left d-by-d blocks. Separately
truncate `q` itself for the cross-site product. In particular, neither `q2`
nor `q4` is a power of the already-truncated `q`. There are no missing-neighbor
boundary springs, normal-ordering counterterms, or energy shifts.
The finite matrices, including the specified basis/cutoff, define the task;
changing a basis internally is allowed only if output tensors are transformed
back. Infinite-volume or continuum extrapolation is not scored.

For an even/odd request the objective is the lowest energy in that global parity
sector, not the unrestricted ground energy. `P_i = diag((-1)**arange(d))`;
the contractor requires `abs(<product_i P_i> - sign) <= 1e-6`, where sign is
+1 for even and -1 for odd. It never silently projects a submitted state.

## Budgets, evaluation, isolation

Short and long requests start independently: no warm files or process reuse.
The runner permits one execution thread, sets BLAS/OMP thread counts
to one, measures CPU through wait4, and enforces CPU, wall, address-space, and
file-size limits. Solver interpreter/import time counts; trusted evaluator and
namespace-launcher setup does not. Do not launch child processes
or use a GPU/network. Each invocation gets a fresh copy of the submitted directory
and a fresh output path. Source and data assets together must be <= 16 MiB.

The harness command is
`python evaluator/evaluate.py --submission DIR --output FILE`.
It reports per-stage recomputed energies, validity, measured runtime, normalized
quality, family aggregates, score, and whether all target gates are met.
Invalid/missing/late solver answers get zero quality and fail the validity gate.
Unresolved infrastructure failures abort without a scientific score.
Formulae are in `scoring.json`.

`workspace/contractor.py` exposes `local_operators`, `hamiltonian_terms`,
`load_mps`, `measure`, and `save_mps`. For example:

    python workspace/solve.py --request input/example_symmetric.json --output "$OUTPUT_DIR/state.npz"
    python workspace/contractor.py --request input/example_symmetric.json --state "$OUTPUT_DIR/state.npz"

The public contractor is a convenience, not a trusted evaluator dependency.
Only `participant/` is released to solvers. The builder's evaluator/hidden,
calibration states, reports, status, and review directories must be withheld.
Evaluation uses separate filesystem, network and process namespaces and fails
closed if required containment is unavailable. The fresh coding session has a
separate allowlist exposing only the participant assets and its output directory.
