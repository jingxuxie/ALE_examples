# Geometry-design contract

Return the geometry of a periodically repeated, planar semiconductor Josephson junction. Improve its **robust topological excitation gap beyond the supplied unoptimized zigzag**, while retaining fabricable, connected superconducting contacts. This is one geometry-design task, not a request to repair a simulator, infer localization lengths, or output eigenvalues.

## Solver contract

Your working directory is `participant/`. The runner supplies the absolute writable attempt directory. `/absolute/attempt` below is a placeholder for that supplied path, not a literal directory or a child of your working directory. Create `solve.py` in that directory. The runner calls it once per request:

```sh
python /absolute/attempt/solve.py --input /absolute/path/REQUEST.json --output /absolute/path/RESULT.json
```

Exit zero and write exactly one JSON object with exactly these keys:

```json
{"schema_version": 1, "request_id": "COPY_FROM_REQUEST", "geometry": {"sc_top": [[0, 1]], "sc_bottom": [[1, 0]]}}
```

The tiny arrays illustrate syntax only: **both arrays must have `ny` rows and `nx` columns**, contain only integer 0/1 or JSON booleans, and be row-major `[y][x]`. `1` assigns that lattice site to the named superconducting contact. Every site assigned to neither is semiconductor. Do not return a score, spectrum, parameters, filenames, or a parametric curve. Output is limited to 2 MB. Stdout/stderr are not the result. The output filename is arbitrary and must be honored.

## Physical scale and families

Requests supply a 20 nm square grid, periods of 980 or 1300 nm, and transverse center-to-center spans of 1200 or 1300 nm. There are 12,936–15,860 BdG degrees of freedom, not a rescaled toy lattice. The kinetic coefficient is 1905 meV nm² (effective mass about 0.02 electron masses), Rashba coefficient 20 meV nm, induced pairing 1 meV, and phase bias π. Transverse boundaries are open; longitudinal boundaries carry Bloch phase `k` in radians **per supercell**.

Geometry is the only design variable. Zeeman splitting is present only in normal sites; spin-orbit hopping is present throughout. The request specifies either matched normal/covered chemical potentials in 10–15 meV and Zeeman splitting 0.5–1.5 meV, or covered chemical potential fixed at 15 meV with normal chemical potential 9.5–10.5 meV and Zeeman splitting 1.35–1.65 meV. Robustness is assessed at three private operating points inside the supplied intervals. These points and all other physical parameters are independent of your output.

The provided baseline is a preoptimization triangular zigzag with 200 nm peak-to-peak centerline modulation and 200 nm perpendicular channel width. No optimized geometry or optimization algorithm is supplied.

## Manufacturing and topology

The checks implemented by `workspace/physics.py:feasibility` define fabrication feasibility:

- Contacts do not overlap; the outer six rows on each side remain fully assigned to their own contact, not the opposite contact.
- Each electrode connects to its corresponding outer contact, including across the periodic seam. Detached superconducting islands and enclosed normal holes are prohibited.
- Both masks are invariant under `x -> (-x) mod nx`. This longitudinal reflection is a physical symmetry constraint, not a file-format convention.
- Minimum distance between occupied sites of opposite electrodes, including the periodic seam, is 100 nm. This is the lattice-center convention; cell-edge clearance can be 80 nm.
- Apply a periodic 3×3 median filter to each mask. At most `maximum_median_flips` sites in total may change. This constrains sub-resolution boundary roughness without requiring perfectly rectangular contacts.

Every private operating point must also have class-D invariant **−1** and a sampled bulk gap above 0.00001 meV. A large trivial gap is not a successful solution. Invalid physical or manufacturing geometry fails the core feasibility gate and has a zero bookkeeping score for that request. Full feasibility takes precedence over numerical improvement when comparing submissions.

## Forward helper and evaluation

You may import the forward-only `workspace/physics.py`. `ForwardModel(request, masks, scenario)` exposes `hamiltonian(k)`, `low_energy(k)` (energies and wavefunctions), `spectral_gap(momenta)`, and `topological_invariant()`. It contains no shape optimizer or local-update search. The basis is spin ⊗ particle-hole, with the precise matrices specified in the source. From your `participant/` working directory, an optional diagnostic is:

```sh
python workspace/forward.py --input input/example.json --output /absolute/attempt/diagnostics.json --momenta 9 --topology
```

Without `--geometry`, this diagnoses the baseline. With `--geometry RESULT.json`, it diagnoses your output. `--mu` and `--zeeman` override the nominal operating point. No hidden evaluator is available to the solver.

The private forward evaluator recomputes the eight states nearest zero at **51 uniformly spaced momenta in [0, π]**, and independently checks the class-D Pfaffian invariant at 0 and π. Reflection symmetry makes the other half of the Brillouin zone redundant. The metric is explicitly a sampled lattice gap, not a certified continuum minimum. Coarser local diagnostics need not reproduce the grade.

For gaps `g1,g2,g3`, physical performance is `R = 0.5*mean(g) + 0.5*min(g)`. Each request has separately measured weak (original zigzag) and strong (private existing design) anchors. Its continuous score is the unbounded normalized improvement `S = (R-Rweak)/(Rstrong-Rweak)`: weak scores 0, strong scores 1, better designs can exceed 1, and worse feasible designs can score below 0. There is no clipping or saturation.

The report exposes `core_feasibility` (the fraction of families passing geometry and physical constraints), `core_score` (the equal-weight mean of family scores, also named `score`), and `worst_family_score` with the corresponding `worst_family` identifier. Missing or invalid outputs fail feasibility and contribute a zero bookkeeping score. Rank complete feasibility before improvement; among fully feasible submissions compare core score, then worst-family score. Raw sampled gaps, per-point topology, robust gaps, and every family score remain visible in the private report. Evaluation does not trust any participant-reported physics.

## Resources

Per request: 1200 seconds wall time, 2400 CPU seconds, 2 CPU cores, and 6 GiB RAM. The external runner must enforce these limits; private scoring time is separate. NumPy, SciPy, and threadpoolctl are sufficient for the helper. Exact diagonalization at every candidate geometry and operating point is expensive: geometrical feasibility and efficient robustness-aware search are separate substantive challenges. The assigned attempt directory starts empty.
