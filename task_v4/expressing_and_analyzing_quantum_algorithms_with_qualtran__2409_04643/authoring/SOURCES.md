# Private source provenance

- Paper: https://arxiv.org/abs/2409.04643 and
  https://arxiv.org/html/2409.04643v1 ; submitted 2024-09-06.
  Archived as `sources/paper.html`.
- Official repository: https://github.com/quantumlib/Qualtran ; snapshot
  `096a2d009059faee0cfae462c3d59cb055300eb9`, committed 2026-08-25.
  A shallow checkout is private at `sources/Qualtran/`.
- Official releases and recent issue/PR metadata retrieved 2026-08-28 from the
  GitHub API, archived as `sources/releases.json` and `sources/recent_issues.json`.
  Inspected releases include v0.7.0 (2026-01-22), v0.6.0 (2025-04-02),
  v0.5.0 (2024-09-10). The paper-era and current source are distinguished.
- Scheduling basis: paper II.2.3, current
  `qualtran/resource_counting/_qubit_counts.py` and
  `qualtran/_infra/binst_graph_iterators.py`. The challenge's baseline independently
  implements the published stable net-width scheduling policy; its resource
  contracts are explicitly a benchmark abstraction, not fabricated hardware data.
- Lookup basis: paper III.2 and III.3; current
  `qualtran/bloqs/data_loading/select_swap_qrom.py`. Data-dependent circuit
  construction is a different optimization question than minimizing the known
  select-swap block-size expression.
- Numerical follow-ups: recent issue #1937 reports Jacobi-Anger degree
  underestimation in HamiltonianSimulationByGQSP. Numerical concept-specific
  source snapshots, constraints and validation live in its private adversary
  directory; citing an issue alone is not accepted as a reproduced failure.
- Prior local task inspected:
  `tasks/expressing_and_analyzing_quantum_algorithms_with_qualtran__2409_04643/`.
  Its status reports a passing reference and a 600-second fresh attempt that
  timed out/crashed. That outcome is not reused as new empirical evidence.

No private source snapshot, old reference, old hidden case, or generation script
is included in any fresh participant mount.
