# Concept 3 — Mode D hidden pair-space tail prediction

**Final disposition: solved; not retained for hardness.** Solvability is demonstrated by one passing fresh attempt and the mandatory actual-champion search. Rejection reason: **scalar inversion shortcut; genuine broader failures not found**. There are zero ratchet generations, no pending ratchet, and no further launch or generation planned.

Known passing solution: `champions/generation_1/submission`; static predictions: `champions/generation_1/submission/predictions.npz`. The archived problem is a simulated seniority-zero pair model, not an ab initio or unrestricted electronic-FCI claim.

## Preserved evidence

| Result | Core RMSE, synthetic Eh | Worst-family RMSE, synthetic Eh |
| --- | ---: | ---: |
| Initial frozen baseline | 6.710884639e-4 (**671.088 µEh**) | 1.426065010e-3 (**1426.065 µEh**) |
| Official fresh attempt, 288 cases | **5.150184402e-15** | **9.373141856e-15** |
| Actual-champion private search, 194 cases | **2.850468180e-15** | **3.724900106e-15** |

The broader search used the unchanged fresh predictor on 192 independent stratified cases across all six families plus both rare-root support variants: zero failures, maximum error **1.620925616e-14 Eh**. Its feature-only sandbox excluded private truth. The shared source profile and low-order CAS data permit algebraic/scalar Hamiltonian inversion; rare root ambiguity did not produce a genuinely difficult failure.

Original records remain at `attempts/baseline/score.json`, `attempts/v_1.score.json`, and `adversary/champion_search/runs/run_1/score.json`. See `adversary/FINAL_DISPOSITION.md` for the final decision and `adversary/champion_search/README.md` for exact private replay artifacts. Historical audit/source scores are preserved; current lifecycle flags are in `status.json`.

## Exact solver boundary

The only permitted solver assets are the reviewed **`participant/` tree**, mounted read-only, plus a separate writable output directory. This includes the mission, canonical `participant/input/workspace/` assets, top-level workspace pointer, baseline wrapper, and the public generator explicitly distributed there.

**Prohibited for a solver:** the concept root or parent task tree; `evaluator/`, `attempts/`, `champions/`, `adversary/`; root status/README; `source/` artifacts; and all generation-private builders, records, Hamiltonians, labels or seeds. Never expose the whole repository or privileged archive. There is no hidden-score API. Static evaluation reads arrays only, executes no submitted code, and does not attest offline CPU/RAM usage. These are archival boundary rules, not authorization for another launch.

## Privileged replay commands

From the concept_3 root, using a writable output directory:

```bash
python -B evaluator/evaluate.py champions/generation_1/submission/predictions.npz --output /path/to/writable/output/champion_score.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B participant/baseline/run.py --output /path/to/writable/output/baseline_predictions.npz --report /path/to/writable/output/baseline_report.json
```

These commands replay preserved artifacts; no replay was performed during disposition finalization. Do not regenerate, reseal, alter frozen participant/evaluator/attempt files, or create another generation. Original freeze records and prelaunch interface amendments remain unchanged; their historical prelaunch knowledge is not rewritten.
