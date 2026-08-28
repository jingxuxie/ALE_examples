# Pilot 03: localization beyond a finite device

## Delivery and isolation

Only this pilot directory is authored. No agents were launched. `attempt/` is intentionally empty. Distribute **only** `participant/` to the participant; create its writable `attempt/` in the central isolated runner. Do not mount this author directory, `private/`, the shared `source/`, or other pilots in that runner. In particular, **no Kwant source or runtime is vendored into participant files**. The public starter imports only NumPy/SciPy and contains only finite-eigenstate density fitting, not a translation/mode solver.

Run all commands below from the pilot root, one directory above this private note:

```bash
python private/evaluator.py --submission attempt/solve.py --report private/report.json
python private/evaluator.py --self-test
```

The first command is an author convenience launcher with resource limits, **not a filesystem security sandbox**. The central sandbox should instead use the split interface:

```bash
python private/evaluator.py --export-input private/staged_input
# Centrally mount staged_input read-only as INPUT, attempt/ as code, and a writable output directory.
# Inside that sandbox: python attempt/solve.py --input INPUT --output OUTPUT
python private/evaluator.py --predictions private/returned_output.json --report private/report.json
```

Both `--export-input` and `run_submission` use the same `stage_inputs` function. It copies the manifest and every referenced NPZ into one clean directory, using regular files rather than symlinks or references back to the pool. All manifest `file` values are basenames relative to that directory. The holdout export is self-contained: exactly `manifest.json` plus 18 NPZs, with no targets, reference code, raw pickle, calibration, or source/runtime dependency. `run_submission` creates a fresh temporary `input/` directory and passes that directory to the submission or Python sandbox wrapper as `--input`; it does not pass or mount `private/challenge_pool`. The central wrapper must mount only this supplied input directory, never its parent or the whole private tree. A nonempty export destination is rejected to prevent stale private files from being included.

The evaluator uses 18 held-out representations: 13 bulk cases and 5 finite-end cases. Two public examples (`b01`, `e10`) are excluded from that mean. The `e11` case is a deliberate gauge-invariance companion of the public finite geometry, not a claimed unseen physical device. Other finite cases use different smooth/rough geometries. No labels or normalization anchors are staged into solver input. The files under `private/reference/` are author-only, even where they are executable.

## Scientific targets and solution gap

Two separately normalized family scores have equal final weight:

1. **Bulk tail beyond a short device.** The nominal straight junction has an archived amplitude length 26,653.783980556494 nm, much longer than its 4550 nm device. Official zero-energy modes reproduce it as 26,653.784060327274 nm with the installed constants. Other full-width parameter cases reach about 122,868 nm. The participant receives complete H/T blocks and finite-device densities, but no asymptotic routine. Finite-window density fits are not an identifiable definition of the infinite tail. The matrices remove that identifiability obstruction without handing over the method. Grouping two actual lattice slices produces singular intercell hopping, so inverting T is not valid; the physical translation length doubles. This is a real representation of the same physical Hamiltonian, not an added arbitrary polynomial.
2. **Finite multimode end extraction.** Full spatial six-state BdG subspaces retain the entire 4550 nm sawtooth, smooth, and rough device. Four higher low-energy states are present alongside the nearly zero-energy pair. Energy-basis rotations and site phases do not change the physical answers. The requested left-end state is defined variationally within the lowest particle-hole pair, not as whichever positive-energy eigenvector the solver returns. Both the complete x-density and its oscillatory finite-window decay statistic are scored. The density target is gauge invariant. It is not legitimate to include all six states, fit a single arbitrarily phased component, square a density twice, or confuse amplitude and density lengths.

The two observables are explicitly **different**: the bulk asymptotic amplitude length and an operational amplitude length fitted to an isolated finite end. No asymptotic length is assigned to a disordered finite sample. The finite fit window follows the source's quarter-to-half indexing, but the definition uses the physically explicit factor of two. It is not an arbitrary peak-finding or smoothing contest.

The weak solver is `participant/workspace/finite_workflow.py`: select the positive-energy finite state, project its density, perform the original finite-window log fit, and correctly convert density slope to amplitude length. It is not intentionally broken by omitting the factor of two or by confusing arbitrary basis columns with eigenstates. For bulk cases it uses a parameter-matched finite witness, not an unrelated nominal profile. The strong NumPy/SciPy solver is `private/reference/strong.py`; it derives a generalized matrix pencil for bulk decay and isolates the pair's end subspace. The hidden bulk labels themselves come from the official stabilized Kwant translation implementation, independently checked against that SciPy solver.

