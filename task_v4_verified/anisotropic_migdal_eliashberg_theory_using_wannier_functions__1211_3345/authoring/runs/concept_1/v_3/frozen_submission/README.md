# Branch-correct Eliashberg solver

Run with Python, NumPy, and SciPy:

```sh
python solve.py --input INPUT.npz --output OUTPUT.npz
```

The standalone entry point writes only the float64 arrays `delta` and `z`.
It does not load the supplied operator, reference solutions, or development
outputs. BLAS and FFT calculations use one thread.

## Method

- Exact finite-cutoff even/odd convolutions use cosine and sine transforms.
  All phonon modes, patch weights, and the doubled Coulomb term are retained.
- The normal-state renormalization is summed analytically from the discrete
  kernel; nonlinear normal corrections use a cancellation-resistant ratio.
- A patch-scaled Newton–GMRES solve starts from the positive gap estimate.
  Step lengths preserve positive low-frequency gaps without forbidding
  high-frequency sign changes.
- Large frequency grids use local cubic interpolation for an inexpensive
  initial solve and approximate Jacobian inverse. Subsequent defect corrections
  evaluate the exact full-grid equations, not the interpolated equations.
- Final convergence uses the per-patch normalized residual. The returned `z`
  is evaluated at the returned gap.

## Validation

`validation.json` records seven public examples and three synthetic stress
cases derived from the public inputs. Every case passed residual, sign,
two-start agreement, and resource checks. Residuals were recomputed using the
supplied independent public operator.

Each measured invocation had a 12-second CPU limit and a 2048-MiB address-space
limit. Public examples used at most 0.42 CPU seconds. Stress cases with 40
patches and 32768 frequencies used at most 1.88 CPU seconds and 259 MiB peak
RSS. The largest checked gap residual was approximately `1.03e-12`.

Two-start checks are numerical branch-consistency checks, not comparisons to
unavailable hidden certificates. Hidden acceptance was not measured.

`isolation.json` contains only the error classes from the two required canary
file-open probes, in the requested order. Neither canary was readable.
