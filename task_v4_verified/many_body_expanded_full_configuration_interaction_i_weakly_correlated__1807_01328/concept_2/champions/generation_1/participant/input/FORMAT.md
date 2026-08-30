# Fixed model and complete submission format

## Scope and provenance

This is a synthetic, number-conserving, Hermitian fermionic Hamiltonian with one- and two-body operators. Attractive as well as repulsive effective coefficients are allowed. Coulomb-integral representability, an underlying molecular geometry, and full-Fock-space ground-state certification are **not** imposed or claimed. All energy, weight, and gap conditions refer to the explicitly specified seniority-zero sector. The instance is deliberately nonuniform; its constants cannot be rescaled or permuted in a submission.

The inspiration is Eriksen and Gauss, *Many-Body Expanded Full Configuration Interaction. I. Weakly Correlated Regime*, arXiv:1807.01328v2, Section 2.1, Eqs. (3)–(8). Eq. (6) uses a maximum of absolute parent increments. The paper explicitly discusses signed increments and misleading energy differences, rather than claiming a universal error bound. This benchmark supplies a coarser, fixed threshold and a precise all-parents gate. A success falsifies only the inference “this gate's termination implies a small tail” in this testbed. It is not a reproduction of the paper's molecular calculations or its initial 1e-10 Eh threshold.

## Hamiltonian

Spatial orbitals are numbered 0 through 9. The occupied reference set is `O={0,1,2}` and the virtual set is `V={3,4,5,6,7,8,9}`. There are exactly three pairs, not three electrons. Define

\[
P_p^\dagger=c_{p\uparrow}^\dagger c_{p\downarrow}^\dagger,
\quad P_p=c_{p\downarrow}c_{p\uparrow},
\quad Q_p=(n_{p\uparrow}+n_{p\downarrow})/2,
\]
\[
H=\sum_p e_pQ_p+\sum_{p<q}U_{pq}Q_pQ_q
+\sum_{p<q}t_{pq}(P_p^\dagger P_q+P_q^\dagger P_p).
\]

All coefficients and energies use Hartree (`Eh`). One microEh is 1e-6 Eh. The coefficient `e_p` is a **pair energy**, not an energy per electron. In the paired sector each `Q_p` is 0 or 1. For every three-orbital determinant `D`,

\[
H_{DD}=\sum_{p\in D} e_p+\sum_{p<q;\ p,q\in D} U_{pq}.
\]

Replacing one occupied pair `q` by one empty orbital `p` gives matrix element `t_pq`; other off-diagonal elements vanish. There are no factors of two or additional signs in this ordered paired basis. The full matrix dimension is `choose(10,3)=120`.

The authoritative constants are the evaluator's frozen copy of `target.json`, identical to the supplied public copy:

- `pair_energy_eh`: all ten fixed pair energies.
- `occupied_virtual_hopping`: the fixed 3-by-7 hopping block; its transpose fills the reverse block. Occupied–occupied hopping is zero.
- `background_density`: fixed entries with at least one occupied index. Its virtual–virtual zero block is replaced, not added to, by the submitted block.
- Only the virtual–virtual hopping and density blocks are variables: 21 distinct entries in each symmetric matrix, 42 continuous degrees of freedom in total.

The reference determinant is `Phi={0,1,2}` with `E_ref=H_Phi,Phi`. It is a stationary closed-shell HF reference because this Hamiltonian has no matrix elements from it to single excitations. We do **not** assert that it is the global orbital-optimized unrestricted HF minimizer. The explicit weakness proxy is its squared overlap with the exact paired-sector ground state. The separate diagonal-margin condition enforces that it is the unique lowest-energy paired occupation determinant.

## Subsystems and increments

For each `S subset V`, retain all three occupied orbitals and exactly the virtuals in `S`, with all three pairs still active. Never freeze occupied pairs. Diagonalize the principal block on all three-pair determinants in `O union S` to obtain its lowest eigenvalue `E(S)`; `E(empty)=E_ref`. This is an exact sector CAS calculation, of dimension `choose(3+|S|,3)`.

Set `C(S)=E(S)-E_ref`, `Delta(empty)=0`, and

\[
\Delta(S)=C(S)-\sum_{\varnothing\ne R\subsetneq S}\Delta(R).
\]

Equivalently use the alternating subset sum of `C(R)`. No base-model subtraction, selection of eigenstate by overlap, screening inside a subsystem, rounding of coefficients, or arbitrary energy offsets are permitted. Subset mask bit `index` denotes virtual orbital `3+index`; masks run from 0 to 127.

Define

