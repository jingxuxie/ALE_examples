# Cold-response submission

`predictions.npz` is the submission artifact. The other files document the
inference, simulation checks, and estimator selection; they are not required by
the evaluator.

## Statistical method

All 172 coupling magnitudes and 96 background fields are inferred separately,
using the supplied signs and independent uniform bounds. The objective is the
exact likelihood of all observations at both training temperatures. Conditional
on the visible spins, the hidden spins split into components of at most six
sites. Their partition functions are enumerated exactly, including
hidden-hidden interactions. The unconditional partition function uses exact
256-state strip transfer.

The bounded posterior is sampled with Metropolis-corrected, dense-preconditioned
Hamiltonian dynamics and exact boundary reflections. The preconditioner does
not change the uniform prior. Additional reversible coupling-swap proposals
improve mixing of weakly identified degree-two hidden sites.

Four chains provide 12,000 post-warmup draws for constructing candidate
predictions. Two further 6,000-draw streams provide selection and audit draws. Every cold
joint distribution is calculated exactly for its parameter draw. Readout fields
are applied before averaging or selecting predictions, with the physical
`beta * field` convention and the published least-significant-bit ordering.

The final decision targets the probability of jointly meeting all three stated
limits, rather than only minimizing posterior expected mean KL. Candidate
centers include the posterior mean, local posterior averages, smooth
threshold-aware optimizations, and exact coordinate refinements. Selection
uses a one-standard-error rule with expected KL as the tie-breaker. The last
simulation stream is reserved for an independent audit.

## Verification

- Exact component likelihood agrees with directly clamped strip inference.
- Analytic likelihood gradients agree with central finite differences.
- 144 direct-field simulator comparisons agree within `3.2e-15` in probability.
- Full reflected leapfrog round trips recover positions within `4e-14`.
- Three random parameter initializations recover the fitted negative log
  likelihood within `1e-5` nats.
- Relevant predictive split-Rhat values are below `1.001` in the construction
  chains; the minimum reported predictive effective sample size exceeds 2,800.
- Archive checks cover member names, NPY versions, dtypes, shapes, query order,
  contiguity, positivity, finiteness, normalization, and the byte limit.

Detailed checks are in `numerical_checks.json`, `prepare.log`, and
`training_evaluation.log`. `submission_manifest.json` records the artifact hash
and numerical properties. `selection_summary.json` records the final selection
and audit. Its coverage numbers concern simulated parameter draws from the
fitted posterior, **not hidden ground truth**. The actual hidden KL/TV targets
cannot be certified from the supplied assets.

## Re-create the final archive

From this output directory, using the saved simulation and candidate archives:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python select_submission.py \
  validation_draws.npz response_candidates.npz coordinate_candidates.npz \
  main_candidates.npz main_optimized.npz lbfgs_pilot.npz \
  --training-mean training_mean.npz --audit-last --output predictions.npz
```

`infer.py`, `posterior.py`, and `evaluate.py` implement model fitting, posterior
sampling, and exact prediction. `verify.py` runs the numerical simulator and
Hamiltonian checks. Only the supplied observations, priors, graph, queries,
baseline snapshot, and parameterized simulator are used.
