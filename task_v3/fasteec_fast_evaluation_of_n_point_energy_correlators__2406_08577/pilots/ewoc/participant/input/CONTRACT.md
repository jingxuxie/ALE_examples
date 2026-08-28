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

Query fields: `geometry`, `algorithm`, `radius`, `observable`, `kappa`, `log_min`, `bins`.

## Subjet observables

Query fields: `geometry` (`pp` or `ee`), `algorithm` (`ca`, `kt`, `antikt`),
`radius` (positive, at most pi), `observable` (`mass` or `angular`),
`kappa` (positive), `log_min`, `bins` (at least 3).

Convert each input constituent to the massless four-vector
`(pt*cos(phi), pt*sin(phi), pt*sinh(y), pt*cosh(y))`. Recluster all constituents
of each supplied jet together, retaining every inclusive subjet at zero pt cut.
Use FastJet E-scheme. The pp algorithms are Cambridge/Aachen, kT, and anti-kT.
The ee algorithms are finite-radius `ee_genkt_algorithm` with powers 0, +1,
and -1, respectively, not exclusive Durham clustering. The radius is an angle
in radians in ee and a rapidity/azimuth radius in pp.

Let P_i denote a recombined subjet. The denominator W is the sum of ORIGINAL
constituent scalar pt in pp and original constituent energies in ee. Define
`z_i=pt(P_i)/W` in pp, `z_i=E(P_i)/W` in ee. For every ordered pair (i,j),
including each diagonal once, add `(z_i*z_j)^kappa` at coordinate X:

- Mass, i!=j: `sqrt((P_i+P_j)^2)` in GeV, including both subjet masses.
- Mass, i==j: `sqrt(P_i^2)`, the individual subjet mass, not twice that mass.
- Angular, i!=j: recombined-axis rapidity/periodic-azimuth distance in pp;
  three-momentum opening angle in radians in ee.
- Angular, i==j: zero.

Apply kappa AFTER recombination. Do not divide mass by the parent momentum,
discard massive diagonal contributions, substitute massless merged axes,
or normalize the output to unit area. Sum over bins equals the per-jet mean
of `(sum_i z_i^kappa)^2`. E-scheme does not conserve scalar pt in pp.

This concept OVERRIDES the common logarithmic-axis convention. There are
`bins-2` finite logarithmic cells between 10^log_min and U, plus separate
underflow and overflow. U=10000 GeV for mass and U=pi for angular. If F=bins-2
and L=log10(U), finite edges are `10^(log_min+(L-log_min)*k/F)` for k=0..F.
Cell zero contains X<10^log_min; finite cell k+1 contains the interval between
edges k and k+1; the final cell contains X>=U. Exact upper edges belong to the
cell on their right. Output still uses the common JSON interface and per-jet
mean bin masses.
