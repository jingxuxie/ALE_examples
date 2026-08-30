# Qulacs-seeded hardness discovery

The three independently packaged concepts use different primary verification
modes: A, structure-aware fusion planning; C, compact full-unitary circuit
construction; and E, budgeted adaptive noise calibration. `authoring/concepts.json`
records ten considered concepts, the selection rationale, paper and official
repository provenance, and the distinction between inherited and newly measured
results. Final empirical decisions are in root and per-concept `status.json`.

## Run an evaluator

From this directory, after selecting a concept and an executable submission:

```
python3 concept_1/evaluator/evaluate.py --submission concept_1/participant/baseline --output concept_1/adversary/recheck.json
python3 concept_2/evaluator/evaluate.py --submission concept_2/participant/baseline --output concept_2/adversary/recheck.json
python3 concept_3/evaluator/evaluate.py --submission concept_3/participant/baseline --output concept_3/adversary/recheck.json
```

Replace a baseline directory with `concept_N/attempts/v_1` to evaluate a fresh
submission. Evaluators never import submitted code into their privileged process.
For the retained compilation task, the matching final attempt is
`concept_2/attempts/v_3`. Its earlier `v_1` and `v_2` submissions belong to
`concept_2/generations/generation_0` and `generation_1`, respectively; use each
archived generation's evaluator when replaying those champions. The current
compilation participant is generation 2, not the easier initial target set.
The shared, fail-closed runtime lives in `authoring/isolation.py` and
`authoring/isolation_bwrap.py`; keep the full root package together. Linux x86-64,
Python 3.10+, NumPy, SciPy, bubblewrap, libseccomp, and util-linux are required.
No Qulacs installation, GPU, network access, or source-native reference solver is
required by participants. Evaluations require permission to create the audited
mount/PID sandbox. Do not remove isolation to make an evaluator succeed.

## Tests and provenance

`REPORT.md` contains the empirical decisions. `status.json` selects the
verified-achievable compilation task and also retains fusion planning as an
open candidate. `authoring/scientific_attempts.json` records all five scientific
attempts separately from infrastructure probes. The calibration concept remains
solved after repeated-outcome stress testing.

```
python3 -m unittest discover -s concept_1/evaluator -p 'test_*.py' -v
python3 -m unittest discover -s concept_2/evaluator -p 'test_*.py' -v
python3 concept_3/evaluator/test_system.py
```

Participant manifests and pre-attempt fixed targets are recorded in each
`adversary/target_freeze.json`. Privileged witnesses, private policy probes,
source snapshots, hidden suites, and previous submissions are generation-only
artifacts. None are mounted into the tested agent. Attempt outputs are separate
from fresh runtime audit logs in `authoring/isolation_fresh_*/`.

`authoring/launch_fresh.py` invokes the unmodified user-supplied allowlisted
runner with `ultima-alpha`, a newly sanitized ephemeral runtime, read-only
participant assets, and an initially empty writable output. Each attempt has a
3600-second deadline. Infrastructure-only canary probes are explicitly marked
non-scientific and are excluded from attempt counts. See
`authoring/isolation_audit.md` for the approved workaround for host network
namespace stalls, its stricter network-denial policy, limitations, and evidence.

Wall and address-space limits are enforced as documented by each task; memory
limits are per process, not cgroup aggregate guarantees. CPU affinity and thread
environment settings establish ordinary benchmark execution, not a security
claim that malicious code cannot change its affinity. Scientific deadlines
exclude separately bounded isolation startup where the protocol supports it.
Infrastructure failures must be resolved or reported as such, never as hardness.

`hard_open_candidate` means a validated task survived the fresh attempt without
a known passing implementation. `hard_verified_achievable` additionally requires
a passing privileged witness or policy under the same scientific constraints.
No global optimality or universal impossibility claim is implied by either.
