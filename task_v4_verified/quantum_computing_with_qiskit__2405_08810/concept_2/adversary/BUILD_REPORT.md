# concept_2 build report

Built August 28, 2026. Mode C: witness/design construction.
Status: **ready_for_fresh_agent**, feasibility verified, hardness untested.
Only `concept_2/` was authored. No fresh Codex agents were launched, no champion
was registered, and no other concept or authoring workspace was modified.

## Deliverables

- Public mission: `participant/TASK.md`.
- Four public matrices, graphs, directed durations and caps:
  `participant/input/instances.json`.
- Complete format/cost/resource contract: `participant/input/FORMAT.md`,
  `participant/input/SCORING.md`, `participant/input/RESOURCES.md`.
- Standalone public checker: `participant/workspace/checker.py`.
- Runnable graph-routed Gaussian baseline: `participant/baseline/solve.py`.
- Frozen private evaluator: `evaluator/evaluate.py`, with a private checker copy
  and immutable data protected by `evaluator/frozen.json`.
- Generator, seed, planted programs and schedules: `evaluator/hidden/` only.
- Evaluator selftests: `evaluator/selftests.py`; machine-readable results in
  `adversary/selftests.json`.
- Release hashes: `evaluator/hidden/release_manifest.json`; complete machine
  audit and status in `adversary/build_audit.json` and `status.json`.

## Frozen measurements

Count means literal native CX pairs; depth means integer-duration ASAP completion
under per-wire list-order dependencies. Each cell below is **CX count / weighted
depth**. Every target must independently satisfy both caps.

| Target | Qubits | Frozen caps | Private planted witness | Routed Gaussian baseline |
| --- | ---: | ---: | ---: | ---: |
| mesh_22 | 22 | 155 / 65 | 146 / 60 | 2,733 / 7,354 |
| bridge_26 | 26 | 189 / 66 | 178 / 61 | 3,463 / 9,250 |
| mesh_30 | 30 | 227 / 78 | 214 / 72 | 4,449 / 10,872 |
| bridge_34 | 34 | 261 / 79 | 246 / 73 | 7,655 / 19,488 |

| Artifact | Valid | Passed | Core score | Worst family | Resource score |
| --- | --- | --- | ---: | ---: | ---: |
| Private planted | true | true | 1.0 | 1.0 | 1.0 |
| Author-run weak baseline | true | false | 0.0 | 0.0 | 0.004053776683087028 |

Both artifacts implement **all four exact matrices**. The baseline fails both
caps on every target, not correctness or the artifact interface. All four
planted witnesses pass; these are private achievability certificates, not fresh
solver results. Count/depth caps were frozen at ceilings of 106%/108% of their
private costs, respectively, before selftests and any fresh-agent attempt.

Score reports: `evaluator/hidden/planted_score.json` and
`adversary/weak_baseline/score.json`. The baseline artifact is stored at
`adversary/weak_baseline/solution.json`; it is not an entry in `attempts/`.

## Validation and integrity

All **51 named tests passed**, without skips, including 112 randomized small
circuits and all ordered remote-CX pairs on paths with two through eight wires.
Dense NumPy elementary-matrix products, all basis inputs, and a separate NetworkX
weighted dependency DAG corroborate the row-bitset checker and scheduler.

Tests cover altered matrices and witnesses, transposed and reversed semantics,
independent equality/one-over count and depth boundaries, shared-control
serialization, direction-dependent durations, identity padding, fractional
diagnostic scores without aggregate acceptance, schema violations, boolean and
nonfinite inputs, duplicate/escaped keys, oversized files/integers/nesting/gate
lists, malformed UTF-8, file symlinks/FIFOs, public-file tampering, private hash
tampering, and absence of submitted-code execution. A relocated participant-only
package reproduces the baseline artifact. Grading succeeds without the private
generator, seed or planted witness present in its own evaluator directory.

All seven Python files compile, with no one-letter identifiers or code comments.
Private generation reproduces the frozen JSON byte-for-byte from its hidden
256-bit seed, and refuses accidental overwrite. Seed/witness leak checks passed.
No dependency was installed; production checking/grading/baseline use the Python
standard library, while independent build tests use existing NumPy and NetworkX.

The public release tree SHA-256 is
`820fcec53836fb5c338eeebf42e9f1f71d846cbd454c3d56203d45432432605c`.
Individual public and private file hashes are in the hidden release manifest.

## Difficulty and scientific link

The source connection is arXiv:2405.08810's third design principle in section II
(HTML II.0.3) and section III.1: retarget high-level Boolean linear transformations
to a native, timing-aware circuit representation. Official Qiskit linear synthesis
code is referenced in the public resource notes. The benchmark matrices and
weighted devices are synthetic, not claimed paper results or real calibrations.

The intended difficulty is recovering a compact native factorization from a
matrix while preserving a shallow weighted schedule. Fixed physical labels,
irregular degree-two/three connectivity, two graph families, asymmetric durations
and two tight per-target caps prevent a cheap global average or free permutation
from hiding a poor target. Exact graph-routed elimination works but is expensive.
This is a difficulty hypothesis supported by a weak baseline, **not** a proof of
hardness or evidence of fresh-agent failure.

The parent controller should expose only `participant/` and a new empty output
directory, grade an immutable `solution.json` snapshot with the private evaluator,
and make the empirical hardness decision after fresh-agent testing. No new
generation or threshold adjustment is part of this handoff.
