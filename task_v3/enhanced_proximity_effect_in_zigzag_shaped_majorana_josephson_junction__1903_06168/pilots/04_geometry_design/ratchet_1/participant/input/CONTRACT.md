# Long-period junction contract

## Interface

The working directory is `participant/`. Write your executable in the separately assigned writable attempt directory. Each request is independent:

```sh
python /absolute/attempt/solve.py --input /absolute/REQUEST.json --output /absolute/RESULT.json
```

Exit zero and write one JSON object with exactly these keys:

```json
{"schema_version": 1, "request_id": "COPY_FROM_REQUEST", "geometry": {"sc_top": [[0, 1]], "sc_bottom": [[1, 0]]}}
```

The small arrays illustrate syntax only. Both arrays must have `ny` rows and `nx` columns, be row-major `[y][x]`, and contain integer 0/1 or JSON booleans. Sites assigned to neither electrode are normal semiconductor. Return geometry only, not spectra, claims, filenames, or scores. Honor the requested output filename. The output limit is 2 MB.

## Physical problem

Requests use a 20 nm grid with `nx=97`, `ny=66`, a 1940 nm periodic length, and a 1300 nm transverse center-to-center span: **25,608 BdG degrees of freedom**. The kinetic coefficient is 1905 meV nm², Rashba coefficient 20 meV nm, induced pairing 1 meV, and phase bias π. Transverse boundaries are open. Longitudinal Bloch momentum is a dimensionless phase per supercell. The precise basis, hopping, and onsite matrices are defined by the supplied `workspace/physics.py`.

Chemical potentials in covered and normal sites are matched. Zeeman splitting acts only on normal sites; spin-orbit hopping acts throughout. Geometry is the only design variable. The model is clean and fixed; do not alter its parameters, grid, or discretization.

**`operating_points` is the exact list of three scenarios scored for that request.** Each provides `mu_normal_mev` and `zeeman_mev`. These points vary between requests within the displayed `operating_region`; there are no undisclosed operating points within a request. The region gives physical bounds, not an instruction to replace the listed scenarios with a different grid. The returned geometry must work at all three supplied points.

`baseline_geometry` is a functioning, preoptimized starting layout, not the original straight or wide zigzag. Its associated earlier optimizer is available in `workspace/baseline/`. The baseline optimizer uses its own regional sampling policy; it is not an oracle for the requested optimum or the reference. No reference geometry is public.

## Feasibility

The unchanged `workspace/physics.py:feasibility` is authoritative:

- Contacts must not overlap. The outer six rows on each side belong entirely to their corresponding contact.
- Each contact is connected to its outer electrode, including across the periodic seam. Detached superconducting islands and enclosed normal holes are forbidden.
- Both masks obey longitudinal reflection `x -> (-x) mod nx`.
- The minimum periodic distance between occupied sites of opposite contacts is 100 nm, measured between lattice-site centers.
- A periodic 3-by-3 median filter may change at most `maximum_median_flips` sites across both masks, limiting unresolved boundary roughness.

At every supplied operating point, the independently checked class-D invariant must be −1 and the sampled excitation gap must exceed 0.00001 meV. A trivial large gap is not a valid solution. Geometry and physical feasibility are mandatory independently of improvement.

## Forward evaluation

`ForwardModel(request, masks, scenario)` supplies `hamiltonian(k)`, `low_energy(k)`, `spectral_gap(momenta)`, and `topological_invariant()`. `scenario` is one entry from `operating_points`. The helper performs forward calculations but does not optimize geometry.

An optional single-scenario diagnostic, with the output written to your writable attempt directory, is:

```sh
python workspace/forward.py --input input/example.json --geometry /absolute/attempt/result.json --mu 10.4 --zeeman 0.72 --momenta 9 --topology --output /absolute/attempt/diagnostic.json
```

Omitting `--geometry` evaluates the supplied baseline; omitting the parameter overrides uses the helper's nominal scenario, not the full request objective.

The evaluator recomputes eight states nearest zero on **51 uniform momenta in [0, π]** and independently evaluates the Pfaffian invariant at 0 and π. The score concerns this sampled lattice gap, not a certified continuum minimum. Coarse diagnostics are not expected to equal the full-resolution score.

For the three gaps, define `R = 0.5*mean(gaps) + 0.5*min(gaps)`. Each request has precomputed baseline and strong-design anchors. The continuous score is **`S = (R - Rbaseline)/(Rreference - Rbaseline)`**. The supplied starting geometry scores zero; the private existing design scores one. Scores are unbounded and are not clipped. A better design can exceed one; a worse feasible design can score below zero. Merely returning the public starting layout is not an improvement.

Reports retain mean core score, worst-request/family score, raw gaps, individual invariants, robust gap, and feasibility. Invalid or missing outputs fail feasibility and receive a zero bookkeeping score. Full feasibility takes precedence over numerical improvement. Physics is recomputed; participant claims are not scored.

## Resources

Per request: **1200 wall seconds, 2400 CPU seconds, two CPU cores, and 6 GiB memory**. Trusted scoring occurs separately. The submission must finish within the resource limits and may write only to its assigned attempt/output locations. NumPy, SciPy, and threadpoolctl are sufficient for the supplied helper. No network, optimized reference, or previous attempt history is available.
