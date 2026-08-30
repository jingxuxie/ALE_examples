# Private numerical provenance

The task is motivated by the OpenFermion paper's Hubbard-model numerical
simulation and reduced-density-matrix setting. Labels here come from the
explicit number-conserving Hubbard Hamiltonian specified in the public schema,
not from OpenFermion software, a fitted model, or the provided champion engine.

`exact.py` constructs signed spin hopping matrices in combination-ordered
occupation bases. `native_reference.py` combines their actions with a double
precision native tensor-product matvec and uses SciPy's symmetric ARPACK solver
with random initial vectors, `which="SA"`, tolerance `1e-10`, and `ncv=16`.
Any rejected residual triggers a `2e-11`, `ncv=32` retry. All four unrounded sector
energies, residuals, timings, iteration counts, and retry counts are retained in
the private `*_source.npz` files. Accepted residual norm is at most `2e-8`.
The spin label is the fixed-Sz-sector difference, without an S-squared claim or
clipping. Physical parameter draws are identical in all three splits; the
private seed is independent entropy and public samplers reveal no test IDs.

`validate_source.py` checks full-Fock tiny matrices, analytic dimer and atomic
limits, free fermions, site permutations, potential shifts, eigensolver
restarts, and RDM energy/trace/Hellmann–Feynman identities. `verify_generation.py`
replays the sampler, checks padding and every saved residual, rejects duplicate
Hamiltonians, and recomputes eight stratified validation examples with new
random starts, permuted sites, tighter tolerance, and larger Krylov spaces.
One 12-site result is checked against explicit full-CSR Hamiltonian actions in
all four sectors, and a 10-site result against an independent full-CSR solve.

The supplied final native baseline is a separate, hashed engine. Its eigenvalues
are never used as training or hidden labels. A successful small quality run and
a failed full-size guarded run must be distinguished: only the latter tests the
256-case resource requirement. Source generation is privileged offline work;
participant training and inference have the separate disclosed resource caps.
