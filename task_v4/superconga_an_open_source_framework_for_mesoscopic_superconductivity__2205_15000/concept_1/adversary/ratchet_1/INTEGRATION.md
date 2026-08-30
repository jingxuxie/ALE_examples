# Focused ratchet proposal: approval required

All files here are private builder-side artifacts. No original participant,
evaluator, champion archive, or root status is modified. No fresh model is launched.

## Proposed task

Use `focused_proposal/manifest.json` and `focused_proposal/target.json`, **not**
the superseded six-case `proposal`. The three cases `nf01`, `nf02`, `nf04` form
one scientific family, `collective_fluxoid`. Input arrays and exact baseline/
witness fields are byte-identical to their already-frozen predecessors.
Quality thresholds remain 0.65 core / 0.45 worst family, with unchanged 60-second
wall and CPU limits, one core, 2 GiB, 256 MiB scratch, and 4 MiB NPZ limit.

`candidate_public` is the complete proposed public asset tree. It contains only
the public model/API, unchanged generation-1 champion baseline, starter, two
development cases, and their numeric targets. These development cases are
excluded from the three hidden cases. Only baseline fields, embedded in JSON,
are exposed; lower witness fields, source seeds, and generators stay private.
Do not publish any other directory here. In particular the original archived
champion directory contains evaluator assets: mount the clean `baseline` copy
instead, never that archive as a submission.

## Runnable sidecar evaluator

From this directory, with the required outer sandbox escalation:

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 focused.py validate
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 focused.py run --submission /ABSOLUTE/ARTIFACT --label unique_name --repeats 1
```

Results are in `runs/unique_name_1/score.json`, including checked energies,
stationarity, all quality scores, reasons, and trusted CPU/wall accounting.
`focused.py` imports the established independent energy/NPZ checker and trusted
Sandbox helper; only a minimal read-only CPU monitor is additionally mounted.
The private reference tree is never mounted. `baseline/solve.py` is the exact
previous champion. `challenger/solve.py`, with sibling `engine.py`, is the
runnable resource-bounded constructive challenger; it does not read witnesses.

## Main integration checklist

1. Approve the three-case scientific scope before launching generation 2.
2. Install only `candidate_public` as public assets, preserving the original
   generation-1 archive. Freeze its public hashes before the fresh launch.
3. Install the three cases, public baseline references, and private witness
   references from `focused_proposal`; update manifest paths and hashes.
4. Replace **both** old evaluator checks that require two cases per family:
   reference loading and aggregation. Require `case_count=3` and
   `family_cardinality={"collective_fluxoid":3}`. `focused.aggregate` is the
   tested generalized implementation; missing/duplicate cases still fail.
5. Keep independent energy, gradient, onsite lower-bound, regression, safe NPZ
   loading, and all resource checks. Outer Bubblewrap `wait4` does **not** measure
   payload CPU on this host. Use repaired parent accounting or the protected
   `cpu_monitor/run.py` protocol here, not submission-reported process time.
6. Preserve the supplied initial field exactly: its energy is `B`, so a baseline
   replay cannot create an artificial regression. Private `W` stays frozen.
7. Check the final `status.json` and low-load repeat reports before fresh launch.

The earlier `analysis_partial.json` is an intentionally preserved incomplete
snapshot, not the final count. `analysis.json` covers all 24 cases; its original
six-case/three-family readiness field is superseded by this focused proposal.
Preliminary `focused_champion_repeat_*` runs have **incomplete outer-only CPU
accounting** and are not used for resource certification. Use the corrected
`focused_champion_cpu_*` reports instead.
