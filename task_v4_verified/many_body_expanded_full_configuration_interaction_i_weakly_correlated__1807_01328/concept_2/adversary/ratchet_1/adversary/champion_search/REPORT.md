# Private challenge result: actual fresh B2 champion

The officially solved B2 result remains **128/128**. Its submitted witness is
byte-identical to the archived generation-2 champion, SHA256
`c68347bd04610b929b040832fa2baea3b501ef78362c10974f91d23afe98cd66`.
The stopped earlier portfolio is preserved in `archive/portfolio_evidence.tar.gz`
with a per-file hash manifest. No participant, evaluator, target, root status,
previous submission, or original portfolio file was changed.

## Broad grid

Successes out of 128 independently drawn cases per cell:

| Uncertainty family | 0.001 Eh | 0.002 Eh | 0.003 Eh | 0.005 Eh | 0.010 Eh |
|---|---:|---:|---:|---:|---:|
| Original VV hopping and density | 127 | 4 | 0 | 0 | 0 |
| Previously fixed OV transfers | 0 | 0 | 0 | 0 | 0 |
| Diagonal pair energies | 128 | 128 | 128 | 126 | 102 |
| All density interactions | 128 | 128 | 128 | 124 | 79 |
| All effective-model coefficients | 0 | 0 | 0 | 0 | 0 |

The complete eight-family results, including fixed density, all pair transfers,
and previously fixed coefficients, are in `summary.json`. All 6,656 main-assay
cases remain physically admissible and retain the material missing tail. Failure
counts, which are not independent across paired cells, are 4,224 parent-gate
failures and 4,199 ratio failures, with no physical, material-tail, or numerical
failures. Maximum independent numerical disagreement is 6.395e-14 Eh.

## Separate confirmation at the unchanged 0.001 Eh radius

Three families use 512 new independent draws each:

- Original VV-only uncertainty: **512/512** pass.
- Previously fixed coefficients only: **1/512** pass.
- All 100 effective coefficients: **1/512** pass.

All 512 full-coefficient cases remain weakly correlated and well separated:
reference weights are 0.982613–0.983427, gaps 0.740160–0.747722 Eh, and diagonal
reference margins 0.961508–0.969688 Eh. Missing tails remain 99.537–111.478 microEh.
The triple maxima span 0.990210–8.239258 microEh: 511 cases lose the parent gate,
and 510 also lose the ratio condition. Paired with the exact same VV components,
511 cases change from a successful VV-only case to an unsuccessful full case.
These are finite reproducible assay counts, not a universal or population claim.

## Mechanism and controls

OV transfer uncertainty dominates; diagonal-energy and density uncertainty alone
are much less damaging at the original radius. For one saved paired example,
OV-only noise gives a 4.478222 microEh triple maximum. Removing OV noise from the
full perturbation restores a passing 0.880162 microEh maximum, while removing
other individual blocks does not restore the gate.

Additional 128-case diagnostic controls show:

- Full uncertainty while keeping all previously zero OO transfers zero: **0/128**.
- Absolute 0.001 Eh noise only on the 13 OV coefficients of magnitude at least
  0.01 Eh: **11/128**.
- Independent one-percent-relative OV noise: **111/128**.

Thus the result is not solely due to adding OO transfer support or applying a
large relative disturbance to nearly zero coefficients. Central finite
differences identify several OV directions with triple-increment sensitivities
around 0.003 Eh/Eh: a 1 mEh change can produce a roughly 3 microEh first-order
increment change. Two finite-difference steps agree to 3.11e-9 Eh/Eh. These local
diagnostics explain this champion; they do not bound all possible witnesses.

## Unfrozen proposal

`target_proposal.json` recommends a qualitative extension: uncertainty in **all
100 coefficients of the same effective model at the original 0.001 Eh radius**,
with the same nominal conditions and at least **122/128** successes. The nominal
42-control submission space can remain unchanged. This is not a proposal to
increase the VV radius or tighten the original numeric witness thresholds.

The proposed target's feasibility is **open**: no passing center is known, and
this challenge did not optimize a generation-3 witness. Main approval is required
before building or freezing anything. Fresh hidden directions would need to be
generated independently of this private challenge; none are generated here.
No previous privileged witness or artifact should enter future participant data.

"All coefficients" refers to the restricted seniority-zero pair-transfer/density
testbed, not an unrestricted molecular integral tensor. The finite-assay proposal
does not assert universal robustness or invalidate the original counterexample.

## Reproduction and resources

- `challenge.py`, `challenge_spec.json`, and saved uniform arrays reproduce the
  grid and predeclared confirmation. Main seed: `202608281207`; independent
  confirmation seed: `202608281208`.
- `diagnose.py` reproduces ablations, relative-noise controls and sensitivities.
- `examples/confirmation_full_coefficients_0p001_pass.json` and
  `examples/confirmation_full_coefficients_0p001_parents_ratio.json` save complete
  passing/failing perturbed Hamiltonians, coordinates, metrics and closure checks.
  A passing individual perturbation is not a passing robust center.
- Run `python -B challenge.py --reproduce examples/EXAMPLE.json </dev/null` for
  independent order-seven verification of an example.
- The main assay took **114.79 seconds**, including tests and representative
  complete-MBE checks: 6,727 engine evaluations and 869,876 diagonalizations.
  Supplementary diagnostics took **9.72 seconds** for 512 additional assay cases,
  ablations, independent checks, and local finite differences. These times exclude
  initial shell startup, authoring, and final audit.
- `tests.json` records independent bitmask/spin-fermion versus combination-basis
  Hamiltonians, independent eigensolver and increment paths, deterministic repeat,
  energy/density gauge invariance, and rejection of malformed/nonfinite inputs.
  `final_audit.json` verifies archived bytes, saved examples, and frozen hashes.
