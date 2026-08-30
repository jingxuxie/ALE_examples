# Scientific specification

This task starts from Section 2.3 of Higgott and Gidney, *Sparse Blossom:
correcting a million errors per core second with minimum-weight matching*,
arXiv:2303.15933, version 2, January 14, 2025. MWPM maximizes a physical
configuration probability in a graphlike independent model; logical maximum
likelihood instead sums probabilities over configurations in each logical class.
This task asks for an accuracy improvement beyond a newer, stronger baseline,
not reproduction of the paper's throughput benchmark.

The baseline follows the official PyMatching correlated-matching implementation:
an ordinary matching pass supplies hypotheses used to reweight correlated edges,
then a second matching pass produces the prediction. Correlations were introduced
in v2.3; the pinned runtime here is v2.4.0, released May 22, 2026.

## Geometry and noise

Each model is a square periodic toric code of distance 7 or 9 with data qubits
on horizontal and vertical edges. Both CSS check sectors are observed; four
classical logical-frame bits specify the two homologies in each Pauli sector.
They are not a claim that four noncommuting logical observables are measured
simultaneously in a quantum experiment. These are Pauli-frame inference models.

1. **Biased Pauli:** independent elementary X, Z and Y mechanisms on each data
   qubit; strong Y bias couples the two check sectors.
2. **Spatial crosstalk:** additional XX and ZZ faults on neighboring parallel
   edges, with unequal channel rates. Events overlap, and their parity can cancel.
3. **Temporal memory:** three data-noise rounds, noisy intermediate checks,
   perfect initial and final checks, and same-qubit Y events spanning adjacent
   rounds. Readout faults flip consecutive time-layer detectors.

All elementary **mechanisms** are independent Bernoulli variables. A Y, XX, ZZ or
YY_time mechanism fires all its components together. X, Z and Y probabilities
are NOT mutually exclusive categorical Pauli probabilities: coincident events
compose by XOR. These are phenomenological, explicitly defined local noise
models, not full gate-level hardware simulations. Periodicity defines locality
at the spatial wrap seam. Exact numerical parameters are in each `case.json`.

For a sampled fault vector e, syndrome = H e modulo 2 and label = L e modulo 2.
Draws are unconditional: there is no filtering for difficult syndromes, no fixed
fault weight, no label balancing and no decoder-generated labels. Multiple
physical explanations of one syndrome need not share a logical label.
Calibration, challenge and holdout use disjoint random streams. Seeds and hidden
labels are not participant assets. Mechanism counts are in the hundreds to
thousands, so enumerating every physical configuration is not a practical solver.

The objective is joint-logical failure rate. Frozen baseline predictions and
candidate predictions are paired on identical shots. Reports include corrected
and spoiled shots, a paired normal confidence interval, a paired delta-method
interval for relative error reduction, and an exact discordant-pair binomial
test. These uncertainty reports describe the frozen finite suite; they do not
remove adaptive evaluation bias. The holdout should be queried only for final
adjudication, not repeatedly used as training feedback.

## Primary sources inspected by the task builder

- https://arxiv.org/abs/2303.15933 and https://arxiv.org/pdf/2303.15933
- https://github.com/oscarhiggott/PyMatching/releases/tag/v2.3.0
- https://github.com/oscarhiggott/PyMatching/releases/tag/v2.4.0
- https://pypi.org/project/PyMatching/2.4.0/
- https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md
- https://arxiv.org/abs/1310.0863

Inspected August 28, 2026. The full DEM, not a graphlike marginal surrogate, is
the sampling ground truth. Stim is an independent implementation used to audit
the published H/L semantics; the challenge labels are sampled directly from H/L.
