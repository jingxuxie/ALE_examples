# Generation 3: fully native-family-calibrated Markovian falsification

The final third task generation adds family-resolved average-channel calibration to the existing family-resolved inverse-pair calibration. The public schema, native ensemble, uniform baseline, 64 KiB cap, row counts/bounds, 2% layer infidelity, depth grid, fitting algorithm, CPU-only one-hour interface, residual limit 0.004, and final-signal floor 0.005 are preserved.

## Predeclared target and genuine failure

The fixed relative-bias target is **0.0235**. It was recorded in `private/target_selection.json` before the new integer search and before any generation-three fresh launch. This round 2.35% robustness claim is calibrated below the previously verified fully stratified continuous candidate's 2.366557% bias. It is not a numerical tightening against the previous champion and is not a theorem attributed to arXiv:2112.09853.

The actual archived generation-two champion has correct global mean and split pair overlaps 28800/1920, and exceeds the new numerical bias target. It nevertheless has native-family mean defects of **26 counts for single-qubit gates and 13 for CNOT gates**. The opposite defects cancel in the fixed mixture. The independent audit is `private/v2_independent_audit.json`.

Generation three requires single-family unweighted Pauli marginals 120 for each weight-one Pauli and zero otherwise; CNOT-family marginals 16 for weight-one, 8 for ring-edge weight-two, and zero otherwise. Both pair overlaps remain exact. These are native-family first-moment and short-depth calibration experiments using the original small counts, not a new giant-integer moment.

The full family calibration class matches the baseline average error channel and depth-two mirror signal for any mixture of the same two native families. The fitted long-depth bias need not be mixture invariant; scoring remains at the original CNOT probability 0.4. Every layer's true infidelity remains 0.02, so layer-infidelity covariance stays zero.

## Demonstrated achievability

`private/winning_witness.json` is an integer passing witness, not a continuous relaxation. Official evaluator values:

- Relative bias: **0.023660982733770264**.
- Maximum residual: **0.003746590589587595**.
- Depth-256 polarization: **0.0065112428073543106**.
- Core score: **100.68503290966069**.
- Both family means and pair overlaps pass exactly.

The unchanged uniform baseline is admissible and nonwinning: relative bias **0.020513162781135796**, residual **0.003219621296773778**, end signal **0.006377523142148609**, core score **87.29005438781189**.

The private search uses a previously saved fully stratified continuous candidate, integer LP projection under all 87 independent linear equalities, and bounded transportation moves to repair the two family-pair quadratic equalities. Source and actual-run evidence are in `private/search_integer.py` and `private/integer_search_run.json`. The fixed target was not changed after search.

## Verification and publication boundaries

The private tuple-based checker imports no public model and independently checks integer family constraints, all 129 polarizations, and a probability-space convolution through depth eight. Official/public entry points and the independent checker agree. The regression suite includes a controlled 28802/1919 pair-calibration failure whose family means and aggregate overlap still pass, the actual v2 failure, malformed/noninteger/duplicate-key/oversized artifacts, filesystem-reference rejection, sampler-calibration checks, and synthetic-exponential recovery.

The evaluator sets `sys.dont_write_bytecode = True` before importing the public model. Public/evaluator bytecode caches are cleared and checked absent. Public assets contain only the scientific contract, model/checker, targets, and ordinary uniform baseline: no old champion, privileged witness, search source, or private report is exposed.

Generation-one/two champion directories and full snapshots are verified byte-for-byte unchanged. No other concept is read or modified. No fresh agent is launched here. Achievability is demonstrated; actual generation-three difficulty awaits main's fresh attempt. This is the final planned generation regardless of its outcome.

## Recheck

From `concept_1`, run:

```bash
python evaluator/evaluate.py --submission adversary/generation_3/private/winning_witness.json
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python evaluator/validate.py
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python adversary/generation_3/private/test_generation3.py
```

Versioned official scores and validation records are under `evaluator/hidden/generation_3_*`. Private actual-run records, immutable-archive hashes, and the public freeze manifest remain under `adversary/generation_3/`.
