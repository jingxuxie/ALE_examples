# Bounded private EWOC reference contract

## Scope and provenance

This is a small, private transfer/integration control for the EWOC framework of
Samuel Alipour-fard and Wouter J. Waalewijn, *Energy Correlators Beyond Angles*,
arXiv:2501.17218, especially section 2. It evaluates supplied jets, not a collision
generator or a reproduction of the paper's event selection, plots, or mass fits.
It is adjacent to, not an implementation of, the FastEEC paper 2406.08577. No
Pythia, detector unfolding, grooming, jet areas, ghosts, or parent-jet finding is
part of this interface. Using `ee` on CMS rows changes the mathematical geometry
and weights; it does not turn a proton-collision sample into electron collisions.

The reference is grounded in the clean local checkout of the official
`samcaf/ResolvedEnergyCorrelators` repository, commit
`0736fc3c24d00f1ea7d08b8ea3c62ccd84f7b10e`. Paths in the following source map are
relative to `author/ResolvedEnergyCorrelators/`; line numbers refer to that commit:

- `write/src/ewocs.cc:194`: both pair and contact terms default to enabled;
  lines 200 and 206 select the scalar-weight convention and common exponent.
- `write/src/ewocs.cc:556`: denominator is the sum of original constituent
  scalar weights, before reclustering. Lines 563 and 585 select inclusive subjets
  and their recombined scalar weights.
- `write/src/ewocs.cc:589`: diagonal plus upper-triangular enumeration;
  lines 607 and 615 give mass contacts **at the individual subjet mass**;
  line 625 sets angular contacts to zero. Lines 644 and 649 assign multiplicity
  two and the combined invariant mass to distinct pairs; lines 659 and 666
  select opening angle or rapidity-azimuth distance. Line 695 applies the common
  power to the product of the two subjet fractions.
- `write/src/ewocs.cc:233`: both flow bins are retained. Line 809 divides by the
  number of analyzed jets; line 823 subsequently divides finite-bin contents by
  bin width. This adapter returns the bin integrals **before** that latter step.
- `write/src/utils/ewoc_utils.cc:36`: the upstream default exponent is one.
  Lines 82, 86, 90, and 175 record algorithm, recombination, exponent, and radius
  metadata. This utility is a defaults/header writer, not a second EWOC kernel.
  Its CMS parent-jet metadata at line 158 are not imposed on supplied jets.
- `write/src/utils/jet_utils.cc:339`: the pp mapping; line 354: the spherical
  generalized-kt mapping; line 474: upstream default subjet recombination is
  `WTA_modp_scheme`; line 662: E-scheme is explicitly supported.
- `write/src/utils/opendata_utils.cc:77`: massless four-vector conversion and
  skipping zero-pt rows. `write/src/utils/general_utils.cc:137` and
  `write/src/utils/general_utils.cc:281`: base-ten bin edges and bin assignment.

This standalone adapter re-expresses that bounded observable calculation; it
does not link the generator-dependent upstream executable or header writer.
**Mass is not restricted to distinct ordered pairs.** Omitting the diagonal
would instead select upstream `contact_terms=false`, which is not this contract.

## Invocation and input

Exactly ten positional arguments follow the executable:

```text
ewoc_reference events_file nevents geometry algorithm radius observable kappa log_min bins output_file
```

- `geometry`: exactly `pp` or `ee`.
- `algorithm`: exactly `ca`, `kt`, or `antikt`, interpreted as specified below.
- `observable`: exactly `mass` or `angular`.
- `radius`: the subjet radius, not the supplied parent-jet radius.
- `nevents`: the number of supplied **jet blocks** to average, not a maximum
  event-ID value or the number of simulated collisions.

Input is whitespace-delimited `event_id pt rapidity phi`, one massless constituent
per row, with pt in GeV and phi in radians. Each contiguous ID block is one
already-selected jet. IDs are unsigned 64-bit decimal integers, must increase
between blocks, and need not start at zero or be consecutive. Blank lines and
lines whose first non-whitespace character is `#` are ignored. Headers, extra
columns, trailing row comments, NUL bytes, non-finite numbers, and malformed tokens are
errors. Rows with pt zero are ignored kinematically but still belong to, and
count against the size of, their jet block. Every jet must have positive scalar
weight; zero-weight jets are errors, not silently removed from the average.

For an input row with rapidity y and azimuth phi the four-vector is

```text
px = pt cos(phi), py = pt sin(phi), pz = pt sinh(y)
E = sqrt(px^2 + py^2 + pz^2) = pt cosh(y) in exact arithmetic.
```

Azimuth is reduced modulo 2*pi before conversion. These are massless *input*
four-vectors; merged subjets are generally massive. Rapidity, not pseudorapidity
of a massive merged subjet, is used for the pp distance.

