# Extended challenge: source-grounded stress regimes

This is an additional `stress` split of the **same concept**, with the same public bounds, Hamiltonians, observables, scoring function, and resource contract. It is not a ratchet, a changed threshold, a new task, an experimental dataset, or a set of confirmed participant counterexamples. The four finite-system inputs are authored physical instances motivated by the primary sources below. No student/attempt or fresh agent is run here. Any later held-out ratchet/confirmation cases must be newly generated and distinct from these four; none are generated now.

## Why these two regimes

### Weak-rung spin-half ladders

Greven, Birgeneau and Wiese, *A Monte Carlo Study of Correlations in Quantum Spin Ladders*, arXiv:cond-mat/9605068v1, PDF pp. 2--3, Fig. 5, discuss the reduction of the spin gap and growth of the low-temperature correlation length when the rung coupling decreases. Their weak-coupling comparison covers rung/leg ratios at most 0.5. Primary URLs: <https://arxiv.org/abs/cond-mat/9605068v1>, <https://arxiv.org/pdf/cond-mat/9605068v1>, <https://doi.org/10.1103/PhysRevLett.77.1865>.

**Design inference, not an exact reproduction:** our 72/80-site ladders have rung/leg ratios approximately 0.30--0.37, rather than the roughly order-one-or-larger ratios in the existing pool. Weak smooth exchange modulation, anisotropy near one, and fields at most 0.003 preserve the declared model while avoiding a uniform-chain energy lookup. Rung and both same/opposite-leg correlators extend to half the rung count. The independent bottlenecks are resolving the low sector excitation and long-distance spin correlations, versus contraction/optimization cost in the more strongly leg-coupled geometry. We do not use the homogeneous source's numerical gap formula as a reference for the inhomogeneous inputs.

### Near-Mott Bose-Hubbard chains

Kühner, White and Monien, *The one-dimensional Bose-Hubbard Model with nearest-neighbor interaction*, arXiv:cond-mat/9906019v2, discusses on-site-only interactions in Sec. VI, hopping correlations in Sec. V.B, connected density correlations in Sec. V.C, and truncation convergence in Appendices A/B, especially Figs. 23--28. Sec. VI/Table I gives the historical unit-filling estimate `t_c/U = 0.297 +/- 0.010` and explains its logarithmic finite-size uncertainty. The paper reports increasing truncation difficulty toward the superfluid regime and stronger long-distance correlation sensitivity than short-distance sensitivity. Primary URLs: <https://arxiv.org/abs/cond-mat/9906019v2>, <https://arxiv.org/pdf/cond-mat/9906019v2>, <https://doi.org/10.1103/PhysRevB.61.12474>.

**Design inference:** the 64/80-site inputs use on-site interactions approximately 4.05--4.14 and hoppings approximately 1.208--1.238, giving an interaction/hopping envelope around 3.27--3.43. They probe the unit-filling Mott-crossover neighborhood rather than the stronger-coupling cases already stored. The trap is at most 0.084. Long-distance one-body coherence, connected density correlations, and the three-sector charge gap are measured separately. We do NOT assert that these finite, mildly inhomogeneous, `nmax=4` systems sit at the exact thermodynamic critical point or lie on opposite sides of it. The local cutoff remains the exact public Hamiltonian definition; it is not silently extrapolated away.

## Why the existing MPS method is the reference

