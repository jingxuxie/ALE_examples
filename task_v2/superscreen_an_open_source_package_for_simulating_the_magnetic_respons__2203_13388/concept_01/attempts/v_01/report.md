# Qualification of the resolved thin-sheet response pipeline

## Decision and scope

Use the **`qualified`** backend, not the legacy adapter, for the supplied
piecewise-affine sheet model. It uses the actual elementwise penetration depths,
integrated sources, hole topology, coupled magnetic energy, and the same triangle
currents for state preparation and vector readout. No output inductance matrix
is projected onto a symmetric matrix, and no magnetic core radius is introduced.

Across all 16 development excitations, its largest differences from the
order-40 calculation are **8.65e-6 in current** and **8.78e-6 in vector field**.
The largest RMS-normalized spatial discrepancies are 3.45e-5 for current and
3.40e-5 for field. These are numerical convergence measurements, **not certified
absolute errors or experimental validation of London theory**. Independent
kernel/energy checks and the limitations below matter alongside these numbers.

## 1. Reproduce, inspect, revise, rerun

The untouched adapter was run first. `baseline.log`, `baseline/raw/`, and its
tables preserve that run; both original contract tests passed. The two-hole
reciprocity defect is **0.0419726**, reproducing the laboratory observation.
Nevertheless, the largest reported fluxoid-control residual is only 7.89e-8
mT um² and the largest linearity residual is 2.23e-7. Evaluating those states
with the subsequently converged variational operator gives a fluxoid-constraint
discrepancy as large as **1.1695 mT um²**. Thus small residuals in the adapter's
own extraction convention did not establish the intended physical state.

Inspection and controlled experiments identify distinct problems:

* **Resolved discretization:** native nodal collocation/extraction is not the
  specified triangle-current energy discretization. Even constant-material,
  single-film controls differ materially after replacing only their readout.
  This is a qualification failure of this adapter/regime, not a claim that the
  upstream scientific package is generally defective.
* **Material representation:** the adapter first averages element coefficients
  to vertices and samples that interpolant. This changes a prescribed
  discontinuous material, rather than accurately solving it.
* **Coupling:** four film-to-film iterations with nodal Biot–Savart transfers
  are not a converged, resolved close-sheet energy solve. Removing coupling
  changes the stack but not the single-film controls, as originally observed.
* **Readout:** output `current` is the triangle gradient of `stream`, but native
  field readout uses native nodal currents and lumped-area source points.
  Lift-off much smaller than an edge is particularly poorly resolved.
* **State/source control:** contour extraction can be internally self-consistent
  without being the conjugate fluxoid of the resolved model. Bare flux is not
  fluxoid. The legacy path also reconstructs vortices from JSON coordinates,
  rather than consuming the authoritative integrated `vortex_load` array.

The first replacement used fixed order-12 near-panel quadrature. Its genuine
pilot outputs remain in `pilot/`; final `fixed12` reproduces those states.
Shrinking the stack gap and penetration depths exposed larger quadrature
differences, recorded in `stress_pilot.log` and `stress_pilot/`. I revised the
cross-film integration to adaptive subdivision, then reran all cases and the
stress series. A recursive Numba implementation also failed on cache reload
with a segmentation fault; it was replaced by a bounded explicit stack.
Fresh-process and relocated runs exercise the non-recursive implementation.
Readout kernels were then cached to make repeated excitations inexpensive.

## 2. One model for state, currents, fluxoids, and fields

Let `P` identify all vertices of each hole with one current degree of freedom,
retain each free film vertex, and eliminate exterior vertices. With `g=P q`,
the triangle current operators are `C_x=partial_y P` and
`C_y=-partial_x P`. Hole-interior triangles have exactly zero current.
The stiffness, in the units specified in `workspace/PHYSICS.md`, is

