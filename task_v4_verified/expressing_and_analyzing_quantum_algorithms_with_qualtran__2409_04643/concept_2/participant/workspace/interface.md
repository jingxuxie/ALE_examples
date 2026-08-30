# Executable contract

Submit `counterexample.json` containing exactly `{"P": [...], "H": [...]}`.
Each array is an ascending-power coefficient list; each complex coefficient is
`[real, imaginary]`. JSON numbers are interpreted as finite binary64 values.
Booleans, duplicate object keys, nonfinite numbers, extra fields and symlink
artifacts are rejected. Both arrays must have the same length.

## Admissibility

- P has degree 8 through 12 inclusive.
- Its coefficient energy E = sum |P[k]|² is between 0.08 and 0.30.
- Every coefficient magnitude is between 0.25 and 4 times sqrt(E/(degree+1)).
- |sum P[k]²| <= 0.8 E, excluding real polynomials up to a common phase.
- H certifies strict whole-circle contractivity: the exact binary64 polynomial
  |P(z)|² + |H(z)|² differs from 16/25 by at most 1e-12 on |z|=1, as certified
  by the coefficient bound described below. Thus |P|² <= 0.640000000001.
- Every submitted real or imaginary component has magnitude at most 2.

For polynomials A,B, form the autocorrelation coefficients of |A|²+|B|².
The certificate bound for target constant c is
`abs(r[0]-c) + 2*sum(abs(real(r[k])) + abs(imag(r[k])))` for k>0.
The checker computes these coefficients exactly as dyadic integers/rationals,
not on a sampled grid. H is only a certificate; the compiler never uses it.

## Method and witness

`target_method.py` freezes the supplied numerical route: Qualtran's FFT
complement routine with tolerance zero, followed by its binary64 phase-factor
extraction. This route is NOT the library's default root-based constructor.
Use the supplied code, including its padding and Fourier cutoff conventions.
No claim is made that all Qualtran compilation routes behave identically.

The six configurations are the Cartesian product of `num_modes` = 4096, 8192,
16384 and these two coefficient gauges:

1. P[k] unchanged.
2. P[k] multiplied in binary64 by exp(i*(0.3125 + 0.2718281828459045*k)).

For each transformed P, recompute Q using the frozen FFT method. The exact
autocorrelation certificate for |P|²+|Q|² must be <=1e-12 relative to 1.
At every descending phase-extraction stage with leading coefficients a,b,
both |b| and |a*conj(b)| must be >=1e-8. This excludes near-zero branch guards.
Nonfinite results, inaccurate complements and exceptions are not witnesses.

The returned circuit is R_d diag(z,1) ... R_1 diag(z,1) R_0. R_0 uses the
returned lambda; every other rotation uses lambda zero. The rotation convention
is given by `rotation_matrix` in the supplied method. The evaluator independently
expands its first column using 80-decimal-digit arithmetic on the returned
binary64 angles. Its error is the coefficient L2 norm of the difference from
the joint target first column [P,Q], minimized over one common unit-modulus
phase. By Parseval this is continuous-circle RMS vector-amplitude error, not
an error measured at a finite set of signal values. Top-block-only error is also
reported, but the witness condition concerns the complete first-column contract.

All six errors must be >=0.05. Core and worst-configuration scores are
`min(1, min_error/0.05)` when every admissibility condition holds, otherwise zero.
Only a score of 1 passes. The 60-second evaluator never executes submitted code.
Python, NumPy and mpmath are available. Construction gets one hour, four CPU
threads and 8 GiB memory; the artifact limit is 64 KiB.

```
python3 baseline/solve.py --output /YOUR_OUTPUT/counterexample.json
python3 workspace/probe.py --submission /YOUR_OUTPUT
```

The public probe has the full deterministic scoring semantics. The private
evaluator uses immutable copies and adversarial parser/independent numerical
validation tests; there is no hidden reference answer.
