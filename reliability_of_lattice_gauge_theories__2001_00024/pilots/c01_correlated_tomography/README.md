# c01_correlated_tomography — minimal pilot

Participant entry: `participant/TASK.md`. Submission API:
`solver.py: solve(case: dict) -> dict`. The participant release consists **only**
of `participant/`, never this entire pilot directory.

Run from this directory:

```bash
python private/evaluator.py --submission private/reference/strong --split screening --output private/reference/validation/reference_screening.json
python private/evaluator.py --submission private/reference/weak --split screening --output private/reference/validation/baseline_screening.json
python private/reference/validate.py
```

The evaluator depends on the main-owned `../../authoring/isolated_eval.py` and
its worker. It calls `run_solver` with a 120-second wall limit and 6 GiB per case;
optional `--participant DIR` selects a ratchet-specific participant mount.
there is no unsafe in-process or unisolated fallback. It requires the common
runner's bubblewrap environment and NumPy/SciPy. Numerical reports include
`mean_core`, `worst_family`, `family_scores`, `component_scores`, and `cases`.
Timeouts, invalid output, missing keys, non-finite values, and invalid witness
shapes score zero; isolation infrastructure failure is an error, not a bad
participant score. Reference data are precomputed JSON, not solved at evaluation.

`private/reference/build.py` reproducibly rebuilds cases from the locally cached
public workbooks using only the standard library, NumPy, and SciPy. It also
rebuilds frozen baseline scales, source hashes, and one unlabeled example.
Do not rebuild after a ratchet without reviewing and versioning the manifest.
`validate.py` checks primal/dual certificates, a different LP implementation,
an independent nonlinear fitting route, source inequalities, external published
points, and an exactly soluble synthetic identifiability counterexample.
The legacy revised-simplex audit requires a SciPy release that still provides
that method (validated environment: 1.8.0); the evaluator/strong solver use HiGHS.

See `private/reference/PROVENANCE.md` for science limitations and reference
independence, and `private/challenge_pool/README.md` for ratchet/confirmation
rules. Author-only results live in `private/reference/validation/`. Keep `attempt/`
completely empty before a fresh pilot: no solver, outputs, logs, or marker files.
