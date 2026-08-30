# Mathematical model, finite assay, and artifact contract

## Model and scientific scope

Spatial orbitals are 0,...,9. The reference is `Phi={0,1,2}`; virtual orbitals are `V={3,...,9}`. There are exactly three electron pairs (six electrons). Define `P_p^dagger=c_p,up^dagger c_p,down^dagger`, `P_p=c_p,down c_p,up`, and `Q_p=(n_p,up+n_p,down)/2`. The Hamiltonian is

\[
H=\sum_p e_p Q_p+\sum_{p<q}U_{pq}Q_pQ_q
+\sum_{p<q}t_{pq}(P_p^\dagger P_q+P_q^\dagger P_p).
\]

All coefficients are real and use Hartree (Eh); 1 microEh = 1e-6 Eh. `e_p` is a pair energy, not an energy per electron. In the seniority-zero sector `Q_p` is 0 or 1. For each three-orbital occupation determinant `D`, the diagonal is `sum(e_p for p in D)+sum(U_pq for p<q in D)`. A single pair transfer from occupied `q` to empty `p` has matrix element `t_pq`, with no extra sign or factor of two. Other off-diagonal elements vanish. The full paired-sector dimension is `choose(10,3)=120`.

`target.json` fixes all ten pair energies, the 3-by-7 occupied–virtual hopping block (reverse block is its transpose), and the density entries with at least one occupied index. Occupied–occupied hopping is zero. Replace the zero virtual–virtual block of `background_density` by the submitted density block. Only the 21 distinct virtual hoppings and 21 distinct virtual density interactions are variables. No relabeling, rescaling, offset, or change of fixed coefficients is allowed.

This is a Hermitian, particle-number-conserving one-/two-body effective fermion model. Attractive interactions are permitted; Coulomb-integral representability and an underlying molecule are not required or claimed. All exact energies, gaps, and weights concern seniority zero, not the full Fock space. `Phi` is a stationary closed-shell HF reference because it has no matrix elements to single excitations; it is not claimed to be the global unrestricted-HF minimizer.

The scientific motivation is Eriksen and Gauss, *Many-Body Expanded Full Configuration Interaction. I. Weakly Correlated Regime*, arXiv:1807.01328, particularly the max-parent rule in Eq. (6) and the warning about signed increments. The coarser fixed gate here is a supplied model diagnostic, not the paper's molecular implementation or a universal theorem that the paper claimed.

## Subsystem energies and the supplied gate

For every subset `S` of virtual orbitals, retain all three occupied orbitals and exactly `S`, keeping all three pairs active. Let `E(S)` be the lowest eigenvalue of that principal block, of dimension `choose(3+|S|,3)`. Never freeze occupied pairs or choose an excited state by overlap. Set `E_ref=E(empty)=H_Phi,Phi`, `C(S)=E(S)-E_ref`, `Delta(empty)=0`, and

\[
\Delta(S)=C(S)-\sum_{\varnothing\ne R\subsetneq S}\Delta(R).
\]

Subset bit `index` denotes virtual orbital `3+index`; masks run from 0 to 127. Define

\[
E_{\le3}=E_{ref}+\sum_{1\le|S|\le3}\Delta(S),\quad
A=\max_{|S|=3}|\Delta(S)|,\quad
L=|E(V)-E_{\le3}|,\quad R=L/\max(A,10^{-10}\mathrm{Eh}).
\]

`L` is an absolute net missing energy, not a sum of absolute increments. `A` is the maximum of all 35 individual absolute triple increments, not a signed third-order sum.

Compute all increments through order three without screening. A quadruple is generated exactly when at least one of its four triple parents has absolute increment strictly greater than 1e-6 Eh. This is the union of the Eq. (6)-style parent tests over all possible appended orbitals. If none is generated, terminate with `E_le3`, with no higher descendants. Equality discards. Thus `A<=1e-6 Eh` forces every quadruple to be discarded.

## Unchanged per-case witness conditions

Every successful case, nominal or perturbed, must simultaneously satisfy:

- `A <= 1e-6 Eh`, `L >= 50e-6 Eh`, and `R >= 100`.
- Squared reference overlap with the normalized full-sector ground state at least 0.95.
- Difference between the two lowest full-sector eigenvalues at least 0.4 Eh.
- Minimum `H_DD-E_ref` over all other 119 paired determinants at least 0.6 Eh.
- Exactly symmetric, zero-diagonal virtual blocks with finite real entries; hopping magnitude at most 0.45 Eh and density magnitude at most 0.60 Eh.

Numerical checks independently recompute all 128 subsystem energies and verify the first two eigenvector residuals, exact-MBE closure, nested-subspace variational ordering, and agreement of two full-spectrum computations, each at absolute tolerance 5e-10 Eh. No additive tolerance is added to any scientific threshold. No submitted energies, scores, or eigenvectors are trusted.

## Exact perturbation distribution and frozen finite assay

