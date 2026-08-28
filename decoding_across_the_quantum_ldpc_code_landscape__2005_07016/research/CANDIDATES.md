# Solution-gap ledger

Target: *Decoding Across the Quantum LDPC Code Landscape*, arXiv:2005.07016. Authoring began August 27, 2026 (America/Los_Angeles). This ledger distinguishes source-confirmed capabilities from proposed benchmark formulations. The later source is privileged by filesystem isolation, not claimed to be secret or unpublished.

## A — Repeated decoder lifetime correctness (pre-fix/post-fix)

- Participant starting artifact: `ldpc` 2.4.0 allocator/lifetime code; earlier `bp_osd` history also explicitly discusses a simulation memory leak in commit `70d5c380c2341cd2f9ab92c50f53334acbfb0d84`.
- Private artifact: `ldpc` 2.4.1, repository `d3429964cd4ffe1abfc041c6ec8b8425cb174f40`, whose release commit explicitly identifies PR #97 as a memory-leak fix.
- Central outcome: repeated creation, channel updates, decoding, and teardown maintain bounded memory and correct per-instance results.
- Generic shortcut: cache one decoder or force Python garbage collection. This does not fix native ownership and can retain stale matrix/channel state when the workload alternates codes.
- Independent bottlenecks: native ownership and Cython exception paths; semantic isolation of mutable decoding state.
- Check: stress alternating real matrices, check syndromes/logical outcomes, and inspect resident-memory growth after warmup. Exact repair must be audited before adoption; a one-line lifetime fix alone is not sufficiently hard.
- Sources: https://github.com/quantumgizmos/ldpc/pull/97 ; https://github.com/quantumgizmos/ldpc/commit/d3429964cd4ffe1abfc041c6ec8b8425cb174f40 ; https://github.com/quantumgizmos/bp_osd

## B — Global postprocessing to localized recovery (original/follow-up)

- Participant starting artifact: original 2020 BP/OSD source and a working minimum-sum pre-decoder.
- Private artifact: official BP+LSD and on-the-fly elimination, later `ldpc` release and the 2024/2025 follow-up.
- Central outcome: logical recovery across quantum degeneracy traps without global elimination dominating latency.
- Generic shortcut: dense GF(2) elimination, matching, or more BP iterations. Elimination alone ignores likelihood; matching cannot represent arbitrary high-degree fault hyperedges; more BP iterations do not reliably resolve split beliefs. Global OSD is benchmarked rather than dismissed.
- Independent bottlenecks: posterior/trapping-set recovery and efficient local algebra/cluster handling.
- Check: realistic HGP and extraction matrices, exact syndrome validity, hidden logical equivalence, measured runtime/memory. **Built as pilot 01.**
- Sources: https://arxiv.org/abs/2005.07016 ; https://arxiv.org/abs/2406.18655 ; https://doi.org/10.1038/s41467-025-63214-7 ; https://github.com/quantumgizmos/ldpc

## C — Finite-window decoding of long memories (realistic scale)

- Participant starting artifact: original static code-capacity decoder and complete finite-history detector records.
- Private artifact: later `ldpc/ckt_noise/base_overlapping_window_decoder.py`, `lsd_overlapping_window.py`, and official window simulations.
- Central outcome: bounded-history decoding with correct commit/buffer boundaries and accumulated observable frames.
- Generic shortcut: decode each round separately or invert one full spacetime matrix. Independent rounds lose measurement-error correlations; global inversion grows with memory duration.
- Independent bottlenecks: temporal boundary/commit semantics and sparse local inference; final-readout closure differs from steady-state windows.
- Check: long histories against stored logical outcomes, window-size shifts, endpoint checks, latency/memory scaling.
- Sources: https://github.com/quantumgizmos/ldpc/tree/main/src_python/ldpc/ckt_noise ; https://doi.org/10.1038/s41467-023-42482-1 ; https://arxiv.org/abs/2406.18655

## D — Correlated biased Pauli recovery in changed frames (physical-family transfer)

- Participant starting artifact: independent CSS X/Z decoding with code matrices and explicitly specified local frames/noise channels.
- Private artifact: `quantumgizmos/bias_tailored_qldpc`, its lifted-product constructions, and `bposd.css_decode_sim` correlation-aware channel updates.
- Central outcome: preserve logical information under high bias, Y correlations, and non-CSS frame changes.
- Generic shortcut: use one scalar error rate or independently decode Pauli marginals. A local Clifford rotation changes which physical error is dominant, while Y errors couple the two syndrome sectors.
- Independent bottlenecks: symplectic/frame interpretation and coupled likelihood/degeneracy resolution.
- Check: source-sized lifted-product blocks, biased and correlated families, exact commutation/syndrome constraints and hidden logical observables. **Built as pilot 02.**
- Sources: https://arxiv.org/abs/2202.01702 ; https://github.com/quantumgizmos/bias_tailored_qldpc ; https://github.com/quantumgizmos/bp_osd

## E — Device readout mismatch (real data)

