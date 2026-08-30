# One scientifically motivated ratchet

Primary source verified on August 28, 2026: arXiv:2503.20006v2, dated May 7,
2025, Weflen et al., *Exploiting a Shortcoming of Coupled-Cluster Theory: The
Extent of non-Hermiticity as a Diagnostic Indicator of Computational Accuracy*.
Equation (4) defines the density asymmetry diagnostic as the Frobenius norm of
the density minus its transpose, divided by sqrt(number of correlated electrons).
The title in the task-planning prompt was a paraphrase; this is the verified title.

The article motivates using density asymmetry as a computational diagnostic.
It does not establish this challenge's combined screening heuristic as a theorem,
nor does it supply the cutoff 0.001 or a guarantee of density representability.
The original scientific seed remains arXiv:2106.06850, unrelaxed CCSD lambda RDMs.

Generation-one fresh agents found Hamiltonian-derived witnesses with numerically
exact right ground states but strongly asymmetric lambda densities. Their DADs
are approximately 0.277948 and 0.382145. Thus their unphysical population predictions
already carry an obvious density-asymmetry warning. The single generation-two
ratchet asks for the same population violation while suppressing that warning:
`DAD <= 0.001`. All original bounds, the 0.02 target, Hamiltonian domain, amplitude
convention, and the 64-step root certificate remain fixed.

This is one primary mode-B counterexample search, not a second task or an added
implementation exercise. DAD is computed from the unsymmetrized density using
all entries. No passing private generation-two witness is assumed. Lack of a
numerical witness is not an impossibility result. Feasibility remains an open
author-side calibration question unless an independent verified witness or a
mathematical obstruction is established.
