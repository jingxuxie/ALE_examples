# Frame-independent five-parton kernel prediction

Deliver a compact, high-throughput predictor for EERAD3's ordered leading-colour
five-parton scalar kernel, with the precision needed for cancellation-sensitive
diagnostics across inertial frames.

Assets: `input/` contains source-native labelled events and the data contract;
`baseline/` contains a runnable regression predictor. Native source, the
generator, previous submissions, and held-out labels are not supplied.

Submit `predict.py` and assets in the output directory. Interface:
`python3 predict.py INPUT.npz OUTPUT.npz`. Predict the natural log of the kernel.

The held-out batch has 200,000 events, balanced over five physical families and
four frame families. Pass requires overall log-RMSE <= 1e-9, every phase/frame
group log-RMSE <= 5e-9, and at least 99% of predictions within relative error
1e-8. Authoritative invariants define the scalar target even when the supplied
four-momenta have lost information through floating-point rounding.

Total prediction process CPU time must be <= 2.4 seconds, including startup and
input/output. Evaluation permits 90 seconds wall time, one CPU, 3 GiB address
space, no network, and 128 MiB of artifacts. Authoring has a one-hour budget.
