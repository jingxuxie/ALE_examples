# Completed G2 alternative-output fairness audit

**Outcome: no eligible pre-cutoff alternative passes. No generation 3 is built.**
The audit supports retaining G2 as `hard_verified_achievable` under the main
worker's classification policy; it does not claim mathematical impossibility.
The independently reproduced private G2 witness remains separate and untouched.

## Eligibility and coverage

- Both `v_3.run.json` and `v_4.run.json` report non-running status before any
  attempt content is read. Every eligible original is checked against its exact
  `submission_sha256` cutoff entry, then copied byte-for-byte.
- All 163 recorded files match their cutoff hashes. There are 23 exact-schema,
  hardware-valid control files representing 22 distinct controls: the two
  canonical submissions and 20 noncanonical alternatives, all from v4.
- v3 explicitly acknowledges failure and deletes other outputs before handoff.
  Deleted/transcript-only material is not reconstructed. v4's `robust.json` is
  an unrecorded FIFO, not a regular JSON artifact; its payload is never read.
- All 22 distinct controls are screened on all 37 frozen cases at 64x32,
  dt=0.02: 814 control-case combinations. No alternative is within 0.001 of
  every required threshold. Coarse output is never accepted as a proof.
- Every one of the 20 alternatives is independently refined on its weakest
  screened frozen case using the official 80x40/dt=0.01, 112x56/dt=0.01,
  and 112x56/dt=0.005 solver configurations and existing official references.
  Twelve selected cases pass all audits and fail fidelity. Eight violate the
  boundary guard; no other guard fails. All twenty selected-case fidelities,
  even with the empirical allowance added rather than subtracted, remain below
  0.980; the largest is 0.9770657855871702. This is an empirical convergence
  check, not a rigorous mathematical upper bound.

## Exact frozen-evaluator results

| Original v4 file | Valid / passed | Core | Worst family | Worst case |
| --- | --- | ---: | ---: | ---: |
| `candidate.json` | true / false | 0.9906051220519476 | 0.9794202299187912 | 0.9711682979219932 |
| `minimax_060.json` | false / false | 0 | 0 | 0 |
| `robust_before_penalty.json` | false / false | 0 | 0 | 0 |

The last two receive zero official scores because they violate the boundary
guard. Their *pre-audit-rejection diagnostic* triples are respectively
0.9925136614133379 / 0.9822178878444381 / 0.9728923832615203 and
0.9940353462073042 / 0.9855142782304979 / 0.9770191615019223.
These are not valid passing scores. The strongest nominal saved checkpoint
therefore misses the minimum-fidelity target even before boundary rejection.
Boundary maxima are 5.7403320595286835e-9, 1.7941072130434645e-8,
and 2.41052426408167e-6, against the unchanged 1e-8 guard.

The first selection grades the strongest alternative with clean coarse
boundary/norm diagnostics. Its official boundary failure illustrates why those
diagnostics cannot certify validity. Supplemental full grades cover the
strongest nominal checkpoint and a lower-leakage candidate. All three full
results agree with the separately refined necessary-case scores within 1e-10.
The other alternatives are excluded by necessary-case violations, not by
extrapolating a coarse aggregate score or by assuming a filename is final.

**Filename selection understated v4's improvements, but hid no passing witness.**
No optimization, coefficient reconstruction, coefficient postprocessing, fresh
agent launch, root edit, attempt edit, champion archive, or G3 construction occurs.
The original v3/v4 official canonical grades are consumed, not redundantly rerun.

## Evidence

- `inventory.json`: completion gates, cutoff hashes, exact copies, exclusions,
  hardware certificates, duplicates, and frozen-source hashes.
- `handoff_review.json` and `excluded_special_outputs.json`: final claims,
  cleanup, checkpoint naming, and the unrecorded FIFO exclusion.
- `screening.json`, `screens/`, and `screen_inputs.json`: all 814 surrogate
  control-case scores and reference provenance.
- `failure_checks.json` and `failure_checks/`: all 20 necessary-case A/B/C
  refinements, error allowances, state checks, and numerical guards.
- `official/`: three unmodified evaluator outputs, logs, original-file hashes,
  selection records, exact commands, and before/after provenance checks.
- `conclusion.json` and `manifest.json`: machine-readable final decision and
  hashes of the sealed evidence. Main retains ownership of campaign metadata.

## Reproduction

Run from the `concept_3` directory. No fresh optimization code is executed.
The wrappers require existing official reference files and verify their hashes;
they refuse to create a missing reference cache under the protected evaluator.
Every generated file stays under this audit directory.

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
/usr/bin/python3 -I -B adversary/alternate_output_audit/audit.py
/usr/bin/python3 -I -B adversary/alternate_output_audit/refine.py --mode failure-checks &
/usr/bin/python3 -I -B adversary/alternate_output_audit/refine.py --mode official-top &
/usr/bin/python3 -I -B adversary/alternate_output_audit/refine.py --mode official-top --candidate v_4__robust_before_penalty.json &
/usr/bin/python3 -I -B adversary/alternate_output_audit/refine.py --mode official-top --candidate v_4__candidate.json &
wait
/usr/bin/python3 -I -B adversary/alternate_output_audit/finish.py
```

The direct official command used for the valid alternative is equivalent to:

```sh
/usr/bin/python3 -I -B evaluator/evaluate.py --artifact adversary/alternate_output_audit/artifacts/v_4__candidate.json --output adversary/alternate_output_audit/replay.evaluation.json
```

The screen takes 388.8 seconds, the 20 necessary-case refinements 122.1 seconds,
and the three full grades 249.6, 268.5, and 251.0 seconds. These components
overlap; summing them is neither elapsed wall time nor measured CPU usage.
The bounded sidecar finishes in approximately 21 minutes including setup and
sealing. Original artifacts, all 37 cases, thresholds, and audits stay unchanged.
