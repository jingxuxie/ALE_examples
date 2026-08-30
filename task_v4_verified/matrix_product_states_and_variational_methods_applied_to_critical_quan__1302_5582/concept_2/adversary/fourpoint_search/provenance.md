# Four-spin generation sidecar provenance

Date: 2026-08-28. Only this directory is written. The only attempt artifact read
is the explicitly authorized `concept_2/attempts/v_3/state.npz`. No attempt
source, logs, or other attempt files are accessed. Current participant targets,
the trusted evaluator, and the earlier private portfolios are not modified.

## Independently inspected primary sources

- G. B. Mbeng, A. Russomanno, G. E. Santoro, *The quantum Ising chain for
  beginners*, SciPost Physics Lecture Notes 82 (2024), Section 8:
  https://arxiv.org/html/2009.09208v2
  https://doi.org/10.21468/SciPostPhysLectNotes.82
  Equations 295–303 develop the X-spin Jordan–Wigner strings, the alternating
  Majorana contractions, and the Wick determinant construction. Equation 294
  gives the connected zz target in the Pauli convention used here.
- Yizhuang Liu, *Spin-operator form factors of the critical Ising chain and
  their finite volume scaling limits*, arXiv:2601.00751v4:
  https://arxiv.org/html/2601.00751v4
  Sections 1–2 discuss the finite-chain NS/R sectors and the critical
  near-Cauchy structure. This paper uses different Hamiltonian prefactors and
  field signs; its energy normalization is not imported into our checker.

## Normalization audit independent of fermion formulas

`search.py` builds the full 2^N by 2^N periodic spin Hamiltonian directly with
Pauli bit flips, H = -sum XX -sum Z, at N=6,8,10,12. It finds the lowest state
without restricting parity, checks the eigen-residual and parity expectation,
and compares every four-site combination with the finite sine determinant.
Thus sign and normalization are checked against spin ED, rather than only
against another implementation of the same fermion identity.

For ordered a<b<c<d, the row set is [a+1,b] union [c+1,d] and the column set
is [a,b-1] union [c,d-1]. The infinite matrix is
1/[pi*(row-column-1/2)], equivalent to 2/[pi*(2*(row-column)-1)].
For an even periodic chain of N sites in its NS ground state, the matrix is
1/[N*sin(pi*(row-column-1/2)/N)]. Results are in `validation_ed.json`.

## Stable composite covariance

For interval lengths left=b-a, right=d-c and gap=c-b, the Cauchy determinant
factorizes into the product of the two exact pair correlations times exp(S),
where S is the sum over cross-interval site separations delta of
-log1p(-1/(4*delta^2)). The exact covariance is pair_product*expm1(S), avoiding
subtraction of almost equal determinants. Long-double prefix sums accelerate
the broad scan. Selected candidates are rechecked by independent 70-digit
direct sums and explicit dense infinite determinants are audited separately.

The submitted-state covariance subtracts that state's own pair means, not the
exact means. Centered transfer environments avoid numerical cancellation.
The batch scan's parity-even contractions are checked against uncompressed
sequential tensor contractions for selected candidates.

All scanned quartets have total span <=1024, already within the existing xx
range. Reports separately constrain the gap to <=128 or <=256 and total span
to <=64,128,256,512. This distinguishes a new composite-operator failure from
merely pushing the same two-point test to larger distances. Covariances below
1e-6 are excluded from the default ranking, and actual target magnitudes and
all six constituent pair errors are retained.
