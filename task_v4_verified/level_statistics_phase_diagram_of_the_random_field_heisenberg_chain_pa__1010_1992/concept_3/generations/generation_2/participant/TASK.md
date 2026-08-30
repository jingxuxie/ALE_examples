# C3 generation 2: independent-replication counterexample

## Mission

Find a robust finite-size counterexample to an author-defined spectral-center
sampling claim inspired by Pal–Huse, arXiv:1010.1992. **The proxy claim is not
the paper's claim.** Submit one generic, bounded twelve-site field profile,
not an estimator, executable solution, or modified Hamiltonian.

## Objective

Compare the exact middle-rank-third adjacent-gap ratio against an average
of three 128-level windows targeting energy densities 0.49, 0.50, and 0.51.
The signed mismatch must replicate across four perturbation families, with
32 members each. Acceptance requires core ≥0.060, worst-family mean ≥0.050,
base discrepancy ≥0.055, and at least 24/32 members in every family with
discrepancy ≥0.025. Every field and spectrum constraint remains mandatory.

The public calibration bank and private grading bank are **different**
independent draws from the same fully disclosed generator law. A public
calibration pass is not a grading pass. Private cases are fixed before
evaluation and bound to a published SHA-256 commitment.

## Assets

- `input/PROTOCOL.md`: authoritative physics, claim, constraints, replication
  law, indexing, acceptance criteria, and interface.
- `input/protocol.json`: 128 public offsets and their reproducible seed.
- `input/commitment.json`: commitment to the separate private bank.
- `workspace/exact.py`: exact public-calibration scoring helper.
- `baseline/solve.py`: original unstructured search, producing `witness.json`.

## Interface And Resources

Submit static JSON containing only `schema_version`, twelve `fields`, and one
`orientation`. The evaluator accepts a positional witness-file path, executes
no submission code, verifies its commitment, and reports scores, validity,
pass/fail, reasons, and resources without revealing private offsets.

Search allowance: 3,600 seconds, at most eight workers, one BLAS thread each.
Evaluation: 129 full 924-level spectra, one worker, 180 seconds, and a 2-GiB
address-space ceiling. Only participant assets are supplied to the solver.
