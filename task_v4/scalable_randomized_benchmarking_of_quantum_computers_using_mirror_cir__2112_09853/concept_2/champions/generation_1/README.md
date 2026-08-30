# Active mirror-benchmark policy

Run `python -B policy.py`. The process reads the evaluator's JSON-lines protocol
from standard input and writes only protocol responses to standard output.
NumPy and SciPy are the only third-party dependencies.

The policy spends 240,000 shots in 768 requests. Empty and singleton controls
calibrate the background and individual-edge errors. Randomized matchings use
under-observed disjoint pairs as forced edges to improve interaction coverage.
Each matching receives a depth-zero SPAM control and a nonzero-depth experiment.
An intermediate fit adapts the remaining mirror depths to the estimated decay.

Inference fits the disclosed matching-dependent SPAM model, including sinusoidal
drift when applicable, and identifies sparse nonnegative pair interactions with
weighted penalized regression. A joint binomial-likelihood refit estimates the
selected layer and SPAM parameters. Predictions use the exact conversion from
layer log decay to entanglement infidelity.

The submission needs no data files, network access, persistent state, or access
to the public development model.
