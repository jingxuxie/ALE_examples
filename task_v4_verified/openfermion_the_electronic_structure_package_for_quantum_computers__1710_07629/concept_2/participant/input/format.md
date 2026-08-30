# Format and mathematical contract (version 1)

## Input

`instances.json` is an object with `version: 1`, `task: "local_slater_v1"`,
and an `instances` array. Each instance has:

- `id` (unique string), `family` (`ladder` or `irregular`), `n_modes`, `n_particles`;
- `initial_occupied`: distinct zero-based mode indices, in ascending order;
- `edges`: distinct undirected pairs of mode indices; the graph is connected;
- `target_projector`: `real` and `imag`, each an n-by-n array of binary64 numbers;
- `budgets`: integer `max_gates` and `max_depth`;
- `tolerances`: `projector_frobenius: 1e-8` and `slater_infidelity: 1e-8`.

The complex matrix is `P = real + 1j*imag`. It is a rank-k Hermitian occupied
projector, to binary64 rounding. Our convention is `P[i,j] = <a_j† a_i>`.
Equivalently it specifies the unique k-particle Slater ground state, up to global
phase, of `H = sum_ij (I - 2P)[i,j] a_i† a_j`. No eigenvectors, orbital phases,
preparation history, or hidden target instances are required for submission.

## Output

Exactly one UTF-8 JSON object in `SUBMISSION_DIR/solution.json`:

```json
{
  "version": 1,
  "circuits": [
    {
      "id": "instance_id_from_input",
      "layers": [
        [{"u": 0, "v": 1, "theta": 0.4, "phi": -0.2}]
      ]
    }
  ]
}
```

The example illustrates syntax only; its edge need not occur in an instance.
Every instance must occur exactly once, in any order. Only the keys illustrated
are allowed at each level. Duplicate object keys, booleans in numeric fields,
nonfinite numbers, unknown IDs, extra fields, and noninteger indices are rejected.
The artifact must be a regular file, not a symbolic link or FIFO.

`layers` is chronological. Each nonempty layer contains gates acting on disjoint
pairs. `[]` denotes an identity circuit, but empty layers inside it are forbidden.
For every gate, `u != v` and the unordered pair must be a hardware edge. The
**ordered** pair `(u,v)` determines the convention; reversing it is not a free
relabelling. Angles are finite JSON numbers in the closed interval `[-pi, pi]`,
in radians. No gate cancellation or identity removal is performed by the scorer.
All submitted gates, including zero-angle and swap-like gates, count once. Depth
is the number of submitted nonempty layers. The evaluator does not reschedule.

The one-particle matrix of a gate, on rows/columns ordered `(u,v)`, is

```text
G(theta, phi) = [[cos(theta),             -exp(-i*phi)*sin(theta)],
                 [exp(+i*phi)*sin(theta),  cos(theta)            ]].
```

It is identity on other modes. For occupied orbital columns `V`, apply `V <- G V`.
Equivalently `P <- G P G†`. Gates lift to the exterior-power representation on
fermionic Fock space; Jordan–Wigner parity for separated indices is implicit.
This is not a bare two-qubit rotation on distant qubits. Each layer is the product
of its disjoint gates, and `U = L_last ... L_first`. The initial orbital matrix is
`V0 = I[:, initial_occupied]`. There are no single-mode gates, free final diagonal
phases, free permutations, or initial-state changes. Rotating occupied orbitals
among themselves and a global many-body phase do not change the target state.

## Numerical and resource checks

Let `V = U V0`, `Pout = V V†`, and `Q` be any orthonormal basis for the top-k
eigenspace of the supplied Hermitian target. The checks are

```text
projector_error = ||Pout - Ptarget||_F                  (absolute, not divided by n)
slater_fidelity = |det(Q† V)|^2
slater_infidelity = 1 - slater_fidelity.
```

Fidelity is evaluated stably as the product of squared singular values of `Q† V`,
with singular values clipped to `[0,1]` for floating-point roundoff. Both errors
must be at most their respective tolerances. A Frobenius check prevents determinant
roundoff from incorrectly certifying a near-but-not-exact state. The official
verifier also checks unitarity and projector integrity; it never normalizes a
submitted nonunitary state or accepts a participant-supplied projector or score.

Each circuit is certified only if numerically accurate and
`gates <= max_gates` **and** `depth <= max_depth`. `valid` means the complete
artifact satisfies syntax, gate, hardware, and scheduling rules; exceeding a
budget or missing the target makes it fail certification, not parsing.

- `core_score`: mean of the four certification indicators (0, .25, .5, .75, 1).
- `worst_family_score`: minimum family mean of those indicators.
- Per-instance `resource_score`: zero unless both numerical checks pass;
  otherwise `min(1, max_gates/max(1,gates), max_depth/max(1,depth))`.
- Overall `resource_score`: mean of those per-instance resource scores. It is
  diagnostic/secondary and cannot turn a failed certification into a pass.
- `passed`: all instances certified. `reason`: readable explanation.
- `runtime_score`: null. `evaluation_seconds`: unscored verifier wall time.

Malformed artifacts receive zero scores, `valid: false`, `passed: false`.
Emergency parser limits: 2 MiB UTF-8 file, 4096 layers and 4096 gates per instance.
They permit the general compiler's diagnostic outputs; they do not relax budgets.
The scorer's JSON includes per-instance errors, resource counts, and flags.
Both CLIs print one JSON report, optionally save it with `--report PATH`, and exit
0 for well-formed artifacts (including failed certificates), 2 for invalid input,
or 3 for evaluator infrastructure failure. Reports use no NaN or Infinity.
