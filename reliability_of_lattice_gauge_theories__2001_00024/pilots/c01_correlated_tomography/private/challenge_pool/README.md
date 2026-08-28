# Held-out groups and ratchet policy

| Split | Ramp times (ms) | Cases | Role |
|---|---|---:|---|
| screening | 0, 60, 90 | 12 | Three real measurement blocks, four inference families |
| challenge | 30 | 4 | Disjoint real block; not a new synthetic trajectory |
| confirmation | 120 | 4 | Reserved, participant-unseen block; do not tune against it |
| ratchet_candidates | 30 | 4 | Unactivated sparse-readout variants of challenge data |

Each family contains the four real A--D readout tracks. `projected` conditions on
eight intended occupation states; `leakage` permits all 64 states up to three
atoms per site; `one_matter_orientation` removes one occupation-sensitive
measurement but retains the split-signal sum; `density_only` removes all
correlated occupation constraints while still scoring readout fits. The last
family directly exposes the failure of marginal-product tomography.

Cases sharing a ramp time are **not independent experimental replicates**.
Twenty published traces and five density rows are the experimental information
budget, not 24 newly collected experiments. Every fifth point of each real
trace is withheld; the remaining points and their published standard deviations
are unchanged. Withheld signal values are private audit data; prediction targets
are the defined visible-data fit, not an oracle for noisy future shots.

Only `participant/` and the submission may be mounted for a solver. Do not expose
this directory, references, source workbooks, validation outputs, or weak solver.
The common isolated runner supplies the per-case input over its controlled path.

## Genuine counterexample ratchets

The four sparse candidates are precomputed and source-grounded but **not yet
evidence of a solver failure**. Activate a candidate only after recording a
reproducible failure, its numerical witness, the implementation it distinguishes,
and why it adds information beyond current cases. Preserve its original source
row lineage. Examples worth testing: omitted damping under peak-biased sampling;
incorrect atom-number normalization; a product-state certificate; adding
individual extrema instead of optimizing the gauge projector; dropping a noisy
channel without reporting envelope inflation; assuming empty omitted sectors.

Additional source-grounded candidates may relabel left/right consistently,
remove actual measured rows, withhold an actual channel, or change an explicitly
declared calibration/uncertainty assumption. Never call these new experiments,
fabricate labeled populations, or import published Fig.4 answers into a case.
Keep confirmation unchanged and sealed during any ratchet. Its SHA256 is in
`../reference/manifest.json`. Adding a new family requires explicit review rather
than silently changing the scoring mixture. Main owns selection and promotion.
