# Physical and submission contract

## Circuit

Number sites `0,...,11` around an isolated decorated hexagon. Edge `j` joins
`j` to `(j+1) mod 12`. There are no external neighbors. Site 0 is the least
significant computational-basis bit. The kick groups are
`A={0,1,3,6,8,11}` and `B={2,4,5,7,9,10}`.

For zero-based layer `l=0,...,23`, first apply the six disjoint ZZ gates on
edges with `j mod 2 = l mod 2`, then kick all sites:

```
D_l(s) = product_{j mod 2 = l mod 2}
         exp(+i (pi/4) [1 + c(s) + d_j(s)] Z_j Z_(j+1))
K_l(s) = product_v exp(-i theta[l,g(v)] [1 + e_g(v)(s)] X_v / 2)
|psi_s> = K_23(s) D_23(s) ... K_0(s) D_0(s) |+>^12
F_s = |(<0^12| + <1^12|) psi_s / sqrt(2)|^2
```

All 48 angles are independently bounded by `[-pi,pi]`. Zero-angle rows do
**not** skip the ZZ gates. The ZZ schedule and nominal strength cannot be
changed. Both group kicks may coincide, but their calibration errors need
not. There is no final correction, phase fitting, or optimization over the
GHZ relative phase. Fidelity is the squared overlap with GHZ+, not merely
population in its two computational-basis outcomes.

## Calibration family

The four channels are independent: `e_A,e_B in [-0.025,0.025]`, common
bond error `c in [-0.015,0.015]`, and each residual edge error
`d_j in [-0.005,0.005]`. They are fractional multiplicative errors, not
radians. All are static across the entire pulse sequence. There is no
decoherence or shot noise. Every checker scenario lies in this public family.

The frozen suite has 63 scenarios: 15 core cases (nominal, six single-axis
extrema, eight common-channel corners with zero residuals), 24 worst-family
cases (all common-channel corners combined with uniform endpoint residuals,
matching-staggered residuals, or long-wavelength residuals), and 24 held-out
cases with independent local disorder. The identities of held-out points
are private. The uniform residual stress reaches total common bond gain
errors of +/-2%. A participant may generate any additional family members.
Finite-suite success does not prove worst-case fidelity over a continuum.

Pass requires `min_s F_s >= 0.95`, including each family; averaging cannot
hide a failure. The checker uses independent complex128 gate contractions
with no sampling, tensor truncation, renormalization, or clipping. It checks
norm and global-X parity as internal invariants. There is no score rounding
or tolerance below the fidelity threshold. Global phase is irrelevant.

## Why this generalization is intentional

Equation (1) of Tindall et al., *Efficient tensor network simulation of IBM's
Eagle kicked Ising experiment*, arXiv:2306.14887v3 (2024), uses fixed
`exp(+i*pi*ZZ/4)` gates on all bonds and a global transverse kick. We retain
the native gates and an actual heavy-hex plaquette but allow two calibrated
kick groups and place kicks between the two fixed bond matchings. This is
a control-design variation, not a reproduction of the original experiment.

Simply alternating the full all-bond Clifford layer with any X-only kicks
on this even ring would make this particular GHZ target impossible: the
full layer commutes with `P_A = product_{even v} X_v`, as do X kicks.
Starting in `|+>^12` fixes `P_A=+1`, while GHZ+ has only half its norm in
that sector, bounding fidelity by 1/2. Splitting the matching layers removes
this extra obstruction. Global `product_v X_v` remains conserved by every
perturbed gate, and both the specified input and GHZ+ have its +1 parity.
In particular, substituting `|0>^12` as the input is not permitted.

## JSON and execution

`pulses.json` is a UTF-8 JSON object with exactly `schema_version` (integer
1) and `angles` (24 lists of two finite JSON numbers). Booleans, strings,
nulls, duplicate keys, extra fields, NaN/infinity, out-of-range numbers,
wrong dimensions, symlink artifacts, and files larger than 65536 bytes are
invalid. Only this artifact is read; submitted Python/native code is not run.

The CLI writes `valid`, `passed`, `score`, `core_score`, `worst_family_score`,
`resource_score`, `runtime`, `runtime_seconds`, and a textual `reason` for
both valid and invalid artifacts. Core/worst-family scores are their minimum
fidelities, or zero for invalid artifacts. `resource_score` is 1 for a valid
fixed-size artifact that completes exact checking, otherwise 0; it is not
a timing bonus or an additional fidelity condition. Runtime fields report
checker wall seconds, not participant search time. Valid results also include
`min_fidelity`, `mean_fidelity`, `threshold`, scenario count, family minima,
artifact/scenario hashes, and invariants. A valid artifact returns exit
code 0 even if below target; malformed artifacts return exit code 2 with
`valid=false`, `passed=false`, `score=0`. Trusted checker failures are not
misreported as participant physics failures. Provide a fresh output path,
not the artifact itself. Checker runtime is comfortably below 120 seconds
on a single ordinary CPU core; no participant runtime is used in scoring.
