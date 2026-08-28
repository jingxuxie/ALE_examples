# Scalar checkpoint executor

Run with the supplied interpreter:

```sh
ALE_INPUT_DIR=/path/to/participant/input /path/to/participant/input/runtime/bin/python3.12 solve.py INPUT.npz OUTPUT.npz
```

`solve.py` and `fast_transport.py` are the required implementation files. All three checkpoints, native and transferred profiles, scalar and row-aligned couplings, and probe/forward/reverse operations are implemented. The NPZ keys, shapes, and float64 output contract are unchanged.

Inference contracts the complete trained tensors and uses periodic FFT correlations. Divergence is the exact zero-displacement Jacobian trace. Conditional derivatives differentiate normalized Gaussian weights and their occurrences in all three trained tensors. Kernel transfer explicitly splits source edge taps and preserves integer displacements, including at even target extents.

Transport uses 100 classical RK4 steps and accumulates density changes independently of the initial log density. Temporal Fourier kernels are prepared once. Larger cases use a CPU JAX loop with double-precision, range-reduced sine/cosine polynomials accurate to roundoff; unusually large arguments use the standard trigonometric functions. Small cases avoid JIT overhead. No features, parameters, or spatial taps are dropped; no stochastic traces or stored case answers are used.

`validate.py` provides independent contractions and FFT/direct-correlation checks, conditional finite differences, boundary and midpoint couplings, odd/even transfers, displacement-resolved impulses, row independence, absolute RK4 comparisons, and an NPZ subprocess test against an exactly integrable zero field. Run it with the same interpreter and `ALE_INPUT_DIR`; its latest output is in `validation.log`.

No public-contract numerical components are unimplemented.
