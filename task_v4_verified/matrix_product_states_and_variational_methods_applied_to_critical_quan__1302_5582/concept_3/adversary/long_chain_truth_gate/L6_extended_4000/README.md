# One-case extended L6 truth gate

Generation-only extension explicitly authorized after the original 1000-second
run. All prior bounded-run files and reports remain unchanged. Only the same
inhomogeneous L6 pilot is used; no new cases or complete dataset are generated.

The extended teacher has a 4000-second wall/CPU budget and 8-GiB address-space
limit. It requires a completed retained-d14 (or d16 if needed) solve, two
successive cutoff log changes <=2e-5, actual onsite Fock 80→160 re-solves, an
independent oscillator frequency 2.0→2.34, all four state residuals <=1e-10,
residual-plus-roundoff/gap <=2e-6, and a dimensionless gap floor of 1e-6.

The reviewed matrix-free Hamiltonian and ARPACK eigensolver are reused. A
parity-preserving diagonal phase gauge fixes neighboring onsite position
matrix elements positive, allowing saved eigenvectors to seed subsequent
actual eigensolves. Warm starts do not replace a solve, waive a residual check,
or promote the old finite-d12 estimate to truth. Full-support initial noise
and a different Krylov dimension are used for confirmation runs. An L2
implementation check compares this gauge/seed variant with the unchanged
source-native code before the expensive L6 work.

Every completed stage retains JSON diagnostics and NPZ eigenvectors/local
operators. Only `LABEL_ACCEPTED.json`, if present, establishes numerical
admission. This is an empirical finite-chain convergence certificate, not a
rigorous infinite-Hilbert-space ground-state claim.

After admission only, the literal unchanged champion and reviewed general-size
source-native controls are probed on this case. Unsupported old API lengths
are not counted as scientific failures. The 30-CPU-second/60-wall-second/2-GiB
single-case probes are generation diagnostics, NOT official 30-CPU batch scores.
Neither a complete corpus nor a hardness claim is produced. C, public files,
evaluators, statuses, and previous champions remain untouched.

## Completed result

The L6 label is now numerically admitted after all unchanged checks.
`FINDINGS.md` summarizes the certificate and measured d4 accuracy/d16 memory
failures, alongside the passing d6/d8 controls. No complete scalability ratchet
or official batch-hardness claim is admitted. All jobs have stopped; preserved
evidence is indexed by `FINAL_REPORT.json` and `evidence_audit.json`.
