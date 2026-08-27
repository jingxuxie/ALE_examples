# Model and archive conventions

Units have hbar=c=1. The real scalar field lives on a circle of circumference
`length=L`, with positive reference mass `mass=m`. Its Hamiltonian is

    H = integral dx [ (pi(x)^2 + (partial_x phi(x))^2 + m^2 phi(x)^2)/2
                      + sum_n g_n(x) :phi(x)^n:_infinity,m ].

The free quadratic part has its infinite-line vacuum energy set to zero.
Interaction normal ordering is relative to the free mass-m **infinite-line**
vacuum. In particular no factor 1/n! is absorbed into the definition of a
coupling. The normal-ordered interaction does not include contractions within
one vertex. This fixes the additive energy convention as well as the theory.
Finite-volume vacuum energy is not zero in this convention, even at zero
coupling. All requested quartic profiles are bounded below; quadratic-only
requests have positive physical mass squared.

Each entry `{degree:n, transfer:q, value:g}` specifies the Fourier coefficient
`g * exp(i*pi*q*x/L)` in `g_n(x)`. An omitted transfer is zero. Nonzero Fourier
coefficients occur in conjugate pairs; supplied values are real. Periodic
profiles have even integer transfers. The archived operator `V[n,q]` is

    integral_0^L dx exp(i*pi*q*x/L) :phi(x)^n:_circle,m .

It changes total doubled momentum by `q` (a simultaneous reversal of all
transfer signs gives the same real-profile Hamiltonian). Consequently
`V[n,q].T = V[n,-q]`, and only their physically paired combination need be
Hermitian. `V[0,0] = L I`; `V[0,q!=0] = 0`.

The circle field expansion is

    phi(x) = sum_r (a_r exp(i*pi*r*x/L) + a_r^dagger exp(-i*pi*r*x/L))
                    / sqrt(2 L omega_r),
    omega_r = sqrt(m^2 + (pi*r/L)^2),  [a_r,a_s^dagger] = delta_rs.

Periodic modes have even integer `r`, including zero. Antiperiodic modes have
odd integer `r`, and there is no zero mode. Only even interactions are used
with antiperiodic boundary conditions. Circle normal ordering puts creation
operators to the left. Occupation states are orthonormal, and no spatial
reflection quotient has been taken in the supplied archives.

`free_energy` is `sum_r N_r omega_r`, with no vacuum constant. The archive is
the projection onto states with this total energy at most its stated cutoff,
not a cutoff on each oscillator independently. `occupations` correspond to
`modes` in the same basis file. All sparse matrices in a sector share that
ordering. Lower cutoffs select indices by `free_energy`, not index count.

`momentum` in a sector means total doubled momentum `sum_r r*N_r`; `null`
means no momentum projection. `parity` is occupation number modulo two;
`null` means both field parities are present. Do not impose additional
reflection or field parity when it is absent from the manifest. The requested
three levels are the three lowest in the specified space, with multiplicity.

The five branches deliberately probe different assumptions:

1. A homogeneous quadratic perturbation: a Gaussian field with a changed
   physical mass, useful for an independent check of truncation effects.
2. A homogeneous periodic quartic field: the original production setting.
3. A homogeneous antiperiodic quartic field: changed mode quantization and
   vacuum; the odd sector uses the smallest positive allowed momentum.
4. A periodic field with uniform cubic and linear terms as well as quartic:
   explicit breaking of field parity, while total momentum remains zero.
5. A periodic spatially modulated interaction: total momentum is not a good
   quantum number; field parity remains good. Degeneracies and nearly
   degenerate states are physically meaningful, not necessarily solver errors.

Useful theoretical evidence, not a renormalization prescription: the
infinite-plane free Euclidean propagator is `K0(m*sqrt(x^2+tau^2))/(2*pi)`;
on the circle it can be obtained by summing images, with alternating image
signs for the antiperiodic field. Its short-distance singularity is logarithmic.
Wick's theorem and the oscillator algebra apply. A total-state-energy
projection is not the same regulator as a local spatial momentum cutoff.
The supplied matrices let you examine actual shell effects before deciding
which asymptotic or numerical treatment is justified.

Hidden requests use the same degree range 1–4, boundary choices and sector
definitions. Typical masses are 1 in the chosen units, lengths 2.5–5.5,
quartic mean couplings 1–2, source magnitudes below 0.7, and cutoffs 10–16.
The inhomogeneous quartic mean exceeds twice the modulation magnitude.
There are no hidden changes of units, column meanings or file formats.
