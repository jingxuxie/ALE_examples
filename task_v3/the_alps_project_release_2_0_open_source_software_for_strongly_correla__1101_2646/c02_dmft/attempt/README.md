# DMFT integration adapter

The submitted entry point is the self-contained `solve.py`. It requires Python,
NumPy, and SciPy, and neither imports sibling files nor assumes a working
directory.

```sh
python solve.py --input /path/to/input.json --output /path/to/output.json
```

## Numerical implementation

- Fourier: subtract all three supplied high-frequency moments, sum both
  fermionic frequency signs through the real-part identity, restore the
  analytic time tail, and enforce `G(beta-) = -c1 - G(0+)`. Every channel is
  active, including channels whose three moments vanish. The forward diagnostic
  subtracts the same time tail and uses only the left endpoints.
- AFM: calculate the scalar self-energy, integrate the supplied discrete DOS
  exactly for each adjacent flavor pair, and update all bands without mixing.
  Each band's measure and second moment remain attached to its two flavors.
  Return the lattice, Weiss, hybridization, and tail-aware Weiss time data.
- Legendre: use `matrix[j][i]`, distinguish the configuration sign from the
  antiperiodic wrap sign, divide by the signed statistical weight, and include
  `sqrt(2*l+1)` exactly once in the measured coefficients. Reconstruct only the
  finite polynomial, using the analytic integral
  `T[n,l] = (-1)^n i^(l+1) sqrt(2*l+1) j_l((n+1/2)*pi)`.
  The spherical Bessel function evaluates this integral without time-grid
  discretization; `Sigma` is the reconstructed `F/G`.

Intermediate algebra and summation use NumPy extended precision to reduce
tail-cancellation error. SciPy evaluates the spherical Bessel functions in
double precision. Outputs are standard finite JSON real numbers, with complex
numbers encoded as `[real, imaginary]`.

## Verification

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m unittest -v test_solve
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python validate.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python check_precision.py
```

The unit tests cover independent scalar Fourier and AFM calculations,
Gauss-Legendre quadrature of reconstructed polynomials, zero-tail channels,
minimum and maximum grid sizes, all twelve flavors, DOS and pair permutations,
the atomic limit, signed cancellation, equal-time events, empty configurations,
finite truncation, and beta scaling. The CLI test copies only `solve.py` into a
temporary directory under this attempt directory and runs from another working
directory, checking both supplied samples and a maximum-size AFM input.

`validate.py` checks another 224 reproducible randomized cases and records
component errors and numerical-kernel timings in `validation_report.json`.
The independent reference calculations are in `test_solve.py`; no supplied
sample is treated as a labeled answer.

`check_precision.py` independently constructs the Legendre frequency kernel
with 120-digit decimal arithmetic and exact half-integer-pi sine/cosine values.
It checks the special-function kernel and reconstructed ratios separately from
quadrature errors; its results are in `precision_report.json`.
