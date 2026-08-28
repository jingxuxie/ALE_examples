# Author handoff

Run commands from the `concept_04_graphical` root. Python, NumPy and SciPy are
required. Evaluation also requires the existing parent
`../private/evaluation_sandbox.py` and Linux Landlock. No Julia, JAX, GPU or
network access is needed. Only `participant/` is participant-visible; keep
`private/` and the main author's `attempt/` out of the participant snapshot.

## Reproduce the current pilot

```sh
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python private/reference/build.py --seed 20260827 --region 0
python private/reference/capture_provenance.py
python private/reference/audit.py --seed 918273 --output private/reference/audit.json
python private/evaluator.py --submission private/reference/solver.py --pool core --output private/reference/strong_core.json
python private/evaluator.py --submission private/reference/solver.py --pool challenge --output private/reference/strong_challenge.json
python private/evaluator.py --submission private/reference/weak_solver.py --pool core --output private/reference/weak_core.json
python private/evaluator.py --submission private/reference/weak_solver.py --pool challenge --output private/reference/weak_challenge.json
```

The default evaluator pool is core. `mean_core` is null in a challenge-only
report, which instead sets `mean_challenge`; `mean_selected`, `worst_family`,
`families`, `cases` and `runtime` always describe the selected pool. Runtime is
the sum of subprocess wall times, including startup, not the author's oracle
precomputation. Case reports expose no reference arrays or child stdout/stderr.
Malformed outputs receive zero; sandbox failure never falls back to unrestricted
execution. The output parser checks bounded archive sizes and numeric headers
before allocating the prediction array.

Initial sandboxed results: strong core `0.9999999999999947`, weak core
`0.20152477986412584`; strong challenge `0.9999999999999879`, weak challenge
`0.20133467780749945`. See the JSON reports for family scores and measured times.
The reference's maximum error is also checked against independently enumerated
small systems and against a different frontier-contraction algorithm at scale.

## Fresh ratchet

```sh
python private/reference/build.py --seed 7359281 --region 1
python private/reference/audit.py --seed 402916 --output private/reference/audit.json
python private/evaluator.py --submission PATH_TO_solver.py --pool core --output private/reference/fresh_report.json
python private/evaluator.py --submission PATH_TO_solver.py --pool challenge --output private/reference/fresh_challenge.json
```

This intentionally replaces both pools, the unlabeled example, private models,
truths and manifest. Region 1 uses more-negative fields and stronger positive
couplings; region 2 uses less-negative fields. Choose seeds privately
after a submission is fixed. Rerun reference/baseline reports after regeneration;
old JSON reports no longer describe the regenerated corpus. Restore the shipped
pilot with the first command block. `audit.py` additionally generates six fresh
region-1/region-2 checks in memory, leaving the selected corpus untouched.
`python private/reference/check_regeneration.py` also tests the complete build
pipeline with the fresh seed above in a temporary private root, checks all 15
reconstructed answers, and leaves the shipped pools unchanged.

## Files and invariants

- `solver.py`: standalone strong submission; grouped fixed CMI, local inversion,
  min-fill log-domain count/parity elimination. It imports no author helpers.
- `weak_solver.py`: standalone independent-bit baseline using visible marginals.
- `author_tools.py`: hidden model construction, local table synthesis, independent
  known-order frontier oracle, tiny exhaustive oracle, private model serialization.
- `build.py`: deterministic 9-core/6-challenge generation and hidden target capture.
- `audit.py`: CMI regression, six exhaustive cases, all-pool ablations, parser
  checks, score continuity, anti-identity assertions and six fresh regional cases.
- `capture_provenance.py`, `source_manifest.json`, `juqst_08101ff.patch`: actual
  source history and hashes, with an explicit unavailable-code declaration.
- `manifest.json`, `core/`, `challenge_truth/`, `models/`: private evaluation data;
  challenge inputs alone live in `../challenge_pool/`.
- `PROVENANCE.md`, `ANTI_COMPRESSION.md`: scientific assumptions and controlled
  evidence. `FILES_CHANGED.md` inventories this worker's exact owned artifacts.

Do not pass the original reference directory to Landlock as a solver-readable
directory. The evaluator first copies the single source file to an isolated code
directory, then calls the shared restrictor with that staged parent and workdir.
It sets HOME, TMPDIR and NUMBA_CACHE_DIR within the workdir and limits BLAS/OMP
threads to one. The public caps are 120 seconds and 3 GiB per case; extra file,
descriptor and process limits prevent unbounded output or fork-heavy execution.

No main-author attempts are created here. The empty `attempt/` directory is
reserved for the main author's isolated ultima-alpha runs.
