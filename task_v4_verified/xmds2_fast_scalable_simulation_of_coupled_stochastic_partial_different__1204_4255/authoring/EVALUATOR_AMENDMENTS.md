# Non-scoring evaluator hardening during generation-one trials

The concept-1 participant, all 30 hidden instances, all baseline costs, and the
fixed 20%/8% targets remain unchanged. A separate privileged audit found two
malformed-input exception cases and a mismatch between the stated one-CPU/job
memory limits and the original per-process resource enforcement.

Before scoring any fresh submission, the organizer catches nested-JSON errors,
implements the already documented zero/zero cost rule, pins the entire execution
tree to one CPU, detects affinity expansion, and monitors aggregate address space
at 50-ms intervals in addition to inherited hard per-process limits. Resource
measurements come from the organizer, not submission-controlled result files.
The 120-second execution clock starts when the trusted launcher is ready, excluding
variable namespace setup delays; setup has its own 180-second watchdog. All
filesystem/network isolation remains active. Sampled CPU accounting is explicitly
reported as a lower bound rather than mislabeling launcher usage as total usage.

The exact checker and cost objective are not changed for any supplied case.
Baseline scores and all 30 costs are rechecked after hardening. The generation-one
run records honestly report the evaluator-file hash change; it is not a target
change, private-case ratchet, or feedback to either active fresh agent.