```
S_ab = (1 / 4 pi) integral_Ta integral_Tb 1 / |r-r'| dA' dA
K = C_x^T [S + diag(area * Lambda)] C_x
  + C_y^T [S + diag(area * Lambda)] C_y
f = P^T (vortex_load - M_applied H)
F(q) / mu0 = q^T K q / 2 - q^T f .
```

The applied load uses the exact affine-triangle mass matrix, including the
complete hole footprints. Lambda stays elementwise; its conservative weak
form requires no invented nodal gradient at a material jump. All inter-film
magnetic blocks are included before the solve. No source is inferred from
metadata or rounded to a vertex in the qualified backend.

Partition `q=(u,I)` into free vertices and holes. Eliminate `u` by Cholesky
factorization of `K_uu`. Then

```
u = K_uu^-1 (f_u - K_uI I)
fluxoid = mu0 (K_Iu u + K_II I - f_I)
L = mu0 (K_II - K_Iu K_uu^-1 K_uI).
```

The unknown-current subblock of `L` imposes the requested fluxoids, while
finite prescribed currents remain fixed. This handles mixed constraints and
arbitrary numbers of drives/holes. The full no-source inductance is a Schur
complement, not a contour fit or a postprocessed symmetrization.

The inner triangle potential integral is analytic: edge logarithms minus
height times signed solid angle. Its analytic gradient gives all three
components of the Biot–Savart integral for a uniform triangle current. This
resolves near-sheet fields without softened kernels or observer quadrature;
at a sheet the signed solid angle is set to its principal-value average.

Only the remaining **outer energy integral** is quadrature-based. The default
uses tensor-Duffy Gauss orders 12 near, 6 intermediate, and 4 far. Separation
is compared with the sum of the panels' centroid radii. Close inter-film pairs
use order-6/order-12 error estimates, relative tolerance 2e-7 and up to three
four-way subdivisions. This estimator is not a rigorous global error bound.
The two integration directions are averaged when assembling each symmetric
energy pair; the reported `L` is never symmetrized afterward.

## 3. Development measurements and attribution

The following are **drive 2** differences from `reference`, taken directly from
`ablation.csv`. Baseline columns are percentages; qualified columns are fractions.
The near set has nearest-plane lift-off below 0.1 times the median square root
of triangle area. The far set has lift-off above that median length.

| Case | Legacy current (%) | Legacy near field (%) | Qualified current | Qualified near field |
|---|---:|---:|---:|---:|
| dev_ring | 14.68 | 80.89 | 1.46e-6 | 1.25e-6 |
| dev_holes | 53.05 | 89.47 | 2.19e-6 | 1.50e-6 |
| dev_pattern | 85.66 | 79.12 | 3.41e-6 | 2.42e-6 |
| dev_stack | 31.11 | 85.19 | 1.70e-6 | 1.63e-6 |

For these drives, baseline far-field differences range from 11.39% to 22.01%,
versus at most 8.56e-7 for the qualified calculation. Baseline full-inductance
differences range from 7.49% to 23.46%, versus at most 1.01e-6 for qualified.
`results.csv` includes every drive, not just these representative rows.

The controlled configurations establish causation more narrowly than a single
before/after comparison:

| Configuration | Change relative to qualified, unless noted | Observation |
|---|---|---|
| `legacy_exact_readout` | Keep legacy states and L; integrate their triangle currents exactly | Ring near-field difference falls from 80.89% to 22.78%; state error remains. |
| `smoothed_material` | Average Lambda element-to-node-to-element only | Patterned current difference is 7.35% on drive 2; constant-material controls are unchanged to roundoff. |
| `no_coupling` | Omit magnetic cross-film blocks only | Stack field difference is 54.39% on drive 2; single-film controls are identical. |
| `bare_flux_control` | Control geometric hole flux, including applied flux, but still report actual conjugate fluxoid | Ring drive 1 has zero bare-flux residual yet a physical fluxoid residual of 0.16789 mT um². |
| `fixed12` | Disable close-pair adaptive subdivision | Reproduces the pre-revision pilot and is less accurate on the close-gap stress cases. |
| `coarse` | Order 4 outer integration, no adaptivity | Worst current difference is 5.54e-4, versus 8.65e-6 for qualified. |
| `refined`, `reference` | Near orders 24 and 40, no adaptivity | Worst order-24/order-40 current difference is 5.09e-7. |
| `legacy`, `uncoupled` | Original adapter, respectively four or zero coupling iterations | Retain the original baseline and its coupling control. |