Exactly the first `nevents` complete blocks are evaluated. EOF closes the last
block; EOF before the requested number is an error. A complete, valid first row
of the next block is consumed as lookahead when present; the rest of that suffix
is not read or validated. There is no charge, pt, rapidity, leading-jet, or
collision-level selection beyond the declared input domain.

## FastJet definitions

Dependency: the local FastJet install in `author/fastjet/include` and
`author/fastjet/lib` (inspected version 3.4.3). Only the core `fastjet` library is
required. The C++17 adapter can be linked with `-Iauthor/fastjet/include
-Lauthor/fastjet/lib -lfastjet` (library after the source/object); no Pythia
headers or libraries are needed.

All supplied constituents are reclustered together using the selected radius,
`fastjet::E_scheme`, and the default FastJet strategy. All
`inclusive_jets(0.0)` are retained. There is no exclusive multiplicity, dcut,
subjet-pt threshold, or selection of only the hardest resulting subjet.
Recombination adds the full four-vectors; it does not reset merged masses to zero
or use winner-take-all axes. Ties follow this FastJet implementation and input
order; a separate, invented tie-breaking clustering rule is not part of the
contract.

Let the algorithm exponent p be 0 for `ca`, +1 for `kt`, and -1 for `antikt`:

| Geometry | ca | kt | antikt |
| --- | --- | --- | --- |
| pp | `cambridge_algorithm` | `kt_algorithm` | `antikt_algorithm` |
| ee | `ee_genkt_algorithm`, p=0 | `ee_genkt_algorithm`, p=1 | `ee_genkt_algorithm`, p=-1 |

The actual distance and inclusive finalization conventions are

```text
pp: dij = min(pt_i^(2p), pt_j^(2p)) * DeltaR_ij^2 / radius^2
    diB = pt_i^(2p)
    DeltaR_ij^2 = (y_i-y_j)^2 + wrapped(phi_i-phi_j)^2

ee: dij = min(E_i^(2p), E_j^(2p)) * (1-cos(theta_ij)) / (1-cos(radius))
    diB = E_i^(2p)
    theta_ij = angle between the three-momenta, in radians.
```

The ee `diB` is an inclusive jet-finalization distance, not a physical incoming
beam. The allowed radius never exceeds pi, so FastJet's different continuation
for radius > pi is irrelevant. In particular, ee `kt` is the **finite-radius
spherical generalized-kt** algorithm, not the exclusive Durham
`ee_kt_algorithm`; ee `ca` is not the Cambridge plugin with soft freezing. These
three spherical choices are already present in the upstream mapping, not new
algorithms introduced by this adapter. Their implementation is also explicit in
`author/fastjet-3.4.3/src/ClusterSequence.cc:278` and
`author/fastjet-3.4.3/src/ClusterSequence_N2.cc:54`.

## Physical observable and normalization

For each original jet J, define the original scalar denominator and the
post-recombination subjet fraction:

```text
pp: W_J = sum_original_particles pt_a; z_i = pt(P_i) / W_J
ee: W_J = sum_original_particles E_a;  z_i = E(P_i) / W_J.
```

`P_i` is a recombined subjet four-vector. In pp, `pt(P_i)` is the magnitude of
the vector sum of transverse momenta, not the sum of their magnitudes. Neither
the parent jet's vector pt nor a sum over the final subjet scalar weights replaces
`W_J`. The exponent is applied **after merging**: the ordered-pair weight is
`(z_i*z_j)^kappa`, not a sum of powered constituent weights.

The ordered-pair coordinate X is:

- `mass`, i != j: `sqrt((P_i+P_j)^2)`, the physical invariant mass in GeV,
  including both subjet masses. It is not mass squared, a massless-subjet
  approximation, or mass divided by parent energy, pt, or radius.
- `mass`, i == j: `sqrt(P_i^2)`, the individual subjet mass, exactly the
  upstream contact convention. In particular, it is **not** `sqrt((2P_i)^2)`
  and is not forced to zero. E-scheme mass contacts can populate finite bins.
- `angular` in pp, i != j: `DeltaR_ij` of the recombined axes, with azimuth
  wrapped to the shortest separation. It is not divided by the subjet radius.
- `angular` in ee, i != j: `theta_ij` in radians, not theta squared,
  `1-cos(theta)`, or `(1-cos(theta))/2`.
- `angular`, i == j: exactly zero, with weight `z_i^(2*kappa)`.

For bin B the output is the bin-integrated measure

```text
H_B = (1/nevents) sum_J sum_(i,j in subjets(J)) (z_i*z_j)^kappa * 1[X_ij in B].
```

