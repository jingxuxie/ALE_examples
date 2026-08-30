# D long-chain truth gate

Private bounded numerical gate only. C is complete and untouched. No D public,
evaluator, target, status, champion, or previous-search files are modified.

The three fixed L4/L5/L6 pilots are reused from the prior search, including the
previously uncertified inhomogeneous L6 case. Each receives at most 1000 seconds
of wall-clock numerical work with one BLAS thread. No fresh agents are launched.

`direct_control.py` is a byte-identical copy of the reviewed prior matrix-free
source-native control. Its physics is the open-chain even quartic Hamiltonian
given in the prior proposal. This is not a claim that the unchanged champion's
L2/L3-specific API supports a larger chain.

Labels require two successive retained-basis log-gap changes <=2e-5, onsite Fock
cutoff doubling 80 to 160, an independently changed oscillator frequency, all
four parity-resolved residuals <=1e-10, residual-plus-roundoff/gap <=2e-6, and a
dimensionless gap floor of 1e-6. Labels are computed Ritz gaps, never extrapolated.
These remain empirical truncation certificates, not rigorous infinite-Hilbert-
space error bounds. The full-Fock L4 check uses a separate uncompressed sparse
Hamiltonian and independent eigensolver start and Krylov subspace.

Only certified labels support accuracy comparisons. Timeouts, unsupported input
shapes, and unconverged teacher values cannot establish scientific failure.
Individual control CPU measurements are not extrapolated into 72-case batch
failures. A complete certified corpus and fair full-batch controls would still
be required before freezing any new D target.
