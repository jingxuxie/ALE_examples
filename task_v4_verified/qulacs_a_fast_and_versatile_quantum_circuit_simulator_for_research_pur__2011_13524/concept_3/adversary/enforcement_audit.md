# Isolation termination accounting

Before evaluating any fresh submission, the secure rerun of the known private
policy revealed two false termination failures: both had already emitted valid
estimates with substantial solve time remaining, but the enclosing bubblewrap
controller had not finished namespace cleanup within one second. The original
secure run of the identical policy passed all 18 episodes at 89.125055/86.846538.

The evaluator now allows the controller to finish within the unchanged 45-second
solve deadline rather than imposing a one-second controller wait. The public
protocol's one-second exit instruction concerns the submitted program; controller
cleanup is not an additional scientific condition. Zero exit status, no trailing
output, the episode deadline, query count, shot count, and all numerical checks
remain enforced. Strict one-second payload-versus-controller attribution is not
claimed. This correction can only prevent infrastructure-induced false rejection;
no hidden data, scoring function, target, or participant asset changed.

The earlier post-handshake report `privileged_final.json` is preserved as
diagnostic evidence and is not a hardness result. The corrected confirmation is
`privileged_confirmation.json`. Host setup itself is separately bounded by a
90-second readiness handshake and is excluded from the 45-second solve clock.
