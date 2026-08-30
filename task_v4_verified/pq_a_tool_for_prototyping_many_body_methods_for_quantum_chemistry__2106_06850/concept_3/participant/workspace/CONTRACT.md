# Compact fermionic state synthesis

## Mission
Recover a short, ordered excitation-only circuit for **each** of the three fixed
target states in `input/targets.json`. Choose both the generalized single/double
excitations and their real angles. Order matters. Every target is achievable
within its budget; no particular decomposition is required.

| Case | Spinorbitals | Electrons (alpha, beta) | Maximum gates |
|---|---:|---:|---:|
| sector_10_6_d24 | 10 | 6 (3, 3) | 24 |
| sector_10_6_d28 | 10 | 6 (3, 3) | 28 |
| sector_10_4_d32 | 10 | 4 (2, 2) | 32 |

## Assets and conventions
`input/targets.json` supplies full real target vectors in the entire fixed-N
determinant basis, including zero entries, reference determinants, and budgets.
These binary64 numbers, not an underlying Hamiltonian or rounded display, define
the targets. Orbital 0 is the least-significant bit; determinant masks increase
numerically. For occupied orbitals `p1 < ... < pN`,
`|mask> = a†[p1] ... a†[pN] |vac>`. Even orbitals are alpha, odd are beta.

A gate has sorted, disjoint `annihilate=I`, `create=A` of equal size 1 or 2;
their spin multisets must agree and `tuple(I) < tuple(A)` lexicographically.
This orientation loses no gates because angles may be negative. Define
`E = a†[A0] a[I0]` for singles and
`E = a†[A0] a†[A1] a[I1] a[I0]` for doubles.
The gate is **`exp(theta * (E - E†))`**, without a half-angle or factorial.
Each `theta` is finite and in `[-pi, pi]`. All JSON-list gates apply in order,
first-listed first. Repetitions and zero angles are permitted and count in full.
Only these gates are allowed: no arbitrary determinant rotations, extra
orbital rotations, phases, ancillas, or initial-state choices.

`workspace/fermion.py` is the public NumPy simulator/API;
`workspace/API.md` documents it. It includes spectator-dependent fermion signs.
`workspace/check.py` is the public data-only checker.

## CLI and submission
From this directory, with Python 3.10+, NumPy and SciPy installed:

```bash
python baseline/run.py --output solution.json
python workspace/check.py --submission solution.json
```

Submit only UTF-8 JSON, at most 131072 bytes, with exactly this structure:

```json
{"schema_version":1,"circuits":[
  {"case_id":"sector_10_6_d24","gates":[
    {"annihilate":[0],"create":[4],"theta":0.4}
  ]},
  {"case_id":"sector_10_6_d28","gates":[]},
  {"case_id":"sector_10_4_d32","gates":[]}
]}
```

This is a format example, not a solution. Include every case exactly once.
Unknown/duplicate keys, booleans as numbers, nonfinite numbers, malformed files,
and any budget violation are invalid. Submission programs are never imported
or executed by the checker. No source code is required in the submission.

## Objective and resources
For every case require squared normalized overlap
`F = |target† state|² / ((target† target) (state† state)) >= 0.999999999`.
Global sign is irrelevant. The diagnostic **core score is min(F)** across cases;
passing requires all three cases and all constraints. Invalid submissions score
zero. There is no length bonus below the caps. Thresholds and inputs are fixed.

The provided baseline greedily appends excitations and makes a limited
continuous refinement; it is a starting point, not an expected solution.
The tournament session allows one hour for development and search across all
cases together. Final JSON is limited to 131072 bytes. The trusted checker has
a separate 20-second wall limit, 12-second CPU limit and 2-GiB address-space cap;
these checker limits are not additional restrictions on development. No network,
GPU, quantum hardware, or pdaggerq installation is needed. Only the participant
tree is supplied to the solving session.

Scientific context: Rubin and DePrince, *p†q: A tool for prototyping many-body
methods for quantum chemistry*, arXiv:2106.06850; the official pdaggerq
`set_unitary_cc(True)` interface; and Evangelista, Chan, and Scuseria,
*Exact Parameterization of Fermionic Wave Functions via Unitary Coupled Cluster
Theory*, arXiv:1910.10130. This is a finite inverse-synthesis challenge, not an
implementation of symbolic normal ordering or an energy minimization problem.
