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

Query fields: `order`, `log_min`, `bins`, `ratio_bins`, `phi_bins`, `nu1`, `nu2`, and `nu3` for order 4. Omitted nu fields default to 1.
The following radial-bin convention overrides the common default.
# Joint resolved energy correlators

`executable events_file nevents order log_min bins ratio_bins phi_bins output_file [nu1 nu2 [nu3]]`

Omitting the trailing exponents preserves the unit-weight mode. Otherwise supply exactly two exponents for order 3 or three for order 4, all finite and strictly positive, with representable finite `1 + sum(nu)`. These are cumulative finite-difference exponents, not independent powers of the constituent weights.

Input rows are `event_id pt rapidity phi`, one massless constituent per row. Each contiguous event is one already-selected jet; nonnegative integer event IDs increase between jets. Blank lines are allowed. Process exactly the first `nevents` complete jets, including the final group at EOF; fewer jets is an error. Momenta are finite and nonnegative, each jet has positive total transverse momentum, and angles are in radians. No clustering, constituent cuts, or multiplicity truncation is performed. `nevents`, `ratio_bins`, and `phi_bins` are positive integers; `order` is 3 or 4; `bins >= 3`; `log_min < 0` is finite with representable positive `10^log_min`.

## Observable

For each jet, define `z_i = pt_i / sum_j pt_j`. Designate one constituent `s` as the special particle and define vectors `v_i = (y_i-y_s, wrap(phi_i-phi_s))` and radii `R_i = |v_i|`. `wrap` takes values in `(-pi, pi]`. Order non-special indices by increasing radius, breaking exact ties by input-row order; the later-ranked index occupies the outer slot. Repeated indices remain the same constituent, not independent copies of its momentum.

The signed angle `angle(v_a,v_b)` is `wrap(atan2(det(v_a,v_b), dot(v_a,v_b)))`, or zero when either vector vanishes. The joint coordinates are:

- Order 3: `(R_1, R_2/R_1, angle(v_1,v_2))`, with `R_1 >= R_2`.
- Order 4: `(R_1, R_2/R_1, angle(v_1,v_2), R_3/R_2, angle(v_2,v_3))`, with `R_1 >= R_2 >= R_3`. The last azimuth is recursive, not measured from `v_1`.

With all exponents one, the per-jet histogram is the weighted sum over labeled choices of the special particle and the remaining indices, with weight `z_s * product(z_i)`, at their radially ordered coordinates. Thus each distinct non-special pair or triple has multiplicity 2 or 6. Zero denominators in ratios give zero except for the explicit repeated-index contact convention below.

**Order 3 includes contacts.** At unit exponents, for each `s`, the all-equal choice contributes `z_s^3` at `(0,0,0)`. For every `a != s`, choices with one remaining index equal to `s` contribute `2*z_s^2*z_a` at `(R_a,0,0)`, and the repeated choice `(a,a)` contributes `z_s*z_a^2` at `(R_a,1,0)`. The remaining choices use three distinct indices. Its total bin mass is one per jet at unit exponents, up to floating-point error.

**Order 4 excludes all contacts:** the special particle and all three remaining indices must be pairwise distinct. This intentionally matches the available four-particle implementation, which rejects contact terms; it is not the inclusive four-point observable. At unit exponents its total bin mass is `24 * sum_{i<j<k<l} z_i*z_j*z_k*z_l`, not one. It is zero for fewer than four constituents at any supported exponents. Do not renormalize it to unit area. Equal-radius ties and coincident distinct constituents use the deterministic convention above rather than an unspecified sorting order.

## Generalized source-defined weights

Define `D_nu(S,z) = (S+z)^nu - S^nu`, interpreted as a mathematical finite difference (stable evaluation is allowed). For fixed `s`, let `j > k > ell` denote distinct non-special ranks in the ascending radial order, and let `p(j,k)` be the ordinary azimuth bin of `angle(v_j,v_k)`. Denote the zero-azimuth bin by `p0`. The relevant prefixes, all excluding the current rank, are:

- `A_j = z_s + sum_{r<j} z_r`.
- `B_jk(p) = z_s * 1[p=p0] + sum_{r<k, p(j,r)=p} z_r`.
- `C_kell(q) = z_s * 1[q=p0] + sum_{r<ell, p(k,r)=q} z_r`.

At the same geometric cells as before, each `(s,j,k)` contributes `2*z_s*D_nu1(A_j,z_j)*D_nu2(B_jk(p(j,k)),z_k)`. Each `(s,j,k,ell)` contributes `6*z_s*D_nu1(A_j,z_j)*D_nu2(B_jk(p(j,k)),z_k)*D_nu3(C_kell(p(k,ell)),z_ell)`. The second and third prefixes are phi-local, not ratio-local; the third uses the recursive azimuth. Prefixes include earlier constituents even if those constituents cannot yet form a complete distinct tuple.

Order-3 contact contributions are, literally: `z_s^(1+nu1+nu2)` at `(0,0,0)`; `2*z_s^(1+nu2)*z_a^nu1` at `(R_a,0,0)`; and `z_s*z_a^(nu1+nu2)` at `(R_a,1,0)` for every `a != s`. Order 4 still has no contact contributions.

**Semantic limitation:** non-unit weights reproduce the source program's binned statistic, not a verified normalized inclusive continuation to `N=1+sum(nu)`. In particular, two constituents with `z=1/2` and `(nu1,nu2)=(2,1)` have total weight `1/2`, not one. The non-unit phi-local prescription can depend on azimuth binning, so a finer histogram need not reduce to a separately evaluated coarser one. Do not impose unit-normalization or unit-weight marginal identities, or replace the source contacts with an invented completion. Naive subtraction of two nearly equal powers can lose precision; this does not change the specified finite-difference formula.

## Bins and output

The radial axis has `bins` cells: cell 0 is `0 <= R_1 < 10^log_min`; cells 1 through `bins-2` partition `log10(R_1)` uniformly from `log_min` to 0; cell `bins-1` contains `R_1 >= 1`. Each ratio has `ratio_bins` uniform cells on `[0,1]`; each azimuth has `phi_bins` uniform cells on `[-pi,pi]`. Cells are left-closed/right-open, except the final ratio/azimuth cell includes its upper endpoint. Contacts at zero azimuth use the ordinary bin containing zero. There are no separate ratio or azimuth flow cells.

Output is the arithmetic mean over the requested jets: **bin masses, not densities divided by bin widths**, one scientific-notation number per line, with no header. Shapes and row-major flat indices are:

- Order 3: `[bins, ratio_bins, phi_bins]`, index `(b1*ratio_bins+b2)*phi_bins+p2`.
- Order 4: `[bins, ratio_bins, phi_bins, ratio_bins, phi_bins]`, index `(((b1*ratio_bins+b2)*phi_bins+p2)*ratio_bins+b3)*phi_bins+p3`.

Summing trailing axes gives the corresponding projected **same-definition** bin masses. An inclusive three-point projection does not equal a contact-free four-point marginal, and the special-particle maximum radius is not the traditional maximum pairwise separation.
