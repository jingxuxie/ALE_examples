# Connected detector calibration submission

Run the worker with:

```sh
/usr/bin/python3 solution.py
```

Keep `kernel.so` and `kernel_avx2.so` beside `solution.py`. The worker uses only
the supplied JSON-lines specification and observations. NumPy and SciPy are
the Python dependencies. No compiler, training data, network, or subprocess is
needed at runtime.

## Method

- A pilot probes the sector controls and a middle rare-channel gain.
- Three allocation rounds optimize approximate family-balanced Fisher
  information while explicitly respecting the query and shot limits.
- Exact Walsh-transform likelihoods integrate both the shared mode and the
  alternate footprint choices. Local overlapping projections handle the large
  connected graphs; sparse low-exposure experiments use global XOR hashes.
- The final conditional composite likelihood uses distant detector projections
  to inform the shared mode. A channel-support exclusion makes the local and
  distant projections independent conditional on that mode; no independence
  between overlapping local likelihood terms is assumed in the observation law.
- Bounded multivariate Gaussian posterior averaging incorporates the published
  rate intervals. The reported parameters are positive intensity rates.

The native Fourier kernel extends the provided reference kernel. Its baseline
build is portable x86-64; the worker selects the AVX2 build only after checking
the processor features. Rebuild with:

```sh
g++ -O3 -march=x86-64 -fPIC -shared kernel.cpp -o kernel.so
g++ -O3 -march=x86-64 -mavx2 -mpopcnt -mfma -fPIC -shared kernel.cpp -o kernel_avx2.so
```

## Validation

`validation.json` records public recovery, independent randomized-rate checks,
and locally observed CPU and memory use. These are development results, not
trusted hidden-suite qualification. The development directory contains the
test scripts and reports. The exact-law test checks normalization, selected
parities and derivatives against the supplied moment helper, and conditional
likelihoods against a full enumerated distribution.
