# Physical families and numerical contract

All matrices are Hermitian one-body matrices in one spin sector. The four fixed
checkerboard components contain disjoint nearest-neighbor bonds on even
periodic square lattices. Different hopping components generally do not
commute. `V` is onsite and diagonal. Bond phases are quenched Peierls phases;
the reverse bond is the complex conjugate. There is no matrix rescaling.

`spec.json` defines all numerical sampling laws. The first four families use
the stated independent binary or clipped-normal onsite fields. Each has a
`uniform_...` counterpart with **the same hopping law**, independently sampled,
and `V=(s*A-mu)I`: one equiprobable sign `s=+/-1`, strength `A~U[.5,6]`, and
chemical potential `mu~U[-.4,.4]` per instance. All sites share that value;
there is no stagger or site noise in these four uniform families.

For `anisotropic_dimer` and its uniform counterpart, first draw `tx`, set
`ty=tx*U[ty_ratio]`, and swap the two hopping scales with probability 1/2.
Dimerizations are independent draws and are not swapped. A horizontal bond
has the factor `1+dx*(-1)^x`, and a vertical bond `1+dy*(-1)^y`, followed by its
independent bond-disorder multiplier. Weak-isotropic hopping scales are equal.
All other ranges and the oriented-bond matrix convention are in the contract.

All onsite potentials are **frozen effective HS-like fields**, held fixed as
`h` changes; no square-root-in-`h` HS scaling or integration over interacting
fields is performed. The uniform sectors commute with hopping, but the same
universal five-component schedule, normalization and 33-stage resource cost
apply. No instance-dependent removal of stages or special-case witness is
permitted. The cost is one abstract local layer sweep per stage, with no
across-macrostep fusion credit for either candidate or baseline.

Development and held-out suites use independent draws from all eight public
laws. Each family has six public and twelve private instances, balanced over
the three shapes. Every instance contributes sixteen points: four steps times
two repetition counts times two observables. Family RMS ratio scores are
equally weighted across families; a single ratio above one also prevents a
pass. Seeds and held-out matrices are private, not the physical laws or gates.

## Product and stable Green functions

First validate the submitted coefficients and their tolerances. Then replace
each reflected pair by its arithmetic mean, leaving the central coefficient
unchanged. This preserves each component's submitted total time and gives an
exact palindrome; do not renormalize component totals. This canonical schedule
is used for **all** numerical comparisons.

Write its stages as `E_j=exp(-h*a_j*H[c_j])`. Its mathematical product is
`P=E_0 ... E_32`, in written order. Equivalently,
`L=E_0 ... E_15 exp(-h*a_16*H[c_16]/2)` gives `P=L L^H`.
The checker independently forms these exponentials. An SVD of L gives the
eigenvectors of P and eigenvalues `sigma^2`. It evaluates candidate
`G=(I+P^r)^(-1)` with the Fermi function of `2*r*log(sigma)`, and exact G with
the eigenvalues of H. It does not use an unstable direct inverse at large
steps. Propagators are compared to the exact exponential of `-r*h*sum(H)`.
This is a stable evaluation of the same stated observables, not a substitute
objective or an asymptotic order condition. All targets and tolerances are
specified exactly in `spec.json`.
