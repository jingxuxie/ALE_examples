# Hidden-spin material response

## Mission
Infer an incompletely observed, interacting Ising material and predict its joint
response after changing temperature or applying small visible-site fields.
This is mode **D: hidden prediction**, not a request to reproduce a paper figure.

## Assets
`input/model.json` discloses the graph, missing-spin mask, coupling signs and
bounds. `input/train.npz` contains independent equilibrium observations of the
64 visible spins at two temperatures. `input/queries.json` specifies 24 held-out
experiments: eight interpolation, eight cooling, and eight field-response cases.
`transfer.py` supplies exact open-strip inference for parameters you choose;
it contains no true material parameters. See `SCHEMA.md` for all conventions.

## Output
Write only the required artifact `$OUTPUT_DIR/predictions.npz`: `probabilities`
is a float64 array of shape `(24,64)` and `query_ids` is a Unicode array of dtype
`<U24` in the published order. Each row is the joint distribution of six spins,
not six separate marginals. No submitted code is executed by the evaluator.

## Fixed Quality And Resources
Pass all three: mean forward KL **<= 0.020 nats**, worst-family mean forward KL
**<= 0.035 nats**, and maximum query total variation **<= 0.120**.
Probabilities must be finite, strictly positive, and normalized; malformed
artifacts fail. The artifact limit is **65,536 bytes**.
Budget: **one hour wall time, four-core CPU affinity, 8 GiB address space per
process, no GPU or network**; the runner enforces these execution limits.
Use the supplied data only for this
material; synthetic calculations under your own parameter estimates are allowed.

Weak starter: `python baseline.py --output "$OUTPUT_DIR"`. It uses the nearest
observed temperature, empirical readout counts, and local field reweighting.
The hidden evaluator, labels, model parameters, and generation seed are not
participant assets. Develop in a separate writable work directory if assets are
mounted read-only; put the final artifact in `OUTPUT_DIR`.