Flatten the 42 adjustable upper-triangle entries in this order: all hopping entries, then all density entries; within each block use lexicographic pairs `(row,column)` with `0<=row<column<7`. Each entry has its own bound `b` (0.45 or 0.60 Eh). For nominal entry `theta` and `delta=0.001 Eh`, define

\[
\ell=\max(-b,\theta-\delta),\quad h=\min(b,\theta+\delta),\quad
\theta'_{r,k}=\ell+(h-\ell)u_{r,k}.
\]

The `u_r,k` are independent uniform variates on `[0,1)`, sampled once using NumPy PCG64 and serialized as binary64-roundtripping JSON numbers. There are 128 rows and 42 columns. The fixed hidden table is committed by `hidden_uniforms_sha256` in `assay_spec.json`. Its seed and entries are private. The formula is evaluated in binary64; each perturbed upper entry is mirrored exactly, and all diagonal entries stay zero. Every case is centered independently on the nominal submission, never on a preceding perturbation. Occupied coefficients and pair energies are never perturbed. This is uniform sampling on the box intersection, **not clipping an initially untruncated noise sample**.

The nominal case must satisfy all original conditions, and at least `ceil(0.95*128)=122` perturbed cases must satisfy all original conditions. A perturbed physical-admissibility failure counts as an unsuccessful case; up to six unsuccessful cases are allowed. A numerical validation failure anywhere makes the evaluation invalid rather than treating an unreliable number as a pass. Every case is evaluated; no early success or statistical extrapolation is used.

The benchmark claims only success on this specified frozen assay. It does not certify all bounded perturbations, an infinite-population success probability of 95%, or an error theorem for the source paper.

## Independent public training diagnostics

`training_uniforms.json` contains 64 independently generated public rows, with a disclosed public seed, not any hidden rows. `workspace/check.py witness.json` uses them. `--seed INTEGER --samples COUNT` generates different public draws; COUNT must be 1 through 512. These diagnostics use the same distribution and fraction threshold, so the default 64-row training threshold is 61 successes. Passing public training does not imply passing the 128-row hidden assay. The public API is `assay.evaluate(candidate, uniforms)`, with `assay.perturb` and `model.compute` also available. No optimization procedure is prescribed.

The public model uses a combination-basis builder and recursive increments. The trusted evaluator separately uses fermionic bit masks, full-sector principal submatrices, and direct alternating subset sums. All files in the participant packet are read-only; place any code you create and all outputs in your own writable working directory.

## Static output at the writable work root

The sole artifact is **`witness.json`**, directly in the writable working-directory root. Do not use `output/witness.json` or place it in the read-only participant directory. It must be a regular UTF-8 file, not a symlink, at most 32,768 bytes, with exactly these keys:

- `schema_version`: the JSON integer 1, not a boolean or floating-point value.
- `virtual_hopping`: seven lists of seven JSON numbers.
- `virtual_density`: seven lists of seven JSON numbers.

Row/column 0 means spatial orbital 3. Repeat symmetric values exactly and use zero diagonal entries. Duplicate keys, wrong shapes, extra keys, strings, booleans, NaN, infinity, overflow such as `1e999`, nonzero diagonals, asymmetry, and coefficient-bound violations are rejected. The complete admissible zero-variable example is `input/baseline_witness.json`; it is the baseline, not a solution. No previous submission or privileged witness is supplied.

From a writable working directory, for example:

```sh
python /absolute/path/to/participant/workspace/baseline.py --output witness.json
python /absolute/path/to/participant/workspace/check.py witness.json
python /absolute/path/to/participant/workspace/check.py witness.json --seed 31415 --samples 128
```

## Scores, validity, and resources

Let `s=min(1,1e-6/max(A,1e-10),L/(50e-6),R/100)` for the nominal case. Let `f` be the fraction of successful hidden cases and `r=min(1,f/0.95)`. For a valid evaluation:

- `core_score=(s+r)/2`.
- `family_scores={nominal:s, perturbed_assay:r}` and `worst_family_score=min(s,r)`.
- `passed` requires nominal success and at least 122 hidden successes, independently of fractional-credit scores.

`valid` requires a schema-valid, physically admissible nominal Hamiltonian and successful numerical verification of every case. It does not require a nominal witness or 122 perturbed successes. Invalid evaluations have zero core and worst-family scores. The minimum individual perturbed nominal score is reported only as a diagnostic; it is **not** the worst-family score and does not replace the permitted six failures.

`resource_score` is 1 for a complete numerically validated evaluation and 0 for malformed input, failed numerical validation, or resource failure. It does not reward speed. The evaluator reports wall time and worker peak memory, uses one BLAS thread, closed stdin, a 60-second wall limit, 45-second CPU limit, and 512 MiB address-space limit. Generation-2 runtime limits come from `assay_spec.json`; legacy runtime entries in the byte-preserved nominal `target.json` are not used. Python 3.10+, NumPy, and SciPy suffice. No submitted code is imported or run. Offline search runtime cannot be inferred from this static artifact; there is no submitted CAS budget.
