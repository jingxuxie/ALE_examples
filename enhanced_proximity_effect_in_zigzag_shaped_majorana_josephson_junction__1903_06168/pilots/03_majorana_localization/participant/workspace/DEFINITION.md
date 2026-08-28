# Contract

INPUT is a directory containing `manifest.json` and NumPy `.npz` files; load with `allow_pickle=False`. OUTPUT is one UTF-8 JSON **file**, not a directory. The program must create its parent if necessary. NumPy and SciPy are installed. No network, private files, Kwant, or symbolic packages are needed at submission runtime. All lengths are nm, all energies meV, all arrays complex128 or float64. These are numerical tight-binding simulations, not measurements. The device length remains 4550 nm; it is not the localization length.

The manifest has `schema_version: 1` and a `cases` list. Each record has unique string `id`, `family`, and relative NPZ `file`. Other fields describe the physical geometry and are not targets. Input filenames and case identifiers have no scientific meaning. Do not train a lookup table. Public inputs are examples, without reference answers. Evaluation includes other parameter settings and basis representations.

## Bulk tail (`bulk_tail`)

The input contains square `onsite` H and `hopping` T matrices, scalar `cell_length_nm` d, and a finite-device witness (`witness_x_nm`, `witness_density`). H is Hermitian. T can be singular. In the supplied representation the infinite periodic system acts as

    (Hamiltonian psi)[j] = T psi[j+1] + H psi[j] + T.conj().T psi[j-1].

At energy zero, consider all nonzero bulk solutions that decay exponentially towards increasing j. Report the **longest finite amplitude decay length** `xi_amplitude_nm`. A solution with envelope norm proportional to exp(-j*d/xi) has amplitude length xi. Discard solutions with strictly finite support; the target concerns the asymptotic tail. The selected cases have no zero-energy propagating modes. This definition is a bulk penetration length; it does not assert that every parameter setting is topological or that every boundary couples to the slowest bulk channel. A local finite-boundary fit is not the target definition.

The cell can contain several original lattice slices. Use the supplied physical d; neither matrix dimension nor orbital count is a length. Cells related by grouping represent the same infinite material. Orbital phase conventions can differ. All transverse orbitals and both superconducting regions are retained.

The witness is the normalized x-projected density of the lowest-positive-energy eigenstate of the 4550 nm open finite device at the **same physical parameters**. It contains 455 original 10 nm lattice slices, even when the bulk input uses grouped cells. The nominal witness is an archived numerical density; other witnesses were recomputed from the same validated tight-binding Hamiltonian. Grouped representations of the same material share a witness. All components in the witness have already been squared and summed: do not square the density again. The bulk matrices, not that finite witness alone, specify the asymptotic problem. The supplied finite-only starter cannot resolve all of these cases.

## Finite end (`finite_end`)

`basis` U has shape (D,6), with orthonormal columns spanning six low-energy states of a finite BdG Hamiltonian. It is not necessarily an energy eigenbasis. `energy_matrix` K has shape (6,6) and is the Hamiltonian projected into this basis: physical states are U*c. `x_orbital_nm` has shape (D,) and gives the position of each amplitude component, with four consecutive components per physical site. `x_grid_nm` is the sorted list of distinct x coordinates. No spatial rows or transverse orbitals have been removed. Basis rotations and orbital gauge transformations carry no physical information.

Let S be the two-dimensional physical subspace corresponding to the **two eigenvalues of K closest to zero in absolute value**. They form a separated particle-hole pair; the other four states must not be included. Define the left-end state as the normalized vector in S minimizing the expectation of x. Its minimizer is unique up to a global phase in these inputs. This variational definition isolates an end without adding an unphysical edge potential and without requiring a gauge-fixed spinor. Do not return a single positive-energy eigenstate, which can occupy both ends.

Return `rho_left`: the real, nonnegative **probability mass** at each coordinate of `x_grid_nm`, obtained by summing squared absolute amplitudes over all rows at that x. It must sum to one. Return densities, not amplitudes; global spinor phase is unscored.

Also return the operational finite-window **amplitude** length `xi_window_nm`. Let N=len(x_grid_nm), q=N//4. On indices q,...,2*q-1, fit log(rho_left) = intercept + slope*x by unweighted ordinary least squares with an intercept. Define xi_window_nm = -2/slope. All target densities in this window are positive and all reference slopes negative. This deliberately fixed finite-window statistic is reproducible even in a multimode oscillatory profile; it is **not** asserted to equal the asymptotic bulk length. There is no arbitrary smoothing, peak threshold, or amplitude cutoff to tune. A density envelope exp(-x/ell) corresponds to amplitude length 2*ell.

## Output

    {"schema_version": 1, "predictions": {
      "example_bulk_id": {"xi_amplitude_nm": 27000.0},
      "example_end_id": {"rho_left": [0.1, 0.2, "..."], "xi_window_nm": 750.0}
    }}

The numbers and identifiers above are illustrative, not answers. Replace the ellipsis by numeric entries. Return every requested ID and no duplicate JSON keys. Lengths must be finite and strictly positive; profile entries finite and nonnegative, with sum within 1e-5 of one. A missing case gets zero quality; a malformed component gets zero component quality without discarding other valid components or cases. Extra IDs are ignored. Do not emit NaN or Infinity.

## Scoring and resources

Each bulk case has raw quality exp(-abs(log(predicted/reference))/0.25).
For an end case, let h2 = 0.5*sum((sqrt(predicted_density)-sqrt(reference_density))**2). The raw profile quality is exp(-h2/0.05); length quality is exp(-abs(log(predicted_length/reference_length))/0.20). The end case raw quality is their arithmetic mean. Malformed components score zero independently. No finite-array renormalization is performed by the evaluator.

Average quality separately over cases of each family. Normalize each family by clip((quality-weak_quality)/(strong_quality-weak_quality),0,1), using fixed author-run calibration of the shipped finite-only starter and an independently implemented strong solver on the same evaluation inputs. The overall score is the equally weighted mean of the two normalized family scores, regardless of case counts. Raw per-component and per-family quality is also reported. This prevents bulk cases from swamping end-state extraction. Zero and one are baseline anchors, not accuracy thresholds.

The batch runtime limit is 300 seconds, one BLAS thread, with a 6 GiB address-space limit. Wall time is reported but is not a separate quality objective. Full finite-system diagonalization is intentionally unnecessary: the expensive six-state extraction is supplied, while the scientific localization analysis remains. Standard dense diagonalization of a single Hamiltonian is not a solution to both targets. Evaluator inputs are staged without answers; proper isolation of private assets is the outer runner's responsibility.
