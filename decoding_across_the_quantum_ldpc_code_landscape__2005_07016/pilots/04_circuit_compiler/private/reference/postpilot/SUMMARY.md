# Verdict: discard this proposed compiler ratchet

The fresh submission's tournament mean_core is 1.5858517822 and worst_family
is 0.8209289211. All four performance outputs and both semantic audits are exact.
The only below-reference case is surface distance 7 / 8 rounds: 0.24 CPU seconds
against the stored reference baseline of 0.15. That is a timing penalty, not a
semantic error. It is not defensible to attribute the entire difference solely
to interpreter startup: the controls show variable system/output overhead too.

The implementation at `attempt/solve.py:104` stores sparse sensitivity sets;
`reverse_instructions` traverses repeats without flattening the input. Thus
the proposed detector-wide-bitset weakness does not apply to this submission.
Three isolated small-case profiles are all exact: total CPU 0.04, 0.14, and
0.16 seconds; reverse compilation itself takes 0.0080, 0.0040, and 0.0040 seconds.
Output CPU varies from 0.0040 to 0.0684 seconds. No scorer or threshold changed.

Exactly two additional scientific regimes were tested:

| Same-contract regime | Faults | Detectors | Exact terms | Submission CPU | Full reference CPU | Native Stim CPU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Surface d=7, 512 rounds | 381074 | 24576 | 191824 | 0.76 s | 2.41 s | 0.3403 s |
| HGP n=76, 128 rounds | 223512 | 8579 | 143647 | 0.68 s | 2.75 s | 0.3742 s |

All four end-to-end runs return successfully with semantic quality 1.0 and
exact agreement at the unchanged tolerance. All fit the unchanged 8 CPU-second
and 1536 MiB limits. Submission peak RSS is 42388 / 36652 KiB; reference peak RSS
is 226032 / 227676 KiB. Reference wrapper feasibility is measured, not inferred
from the faster native compilation kernel. Native recompilation agrees with
the saved DEMs; noise-free detector/observable checks also pass.

These are the existing official Stim surface constructor and official ldpc
CSS/HGP constructor, using identical Pauli channels and the same HGP seed, with
only extraction duration increased (64x and 12.8x). Source URLs and the bounded
test specification are in `PLAN.md`. No new gates, format tricks, thresholds,
external agent, or curriculum/ratchet changes were introduced.

There are zero verified substantive counterexamples. The submission handles
both scientific scaling regimes tested, so discard pilot04 as a proposed
hardening/selection candidate on this evidence. This is a bounded empirical
conclusion, not a proof about every allowed circuit.

Evidence: `report.json`, per-regime statistics JSON, submitted-code snapshots,
and the inputs/exact answers/Stim/DEM files in
`private/challenge_pool/postpilot/`. The original submission hash is unchanged.
All persistent audit writes are confined to the two authorized postpilot trees.
