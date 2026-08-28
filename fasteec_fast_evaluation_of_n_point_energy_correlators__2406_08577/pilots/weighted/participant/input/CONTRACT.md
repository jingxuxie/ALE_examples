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

## Weighted projected observable

Query fields: `order` (integer 2..8), `kappa` (1..2), `algorithm` (`ca` or
`kt`), `resolution` (>1 for ca, >0 for kt), `log_min`, `bins`.

For uncompressed particles, sum over ordered order-tuples **with replacement**
the weight product of `(pt_i/sum_j pt_j)^kappa`; histogram the maximum pairwise
rapidity/periodic-azimuth distance in the tuple. Coincident indices count.

For compatibility the target uses the following finite-resolution prescription,
not the exact uncompressed observable. Recluster each supplied jet with FastJet
R=1.5 and `pt_scheme`, using the requested algorithm (generalized-kT powers
0 and 1 respectively). At every binary split let theta be the rapidity/azimuth
distance of the children. Resolve both children with
`exclusive_subjets(theta^2/(1.5^2*resolution))` in the requested clustering tree.
At this node include only tuples whose support intersects both children;
descendant-only contributions use their own resolution. Geometry is the
pt-scheme subjet rapidity and azimuth. For kappa=1 use subjet pt divided
by the original scalar total pt. For kappa!=1 use sum of constituent pt^kappa
divided by the original scalar total pt^kappa as each subjet's weight.
Single-particle leaves contribute the corresponding order-th power at zero.
These rules define the observable even where finite-resolution errors differ
from the exact particle-level result. Inputs recluster into a single R=1.5 jet.
