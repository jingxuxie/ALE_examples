# D long-chain truth gate: final findings

No admissible scalability ratchet is established by this bounded gate. Uncertified lengths remain excluded from all truth and failure claims. The certified pilots show the already-known four-state truncation failures, but no new failure of the reviewed six/eight-state source-native controls. A complete independently certified corpus and actual full-batch efficient-control measurements remain missing; isolated timings are not extrapolated.

No public/evaluator/status changes, no fresh agents, no new frozen target, and no C work. Original D remains solved on its original 360-case domain.

## Strengthened private labels

| Sites | Certified | Retained states | Odd gap | Even gap | Odd-sector spacing |
|---|---|---:|---:|---:|---:|
| 4 | yes | 16 | 0.000244376917613 | 1.60653404719 | 1.65419948708 |
| 5 | yes | 14 | 0.00135641238452 | 1.13283141661 | 1.18439213858 |
| 6 | **no; excluded** | — | not a label | not a label | not a label |

Each accepted label has two successive retained-basis convergence checks, onsite Fock doubling 80→160, an independent frequency 2.0→2.34, four parity-resolved residuals, and the original gap-floor/roundoff tests. Absolute even/odd energies and the ground energy are retained in JSON. The certificates remain empirical, not rigorous infinite-space tail bounds.

The independently assembled full-Fock implementation agrees with a complete rotated local basis at L2 to about 1e-15. L4 additionally has direct full-Fock cutoff-24/32 cross-check records. See `implementation_validation.json` and `L4/result.json`.

## Measured source-native controls

| Sites | Retained states | Mean log error | Maximum log error | CPU seconds | Single-case thresholds |
|---|---:|---:|---:|---:|---|
| 4 | 4 | 0.298405916 | 0.871283524 | 0.0738 | FAIL |
| 4 | 6 | 0.0276145872 | 0.0646091358 | 0.1247 | pass |
| 4 | 8 | 0.00113956896 | 0.00223246512 | 0.2043 | pass |
| 5 | 4 | 0.254053174 | 0.619996932 | 0.1122 | FAIL |
| 5 | 6 | 0.0118908681 | 0.0308258901 | 0.3285 | pass |
| 5 | 8 | 0.000268060798 | 0.000717886153 | 1.3242 | pass |

The four-state failures are actual inaccurate parity splittings, not shape errors or timing artifacts. They do not by themselves establish useful hardness: the six/eight-state controls must be judged separately. These are source-native adapted controls, not an accusation that the original L2/L3-specific champion fails a contract it was never given.

Single-case CPU measurements are not extrapolated into a 72-case resource verdict. A small fixed basis failing is not evidence that all direct solvers, adaptive bases, sparse methods, or tensor methods fail.

## Evidence and limits

- L4: `L4/result.json`; original numerical admission conditions plus 80-to-160 onsite-cutoff check passed. Computed retained counts: [6, 8, 10, 12, 14, 16].
- L5: `L5/result.json`; original numerical admission conditions plus 80-to-160 onsite-cutoff check passed. Computed retained counts: [6, 8, 10, 12, 14].
- L6: `L6/result.json`; unconverged or uncertified within fixed numerical budget; not a label and not failure evidence. Computed retained counts: [6, 8, 10, 12].
- `certified_cases.json` contains only accepted labels; unresolved L6 diagnostic estimates must never become targets.
- `FINAL_REPORT.json` contains full certificate maxima, source hashes, control predictions/errors, measured CPU times, and the admission decision.
- `completion.json` confirms all bounded numerical workers stopped and original public/evaluator/champion files remain unchanged.

## Primary local sources

- `../champion_1_search/FINAL_REPORT.json`, `../champion_1_search/FINDINGS.md`, and `../champion_1_search/target_proposal.json`: prior evidence, exclusions, and unmet freeze gates.
- `../champion_1_search/direct_control.py`: reviewed open-chain dressed-onsite matrix-free source; `direct_control.py` is a byte-identical copy.
- `../champion_1_search/extension_teacher.py` and `../../evaluator/hidden/teacher.py`: numerical admission rules and correctly projected oscillator operators.
- `../../champions/generation_1/predict.py`: original winning source, reviewed but not blamed for unsupported longer-chain schemas.
- `../champion_1_search/private/extension_seeds.json`: the three fixed pre-existing pilot parameter sets; no new performance-conditioned sampling.
