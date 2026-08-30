# Generation-two private author report

All writes are confined to concept_3/generations/generation_2. No fresh
agents were launched and no previous fresh solver or witness was copied.
The baseline derives only from the original PUBLIC unstructured-search code.
The unchanged initial privileged author witness is retained privately as a
reference, not a fresh champion.

## Independent replication

Four families now have 32 members each. Required coverage is 24/32 (75%).
The numeric core, worst-family, base, and member-floor targets remain
0.060, 0.050, 0.055, and 0.025. Public and private banks have different
independent 256-bit OS-entropy seeds. Both were fixed and the private bank
committed before any scoring. No bank was resampled or selected by scores.
Private protocol SHA-256: `9fbe62920caf6f7eb5bbe677f203b63c5522681ecfbf44be4e35bc1159bbc652`.

## Recorded scores

| Witness | Bank | Core | Worst family | Valid | Pass |
|---|---|---:|---:|---|---|
| Unstructured baseline | Public | 0.005100457084 | 0.000866847516 | True | False |
| Unstructured baseline | Private | 0.004549137404401642 | 0.0012310790727466346 | True | False |
| Old privileged reference | Public | 0.054415415846 | 0.048965351874 | True | False |
| Old privileged reference | Private | 0.05790733789809299 | 0.0552733977242322 | True | False |

Generation-two solvability status: open; no passing generation-two witness established. No stronger-witness
search was run; no reference-solution search delays readiness.

## Validation and resources

15 malformed/static controls passed, plus separate checks for
commitment mismatch and rejection of a public bank as grading data. Both
commitment faults return evaluator_valid=false, whereas invalid witnesses
return evaluator_valid=true and valid=false. All report aliases were checked.
The evaluator does not expose private per-member diagnostics or seeds.

Independent evr/evd checks covered the base and one member per family:
maximum statistic disagreement 1.45e-13.
Private evaluations took 11.275 seconds for the
baseline and 10.185 seconds for the old reference.
The 180-second limit is retained for 129 full spectra with one worker and
one BLAS thread; the memory ceiling remains 2 GiB.

The main runner owns final package freeze and launch. ready_manifest.json
hashes all participant/evaluator assets. The private seed, old reference,
ratchet stress summary, and all validation artifacts stay under adversary/
or evaluator/hidden/, never in the tested participant bundle.
