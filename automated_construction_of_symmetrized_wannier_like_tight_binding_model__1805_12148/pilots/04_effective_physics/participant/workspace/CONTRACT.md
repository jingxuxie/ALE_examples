# Interface

Input is a NumPy NPZ archive, loaded with `allow_pickle=False`.

| Key | Shape | Meaning |
|---|---|---|
| `energy` | `(n,)` | Full-space band energies in eV, in the supplied eigenbasis. |
| `momentum` | `(3,n,n)` | Hermitian generalized momentum matrices in atomic units, including spin-orbit terms. |
| `spin` | `(3,d,d)` | Pauli-spin matrices projected onto the selected bands, not bare abstract Pauli matrices. |
| `target` | `(d,)` | Zero-based full-space band indices, in the order used by spin and representations. |
| `dft_repr` | `(g,d,d)` | Numerical unitary parts of symmetry corepresentations in the selected input basis. |
| `standard_repr` | `(g,d,d)` | Desired unitary parts of the same generators. |
| `antiunitary` | `(g,)` | Whether a generator includes complex conjugation. |
| `cart_rotation` | `(g,3,3)` | Spatial part of each generator; an antiunitary generator also reverses momentum. |
| `order` | scalar integer | Requested expansion order, either 2 or 3. |

Return a complex-valued NPZ containing `U`, `H0`, `H1`, `H2`, `H3`, `G`:

- `U` has shape `(d,d)` and maps standard-basis coordinates into input-basis coordinates. It is unitary and satisfies `D_input @ U = U @ D_standard` for unitary generators and `D_input @ U.conj() = U @ D_standard` for antiunitary generators. Numerical representation noise is expected. No particular residual gauge or overall phase is preferred.
- `H0`, `H1`, `H2`, `H3` have shapes `(d,d)`, `(d,d,3)`, `(d,d,3,3)`, `(d,d,3,3,3)`. They are the standard-basis tensors of the canonical Hermitian Löwdin effective Hamiltonian for the selected subspace. Use the near-identity block-unitary convention whose diagonal blocks are Hermitian, not an energy-dependent Schur complement. Cartesian derivative indices in `H2` and `H3` are fully symmetric. For order 2 return an all-zero `H3`.
- With Cartesian `q` in inverse Angstrom, the effective Hamiltonian is `H0 + sum_a H1[...,a]*q[a] + sum_ab H2[...,a,b]*q[a]*q[b] + sum_abc H3[...,a,b,c]*q[a]*q[b]*q[c]`. These are coefficients, not raw derivatives: there are no extra factorials. Both diagonal and mixed Cartesian tensor entries are returned, not only independent monomials.
- The full-space unperturbed problem is `diag(energy)`; its linear term is `(2*c/bohr) * sum_a momentum[a]*q[a]`, and its quadratic term is `c*dot(q,q)*I`, where `c=3.809982208629016` eV Angstrom squared and `bohr=0.52917721067` Angstrom. Do not truncate the remote space or insert empirical fits.
- `G` has shape `(d,d,3)` and is defined by `H_Z = mu_B * sum_a G[...,a]*B[a]`. Include both the projected spin and the orbital contribution from virtual transitions, consistently with the same Hermitian Löwdin reduction to second order in momentum. The electron convention uses the covariant-wavevector commutator `[q_a,q_b] = -i*(mu_B/c)*epsilon_abc*B_c`. This fixes the sign and normalization without an electron-charge ambiguity.

All matrix tensors are in the returned standard basis. Individual tensor comparisons allow any admissible residual gauge by using the submitted `U`; matching a single privileged basis choice is not required. Basis admissibility, quadratic corrections, cubic corrections and Zeeman response each contribute to the core score; zeroth/first-order export, Hermiticity and consistency are checked too. The raw numerical tensors are requested, without additionally projecting away the small symmetry violations in the electronic-structure data. Full datasets have 600–800 bands and target dimensions 2–4. A target may contain several distinct energies; denominators within the retained space are not remote-band denominators.

`input/smoke.npz` is an unlabeled real-data smoke input. Running the legacy exporter checks the file interface, not scientific correctness. Hidden materials and raw reference outputs are intentionally not supplied.
