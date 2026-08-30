# Ensemble contract

All matrices are one-body Hermitian matrices in one spin sector. Four already
fixed perfect matchings split nearest-neighbor hopping on an even periodic
square lattice; `V` is a real onsite diagonal matrix. There is nothing to color.
Each matching consists of disjoint two-site terms, but different matchings and
the onsite field generally do not commute. A stage is one entire matching or
onsite sweep, not an individual bond. Complex random bond phases describe
quenched Peierls flux; conjugate reverse bonds preserve Hermiticity.

`spec.json` specifies every distribution and evaluation constant. In the
anisotropic family first draw `tx`, set `ty=tx*uniform(ty_ratio)`, and swap the
two hopping scales with probability 1/2; the dimerizations are independent
draws and are not swapped. A dimerization multiplies a bond by
`1+dx*(-1)^x` or `1+dy*(-1)^y`. Bond disorder multiplies it again by an
independent uniform factor. The weak family's two hopping scales are equal.
No hidden sample is conditioned on a design's errors. There is no post hoc
matrix normalization. Chemical potential shifts are included in `V`.

The binary fields model frozen discrete-HS configurations, and clipped normal
fields probe bounded continuous-field inhomogeneity. They are effective
one-body potentials held fixed while changing `h`; they do **not** impose an
HS transformation's square-root-in-`h` scaling. Consequently the exact
comparison is always the exponential of the same five-component Hamiltonian.
This benchmark certifies a frozen-field propagator design, not an improved
interacting QMC algorithm or a universal fourth-order positive splitting.

The development and held-out suites have independent fixed draws of the same
four laws. Every family contains equal numbers of the three listed sizes.
Seeds and held-out instances are private; distributions, sizes, counts,
tolerances, metrics, caps, baseline, and targets are public. Every instance has
16 scored points: four steps times two repetition counts times two errors.
The largest pointwise ratio over **all** these points is also a pass gate;
improving an average cannot hide a badly degraded family or observable.

The onsite and bond layers each count as one abstract linear-time local sweep.
This equal-cost convention deliberately does not reward hardware-specific
dense matrix tricks: the witness is a schedule, not an implementation.
