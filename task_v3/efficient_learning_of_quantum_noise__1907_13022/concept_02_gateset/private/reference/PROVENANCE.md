# Source connection and scientific validity

This is direction F in the parent `private/CANDIDATES.md`, authored as a disjoint worker. No independent participant agent or ultima-alpha attempt was launched. All benchmark changes are inside `concept_02_gateset/`; the parent source checkout and shared evaluator sandbox are read-only dependencies.

## Exact later source

- Official repository: `csenrui/PauliGST`, revision `9946e16305a3927ffff9706f3ffedd4c98b9b30f`.
- Local artifact: `../../../private/sources/PauliGST/PauliGST_published_250514.ipynb`, SHA-256 `81a63ad79a43c3d7640d10f5671a392c13727970ce76428f75e46bcecb41047d`.
- Associated paper: Chen, Zhang, Jiang, Flammia, *Efficient self-consistent learning of gate set Pauli noise*, arXiv:2410.03906v2. The pertinent results are the pattern-transfer cycle/cut characterization, reduced-model pullback, rooted depth-zero/one experiment construction, and gate-cycle amplification in Sections III–IV, with spatial ansatz applications in V–VII.
- Notebook cell numbers below are zero-based. Cell 6 constructs parallel entangling layers. Cells 9–10 define reduced parameters and `add_S_noise`, `add_M_noise`, `add_G_noise`. Cell 12's `getEq` reverses a circuit, propagates Pauli observables, and accumulates reduced noise features. Cell 14 constructs depth-zero/one experiments; cells 18–19 build amplified experiments; cell 22 checks their learnable gate rank. Cells 37–40 reconstruct the log-linear model from finite-shot contrasts. Cell 42 embeds reduced parameters into channel eigenvalues; cell 48 explicitly distinguishes gauge-dependent eigenvalues from learnable cycles.

`solver.py:Model.feature` is the same reduced eigenvalue embedding in an invertibly transformed local coordinate system. `Model.trace` follows `getEq`; `Model.rooted_experiments` and `structural_basis` implement the rooted-cycle construction, rather than treating the rank of the supplied calibration matrix as the structural gauge. `likelihood_fit` is an explicitly authored statistical refinement of the notebook's log/pseudoinverse estimator: it fits the actual signed binomial counts under a positive local-generator model. We do not claim the notebook itself uses this likelihood optimizer or that the entire notebook was executed.

### Frame and sign adaptation

The notebook's `getEq` conjugates first and adds gate noise to the resulting Pauli. The public interface therefore fixes the **input-frame** convention `U ∘ Λ`. The paper also writes an output-frame convention; these are related by Clifford conjugation of the channel eigenvalue indices. No input/output-frame ambiguity is left to the participant. Unlike the notebook's example estimator, this pilot preserves ideal Clifford signs instead of taking absolute contrasts. Raw counts therefore include negative signed expectations.

### Equivalent local coordinates, not sparse recovery

Gate channels contain every full-weight nonidentity Pauli generator on each declared one-/two-site factor, with strictly positive rates. Their log eigenvalues are `2 Σ_E r_E [E,P]`. SPAM factors are isotropic subsystem-depolarizing semigroups with log eigenvalues `Σ_F s_F 1{F intersects support(P)}`. Products of these channels are completely positive and trace preserving.

The notebook uses anchored subset cumulants: a term on factor `F` contributes when all its sites are nonidentity. For a fixed nonidentity axis assignment on `F`, its cumulant equals `Σ_{T⊆F} (−1)^(|F|−|T|) x(P_T)`. Our models include singleton factors whenever a pair factor is included. This invertible change of coordinates makes the two embeddings identical; pair cumulants need not be positive even though all physical generator rates are positive. `test_original_notebook_embedding_functions` checks the pinned source hash, executes the original three embedding functions from cell 10, and compares their predictions with the independent generator embedding for every four-qubit Pauli.

## Why identifiability is not a planted-gauge label