- Participant starting artifact: hardened Surface-13 readout records and nominal noise model, with calibration records rather than known latent error labels.
- Private artifact: the experimental soft-readout analysis and released neural-network decoder/replication scripts from the Surface-13 study.
- Central outcome: recover the logical-error improvement when actual analog distributions, unequal fidelities, and leakage differ from the nominal binary model.
- Generic shortcut: use a single symmetric Gaussian likelihood or optimize hard syndrome weights. The experiment documents unequal fidelities and non-Markovian/leakage complications; hardening discards per-shot information.
- Independent bottlenecks: readout-density calibration and temporal/leakage-aware inference.
- Check: disjoint acquisition runs/input computational states and logical survival curves, with no tuning on held-out state labels. Data download/licensing and a reproducible trained reference remain admission gates; no simulated data is represented as experimental data.
- Sources: https://doi.org/10.1103/PhysRevApplied.22.044031 ; https://github.com/BorisVarbanov/qrennd ; https://github.com/MarcSerraPeralta/surface-13_nn

## F — Circuit-to-detector compilation (multi-component integration)

- Participant starting artifact: parsed Clifford extraction circuits and a limited code-capacity-style conversion baseline, not a complete circuit simulator.
- Private artifact: official Stim detector-error analysis and later circuit-model integration modules.
- Central outcome: obtain semantically correct detector/observable fault signatures and probabilities from nontrivial extraction circuits at realistic size.
- Generic shortcut: replay the complete circuit separately for each fault or assume static check support. The former multiplies circuit length by fault count; the latter misses propagation, resets, temporal offsets, and logical-only faults.
- Independent bottlenecks: Clifford propagation; measurement/reset and detector bookkeeping; probabilistic aggregation.
- Check: compare canonical fault mechanisms or explicitly specified signatures to precomputed simulator output, plus large-circuit runtime. Provide a parsed input schema so parser trivia is not the challenge. **Built as pilot 04.**
- Sources: https://github.com/quantumlib/Stim ; https://github.com/quantumgizmos/ldpc/tree/main/src_python/ldpc/ckt_noise ; https://github.com/oscarhiggott/stimbposd

## G — Correlation-safe decoder ablation (missing ablation)

- Participant starting artifact: original independent-sector Monte Carlo summaries and code/noise configurations.
- Private artifact: joint-channel trajectories and correlation-aware simulation in the bias-tailored follow-up, plus analog follow-up comparison scripts and published data.
- Central outcome: separate improvements from channel information, scheduling, and postprocessing while comparing the same logical experiment.
- Generic shortcut: multiply independent X/Z success probabilities or compare aggregate WER/LER numbers at mismatched noise strengths. Pauli-Y correlation breaks independence; analog variance and hardened syndrome-flip rate must represent the same physical channel.
- Independent bottlenecks: matched physical-channel conversion and statistically valid joint/paired estimands, including censoring at rare logical failures.
- Check: paired trajectories, exact probability identities on auditable small instances, held-out simulations and confidence coverage. This is a proposed missing-ablation task, **not a claim that the original paper contains a proven bug**. A unique strong reference for the full inference task has not been established, so it is lower priority.
- Sources: https://arxiv.org/abs/2202.01702 (Appendix D) ; https://arxiv.org/abs/2311.01328 (noise-model conversion and analysis appendices) ; https://zenodo.org/records/12548001

## H — Reliable-subset reduction without losing degeneracy (performance/correctness)

- Participant starting artifact: fixed-order minimum-weight BP+OSD.
- Private artifact: the MBP+ADOSD/RSR follow-up and its released implementation, identified by arXiv:2412.21118 (v4 dated February 21, 2026).
- Central outcome: reduce search cost while retaining logical-coset performance across CSS/non-CSS and circuit regimes.
- Generic shortcut: freeze all high-confidence bits and stop at the first syndrome-valid vector. A confidence mistake can exclude the correct logical class; degeneracy means minimum weight and maximum logical-class probability are different objectives.
- Independent bottlenecks: safe reliability reduction and degeneracy-aware list search/stopping.
- Check: stored high-quality logical outputs, calibrated confidence failure regions, runtime on more than 10,000 error variables. A runnable release must be pinned before use; not selected for this four-concept round.
- Sources: https://arxiv.org/abs/2412.21118 ; https://arxiv.org/html/2412.21118v3

## I — Analog repeated-syndrome memory (additional follow-up gap)

- Participant starting artifact: hard-syndrome independent-time inference with analog measurement records and a complete physical input schema.
- Private artifact: MQT-QECC analog-information decoding, higher-dimensional code fixtures, and `ldpc` soft-information/augmented decoding.
- Central outcome: use continuous readout while consistently assigning data faults and syndrome faults across a memory experiment.
- Generic shortcut: threshold the readout and run the original decoder, or solve each time slice independently. Thresholding discards shot-dependent reliability; independent slices misattribute measurement faults to persistent data changes.
- Independent bottlenecks: analog likelihood and joint temporal/meta-check inference, with final boundary closure.
- Check: exact latent logical outcomes, source code families, analog-noise and duration shifts, measured execution cost. **Built as pilot 03.**
- Sources: https://arxiv.org/abs/2311.01328 ; https://github.com/munich-quantum-toolkit/qecc/tree/main/src/mqt/qecc/analog_information_decoding ; https://github.com/quantumgizmos/ldpc

## Initial tournament choices

The four built concepts are B, D, I, and F, in that order of pilot IDs 01, 02, 03, 04. This is a portfolio of a scalable recovery service, physical-frame/correlation transfer, analog temporal inference, and a compiler, not eight parameter variants of a single simulator. None is rejected merely because a standard method is predicted to work. The tournament and fresh confirmation determine acceptance.
