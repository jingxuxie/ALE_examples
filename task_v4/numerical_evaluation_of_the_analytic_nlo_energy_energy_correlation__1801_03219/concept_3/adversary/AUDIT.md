# Private readiness audit

Frozen target SHA-256: `54f9ca8017f47515f81312b42e9b95ad82a96d05fdcb99fb2ab000568879d1be`.

Independent arithmetic and static-artifact checks passed: 44 named checks, 512 individually perturbed lags, and 32 integer swap-delta tests. All 1024 directed bins and 513 geometric angular bins agree; exact rational normalizations are one, with self-pairs and antipodal endpoints retained.

The planted witness scores 1.0 and remains exclusively private. Malformed JSON, wrong counts, cyclic-boundary violations, feasible wrong correlations, symlinks, directories, FIFOs, oversized files, target spoofing, and submitted-code probes are rejected or ignored as appropriate. Rotations and reflection pass.

## Bounded controls

| Seed | Proposals | Core | Matched lags | Squared error | Search seconds |
|---|---:|---:|---:|---:|---:|
| 1701 | 240000 | 0.0 | 79 | 3542 | 3.481 |
| 2718 | 240000 | 0.0 | 66 | 4060 | 4.226 |
| 31415 | 240000 | 0.0 | 73 | 3902 | 4.487 |

The target was not resampled or changed after these controls. Their failures are evidence against this bounded baseline only. They do not establish failure of phase-retrieval, constraint-programming, stronger search, or the forthcoming agents. No fresh agents were launched. This audit is implementation-independent arithmetic by the authoring process, not a separate agent's review.
