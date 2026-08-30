# Exact excitation API

Import `fermion` with this directory on `sys.path`. Python 3.10+ and NumPy are
sufficient for the checker. The baseline also uses SciPy.

- `load_cases(path=DEFAULT_TARGETS) -> tuple[Case, ...]`: validated full fixed-N
  vectors, basis masks, spin counts, reference masks and caps.
- `determinant_basis(n_orbitals, n_electrons) -> tuple[int, ...]`: increasing masks.
- `allowed_excitations(n_orbitals) -> tuple[Excitation, ...]`: all legal canonical
  choices, 250 for each supplied 10-orbital case, independent of initial occupation.
- `Excitation(annihilate: tuple, create: tuple)`: immutable gate label.
- `rotation_pairs(n_orbitals, n_electrons, excitation)`: cached read-only source,
  destination, and sign arrays. These arrays partition the active determinants
  into disjoint pairs. The API assumes the gate label is already legal.
- `reference_state(case) -> ndarray`: fresh real state vector.
- `apply_rotation(state, pairs, theta) -> ndarray`: fresh rotated state.
- `apply_generator(state, pairs) -> ndarray`: `(E-E†) state` for derivatives.
- `circuit_state(case, [(excitation, theta), ...]) -> ndarray`: first gate first.
- `squared_overlap(target, state) -> float`: normalized, phase-invariant fidelity.
- `validate_submission(data, cases) -> dict[case_id, tuple[(Excitation, theta)]]`:
  strict schema, angle, spin, and gate-count validation; raises `ValidationError`.
- `evaluate_path(submission_path, targets_path=DEFAULT_TARGETS) -> dict`: fail-closed
  report with `core`, `worst_fidelity`, `pass`, `reason`, `runtime_seconds`, and
  individual case fidelities, gate counts, pass flags and state norms.

For `E |source> = sign |destination>`, the update is

```text
new[source]      = cos(theta) old[source] - sign sin(theta) old[destination]
new[destination] = sign sin(theta) old[source] + cos(theta) old[destination]
```

All other coefficients are unchanged. An elementary annihilation or creation
at orbital `orbital` contributes `(-1)^popcount(mask & ((1<<orbital)-1))`
on the **current** intermediate determinant. In a double excitation,
annihilate `I0`, then `I1`, then create `A1`, then `A0`. This implements exactly
`a†[A0] a†[A1] a[I1] a[I0]`; a Jordan-Wigner-free qubit excitation is not equivalent.

The target file includes the complete number-sector vectors (210, 210, 210
coefficients); spin-forbidden entries are explicitly zero. The simulator never
renormalizes the state after a gate. The overlap formula only compensates for
binary64 roundoff in the supplied target and simulated state norms. Norm drift
above `5e-12` is an evaluator error, not a way to improve score. Valid global
negative target states pass, and there is no comparison to a particular circuit.
