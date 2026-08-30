# Discovery shortlist

Paper seed: Sivarajah et al., *t|ket>: A Retargetable Compiler for NISQ Devices*, arXiv:2003.10611v3, 24 April 2020. Discovery date: 28 August 2026.

Eight concepts were considered before the tournament:

1. **A, selected:** improve a portfolio qubit router on weighted, sparse architectures with exact dependency/mapping replay and a fixed worst-family improvement target. Search quality, hardware heterogeneity, and compilation latency interact; implementing a textbook router alone is not the objective.
2. **B, selected:** construct a resource-regret counterexample to a supplied finite-lookahead routing portfolio, accompanied by a cheaper, independently replayable legal routing witness. The claim under test belongs to the supplied benchmark method, not a theorem asserted by the paper.
3. **C, selected:** recover compact native CNOT networks that implement exact linear maps and expose specified phase parities, under simultaneous gate/depth bounds. Private forward construction supplies feasibility witnesses without giving inverse synthesis to participants.
4. **D:** predict architecture/compiler choice from held-out hardware calibration and circuit observations. Not built: no sufficiently clean, sizeable hardware outcome dataset is locally available; synthetic labels would risk collapsing to reproducing the simulator.
5. **E:** actively identify coherent/correlated device errors using compiled circuit probes. Not built: query-model design and identifiability validation would dominate the experiment, weakening the paper connection.
6. **F:** repair interactions between conditional boxes, implicit permutations, and compiler predicate caches. Not built: a minimal reduced system risks being artificial; a full frozen upstream build is expensive and known bug patches are too direct a solution.
7. **B:** find an AutoRebase/GreedyPauliSimp semantic failure involving PhasedX. Rejected: official issue #1771 contains a direct reproducer, so hiding that issue would test retrieval rather than a difficult scientific search.
8. **C:** construct a Pauli measurement grouping with entangling basis changes and low routed depth. Not built: a promising distinct follow-up, but exact phase/parity synthesis provides a smaller, more auditable verifier and stronger private construction asymmetry.

Only the three selected concepts are built. Private sources, generators, evaluators, witnesses, logs, other concepts, and previous attempts are outside each fresh session's participant/output allowlist.
