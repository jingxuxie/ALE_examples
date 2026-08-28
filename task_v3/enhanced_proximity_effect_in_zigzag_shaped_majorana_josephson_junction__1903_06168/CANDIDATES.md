# Solution-gap mining ledger

Authoring date: 2026-08-27. These are scientific-computing candidates, not claims that each is hard. All four selected concepts receive empirical tests before a selection decision.

## Provenance and discovery

- Original preprint: https://arxiv.org/abs/1903.06168 (submitted 2019-03-14).
- Official code and complete retained history: https://github.com/basnijholt/zigzag-majoranas ; checked out `012e1ad347959690b7d25597ef8f1af34c43ac8d` (694 commits).
- Original data DOI: https://doi.org/10.5281/zenodo.2578027 . The official repository also contains the raw data used below.
- Later supplemental work: `paper/appendix.tex`, `paper/referee_responses.md`, `paper/referee_responses_round_2.md`, and their git history. Importantly, this is not identical to the five-page original preprint. The final supplementary work includes disorder, one-superconductor devices, misaligned and snaking fields, and a transparency ablation.
- The repository's public issue/PR pages and release listings were inspected. No extra issue-derived or release-specific fix is claimed. Useful fix evidence comes from actual retained commits, not an inferred issue history.
- Follow-up: https://arxiv.org/abs/2205.05689 , submitted 2022-05-11, revised 2022-10-31, SciPost Physics 14, 047 (2023).
- Adjacent phase-gradient family: https://arxiv.org/abs/1905.02725 .
- Authoritative numerical implementation: https://kwant-project.org/doc/1/reference/generated/kwant.physics.modes and https://kwant-project.org/doc/1/pre/whatsnew/1.4 .

## A — Historical geometry and spectrum integration repair (pilot 01)

**Visible start:** a retained pre-fix revision or faithful extracted modules from it, with geometry and spectral call contracts but without later fixes.

**Private solution:** actual commits `7bc79e9` (closure binding), `06acb1b` (outer-edge handling), `00b1c82` (gap routine returning momentum instead of energy), and `ff2b0e0` (superconductor template integration); later official source is the comparison implementation.

**Outcome:** correct geometry/boundary behavior and physically meaningful spectral output across finite, periodic, and asymmetric-interface branches.

**Shortcut and failure regime:** fixing the obvious scalar return does not repair geometry/interface semantics; a single hand-drawn polygon does not implement periodic Boolean shape operations.

**Independent bottlenecks:** geometry composition and region ownership; Bloch/spectral API semantics; lead-template integration. **Check:** private source-generated geometry/Hamiltonian probes and spectral values. This may be solved easily; that is a reason to pilot, not to pretend it is frontier-hard.

## B — Original zigzag versus later robust inverse design (pilot 04)

**Visible start:** an unoptimized straight/zigzag device and forward model, without the follow-up optimizer or optimized masks.

**Private solution:** the later greedy-geometry work and its archived optimizer/design outputs, subject to executable artifact verification.

**Outcome:** manufacturable geometries with a robust spectral gap, rather than reproduction of a known zigzag plot.

**Shortcut and failure regime:** one sinusoidal or sawtooth ansatz and single-parameter optimization can overfit chemical potential/Zeeman field or violate feature constraints.

**Independent bottlenecks:** efficient local shape decisions on a large BdG matrix; geometric admissibility; robustness across physical parameters. **Check:** independently recomputed feasible geometry and held-out forward-model values relative to straight and archived strong designs. No geometry will be accepted solely on the participant's claimed gap.

## C — Clean workflow versus realistic disorder ensembles (pilot 02)

**Visible start:** clean junction assembly and sparse low-energy workflow, plus complete stochastic-disorder and result contracts; later disorder implementation and ensemble outputs remain private.

**Private solution:** commit `e3a750a`, later `disorder_strength_from_mfp`, `disorder_potential`, and `data/mfp-vs-gap.pickle`, containing 98,400 archived numerical evaluations. The supplement specifies 40 realizations and a three-period cell.

**Outcome:** correctly calibrated disorder and gap statistics/contrasts for clean-to-disordered straight and zigzag devices at the author's physical scale.

**Shortcut and failure regime:** equating disorder broadening with the gap or extrapolating the clean geometric enhancement fails when the gap distribution changes with mean free path, phase, and field. Dense diagonalization of all supercells is not an adequate reference strategy.

**Independent bottlenecks:** units/disorder normalization and reproducible spatial disorder; low-energy spectral computation across the ensemble; contrasting geometry and phase branches rather than reporting only a mean. **Check:** stored author outputs, independently validated numerical spot checks, family-level continuous errors and runtime. The precise archive mapping and reference reliability must pass author validation before launch.

## D — Zeeman SNS to a genuinely different phase-gradient/NS family

**Visible start:** the original two-terminal, uniform-field junction model.

**Private solution:** the later one-superconductor appendix/raw NS phase diagrams, or the adjacent supercurrent-induced proposal with phase gradients and momentum-mixing mechanisms. These are separate candidate transfer targets, not interchangeable models.

**Outcome:** establish a gapped topological phase after the physical mechanism and boundary conditions change.

**Shortcut and failure regime:** replacing a scalar Zeeman parameter or deleting a pairing term need not implement a spatial phase gradient and gauge-consistent hoppings; a gap alone does not identify topology.

