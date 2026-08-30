# Simulator audit notes

The sign and kick order follow arXiv:2306.14887v3, equation (1), specialized to
the isolated 12-site cycle, not the full 127-site Eagle graph. The observable
`zz1` equals `1 - 2*rho`, where `rho` is the domain-wall density over edges.

`entangle_ring` uses `exp(i*pi*ZZ/4) = (I + i*ZZ)/sqrt(2)` exactly. Each chain
edge gets a bond-two expansion. The closing edge propagates a two-valued
identity/Z channel through block-diagonal middle tensors. Thus intermediate
bonds are at most four times the previous cap. No swaps are approximated.

`compress` first right-canonicalizes without truncation. Each subsequent SVD
is therefore a genuine Schmidt projection in the physical norm. The kept
dimension is at most `chi` and numerically zero singular values are removed
below `1e-13` relative to the largest value. A discarded fraction is the sum of
discarded squared singular values divided by the full sum at that cut.
Fractions are summed for diagnostics; that sum is not asserted to be a final
observable-error bound. Large values explicitly warn against interpreting the
convergence heuristic as a rigorous accuracy certificate.

At degeneracies within `1e-11` of the leading singular value, select a basis
from the subspace projector by maximum-residual-diagonal coordinate pivots,
breaking diagonal ties within `1e-10` by smallest coordinate. This is applied
to fully retained degenerate groups too, fixing the preceding left-bond gauge.
Two Gram-Schmidt passes orthogonalize each selected vector. Transfer tensors
are projections of the original matrix, rather than fabricated singular data.
This prevents a witness from exploiting an arbitrary LAPACK choice of basis.

Evolution uses only MPS tensors. Expanding the final 12-site MPS for measurement
is exact contraction, not a statevector shortcut during approximate evolution.
The maximum exact Schmidt rank is 64, so chi=64 must reproduce the full state.
The generation audit also compares a separate bit-pair oracle, dense Hamiltonian
exponentials on four sites, transfer-matrix observables, and two SVD drivers.

The paper discusses uncontrolled BP error even as bond dimension increases
(Figure 4 caption and Methods). Its high-bond MPS cross-checks also monitor
truncation error. Our low-bond, layer-compressed MPS and spread-only heuristic
are supplied benchmark algorithms, not a reimplementation of that paper's
BP-TNS or optimized MPS code. A successful witness refutes only the implication
"these three estimates nearly agree, therefore their error is small."
