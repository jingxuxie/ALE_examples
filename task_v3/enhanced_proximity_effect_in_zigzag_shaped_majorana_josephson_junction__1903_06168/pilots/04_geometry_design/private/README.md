# pilot04_geometry_design — author build

One concept: manufacturable, robustness-aware geometry design beyond an unoptimized zigzag. No agent or participant pilot has been launched. The participant attempt is intentionally empty.

## Provenance

- Original concept: Laeven et al., arXiv:1903.06168; PRL 125, 086802 (18 August 2020).
- Existing strong implementation: Melo, Tanev, Akhmerov, arXiv:2205.05689 (11 May 2022; v3 31 October 2022); SciPost Phys. 14, 047 (23 March 2023), https://doi.org/10.21468/SciPostPhys.14.3.047.
- Immutable source artifact: https://zenodo.org/records/7266609, v2; direct https://zenodo.org/records/7266609/files/code.zip?download=1. The record's publication date is 11 May 2022; this version was created 31 October 2022. MD5 `750859a1c2c847acdff9eda0ed24873e`.
- The complete ZIP is preserved privately, including `optimization.py`, `utils.py`, both notebooks, historical environment/license, and all full optimization histories. It expands to 97,096,765 bytes. The author optimizer performs projected perturbation ranking, multi-update epochs, random operating-point shifts, and median filtering. None of that optimizer is exposed to the participant.
- Strong anchors are unmodified epoch-800 masks from the homogeneous filtered, 980 nm filtered, and chemical-potential-mismatched filtered histories. No alleged optimal design was synthesized for this task. `private/reference/manifest.json` records member hashes, dimensions, and changes limited to key naming/removal of unused empty gate masks.

The archived optimizer targets Kwant/MUMPS, sparse, scikit-image, and a Dask cluster helper. This pilot preserves its real outputs without executing or repairing that optimizer. The supplied forward-only SciPy engine implements its finite-difference Hamiltonian independently of that runtime. The source-consistency check compares a recomputed 51-point half-zone gap with the archived 101-point full-zone gap, alongside Hermiticity, particle-hole symmetry, and dense-vs-block Pfaffian checks. Stored mask dimensions, not stale notebook dimensions, define each grid.

## Author commands

Run from the pilot root, which contains only `participant/`, `private/`, and the empty `attempt/`. The archive is in the authorized task-root source directory.

```sh
python private/reference/prepare_reference.py --archive ../../source/greedy-geometry/code.zip
OPENBLAS_NUM_THREADS=1 python private/reference/check_forward.py --full
OPENBLAS_NUM_THREADS=1 python private/evaluator.py --calibrate --workers 3 --output private/reference/calibration_report.json
python private/evaluator.py --export-requests private/exported_requests --output private/export_report.json
python private/evaluator.py --results-dir private/returned_results --workers 3 --output private/score_report.json
python private/reference/check_build.py
```

The evaluator uses a **results-directory handoff**, not a `--solver` option. It only exports requests, measures existing reference geometries, or scores returned JSON. **It never launches a solver.** The fresh agent's working directory is `participant/`, not the pilot root. The common sandbox wrapper supplies an absolute writable attempt directory and invokes `python /absolute/attempt/solve.py --input REQUEST --output RESULT`, replacing the placeholder with that assigned path. It enforces the declared resource budget and stages each result as `<request_id>.json` in the directory passed to `--results-dir`. Public helper paths are therefore `workspace/` and `input/`; public output paths use the assigned absolute attempt directory. Mount only participant-facing files, the writable attempt directory, and scratch space. Do not expose this README, `private/`, the follow-up source directory, or the unrestricted host filesystem. The evaluator is not an OS security sandbox.

## Readiness and limitations

Do not allocate participant runs until `forward_check.json` has `full_source_comparison: true` and all three 51-point calibrations have `ready: true` under the current scoring rule. Physical measurements are tied to physics/request/scenario/reference hashes; calibration also checks the scoring version. Anchor measurements store all 51 momentum-resolved gaps per operating point, not just scalar scores. Scoring always recomputes participant physics; it has no equality/hash shortcut for a known design.

Normalized improvement is unbounded: weak 0, strong 1, with neither upper nor lower clipping. Reports expose `core_feasibility`, `core_score`, and `worst_family_score`/`worst_family`. Invalid results fail the core feasibility gate, independently of their zero bookkeeping score. Compare full feasibility first, then mean improvement and worst-family improvement.

The initial clipped scoring rule was revised before any participant launch. `reference/scoring_revision.json` records the old/new code and checkpoint fingerprints. All forward-model bytes and all measured numerical values were preserved; only verified physical checkpoint keys were migrated, and derived calibration was rebuilt under the new rule. `reference/strong_reference_check.json` is a separate full forward reevaluation of the exact archived strong geometries through the returned-results interface, not a solver run.

This task uses a fixed 20 nm lattice and a finite momentum grid; it does not claim continuum convergence, device-specific electrostatics, orbital-field realism, or disorder-ensemble performance. Family shifts are supercell/transverse size and covered-vs-normal doping. The paper's existing filtering, parameter-shifting, seed, disorder, symmetry, and supercell checks are not claimed as novel missing ablations. Separate substantial bottlenecks are fabrication/topological validity and computationally efficient robust geometry search. Source data are synthetic theory outputs, not experimental measurements.
