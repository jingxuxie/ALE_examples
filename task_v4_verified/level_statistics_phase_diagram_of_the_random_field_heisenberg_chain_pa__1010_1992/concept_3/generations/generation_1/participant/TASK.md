# C3: Falsify a spectral-center sampling proxy

## Mission

Find a robust finite-size counterexample to an author-defined spectral-sampling
proxy inspired by Pal–Huse, arXiv:1010.1992. **This proxy claim is not the
paper's claim.** Search for one generic, bounded twelve-site field profile;
do not submit a new estimator or change the Hamiltonian.

## Objective

For the periodic spin-1/2 Heisenberg chain in its complete zero-magnetization
sector, compare exact middle-rank-third gap statistics against an average
of three 128-level windows targeting energy densities 0.49, 0.50, and 0.51.
The same signed discrepancy must persist across four fixed perturbation
families. Required thresholds are core ≥0.060, worst-family mean ≥0.050,
base discrepancy ≥0.055, and at least six of eight members per family
with discrepancy ≥0.025. All admissibility constraints are mandatory.

## Assets

- `input/PROTOCOL.md`: authoritative model, claim, constraints, indexing,
  perturbations, acceptance rules, and evaluator interface.
- `input/protocol.json`: explicit public offsets and fixed targets.
- `workspace/exact.py`: public exact-diagonalization and scoring helper.
- `baseline/solve.py`: runnable unstructured search; produces `witness.json`
  by default but is not promised to pass.

## Interface

Submit only a static `witness.json` containing `schema_version`, twelve
`fields`, and one `orientation`. The evaluator recomputes every spectrum;
it never executes submission code or trusts claimed scores. It reports
scientific scores, validity, pass/fail, reasons, and measured resources.
Use the positional witness-file CLI documented in the protocol.

## Resources

The search allowance is 3,600 seconds, at most eight generator workers,
and one BLAS thread per worker. Evaluation uses 33 full 924-level spectra,
one worker, a 180-second wall limit, and a 2-GiB address-space ceiling.
No private search artifacts are required.
