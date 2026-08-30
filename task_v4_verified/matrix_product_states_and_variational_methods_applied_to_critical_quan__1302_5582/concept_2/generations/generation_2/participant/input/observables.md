# Observable definitions

The lattice spacing and couplings are one. Pauli matrices have eigenvalues +1 and -1, not spin-one-half normalization. The infinite-chain exact vacuum has energy density `-4/pi` and `<sigma_z>=2/pi`.

For an integer separation `r>=1`, the order correlation is the determinant of the `r` by `r` matrix with entries

`M[row,col] = 2 / (pi * (2*(row-col)+1))`, with zero-based row and column indices.

The connected density correlation is `4/(pi*pi*(4*r*r-1))`. The disconnected contribution is subtracted using the submitted state's own `<sigma_z>`, not the exact value. The y-spin correlation is minus the order correlation divided by `(4*r*r-1)`, with `sigma_y=[[0,-i],[i,0]]`. The supplied checker computes these definitions. They specify the scientific targets, not a construction of an MPS.

The determinant can equivalently be evaluated as `(2/pi)^r * product_(j=1..r-1) (1-1/(4*j*j))^(-(r-j))`; the checker uses logarithms of this product at large separation. This is only an exact observable formula, not a formula for an admissible tensor.

For a right-canonical tensor, one-site expectations are `trace(rho E_O(I))`, where `E_O(X)=sum_(s,t) O[t,s] A[s] X A[t]^dagger`. Two-site expectations are `trace(rho E_O(E^(r-1)(E_O(I))))`.

## Composite order-pair fluctuations

For each ordered quartet `a<b<c<d` in `fourpoint_quartets.json`, define

`C4(a,b,c,d) = <X_a X_b X_c X_d> - <X_a X_b><X_c X_d>`.

Here `X` means `sigma_x`. The measured covariance must subtract the submitted
state's own two interval means. The exact target separately subtracts the exact
ground state's two interval means. Subtracting exact means from the submitted
four-point value is not the specified observable. Matching raw `<XXXX>` alone
is not sufficient: every listed covariance must have relative error at most
`0.01`, with the exact covariance as the denominator.

The public list contains exactly the quartets `(0,left,left+gap,left+gap+right)`
for `left,right in {16,32,64,96}`, `gap in {32,64,96,128}`, and total span at most
256, including both interval orderings. There are 60 quartets.

The infinite-chain exact raw four-X expectation is a Cauchy determinant. Its
row sites are the union of the inclusive integer intervals `[a+1,b]` and
`[c+1,d]`; column sites are the union of `[a,b-1]` and `[c,d-1]`. The matrix is

`M[row_site,column_site] = 2 / (pi * (2*(row_site-column_site)-1))`.

Its determinant is the exact raw `<XXXX>` value. Subtract the product of the
exact order correlations at distances `b-a` and `d-c` to obtain the exact C4.
Equivalently, with `P=exact_order(b-a)*exact_order(d-c)` and

`S = -sum_(u=a+1..b, v=c+1..d) log(1 - 1/(4*(v-u)^2))`,

the raw target is `P*exp(S)` and the covariance target is `P*expm1(S)`. The
latter expression avoids cancellation. All 60 exact covariance targets exceed
`0.0003234`. These are exact lattice targets, not continuum approximations.

The submitted raw value is contracted from the tensor as

`trace(rho E_X E^(b-a-1) E_X E^(c-b-1) E_X E^(d-c-1) E_X(I))`,

with map composition read right to left. The checker subtracts the two measured
interval expectations afterward. It does not impose the ground-state Cauchy
identity on the submitted state's two-point functions. Public functions
`exact_four_order`, `exact_composite_covariance` and `composite_observables`
are provided in `workspace/physics.py`.

Paper context: Milsted, Haegeman and Osborne, arXiv:1302.5582, Sections II–III on uMPS and finite entanglement. Exact Ising calibration: Pfeuty, Annals of Physics 57, 79–90 (1970), DOI 10.1016/0003-4916(70)90270-8. These targets are infinite-chain quantities; there is no finite-size extrapolation in the checker.
