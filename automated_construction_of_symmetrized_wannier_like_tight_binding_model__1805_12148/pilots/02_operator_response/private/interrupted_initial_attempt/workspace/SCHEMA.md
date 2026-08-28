# Input and output contract

Each case directory contains `case.json` and `model.npz`. Read numerical arrays
without pickle. Lengths are angstroms, energies are eV, and reciprocal query points
are reduced coordinates, with no factor of 2 pi incorporated into those points.
All orbitals, real-space vectors, and matrix elements must be retained.

## Model

- `lattice[3,3]`: lattice vectors as Cartesian **rows**.
- `rvec[nr,3]`: integer lattice translations, no omitted degeneracy weights.
- `ham[nr,nw,nw]`: complex `<n,0|H|m,R>`.
- `centers[nw,3]`: Cartesian Wannier centers in the given orbital order.
- `connection[nr,nw,nw,3]`: complex center-subtracted position matrix,
  `<n,0|r|m,R> - delta(R,0) delta(n,m) centers[m]`.
- `query_points[nq,3]`: points at which to evaluate both original and repaired models.

The Bloch embedding uses `exp(2 pi i k.(R + center_m_red - center_n_red))`.
Use the same embedding for H and the center-subtracted connection; derivatives
for the requested observables are with respect to Cartesian wavevector, in
inverse angstroms. Do not drop the off-diagonal or intercell position elements.

The stored position coefficients are taken as supplied and need not satisfy
an exact adjoint relation between R and -R. Preserve this coefficient-level
information during symmetry projection. For **observables**, use the Hermitian
part `(M(k) + M(k).conj().T)/2` of each Fourier-transformed Hamiltonian and
position-connection component, and differentiate that convention consistently.
Do not silently Hermitize the requested real-space output coefficients instead.

## Symmetry data

All operations, including identity, are explicitly supplied. At operation `g`:

- `fractional_rotations[g,3,3]` acts on reduced **column** vectors.
- `cartesian_rotations[g,3,3]` acts on Cartesian **column** vectors and includes inversion when present.
- `translations[g,3]` is the fractional spatial translation.
- `antiunitary[g]` indicates antiunitarity.
- `unitary[g,nw,nw]` is the unitary part of the orbital action, including spin and
  the permutation of orbitals/sites. Its rows are output orbitals and columns
  are input orbitals. The antiunitary flag is not already absorbed as conjugation.
- `orbital_shifts[g,nw,3]` gives the integer cell shift for each source orbital.

Precisely, the action on a localized ket is
`g |n,R> = sum_j unitary[g,j,n] |j, S_g R + orbital_shifts[g,n]>`;
coefficients of a state are conjugated for an antiunitary operation. Position
is a polar, time-reversal-even vector, not a scalar copy of H. Apply the group
projection to the operators and transform/average centers consistently. Expand
the real-space support as needed; missing terms are zero, not a reason to omit
symmetry-related images. No orbital reshuffling is allowed in the result.

`case.json` records the material, orbital ordering, native-to-displayed ordering,
and passive orthogonal Cartesian frame. The supplied arrays already use the
displayed frame and order. These metadata are provenance, not extra transformations
to apply to them. Internal orbital-basis matrices remain in their declared basis
under a passive Cartesian frame change.

## Observables

`occupied` in `case.json` specifies the lowest-band subspace I at every query
point; J is its complement in the complete supplied model. In a metal this is
a specified spectral-subspace diagnostic, not an assumption of a global gap or
a fixed physical Fermi occupation. Sum over the whole requested subspace.

- `energies[nq,nw]`: ascending energies of the **original** model.
- `berry_raw[nq,3]`: trace over I of the original-model Berry curvature, ordered
  `(Omega_yz, Omega_zx, Omega_xy)`, in angstrom squared. The sign convention is
  `A_n = i <u_n|grad_k u_n>` and `Omega_n = curl_k A_n`.
- `optical_raw[nq,3,3]`: the full complex interband Kubo numerator
  `Q_ab = i sum_(n in I,m in J) A^H_nm,a A^H_mn,b`, in angstrom squared.
  `A^H` is the Berry connection in the Hamiltonian eigenbasis, including the
  supplied position connection and the derivative of the eigenbasis.
  Q is a transition kernel **before** frequency, occupation, and SI prefactors,
  not an integrated optical conductivity.
- `berry_repaired`, `optical_repaired`: the same quantities for the completely
  repaired H/connection/center model, with the same band count and query points.

The original-model response is independent of whether operator repair succeeds.
The post-repair quantities test their integration. Arbitrary phases or rotations
within a completely included degenerate subspace must not change the reported
traces/kernels. Do not replace the physical position connection with orbital
centers or the Hamiltonian derivative alone.

## Result NPZ

Return `rvec`, `ham`, `connection`, `centers`, and all five observable arrays named
above (`energies` plus the four response arrays; the original and repaired model
operators share the single repaired model payload). `ham`, `connection`, `centers`
are repaired outputs; `lattice` need not be returned because it is unchanged.
The R rows may be in any order but must be unique integers. Extra exactly zero
R rows are allowed. Keep complex arrays complex. NaN, infinity, duplicate R rows,
incorrect shapes, or missing fields lose their corresponding credit.

Evaluation compares operator coefficients in this fixed orbital gauge as well
as response tensors. It gives continuous credit calibrated against the supplied
Hamiltonian-only workflow. Matching only eigenvalues or returning zero Berry
curvature does not complete the mission.
