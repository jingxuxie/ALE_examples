# Extended original-control portability checks

This audit writes only here, outside the immutable generation-two packet. It
tests the two original N10 controls from fresh public inputs, without exposing
archived answers, reverse checkpoints, private certificates or seeds. Completed
secondary-source interfaces were inspected, but this profile uses the primary
champion's unchanged archived algorithms and binaries.

Each control has a 600-second outer wall bound; the worker gets 580 seconds to
leave startup/teardown margin. Two controls may run concurrently. The original
beam variant first uses width 2000, branches 60 and entropy weight 0.1, matching
the archived search's wider settings more closely than the short selection
probes. Newly generated beam checkpoints seed unchanged two-gate bridges and,
if needed, continuous refinement/pruning. The fallback is the archived beam2
at width 10000/branches 80 followed by fresh-checkpoint bridges. Search stops
when an independently validated legal circuit passes.

This is an extended portability profile, not the same narrow beam3 profile used
for the earlier 60/300-second candidate-selection probes. Its results must not
be presented as if the selected new cases were tested with this stronger
profile. No full-hour failure claim follows from either bounded benchmark.

Every solver executes in a new certificate-free bubblewrap namespace. Runtime
mounts include only system libraries, audited archived code/binaries, one old
public target, and fresh per-control outputs. Host /home, /srv, task parents,
champion archives and candidate pools are not visible. The trusted parent
recomputes fidelity and constraints from the original public input. Frozen
participant and evaluator-core hashes are checked before and after the audit.

`report.json` holds the combined evidence; `runs/<control>/` retains phase logs,
fresh submissions, namespace attestations and trusted scores; `provenance.json`
records source/binary hashes and the absence of archived checkpoint inputs.
