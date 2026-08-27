# Reference correction, not participant failure

The initial grading showed near-perfect numerical agreement in five families and a large discrepancy in the flux-ring family. This discrepancy was investigated before making a difficulty decision.

The reference had omitted an occupied bound state at energy −2.000434339205876, only 0.00043434 below the continuum edge. Both its nominal and refined finite localization domains failed the same tail-probability cutoff, so their agreement was a false completeness check. The missing central probability is 0.198604416899713.

Independent verification, without fitting to the participant's transient outputs:

1. Solve the real-energy retarded secular equation outside the union of scalar-lead bands and normalize the pole residue with I−dΣ/dE. The missing pole's density accounts for the initial discrepancy to 1.01e-8 per orbital.
2. Solve a separate 3,084-orbital Hermitian system with 1,024 cells per reservoir. Its energy differs from the analytic pole by 1.78e-15 and its central probability profile by 6.28e-14. Outer-edge probability is 1.66e-23.
3. Repair the reference's scalar-lead discrete spectrum using secular roots and infinite-tail normalization, retain the independent finite search for in-band dark states, and rerun the unchanged physical ring experiment.

Supporting files: `screening/independent_ring_poles.json`, `screening/independent_long_lead_pole.json`, `private/check_ring_poles.py`. The previous erroneous ring target is preserved in this directory as `incorrect_ring_gold.npz` and `.json`.

The original 0.6666 core score is invalid and superseded: it must not be counted as an agent failure, moderate task, or evidence of frontier hardness. Only the corrected grading can be used. No participant input, task instruction, physical model, scoring formula, numerical tolerance, runtime/memory limit, or classification threshold changes. The participant receives no feedback and is not rerun with privileged information; its completed, immutable executable is replayed against the corrected independently verified reference.

This is a reference repair, not a fundamental redesign of the participant task.
