# Invariant five-parton kernel

Run the supplied, already-built predictor:

```sh
python3 predict.py INPUT.npz OUTPUT.npz
```

Only `s` is read. The output contains one float64 array, `log_weight`, in input
order. There are no fitted model parameters, training-data dependencies, network
requests, runtime compilation, or worker processes. Python 3 and NumPy are
required. `kernel.so` is the included Linux x86-64 native library.

## Calculation

The implementation evaluates the color-ordered tree current for a vector source
decaying to a quark, antiquark, and three gluons. It includes ordered three- and
four-gluon currents and all positions of the vector vertex on the fermion line.
Eight real gluon polarization combinations are summed using two-component Weyl
spinors. Parity supplies the second quark helicity. The two opposite endpoint
orderings give the reversal pair with the normalization checked against the
source-native labels.

Authoritative invariants determine a well-conditioned internal dipole frame.
The largest pair invariant selects the two light-cone axes, and the largest
transverse radius selects an azimuthal reference. Reconstruction uses extended
precision. Every propagator denominator is calculated directly from the supplied
invariants, not from reconstructed or input four-momenta. Thus rounded boosted
momenta cannot affect the answer. Internal spinor and polarization charts avoid
coordinate-axis singularities.

## Build and validation

Rebuilding is optional:

```sh
sh build.sh
```

The build uses ordinary x86-64 instructions and does not enable unsafe fast-math
transformations. Local validation can be repeated with:

```sh
OPENBLAS_NUM_THREADS=1 python3 stress.py
python3 check_submission.py /path/to/participant/input
rm -f _stress.npz
```

`stress.py` generates independent physical momenta and checks reconstruction
against direct-momentum evaluation. It is a numerical consistency test, not an
additional native-label oracle. `check_submission.py` evaluates all provided
labels, then times three complete 200,000-event prediction processes using a
compressed input, one pinned CPU, and a 3 GiB address-space limit.

Results of the final local validation:

| Check | Result |
| --- | ---: |
| 25,000 training events: log-RMSE | 2.22e-12 |
| 1,500 validation events: log-RMSE | 3.44e-13 |
| 6,000 frame-validation events: log-RMSE | 3.44e-13 |
| Worst frame-validation phase/frame RMSE | 7.62e-13 |
| Relative-error coverage at 1e-8, all labelled files | 100% |
| 200,000-event complete-process CPU, three runs | 1.31–1.53 seconds |

All twenty supplied phase/frame groups pass the requested accuracy thresholds.
The timing includes Python startup, compressed input loading, native evaluation,
and output writing. These are local measurements, not hidden-evaluator results.
