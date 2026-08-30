# Final parent handoff

**Recommendation: stop; do not build a third generation from vp03/vp05.** A2 remains officially solved. The historical campaign status remains `resource_inconclusive`; this additive review does not change the frozen policy, results, targets, or witnesses. No new solver runs, task installation, or fresh launches accompany this review.

## Frozen-input A2 repeats

All six runs returned normally with exit 0, a valid independently checked stationary field, gap closure 0, and zero reported nonlinear candidate trials. CPU below is the existing runner's charged CPU; wall includes the entire monitored launch. Each repeated field equals its frozen baseline in independently recomputed energy.

| Case / repeat | CPU s | Wall s | CPU/wall | Closure | Low-load proxy missed | Observed stop |
|---|---:|---:|---:|---:|---|---|
| vp03 / 1 | 6.831460 | 13.552120 | .504088 | 0 | CPU/wall | Normal exit; no deadline |
| vp03 / 2 | 7.286317 | 10.019983 | .727179 | 0 | CPU/wall, sibling load | Normal exit; no deadline |
| vp03 / 3 | 7.169923 | 10.918034 | .656705 | 0 | CPU/wall | Normal exit; no deadline |
| vp05 / 1 | 9.159466 | 20.723425 | .441986 | 0 | CPU/wall | Normal exit; no deadline |
| vp05 / 2 | 9.639310 | 17.458649 | .552122 | 0 | CPU/wall, sibling load | Normal exit; no deadline |
| vp05 / 3 | 9.904265 | 13.330208 | .742994 | 0 | CPU/wall, sibling load | Normal exit; no deadline |

**The ratio misses cannot explain these failures by time-budget truncation.** The unchanged source uses a 55-second inner budget; its largest early-stop reserve is 6.5 seconds. Even the slowest complete launch leaves at least 34.276574 seconds of inner budget, far above every timed search cutoff. The low-load proxies still fail under the predeclared rule, so formal certification remains inconclusive; that does not turn an early, normally completed search into a timeout. Initialization-only diagnostics on the exact frozen inputs also successfully construct the hole-sector model. Evidence supports a proposal-space limitation: hole-sector search without explicit bulk-vortex relocation, rather than insufficient runtime. Zero-trial logs support this interpretation but are not used as trusted timing measurements.

## Preexisting generation-1 capability

Both stored `ratchet_1/runs/champion_warm` fields were independently reloaded through the bounded NPZ checker and rescored against the **same current frozen B and W**. No optimization or new solver execution was performed.

| Case | Current B | Same W | Stored G1 warm energy | Closure | Residual E−W | Historical wall s |
|---|---:|---:|---:|---:|---:|---:|
| vp03 | -1422.745156445820 | -1423.947169760779 | -1423.891812742211 | .953946418165 | .055357018568 | 54.994862 |
| vp05 | -1497.639653053848 | -1498.186104051798 | -1498.075755165084 | .798062612881 | .110348886715 | 55.773705 |

Independent gradient RMS is respectively `1.0159380434123259e-7` and `2.7207593646919544e-7`. Both historical records are valid, exit 0, and describe an actual trusted 60-second sandbox with one-core affinity and 2 GiB. The fields satisfy the current quality/stationarity gates individually; their retrospective two-case, one-family mean is **.876004515523**, above both .65/.45 gates. Both remaining gaps are below the predeclared .5 meaningful-gap threshold. Archived generation-1 source and the historical `ratchet_1/baseline/solve.py` have identical SHA-256 `e7b932fe92ff8aada72703383dd504abcbfc6164b786f293d18440b4e6236f6e`.

**Qualification limit:** these are preexisting executable outputs with recorded in-budget wall times, not merely expensive witness fields. Their historical inputs have identical physical arrays but differ from the current frozen inputs in `initial_real` and `initial_imag`; this is not a new byte-identical-input replay qualification. The old records do not contain the later protected payload CPU measurements, so no numerical historical CPU value is asserted. Their demonstrated quality and resource-bounded provenance nevertheless establish prior capability covering both candidate gaps. A third generation based on these cases would test a regression/specialization relative to G1, not a convincingly harder previously unsolved capability.

## Evidence and disposition

- `parent_review.json`: machine-readable additive review and exact values.
- `report.json`, `REPORT.md`, `status.json`: unchanged historical campaign (13 broad cases, 21 launches, `resource_inconclusive`).
- `runs/frozen_repeat_{1,2,3}/{vp03,vp05}/record.json`: trusted timing, resource validity, independent energy checks; adjacent `solver.log` records zero trials.
- `frozen_warm_inputs/{vp03,vp05}/reference.json`: unchanged B/W and hashed provenance of the preexisting G1 warm fields and records.
- `../ratchet_1/runs/champion_warm/{vp03,vp05}/{field.npz,record.json,solver.log}`: existing G1 outputs; independently rechecked during parent review.
- `root_cause.json`, `diagnostics/frozen_baseline/{vp03,vp05}.json`: initialization, stationarity, polish, and topology evidence.
- `evidence_manifest.json`, `corpus/manifest.json`, `source_manifest.json`: existing sealed historical evidence, physical cases, and unchanged A2 source.

No formal generation-3 proposal is installed or recommended. Search is stopped. A final host process inspection found no active `ratchet_2`, `/submission/solve.py`, `cpu_monitor/run.py`, or `bwrap` replay processes. All work remains within the private ratchet-2 sidecar; no live or archived task artifacts were changed.
