# Break a bounded-distance certificate

The supplied deliberately overconfident, pruned syndrome-search wrapper claims
that the fixed parity-memory instrument has no undetectable logical fault of
weight at most 36. Falsify that claim with a concrete counterexample.

Submit `OUTPUT_DIRECTORY/witness.json` containing exactly `{"faults": [integer IDs]}`.
Choose 1–36 distinct IDs from 0–511 whose detector columns XOR to zero and whose
observable bits XOR to one. Any such set is accepted; an argument that pruning
is unsound, or a heavier logical fault, is not a successful submission.

The entire fixed matrix, observable, physical circuit, search implementation,
claim, and checker are in read-only `input/`. See `input/README.md` for technical
details. The participant directory is read-only. Work only in the separate empty
output directory supplied by the runner. The evaluator reads the static JSON
artifact and never executes your code. From the participant directory,
`python3 baseline/solve.py --output OUTPUT_DIRECTORY/witness.json` runs the
baseline; `python3 input/check_witness.py OUTPUT_DIRECTORY/witness.json` checks
a candidate. The artifact limit is 16,384 bytes; the search time limit is one hour.

`baseline/` also supplies the successful previous-generation search implementation
and its best artifact on this instrument. Its source and executable are available
as a starting point; this instance has the same dimensions but a different model.

This is a general high-connectivity Clifford stabilizer instrument, not a local
surface code or a hardware-performance claim. The false certificate belongs to
the supplied wrapper, **not Stim**; Stim documents its cutoff search as heuristic.