Readout-only repair is not universally an improvement in a scalar norm:
the two-hole drive-2 far-field difference rises from 22.01% to 33.74% when
accidental cancellation with the erroneous state is removed. This is why the
final method repairs state and readout together. Similarly, bare-flux control
still solves the interior equilibrium accurately but prepares the wrong
topological state. Qualified ring drive 1 instead has an order-40 physical
fluxoid residual of 8.32e-9 mT um².

The qualified own-system constraint residual is at most 6.67e-16 mT um² and
its linearity residual is at most 5.94e-16. Re-evaluation with order 40 gives
a less flattering but useful maximum fluxoid-constraint discrepancy of
3.63e-6 mT um². These two different residuals are deliberately both reported.

## 4. Independent checks and stress experiments

`workspace/tests/` has nine passing tests, including the two original tests.
Checks include analytic potential/vector integrals against direct, high-order
area integration; singular self-energy against an independently reduced
boundary integral; close-sheet adaptive integration against order 100;
hole-current/fluxoid control and energy conjugacy; positive vortex response;
the no-hole/one-drive case; and vertex/triangle permutations.

Additional reproducible experiments, with generated inputs retained under
`experiments/inputs/`, give the following evidence:

* **Close sheets:** gaps 0.008, 0.0008 and 0.000008 um, each with original Lambda
  and Lambda multiplied by 0.01. At the hardest setting, fixed12 field difference
  from order 72 is 1.290e-3; adaptive qualified reduces it to **8.231e-5**.
  Order 40 itself differs from order 72 by 6.406e-5 there, so it cannot be
  treated as an exact oracle for this stress case. See `stress.csv`.
* **Spatial vortex source:** a barycentrically distributed integrated vortex
  load on the ring gives current convergence of 3.84e-6. Moving the same total
  load to one nearest vertex changes current by **64.58%**, showing why the
  supplied source array must not be replaced by rounded coordinates.
* **Numbering invariance:** arbitrary vertex/triangle permutations plus cyclic
  triangle rotations change current by 1.41e-6, consistent with quadrature
  orientation error rather than an indexing assumption.
* **Sheet limits:** the full-mesh field jump agrees with
  `mu0 (J_y,-J_x,0)` to 1.93e-9 at lift-off 1e-9 um. The on-sheet field equals
  the symmetric two-sided average to the recorded precision.
* **Continuum kinetic limit:** increasing ring Lambda from 15 to 1500 um
  reduces the difference from `2 pi mu0 Lambda / log(b/a)` from 4.07% to
  **1.48%**. The remaining polygon/finite-element discrepancy is not removed
  by energy quadrature refinement and is not concealed as solver tolerance.

`energy_consistency.csv` also compares magnetic energy from the current-current
matrix against independently integrated `integral(g B_z)/2` over the complete
footprints, with the currents held fixed. Its order series checks that readout
and state assembly represent the same magnetic energy, including hole regions.
From integration order 6 to 24 the energy discrepancy decreases from 0.199%
to 0.0140% for the ring, and from 0.882% to 0.0622% for the stack. This direct
area integration of logarithmic near-edge fields converges more slowly than
the potential-based matrix assembly. Omitting hole regions instead leaves
54.75% and 63.15% discrepancies at order 24: their zero current does **not**
permit omitting their constant stream from the field-energy identity.
`diagnostics.csv` and the corresponding raw archives back the other checks.

## 5. Runtime, memory, and repeated excitations

