# Mandatory champion search — completed

**Disposition: reject v1 as a final hardness candidate.** The actual fresh D1 inverse predictor, unchanged, solved every case in this independent private search to floating-point accuracy. No genuine difficult failure was exposed, including the deliberately ambiguous support cases. This is an independent robustness result, not a duplicate official launched-set score or a universal proof over every possible draw.

## Actual predictor and isolation

- Source: `attempts/v_1/reconstruct.py`, 251 lines, SHA-256 `3a44571417a0c19d08fb923b1a9a415dbea5ab890dc7c5e23d2c2874a519b304`.
- The snapshot is byte-identical. No algorithm, thresholds, root enumeration, triple selection or fallback was changed. Only I/O was adapted to call its original `reconstruct(features, generator)` function and retain per-case diagnostics.
- Submitted code ran inside bubblewrap with feature/code-only read mounts, an output-only write mount, isolated network/PID namespaces, and no home/repository/private-label mounts. Runtime checks confirmed that all tested host/private paths and the original default-assets path were invisible.
- The private scorer ran separately after prediction. It did not execute submitted code. No official evaluator call was made, and `attempts/v_1.score.json` was neither read nor modified.

## Challenge coverage

The fixed audit contains **192 independent accepted models**, balanced with four draws in every family × occupied-pair-count × virtual-count stratum: all six families, 2/3 pairs and 6/7/8/9 virtuals. Two further non-IID support probes reproduce the lower and upper physical roots of the rare two-root witness. Both satisfy the original curation. All 194 rows were shuffled and given independent opaque IDs.

The predictor received no labels, true transfers, sampling seed, reference weights, or cohort tags. The minimum true reference weight is 0.852206; the minimum absolute tail is 1.53639e-4; the maximum label-solver residual is 9.14e-16. These are nonnegligible-tail weakly correlated cases, not near-zero-label checks. No new participant generation was created.

## Results

| Cohort | Cases | Tail RMSE, synthetic Eh | Maximum absolute error |
| --- | ---: | ---: | ---: |
| All cases | 194 | 2.85047e-15 | 1.62093e-14 |
| Independent stratified draws | 192 | 2.86505e-15 | 1.62093e-14 |
| Rare lower-root witness | 1 | 2.22045e-16 | 2.22045e-16 |
| Rare upper-root witness | 1 | 4.44089e-16 | 4.44089e-16 |

Worst-family RMSE is **3.72490e-15**. Maximum recovered-transfer error is **1.34074e-13**; maximum singleton/pair/triple feature residual is **1.77636e-15**. All 194 predictions are valid and finite. There are **zero exceptions, zero substantive accuracy failures, and zero cases exceeding 3e-5**. Both ambiguous pairs were handled by the submitted algorithm. Per-family, per-cohort and per-case records are saved; no failures are hidden by successful-only averaging because every case succeeded.

### Failures and root cause

No predictor failure was observed. The only setup issue was environmental: the CLI's nested sandbox denied bubblewrap network-namespace setup, and the minimal isolated runtime initially lacked the system BLAS alternatives/cache paths. These were resolved by an approved outer bubblewrap launcher and read-only system-runtime mounts—not by relaxing label isolation or modifying the champion.

The hardness failure is structural: the submitted predictor analytically recovers occupied–virtual amplitudes, enumerates pair transfers through small generalized eigenproblems, selects ambiguous branches using local triple checks, and diagonalizes the reconstructed small Hamiltonian. This removes the intended predictive uncertainty without training. The rare root ambiguity does not supply a difficult failure for this actual champion.

## Runtime

- Challenge preparation: **8.149 s**.
- Total time inside the original numerical `reconstruct` calls: **3.464 s**.
- Adapter runtime after its initial imports: **4.124 s**.
- Complete bubblewrap launch/runtime, including startup: **21.790 s**.
- Predictor peak RSS: **58.94 MiB**.

## Exact replay and preservation

`runs/run_1/score.json` is the aggregate record; `runs/run_1/case_results.json` contains every target, prediction, error and diagnostic. `runs/run_1/launch.json` records the exact sandbox command and mounted-input hashes. The input NPZ, byte-identical source snapshots, output NPZs, logs, private truth and independent sampling manifest are retained. `README.md` gives replay commands using a new run name; `REVIEW.md` documents the code review and isolation boundary.

All protected public/evaluator files and the original fresh predictor remained byte-identical. Existing target, baseline, seeds, labels, participant assets, evaluator and champion algorithm were not changed. The main process retains responsibility for the official score and champion archive. Any future ratchet remains a separate, explicitly authorized task; none was built here.
