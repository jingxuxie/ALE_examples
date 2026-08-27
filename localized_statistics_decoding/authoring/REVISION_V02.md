# Structural replacement after a perfect first pilot

Version 1 was solved with score 1.0 in 1125.771 seconds, without timeout.
The first launch failed before model initialization because of the parent's
read-only runtime mount; it was retried with the original child allowlist and
does not count as a substantive screening round.

New candidate concepts considered: (a) circuit-to-detector compilation plus
decoding, (b) resource-constrained hard decoding on full quantum code families,
and (c) syndrome-only identification of nonstationary noise followed by regional
soft decoding. Selected (c): it changes the professional task from implementing
inference with known parameters to an experimental calibration and deployment
workflow. It is not extra edge cases or larger instances of version 1.

The participant must infer hidden mode count, rate families, dose dependence,
initial occupancy and temporal transition dynamics from raw parity observations.
Neither true fault histories nor per-mechanism probabilities are supplied.
Those learned parameters must then support uncertainty-aware decoding on new
region topologies and dose schedules. Decisions include the noise model order,
likelihood/optimization strategy, handling label symmetry/local optima, and
local probabilistic factorization. Public predictions provide feedback after
training but do not disclose the learned physical parameters.

Connection to the source: the paper's local binary subspace and regional
factorization workflow is retained as the decoding substrate. The replacement
investigates the consequential upstream assumption that reliable soft fault
information is available. Temporal calibration and joint-risk output are a
newly authored extension, not a claim about the paper's reported algorithm.
