# Data and interface

Each NPZ contains `s` (N,10), `p` (N,5,4), and `family` (N,). Labelled NPZs
add `log_weight` (N,). Arrays are float64 except integer `family`.

Particles 1 and 2 are a quark and antiquark; 3,4,5 are ordered gluons.
`p` stores (px,py,pz,E), with total CM energy one. All particles are massless.
`s` is 2 p_i dot p_j / Q^2, ordered 12,13,14,15,23,24,25,34,35,45.
They are positive, sum to one, and respect physical four-dimensional phase space.

The positive target kernel is the ordered leading-colour pair `tt0` in EERAD3's
`sig5ZQ`, before coupling, colour, and phase-space factors. Its log is the
training label. It averages the two reversal-related ordered qqbar+ggg tree
matrix elements. It is not a complete NNLO prediction and has no subtraction
terms, virtual terms, or histogram weights. Labels use quadruple-precision
native evaluation before rounding to float64. The source formula is not an asset.

Families 0 through 4 are generic, soft, single-collinear, double-collinear,
and triple-collinear. All are present in both training and test. Underlying
positive energies are gamma(2,1); directions are isotropic before boosts.
Soft events reduce the fourth energy by a log-uniform factor 10^-4.5 to 10^-1.
Collinear directions are perturbed by factors 10^-2.5 to 10^-0.35. Double
collinear uses pairs (3,4) and (1,5); triple collinear uses (3,4,5).
All events are boosted to their CM frame and normalized. Events with any
invariant <= 1e-10 or nonpositive/nonfinite native weight are excluded.
Test events are independent draws from these same family definitions.

Write an NPZ with exactly one required field, `log_weight`, shape (N,), finite
float64 values in the input order. At inference only the submission directory
and the unlabelled query file are visible, together with system libraries.
Python 3, NumPy, SciPy, scikit-learn, C/C++, and gfortran are available.
The input path may be arbitrary; locate model files relative to `__file__`.
Baseline training: `python3 baseline/train.py input/train.npz OUTPUT_DIRECTORY`.
Then `python3 OUTPUT_DIRECTORY/predict.py input/validation.npz predictions.npz`.

Core score = exp(-overall log-RMSE); worst-family score =
exp(-maximum family log-RMSE). Passing uses all three thresholds in TASK.md,
not a single aggregate score. Relative error is abs(exp(prediction-label)-1).
Runtime is scored separately and cannot compensate for inaccurate predictions.

## Generation 2 production budget

The exact interface and target quantity are unchanged. The held-out batch now
contains 200,000 independently generated events, 40,000 from each family.
The supplied baseline remains the regression predictor. A private incumbent
predicts accurately but exceeds the production CPU budget. Its implementation
and the native generator are not participant assets.

The complete prediction subprocess, including Python startup and input/output,
has a total user-plus-system CPU budget of 2.4 seconds. CPU use of descendants
is included; the process is pinned to one available CPU. The independent
90-second wall timeout still applies. No training-data read is required during
inference: submit any needed model data with the predictor.

Runtime score = min(1, 2.4 / measured CPU seconds). Core and worst-family scores
retain their accuracy definitions; all quality thresholds AND the CPU/wall
budgets are mandatory. Training time is separate from inference time.