The sum includes every ordered pair and each diagonal once. Equivalently, each
distinct unordered pair contributes twice and each contact once. There is no
factor 1/2, division by subjet multiplicity, cross-section factor, bin-width
division, or subsequent unit-area normalization. All jets, including single
subjets, enter the denominator of the average.

With both flow bins included, `sum_B H_B` equals the jet average of
`(sum_i z_i^kappa)^2`. At kappa=1 this is one in ee, up to roundoff. In pp it can
be smaller than one because E-scheme does not conserve scalar pt. For general
kappa it need not be one. A single massive subjet contributes a mass contact,
not an empty mass histogram.

## Histogram and output

Because this CLI has no `log_max`, the adapter fixes the upper finite edge U to
**10000 GeV for mass** and **pi for angular** (DeltaR in pp, radians in ee).
These are explicit presentation choices, not claimed upstream defaults or
physical cuts. In particular, pp separations greater than pi are allowed and
retained in overflow; the ee back-to-back endpoint pi also belongs to overflow.

`bins` counts **all** output entries, including underflow and overflow. Write
F = bins - 2 and L = log10(U). The finite edges are

```text
t_k = 10^(log_min + (L-log_min)*k/F),  k = 0,...,F; t_F = U exactly.
entry 0:          0 <= X < t_0
entry k+1:        t_k <= X < t_(k+1),  k = 0,...,F-1
entry bins-1:     U <= X.
```

Thus log_min is log10 of mass measured in GeV or of the angular coordinate in
the stated convention. Zero contacts always enter underflow; underflow is not
a contact-only bin and can include small positive coordinates. Nothing is
dropped, including overflow, and no logarithm of a zero coordinate is needed.
Exact representable edge equality goes to the bin on its right. Computed
double-precision edges must be strictly increasing.

Output is exactly one newline-terminated row of `bins` whitespace-separated
double values, ordered from underflow through finite bins to overflow, with
scientific notation and 17 digits after the decimal point. It has no metadata,
edges, labels, timings, or FastJet banner. It is an average of integrated EWOC
weights, **not** `dSigma/dX` or `dSigma/dlog10(X)`.

## Bounded domain and explicit deviations

The private reference admits 1 <= nevents <= 100000, 3 <= bins <= 65536,
1e-6 <= radius <= pi, 0 < kappa <= 8, and -12 <= log_min < log10(U).
Every row has either pt=0 or 1e-12 <= pt <= 1e9 GeV, |rapidity| <= 10,
and finite phi. Limits are 4096 rows per jet (including zero-pt rows), 10000000
rows in evaluated jets, 20000000 consumed lines including comments/lookahead,
and 4096 bytes per line excluding its newline. Across the evaluated jets,
`sum_J n_subjets(J)^2` must not exceed 50000000. These are resource/numerical
guards for a bounded control, not claims of new physical difficulty or new
upstream restrictions. Radius zero and the collinear-unsafe particle-level
mass limit are outside this contract.

All kinematics, weights, and histogram accumulation use double precision.
For physical timelike mass sums, negative computed mass squared down to
`-64*epsilon*E^2` is clipped to zero; more negative or non-finite values fail.
Positive mass squared is not rounded to zero, so a nominally massless input can
have a tiny positive numerical contact mass. Opening-angle cosines are clamped
to [-1,1] against roundoff. An ee angular subjet with exactly zero spatial
momentum is rejected rather than assigned an arbitrary axis. Zero-weight pp
contributions are omitted without defining an angular axis for a zero-pt
subjet. Values extremely close to bin edges or clustering ties remain sensitive
to floating-point rounding; bitwise agreement across FastJet/compiler versions
is not promised.

Relative to the paper's winner-take-all studies and the source defaults, fixed
**E-scheme** is a requested, source-supported variant; in particular it changes
subjet axes, scalar-pt sums, and mass contact positions. The flattened format,
fixed upper edges, bin-integral rather than density output, strict prefix reader,
numerical guards, and resource bounds are adapter-specific interface choices.
They must not be presented as verbatim upstream defaults. The contact and pair
weights and the six algorithm/geometry mappings are source-backed, not
extensions. The paper's schematic normalized sum must not override the actual
source scalar denominator when using E-scheme in pp.

Success exits zero. Invalid input, missing jets, unsupported options, exceeded
bounds, FastJet errors, or I/O errors exit nonzero with a diagnostic on stderr;
there is no fallback algorithm, partial-prefix average, or skipped failed jet.
Input and output must not name the same file, including existing hard-link or
symlink aliases. Output is opened only after successful evaluation, so validation
failures do not truncate an existing result. A write failure can leave a partial
output, which must be ignored when the exit status is nonzero.
