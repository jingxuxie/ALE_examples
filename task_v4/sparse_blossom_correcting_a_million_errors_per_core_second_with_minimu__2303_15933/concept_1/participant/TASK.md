# Beyond two-pass correlated matching

Improve logical decoding under correlated local faults. The supplied baseline is
**PyMatching 2.4.0 two-pass correlated matching**, with correlations enabled both
when constructing the graph and when decoding. Do not reimplement sparse blossom
or merely switch on its existing correlations: they are already enabled.

The scientific objective is to infer the most probable **joint logical class**,
not just the most probable physical fault configuration. Develop an
improvement that handles competing correlated explanations and/or logical-class
degeneracy, while remaining computationally practical. No particular algorithm
is prescribed; a single textbook algorithm is not the deliverable by itself.

Use the six fully specified toric-code models and representative labeled
calibration samples in `input/`. They cover biased local Pauli faults, spatial
two-qubit crosstalk, and repeated noisy-check memory with temporal bursts.
All mechanisms, probabilities, detector incidence, and logical incidence are
provided. Hidden shots are independent draws from these same distributions.

Copy `workspace/submission.py` to `$OUTPUT_DIR/submission.py` and implement
`Decoder` there; see `input/API.md`. Participant assets are read-only; only your
output directory is writable. You have **one hour** of agent development time.
Use only participant-visible assets; no network, hidden-file access, upstream
source checkout, pretrained decoder download, or lookup of hidden shot labels.
You may generate additional correctly sampled training data from the public models.

Success requires **at least 25% fewer joint-logical failures** than the frozen
correlated baseline, at least **20% fewer on the independent holdout**, and no
family with more than **5% additional failures**. The paired 95% confidence
interval for the pooled improvement must exclude zero. Runtime is at most
**180 CPU-seconds total**, including imports and initialization, on one CPU core,
with a **6 GiB address-space limit** and a separate 900-second wall watchdog.
CPU usage is measured by the trusted parent, not candidate-reported timing.
The evaluator measures both accuracy and
runtime; matching speed alone does not earn success.

Run the public check from this directory:

```
cp workspace/submission.py "$OUTPUT_DIR/submission.py"
/usr/bin/python3 input/run_public.py --submission "$OUTPUT_DIR/submission.py"
```

Read `input/SCIENCE.md` for the exact noise interpretation and primary sources.
The baseline is a working starter, not a passing solution.
