# Circuit-to-detector compiler

Run `python solve.py --input case.json --output answer.json`. The solver uses
only the Python standard library and implements the supplied version-1 schema.

The compiler traverses the circuit backwards, retaining the complete output
signature of an X or Z fault on each qubit. These are the columns of the
remaining circuit's linear map from Pauli frames to detector/observable flips.
Clifford gates update these columns by the transpose of their forward frame
map. Resets discard both incoming columns. Measurements add their record's
output parity to the appropriate column without resetting the frame.

Detector declarations and observable includes accumulate into pending absolute
measurement records, cancelling repeated references. A correlated Pauli product
is the symmetric difference of its component columns. Equal full signatures
are merged using the exact independent parity probability, including logical-
only signatures; silent and zero-probability terms are omitted.

Signatures use sparse sets, so a local detector signature does not consume a
bit vector proportional to the total number of rounds. Repeats are traversed
without expanding or copying the input operations, including nested repeats.
For bounded signature support, work is linear in expanded circuit size plus
output size, rather than faults times circuit length. No decoding is performed.

The parsed instruction tree is lowered once into sparse XOR, swap, reset,
measurement, and fault instructions. Repeated rounds reuse this representation.
The CLI releases the original operation tree and writes merged terms in bounded
batches instead of constructing another full output-object tree. The compiler's
data structures are acyclic, so the CLI disables cyclic garbage collection while
retaining normal reference-counted reclamation.

## Validation

Run `python test_solve.py -v` with the supplied participant directory alongside
the submission directory. Tests compare against the independent supplied
forward compiler on 600 randomized circuits, 100 deterministic Clifford echoes,
small nongeometric HGP extraction circuits, nested repeats, and all worked
examples. They also check a 10,000-round circuit against its analytic signature
model, probability endpoints, full logical signatures, and streamed CLI JSON.

Run `python test_solve.py --benchmark --size 12 --rounds 128` to measure JSON
parsing, compilation, and output serialization on an authored repeated HGP
extraction circuit. The production solver has no dependency on the participant
helpers or test module.

An end-to-end CLI run of the 12-by-12, 128-round stress case (1,069,698 expanded
operations and 570,384 output terms) took 3.28 CPU seconds and approximately
93 MiB peak RSS on this host, with the 8-second/1536-MiB limits enforced.
A deliberately larger 24-by-24, 64-round case (2,138,434 operations and over
one million output terms) reached the 8-second CPU limit. These are authored
stress measurements, not claims about unavailable evaluation cases.
