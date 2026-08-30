# Measured results

The submission is the root directory containing `solve.py` and
`local_solver.so`. No hidden evaluator, hidden cases, or official reference
energies were available. These results are local numerical checks, not a claim
about the hidden score.

## Final validation

- All 15 short-budget cold-start cases passed the public MPS contractor and
  resource checks. Maximum CPU time: **5.594 s** against 6 s; maximum wall time:
  **5.889 s** against 30 s.
- All 14 long-budget cold-start cases passed. Maximum CPU time: **36.802 s**
  against 40 s; maximum wall time: **37.594 s** against 120 s.
- Three additional cutoff-induced parity-inversion checks passed at the short
  budget. In that example, the unrestricted solver correctly selected an odd
  ground state rather than imposing even parity.
- Peak measured resident memory across the main suite was **71,720 KiB**, well
  below the 2 GiB address-space limit. The launcher also enforced the address
  space and 8 MiB output-file limits.
- Two dense local-eigensolver checks, sixteen additional shuffled-charge and
  odd-dimension checks, and complete four-site dense comparisons in unrestricted,
  even, and odd sectors all passed. The complete-chain energy errors were below
  `1e-12`.

Machine-readable final records are `experiments/validation_short.json`,
`experiments/validation_long.json`, and `experiments/inversion_checks.json`.
The cases include all three provided examples, independent 64-site tests,
nonuniform fields/couplings, strong cutoff effects, and odd bond/physical
dimensions. Earlier exploratory logs are not final validation records.

## Public-example energies

Every energy is recomputed from an actual MPS using the public Hamiltonian.
Baseline figures come from local runs of the supplied frozen optimizer. Those
baseline development runs exclude imports from their optimization clocks,
whereas the submission CPU figures below include interpreter/import and output
costs. They are not official evaluator baseline measurements.

### Six-second budget

| Example | Baseline energy | Submission energy | Submission CPU (s) |
| --- | ---: | ---: | ---: |
| Zero field | 24.623219821008 | 24.617014340508 | 3.203 |
| Odd sector | 31.151222843472 | 31.151094491318 | 5.468 |
| Nonuniform | 24.348109931008 | 24.340940332792 | 2.769 |

### Forty-second budget

| Example | Baseline energy | Submission energy | Submission CPU (s) |
| --- | ---: | ---: | ---: |
| Zero field | 24.617014340529 | 24.617014340508 | 2.867 |
| Odd sector | 31.151095077724 | 31.151094488672 | 8.242 |
| Nonuniform | 24.340940332905 | 24.340940332792 | 2.794 |

The independent 64-site, dimension-14, cap-24 even test reached energy
`48.000145790022` in 36.802 CPU seconds, agreeing with a longer variational run
to numerical precision. Other large odd and nonuniform tests also agreed with
longer runs; these are variational comparisons, not exact-energy certificates.

## Sample artifact

`example_state.npz` is the actual 48-site odd-sector public-example output from
the final long-budget validation. Its matching request is `example_request.json`.
Recomputation gives energy `31.151094488671625`, parity `-1`, and maximum bond
dimension `20`.

```sh
python contractor.py --request example_request.json --state example_state.npz
```

The solver never loads this sample. It generates a fresh state for every
request. Intermediate experimental NPZ files were removed to keep the complete
submission comfortably within the 16 MiB package limit.

## Budget fixes

Cold-start checks exposed output/finalization overhead that was absent from
warm optimizer timings. The final implementation reserves 0.6 CPU seconds,
buffers the uncompressed archive before a single file write, disables cyclic
collection during serialization, and exits only after the file is closed.
All final resource results above include those costs.