All numerical kernels use one CPU thread. The final development timing pass
runs each case/configuration in a fresh process, serially. Resource rows are
not cumulative high-water marks of one long suite process. The measured default
development results are:

| Case | Vertices / triangles | Setup (s) | In-process total (s) | Peak RSS (MiB) |
|---|---:|---:|---:|---:|
| dev_pattern | 126 / 222 | 0.687 | 1.137 | 152.7 |
| dev_holes | 131 / 233 | 0.702 | 1.320 | 152.7 |
| dev_stack | 151 / 243 | 2.079 | 2.483 | 153.3 |
| dev_ring | 165 / 292 | 1.030 | 1.449 | 153.8 |

`scaling.csv` additionally includes a 330-vertex/584-triangle two-ring device
and a **relocated, empty-cache** run. Its `run_kind` and `raw_file` columns
identify these separately. `warmup_seconds` measures JIT compilation/cache
loading; `setup_seconds` measures geometry, matrix construction and factorization;
`solve_seconds` and `readout_seconds` isolate excitation and first readout.
The in-process total also includes backend import overhead; `process_wall_seconds`
additionally includes interpreter startup, input loading and output writing.
Cached development kernel warm-up is about 0.21–0.22 s. Cold compilation is
substantially larger and must not be interpreted as geometry scaling.
The larger device takes **3.366 s and 159.5 MiB** (2.905 s setup). The relocated
cold ring takes **16.614 s and 271.8 MiB**, including **15.273 s warm-up**;
its arrays reproduce the ordinary run. These measured processes are below
the 60 s / 4 GiB limits. The fresh-process legacy timings include upstream
initialization/JIT costs that are not separately instrumented; they must not
be confused with the much shorter subsequent in-process baseline solves.

After a fixed-device `SheetModel` is constructed, 30 batches of four changed
excitations take **0.81–1.14 ms per batch, median**, with factorization and
observer kernels reused (`reuse.csv`). These API timings exclude file I/O;
invoking the CLI anew does not retain that in-memory state. The method is
therefore practical for repeated excitations, even when a fresh setup is costly.

Storage is dense, approximately O(T² + n² + PT), and construction includes
quadratic panel interactions and a cubic free-vertex factorization. More
close pairs increase quadrature work: triangle count alone does not explain
the stacked-device time. The supplied sizes are too narrow for a convincing
empirical asymptotic exponent. Wall-time outliers and shared-host scheduling
remain visible in the resource data; no timing-based accuracy claim is made.

## 6. Reproduction and limits

Set `ALE_RUNTIME` to the supplied offline dependency directory. The required
interfaces are supported without the original implementation workspace:

```bash
bash run.sh case CASE.npz RESULT.npz [--config NAME]
bash run.sh suite /path/to/input/suite.json /path/to/output
bash reproduce.sh /path/to/input /path/to/output
```

`reproduce.sh` adds the stress/source/energy/reuse/scaling experiments, cold
relocation, table/claim audit and tests. `claims.json` makes six quantitative
comparisons in `ablation.csv`; the audit checks them against the actual rows,
recomputes original summaries from raw arrays, and checks the preserved
baseline and pilot. The two required figures are generated only from the
submitted `ablation.csv` and `scaling.csv`.

Trust is limited to the specified **resolved, linear, zero-thickness model**.
The quadrature comparisons share implementation and use the same intermediate
and far rules; they do not exclude all common-mode errors. The added analytic,
independently integrated and energy/readout checks reduce that risk but are
not an independent full-device oracle. Adaptive depth is bounded, not a proof
of arbitrary-gap convergence. No mesh-refinement certification, finite-thickness
correction, experimental material calibration, nonlinear/Josephson physics,
point-vortex ultraviolet energy, or general continuum error bound is claimed.
Exactly on a discontinuous-current edge, ideal-sheet fields can be singular;
the smooth-interior sheet-limit tests do not certify such singular observers.
Held-out geometries have not been seen, and these development measurements
are not a universal performance or accuracy guarantee.
