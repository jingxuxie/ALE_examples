# Ordered five-parton scalar kernel

Run `python3 predict.py INPUT.npz OUTPUT.npz`.

The predictor reads only the authoritative normalized pair invariants `s`.
It reconstructs a bounded-boost representative using the rest frame of the
largest-invariant pair, with extended precision for the Gram reconstruction.
It evaluates the color-ordered tree current using Berends–Giele recursion,
sums physical gluon polarizations and quark helicities, and averages the two
quark/antiquark orderings with the normalization verified against the supplied
native labels. All propagator denominators use the supplied invariants directly.
No fitted parameters, training data, or frame-dependent momentum operations
are used at inference.

`kernel.so` is the precompiled C++ implementation. To rebuild on a compatible
Linux system, run:

```
g++ -O3 -std=c++17 -fPIC -shared -fno-math-errno -fno-trapping-math -fcx-limited-range kernel.cpp -o kernel.so
```

Python 3 and NumPy are the only Python dependencies. Compilation is not part of
inference. `check.py` validates against the supplied labelled datasets when
the `DATA` environment variable names their directory.

The supplied 6,000-event frame validation set passes every phase/frame group,
with log-RMSE approximately `5.1e-12` overall and 100% relative-error coverage
at `1e-8`. A 200,000-event end-to-end local benchmark, including compressed
input, Python startup, and output, is below the 2.4-second CPU limit.

`stress.py` additionally checks invariant reconstruction against original
momenta on 250,000 independently sampled physical events. This is a numerical
self-consistency test, not a substitute for native-label validation.