**Independent bottlenecks:** gauge-consistent model transfer; gap closure/topological classification. **Check:** hidden NS archive and, only where available, adjacent authors' executable reference. Not selected: original NS transfer overlaps the chosen numerical pilots; the more distinct phase-gradient target needs a verified reference artifact.

## E — Experimental circuit discrepancy, not just ideal band gaps

**Visible start:** the ideal/DC transport workflow and uncorrected measured three-terminal conductance maps, without the later instrument-circuit correction modules.

**Private solution artifact:** the official https://github.com/microsoft/azure-quantum-tgp repository, specifically `tgp/frequency_correction.py`, `tgp/bias_correction.py`, and `notebooks/fridge-calibration.ipynb`, with its experimental data. The two correction modules and the official module listing are retained under `source/tgp_*`. They implement frequency-dependent amplifier/filter mappings, three-terminal circuit corrections, and corrected bias coordinates. This later, adjacent capability is absent from the original ideal-junction workflow.

**Outcome:** recover calibrated device conductance and bias coordinates rather than misattributing circuit-induced mixing or gain errors to the intrinsic gap. Topological truth is explicitly not the target label.

**Shortcut and failure regime:** one scalar gain or constant series-resistance correction does not account for complex-frequency three-terminal cross-coupling and gate-dependent voltage redistribution. Fitting a density of states to a zero-bias feature would also conflate the measurement circuit with device physics.

**Independent bottlenecks:** measured filter/amplifier calibration, coupled-terminal network inversion, and nonlinear bias-coordinate correction. **Check:** withheld calibration sweeps and corrected arrays produced by the official modules, not a supposed experimental Majorana label. Not built: this is less directly tied to geometric optimization than the four selected concepts, and the operational calibration artifact was verified during the final source audit after the four pilot slots were committed. No fifth pilot was created. The earlier idea of grading a definitive topological interpretation from transport alone is rejected as unidentifiable: adjacent quasi-Majorana work (https://arxiv.org/abs/1806.02801) and the original experimental claim/its later critiques cannot be treated as an uncontested classification oracle.

## F — Multi-component gauge and lead integration

**Visible start:** manual Peierls phases and independently assembled finite-device/leads from the old modeling workflow.

**Private solution:** later Kwant 1.4 `magnetic_gauge` implementation, plus original snaking-field supplements. Distinguish orbital Peierls phases from the original in-plane Zeeman texture; they are not the same effect.

**Outcome:** correct loop fluxes and gauge-equivalent scattering observables in multi-lead devices.

**Shortcut and failure regime:** applying a Landau-gauge phase everywhere ignores lead periodicity and interface gauge matching; checking only Hermiticity misses the error.

**Independent bottlenecks:** graph cycles/flux constraints, lead embedding, transport covariance. **Check:** loop invariants and gauge-transformed transport with the official implementation. Not selected: less direct connection to the target's neglected orbital effects than the selected follow-up design task.

## G — Missing transparency-versus-path-cutoff ablation

**Visible start:** the original comparison of straight and order-width zigzag junctions, which changes both incidence angle and flight length.

**Private solution:** supplemental short-wavelength corrugation ablation: period/amplitude 80 nm, width 400 nm, reported gap approximately 6.1 micro-eV rather than an order-of-magnitude gain.

**Outcome:** produce a controlled comparison that distinguishes the two geometric mechanisms, including discretization convergence.

**Shortcut and failure regime:** reusing a large-amplitude zigzag comparison confounds transparency with the cutoff; too coarse a lattice aliases the short corrugation.

**Independent bottlenecks:** matched-control geometry and multiscale discretization/convergence; physically defensible attribution. **Check:** independent high-resolution spectra and geometric path diagnostics. Not selected: overlaps spectral work and has only a narrow archived reference region; no claim of broad ground truth from one printed number.

## H — Finite-state fitting versus asymptotic localization (pilot 03)

**Visible start:** a finite-wavefunction fitting workflow and raw device/eigenstate inputs without the later robust translation-mode branch.

**Private solution:** official translation-eigenvalue and Majorana-size methods, retained localization fixes including `b0c4aa5`, and archived wavefunctions.

**Outcome:** correct localization for both long-coherence straight junctions and short, oscillatory zigzag states, with a declared amplitude/density convention.

**Shortcut and failure regime:** a single log-linear density fit is unreliable when a 4.55 micrometer device is much shorter than a roughly 26 micrometer decay length or when both end states mix; a scalar inverse-gap heuristic ignores velocities and channel structure.

**Independent bottlenecks:** asymptotic mode selection and rank-deficient translation coupling; end-state/subspace extraction and oscillatory density interpretation. **Check:** mode-reference decay lengths, source finite-state data, gauge/end-state consistency, and separate long/short families.

## Anti-compression gates, before pilot construction

01 requires interacting geometry and spectral repairs, rather than a single numerical kernel. 02 must combine disorder calibration with realistic ensemble spectral work and branchwise attribution. 03 must require a genuine method decision between finite-state and asymptotic regimes, not merely call an eigensolver on every input. 04 combines constrained inverse design and robust physical evaluation. If implementation or pilot evidence shows any concept compresses to one fixed solver without a realistic-scale obstacle or independent bottleneck, it is discarded even if its average score is low.

No candidate is called hard before an isolated `ultima-alpha` attempt. Acceptance additionally requires executable strong-reference score above 0.90, complete public contract, fresh confirmation below 0.70, and substantive unsolved physics/numerics rather than missing dependencies, impossible identification, schema traps, or arbitrary tolerances.
