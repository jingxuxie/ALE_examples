# Supported-interface cold audit: substantive failures found

Completed August 28, 2026. This evaluates a **deterministic-subset posterior REPLAY**, not the bitwise original champion. The previously completed full source-faithful replay differed from the archived original predictions by maximum query TV 0.0002738557673308919 on the original queries. That comparison does not bound differences on these colder queries.

## Frozen design and provenance

- The interrupted 96-query proposal was never executed. `AMENDMENT48.json` supersedes it before any cold query predictions or labels existed.
- The actual design has 48 queries: 12 at each beta 4, 6, 8, and 10. Each beta has six zero-field and six readout-local-field cases. Four local visible fields have two +1 and two -1 amplitudes, at publicly seeded sites. Identical patterns recur across beta; none were selected using scores.
- Each beta covers all eight columns having six visible spins. The remaining four lattice columns have only four visible spins and cannot support the unchanged six-visible-spin interface.
- `queries.json` and `QUERIES_FROZEN.json` were frozen at 21:26:52.700455 UTC; predictions were frozen at 21:27:04.946177 UTC, **before** opening the private model for labels. Exact truth is saved in `true_probabilities.npz`, aligned by `query_ids`.
- The posterior uses unchanged recovered `NativeLikelihood.predict` and theta indices 0,8,...,2392 from each of four already-frozen chains: 1,200 predictive distributions averaged, not parameter averaging. Weakfit is the already-frozen public-data latent weak-penalty fit. No fitting, model initialization, query tuning, or recovered-science edits occurred.
- Recovered source, public inputs and weakfit hashes were checked unchanged. The command is saved in `COMMANDS.md`; executable invocation, environment and affinity are in `commands.json`. Audit execution took **13.03 seconds** on affinity CPUs 380–383, with numerical libraries restricted to one thread.

## Fixed reference gates and results

The unchanged gates are mean forward KL <= 0.020 nats, worst-family mean KL <= 0.035, and maximum per-query TV <= 0.120. An individual KL above 0.020 is only diagnostic, not an original individual-query gate.

| Frozen predictor / audit | Mean KL | Worst-family mean KL | Max TV | TV failures | All gates |
| --- | ---: | ---: | ---: | ---: | --- |
| Posterior REPLAY subset, previous supported 60 | 0.00376711 | 0.00425864 | 0.08268756 | 0 | Pass |
| Weakfit, previous supported 60 | 0.00226698 | 0.00233019 | 0.06404439 | 0 | Pass |
| Posterior REPLAY subset, cold 48 | 0.02529506 | 0.04273012 | 0.40005286 | 4 | Fail all three |
| Weakfit, cold 48 | 0.01322685 | 0.01865455 | 0.20509031 | 4 | Fail max TV |

| Beta | Replay mean KL | Replay max TV | Weakfit mean KL | Weakfit max TV |
| --- | ---: | ---: | ---: | ---: |
| 4 | 0.01049286 | 0.13856429 | 0.00605354 | 0.08424423 |
| 6 | 0.01921876 | 0.23975353 | 0.01211815 | 0.12283595 |
| 8 | 0.03030924 | 0.32830248 | 0.01637606 | 0.16446124 |
| 10 | 0.04115937 | 0.40005286 | 0.01835967 | 0.20509031 |

The replay's four TV failures are the same column-4 local-field pattern at the four preregistered betas. Weakfit fails that pattern at beta 6, 8 and 10, plus a column-0 local-field case at beta 10 (the latter is borderline, TV 0.120557). The column-4 beta-8/10 failures are not borderline threshold effects. All zero-field cases remain below the TV gate. Full numerical results and every case are in `RESULTS.json` and `per_query_scores.json`.

## Concrete physical failure and uncertainty

`cold_044` has beta 10, readout [32,35,36,37,38,39], and fields -1,+1,+1,-1 on sites [32,36,38,39]. All fields are visible and inside the readout column, exactly within the recovered predictor's supported interface. Outcome code 30 has true probability 0.625189, replay probability 0.227469, and weakfit probability 0.429767. Outcome 62 instead receives 0.556025 from replay versus truth 0.299240. This is a substantial redistribution between competing low-temperature states, not an unsupported-field artifact or arbitrary precision tightening.

The 1,200-draw approximation is explicit: maximum cold interleaved-half mean TV difference is 0.042008, and maximum individual-chain mean TV from the pooled mean is 0.018717. At the worst case the latter is 0.008820. These are diagnostics, **not rigorous error bounds**, and the full 9,600-draw cold replay has not been evaluated. Do not report these numbers as full-posterior or original-champion results.

At the worst case, the 95th percentile posterior-draw TV from the replay mean is 0.443748; the marginal posterior interval for outcome 30 is [0.025712,0.645537], containing truth. Broad conditional predictive uncertainty and error growth under cooling are consistent with finite-observation extrapolation sensitivity. They do **not** establish an information-theoretic limit, calibrated posterior coverage, global chain mixing, or that a better public-data estimator cannot pass. The weakfit control has no posterior-subsampling approximation and independently demonstrates a substantial supported failure.

## Exactness and scope

- Native local-field prediction versus generic exact transfer on predetermined frozen draws/cases: maximum absolute probability discrepancy 2.33e-15.
- All 48 true labels independently checked against dense 256-state transfer: maximum discrepancy 8.88e-16.
- All 48 true labels checked under global spin flip with reversed fields: maximum discrepancy 2.22e-16. Every vector is finite, strictly positive and normalized; all audit NPZ parsing disables pickle.
- The earlier stress120 audit uses only its 60 zero/readout-local cases. Its 60 neighbor/remote-field cases are excluded because the optimized native interface does not support them; **they are not counted as scientific failures**.
- Initial task status remains SOLVED and untouched. These sidecar failures demonstrate sensitivity of two frozen public-data predictors, not solvability or impossibility of a revised task. No new generation, fresh agent, refit, target change, or scientific-asset/status modification was performed.
