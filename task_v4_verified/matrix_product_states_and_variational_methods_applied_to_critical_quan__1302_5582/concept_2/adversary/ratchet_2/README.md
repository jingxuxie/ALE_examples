# C ratchet generation 2: critical-vacuum-v3

The participant and evaluator are freeze-ready. The user fixed the new
composite-covariance maximum relative error at **0.01** before fresh v3 attempts.
This is stricter than the historical fourpoint_search proposal's 10% diagnostic
threshold. No fresh agents were launched by this builder, and no passing v3
tensor or feasibility result is known.

All v2 physics and resource requirements are retained: even D<=24, right
canonical form, fixed parity convention, full-rank stationary density,
primitivity, energy excess<=5e-5, xx<=2.5% at r=1..1024, connected zz<=10% at
r=1..256, yy<=10% at r=1..128, one-hour construction budget and 120-second
evaluator timeout. The new fifth family is the maximum composite-order
covariance relative error over the 60 explicit public quartets with span<=256.
There is no additional raw-four-point-only scoring gate.

The measured covariance subtracts the submitted state's own left and right
interval means. Exact targets subtract exact means and use a stable Cauchy
product/expm1 identity. Submitted raw four-point values are contracted directly
from the tensor, never reconstructed from submitted two-point curves.

## Baseline

Only `champions/generation_2/state.npz` was copied into the participant baseline.
It has SHA-256
`0da59e2f4f8eefca2ff34137bb1c44664d5607aa5fbbaa253efe85e054e90e5b`.
The old baseline build script is removed; no previous construction code is
included. The baseline is admissible and all four v2 families still score 1.
Its new composite error is 0.20978908908719263, giving core score
0.5440557699601863 and worst-family score 0.047666921304204704. It fails v3.
The official baseline check takes about 0.817 seconds in this validation run.

## Independent validation

- Legacy normalization, finite-ring tensor enumeration, stationary-limit and
  finite-spin checks pass: `legacy_validation.json`.
- 790 finite periodic spin-ED quartets at N=6,8,10,12 agree with the finite
  sine determinant within 2.276e-15 absolute: `ed_certificates.json`.
- All 60 infinite covariance targets agree with separate dense determinants
  within 2.444e-16 absolute: `exact_target_certificates.json`.
- Baseline four-point contractions agree with the independent prior adjoint
  contraction helper within 1.527e-16 absolute. Using exact rather than submitted
  interval means is a detected negative control, not an equivalent convention.
- The baseline's entire v2 energy/xx/zz/yy output is unchanged from the earlier
  independent audit, with zero numerical difference.
- 22 malformed/container/symlink cases are rejected by the trusted function,
  public CLI and official CLI. Numeric NPY versions 1,2,3 remain accepted.
  Oversized declared array shapes are rejected before allocation.
- Public and trusted physics sources are byte-identical. Synthetic boundary
  tests cover each of the five score limits; these are not physical witnesses.

`validation.json` consolidates results. `baseline_score.json` and
`baseline_public_score.json` independently score the supplied baseline.
`artifact_rejection.json` retains per-interface rejection evidence.
`freeze_manifest.json` hashes every participant/evaluator file and records the
fixed threshold and resource limits. `status.json` at the concept root points
to this generation and explicitly leaves solvability unknown.

Revalidate without accessing any previous attempt construction code:

```sh
PYTHONDONTWRITEBYTECODE=1 python evaluator/hidden/test_validation.py
PYTHONDONTWRITEBYTECODE=1 python evaluator/hidden/test_ratchet_2.py
PYTHONDONTWRITEBYTECODE=1 python adversary/ratchet_2/freeze.py
```

All builder writes are restricted to the authorized participant/evaluator,
concept status, and `adversary/ratchet_2*` scope. Old generation archives are
unchanged. No tests or build actions launch participants.
