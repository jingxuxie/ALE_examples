# Observable definitions

The lattice spacing and couplings are one. Pauli matrices have eigenvalues +1 and -1, not spin-one-half normalization. The infinite-chain exact vacuum has energy density `-4/pi` and `<sigma_z>=2/pi`.

For an integer separation `r>=1`, the order correlation is the determinant of the `r` by `r` matrix with entries

`M[row,col] = 2 / (pi * (2*(row-col)+1))`, with zero-based row and column indices.

The connected density correlation is `4/(pi*pi*(4*r*r-1))`. The disconnected contribution is subtracted using the submitted state's own `<sigma_z>`, not the exact value. The supplied checker computes these definitions. They specify the scientific targets, not a construction of an MPS.

For a right-canonical tensor, one-site expectations are `trace(rho E_O(I))`, where `E_O(X)=sum_(s,t) O[t,s] A[s] X A[t]^dagger`. Two-site expectations are `trace(rho E_O(E^(r-1)(E_O(I))))`.

Paper context: Milsted, Haegeman and Osborne, arXiv:1302.5582, Sections II–III on uMPS and finite entanglement. Exact Ising calibration: Pfeuty, Annals of Physics 57, 79–90 (1970), DOI 10.1016/0003-4916(70)90270-8. These targets are infinite-chain quantities; there is no finite-size extrapolation in the checker.
