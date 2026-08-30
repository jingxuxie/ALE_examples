# Five-parton matrix-element surrogate

Build a compact predictor for the leading-colour five-parton kernel used in
EERAD3's electron–positron annihilation calculation. The supplied training and
validation events have exact source-native labels, including unresolved regions.

Assets: `input/` contains labelled arrays and the data/interface contract;
`baseline/` contains a runnable regression baseline. The native generator and
held-out labels are not supplied.

Submit `predict.py` and any model files in the output directory. The executable
interface is `python3 predict.py INPUT.npz OUTPUT.npz`. Predict the natural
logarithm of the positive kernel for every input event.

The objective is accurate held-out prediction across all five physical families,
not only average accuracy. Pass requires overall log-RMSE <= 0.05, every-family
log-RMSE <= 0.08, and at least 95% of predictions within 15% relative error.
Inference has 90 seconds, one CPU thread, 3 GiB address space, no network, and
128 MiB of submitted artifacts. Training may use the one-hour authoring budget.
