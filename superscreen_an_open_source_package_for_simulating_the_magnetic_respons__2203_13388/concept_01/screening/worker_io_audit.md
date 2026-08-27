# Evaluation worker I/O clarification

Before evaluating the fresh submission, inspection identified that the public
contract does not require solution code directories to be read-only on rerun.
Ordinary scientific programs can create JIT/cache files beside their code.
The evaluator therefore runs a writable disposable copy of each submitted
directory, preserving its original absolute mount point. Symlinks are copied
as symlinks, not followed into private directories. The original submission is
not modified, and all oracle files remain outside the mount namespace.

This is an infrastructure-only clarification, not a changed scientific task or
fundamental redesign. No fresh-agent score had been computed. All input cases,
reference arrays, scoring formulas, weights, thresholds and resource guards are
unchanged. The old evaluator hash and the current worker version are retained.
The reference is re-evaluated under the same worker used for the participant.
