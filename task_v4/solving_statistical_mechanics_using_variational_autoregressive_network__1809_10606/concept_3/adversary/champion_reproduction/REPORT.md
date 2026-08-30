# Champion source reproduction

Source-faithful rerun differs numerically from the archived champion. Do not label this rerun or portfolio stress results as champion evaluations.

## Completed replay and comparison

The unchanged recorded pipeline completed in 438.63 seconds: public-data MLE,
native C++ verification, transformed-posterior geometry, four fixed-seed HMC
chains with 800 warmup steps and 2,400 retained draws each, and the recorded
final summarizer using all 9,600 retained draws. All eight restored source
hashes were checked after execution.

- Exact probability-array/ID reproduction: **not established; arrays differ**.
- Maximum absolute probability difference: **0.0002028670901199625**.
- Maximum query total variation between archive and replay: **0.0002738557673308919**.
- Mean KL from archived predictions to replay predictions: **9.837471901840567e-08**.

These are differences between two prediction artifacts, not scores against
hidden ground truth. No hidden evaluator or material/query labels were used.
The archived artifact was opened only after the reproduced output was complete
and its hash recorded. No retry or parameter selection was made using this
comparison.

The original transcript reports MLE termination at 411 iterations/440 function
calls, loss 30.86898187273276. This replay terminates at 416 iterations/435 calls,
loss 30.868981870900072. Optimizer/floating-point differences propagating into
finite seeded posterior trajectories are a plausible explanation, not a proven
diagnosis. The deleted original fit, posterior geometry, and chains are not
available to establish exact state identity.

## Consequence for broad-challenge claims

**No champion stress evaluation was performed.** The earlier response-stress
portfolio remains a separate evaluation of public-data portfolio models, not
an evaluation of the archived generation-1 champion. A close source-faithful
rerun is useful provenance but is not silently substituted for that champion.

The recovered generic `infer.prediction` helper supports arbitrary visible-site
fields through the public transfer implementation. The accelerated
`NativeLikelihood.predict` used by the final summarizer instead assumes field
sites are in the readout column. This distinction would need to be explicit in
any future stress replay; neither source was scientifically modified here.

Eight sources are restored with command/line/hash provenance in SOURCE_PROVENANCE.json. The recorded summarizer Update File is applied after its verified initial full-file snapshot. Source code is unchanged otherwise; output paths relocate automatically through __file__.

Only public material observations and priors were used for fitting. The archived predictions are opened only after replay completion. No original attempts, champions, participant assets, evaluator, or status were modified. No hidden material parameters or query labels were used.

The original native prediction method assumes field sites are in the readout column; nonlocal stress fields are outside its implemented interface. No correction of that scientific behavior is made.

See REPRODUCTION_RESULT.json and stage logs for numerical comparison and runtime.
