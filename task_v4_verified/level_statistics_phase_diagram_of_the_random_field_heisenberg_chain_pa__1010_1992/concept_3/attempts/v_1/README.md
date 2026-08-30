# Static counterexample

The submission is `witness.json`, a 358-byte static JSON object with exactly
the three required keys. Its orientation is `-1`: the proxy underestimates
the middle-rank-third adjacent-gap statistic.

The supplied public exact scorer verifies all acceptance checks:

| Quantity | Measured | Required |
|---|---:|---:|
| Core | 0.063975506403764 | 0.060 |
| Worst-family mean | 0.057290358878778 | 0.050 |
| Base signed discrepancy | 0.072371283310220 | 0.055 |
| Members above floor, by family | 8, 8, 7, 7 | 6 each |

Every field and spectrum constraint passes. The smallest gap across all
33 spectra is 0.0000216953846639. The `evr` validation takes 3.81 seconds
with one worker, one BLAS thread, and a 2-GiB address-space limit.

## Reproduction

Run from this directory; the scripts read the original participant assets.

```bash
mkdir -p structured
python -B structured.py --seed 8131979 --candidates 6144 --partial 1024 --finalists 256 --output structured
python -B gradient.py --input structured/finalists.json --starts 4 --evaluations 100 --iterations 80
cp passing.json witness.json
python -B validate.py witness.json --output validation.json
python -B validate.py witness.json --driver evd --output validation-evd.json
```

The search uses at most eight workers, with one BLAS thread per worker.
Gradients guide field selection only; final certification recomputes the
unchanged protocol using full eigenvalue-only spectra. Both validation
drivers pass, with a maximum member-discrepancy difference below 2.4e-13.
`validation.json` records the public-helper result, not an independently
executed private evaluator report. Only `witness.json` is submitted.

This is a finite-size counterexample to the task-defined proxy claim,
not a refutation of the Pal–Huse paper.
