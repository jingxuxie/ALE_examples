# Author build and verification

Run from `tasks_v3/efficient_learning_of_quantum_noise__1907_13022/concept_01_sparse`. Requires the existing Python/NumPy/SciPy installation and the task-root common `private/evaluation_sandbox.py`; installs nothing. Use `python -B` to avoid cache files outside the intended layout.

```bash
python -B private/reference/build.py --public-example
python -B private/reference/build.py --pool core
python -B private/reference/build.py --pool challenge
python -B -m unittest discover -s private/reference -p 'test_*.py' -v
python -B private/reference/benchmark.py --pool core --ablations
python -B private/reference/benchmark.py --pool challenge --ablations
python -B private/evaluator.py --submission private/reference/solver.py --pool core --output private/reference/core_report.json
python -B private/evaluator.py --submission private/reference/weak_solver.py --pool core --output private/reference/weak_core_report.json
python -B private/evaluator.py --submission private/reference/solver.py --pool challenge --output private/reference/challenge_report.json
```

The builder independently checks physical forward observations and writes inputs, physical truth, and manifests for 9 core and 6 challenge cases. Calibration executes both standalone solvers under Landlock, stores their actual output NPZs, checks every strong score above 0.9, every weak score below 0.2, and every raw strong loss below 0.1. Reports include both recovery and estimation subcomponents. The evaluator requires a calibrated manifest.

Fresh ratchet inputs, without overwriting the current pool:

```bash
python -B private/reference/build.py --seed 20260829 --region heldout --pool core --count 3 --destination private/reference/heldout
python -B private/reference/benchmark.py --case-root private/reference/heldout --ablations
python -B private/evaluator.py --submission private/reference/solver.py --case-root private/reference/heldout --output private/reference/heldout_report.json
```

Any integer seed and nonstandard region token are supported. Keep the seed and generated pool private before future participant runs. Generation never retries or discards a case based on reference success. An uncalibrated fresh pool fails closed until its reference is checked. `--pool challenge` selects the stronger source-valid parameter region; any nonstandard `--region` additionally changes dimensions, density, range, and noise. Core/challenge IDs need not be unique across separate manifests.

Files: `solver.py` is the source-grounded reconstruction; `weak_solver.py` is the restricted-support baseline; `build.py` is the author build script; `physical.py` is the independent physical evaluator; `metrics.py` defines validation and uncapped grading; `benchmark.py` records executable evidence and dense resource estimates; `test_reference.py` tests transforms, physics, reconstruction, held-out seeds, schemas, and continuous grading. `PROVENANCE.md` and `AUDIT.md` document source correspondence and information boundaries. Full participant schema is `participant/input/FORMAT.md`. This is one concept only; no fresh agents or tournament attempts are launched.
