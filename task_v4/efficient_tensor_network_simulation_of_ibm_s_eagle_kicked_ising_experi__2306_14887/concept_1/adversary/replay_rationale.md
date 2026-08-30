# Planner replay protocol

The first measured fresh score is 3.663561x against the pre-frozen 4x target.
That is a narrow miss, so it is not sufficient evidence for confident retention
without a stability check. The frozen submission is replayed unchanged.

The original execution pinned every test to the first available CPU. On this
shared machine, concentrating every benchmark there may create contention.
Replay deterministically spreads cases across available CPUs using an input
hash, still restricting each invocation to exactly one CPU and the same
45-second wall limit. Namespace startup remains excluded. CPU usage is also
recorded. No input, target, work convention, memory convention or artifact is
changed. A successful replay counts as success of the fresh submission, not as
an independent new solution. A private 36-second-search variant is separately
identified and cannot retroactively alter the fresh result.

Outcome: the unchanged solver scores 3.663562888x on replay versus
3.663561127x originally. The miss is narrow but reproducible under the changed
CPU placement. The recorded wait-resource counters describe only the bubblewrap
launcher, not the nested solver; their apparent CPU fractions must not be used
to infer utilization. Subsequent reports explicitly label that accounting scope.
The private 36-second variant times out on inhomogeneous_2 and is not a passing
resource-compliant solution. No passing implementation is known.
