# Privileged generation-two passing witness

Status: **official frozen-evaluator pass** on August 28, 2026. This is a
post-deadline generation-worker construction, not a fresh-agent success and not
a hardness conclusion. No live generation-two v3/v4 attempts were read.

## Artifact and exact proof

- `control.json`: portable data-only witness, identical to `blend10_25.json`.
- Raw artifact SHA256: `14e1480d990bbd59998af6ce86d97ce791c9fc23ef73f4e391b5bc3ccfe6214c`.
- Canonical artifact SHA256: `f37ce864fe17b04107d07931b2df71e94390fe9f3959798c422d4418300c03e8`.
- `evaluation.json` and `evaluation.log`: actual unmodified root evaluator CLI output.
- `proof.json`: exact command, frozen evaluator/reference hashes and artifact binding.
- `manifest.json`: sidecar witness/source hashes and environment.

Audited core = **0.992060421218**, worst family =
**0.985187020602**, minimum case =
**0.980152776816**. Targets remain **.990 / .985 / .980**.
All 37 cases and every configured numerical audit pass. Maximum boundary mass
is `8.86339019821e-09` against `1e-8`; maximum
fidelity allowance is `1.78087354987e-05`. Runtime was
`559.209603` seconds, runtime score
`0.321882880650`, resource score `0.813002211837`.

## Reproduce the official grade

Run from `concept_3/adversary/gen2_proof_search/`:

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
/usr/bin/python3 -I -B ../../evaluator/evaluate.py --artifact control.json --output reproduction.json
```

The root participant, evaluator, references, generations, champions and attempts
were not modified. The trusted full reference caches already existed before the
CLI launch. Its solver and cache hashes remained unchanged throughout grading.

## Construction provenance

The initial seed is the preserved completed G1 v2 champion. Reviewed G1 v2
`optimize.py` was copied here and adapted for complex128 discrete adjoints,
family-balanced risk objectives, a threshold hinge and boundary penalties.
Training used all 37 private frozen cases, which is generation privilege.
Three bounded SLSQP runs completed 146, 61 and 38 iterations; their inputs,
parameters, hashes, histories, checkpoints and completion records are retained.
The passing free spline coefficients are the convex blend
`0.75 * hinge64.iter010.json + 0.25 * risk60.best_score.json`.
`blend10.provenance.json` binds both preserved parents by SHA256. Every control
was checked with the frozen amplitude, slew, acceleration and RF-radius rules.

`gradient_check.json` records all-six-channel finite-difference checks, with
maximum absolute gradient discrepancy `2.163922374620597e-10`, and an independent
trusted-forward fidelity difference `9.214851104388799e-14`. Additional hinge
finite differences passed with maximum discrepancy `2.0072500106493862e-08`.

The scientific connection remains the frozen XMDS2-inspired coupled nonlinear
Gross-Pitaevskii/spectral atom-optics control task. No equations, target fields,
uncertainty ranges, numerical guards or thresholds were changed; the scientific
sources remain in the root `participant/input/SOURCES.md`.

## Uncertified alternative

`fallback_25.json` has a stronger 64x32, dt=.02 surrogate minimum
`.9815100933033553` with boundary mass `2.9155648645242325e-9`. Its core/family
scores are `.9917303209920704 / .9854881980057878`.
**It has not been officially graded.** It is not substituted for the certified
`control.json`, and its coarse score is not proof of a pass.
