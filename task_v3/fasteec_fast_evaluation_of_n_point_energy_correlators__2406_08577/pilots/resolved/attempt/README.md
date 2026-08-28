# Joint resolved correlator submission

Run `python solve.py --input JOB.json --output RESULT.json`. Relative event paths
are resolved against the job file. `solve.py` builds and caches `engine` from
`engine.cpp`; the submitted cached binary avoids compilation on normal runs.
The build uses g++17, the host CPU's SIMD instructions, and the system math
library (`libmvec`). No FastJet, clustering, external data, or network is used.

## Numerical method

Every original constituent is retained. For each special constituent, the
remaining constituents are stably ordered by radius, with input order breaking
exact ties. Pair cells retain both radius ratios and signed orientation. The
four-point inner angle is measured from the middle vector, not the outer one.

The inner finite differences telescope within each ratio/azimuth cell because
radial rank is monotone in ratio. Their sum is evaluated using the cell's total
energy and its phi-local prefix. For order four, this conditional inner
histogram depends only on the middle rank. Each outer/middle pair therefore
updates it with the specified first and second finite differences. This is an
exact factorization, not an independent-marginal approximation. One-cell
projections have a separate exact cumulative implementation.

Order three includes all three specified contact types. Order four excludes
every repeated-index contact, including contacts with the special constituent.
Histograms are divided only by the number of processed jets. Non-unit weights
are not normalized or replaced by independent powers of constituent weights.

Power differences use cancellation-safe evaluation. Large exponents use
complementary energy sums to preserve powers of prefixes extremely close to
one. Geometry binning is vectorized, with direct determinant/dot-product angle
evaluation near azimuth boundaries. Histogram accumulation uses double
precision and a single CPU thread. Event storage is streaming rather than
proportional to the total number of jets.

A rare extended-precision prefix path retains fractional-power contributions
when normalized constituent energies are too small to represent as doubles.

## Validation

`python validate.py` compares the public fixture and analytic/random cases
against independent explicit tuple enumeration. It covers both orders,
non-unit exponents, contacts, coincident particles, stable ties, odd/even
azimuth counts, branch cuts, bin boundaries, zero momenta, and tiny weights.
An 800-digit Decimal oracle also checks exponents of order `1e100` with strongly
hierarchical energy fractions. The tests verify the specified two-particle
non-unit contact total of one half, fractional powers of energy fractions near
`1e-600`, omitted exponent defaults, first-jet limits, EOF, and short-input errors.

`python benchmark.py --count 2000` checks streaming throughput on repeated
public 30/38-constituent jets and on synthetic 139-constituent jets. Unit-weight
totals are checked against one for order three and the fourth elementary
symmetric polynomial times 24 for order four. `--mode all`, `--mode unit`, and
`--mode projected` select individual benchmark families.

Measured single-thread runs in this environment, with all four public queries:

| Input | Jets | Wall time | CPU time |
| --- | ---: | ---: | ---: |
| Repeated public 30/38-constituent jets | 100,000 | 162.17 s | 161.42 s |
| Synthetic 139-constituent jets | 100 | 9.66 s | 9.54 s |
| Public jets, one-cell projections | 100,000 | 30.50 s | 26.30 s |

Reported child-process peak resident memory is below 35 MiB for these runs.

## Limitations

Results have floating-point rounding and the contract's intentional non-unit
phi-binning dependence. Runtime grows with multiplicity, query count, and the
number of conditional cells; large dense output shapes also require memory
proportional to the requested output. There is no stochastic sampling,
constituent truncation, or unit-area rescaling. Cached binaries target the
current machine; remove `engine` to rebuild for another CPU.
JSON serialization is streamed in bounded chunks rather than retaining Python
lists for all output histograms at once.
