# Public interface and semantics

## Fixed data

`model.json` is the authoritative public binary model. It contains 512 fault
columns and 192 detector rows, over GF(2). `columns[index]` is a zero-padded,
48-digit hexadecimal integer: bit `row` is `H[row, index]`, with detector 0 the
least significant bit. Leading zeros are significant only for fixed-width
serialization. `observable[index]` is the corresponding bit of one logical
parity. `num_faults`, `num_detectors`, `num_observables`, `weight_bound`, and
`fault_probability` specify 512, 192, 1, 20, and 0.001 respectively.

The columns are dense, nonzero, and distinct. H has row rank 192. There are no
zero-syndrome sets of two or three distinct columns. No claim of optimal distance
or uniqueness of a weight-20 solution is made. All fault IDs have the same
physical probability and the same serialization format.

`memory.stim` and `model.dem` are complete, not abbreviated. DEM instructions
are listed in fault-ID order, but an external DEM compiler may reorder them.
The column/observable pair, not a compiled DEM line number, identifies a fault.
`claim.json` records the wrapper's assertion, model hash, and exact search result.

## Physical instrument

There are 705 qubits: data 0–511, check ancillas 512–703, and logical-readout
ancilla 704. All start in |0> via Z resets. A single `X_ERROR(0.001)` instruction
applies independent Bernoulli X noise to each of the 512 data targets. There is
exactly one allowed fault location per data qubit, and no other noise.

For row `row`, apply a CNOT from every data `index` with `H[row,index]=1` to
ancilla `512+row`, measure that ancilla in Z, and annotate its result with one
`DETECTOR rec[-1]`. Finally, accumulate the public observable parity onto ancilla
704 in the same way, measure it, and apply `OBSERVABLE_INCLUDE(0) rec[-1]`.
Gate order within each parity is increasing data ID. Checks are in increasing
row order; observable readout follows them. All gates and measurements are ideal.

Consequently, for a binary fault vector `fault_vector`, the detection record is
`H * fault_vector`, and the logical flip is `observable * fault_vector`, modulo
two. The noiseless record is all zero. The commuting Z checks are independent;
the observable is independent of them. This can be viewed as a Z-only
stabilizer code with 320 unprotected logical degrees of freedom and one monitored
Z observable, prepared in a known state. The task's distance is restricted to
these 512 X locations and this observable, not arbitrary Pauli circuit distance.
Dense hyperedges must not be replaced by a graphlike approximation.

## Supplied search, exactly

`overconfident_search.py` is a standalone Python implementation, **not** a
reimplementation or invocation of Stim's internal search. Its fixed parameters
are maximum fault weight 20, edge degree 112, intermediate detector weight 104,
beam width 64, and nonincreasing detector weight after the first fault.

1. Start with the empty support, syndrome zero, logical parity zero.
2. At each depth 1–20, visit retained parents in their current order and append
   each fault ID greater than the parent's last ID, in ascending order. Thus
   every explored support is distinct and sorted. There is no state merging.
3. Reject an extension if the new column's detector weight exceeds 112; otherwise
   compute XORs and reject if the new syndrome weight exceeds 104; otherwise
   reject if a nonempty parent has a smaller syndrome weight than its child.
   These tests occur in that order; first-fault seeds are exempt only from the
   nonincreasing test.
4. Immediately return the first surviving zero-syndrome, odd-logical candidate,
   before beam selection. Otherwise sort surviving candidates by
   `(syndrome_weight, 1-logical_parity, support_tuple)` and retain the first 64.
   No randomness, wall-clock limit, or undocumented budget is used.
5. Stop on an empty retained frontier or after depth 20. If no witness was found,
   the wrapper improperly emits `claimed_certified: true` and
   `claimed_distance_lower_bound: 21`, despite `search_exhaustive: false`.

The false claim is that **all** supports of size at most 20 were ruled out, not
merely the explored ones. The recorded counters expose the pruning. Stim's
similarly motivated cutoff API explicitly warns that it is heuristic and offers
no such guarantee; this task does not allege a Stim bug.

## Submission and checker

Only `witness.json` is graded. The UTF-8 JSON object must have exactly one key,
`faults`, holding a list of distinct integer IDs in [0,511]. Booleans, floats,
strings, duplicate IDs/keys, extra fields, nonfinite values, symlinks, nonregular
files, and files larger than 16,384 bytes are rejected. Order is immaterial.
An empty list is a well-formed unsuccessful baseline artifact.

From the read-only participant directory, with a separate writable output directory:

```sh
python3 baseline/solve.py --output OUTPUT_DIRECTORY/witness.json
python3 input/check_witness.py OUTPUT_DIRECTORY/witness.json
python3 input/overconfident_search.py --output OUTPUT_DIRECTORY/witness.json --report OUTPUT_DIRECTORY/search_result.json
```

The checker prints JSON and exits 0 for an accepted counterexample, 1 for an
unsuccessful artifact, and 2 for an input/configuration error. No package beyond
Python 3.10+ is needed. The evaluator uses its own trusted model and implementation,
not modified participant scripts. The evaluator also reproduces the supplied
bounded search's failed claim; it does not search for a replacement witness.

`valid` is true **only** for a nonempty support of weight at most 20, detector
weight zero, and logical parity one. Such a witness scores 1. All other
well-formed nonempty artifacts receive the diagnostic score

`0.10 + 0.15*min(1,20/weight) + 0.45*(1-detector_weight/192) + 0.10*logical_parity`.

This is at most 0.80 and never counts as success. Empty or malformed artifacts
score zero. A heavy exact logical word earns diagnostics but is invalid. Scores
are not a certificate, lower bound, or calibrated estimate of search progress.

## Primary sources

- Craig Gidney, *Stim: a fast stabilizer circuit simulator*, Quantum 5, 497 (2021),
  arXiv:2103.02202. `https://arxiv.org/abs/2103.02202`
- Stim tag v1.15.0, Python API reference, `Circuit.search_for_undetectable_logical_errors`:
  `https://github.com/quantumlib/Stim/blob/v1.15.0/doc/python_api_reference_vDev.md`
  (The filename says vDev; the repository tag pins the referenced release.)
- Stim tag v1.15.0, gate reference, X_ERROR, CX, R, M, DETECTOR, OBSERVABLE_INCLUDE:
  `https://github.com/quantumlib/Stim/blob/v1.15.0/doc/gates.md`
