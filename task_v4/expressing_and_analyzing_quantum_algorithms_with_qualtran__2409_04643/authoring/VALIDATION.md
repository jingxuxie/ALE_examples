# Independent validation and decision limits

The reusable audits in `audits/` are generation-time checks, not participant
attempts. Their reports record script hashes and verify frozen-file integrity.
Neither audit writes participant, evaluator, or attempt files.

- Lookup: 14,336 independently evaluated rows, clean reversible lifts with
  address preservation and cleared workspace, six private passing designs,
  24 individual resource-boundary failures, 36 corrupted-row failures, and
  37 malformed-artifact failures. No serious verifier issue was found.
- Numerical: exact rational certificate checks, upstream extraction/guard
  equivalence, 80/120-digit reconstruction comparisons, and independent
  matrix-product quadrature. All 48 actual configuration records and their
  288 numeric fields were finite. Older positive witnesses are explicitly
  rejected by the final degree gate.
- Scheduling: independent live-edge and integer-summary accounting, exhaustive
  small-graph checks, and exact replay of baseline, private, and fresh schedules.

Two nonblocking implementation limits are recorded rather than hidden. The
lookup verifier accepts an ancestor-symlink submission path while rejecting a
linked artifact; tournament scoring uses fixed, generator-owned directories and
regular-file snapshots, so this does not bypass semantic or resource checks.
The numerical verifier has a latent NaN aggregation weakness under injected
internal faults. No admissible JSON exploit was demonstrated, and actual bounded
routes remained finite. The final package audit independently rejects any
nonfinite score field. Frozen evaluators were not patched during the tournament.

Numerical reconstruction is high-precision validation, not an interval-certified
transcendental proof. Logical resource counts are the stated representation-level
proxies, not hardware performance measurements. Ancilla and AND caps are
redundant for this particular retain-products lookup lift; depth and affine-size
constraints remain separately checked. A private passing design demonstrates
feasibility, not a one-hour discovery algorithm or a global optimum.

Only completed, nonexcluded fresh submissions count toward hardness. The failed
initial scheduling infrastructure run does not count. Current-domain numerical
solvability cannot be inferred from degree-14 or degree-48 historical witnesses.
