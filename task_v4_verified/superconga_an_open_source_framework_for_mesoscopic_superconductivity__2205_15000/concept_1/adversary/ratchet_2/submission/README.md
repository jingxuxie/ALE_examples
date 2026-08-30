# Perforated-grain GL solver

Run from this submission directory:

```sh
python3 solve.py --input CASE_JSON --output RESULT_NPZ
```

Dependencies are Python, NumPy, and SciPy. The three Python files must remain
together. The output contains exactly one complex128 array, `psi`, with inactive
sites set to zero. No external executables, network access, or cross-case state
are used. `--progress` optionally prints search diagnostics.

## Method

- Construct the exact sparse, gauge-covariant GL energy and gradient.
- Extract hole cycles from the supplied mask and project their phase fields
  through a weighted graph Laplacian. This gives a small quadratic model of
  changes in hole winding, without assuming a gauge or uniform material.
- Search winding sectors using population annealing, paired changes, and
  spatial cluster changes. Fit small corrections to the quadratic model from
  the full GL energies observed during this invocation.
- Reconstruct complete complex fields and relax them with nonlinear conjugate
  gradients and exact quartic line searches. The local relaxation follows the
  supplied previous solver's method.
- Retain the stationary baseline as a fallback, accept only lower-energy
  stationary fields, and polish the best field before writing the result.

The search checks both wall and CPU time against a 55-second internal budget.
Numerical-library thread counts are set to one before importing NumPy/SciPy.
The solver reads no case identifiers, development targets, or reference fields.

## Development validation

The supplied independent `gl_model.py` recomputed these results:

| Development case | Energy | Gradient RMS | Clipped gap closure |
| --- | ---: | ---: | ---: |
| `dev_disordered_loops` | -1803.3483169362473 | 1.223e-7 | 1.0 |
| `dev_pinned_loops` | -2835.4878974408157 | 1.352e-7 | 1.0 |

Measured end-to-end solver times were 47.0 and 48.7 seconds, respectively.
Both NPZ files passed shape, dtype, finiteness, inactive-site, exact-array-name,
and compressed/decompressed size checks. Their compressed sizes were under
124 KiB. A nontrivial local gauge transformation also preserved the candidate
field and energy to numerical precision; the sparse gradient agrees with the
independent implementation to below 4e-15 on the tested field.

These are public development diagnostics, not held-out evaluation results.

A further pinned-case run with CPU affinity restricted to one core, a 2 GiB
address-space limit, a 60-second CPU limit, and a 60-second wall alarm completed
in 51.7 seconds. Peak resident memory was 160,460 KiB, and its independently
checked energy and gradient matched the table.
