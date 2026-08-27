# Executable sheet-response qualification

The default `qualified` backend is an energy-Galerkin solver on the supplied
continuous piecewise-affine streams. It uses the elementwise material map,
exact source mass integration, fully coupled magnetic blocks, Schur-complement
fluxoid control, and analytic uniform-triangle Biot–Savart readout.

From the deliverable directory, with the provided offline runtime:

```bash
export ALE_RUNTIME=/path/to/supplied/workspace/runtime
bash run.sh case /path/to/device.npz /path/to/result.npz
bash run.sh suite /path/to/input/suite.json /path/to/results
export PYTHONPATH="$PWD/workspace:$ALE_RUNTIME"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1
export NUMBA_CACHE_DIR="$PWD/.cache/numba"
python -m pytest workspace/tests -q
python -m qualification.experiments /path/to/input "$PWD"
python -m qualification.audit /path/to/input/suite.json "$PWD"
```

`bash reproduce.sh /path/to/input /path/to/output` automates the suite,
additional experiments, a relocated empty-cache run, the combined scaling
table/figures, raw/table/claim audit, and tests. It does not require the original
implementation workspace, only the frozen inputs and `ALE_RUNTIME`.

The sibling JSON is required. No installation or network access is used.
The suite runs each case/configuration in a fresh process, writes raw arrays
and per-run metrics, derives all tables and claims from those arrays, and
plots the submitted tables. `high_reference` is additionally available through
`case --config high_reference`; it is used for the hardest extra stress test.

The development suite intentionally runs all eleven configurations and takes
several minutes. Use `case` for a single default solve.

For repeated excitations, import `qualification.galerkin.SheetModel`, construct
it once for a fixed geometry/material/topology, then call `model.solve(case)`
with changed `drive_H`, `vortex_load`, current and fluxoid targets. Geometry
and material must remain unchanged. Factorizations and observer kernels are
reused; changed observer coordinates rebuild only the readout kernel.

Configuration definitions and qualification limits are in the top-level
`report.md`. The retained upstream package is used only by the named legacy
ablations; its license is in `UPSTREAM_LICENSE`.
