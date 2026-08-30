# Final disposition — concept_3

**Finalized August 28, 2026. Status: solved. Retained for hardness: false. Solvability: demonstrated.**

- Rejection reason: `scalar inversion shortcut; genuine broader failures not found`.
- Fresh count: **1**. Ratchet pending: **false**. Ratchet generations: **0**.
- Known passing solution: `champions/generation_1/submission`.
- Static submission: `champions/generation_1/submission/predictions.npz`.
- No new generation, ratchet, launch, rescore or baseline execution is part of this finalization.

## Evidence and scientific interpretation

The original frozen baseline has core RMSE **6.710884639293459e-4 synthetic Eh (671.088 µEh)** and worst-family RMSE **1.426065009900344e-3 synthetic Eh (1426.065 µEh)**. Its original score and resource/audit records remain unchanged.

The official fresh attempt passed on 288 test cases with core RMSE **5.150184402154734e-15 Eh** and worst-family RMSE **9.373141855843252e-15 Eh**, as recorded in `attempts/v_1.score.json`. The full original `fresh_score` record is preserved in `status.json`.

The mandatory search replayed the **actual unchanged fresh predictor**, not the sidecar inverse, on **194 private challenge cases**: 192 independent accepted draws spanning all six families, both occupied-pair counts and all virtual counts, plus both physical roots of the rare support witness. It produced **zero failures**, RMSE **2.850468179656622e-15 Eh**, maximum error **1.620925615952729e-14 Eh**, and worst-family RMSE **3.724900106291676e-15 Eh**. The predictor ran in a feature-only bubblewrap sandbox without private labels or generation metadata. Exact code, data, commands, outputs and per-case errors remain under `adversary/champion_search/`.

The shared known occupied profile makes singleton transfer recovery explicit; each pair then leaves a scalar transfer problem, and local triple checks resolve the observed ambiguities. The broad actual-champion search found no genuine difficult failure. Therefore passing v1 demonstrates a reliable inverse-reconstruction solution, not the requested final hard predictive-discovery challenge. This is sufficient to reject v1 for hardness retention; it is not a universal proof about every mathematical support point.

The earlier rank>1 proposal remains an unbuilt private sketch, not a pending ratchet or authorized new generation. Other concept ratchets are outside this disposition.

## Exact participant-only boundary

Any archival solver replay may receive only the reviewed `participant/` tree, read-only, and a separate writable output directory. The public generator distributed inside that tree is allowed. The solver must not receive the concept root or parent task tree, `evaluator/`, `attempts/`, `champions/`, `adversary/`, root status/README, `source/` artifacts, or generation-private builders, records, Hamiltonians, labels or seeds. No hidden-score API is available. Private scoring stays outside the solver process; static evaluation does not attest offline CPU/RAM use.

## Privileged evaluator and baseline replay

Commands are relative to the concept_3 root and require writable outputs:

```bash
python -B evaluator/evaluate.py champions/generation_1/submission/predictions.npz --output /path/to/writable/output/champion_score.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B participant/baseline/run.py --output /path/to/writable/output/baseline_predictions.npz --report /path/to/writable/output/baseline_report.json
```

These are replay instructions only; no frozen data, targets, baseline, evaluator or attempt files are changed. Original prelaunch freeze metadata remains historical. Current solved/nonretained flags supersede stale lifecycle readiness, possible-open and pending-ratchet flags in the root status.

## Files changed for finalization

1. `status.json` — final lifecycle flags, passing-solution path and evidence references; original score/audit fields retained.
2. `README.md` — final disposition, preserved comparison, replay commands and solver boundary.
3. `adversary/FINAL_DISPOSITION.md` — this private decision record.
