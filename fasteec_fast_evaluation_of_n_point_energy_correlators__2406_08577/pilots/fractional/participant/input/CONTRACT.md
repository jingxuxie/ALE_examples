# Execution contract

The entrypoint is `python /absolute/attempt/solve.py --input JOB.json --output RESULT.json`.
Resolve the job's relative `events_file` against JOB.json's directory. Each event
row is `event_id pt rapidity phi`, with massless constituents and positive pt.
IDs are contiguous from zero. Azimuth is periodic modulo 2*pi. `nevents` is the
number of supplied jets. Input order is not meaningful except for exact angular
ties, for which stable constituent order is the convention. No external files
or network access are required.

JOB contains `kind`, `events_file`, `nevents`, and a list `queries`. Return
`{"histograms": [[...], ...], "claims": {"method": "...", "limitations": "..."}}`:
one flat numerical histogram per query, in query order. Report per-jet mean bin
**masses**, not densities or unit-area rescalings. Use finite double-precision
JSON numbers. Claims do not earn accuracy credit. The sample is an interface
fixture, not a labeled training set.

Unless a concept-specific axis convention below overrides this paragraph,
logarithmic distance/mass axes have `bins` equal log10 bins between `log_min`
and 0. Clamp underflow (including zero/contact) to bin zero and overflow to the
last bin. For x>10^log_min the bin is
`min(bins-1, floor((log10(x)-log_min)*bins/(-log_min)))`.

The environment has Python, NumPy, SciPy, and g++17. A local static FastJet 3.4.3
dependency is in `workspace/vendor`. Compile with
`-I<workspace>/vendor/include <workspace>/vendor/lib/libfastjet.a -lm`.
The historical implementation in `workspace/legacy` is an intentionally
incomplete starting point. There is no requirement to retain its architecture.
Keep generated binaries and intermediate files in the attempt directory, not
the read-only participant directory.

Evaluation uses multiple unlabeled CMS-derived ensembles, including rare
high-multiplicity jets, and analytic/kinematic checks. Constituent counts are
not reduced for evaluation (up to 139 in the real sample). Large jobs may use
100,000 jets. One CPU thread and 3 GiB address space are available. A job is
terminated after max(60 s, 5*the stored reference runtime +20 s), including
entrypoint startup; cache compilation in your attempt directory. Accuracy is
continuous normalized L1 skill relative to the supplied weak starting
contact-only weak approximation, with a characteristic error scale 2.5% of its error (minimum
0.0005). Runtime receives a smooth penalty on a scale of
20 s +12*reference runtime. Both mean and worst-family results are reported;
a missing central family cannot be hidden by easier cases.

## Continuous-order projected observable

Query fields: `nu` (positive real), `nsub` (integer 2..16), `log_min`, `bins`.
For a finite set S with fractions z_i define W(empty)=0 and
`W_nu(S) = (sum_{i in S} z_i)^nu - sum_{T proper subset of S} W_nu(T)`.
Histogram W_nu(S) at the largest pair distance within S; singleton distance
is zero. This is not interpolation between integer orders, and the result
need not be a positive measure.

The compatibility target uses a specified bounded-resolution prescription:
recluster each supplied jet with generalized-kT power 0, R=1.5, FastJet `pt_scheme`.
At each binary split resolve **each child separately** into at most
floor(nsub/2) exclusive subjets, using `exclusive_subjets_up_to`. Evaluate
the subset measure on this local union, counting only subsets intersecting
both children, then include descendant-only contributions at their own splits.
Fractions at a node are pt-scheme subjet pt divided by the **original
jet's scalar sum of constituent pt**. At original leaves include z_i^nu at
zero. This finite-resolution definition, including independent per-child
caps, is the target; do not substitute either an exact full-particle observable
or an anchor-distance projection. Inputs recluster into one R=1.5 jet.

The target is defined mathematically, but evaluation does not require tiny
relative accuracy for near-zero weights. Integer collapse, signed geometry,
and realistic multiplicity are separate checks. The normalization of a
compressed approximation is not forcibly reset to one.
