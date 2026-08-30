# Model and objective

The starting distinction is Section 2.3 of Higgott and Gidney, *Sparse Blossom*,
arXiv:2303.15933v2 (January 14, 2025): optimizing one physical explanation is not
the same objective as summing over explanations of each logical class. The
original task used PyMatching's two-pass correlated matching. This generation's
baseline is a successful subsequent compiled BP/reliability-ordered-search
decoder with deterministic ensemble diversity and approximate logical-class
mass aggregation. Neither baseline is claimed to be an exact Bayes decoder.

These are square periodic toric Pauli-frame models, not a gate-level hardware
simulation. Two CSS syndrome sectors are supplied. The four output bits specify
two homologies in each Pauli sector; they do not claim simultaneous measurement
of noncommuting logical observables in a physical experiment.

Each elementary fault mechanism is an independent Bernoulli variable. Its
components fire together. X, Z, and Y mechanisms at one qubit are NOT categorical
alternatives: their coincident effects compose by XOR. XX/ZZ pair mechanisms
couple neighboring parallel edges; YY_time mechanisms couple the same qubit in
adjacent rounds. Readout mechanisms flip two consecutive time-layer detectors.
Both initial and final checks are perfect in the memory interpretation.

The three scientific families are:

1. **Overlapping spatial pairs:** distances 9 and 11, Y-biased channels plus
   unequal XX and ZZ pair rates. Overlapping events can cancel their syndrome.
2. **Known nonuniform crosstalk:** distances 9 and 11, with each mechanism whose
   nonzero H support touches detector columns x=0 or x=1 having double its base
   probability. The profile is part of the known prior, not a hidden shift.
3. **Space-time pair memory:** distances 7 and 9, three rounds, spatial pairs,
   cross-sector Y, temporal YY, and readout faults. One case is uniform. In the
   other, mechanisms touching the middle detector-time layer have readout rates
   multiplied by 4, YY_time rates by 2, and X/Z/Y rates by 1.5. Spatial-pair rates
   are unchanged there. All profile rates are clipped to [1e-8, 0.25].

The explicit matrices/DEM define the model, including wraparound locality and
the chosen logical-frame convention. Each unconditional fault vector e gives
syndrome H e mod 2 and label L e mod 2. No fault-weight conditioning, rejection,
class balancing, decoder labeling, or difficulty selection is used. Public
calibration, hidden challenge and hidden holdout have separate random streams.
The six model configurations are public; only individual draws are hidden.

The objective counts any wrong bit as one failed shot. Reports compare baseline
and candidate on the same samples, with corrected/spoiled counts, paired normal
95% absolute-improvement intervals, paired delta-method relative intervals, and
an exact one-sided discordant-pair binomial test. These intervals are descriptive
and do not correct for repeated adaptive evaluation. Holdout is for final
adjudication, not repeated tuning. This finite suite is not a threshold or a
Bayes-optimality claim.

## Primary sources inspected August 28, 2026

- https://arxiv.org/html/2303.15933v2
- https://github.com/oscarhiggott/PyMatching/releases/tag/v2.3.0
- https://github.com/oscarhiggott/PyMatching/releases/tag/v2.4.0
- https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md

PyMatching introduced two-pass correlations in v2.3; the bundled runtime is
v2.4.0. Its library is available for alternative decoding components, but this
generation is scored against the stronger supplied decoder. Stim independently
audits parity/DEM semantics; challenge labels come directly from Bernoulli faults.