This is an **honest candidate**, not a claim of an unsolved task. A participant familiar with singular quadratic eigenproblems and projected-position localization may solve it within an hour. The full mathematical contract necessarily permits deriving the short strong algorithm. If a fresh isolated participant solves it, reject the pilot rather than obscuring its definitions or changing physical scales. The private sanity report also measures an overgenerous shortcut that reuses exact public strong outputs everywhere; those outputs are not supplied to participants.

## Anti-compression rationale

- No reduced transverse model: straight cells contain all 320 BdG orbitals; grouped cells contain 640 and have hopping rank 320.
- No short substitute device: every finite witness has 455 lattice slices at 10 nm spacing, x=0,...,4540 nm, representing an open device of length 4550 nm. The missing endpoint at 4550 is the original half-open discretization, not truncation.
- Finite end states retain 182,000 or 183,820 orbital rows and 45,500 or 45,955 sites. Smooth/rough boundaries and both 300 nm superconducting regions remain. The source sawtooth/sine amplitude parameter is 100 nm; do not reinterpret it as a new reduced junction.
- Supplying six precomputed low-energy states removes the expensive generic sparse eigensolver, not the scientific localization target. All positions and complex amplitudes remain. The task is deliberately not benchmarking SuperLU versus MUMPS.
- Grouping and gauge transformations are invariance checks, not counted as new independent physical bottlenecks. Final family weighting is independent of representation count.
- The parameter sweep uses the official high-density model, including the nominal 26.65 micrometer tail and larger tails, rather than shrinking the difficult long-tail regime to a well-localized toy.
- The raw archive is retained unmodified and hashed privately. No simulation is described as a measurement. Generated parameter witnesses and regenerated spinors are identified as such.

## Source provenance and historical qualification

Upstream: `https://github.com/basnijholt/zigzag-majoranas` and arXiv `1903.06168`, localization section IV, Figure 3. The shared checkout is complete, not shallow: **694 commits**, HEAD `012e1ad347959690b7d25597ef8f1af34c43ac8d` (2020-10-09). `private/reference/full_history.txt` records every commit. Relevant evidence is retained privately:

- `b0c4aa5cb93db556e119e2eab91b19e5e8db5ebd` (2019-02-19), “fix xi_M algo and add phase bounds”: corrects extraction of the primitive lattice spacing in the existing mode method and adds the scalar particle-hole-breaking edge-potential plumbing. The complete diff is `reference/b0c4aa5.patch`.
- **The parent already contained `slowest_evan_mode`.** Therefore this participant package is a deliberately restricted finite-only starting workflow, not a fabricated claim that an exact historical commit predates all mode methods. `reference/historical_spectrum_before_fix.py` preserves that fact.
- `9f732f72b11a746f237586905f894a8d3869b551` (2019-02-25) added `data/wave_functions.pickle`; its Git blob is `c130ec5248cbc694c9b144eea1215103dd9f9a3b`.
- `ce302abb93a7748045b004acbe100074640dbe39` (2019-02-25) explains the two localization procedures in the text.
- Current `zigzag.py`: `translation_ev`, `majorana_size_from_modes`, `majorana_state`, `majorana_size_from_fit`, `system`, and `cell_mats` are the relevant official routines. `reference/official_zigzag.py` and the upstream BSD license preserve the full later implementation privately. No source file in the shared checkout is edited.

The unmodified archive is `private/reference/wave_functions.pickle`, SHA-256:

```text
d8a5ddc47486866fd37b95e1c82ba0dc4155c4ffca6be9951ee3f55d650f6abf
```

Its four records are `[E_M, site_density, E_gap, xi_label_in_micrometers]`. Despite the filename, it does **not** contain complex wavefunctions. Raw straight xi is 26.653783980556494 micrometers; raw shaped-device labels are 0.3869118688130279, 0.3543503249209758, and 0.3680309027094468 micrometers. These labels are not blindly relabeled as our finite-end amplitude targets.

**Important convention/reproducibility finding:** `majorana_size_from_fit` fits log of density and returns `1/slope_magnitude`; `majorana_size_from_modes` returns an amplitude length. Directly fitting the archived shaped densities reproduces the archived labels (about 386.912, 354.350, 368.031 nm). Moreover, the checked-out notebook's `get_phs_breaking_potential` selects the minimum **y**, whereas its Hamiltonian calls `V_breaking(x)`; in these systems minimum y=-500 nm and all x>=0, so that helper is a no-op. This does not justify claiming that the archive contains an isolated pinned-end spinor. The pilot instead defines and verifies a gauge-invariant isolated-end target, and keeps the archive's original conventions explicit. Its finite amplitude targets are approximately 652.653, 583.276, and 615.471 nm; they are not the archive's printed xi values.

