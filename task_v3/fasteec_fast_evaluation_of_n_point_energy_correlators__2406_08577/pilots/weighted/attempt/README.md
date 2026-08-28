# Weighted angular-correlator submission

Run `python solve.py --input JOB.json --output RESULT.json`.

`solve.py` invokes the cached `engine` executable. If necessary, it compiles
`engine.cpp` with the supplied static FastJet library. Compilation intermediates
stay in this directory. Event paths are resolved relative to the job file.

## Numerical method

The engine clusters each event once per requested algorithm, with FastJet
R=1.5 and `pt_scheme`. Each binary split uses the prescribed child
`exclusive_subjets` cutoff. Subjet weights for nonunit kappa are sums of the
original normalized constituent weights, not powers of the recombined pt.

For each bin threshold, construct the graph whose edges connect subjets at
or below that threshold. A tuple has diameter below the threshold exactly
when its distinct support is a clique. For vertex weights `w`, the exponential
generating function is

`F(t) = sum over cliques S of product over i in S of (exp(w_i*t) - 1)`.

Its nth derivative at zero is the ordered, with-replacement nth moment.
Subtracting the two single-child clique moments retains precisely the mixed
tuples belonging to this split. Successive cumulative differences give bin
masses. Original constituent contacts are added separately, and the accumulated
histograms are divided by the supplied number of events.

The exact recursion uses true-twin merging, analytic universal-vertex sums,
factorization over complement-graph components, and bounded memoization.
Orders through eight and up to four kappa values are evaluated together.
Clustering, split resolution, and angular distances are reused across queries.
There is no sampling, constituent removal, or extra resolution approximation.

## Validation

- `python validate.py`: public fixture versus independent positive support
  enumeration; all orders and both algorithms; noninteger weights; ordered-tuple
  particle-level reference; contact and periodic-angle checks; mixed axes;
  input-order, boost, rotation, and scale checks; mass conservation.
- `python check_ring.py`: 139-particle near-antipodal configurations, compared
  with independent cycle-graph counting and weighted polynomial dynamic
  programming. These exercise a difficult high-order graph structure.
- `python benchmark.py`: 139-particle uniform/core stress cases, several
  resolutions, and 3,000 public-fixture jets with 42 simultaneous queries.
- `python check_large.py`: 100,000 public-fixture jets and 42 simultaneous
  queries under a 3 GiB address-space limit. Records runtime, peak child RSS,
  and mass-conservation error in `large_batch.summary.json`.

Small-case normalized errors are at double-precision roundoff (approximately
4e-15 or less). The high-multiplicity stress cases include full particle
resolution, rather than truncating the input multiplicity.

The measured 100,000-jet, 42-query public-fixture batch took 24.8 seconds
including entrypoint startup, with 84.5 MiB peak child RSS. Its maximum relative
total-mass error was 1.3e-12. This benchmark repeats the three public jets;
it is not a measurement on an unseen CMS ensemble. The 139-particle weighted
near-antipodal cycle agrees with independent polynomial dynamic programming
to 8.4e-16 relative error and takes about 0.011 seconds in the engine.

## Limitations

This implements the weighted contract only. Arithmetic is double precision.
Exact clique recursion has data-dependent runtime; memoization is capped to
bound memory. The bitset implementation supports up to 192 resolved subjets,
covering the contract's maximum of 139 constituents. Inputs that do not form
one R=1.5 jet are rejected, as they are outside the stated contract.
