# Privileged checker and resource audit

All artifacts in this directory are generation-only. No participant, evaluator,
hidden, status, trial, or champion files were modified. No fresh agents were
launched. The small fork in `resource_probe/solve.py` is a resource probe, not an
agent or planner search worker.

## Confirmed evaluator robustness defects

1. **Uncaught deeply nested JSON.** A response consisting of 2,000 nested arrays
   raises `RecursionError` in `json.loads` inside `evaluate`. The evaluator's
   exception tuple does not catch it. This should be an invalid submission,
   not an exception escaping the evaluator. This is a denial-of-evaluation
   defect, not evidence of an invalid schedule being accepted.
2. **Documented zero-cost rule is missing.** A legal 3-dimensional, 2-field,
   30-home-read instance has zero baseline and submitted cost. The protocol says
   its ratio is 1. The evaluator instead divides by zero and raises uncaught
   `ZeroDivisionError`. `zero_cost_case.json` is the conforming reproducer.
   All supplied hidden cases have positive baseline costs, so this defect does
   not change the reported hidden30 scores.

These tests execute the real `evaluate` function and real checker, replacing
only the submission transport with a deterministic response. Exact exceptions
and the protected-file hashes are in `audit_results.json`. No fixes were made.

Suggested repairs are to catch/depth-limit malformed JSON and implement the
specified zero/zero ratio, with an explicit policy for positive submitted cost
against a zero baseline. Neither repair requires changing the fixed target.

## Confirmed resource-enforcement gap

`probe_resources.py` invokes the supplied `authoring/isolation.py` runner with
its normal 120-second allowance. It succeeded under privileged host execution:
return code 0, approximately 15.71 seconds wall time, 0.29 seconds CPU, and
12,152 KiB maximum RSS. The initial outer-sandbox run failed with the reported
NETLINK restriction; a short 10-second host retry was insufficient for startup.

Inside the actual bubblewrap namespace, both the planner process and its forked
child reported an affinity mask containing **384 CPUs**, indices 0 through 383.
The child was allowed to start. Both independently inherited:

- `RLIMIT_AS = (1073741824, 1073741824)`;
- `RLIMIT_CPU = (120, 121)`.

The supplied runner has no CPU affinity restriction or aggregate descendant
memory/CPU accounting. These are per-process limits, not a one-CPU or aggregate
1-GiB job restriction. Filesystem/network isolation can be correct while this
resource promise remains unenforced. An external cgroup could supply additional
limits, but none is established by this runner or this probe. No >1-GiB memory
allocation or CPU saturation attack was attempted. The observed permissions
and source-level absence of aggregate enforcement, not a stress-test claim,
are the evidence. Full output is in `resource_probe_results.json`.

Suggested repair: pin the submitted process tree to one CPU and apply aggregate
job memory/CPU limits, or otherwise enforce equivalent restrictions on child
processes. The direct planner timing harness in `verify_runtime.py` explicitly
pins its single-process planner to one CPU and sets the 1-GiB address-space
limit. Those timings are not mislabeled as official isolated evaluations.

## Representation checker tests

All **55/55** expectation tests pass. They cover:

- malformed answer/action shapes, excessive actions, unknown action kinds;
- booleans/floats/negative/out-of-range coordinates and non-boolean keep flags;
- unavailable sources, duplicate destinations, missing and extra reads;
- distributed-axis transforms and no-op transposes;
- pinned-home drop, overwrite, and destination prohibitions;
- stale reads, stale sources, and stale drops following updates;
- fresh-home reuse and preservation of unmodified fields;
- scratch accounting after every transform and after the final read;
- legal single-buffer in-place transforms and homes outside scratch;
- charging transforms after the last read rather than ignoring them.

No malformed/stale/home/memory semantic bypass was found in these tests. This
is finite adversarial coverage, not a proof that every possible input is safe.

## Independent numerical replay

`independent_semantics` does not use the checker's representation-state updates
or route tables. It stores actual small complex tensors, applies NumPy FFT/IFFT
along the specified logical axes, physically permutes layout axes, replaces
home values at updates, and compares every read with a freshly transformed
current-version home. Axis lengths alternate 2 and 3, so layout permutations
are also tested on unequal shapes. It separately recounts cost and scratch.

The seeded tiny suite comprises 50 three-dimensional instances, each planned
by both the baseline and weighted planner: **100 schedules and 3,000 reads**.
All costs, peaks, and reads agree with the exact checker. Maximum absolute
Fourier discrepancy is approximately **2.665e-15**. This is an independent
concrete realization of the task's representation algebra, not verification
of the XMDS2 numerical PDE solver or physical transform-cost model.

`collect_evidence.py` additionally replays all selected hidden30 schedules with
the same independent implementation. The resulting 1,774 read comparisons,
maximum error, exact costs, and plan hashes are in `best_privileged.json`.

## Reproduction

From this directory, with bytecode disabled:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 audit_checker.py
PYTHONDONTWRITEBYTECODE=1 python3 probe_resources.py
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 collect_evidence.py
```

The resource probe needs an environment that permits the existing bubblewrap
runner. Temporary host files are directed under `adversary/temporary/`.