## Numerical reproduction

`private/build.py` imports the read-only shared `source/runtime` (Kwant 1.5, tinyarray) and official `zigzag.py`. It reproduces notebook cell 4 parameters and cell 15 geometries: m_eff=0.02 m_e, alpha_middle=20 meV nm, mu=10 meV nominal, code B_x=1 nominal, g_factor_middle=26, Delta=1 meV, phase=pi, W=200 nm, lattice a=10 nm, period=1300 nm, L_sc_up=L_sc_down=300 nm, and roughness (60,30,1) where applicable. It preserves the **code's** Zeeman parameter convention rather than silently inserting an additional factor 1/2. Both k_x hopping in the superconductors and transverse spin-orbit coupling are retained.

The only author-side compatibility shim subclasses Kwant's `_NumericPrinter` to register unqualified sin/cos/exp under SymPy 1.12. It changes generated function printing, not the Hamiltonian, and is not a participant challenge. All finite eigensolves use SciPy sparse `eigsh`, not the official MUMPS-only wrapper.

For the three shaped geometries, fresh full-matrix eigensolutions match the actual archived site densities at total variation 9.50e-8, 7.88e-8, and 7.42e-8. Absolute eigenpair residuals are below 4.4e-10 meV; archived-versus-recomputed near-zero energies differ by at most 1.71e-9 meV. The straight finite reconstruction is separately validated against its archive (density-profile TV about 2.31e-7, energy difference about 4.54e-8 meV). These are measured numerical differences, not claimed bitwise identity or asserted experimental error bars. Detailed values are in `reference/finite_*_audit.json` and `reference/straight_*.json`.

Each unique bulk parameter combination gets a 145,600-orbital open-chain witness from the complete official primitive-cell blocks. Nominal archived density is used after validating the regeneration; other parameter densities are regenerated simulations. The build checks primitive and grouped official translation results and stores hidden mode roots. `reference/provenance.json` records all input SHA-256s and reference lengths. A full rebuild followed by fresh strong/weak runs is:

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python private/build.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python private/evaluator.py --calibrate
```

The build has local numerical caches; delete only the relevant pilot-private cache if intentionally changing a Hamiltonian. Do not reuse caches after changing the source revision or parameters. Normal evaluation never rebuilds references or imports Kwant.

## Sanity artifacts

`reference/calibration.json` fixes the weak/strong anchors per split. `reference/calibration_runs.json` records raw case qualities and measured wall times. `reference/sanity_checks.json` includes strong=1, weak=0, missing=0, exactly one solved family=0.5, factor-of-two convention errors, nonfinite lengths, negative profiles, memorized nominal xi, and public-template reuse. `--self-test` rechecks these saved runs; `--calibrate` actually reruns both programs against staged inputs. Finite gauge variants also pass direct profile/length invariance assertions during building.

Runtime is reported, not rewarded: the default batch limit is 300 s with one BLAS thread and 6 GiB address space. The reference generalized pencil is intentionally an independent transparent SciPy cross-check, not an optimized opaque library call. No acceptance or rejection claim is made without the requested fresh centrally sandboxed participant pilot.

Final fresh holdout calibration measured weak raw qualities **0.1948107144 bulk / 0.2017743084 end**, and strong raw qualities **0.9999999999 bulk / 1.0 end**. The normalized mean is weak **0** and strong **1**. Solving only either family yields **0.5**. Halving all amplitude lengths yields **0.19659**; memorizing the nominal bulk length with weak end extraction yields **0.20508**; reusing exact public strong answers everywhere yields **0.54433**. Measured batch times were **0.92 s weak / 96.21 s strong** on the shared author host, not guaranteed hardware-independent timings.

Final packaging checks verified all 20 input hashes, Hermitian bulk onsite blocks, normalized finite witnesses, orthonormal uncompressed spatial bases, an empty `attempt/`, and absence of Kwant imports/code in participant files. Central-export staging contains exactly the 18 held-out NPZs plus the manifest, without symlinks or references. Duplicate JSON keys, oversized integers, nonfinite lengths, malformed/negative profiles, and nonempty staging directories are checked. `reference/archive_conventions_audit.json` records the direct archived-density fits discussed above.
