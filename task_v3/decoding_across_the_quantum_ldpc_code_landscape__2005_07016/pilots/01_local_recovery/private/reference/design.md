# Pre-build anti-compression audit

Question: Can one fixed general solver handle every public and hidden case?

A generic binary linear solver obtains syndrome validity, but not logical recovery. A full likelihood optimizer is computationally intractable at the intended block sizes. A dense reliability-ordered postprocessor is a serious baseline, not assumed defeated: the experiment will measure it on tens of thousands of circuit variables and high-rate hypergraph products. Matching is not generally applicable because hypergraph columns have degree greater than two. The two independent scored bottlenecks are recovery through degenerate BP trapping regions and sparse/postprocessing latency at realistic scale. The three source families require success on both, not success averaged across a small easy family.

The participant starts with an explicit implementation of pre-postprocessing minimum-sum BP, plus the original 2020 source snapshot if available. The hidden solution is the official later `ldpc` 2.4.1 BP+LSD implementation (`src_cpp/lsd.hpp`, on-the-fly elimination in `src_cpp/gf2sparse_linalg.hpp`), installed only in the private authoring tree. This is a genuine later-paper capability rather than an author-invented solution. The official distribution includes serial LSD, so this benchmark does NOT claim to test a hardware-parallel implementation.

Primary provenance:
- Original paper: https://arxiv.org/abs/2005.07016 (15-page version, Appendices A–C included).
- Original repository and 2020 pre-state: https://github.com/quantumgizmos/bp_osd/tree/74f86d3ef00f04bbb90a043dfef52e92a091f4d3
- Later algorithm: https://arxiv.org/abs/2406.18655 and https://doi.org/10.1038/s41467-025-63214-7
- Reference source: https://github.com/quantumgizmos/ldpc/tree/d3429964cd4ffe1abfc041c6ec8b8425cb174f40
- Official code fixtures: `python_test/pcms/hx_400_16_6.npz` and `lx_400_16_6.npz`.
- Circuit generator and error-model reference: https://github.com/quantumlib/Stim (installed version 1.16.0).

The high-rate fixture is not described as a random HGP: its exact author-supplied matrix is preserved. The larger HGP matrices are new full-row-rank (3,6)-regular hypergraph products with explicit commuting stabilizers and full logical-observable construction. Circuit faults are sampled from the exact independent detector-error model produced by the official simulator, not from a fabricated detector graph. Fresh random seeds, graph instances, and larger extraction circuits are reserved for confirmation; inspected shot vectors will never be the only confirmation cases.
