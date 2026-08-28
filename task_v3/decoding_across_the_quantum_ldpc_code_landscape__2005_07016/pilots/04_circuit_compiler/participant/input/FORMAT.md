# Circuit-to-detector compiler

Replace `workspace/solve.py` with an efficient, exact compiler for the provided
Clifford measurement circuits. This is not a decoding task. Run:

`python3 solve.py --input case.json --output answer.json`

The starter already computes the correct model by propagating every fault
separately. This becomes too slow for repeated extraction. You may replace it
entirely. Standard-library Python, NumPy, and SciPy are available. Do not use
Stim, another quantum-circuit compiler, network access, or private evaluator
assets. No circuit construction or text-format parser is required.

## Parsed input

JSON contains `schema_version: 1`, `case_id`, `num_qubits`, `num_measurements`,
`num_detectors`, `num_observables`, and `operations`. Qubits are zero-based.

- `{"op":"H","qubits":[0,2]}` applies H independently to the targets. The
  other single-qubit gates are `S` and `S_DAG`.
- `{"op":"CX","qubits":[0,1,2,3]}` applies control 0 to target 1, then
  control 2 to target 3. `CZ` and `SWAP` use the same paired-target layout.
- `R` resets each target to |0>; `RX` resets each to |+>.
- `M` measures each target in Z; `MX` measures each in X. Each target appends
  one measurement record, in order. These do not reset the qubits.
- `{"op":"ERROR","qubits":[0,2],"paulis":["X","Y"],"probability":0.01}`
  applies the whole product X0 Y2 with independent Bernoulli probability 0.01.
  Each ERROR is independent of every other occurrence, including in repeats.
  Targets within an ERROR are distinct. No mutually-exclusive error channels
  or approximation of those channels is involved.
- `{"op":"DETECTOR","records":[-1,-3]}` declares the XOR of those records,
  relative to the current record count. Detector IDs count declarations from
  zero in execution order. Repeated references cancel by XOR.
- `{"op":"OBSERVABLE","index":2,"records":[-1]}` XORs those records into
  observable 2. Multiple includes with the same index accumulate by XOR.
- `{"op":"REPEAT","count":5,"body":[...]}` repeats the parsed body. Record
  offsets refer to the global execution history, including previous rounds.
- `{"op":"TICK"}` is a scheduling boundary with no semantic action.

All declared detector and observable parities are deterministic without noise.
There are no gauge detectors, feed-forward gates, or non-Clifford operations.
`protocol.py` provides repeat expansion and lowering to absolute measurement
records so bookkeeping boilerplate need not be reimplemented.

## Exact output

Return JSON with `schema_version:1`, the exact `num_detectors` and
`num_observables`, and `errors`, a list of objects containing sorted unique
integer `detectors`, sorted unique integer `observables`, and `probability`.
Each term represents an independent Bernoulli flip of exactly that full
signature. Omit silent faults and zero-probability terms. Preserve
observable-only faults. Merge identical FULL signatures by parity probability:
`p_merged = p_old*(1-p) + p*(1-p_old)`, not by summing probabilities. Distinct
logical signatures must not be merged even if their detector sets coincide.
Term ordering is unrestricted, but duplicate terms are invalid.

Worked inputs and exact outputs are in `workspace/examples/`. In
`parity_probability`, two identical X-fault mechanisms with probabilities
0.1 and 0.2 produce probability 0.26, not 0.3.

## Evaluation

Hidden cases include repeated surface and nongeometric CSS/HGP extraction,
correlated Pauli products, resets, both measurement bases, Clifford conjugation,
record references across rounds, and probability merging. The per-case budget
is 8 CPU seconds with 1536 MiB address-space limit, including process startup
and JSON I/O. User plus system CPU time determines runtime scores; wall time
is reported separately, with a wall allowance of at least 60 seconds to avoid
mount/startup jitter. The evaluator uses the provided independent forward compiler as the
weak baseline and an exact private reference compiler; neither is a decoder.

Semantic quality is support F1 times normalized probability-L1 fidelity.
Semantic audits multiply performance-case quality. Exact agreement is also
reported at relative tolerance 1e-9 and absolute tolerance 1e-12. For quality Q,
weak quality Qw, CPU time T, weak CPU time Tw, reference CPU time Tr, and epsilon=1e-6:

`speed = log((Tw+epsilon)/(T+epsilon))/log((Tw+epsilon)/(Tr+epsilon))`

`score = 100*(Q**4*(1+speed)-Qw**4)/(2-Qw**4)`

The equal-weight mean is reported. Weak maps to 0, exact reference to 100;
scores are not clipped at either end. Faster exact compilation can exceed 100.
Failures/timeouts have Q=0. Prioritize correctness, then avoid fault-by-fault
replay on the full extraction circuit.
