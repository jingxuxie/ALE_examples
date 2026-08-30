# Five-parton kernel predictor

Run:

```sh
python3 predict.py INPUT.npz OUTPUT.npz
```

`predict.py` reads the `(N, 5, 4)` `p` array and writes only the float64
`log_weight` array. It locates `kernel.so` relative to its own location, so the
working directory and input/output paths can be arbitrary. No training data,
network access, or model fitting is required at inference.

## Implementation

The predictor directly evaluates the tree-level ordered vector current rather
than approximating it with a regressor. It uses Berends–Giele gluon currents,
two-component massless quark spinors, and a sum over physical linear gluon
polarizations. Shared one- and two-gluon currents are cached within each event.
The kernel is the sum of the spin-summed squared currents for gluon orderings
`(3, 4, 5)` and `(5, 4, 3)`, divided by 16. Charge conjugation permits the
second ordering to reuse the gluon currents with exchanged quark endpoints.

Pair invariants are calculated from differences of unit directions, avoiding
cancellation in nearly collinear configurations. Polarization axes are selected
to avoid coordinate-axis singularities. The implementation assumes the supplied
contract: massless momenta in the center-of-mass frame with total energy one.

The included shared library targets baseline x86-64, without AVX or other
machine-specific requirements. Rebuild it using the supplied C++ source:

```sh
sh build.sh
```

## Local validation

All 25,000 training events and 1,500 validation events match their supplied
labels to numerical precision. Validation log-RMSE is `1.72e-13`; the worst
validation family log-RMSE is `3.81e-13`. Every prediction is within 15% relative
error.

A 200,000-event benchmark repeats and shuffles the training events and applies
independent azimuthal rotations, which preserve the labels. The complete
prediction subprocess is pinned to one CPU and limited to 3 GiB address space.
Measured CPU times, including Python startup and NPZ input/output, were 1.01 s
for uncompressed input and 1.45 s for compressed input. Both runs have log-RMSE
`2.12e-13` and 100% of predictions within 15% relative error. These are local
measurements, not results on hidden data.

Reproduce accuracy and production-size timing checks with:

```sh
python3 validate.py /path/to/train.npz /path/to/validation.npz --benchmark 200000
```
