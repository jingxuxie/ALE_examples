# Trusted evaluator and build provenance

Only `../participant/` is public. Never distribute `hidden/`, `attempts/`,
`champions/`, `adversary/`, or this evaluator to a scientific participant.
The hidden labels are loaded by the parent before launching candidate code;
only feature arrays are copied into the candidate's scratch directory.

From `concept_3/`:

    OPENBLAS_NUM_THREADS=1 python evaluator/evaluate.py --candidate participant/baseline --split hidden --report attempts/check.json

Submissions are directories containing `solve.py`. The trusted parent invokes
`sandbox_adapter.py`, which uses the task-root `authoring/sandbox_runner.py`
without modifying it, then tightens seccomp to deny clone/clone3. Numerical
libraries are loaded with one-thread limits before this tightening. Missing
Landlock/seccomp fails closed. Candidate output is never imported as code.
Parent rusage measures CPU; stdout/stderr JSON is not trusted. Every result
has `reason`, `core`, `worst`, `resources`, `pass`, and legacy `passed` fields
for an executed candidate. Invalid output has null scores and cannot pass.

Output validation rejects symlinks, nonregular files, oversized compressed or
uncompressed archives, invalid NPY shapes/dtypes before allocation, extra NPZ
keys, nonfinite values, and violations of sheet normalization. Candidate-tree
symlinks are rejected instead of dereferenced. An aggregate scratch-disk quota
is recommended for hostile multi-file disk-filling attacks.

## Frozen version 2.1 — READY

Before any fresh concept_3 launch, the parent requested a discrete/global
identifiability review. V2.1 scores active spectra up to one whole-sheet
permutation, eliminating a hidden sheet-name convention. Physical NPZ data,
resolution, noise, and accuracy/resource limits are unchanged. See
`IDENTIFIABILITY.md` and `hidden/global_identifiability.json`. The authoritative
baseline reports are `../attempts/baseline_*_v2_1_tuned.json`.

Participant resources, evaluator code, target, and test data are immutable
after READY. Private diagnostic reports may finish updating. Hardness remains
provisional until a fresh scientific attempt is measured; no passing private
predictor is required to launch this explicitly open candidate.

V1 was rejected after its baseline passed comfortably. The user explicitly
authorized pre-tournament redesign of the same concept; it is archived under
`adversary/prelaunch_v1/`. No fresh scientific agent was run by this builder.
Bounded calibration used public training/validation cases only. Probe-average
targets remained easy across noise/resolution and frequency grids. V2 instead
scores physically sheet-resolved masses with the original per-window absolute
mass tolerances. The public sheet count is structural information, not a hidden
family/parameter leak. Train/validation seeds were retained for paired public
calibration; hidden test and private audit seeds were freshly drawn. No cases
were rejected, replaced, or selected by their scores.

The target is frozen in `hidden/target.json`, hash-checked against
`hidden/data_manifest.json` before every evaluation. Public resources, scoring
code, hidden data, and the external shared-runner hash are recorded in
`hidden/freeze_manifest.json`. Do not regenerate or retune the target after
a fresh scientific attempt. `build_data.py` rejects a second v2 regeneration.

## Evidence and limitations

- `hidden/baseline_tuning_v2.json`: six ridge strengths, public validation only.
- `../attempts/baseline_*_v2_tuned.json`: selected baseline, isolated and scored.
- `hidden/physics_checks.json`: PSD Nambu residues, direct complex forward
  map, independent quadrature, normalization, noise, and data hashes.
- `hidden/identifiability_local.json`: local Fisher diagnostics at true latent
  locations; these are explicitly **not** predictive evidence.
- `hidden/blind_audit.json`: expensive inference initialized from independently
  generated public-family models; inference receives observations, noise, and
  public sheet count only. Labels are loaded after predictions finish.
- `../adversary/report.json`: 21 output/security checks and label-replay scorer
  sanity. The latter is not an attainability claim.

The blind audit reaches core 0.849 but worst-family 1.328 on 12 cases, narrowly
missing 1.25. Its 137.8 CPU seconds do not establish a 64-case/180-second solver.
The local prior diagnostic is borderline, particularly for three sheets, and
does not certify global uniqueness. Status remains `hard_open_candidate`.
The retuned baseline fails all gates, but its 1.425/1.773 validation metrics are
slightly below the suggested 1.5/1.8 calibration margins. This is reported,
not repaired by a post-freeze target change.
