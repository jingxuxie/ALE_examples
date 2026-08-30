# A2 bounded broad replay sidecar

Private write scope: this directory only. Never publish or mount the sidecar root.
No fresh agents or live participant/evaluator/champion modifications are allowed.

## Frozen corpus and policy

`corpus/manifest.json` preserves all 24 physically validated ratchet-1 cases,
metadata, stationary generation-1 outputs, and independently recomputed attained
witness fields with source hashes. `policy.json` was frozen before any v2 source
inspection. Exactly 13 starts have a preexisting energy separation at least 0.5;
only these are replayed. The other 11 are preserved as negative/coverage evidence,
not padded into artificial challenges. No new generator or witness search runs.

The objective arrays are byte-equivalent numerically to the originals. Initial
fields are replaced by actual stationary champion outputs, matching A2's public
input contract. Positive stiffness, connected physical grains, prescribed smooth
fields and hole solenoids, and the declared near-Tc finite-lattice GL model remain
unchanged. References are attained fields, not global minima.

## Activation

Main must notify completion. The executable additionally requires the exit marker
and an explicitly valid/pass watcher evaluation before inspecting/copying source:

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 replay.py --main-notified --submission ../../attempts/v_2
```

Run this outer command with sandbox escalation for Bubblewrap's network namespace.
Without notification or completion, it returns without polling. If v2 failed, it
records `not_needed`, preserves the watcher result, and never inspects source or
launches a replay. A passing artifact is copied unchanged, including helper files,
into private `submission`; `source_manifest.json` preserves its hashes and the
gate's exit/evaluation evidence. Only that clean copy and a frozen public tree are
mounted, never witness directories or archived evaluators.

## Bound and controls

One solver at a time; each gets 60 seconds wall/CPU, locked one-core affinity,
2 GiB address space, 256 MiB monitored scratch, and 4 MiB compressed/decompressed
NPZ. The actual child CPU is measured by a protected trusted parent inside the
namespace, not outer Bubblewrap rusage or solver stdout. All energies, gradients,
inactive sites, initial-state regression, and NPZ payload sizes are independently
checked. Source, input, process logs, output fields, CPU/load audits, and scores
are retained. Maximum 32 solver launches and 2,400 campaign seconds; no concurrency.

Thirteen broad replays normally cost about 10–13 minutes. At most four surviving
cases get a bounded tight local polish and one warm-discovery run. The best actual
A2 output is then supplied unchanged as a frozen initial field. Two independent
repeats start from that exact same field, not chained states. At most three attempts
are made to collect the two repeats; quiet-core waits are capped at 15 seconds.
Maximum solver time with four full control sets is 29 minutes for this corpus.

To claim stable failure, each accepted repeat must receive at least 95% CPU/wall,
have measured sibling utilization at most 30%, and begin with core/sibling load
at most 25%. It must retain at least 0.5 energy gap, reliable winding or vortex
misallocation, and closure at most 0.55, comfortably below the unchanged 0.65
core goal. Tight polishing may explain at most 10% of the gap. A successful
replay under any load invalidates a gap; a busy failed run never proves hardness.

## Dispositions

- `not_needed`: v2 failed; A2 retains its hard result; no sidecar search.
- `no_meaningful_ratchet`: selected gaps close or fail scientific controls; stop.
- `resource_inconclusive`: budget, output validity, or quiet controls are insufficient;
  do not relabel throughput problems as hardness or global robustness.
- `proposed_solvability_unknown`: stable cases support a private generation-3
  proposal. Keep 0.65 core / 0.45 worst-family, meaningful preexisting witnesses,
  actual supplied A2 baseline fields, and honest family cardinalities. No forced
  family diversity and no installation. Witness fields alone do not prove a
  passing generation-3 executable exists.

These outcomes concern this bounded corpus, not every physical parameter regime.
Main owns any later installation, resource-bounded solver qualification, or fresh
attempt. See `report.json`, `REPORT.md`, `broad_progress.json`, and `controls` for
measured outcomes. `test_harness.py` validates numerical, provenance, safety, gate,
and decision logic without launching any solver processes.
