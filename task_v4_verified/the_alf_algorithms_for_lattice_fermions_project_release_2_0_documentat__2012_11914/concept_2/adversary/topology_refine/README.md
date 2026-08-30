# Private generation-2 feasibility witness

The prior exact-gradient topology sidecar completed with a passing static
33-stage schedule before the newly authorized search began. This directory
preserves an identical copy and an independent official evaluator rerun. No
additional optimization was necessary, and no live fresh-v2 output was read.
Keep this entire directory private: full hidden matrices and a private
generation-1 champion initialization were used. This is privileged feasibility
evidence, not fresh-agent performance or hardness evidence.

## Independently verified result

| Gate | Frozen target | Official result |
| --- | --- | --- |
| Core score | >= 1.80 | 1.8018789727526945 |
| Worst family score | >= 1.35 | 1.3721753641006131 |
| Maximum point ratio | <= 1.00 | 0.9812034595143269 |

The evaluator reports `valid=true`, `passed=true`, resource score 1.0, and
runtime score 1.0 over 1,536 points. The worst point is
`uniform_flux_disordered_03`, step 1.0, four repetitions, propagator.
The artifact is one universal schedule, with no runtime case selection.
Its core margin is small; this proves the frozen finite-instance gates are
achievable, not that the schedule generalizes to every possible draw.

## Provenance and budget

- Source witness: `../exact_refine/refined_submission.json`.
- Source code: `../exact_refine/refine.py` and `../exact_refine/order_refine.py`.
- Source trace: `../exact_refine/order_search_summary.json`.
- The previous search scanned 65 swap/symmetry word candidates and used
  227.560743507 aggregate optimization CPU seconds, within its 600-second cap.
- The passing phase was `word_opt_0:lattice_symmetry_True_True_False`.
- Central-difference full point-Jacobian relative error was
  5.240584779996078e-7; the passing phase's directional gate-Jacobian relative
  error was 1.3604354636716466e-7.
- This authorization used zero of the 900 optimization CPU seconds. The
  independent official rerun used 3.584293 child-process CPU seconds.

## Files and integrity

`submission.json` is byte-identical to the private passing source. Its SHA256 is
`55a7773e0aa3160a87bdead611b4e4e6e9c706c423c90dad08cb42268fdc1e98`.
`official_report.json` contains the new official result; `summary.json` records
provenance, CPU use, and zero score differences from the prior official run.

`protection_check.json` confirms all 80 protected files are unchanged, including
participant, evaluator, root status, generation-1 archives, and exact_refine.
Participant/evaluator hashes also match the original pre-search snapshot.
The before/after manifests are `protected_before.json` and
`protected_after.json`. No participant, evaluator, fixture, status, target,
archive, or previous-search file was modified by this verification.

## Reproduce from concept_2 root

```sh
python3 -B adversary/topology_refine/verify.py
```

This copies the private source artifact, invokes the official checker, and
checks protection hashes. All output remains in this private directory.
The direct checker invocation is:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 -B evaluator/evaluate.py --submission adversary/topology_refine/submission.json --output adversary/topology_refine/official_report.json
```
