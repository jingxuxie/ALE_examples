# Bounded compiler post-pilot audit

No participant, attempt, evaluator, helper, or existing challenge is changed.
Exactly two additional scientific regimes are tested, with unchanged gates,
independent Pauli channels, 8 CPU seconds, and 1536 MiB. Wall allowance is 120
seconds solely to separate known host/mount jitter from CPU failures.

1. Long surface memory: official Stim rotated Z memory, distance 7, 512 rounds
   instead of the pilot's 8. This tests long record lifetimes and high detector
   indices with local fault support, not new syntax or a narrower tolerance.
2. Long nongeometric HGP memory: the same 76-data-qubit HGP construction,
   classical shapes (4,7) and (5,8), seed 613, and both extraction bases, with
   128 rounds instead of 10. This tests repeated nongeometric sparse causal
   propagation, including nine logical observables.

Sources are the already-used official constructors:

- https://github.com/quantumlib/Stim/blob/v1.16.0/doc/python_api_reference_vDev.md
- https://github.com/quantumgizmos/ldpc/pull/69
- https://github.com/quantumgizmos/ldpc/blob/ce5778b7ed9073cc1a77cc424685122d4e216169/src_python/ldpc/ckt_noise/css_code_memory_circuit.py

The submitted implementation uses sparse sets, not detector-wide bitsets.
Its tournament outputs are all exact. Three small-case profiling repetitions
are measurement controls, not additional scientific regimes. They separate
algorithm/JSON CPU from process/startup overhead without changing the code.

Stored exact references may be precomputed outside the runtime limit. Each
reference is then independently recomputed by the unchanged official Python
wrapper under the same CPU/memory limits. Native Stim compilation CPU is also
measured separately. Native speed alone does not establish end-to-end reference
feasibility. A counterexample requires a feasible exact reference and a genuine
candidate correctness/resource failure; otherwise discard the proposed ratchet.
