# Extended L6 truth gate: admitted label, no complete ratchet

The one pre-existing inhomogeneous L6 case now passes the unchanged empirical
numerical-admission rules. This removes its earlier teacher-convergence gate.
It does **not** establish a complete scientifically justified scalability
ratchet: the reviewed six- and eight-state controls pass this individual case,
and no prospective full-batch benchmark or complete teacher corpus was built.

## Admitted numerical label

Case `a88c1f0553e4fe6b4b9290af` is unchanged; its full physical parameters are in
`plan.json`, `query.json`, and `FINAL_REPORT.json`. It has six open-chain sites,
positive site-dependent quartic couplings, inhomogeneous masses/bonds, and
global parity symmetry. The final label uses retained local dimension 14 and
onsite oscillator cutoff 160, not an extrapolation of the old d12 result.

| Quantity | Admitted value |
| --- | ---: |
| E0(odd) - E0(even) | 0.00004345453819056336 |
| E1(even) - E0(even) | 1.3587046924693134 |
| E1(odd) - E0(odd) | 1.3685208870499486 |

The corresponding finite-basis ground-energy diagnostic is
`-2.597845054942061`. This is an empirical finite-chain convergence certificate,
not a rigorous infinite-Hilbert-space ground-state bound or an asymptotic label.

| Check | Measured maximum | Unchanged limit |
| --- | ---: | ---: |
| d10 to d12 absolute log-gap change | 1.8043590156e-5 | 2e-5 |
| d12 to d14 absolute log-gap change | 2.1251099640e-7 | 2e-5 |
| Onsite cutoff 80 to 160 absolute log-gap change | 1.2476131238e-10 | 2e-5 |
| Frequency 2.0 to 2.34 at cutoff 160 | 1.8038537332e-10 | 2e-5 |
| State residual, three new stages | 3.1645501564e-13 | 1e-10 |
| Residual-plus-roundoff/gap, three new stages | 4.1334574264e-9 | 2e-6 |

All gaps also pass the original dimensionless floor of 1e-6. Each confirmation
is an actual ARPACK eigensolve, with warm starts only changing the starting
vector and Krylov dimension. A parity-preserving onsite sign gauge aligns
eigenvectors across basis choices; no physical Hamiltonian or tolerance changes.
The source-equivalence check on the small two-site truncation differs by at
most 8.89e-16 in gaps. `evidence_audit.json` additionally records a separate
post-run application of the saved label Hamiltonian to all four saved
eigenvectors, recomputing norms, residuals, and gaps without another eigensolve.

## Reviewed source-native controls

These are **generation-only single-case probes**, each limited to 30 CPU
seconds, 60 wall seconds and 2 GiB address space. They are not official
30-CPU-second batch scores. Accuracy uses the original mean absolute log-error
limit 0.03 and p95 limit 0.12; no thresholds were tightened.

| Retained local states | Mean log error | Maximum log error | Solve CPU seconds | Single-case result |
| --- | ---: | ---: | ---: | --- |
| 4 | 0.3529750234 | 0.9016550861 | 0.1871 | Accuracy failure |
| 6 | 0.0173776416 | 0.0474615750 | 1.7552 | Pass |
| 8 | 0.0004124718 | 0.0011628114 | 15.4987 | Pass |
| 16 | No prediction | No prediction | 1.9094 child CPU before failure | Memory failure |

The generalized d16 implementation genuinely fails allocation inside ARPACK:
the `(8388608, 24)` float64 Krylov array alone requires 1.50 GiB, exceeding the
2-GiB address-space budget once existing allocations are included. This is a
measured source-native resource failure on the admitted physical case, not a
shape trick. It does not show that a smaller, adaptive, sparse or MPS method
fails. In particular, the d6/d8 results above prohibit claiming that all cheap
controls fail this seed. The CPU figures for successful controls exclude
interpreter startup; full child CPU/wall figures are retained in
`generation_probes.json`.

The byte-identical old champion also ran. It raises an out-of-range sparse
index error because its Hamiltonian construction supports only lengths two
and three. This unsupported-length failure is explicitly excluded from
scientific or hardness evidence. No original-domain champion failure is claimed.

## Preservation and provenance

The extended worker and its controls finished in 2300.14 wall seconds,
1851.25 parent CPU seconds plus 21.51 child CPU seconds, with peak parent RSS
2124.31 MiB. The separate evidence audit has its own measured cost in
`evidence_audit.json`. All numerical processes have exited. The earlier
1000-second L6 cap remains unchanged and unadmitted in the parent directory;
its partial values and all earlier failed/control runs are preserved.

`FINAL_REPORT.json` is the complete extended run record; `LABEL_ACCEPTED.json`
is the admission checkpoint. The three `d14_*.json` files and matching NPZs
retain actual eigenvectors, onsite operators, residuals and hashes. Probe
predictions and stdout/stderr remain separate. `plan.json` records source hashes
and a protected-file snapshot; the post-run audit confirms every protected
file is unchanged.

Primary local sources are the unchanged parent `direct_control.py` and
`truth_gate.py`, the original `adversary/champion_1_search` reports/teacher,
the original `evaluator/hidden/teacher.py` admission rules, and the byte-identical
`champions/generation_1/predict.py` copy. No public files, evaluator, status,
champion, old archive, or C artifact was modified. No fresh agents, additional
truth cases, complete dataset, target change, or official batch evaluation
were launched. **A complete D scalability ratchet remains unadmitted.**
