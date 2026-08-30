# Production five-parton kernel prediction

Build a compact, high-throughput predictor for the leading-colour five-parton
EERAD3 kernel. The predictor must be accurate and cheap enough for a large
Monte Carlo campaign.

Assets: `input/` contains source-native labelled events and the data contract;
`baseline/` contains a runnable regression baseline. The native source,
generator, prior submissions, and held-out labels are not supplied.

Submit `predict.py` and model assets in the output directory. Interface:
`python3 predict.py INPUT.npz OUTPUT.npz`. Predict the natural log of the kernel.

The held-out batch has 200,000 independent events across all five physical
families. Pass requires overall log-RMSE <= 0.05, every-family log-RMSE <= 0.08,
and at least 95% of predictions within 15% relative error. Total prediction
process CPU time must be <= 2.4 seconds (12 CPU seconds per million events),
including startup and input/output. Evaluation permits 90 seconds wall time,
one CPU, 3 GiB address space, no network, and 128 MiB of submission artifacts.
Training and implementation may use the one-hour authoring budget.
