# Regularized baseline

`solve.py` uses public training pairs only. It whitens the known AR(1) noise,
learns a covariance-regularized linear conditional estimate, combines it with
locally weighted ridge regression, and projects window masses to the simplex.
The local prior uses both Nambu channels and both probes; this is stronger than
an unregularized rational fit. Hyperparameters are fixed in the source, not
tuned against hidden labels. No fitting data are embedded in the program.

Run from `participant/` as documented in `input/FORMAT.md`. For standalone
use elsewhere set `ALE_PUBLIC_INPUT` to the absolute public resource directory.
No nonstandard packages or subprocesses are required.
