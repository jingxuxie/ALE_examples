# Method and scientific scope

Primary sources (checked 2026-08-28):

- Sivarajah et al., *t|ket>: A Retargetable Compiler for NISQ Devices*,
  arXiv:2003.10611v3, section 7, especially 7.2.
  https://arxiv.org/html/2003.10611v3#S7.SS2
- Cowtan et al., *On the qubit routing problem*, arXiv:1902.08091v2,
  section III.3 and Appendix A. This routing-method paper predates the compiler
  paper; it is not a later follow-up publication.
  https://arxiv.org/html/1902.08091v2#S3.SS3

The papers motivate distance-based dynamic routing, finite lookahead, and
shortest-path escape. They report empirical performance, not the approximation
bound being falsified here. The target is precisely the supplied implementation.

## Supplied algorithm

Drain all dependency-ready adjacent gates. Recompute future DAG layers by deleting
completed gates, not by imposing global serial barriers. Consider every hardware
edge touching a currently ready gate's operand. Score its resulting placement
using average excess shortest-path distance per future layer. Weighted variants
sum these scores with geometric decay; lexicographic variants compare layer
scores in order. Resolve ties with the configured physical-edge ordering.

Do not revisit a placement without executing a gate. If all candidates are
excluded, or 32 swaps have not executed a gate, shortest-path route a closest ready
pair and execute it. Then resume the normal heuristic. This ordinary progress
safeguard guarantees termination and is identical for all configurations. Each
result is replayed and its fallback use is reported.

This is a transparent, competitive **SWAP-only adaptation**, not a bit-for-bit
implementation of tket. It omits initial-placement optimization, CX bridges,
disjoint double-SWAP search, pointwise distance-vector pruning, and native-gate
cleanup. The same fixed placement and SWAP-only primitive set apply to both
competitors. Weighted lookahead and relabeling diversification are benchmark
extensions. No injected correctness defect or deliberately wrong distance table
is involved. Conclusions must be limited to this particular routing portfolio.

## Search guidance

One productive representation is a valid physical schedule: start at identity,
insert a modest number of hardware-edge SWAPs, and emit adjacent native gates.
Track occupants to derive the logical demand list. The schedule itself certifies
an upper bound; no optimality oracle is needed. Vary gate order, local interactions,
and SWAP placement, enforcing the regularity constraints. Test all portfolio
settings and all relabelings rather than optimizing one tie-breaking accident.
The weak baseline generator demonstrates this inverse-routing construction.
