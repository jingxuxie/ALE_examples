# Analog memory NPZ interface

Implement `workspace/solve.py`. For each supplied case, reconstruct the binary
data-error increments and the corresponding noiseless parity history from noisy
continuous readouts. Preserve the logical information at the end of the memory.

Invocation: `python solve.py --input CASE.npz --output ANSWER.npz`.
One invocation handles all independent shots in a case. Only NumPy/SciPy and the
Python standard library are guaranteed; do not rely on network access or private
packages. The example is small and unlabeled, not a training set.

Reusable binary-decoding building blocks are supplied in `workspace/legacy_2020/`
(native source, with its license) and `workspace/binary_bp.py`. The latter exposes
`recover(parity_csr, probabilities, syndrome, iterations=30)` for a single binary
problem; its standalone CLI targets a different schema and is not the submission
entry point. You may reuse, wrap, compile or replace these components. They do not
assemble this memory model or interpret continuous measurements. Native sources
are not prebuilt; build any executable into your writable submission directory.

## Input NPZ (no pickle)

Let `shots`, `rounds`, `checks_count`, and `qubits` be the dimensions below.
Every check, stabilizer, metacheck, syndrome and error is binary; matrix equations
use arithmetic modulo two. Array indices are zero-based.

| Key | dtype / shape | Meaning |
|---|---|---|
| `schema_version` | integer scalar, 1 | Contract version |
| `case_id` | Unicode scalar | Opaque identifier; carries no decoding information |
| `checks` | uint8 `(checks_count, qubits)` | Parity measurements |
| `stabilizers` | uint8 `(stabilizer_count, qubits)` | Equivalent, harmless data errors |
| `metachecks` | uint8 `(meta_count, checks_count)` | Relations between noiseless checks; may have zero rows |
| `readout` | float64 `(shots, rounds, checks_count)` | Continuous parity measurements |
| `mean0`, `mean1` | float64 `(rounds, checks_count)` | Conditional readout means for noiseless parity 0 and 1 |
| `sigma` | float64 `(rounds, checks_count)`, positive | Conditional Gaussian standard deviation, same for both parities |
| `data_error_prob` | float64 `(rounds, qubits)` | Independent Bernoulli data-error probability in each interval |
| `terminal_syndrome` | uint8 `(shots, checks_count)` | Exact parity immediately after the last noisy readout, with no intervening data errors |

The data state starts at zero. At each round, fresh independent data errors are
added to the previous state, then parity is measured. Conditioned on the actual
parity, readouts are independent Gaussian draws using the supplied calibration.
The final exact boundary is an additional measurement, not an additional error
interval. Calibration varies across checks and rounds. Cases contain 81–544
qubits, 3–6 noisy rounds, and at most 128 shots per invocation.

## Output NPZ (exactly these two arrays)

- `increments`: binary integer `(shots, rounds, qubits)`, your inferred fresh data
  errors. Their cumulative parity defines your inferred data state at each round.
- `syndrome_history`: binary integer `(shots, rounds, checks_count)`, your inferred
  noiseless parity at each round.

For every shot, the reported history must equal `checks` applied to the cumulative
increments, satisfy all metachecks, and end at `terminal_syndrome`. Violating any
of these requirements invalidates that shot. Errors differing by a row-space
combination of `stabilizers` are logically equivalent at the final boundary.

Two independently measured objectives are final logical recovery and balanced
accuracy of the intermediate/noiseless syndrome history (excluding its already
known final row). Neither requires copying
a particular reference correction. Family-balanced scores are normalized relative
to a weak baseline and a stronger reference, without clipping; performance above
the reference can exceed 1. Runtime is user plus system CPU time, with a
120-CPU-second, 1536-MiB limit per case; wall time is reported separately and has
a 360-second safety timeout. Malformed output, crashes and timeouts count as
failures, not omissions.