- Dolfi et al., *Matrix Product State applications for the ALPS project*, arXiv:1407.0872v2: Sec. 2 explains controlled bond-dimension truncation and the effect of lattice-to-chain ordering; Sec. 3.2/Fig. 7 demonstrates that distant pairing correlations can remain inaccurate after much easier quantities appear stable. This supports checking correlations separately from energy, not transferring the paper's Hubbard-ladder numerical values to these spin/boson models. <https://arxiv.org/html/1407.0872v2>, <https://arxiv.org/abs/1407.0872v2>.
- Hauschild and Pollmann, *Efficient numerical simulations with Tensor Networks: Tensor Network Python (TeNPy)*, arXiv:1805.00055v4: Sec. 2.1 motivates the entanglement/correlation-length limitation, Sec. 3.5 describes finite-system DMRG, and Sec. 5 explains charge-conserving tensor operations. The discussion after the TEBD example notes slower ground-state convergence near critical points and motivates the more general DMRG implementation. <https://arxiv.org/pdf/1805.00055v4>, <https://doi.org/10.21468/SciPostPhysLectNotes.5>.
- Official ALPS correlation tutorial: the summary contrasts critical versus gapped correlation decay and warns that long-range correlations converge more slowly with kept states than local energies. <https://alps.comp-phys.org/tutorials/dmrg/dmrg06/>. This live documentation is supporting explanation, not the pinned numerical reference.

Exact historical tutorial paths, verified in the official ALPS tree at `34688482fbc09fe7d359987f3e1e223fa07bfcb2`:

- <https://github.com/ALPSim/ALPS/blob/34688482fbc09fe7d359987f3e1e223fa07bfcb2/tutorials/dmrg-04-correlations/spin_one_half.py>
- <https://github.com/ALPSim/ALPS/blob/34688482fbc09fe7d359987f3e1e223fa07bfcb2/tutorials/dmrg-02-gaps/spin_one_half_gap.py>
- Official later MPS implementation: <https://github.com/ALPSim/ALPS/tree/34688482fbc09fe7d359987f3e1e223fa07bfcb2/applications/dmrg/mps>

Actual executable reference remains TeNPy v1.0.6, `b5408eaf11d3f3ed8fc71de96a8b681c8e4c7c04`, with no new solver invented:

- <https://github.com/tenpy/tenpy/blob/b5408eaf11d3f3ed8fc71de96a8b681c8e4c7c04/tenpy/algorithms/dmrg.py> (`TwoSiteDMRGEngine`)
- <https://github.com/tenpy/tenpy/blob/b5408eaf11d3f3ed8fc71de96a8b681c8e4c7c04/tenpy/models/model.py> (the existing explicit spin-bond MPO interface)
- <https://github.com/tenpy/tenpy/blob/b5408eaf11d3f3ed8fc71de96a8b681c8e4c7c04/tenpy/models/hubbard.py> (`BoseHubbardChain`)
- <https://github.com/tenpy/tenpy/blob/b5408eaf11d3f3ed8fc71de96a8b681c8e4c7c04/tenpy/networks/mps.py> (sector-state tensors, correlations, entanglement diagnostics)

## Reference and preservation protocol

`stress.py` reuses the existing `generate.py` optimizer and contractions. Four processes run independently, with BLAS/OpenMP threads set to one in those processes only. Every case starts at chi 128 and then 256. Chi 384 and 512 are attempted only if the preceding pair fails the unchanged reference tolerances. No convergence is presumed from the chosen chi values. Energy per site, the actual sector gap, and the maximum correlation difference must all pass; charge, norm, and final-sweep checks also gate readiness. Every completed sector records its energy, entropy, sweep history, and timing.

`stress_audit.json` compares each lower-chi output against the final high-chi output using the UNCHANGED scoring function, without executing any submission. Such a score is a reference-quality diagnostic, not a student score. Approximate agreement between successive chi values is not a rigorous proof of the global ground state; it supplements the pre-existing independent exact small checks.

Only new inputs under `challenge_pool/stress/`, new `reference/data/stress_*.json` artifacts, and stress-specific source/log/audit files are written. The manifest gains only `splits.stress`. `stress_preservation.json` records hashes of the public files, evaluator, original generation code, and every existing core/challenge input and reference; the final audit checks that they are unchanged.

From the concept root, generate with `PYTHONDONTWRITEBYTECODE=1 python private/reference/stress.py --workers 4`; audit with `PYTHONDONTWRITEBYTECODE=1 python private/reference/stress.py --audit`. Do not call the older `cases.py`, which would rewrite the public examples. A `ready: false` stress artifact must not be graded as a student failure.
