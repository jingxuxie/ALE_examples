# Solution

`solve.py INPUT.npz OUTPUT.npz` fits both force-constant orders using NumPy and SciPy.

## Implemented
- Orthonormal sparse tensor bases built from compact translation maps, simultaneous atom/Cartesian permutations, and the supplied Cartesian crystal operations.
- Acoustic sum rules imposed through a constraint nullspace; cubic support enforced while constructing the basis, rather than by masking an unconstrained fit.
- Equal-weight least squares over every snapshot, atom, and force component. Mode 0 fits both orders jointly; mode 1 fits the large-cell harmonic tensor first, alias-sums it into the cubic cell, and fits the residual cubic forces.
- No intercept or ridge penalty. Well-conditioned full-rank systems use sufficient statistics; ill-conditioned or rank-deficient systems use SVD for the minimum-norm tensor solution.
- Blocked feature construction with inverse compact permutations, without expanding the full cubic tensor.

## Tested
- Public smoke CLI: correct finite float64 output shapes, force RMSE about 0.006548, and symmetry/acoustic residuals below 1e-10.
- `validate.py`: independently constructed constraint subspaces and rank-deficient minimum-norm fits; exact recovery with rotated Cartesian axes, shuffled atom orders, non-self-inverse translations, and different 512/64-atom cells.
- `validate_more.py`: low-symmetry two-species cells and hexagonal nonsymmorphic operations; noisy joint and two-stage fits agree with direct SVD references to below 1e-8 in tensor norm. Noiseless relative recovery errors are below 1e-12.
- A synthetic 512/64-atom CLI stress case with 256 harmonic and 128 cubic snapshots, and a 6-angstrom cubic cutoff, completed in 18.11 seconds with 574800 KiB peak memory. Output acoustic residuals were below 3e-14.

Only the public smoke data and locally generated synthetic tests were used; no labeled real-force targets were available.
