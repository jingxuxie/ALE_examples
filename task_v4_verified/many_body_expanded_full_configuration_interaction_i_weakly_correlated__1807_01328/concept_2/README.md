# Retained robust-counterexample task

**Status: hard_open_candidate. Generation 3; two ratchets. Solvability unknown.**

The canonical participant/evaluator are the final generation, copied byte for
byte from `adversary/ratchet_2/`. The frozen packet status is a prelaunch
snapshot; `status.json` here records the completed tournament. Earlier passing
champions remain in `champions/generation_1/` and `champions/generation_2/`.

## Final evidence

Nominal constraints are unchanged: maximum triple 1 microEh, omitted tail at
least 50 microEh, ratio at least 100, reference weight at least 0.95, gap at
least 0.4 Eh, and diagonal margin at least 0.6 Eh. Additionally, each of two
independent frozen 128-draw perturbation families requires at least 122 successes.
Both use radius 0.001 Eh: VV-only controls and all 100 coefficients of the
restricted paired model. This is a finite assay, not a population guarantee.

| Artifact | VV successes | Full successes | Core score | Worst-family score |
| --- | ---: | ---: | ---: | ---: |
| Supplied zero baseline | 0/128 | 0/128 | 0.00001043 | 0 |
| Previous B2 champion | 128/128 | 0/128 | 0.666667 | 0 |
| Fresh attempt v3 | 128/128 | 7/128 | 0.685855 | 0.057566 |
| Independent fresh attempt v4 | 128/128 | 9/128 | 0.691338 | 0.074013 |

Both fresh nominal witnesses and all their perturbed physical-regime checks
pass. Their persistent-witness conditions fail badly in full uncertainty.
Artifacts and validator resources are valid; this is not an interface or
runtime failure. Construction durations are 3349.31 and 3163.86 seconds, each
under its independent one-hour limit. `v_4` repeats generation 3; it is not a
fourth task generation. Main's canonical replay reproduces v4's score exactly.

A private warm-start portfolio completes six runs and 280 objective evaluations
without finding a passer. A point witness for an earlier generation does not
demonstrate current feasibility. No impossibility claim is made.

The failed capability is preserving low-order cancellation together with a
material omitted tail under 100-dimensional coefficient uncertainty, while
remaining weakly correlated. These are effective seniority-zero Hamiltonians,
not arbitrary ab initio Coulomb tensors or a universal theorem about screening.

## Participant boundary

Expose only `participant/` read-only and a separate initially empty writable
output directory. Keep this README/status, evaluator, private draws, previous
witnesses, portfolio, and all other attempts inaccessible. The participant
contains the original weak baseline, never a previous fresh solution.

## Privileged reproduction

From this concept directory with Python 3, NumPy, and SciPy:

```bash
python -B participant/workspace/baseline.py --output /tmp/c2_baseline_witness.json
python -B evaluator/evaluate.py --artifact /tmp/c2_baseline_witness.json --report /tmp/c2_baseline.json
python -B evaluator/evaluate.py --artifact attempts/v_3/witness.json --report /tmp/c2_v3.json
python -B evaluator/evaluate.py --artifact attempts/v_4/witness.json --report /tmp/c2_v4.json
OPENBLAS_NUM_THREADS=1 python -B evaluator/hidden/test_packet.py
```

The checker executes no submitted code. Its separate validation limits are
CPU 60 seconds, wall 90 seconds, and 512 MiB address space; they do not claim to
measure the solver's offline CPU/RAM. The artifact limit is 32 KiB. The private
provenance fixture required by the validation tests is copied unchanged into
`adversary/draw_provenance.json`.
