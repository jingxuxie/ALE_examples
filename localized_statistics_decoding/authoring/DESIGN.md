# Author record

Source: https://arxiv.org/abs/2406.18655 (accepted v2). Inspected sections 2,
4.1, 4.2, 4.3 and the public quantumgizmos/ldpc implementation, specifically
src_cpp/lsd.hpp and src_cpp/gf2dense.hpp. No upstream code is copied.

Three concepts considered before construction:

1. Repair a hard-output reliability-guided cluster decoder under hyperedge and
   rank-deficiency shifts. Rejected as the first choice because a global
   bit-packed solve with a modest search could bypass most local architecture.
2. Repair and extend a regional hard-output prototype into a calibrated joint
   logical-risk decoder, with erased detectors and a run-wide latent noise
   mode. Selected: requires local affine-space summation, cross-region
   coupling, evidence normalization and batch-level inference, with multiple
   viable contraction/search approaches and strong behavioral oracles.
3. Implement rollback-capable on-the-fly binary factorization for an online
   window decoder. Rejected as the first choice because enforcing incremental
   work without implementation inspection would require oversized workloads.

The selected task is an extension, not a claimed reproduction of the paper's
algorithm. It takes the paper's local matrix validity and factorization idea
and changes the output to uncertainty-aware logical statistics. Finding one
solution to a syndrome is no longer enough. The public hardware regions are
not independent: crossing fault mechanisms couple them. A global latent mode
also couples otherwise independent shots. Hidden cases change boundary graph
topology, missing-check patterns, rank defects, and prior support.

Consequential choices: how to represent each affine solution space; when and
how to retain or eliminate boundary fault variables; how to sum degenerate
faults without confusing maximum weight with total mass; how to share evidence
across shots without mixing noise modes independently. The public starter and
validation oracle support an explicit diagnose/run/revise/rerun workflow.

Reference strategy (privileged): regional GF(2) column bases and nullspace
enumeration; character-valued boundary factors; min-width variable elimination;
inverse Walsh transform for the joint logical distribution; log-evidence
Bayesian mixing of a batch-wide mode. This is not required of participants.

All matrices and fixtures are newly generated synthetic detector-error-model
workloads. They are not represented as named code families or threshold data.
Scores measure behavioral probability accuracy, not implementation similarity.
