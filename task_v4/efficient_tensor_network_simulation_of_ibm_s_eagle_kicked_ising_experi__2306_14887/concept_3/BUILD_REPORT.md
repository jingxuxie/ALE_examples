# Generation-1 ratchet build report

## Launch-ready open candidate

The authorized current bound is **static Z drift +/-0.01 radians/site/layer**,
with unchanged **minimum fidelity target 0.95**. This is a
**hard_open_candidate; solvability UNKNOWN**. None of seven graded artifacts
passes. The former +/-0.005 witness is NOT a passing witness at this strength.
No fresh agent was launched for this ratchet; main owns v2 launch and status.

The circuit remains a 12-cycle, initially `|+>^12`, with 24 alternating
fixed-ZZ matching layers and bounded two-group RX angles. A static local
RZ interval follows every kick layer, including the last. Group gains remain
+/-2.5%, common ZZ gains +/-1.5%, and edge residuals +/-0.5%.

## Fixed suite and scores

There are **223 scenarios**: the exact original 63 zero-drift cases, 16
nominal structured/local Z cases, 64 coherent joint stress cases, 16 concrete
adversarial joint cases, and 64 held-out local-disorder cases. Core/worst/
held-out counts are 31/104/88. The participant gets 31 public examples.

| Artifact | Overall minimum | Core minimum | Worst-family minimum | Pass |
|---|---:|---:|---:|---|
| original_weak_baseline | 0.7482699165 | 0.7902458098 | 0.7482699165 | No |
| generation_0_fresh_champion | 0.9110914853 | 0.9525814063 | 0.9110914853 | No |
| generation_0_private_builder | 0.9270794988 | 0.9660914503 | 0.9270794988 | No |
| private_0005_not_a_001_witness | 0.9360934655 | 0.9675337692 | 0.9369108347 | No |
| private_continuous_001 | 0.9272893051 | 0.9652800737 | 0.9288067544 | No |
| private_branch_refined_001 | 0.9313229693 | 0.9549484463 | 0.9313229693 | No |
| private_discrete_branch_001 | 0.9207193615 | 0.9481787043 | 0.9207193615 | No |

The actual new-suite fresh-champion minimum is slightly below the earlier
0.911183 sidecar result because the frozen natural joint-stress family also
includes additional coherent endpoint combinations. Scores are computed
independently by the trusted full-state checker; all norms pass. Runtime
is approximately 10–13 seconds per 223-case grade on this host.

## Independent audits

- 24 full-state comparisons: maximum public/trusted difference
  5.148e-16.
- Independent compiled state-vector/trusted fidelity difference:
  9.975e-18.
- 12 dense Kronecker RX/RZ/ZZ gate checks: max error
  0.000e+00; norm deviation max 1.066e-14.
- Zero-drift evolution matches generation 0 exactly in the audit; all 63
  original scenario coordinates are preserved.
- Nonzero drift produces global-X expectation 0.901567
  in a tested case and is correctly accepted. Parity is asserted only for
  the 63 zero-drift cases; norm remains an invariant for all 223 cases.
- 18 malformed/missing/symlink artifacts rejected, including NaN, infinity,
  booleans, strings, invalid dimensions and oversized files; three invalid
  CLI outputs checked for all required result fields.
- The isolated public baseline runner smoke test passes. The original weak
  baseline pulse bytes are unchanged, and no private artifact/code hash
  occurs in participant assets.

## Archive, privacy, freeze

`generations/generation_0/` contains the exact original participant,
evaluator, status, freeze and builder documents. All 18
archived file hashes verify. All 5 first-tournament score
records retain their original bytes, resolving relocated private paths.
The original champion's 25 files are unchanged.

Prior raw attempts and the raw model log are quarantined under
`adversary/generation_1/tournament_0_raw/`; only the independently authored
weak baseline remains public. Do not expose prior fresh/private pulses or
solver source to v2. Main should expose only `participant/` and `attempts/v_2/`.

The current manifest freezes 12 public/trusted files before v2.
Verify with `python adversary/verify_freeze.py`. The hidden scenario digest
is `0753ffe6019891d37183bdd252a8a781fec81336d3ccc29925a3f0221bfedff9`. Candidate scores/audit detail reside in
`adversary/generation_1/ratchet_build/`. No private search diagnosis or
optimized artifact is placed in participant material.
