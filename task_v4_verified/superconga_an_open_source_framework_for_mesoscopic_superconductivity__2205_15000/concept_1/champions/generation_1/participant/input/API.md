# Input and solver API

All files are self-contained JSON (`schema_version: 1`). Required keys:

| Key | Meaning / shape |
| --- | --- |
| `case_id` | Opaque identifier; do not branch on it |
| `shape` | `[ny, nx]`, development grids smaller; hidden grids 56–76 per side |
| `h` | Positive dimensionless spacing |
| `mask` | Integer 0/1, `(ny,nx)` |
| `alpha`, `beta` | Finite onsite coefficients, `(ny,nx)` |
| `ax`, `kx` | Rightward link phases and stiffness, `(ny,nx-1)` |
| `ay`, `ky` | Increasing-row link phases and stiffness, `(ny-1,nx)` |
| `initial_real`, `initial_imag` | A valid, gauge-compatible reference start, `(ny,nx)` |
| `wall_seconds` | Informational resource limit, 60 |

Initial fields are suggestions, not constraints or known equilibria. All solver
decisions may depend on the numerical input. Hidden generation seeds, family
labels, target energies, and witness fields are not part of the input. Domain
connectivity and holes can be inferred from the mask. Do not assume a particular
gauge, identical material coefficients, or uniform plaquette flux.

```python
from gl_model import load_case
from scipy.optimize import minimize

model = load_case(case_path)
energy, complex_gradient = model.energy_gradient(model.initial)
packed = model.pack(model.initial)
energy, real_gradient = model.objective(packed)
result = minimize(model.objective, packed, jac=True, method="L-BFGS-B")
psi = model.unpack(result.x)
```

`gl_model.py` is in the sibling `input` directory, not installed globally. The
workspace and input layout are preserved in evaluation. `energy` accepts a
full complex grid; inactive values are ignored mathematically, but outputs must
set them to zero. `pack/unpack` operate on active coordinates only.

The artifact is the designated output directory containing `solve.py` at its
root, not a modification to read-only `participant/workspace`. It runs with Python as
`solve.py --input CASE_JSON --output RESULT_NPZ`. Use `np.savez` or
`np.savez_compressed` with **exactly one array, `psi`**, of shape `(ny,nx)` and
dtype `complex64` or `complex128`. Real-only, object, nonfinite, incorrectly
shaped, oversized, or extra-array outputs are invalid. Inactive entries must have
modulus at most `1e-12`. Write the exact output path; the evaluator never takes
an energy, path, timing, or feasibility assertion from the submission.

Only the submitted directory, public `input` and `baseline` assets, one case, and
an empty output/scratch area are exposed. Submission sources are immutable during
evaluation. The process working directory is its workspace. Use standard library,
NumPy and SciPy already installed; do not install dependencies. Threads are limited
to one. A missed deadline invalidates the case even if an output exists. The
scratch limit includes `/tmp`, output files, and diagnostics; at most 4096 scratch
entries and 64 MiB per scratch/log file are allowed. The final NPZ has the tighter
4 MiB compressed and decompressed limit. Scratch bytes are monitored and checked
again on exit, not enforced by a filesystem quota.

Development baseline and lower-energy witness energies are in
`development_targets.json`. They are independently recomputed from attained
fields, not asserted ground-state energies. Development energies are diagnostics,
not hidden targets. No state may persist
across invocations; a solver must work for arbitrary cases satisfying this schema.
