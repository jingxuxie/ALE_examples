# Predict circuits beyond a characterization campaign

Your laboratory must predict single-qubit measurement probabilities on long,
structured circuits using finite-shot characterization records. The devices have
classical environmental memory, pulse-history dependence, and smooth drift.
The physical model class is disclosed; its device-specific parameters are not.

## Assets
- `input/train.npz`: characterization circuits and binomial outcome counts.
- `input/development.npz`: representative longer circuits and independent counts.
- `input/queries.npz`: all test circuits, without outcomes.
- `input/PHYSICS.md`, `input/FORMAT.md`, `input/protocol.json`: physical assumptions,
  data format, and frozen scoring contract.
- `baseline/predict.py`: a runnable, stationary process-tomography baseline.
- `workspace/score_development.py`: a local count-based diagnostic.

## Deliverable
Write `predictions.json` in your writable output directory. Its only keys are
`ids` and `p1`: parallel arrays containing every test query ID exactly once and
your probability of outcome **one**. Order is arbitrary. Predictions must be
finite numbers in `[0,1]`. No executable submission is evaluated.

Example invocation from this directory:
`python baseline/predict.py --input input --output /YOUR_OUTPUT/predictions.json`

## Objective and resources
Recover probabilities, not the particular random count realization. Evaluation
uses private, exactly marginalized simulator probabilities for these same four
devices. Pass requires macro RMSE at most **0.020**, RMSE at most **0.025 in every
announced circuit family**, and at most **0.040 in every device/family cell**.
Scores, their direction, and secondary diagnostics are defined in the protocol.
All families and devices occur in the labeled data; test depth is the principal
extrapolation. There is no unannounced noise mechanism or hidden device.

You have one hour, an affinity of 8 CPUs and an **8 GiB address-space limit per
process** (RLIMIT_AS), no external experiment queries, and a 2 MiB prediction-file
limit. NumPy and SciPy are available. You may
use the training and development counts together. Only participant assets and
your output directory are available; write working files into that output
directory. Prediction-generation time is governed by the runner, not inferred
from a submitted timing claim.
