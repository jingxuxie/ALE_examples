# Continuous-order projected energy correlator

Run `python solve.py --input JOB.json --output RESULT.json`. The Python entrypoint
compiles and caches the C++17 engine in this directory, using the supplied static
FastJet library. The engine is single-threaded and accepts constituents in any
event order while preserving their within-event order.

## Exact finite-resolution algorithm

Each jet is clustered with generalized-kT power zero, radius 1.5, and the
pt recombination scheme. At every binary split, each child is independently
resolved into at most `floor(nsub/2)` exclusive subjets. Original constituent
contacts are added separately. There is no sampling or constituent reduction
beyond the resolution prescription in the contract.

Let `f(S) = (sum of fractions in S)^nu`, with `f(empty)=0`. The recursive
subset weight is the Boolean-lattice Möbius transform of `f`. For a given
diameter-bin upper boundary, allowed subsets are precisely the cliques of the
graph of allowed pairwise distances. Every clique is contained in a maximal
clique. The sum of cross-child weights over all subsets of a clique `C` is

`g(C) = f(C) - f(C intersect left) - f(C intersect right)`.

Inclusion-exclusion over the maximal cliques, collecting identical intersections,
therefore gives the exact cumulative cross-child mass as a short signed linear
combination of `g(C)`. Differences between successive cumulatives give bin
masses. This avoids computing all `2^nsub` fractional powers at each node while
preserving negative contributions and the actual maximum-pair distance.

Histogram accumulation uses extended precision; fractional powers and FastJet
kinematics use double precision. Order one is handled analytically. There is no
clipping of negative weights and no normalization reset. A separate exhaustive
long-double Möbius-transform mode is included for numerical cross-checking.

The implementation is for `kind="fractional"` only. It computes the bounded
resolution observable, not the full uncompressed-particle observable when a
child exceeds its cap. Extreme unphysical floating-point inputs remain subject
to the usual limits of double precision.

## Validation

Run `python validate.py --benchmark-events 10000` for the public sample,
independent full-subset enumeration on small jets, exhaustive local Möbius
transforms on jets up to 139 constituents, signed polygon geometry, integer
orders, odd caps, contact/overflow bins, periodic azimuths, kinematic and
permutation invariance, and rebinning. Results are in `validation_report.json`.

After that command, `python stress_validate.py` repeats the benchmark ensemble
to 100,000 jets without materializing it in Python memory. It runs the actual
entrypoint from the read-only participant directory, pins the process to one
CPU, imposes a 3 GiB address-space limit, and checks agreement with the smaller
ensemble's mean. Measurements are in `stress_report.json`. Its large temporary
event file is deleted after successful validation.
