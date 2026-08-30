# Branch-correct Eliashberg solver

Run the self-contained submission with:

```sh
python solve.py --input FILE --output FILE
```

The output NPZ contains only float64 `delta` and `z` arrays. The solver uses
single-threaded NumPy/SciPy and does not require the supplied helper module.

## Numerical method

- Exact finite-cutoff even/odd convolutions use padded cosine/sine transforms.
  Mode interactions are combined in transform space before nonlinear iteration.
- Damped self-consistency provides a positive-branch starting point.
- Analytic Newton corrections use GMRES with separate patch scales, preserving
  sensitivity to tiny induced gaps.
- Step lengths preserve positive first-frequency gaps. Both the normalized
  residual and the relative Newton correction control termination, resolving
  the amplitude near the superconducting transition.

No frequency truncation, interpolation, tail correction, or modified physics
is used.

## Validation

Reproduce the public and enlarged-instance checks with:

```sh
python validate.py --input "$ALE_PUBLIC_INPUT" --output validation.json
```

`validation.json` records direct-sum residuals and two-start agreement for all
five public examples, plus checks enlarged to 25 patches and 2048 frequencies.
Near-critical enlarged cases have leading normal-state pairing eigenvalue
1.00002. Public normalized gap residuals are below 1e-14, and two-start
distances are below 4e-12.

`stress_validation.json` records additional perturbed combined cases and a
five-band test with several nearly critical bands and weak induced gaps.
Their direct residuals are below 4e-15 and two-start distances below 9e-12.
Non-power-of-two frequency counts were also compared against the supplied
operator.

`resource_validation.json` records a fresh 25-by-2048 five-band CLI execution
under hard limits of 12 CPU seconds and 2048 MiB address space: 2.63 CPU seconds
including imports and approximately 94 MiB peak resident memory.

These are public and locally constructed checks, not hidden-instance scores.
`isolation.json` records the two required file-open probe error classes.
