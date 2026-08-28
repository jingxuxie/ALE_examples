# Concept 04: circuit-to-detector compilation

Written before implementation, 2026-08-27. This pilot is confined to
`pilots/04_circuit_compiler`. It is a compiler task, not a decoder task.

## Historical integration gap and primary sources

The code-capacity BP+OSD interface accepts a parity-check matrix and priors;
fault-tolerant extraction instead requires propagation of faults through an
entire measurement circuit into detector and logical-observable parities.
The official `ldpc` history documents that this bridge is not automatic:

- https://github.com/quantumgizmos/ldpc/issues/68
- https://github.com/quantumgizmos/ldpc/pull/69
- https://github.com/quantumgizmos/ldpc/commit/ce5778b7ed9073cc1a77cc424685122d4e216169
- https://github.com/quantumgizmos/ldpc/pull/62

Issue 68 reports missing CNOTs and a one-basis classical memory circuit being
used where both CSS bases and idle-noise accounting matter. These motivate
the integration task; this pilot does not claim to reproduce that exact bug.
The hidden solution is the actual official Stim 1.16.0 compiler, not an
author-written imitation or a precomputed decoder:

- https://github.com/quantumlib/Stim/releases/tag/v1.16.0
- https://github.com/quantumlib/Stim/blob/v1.16.0/src/stim/simulators/error_analyzer.cc
- https://github.com/quantumlib/Stim/blob/v1.16.0/doc/file_format_dem_detector_error_model.md
- https://github.com/quantumlib/Stim/blob/v1.16.0/doc/python_api_reference_vDev.md

## Participant pre-state

Expose only `participant/`: an already-parsed JSON operation schema, repeat
expansion helper, runnable weak forward-fault compiler, tiny worked examples,
and a `workspace/solve.py --input case.json --output answer.json` entry point. Do not
expose this directory, challenge generators, challenge answers, official Stim,
the private vendor directory, or the source checkout. Parser work and code
construction are not part of the task. Inputs already contain circuits.

## Exact model

Supported operations are Clifford gates, Z/X resets and measurements,
measurement-record parity detectors, logical-observable includes, and repeats.
Each ERROR is an independent Bernoulli Pauli product, including multi-qubit
products. There are no mutually-exclusive depolarizing alternatives, gauge
detectors, feedback, or non-Clifford gates. Identical nonempty detector AND
observable signatures are combined by XOR probability, never by summation.
Silent faults are omitted. All measurement references are relative to the
number of measurements executed at their declaration, including across repeat
boundaries. Noise-free declared parities must be deterministic.

Use `Circuit.detector_error_model(decompose_errors=False,
flatten_loops=True, approximate_disjoint_errors=False,
allow_gauge_detectors=False)` as the private reference. No graphlike
decomposition and no independent-channel approximation are allowed.

## Anti-compression test, to be measured before handoff

The generic shortcut independently propagates each fault forward through all
remaining operations. Its cost is proportional to the number of faults times
the expanded circuit size. It is deliberately provided, not made artificially
hard to discover. Exact one-fault propagation is a valid correctness oracle on
tiny cases but should fail the fixed runtime limit on source-realistic
repeated surface and nongeometric HGP extraction circuits.

Before accepting the pilot, record real counts of qubits, rounds, detectors,
expanded operations, faults, output terms, reference CLI and kernel runtime,
weak CLI runtime, correctness, and CPU-budget failures in `calibration.json`. Require at
least one surface case and one HGP case on which the weak baseline exhausts its CPU budget
while exact Stim finishes well within the same limit. If this does not occur,
increase actual extraction size, not parser or format complexity. No
unmeasured speedup or timeout claim is an acceptance result.

## Independent implementation bottlenecks

1. Backward Clifford fault sensitivity or an equivalently scalable algorithm:
   X/Z/Y anticommutation, control/target direction, phase gates, and correlated
   products. Correct measurement bookkeeping alone cannot solve propagation.
2. Measurement/reset and parity lifetime bookkeeping: resets erase prior
   sensitivities, measurements create record dependencies, XOR cancellations
   occur, and repeats carry record references across boundaries. Correct
   unitary propagation alone cannot solve this module.
3. Output probability algebra: aggregate independent events by their FULL
   detector-plus-logical signature, retain observable-only events, discard
   silent events, and handle exact parity probabilities. Correct support with
   summed probabilities is still wrong.
4. Sparse scalable execution: repeated large nongeometric extraction prevents
   a table lookup, a surface-only geometric rule, or quadratic fault-by-fault
   replay from meeting the runtime budget.

## Grading

Compare canonical signature support F1 and normalized probability L1 fidelity;
their product is semantic quality Q in [0,1]. Dimension mismatches, duplicate
terms, invalid indices, invalid probabilities, and malformed answers fail.
Also report exact agreement at tight floating-point tolerance independently
from the continuous score.

For each case measure weak quality Qw, weak CPU Tw (the budget on exhaustion),
and actual reference CLI CPU Tr. For participant CPU time T, set
`speed = log((Tw+epsilon)/(T+epsilon)) / log((Tw+epsilon)/(Tr+epsilon))` and
`score = 100 * (Q**4 * (1+speed) - Qw**4) / (2-Qw**4)`.
Weak maps to 0 and exact reference to 100; neither negative values nor values
above 100 are clipped. Require Tw > Tr before including a case in the scored
suite. Use the equal-weight mean across cases. The fourth power prevents a
very fast incorrect model from getting nearly full credit. Missing/timeout
outputs have Q=0. Keep the raw semantic and timing fields visible to auditors.

## Isolation and limitations

An environment-variable cleanup is not a security boundary. The main harness
must give the participant only the public tree and runtime inputs and deny
network/private paths. Evaluator subprocesses must not inherit private vendor
paths. No external agent is launched here. Validation includes tiny exact
cross-checks against the independent forward compiler and Stim's own
noise-free detector checks. Challenge generation and calibration are private.
