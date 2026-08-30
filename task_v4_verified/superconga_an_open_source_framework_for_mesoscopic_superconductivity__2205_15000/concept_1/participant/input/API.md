# Input and solver API

Each self-contained JSON has `schema_version: 1` and these required fields:

| Key | Meaning / shape |
| --- | --- |
| `case_id` | Opaque identifier; do not branch on it |
| `shape` | `[ny,nx]`; medium grids, approximately 90–140 sites per side |
| `h` | Positive dimensionless spacing |
| `mask` | Integer 0/1, `(ny,nx)` |
| `alpha`, `beta` | Finite onsite coefficients, `(ny,nx)`; `beta > 0` |
| `ax`, `kx` | Rightward link phases and positive stiffness, `(ny,nx-1)` |
| `ay`, `ky` | Increasing-row link phases and positive stiffness, `(ny-1,nx)` |
| `initial_real`, `initial_imag` | Exact frozen baseline field, `(ny,nx)` |
| `wall_seconds` | Informational resource limit, 60 |

The initial field is a feasible stationary state found by the prior solver.
Its independently recomputed energy is the scoring baseline `B`. Returning this
field unchanged is reproducibly valid with zero improvement: there is no
regression penalty caused by a stochastic baseline replay. You may change all
active amplitudes and phases, including vortex and hole-winding sectors.

Masks describe connected grains with dozens of perforations and narrow bridges;
some include metallic pinning patches. Link phases are physical vector-potential
line integrals, including flux confined to holes and optional smooth bulk fields.
No independent random Peierls bonds or negative stiffness occur. Do not assume a
particular gauge, uniform material, exact translational symmetry, or identical
hole flux. Infer geometry from the mask; no private generator is needed.

`gl_model.py` is in `input`, not installed globally. The supplied baseline is
self-contained. The public API is unchanged:

```python
from gl_model import load_case

model = load_case(case_path)
energy, complex_gradient = model.energy_gradient(model.initial)
packed = model.pack(model.initial)
energy, real_gradient = model.objective(packed)
psi = model.unpack(packed)
```

See `MODEL.md` for the real-coordinate gradient convention. `pack/unpack` operate
on active sites. Energy ignores inactive values, but valid outputs must set them
to zero within modulus `1e-12`.

Submit a directory with `solve.py` at its root. Its CLI is
`solve.py --input CASE_JSON --output RESULT_NPZ`. Use `np.savez` or
`np.savez_compressed` with **exactly one array, `psi`**, shape `(ny,nx)`, dtype
`complex64` or `complex128`. Object, real-only, nonfinite, wrong-shape, extra-array,
or oversized outputs are invalid. Both compressed NPZ bytes and the sum of ZIP
members' declared decompressed sizes must be at most 4 MiB, checked before loading.

Only public participant files, the immutable submission, one input case, and
empty output/scratch are exposed. `/participant`, `/submission`, `/input`, and
`/output` are evaluation mount points; the working directory is `/submission`.
`PYTHONPATH=/participant/workspace:/participant`. Add `/participant/input` or the
corresponding local sibling path when using `gl_model.py`. There is no persistent
cross-case state. All threads share one CPU core. A missed deadline invalidates
the result even if an NPZ exists. Scratch includes `/tmp`, output and logs, with
at most 4096 entries and 64 MiB per file; total bytes are monitored and checked
at exit, not protected by a filesystem quota.

Development numeric targets are diagnostics, not hidden references. Private
witness fields and generation scripts are never public. A witness energy is an
attained upper bound on the unknown global minimum, not an optimum certificate.
