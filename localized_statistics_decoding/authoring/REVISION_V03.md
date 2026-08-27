# Final task-mode replacement

Both earlier posterior-reconstruction tasks were solved perfectly. Version 2's
valid fresh pilot scored 1.0 in 900.742 seconds, without timeout. The final
version replaces that task mode with performance-driven recovery on a curated
quantum-decoder failure corpus. It neither adds posterior edge cases nor asks
for more precision or larger output tables.

Alternative final concepts considered: active experiment design for decoder
calibration; circuit-to-detector compilation; and logical recovery of difficult
syndrome-consistent failures. Selected the last because the scientific objective
does not supply a tractable inference recipe. Search/ranking/scheduling choices
must actually repair logical errors on validation data and transfer across
matrix geometry, size and noise bias. A correct Gaussian elimination routine
alone receives only the 15% syndrome-consistency component.

Matrices are newly generated commuting two-block cyclic CSS constructions;
three independent binary mechanisms per physical qubit encode X, Y and Z
effects. Full logical maps are computed from the nullspace/stabilizer quotient.
The corpus is deliberately conditioned on legacy logical failures which have
a lower-cost reference-recoverable sector. TASK.md explicitly explains the
curation and prohibits interpreting these rates as threshold estimates.

The private reference is an ensemble of BP-plus-higher-order ordered-statistic
searches, followed by prior-likelihood candidate selection. It uses the
paper-associated public quantumgizmos/ldpc implementation, vendored under the
private solution only. Source API documentation inspected:
https://software.roffe.eu/ldpc/ldpc/bposd_decoder.html
The package version is 2.4.1. No package API or search recipe is prescribed to
the participant. The evaluator accepts every equivalent logical recovery.

Connection to the supplied paper: local matrix inversion, unreliable soft
information, cluster/search-order decisions, arbitrary hyperedges and quantum
degeneracy motivate the troubleshooting workload. This benchmark is not a
threshold reproduction. The reference chooses a different compatible recovery
approach, as permitted for behavioral evaluation.