Let `Q` embed reduced coordinates into the complete channel eigenvalue edge space. The complete pattern-transfer graph has a root for SPAM and nonzero support-pattern vertices. Preparation edges go root→pattern, measurement edges pattern→root, and a gate edge goes from the support of its input-frame Pauli to its ideal propagated support. If `B` is the edge-by-nonroot-vertex incidence matrix, an interior reduced displacement is gauge precisely when `Q δ ∈ image(B)`. Learnable linear functions annihilate these displacements. This is the reduced cycle/cut characterization, not a statement about the randomly chosen rates.

The reference constructs rooted length-two/three circuit rows from the input gate/factor descriptions. They span all structurally learnable functions. To avoid enumerating all `4^n` Paulis, it enumerates observable supports within the dependency scopes of each local term and its Clifford pullback. An anchored inclusion–exclusion expansion shows this suffices: every root-row function is a sum of functions on these scopes, so its full-support evaluation is a linear combination of evaluations on their subsets. In these gate sets the largest scope is four sites. The exhaustive four-qubit test verifies the compressed construction against every Pauli.

Structural labels test query membership in this all-experiment row space. Calibration labels instead use the supplied training rows. Neither computation reads shot counts, fitted rates, seeds, or oracle values. The restricted-components family has a genuine additional calibration null space. Its two small core cases probe some disconnected patches only in a computational sector; its large core and all challenge cases instead use connected chains/rings with computational-sector-only calibration across the device, even though perfect single-qubit controls are available in principle. The large instances are not replications of the small patches.

For independent validation, `graph_constraints` in `test_reference.py` explicitly constructs the complete graph and an independently computed generator embedding, projects off its cut space, and compares the resulting learnable projector with the reference. A separate test moves a strictly positive physical model along nonzero gauge vectors: circuit expectations are unchanged while individual channel atoms change. Another test perturbs all unidentifiable oracle query values by 1000 and verifies that every loss remains unchanged. Thus no solver is penalized for failing to recover an arbitrary planted gauge.

## Oracle, fitting, and independent checks

Generation uses seeded positive physical channels to compute latent held-out means and query values. These hidden values are scoring targets only. The strong solver's sole argument is the public input dictionary, and the executable is staged alone under Landlock: even its original reference directory is not readable. It fits rates from noisy training counts; only calibration-identifiable query values are scored. Its physically constrained rate vector may select any feasible gauge representative.

The unit suite also implements a separate density-matrix simulator, explicit subsystem twirling, independent bit-indexed Clifford unitaries, and direct Born-rule parity expectations. It checks signed predictions, trace preservation and positivity for small fully local and crosstalk models. A distinct binary-symplectic implementation checks all training/held-out signs. Tests cover source equivalence, graph/root equivalence, positive gauge orbits, incomplete calibration, fresh-seed 24-qubit fitting, connected 16-qubit restricted-sector construction, deterministic regeneration, smooth scoring, private-path denial through both filesystem aliases, and writable temporary/cache directories.

## Scale correction and complexity

The initial 4–10-qubit core and 10/12-qubit challenges were insufficient evidence of the requested scalable setting. Before any participant launch, the unchanged reference was tested on genuinely coupled 20- and 24-qubit crosstalk models. Both pass the same 120-second/3-GiB Landlock limits; `scale_probe.json` records their measured runtime, peak RSS, accuracy, graph connectivity and propagated observable weights. The active pool now keeps exactly nine core cases, with one connected 20-qubit case per family, and six challenges, all connected 20/24-qubit cases.

At 24 qubits the probe has 672 reduced parameters and 6,048 compressed rooted experiments, with maximum local dependency scope four. No full `2^n` pattern graph or `4^n` Pauli space is enumerated by the submitted reference or generator. Full graph/Pauli enumeration appears only in independent three-/four-qubit tests. The reference still uses dense polynomial-cost SVD and likelihood linear algebra on the compressed representation; this is not a claim of graph-linear runtime or demonstrated performance beyond 24 qubits. Actual scalability and benchmark hardness remain separate claims.

This remains a synthetic, source-grounded pilot—not acquired device data and not an empirical claim of participant hardness. See `ANTI_COMPRESSION.md` for the measured limitations.
