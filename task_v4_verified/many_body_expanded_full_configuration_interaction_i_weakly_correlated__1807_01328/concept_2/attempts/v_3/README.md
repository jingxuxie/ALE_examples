# Partial Hamiltonian witness

`witness.json` is the static submission artifact. It contains only schema version 1 and the two symmetric, zero-diagonal 7-by-7 VV control matrices.

**The complete task target was not achieved.** The artifact passes the nominal requirements, but the full-coefficient perturbation family remains below the required success count. No claim is made that a passing witness is impossible or that the unavailable hidden assay passes.

## Nominal diagnostics

| Quantity | Measured value | Required condition |
| --- | ---: | ---: |
| Maximum absolute triple increment | 0.698260457 microEh | <= 1 microEh |
| Missing third-order tail | 98.748470642 microEh | >= 50 microEh |
| Tail-to-parent ratio | 141.420682946 | >= 100 |
| Reference weight | 0.981111975126 | >= 0.95 |
| Paired-sector spectral gap | 0.785513599734 Eh | >= 0.4 Eh |
| Diagonal reference margin | 0.965714014654 Eh | >= 0.6 Eh |

## Recomputed finite assays

| Pool | VV successes | Full-coefficient successes | Required per family |
| --- | ---: | ---: | ---: |
| Supplied public pool | 61/64 | 3/64 | 61 |
| Additional pool, seed 419628 | 125/128 | 6/128 | 122 |

Both checker runs are numerically valid. They run with closed stdin, one BLAS thread, a 512 MiB address-space limit, a 60-second CPU limit, and a 90-second wall timeout. Independent nominal full-energy disagreement is 3.553e-15 Eh; independent gap disagreement is 7.994e-15 Eh.

## Artifact and records

- Artifact size: 2256 bytes; allowed maximum: 32768 bytes.
- SHA-256: `f994423a93abafdc059b50b68ba2269841baeed4b783e864517a42744202a19d`.
- Selected construction candidate: `sharpfull_000_probability.json`.
- `nominal_diagnostic.json`: complete nominal expansion and signed increments.
- `public_diagnostic.json` and `holdout_diagnostic.json`: trusted supplied-checker results.
- `verification.json`: schema, independent numerical checks, and resource measurements.
- `finalist_summary.json` and `pareto_comparison.json`: additional candidate-comparison pools.
- Search code, candidate artifacts, and all scratch logs remain in this directory. Only `witness.json` is evaluator input.

The search uses exact subsystem diagonalization, analytic energy derivatives, multistart constrained optimization, and independent finite perturbation checks. These results concern only the supplied seniority-zero effective model, not an ab initio molecule or a universal screening theorem.

## Reproduce the supplied diagnostic

From this output directory:

```sh
OPENBLAS_NUM_THREADS=1 python -B ../../adversary/ratchet_2/participant/workspace/check.py witness.json --report public_diagnostic.json
OPENBLAS_NUM_THREADS=1 python -B ../../adversary/ratchet_2/participant/workspace/check.py witness.json --seed 419628 --samples 128 --report holdout_diagnostic.json
```
