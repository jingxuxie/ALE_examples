# Calibration and deployment diagnosis

The prototype equates average detector occupancy with a fault probability,
collapses rate groups and regimes, ignores dose response and transitions, treats
missing observations as zero, and scores one affine representative instead of
summing fault mass. These are different scientific failures: improving the
hard correction alone cannot fix calibration or logical-risk probabilities.

The replacement compares one-, two-, and three-regime calibrations using the
full syndrome-record likelihood, with multiple starts for the nonconvex fits.
Negative log likelihood per five-shot sequence was respectively 16.378269,
16.129859, and 16.066633. BIC was 393144.48, 387248.64, and 385819.23. The
three-regime model was selected. The two three-regime starts agreed to about
5e-9 in average objective value, after 73 and 71 iterations. Fitting all
candidates took about 14 seconds with one BLAS thread. Label permutations do
not affect deployment predictions.

Probe emissions sum all independent mechanism configurations that produce a
syndrome. A differentiated scaled forward pass supplies likelihood gradients.
Calibration records contain neither true fault vectors nor regime labels.
The supplied model artifact is learned from those records, not from deployment
answer tables. Model selection uses BIC; no held-out calibration likelihood is
claimed here. Public deployment predictions provide a separate transfer check.

Deployment builds regional affine spaces, retains boundary mechanisms, and
contracts character-valued probability factors. This computes per-regime
emissions and logical/query statistics. A log-space forward/backward pass then
conditions each shot on past and future records and computes adjacent-regime
switch probabilities. Missing rows are excluded, not set to zero.

Measured public baseline -> final errors:

| Case | Mean logical TV | Mean query absolute | Mean switch absolute | Evidence error / observed bit |
|---|---:|---:|---:|---:|
| dose_ring | 0.664762 -> 0.003735 | 0.136482 -> 0.000622 | 0.353192 -> 0.012955 | 0.542149 -> 0.000211 |
| drift_ladder | 0.423773 -> 0.007218 | 0.216588 -> 0.001584 | 0.276905 -> 0.009338 | 0.383799 -> 0.000154 |

Commands from the task root, with OPENBLAS_NUM_THREADS=1:

```
python participant/v_02/software/train.py --calibration participant/v_02/input/calibration.json --records participant/v_02/input/calibration_records.npz --output participant/v_02/software/model.json
python participant/v_02/software/solve.py --input participant/v_02/input/validation.json --output authoring/starter_v02_validation.json
python solution/v_02/train.py --calibration participant/v_02/input/calibration.json --records participant/v_02/input/calibration_records.npz --output solution/v_02/model.json
python solution/v_02/solve.py --input participant/v_02/input/validation.json --output solution/v_02/validation_predictions.json
python participant/v_02/software/validate.py --input participant/v_02/input/validation.json --expected participant/v_02/input/validation_expected.json --actual solution/v_02/validation_predictions.json
python authoring/check_v02.py
```

Independent checks exhaust both fault configurations and short regime paths
on microcases, and compare the training gradient against central differences.
Inference is exact conditional on the fitted model; parameter uncertainty is
not integrated. Runtime is exponential in local nullity and boundary width,
so no claim is made for unstructured high-width networks. Dose extrapolation
uses the specified physical log-odds law, not constant-rate clipping.
