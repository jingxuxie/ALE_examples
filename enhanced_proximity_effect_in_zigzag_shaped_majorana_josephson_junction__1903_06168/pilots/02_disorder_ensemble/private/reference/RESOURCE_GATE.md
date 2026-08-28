# Full-size source-side replay

## Conclusion

The first archived value is supported by independent numerical eigenpairs of the
actual **124,800-DOF** source Hamiltonian. There is no confirmed source/model or
archive-mapping mismatch. However, neither tested minimization returned a normal
result file: both stopped at an absolute eigenpair-residual guard during local
refinement. **A completed executable reference under 600 seconds remains
unvalidated.** Do not use the archived lookup as runtime proof, and do not present
this guard failure as evidence of inherent numerical difficulty.

Only this directory was edited. No participant, evaluator, attempt, other pilot,
or source files were changed. No fresh agents were launched, and no participant
outputs were used as reference values.

## Independent source validation

`validate_fullsize_source.py` checks the visible snapshot byte-for-byte against
`e3a750a^`, then independently constructs the source `e3a750a` system using its
native Hamiltonian substitutions and disorder functions. The source/reference
matrices agree exactly at Bloch phases 0, 0.713, and pi, including all lattice
tags, 124,800 orbitals, and 836,160 nonzeros. Hermiticity error is zero.

The source and private calibration both give **16.31897623893178 meV**; the random
potential agrees at every site. Independent archive indexing selects index 24672
of 98,400, whose stored gap is **0.22934536743383552 meV**. Full details and the
archive checksum are in `fullsize_source_validation.json`. MUMPS is unavailable.

## Computation and timings

The private solver now supports explicit `splu(MMD_AT_PLUS_A)` shift-invert,
single-threaded execution, a configurable pivot threshold, residual checks, and
phase-by-phase timing logs. Disabling pivoting and enabling symmetric mode greatly
reduces fill. The factor has 19,829,132 nonzeros. Source Bloch-harmonic matrix reuse
is checked against a separately assembled phase, with maximum error 1.78e-15.
The eigensolver uses mixed warm starts; no archive values enter this computation.

- MMD with normal pivoting: timed out after 360 seconds without completing one
  factorization. This is separate from the previously reported COLAMD timeout.
- Symmetric MMD, zero-phase witness: 8.72 s preparation, 0.90 s assembly, 3.96 s
  factorization, 7.66 s eigensolve; 21.26 s overall. Energy 0.22966152469183937 meV;
  eigenpair residuals at most 1.70e-10. This is **not** the global gap.
- Full 31-point grid plus source-style `fmin`: all 31 grid phases completed.
  At elapsed 541.23 s, phase 2.646628186032026 produced
  **0.22934536743378847 meV**, differing from the archive by about 4.7e-14 meV;
  residuals were at most 1.28e-8. The next refinement evaluation exceeded the
  1e-7 absolute residual guard and exited nonzero. No completed gap result exists.
- Nine-point grid plus bounded local refinement: at elapsed 195.31 s, phase
  2.6466777043272485 produced **0.22934536743399894 meV**, differing by about
  1.64e-13 meV, with residuals at most 7.49e-8. The next evaluation exceeded the
  same guard and exited nonzero. This was **not** a 31-point replay and did not
  return a completed search result.

Both search processes had a 12-GiB address-space cap; reported peak RSS was about
600 MiB. Typical completed phases take roughly 11–15 seconds. Machine-readable
totals, all phase data, and the distinction between witnesses and completed
minimizations are in `resource_gate_report.json` and the `mmd_*_trace.jsonl` files.

The residual threshold was an author-side safety check, not an evaluator rule.
Its failure does not establish an inaccurate scalar eigenvalue or a fundamental
resource obstruction. A possible next numerical improvement is residual-driven
subspace/inverse-iteration refinement before rejecting a phase. That improvement
has **not** been implemented or validated here. No production or acceptance claim
is made. Only the first archived case was checked; nothing here proves accuracy
or runtime across the full disorder ensemble.

## Commands

Run from this reference directory. All generated outputs stay here.

```sh
PYTHONDONTWRITEBYTECODE=1 python validate_fullsize_source.py --input spot_request.json --output fullsize_source_validation.json
PYTHONDONTWRITEBYTECODE=1 timeout 360 python solve.py --input spot_request.json --output mmd_zero_witness.json --witness-phase 0 --pivot-threshold 1 --trace mmd_zero_trace.jsonl
PYTHONDONTWRITEBYTECODE=1 timeout 360 python solve.py --input spot_request.json --output mmd_symmetric_zero_witness.json --witness-phase 0 --pivot-threshold 0 --trace mmd_symmetric_zero_trace.jsonl
PYTHONDONTWRITEBYTECODE=1 timeout 600 python solve.py --input spot_request.json --output mmd_full_spot.json --grid-points 31 --refinement fmin --trace mmd_full_trace.jsonl
PYTHONDONTWRITEBYTECODE=1 timeout 360 python solve.py --input spot_request.json --output mmd_bounded_spot.json --grid-points 9 --refinement bounded --trace mmd_bounded_trace.jsonl
PYTHONDONTWRITEBYTECODE=1 python summarize_benchmark.py --full-exit-code 1 --pivoted-exit-code 124 --bounded-exit-code 1
```

The initial zero-phase timings predate Bloch-matrix caching and the explicit
address-space cap; a rerun with the final script has that extra setup. The two
full searches include both. `--stored` remains available, but labels its output
`offline_author_archive_lookup` and prints an explicit warning: it is author-side
offline data retrieval, **not** a numerical replay or runtime validation.
