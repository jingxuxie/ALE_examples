# Detector calibration submission

Run the JSON-lines worker with:

```sh
/usr/bin/python3 /submission/solution.py
```

Keep `kernel.so` and `kernel_avx2.so` next to `solution.py`. The worker selects
the AVX2 implementation only when the processor supports all required features;
`kernel.so` is the portable x86-64 implementation. NumPy and SciPy are the only
Python dependencies.

The estimator marginalizes the shared shot mode and channel footprint choices.
It evaluates exact XOR-projection likelihoods using Walsh transforms, allocates
shots using rate-dependent Fisher information, and refines informative actions
against their full detector distributions. Bounded Gaussian posterior averaging
accounts for published rate bounds. All experimental choices depend only on
the public specification and returned syndrome histograms.

The native libraries are supplied prebuilt. To rebuild them from `kernel.cpp`:

```sh
g++ -O3 -march=x86-64 -ffast-math -fPIC -shared kernel.cpp -o kernel.so
g++ -O3 -march=x86-64 -mavx2 -mpopcnt -mfma -ffast-math -fPIC -shared kernel.cpp -o kernel_avx2.so
```

Development checks compare the native probabilities and gradients with the
provided exact parity helper, exercise the supplied JSON-lines tester, and
run independently randomized rates and synthetic 20-detector stress cases.
These are local checks, not hidden-suite certification.

`validation.json` contains aggregate recovery metrics, resource observations,
and submission hashes. `development/results/` holds the underlying reports.
From this directory, the checks can be reproduced with `P` set to the absolute
participant directory:

```sh
export P=/absolute/path/to/participant
/usr/bin/python3 development/test_kernel.py
/usr/bin/python3 development/experiment.py --episode 5 --seed 4 --random-rates --limit
/usr/bin/python3 development/summarize.py
```
