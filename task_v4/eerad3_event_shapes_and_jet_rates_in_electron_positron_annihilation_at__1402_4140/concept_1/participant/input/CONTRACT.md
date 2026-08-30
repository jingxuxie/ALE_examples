# Data and interface

Each NPZ contains `s` (N,10), `p` (N,5,4), and `family` (N,). Labelled NPZs
add `log_weight` (N,). `frame` (N,) is an optional integer field; missing means
frame 0. Arrays are float64 except integer `family` and `frame`.

Particles 1 and 2 are a quark and antiquark; 3,4,5 are ordered gluons.
`p` stores (px,py,pz,E), with invariant total mass Q = 1. All latent particles
are future-directed and massless. Momenta need not be in their CM frame.
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
Latent events are boosted to their CM frame and normalized. Events with any
invariant <= 1e-10 or nonpositive/nonfinite native weight are excluded.
Test events are independent draws from these same phase-family definitions,
then transformed into one of the four frame families described below.

Write an NPZ with exactly one required field, `log_weight`, shape (N,), finite
float64 values in the input order. At inference only the submission directory
and the unlabelled query file are visible, together with system libraries.
Python 3, NumPy, SciPy, scikit-learn, C/C++, and gfortran are available.
The input path may be arbitrary; locate model files relative to `__file__`.
Baseline training: `python3 baseline/train.py input/train.npz OUTPUT_DIRECTORY`.
Then `python3 OUTPUT_DIRECTORY/predict.py input/validation.npz predictions.npz`.

Core score = exp(-overall log-RMSE); worst-family score =
exp(-maximum phase/frame-group log-RMSE). Passing uses all three thresholds in TASK.md,
not a single aggregate score. Relative error is abs(exp(prediction-label)-1).
Runtime is scored separately and cannot compensate for inaccurate predictions.

## Frame families and precision

Frame 0 is CM; frame 1 is CM rotated so the quark is on either z axis.
Frame 2 uses isotropic boosts with gamma log-uniform in [10, 1000]; frame 3
uses isotropic boosts with gamma log-uniform in [1e5, 1e8]. Each of the 20
phase/frame intersections has 10,000 hidden events. The target is unchanged
under these transformations. `frame_validation.npz` provides labelled
examples of all frame families; the other labelled files contain CM events.

The normalized invariants `s` are authoritative. Four-momenta are binary64
roundings of transformed physical events. At large boosts their small
invariants, null shells, and total invariant mass cannot be recovered to
the target accuracy from those rounded components. This representational
loss does not change `s` or the target; input consistency is interpreted at
the unrounded physical-event level. The labelled examples illustrate this
contract. The kernel remains a Lorentz scalar, not a lab-frame angular rate.

The required relative tolerance is 1e-8 with coverage >= 0.99, in addition to
overall log-RMSE <= 1e-9 and each phase/frame-group log-RMSE <= 5e-9. These
gates support cancellation-sensitive diagnostics; a small aggregate error
cannot hide failure in an unresolved or boosted family.

## Production budget

The held-out batch contains 200,000 independently generated latent events,
40,000 from each phase family. The supplied baseline remains the regression
predictor. A private incumbent is fast and accurate in the CM frame but fails
on boosted events. Its implementation and the native generator are not assets.

The complete prediction subprocess, including Python startup and input/output,
has a total user-plus-system CPU budget of 2.4 seconds. CPU use of descendants
is included; the process is pinned to one available CPU. The independent
90-second wall timeout still applies. No training-data read is required during
inference: submit any needed model data with the predictor.

Runtime score = min(1, 2.4 / measured CPU seconds). Core and worst-family scores
retain their accuracy definitions; all quality thresholds AND the CPU/wall
budgets are mandatory. Training time is separate from inference time.
