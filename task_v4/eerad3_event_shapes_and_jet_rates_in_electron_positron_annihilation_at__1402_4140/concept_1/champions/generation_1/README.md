# Five-parton kernel predictor

Run from any working directory:

```sh
python3 /path/to/submission/predict.py INPUT.npz OUTPUT.npz
```

The input supplies `p` with shape `(N, 5, 4)` and `s` with shape `(N, 10)` as
specified in the task contract. The output contains only `log_weight`, a finite
float64 array of shape `(N,)`. Neither labels nor family identifiers are used.
There are no training-data files, fitted parameters, or network dependencies.

## Method

This is a compact numerical tree-amplitude evaluator rather than a regression
approximation. It constructs color-ordered gluon currents with the cubic and
quartic Yang--Mills vertices. Left and right quark currents recursively collect
all contiguous gluon partitions, and the vector current is inserted at each
of the four possible splits. The calculation sums two transverse polarizations
per gluon, both quark spin states, and three spatial vector-current components
in the specified center-of-mass frame.

The two contributions have orders `(1,3,4,5,2)` and `(2,3,4,5,1)`. In the
implementation's vertex conventions, the native kernel is their sum divided
by 16. This normalization and the current construction agree with every
supplied label to numerical precision.

Fermion spinors are applied before squaring, so the spin sum is a sum of
nonnegative squared amplitudes rather than a cancellation-prone Dirac trace.
Propagator denominators use sums of the supplied invariants instead of
subtracting nearly equal squared energies and momenta. These choices preserve
accuracy in the unresolved families.

## Build and dependencies

`predict.py` requires Python 3 and NumPy. The included `kernel.so` is a
single-threaded x86-64 Linux shared library with no model dependencies.
Its complete source is `kernel.cpp`. Rebuild with:

```sh
g++ -std=c++17 -O3 -DNDEBUG -fPIC -shared kernel.cpp -o kernel.so
```

The wrapper also runs this build if `kernel.so` is missing. No compilation is
needed when using the supplied library.

## Local validation

The supplied 25,000 training events and 1,500 validation events were evaluated
without fitting. Detailed measurements are in `validation_metrics.json`.

| Metric | Training | Validation |
| --- | ---: | ---: |
| Overall log-RMSE | 3.11e-13 | 2.75e-13 |
| Worst-family log-RMSE | 6.89e-13 | 6.14e-13 |
| Maximum absolute log error | 2.16e-11 | 8.96e-12 |
| Within 15% relative error | 100% | 100% |
| Kernel evaluation time | 1.18 s | 0.082 s |

Times are local single-thread measurements, excluding Python startup and file
I/O. Held-out labels are unavailable, so these are supplied-data results only.

The executable interface also passed checks with empty, singleton, and full
validation inputs from an unrelated working directory, without labels or family
identifiers. These subprocesses were restricted to one CPU, 3 GiB of address
space, and 90 CPU seconds. The 1,500-event CLI run took 1.13 seconds including
startup and I/O; maximum child resident memory was approximately 32 MiB.
Rotation, quark/antiquark interchange, and gluon-order reversal checks also
preserved predictions to numerical precision.