\[
E_{\le3}=E_{\rm ref}+\sum_{1\le |S|\le3}\Delta(S),\quad
A=\max_{|S|=3}|\Delta(S)|,\quad
L=|E(V)-E_{\le3}|,\quad R=L/\max(A,10^{-10}\ {\rm Eh}).
\]

The signed tail is also reported. `L` is the **absolute net missing energy**, not a sum of absolute increments, and `A` is a maximum over **all 35 triples**, not a signed third-order sum.

## Precise screening gate being challenged

Compute every increment through order three without screening. A quadruple `Q` is generated if and only if at least one of its three-element parents has absolute increment **strictly greater** than `tau=1e-6 Eh`. Equivalently, for each possible appended orbital `d in Q`, form the three triples containing `d` from two elements of `Q without d`, apply the maximum test of Eq. (6), and take the union over all possible generating parents. Since every triple exists at this point, the union test equals the maximum over all four triples in `Q`.

If no quadruple is generated, terminate and return `E_le3`; no higher descendants can be generated. This task requires `A <= tau`, so all 35 quadruples must be discarded. Equality at the threshold means discard. No rounding or threshold relaxation is used. A tiny **signed** third-order sum alone cannot qualify.

The complete witness conditions are `A <= 1e-6 Eh`, `L >= 50e-6 Eh`, and `R >= 100`. This deliberately probes a failure of the supplied screening implication, not merely an implementation error in the MBE identity.

## Physical admissibility

Let `lambda_0 <= lambda_1` be the two lowest full-sector eigenvalues and `psi_0` its normalized ground eigenvector. Require all of:

- `|<Phi|psi_0>|^2 >= 0.95`.
- `lambda_1-lambda_0 >= 0.4 Eh` in the full 120-dimensional paired sector.
- `min_{D != Phi}(H_DD-E_ref) >= 0.6 Eh`, over all other 119 paired determinants, not just pair singles.
- Every entry in each virtual block is finite, the matrices are exactly symmetric with exactly zero diagonals, `|t_pq| <= 0.45 Eh`, and `|U_pq| <= 0.60 Eh`.

The evaluator recomputes all energies and wavefunction diagnostics independently. It also checks the eigenvector residual, exact-MBE closure, nested-subspace variational ordering, and two full-sector eigensolver results at absolute tolerance 5e-10 Eh. Scientific thresholds receive **no additive tolerance**. Search with comfortable margins rather than aiming at floating-point equality. The ratio floor is only a numerical denominator convention, not a license to submit energies.

## Static JSON format

`output/witness.json` must be a regular UTF-8 file, not a symbolic link, at most 32,768 bytes. It has exactly these three keys:

```json
{
  "schema_version": 1,
  "virtual_hopping": [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "six more numeric rows"],
  "virtual_density": [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "six more numeric rows"]
}
```

The display is schematic: the actual arrays must each have seven rows of seven JSON numbers. Row/column 0 means spatial orbital 3. `input/baseline_witness.json` is a complete valid example. Repeat symmetric values exactly. Booleans, strings, duplicate keys, NaN, infinities (including overflow such as `1e999`), extra keys, wrong shapes, nonzero diagonals, and bound violations are rejected. Do not supply claimed metrics or code. Only this file is evaluated; other output files are ignored.

## Scores, resources, and local diagnostics

For an admissible candidate the core score is

\[
\min\left(1,\frac{10^{-6}}{\max(A,10^{-10})},\frac{L}{50\times10^{-6}},\frac{R}{100}\right).
\]

An inadmissible or malformed candidate scores zero. `valid` means schema, physical bounds, and numerical checks all pass; it does not mean that a witness was found. `passed` requires validity and all three witness conditions. There is one fixed family, so `worst_family_score` is `null` (not a second optimization objective). `resource_score` is 1 for a well-formed, within-budget numerical evaluation and 0 for malformed input or evaluator resource failure; it does not reward speed and is not a search-runtime score. Wall time and worker peak memory are reported separately.

The trusted evaluator has a 30-second wall limit, 15-second CPU limit, 512 MiB address-space limit, one BLAS thread, and closed stdin. It never imports or executes participant code. There is no submitted CAS budget and no way to attest offline search runtime from this static artifact.

The public Python API is `model.compute(witness, complete=True)` and `model.score(metrics)`. `complete=False` evaluates only the 64 subsets through order three plus the full problem, useful for search. Complete diagnostics include all 128 subset energies, all increments, order sums, and maximum absolute increments. The evaluator uses a separate fermionic-bitmask matrix builder and direct alternating subset sums, not this public module.
