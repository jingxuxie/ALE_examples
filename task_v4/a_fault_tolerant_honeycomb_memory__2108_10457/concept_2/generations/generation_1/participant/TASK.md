# Design a honeycomb memory for heralded phase erasures

**Mode C — construction.** Find a static 24-site local-Clifford pattern that
makes a honeycomb quantum memory robust to flagged laboratory-frame phase
errors. The same supercell must work on all three supplied periodic lattices,
containing 24, 96 and 216 data qubits. Preserve both encoded qubits: all four
logical Pauli coordinates count.

Submit a regular, non-symlink `design.json` file containing exactly
`{"z_image": [24 integers]}`. Entries `0`, `1`, `2` select original-frame
`X`, `Y`, `Z` images of a laboratory `Z` error. The identity baseline is 24 twos.
The host fixes geometry, timing, detector information and logical transport;
your artifact changes only the repeating local measurement bases. Arbitrary
native two-qubit Pauli measurements are explicitly permitted. No submitted
program is executed.

The exact witness is correctability of **every error combination** within
each flagged support `E`:
`rank_GF2([H_E; L_E]) - rank_GF2(H_E) = 0`, using all four logical rows.
This is an idealized heralded-dephasing task, not a decoder benchmark or a
claim about ordinary EM3 thresholds.

**Pass target: core score at least 0.85, with every size × family group at
least 0.60.** The core score averages nine correctability fractions across
independent, spatial-stripe and temporal-burst erasure families. Hidden
supports are independent of public practice draws but follow the same
published distributions. Lower mean ambiguity is also reported.

Development budget: **one hour**. Artifact limit: **16 KiB**. Evaluation uses
only Python's standard library. Read `workspace/INTERFACE.md` for the exact
model, schema, data format and practice commands; `input/objective.json`
records the frozen scoring contract. A runnable identity baseline and a
faithful public practice checker are included. Optimize held-out robustness,
not memorization of the supplied practice supports.
