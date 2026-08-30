# Cold response of a partially observed material

Infer a disordered Ising material from incomplete equilibrium observations and
predict its joint response under substantial cooling and visible-site fields.
The mission is hidden prediction, not reproducing a paper figure.

`input/model.json` gives the graph, missing-spin mask, coupling signs and prior
bounds. `input/train.npz` contains independent observations of 64 visible spins
at two temperatures. `input/queries.json` specifies 48 cold experiments.
`transfer.py` supplies exact strip inference for parameters you choose;
`SCHEMA.md` defines all conventions. The baseline contains frozen predictions
from a public-data-fitted predecessor, not hidden material parameters.

Write `predictions.npz` in your output directory: a C-contiguous float64
`probabilities` array of shape `(48,64)` and Unicode `<U24` `query_ids` in the
published order. Each row is the joint distribution of six spins. The evaluator
reads this artifact only and executes no submitted code.

Pass all three fixed targets: mean forward KL **at most 0.020 nats**,
worst-family mean KL **at most 0.035 nats**, and maximum query total variation
**at most 0.120**. Probabilities must be finite, strictly positive and normalized.
The artifact limit is **65,536 bytes**.

Budget: **one hour**, four CPU cores, 8 GiB address space per process, no GPU or
network. Use only the supplied observations for this material; synthetic
calculations under your own parameter estimates are allowed. Develop in your
writable output directory. Emit the baseline with
`python baseline/run.py --output OUTPUT_DIRECTORY`.
