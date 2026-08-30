# Connected detector calibration submission

Run the JSON-lines worker with:

```sh
/usr/bin/python3 /submission/solution.py
```

Keep `kernel.so` and `kernel_avx2.so` beside `solution.py`. The portable library
checks processor features before the worker selects the AVX2 implementation.
NumPy and SciPy are the only Python dependencies. The worker does not read
training episodes or any external data files.

## Method

- Preserve the full sparse observation histograms with 64-bit syndrome codes.
- Fit exact local XOR-projection distributions, including alternate footprints
  and the two shared-mode components, using Walsh transforms and analytic gradients.
- Use a pilot and two adaptive allocation stages. Rate-dependent Fisher information
  balances family errors while respecting both the shot and query budgets.
- Refine with a normalized local-conditional approximation to each mode's joint
  syndrome distribution, then marginalize one shared mode for the entire shot.
  The local distributions are exact; the large-graph conditional factorization
  is an approximation, not an independence claim about overlapping marginals.
- Average a bounded Gaussian posterior approximation in log-rate coordinates.

The final refinement uses up to 13 detector bits per local block. CPU deadlines
leave room for posterior averaging and the final protocol response.

## Native build

The libraries are supplied prebuilt. Rebuild from the included source if needed:

```sh
g++ -O3 -march=x86-64 -ffast-math -fPIC -shared kernel.cpp -o kernel.so
g++ -O3 -march=x86-64 -mavx2 -mpopcnt -mfma -ffast-math -fPIC -shared kernel.cpp -o kernel_avx2.so
```

## Validation

`validation_summary.json` records development results, resource measurements,
and submission hashes. These are public/local checks, not hidden-suite certification.
The tests compare native probabilities and derivatives against the supplied exact
parity law and check the joint-likelihood gradient against finite differences.
The protocol tests use the provided `input/local.py`, with an additional local
60-second CPU and 3-GiB address-space limit.

Final local results (mean / worst regime-family log RMSE):

| Suite | Episodes | Mean | Worst |
| --- | ---: | ---: | ---: |
| Public protocol | 6 | 0.05951 | 0.07243 |
| Fresh randomized rates | 24 | 0.06168 | 0.08188 |

The maximum measured CPU time is 22.24 seconds, including the portable-kernel
check. Maximum observed RSS is 137.3 MiB. Runs use 40,000 shots and at most
58 queries. A separate 24-episode development randomized suite also meets the
declared accuracy targets.

With `PART` set to the absolute participant directory, run from this directory:

```sh
/usr/bin/python3 test_kernel.py
/usr/bin/python3 experiment.py --episode 5 --seed 201 --random-rates --limit --output result.json
```
