# D longer-chain backup: closed, no admitted ratchet

**Original D remains solved, with ratchets 0 and its original 360/360 passing
audit unchanged.** Its domain is L2/L3. The L4/L5/L6 results below are private,
out-of-domain generation probes, not original-D failures and not a frozen
generation or official full-suite hardness result. A complete longer-chain
extension's **solvability remains unknown**.

## Demonstrated labels

One pre-existing pilot at each length has passed the unchanged empirical
cutoff/basis/residual admission rules, including actual onsite 80-to-160 and
changed-frequency confirmations. L4 also has saved independent full-Fock
cross-checks. Values are finite-chain numerical labels, not extrapolated truths
or rigorous infinite-Hilbert-space ground-state certificates.

| Length | Retained local states | Odd gap | Even gap | Odd spacing |
| --- | ---: | ---: | ---: | ---: |
| L4 | 16 | 0.000244376917613 | 1.60653404719 | 1.65419948708 |
| L5 | 14 | 0.00135641238452 | 1.13283141661 | 1.18439213858 |
| L6 | 14 | 0.0000434545381906 | 1.35870469247 | 1.36852088705 |

Exact values and certificates are in `L4/result.json`, `L5/result.json`, and
`L6_extended_4000/FINAL_REPORT.json`. The original 1000-second L6 run remains
unchanged and unadmitted; the later extended run, not finite d12, supplies the
accepted L6 label. Its actual eigenvectors, operators, logs and post-run
residual audit remain in `L6_extended_4000/`.

## Source-native controls

The table shows measured **single-case mean absolute log errors**, judged
against the original accuracy thresholds. It is not a batch resource score.

| Length | d4 | d6 | d8 |
| --- | ---: | ---: | ---: |
| L4 | 0.298406 — fail | 0.027615 — pass | 0.001140 — pass |
| L5 | 0.254053 — fail | 0.011891 — pass | 0.000268 — pass |
| L6 | 0.352975 — fail | 0.017378 — pass | 0.000412 — pass |

The generalized d16 L6 control additionally has a genuine measured 2-GiB
memory-limit failure: its ARPACK Krylov array alone requests 1.50 GiB on top
of existing allocations. The literal old champion's unsupported-L6 indexing
error is excluded from scientific evidence. Neither failure says that every
adaptive, smaller-basis or efficient solver fails; d6/d8 already pass all three
individual pilots. Timings are generation-only controls, not official
30-CPU-second full-batch scores.

## Closure and preservation

No further numerical computation, cases, dataset, fresh launch, or D generation
was performed during this closeout. All owned D workers, probes and the
saved-vector audit have exited; this sidecar is quiescent. Earlier failed and
budgeted runs remain intact. `BACKUP_SUMMARY.json` provides exact metrics,
source references, and hashes of the unchanged original D status and audit.
Participant, evaluator, status, champions and original 360-case evidence were
not edited. No complete extension dataset or frozen contract exists, so no
extension solvability or hardness claim is made. The main agent can close this
backup without changing original D's solved status or ratchet count.
