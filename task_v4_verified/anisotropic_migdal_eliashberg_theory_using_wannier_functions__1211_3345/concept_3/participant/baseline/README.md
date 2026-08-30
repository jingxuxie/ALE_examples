# Regularized baseline

`solve.py` uses public training pairs only. It whitens the known AR(1) noise,
learns a covariance-regularized linear conditional estimate, combines it with
locally weighted ridge regression, and projects window masses to the simplex.
Separate fits use the publicly known two-/three-sheet topology, with inactive
sheet slots set to zero. The local prior uses both Nambu channels and both probes; this is stronger than
an unregularized rational fit. Hyperparameters are fixed in the source, not
tuned against hidden labels. For v2, strengths {.25,1,4,12,24,64} were compared
on public validation; strength 4 won using the maximum normalized pass-limit
ratio as the selection objective. The selected local penalty is 6, not the
v1 value 36. No fitting data are embedded in the program.

Run from `participant/` as documented in `input/FORMAT.md`. For standalone
use elsewhere set `ALE_PUBLIC_INPUT` to the absolute public resource directory.
No nonstandard packages or subprocesses are required.
