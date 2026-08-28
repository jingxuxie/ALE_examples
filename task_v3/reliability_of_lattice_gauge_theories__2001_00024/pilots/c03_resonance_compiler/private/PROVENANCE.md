# Provenance — written before construction

This is an author-reimplementation benchmark, not released paper software, an
official benchmark, or an official bug-fix. The synthetic engineering wrapper,
finite hardware alphabet, channel placements, uncertainty boxes, and evaluation
metric are new. No claim of a new protection theorem or fundamental solution is
made. This document and ANTI_COMPRESSION.md precede implementation and case freeze.

## Source chain

* Halimeh and Hauke, *Reliability of lattice gauge theories*, arXiv:2001.00024,
  PRL 125, 030503 (2020). The supplied original source is
  `../../authoring/sources/target_tex/arXivVersion.tex` (relative to the pilot
  root). It motivates protection of physically reachable gauge-breaking errors,
  rather than arbitrary integer constraints. Its Z2 generator includes a
  staggered background and a shift; our protocol instead explicitly uses the
  successor paper's ±1 convention. We do not silently identify these conventions.
* Halimeh et al., *Gauge-Symmetry Protection Using Single-Body Terms*,
  arXiv:2007.00668, PRX Quantum 2, 040311 (2021). Primary source:
  `https://arxiv.org/pdf/2007.00668`. Equation numbering here refers to the
  inspected arXiv PDF: (14), compliance; (19), link flips and matter pair errors;
  Fig. 3, six-site compliant vector (-115,116,-118,122,-130,146)/146;
  Fig. 4, local staggered sequence; Sec. IV B and (20), digital overrotation;
  Sec. V B, correlated sigma-minus / tau-plus / sigma-minus error on four
  consecutive constraints. The PRX version can have different equation numbers.
* Halimeh et al., *Stabilizing lattice gauge theories through simplified local
  pseudogenerators*, arXiv:2108.02203, inspected v2 (2022). Primary source:
  `https://arxiv.org/pdf/2108.02203`. Equations (4),(5) and Table I distinguish
  G=(-1)^n X_left X_right from W=X_left X_right+2 g_target n.
  Equation (6) supplies assisted hopping and density-conditioned link errors.
  Sec. III B / Fig. 3 uses c_j=[6(-1)^j+5]/11 for local errors.

## Reimplementation boundary

The constructive reference starts from these published staggered, finite
compliant, and period-two local sequences, quantizes them to the available
controls, then performs bounded discrete local optimization and digital phase
search. Repeating a finite compliant vector is only an initialization: it is NOT
a globally compliant sequence at long lengths. All accepted quality values are
recomputed for the actual reachable channels, never inferred from a paper label.

The task measures direct departures from the entire target sector under each
specified local coherent channel, not high-order error words, long-time dynamics,
the spectrum of H0, or full all-sector compliance. Simultaneous correlated errors
are explicit physical operator products, not arbitrary integer-vector puzzles.
Extra short-range crosstalk products, bare U1 hopping, and the U1 matter drive
are synthetic. Their explicit operators are given in the case generator.
For Z2 the protection includes two-link terms: it is NOT a single-body-only
implementation. Digital circular gaps certify the specified diagonal protection
layer, not the full interacting Floquet spectrum. Uncertainty is worst-case
coefficient error within stated independent bounds. Channels are separate error
mechanisms; interference is retained within each channel but not across channels.

No fresh Codex participant run is authorized here. Empirical generic-solver
hardness and retention/discard decisions belong to the main tournament.
