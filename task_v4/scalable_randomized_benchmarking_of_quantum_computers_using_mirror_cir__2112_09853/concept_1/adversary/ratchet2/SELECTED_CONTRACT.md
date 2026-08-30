# FINAL selected generation 2: native-family-resolved inverse-pair calibration

This supersedes the stronger proposal in `CONTRACT.md` and `recommendation.json`. Status: **hard_open**. No integer passing witness is verified. Main selected this contract after inspecting the private pair-only search. No old champion, artifact, search source, or private evidence belongs in participant assets.

## Exact next contract

Keep the generation-one integer schema, denominator 3000, row bounds and sums, fixed native ensemble, nominal CNOT sampling probability 0.4, layer infidelity 0.02, original **global** average-channel equality, and all fitting conventions.

Use bias target **0.0239**, maximum fit residual **0.004**, and depth-256 polarization at least **0.005**. The bias target is an explicitly revised quantitative claim for the stronger calibration class, not a theorem attributed to the seed paper.

Replace the single weighted inverse-pair check by the following two exact **unweighted** checks, or retain the old check redundantly:

    O_S = sum over single-qubit L and Q != I of c_(L^-1)(Q) * c_L(L Q L^-1) = 28800
    O_C = sum over CNOT L and Q != I of c_(L^-1)(Q) * c_L(L Q L^-1) = 1920

Their implication for the old check is O_S + 2*O_C = 32640. Do not multiply CNOT terms by two when comparing with 1920. **Do not add separate single-family/CNOT-family average-channel constraints.** Do not add off-nominal sampler or error-rate scoring cases.

In the public model's existing array conventions, the entire new calibration calculation is:

```python
products = counts[INVERSE] * np.take_along_axis(counts, PERMUTATIONS, axis=1)
single_overlap = int(products[:24].sum())
cx_overlap = int(products[24:].sum())
```

Require `single_overlap == 28800` and `cx_overlap == 1920`. All values use the existing small integer counts; no larger denominator or higher-degree moment is introduced. The linear calibration rank stays 79; there are now two independent quadratic overlap equalities.

## Scientific meaning

The extra information is two native-family-specific depth-two mirror calibration experiments rather than one mixture-averaged calibration. The original champion hides opposite family-specific cancellation errors in the mixture.

Let kappa_S=O_S/(24*60^2), kappa_C=O_C/(8*60^2). With CNOT mixture probability eta and a common stochastic layer error epsilon, depth-two mirror entanglement fidelity is

    (1-epsilon)^2 + epsilon^2*((1-eta)*kappa_S + eta*kappa_C).

The two checks enforce kappa_S=1/3 and kappa_C=1/15, so this short-depth calibration equals the baseline for every mixture eta, and under uniform rescaling of epsilon. **The mean channel is still matched only at the nominal mixture**, because family means are not separately constrained. Do not claim full average-channel robustness to sampler changes. Long-depth bias is scored only at the original nominal settings.

## Independently verified champion failure

The actual archived generation-one champion remains a genuine original-task success: bias 0.02452293449, residual 0.00391242715. It also clears the revised 0.0239 numerical threshold. It is rejected by the new calibration, not by a threshold squeeze:

- O_S = **25466**, target **28800**, deficit **3334**.
- O_C = **3587**, target **1920**, excess **1667**.
- The old aggregate still passes: **25466 + 2*3587 = 32640**.

The independent tuple-based audit corroborates these exact integers and the nominal fit. Nearby sampler probes diagnose the consequence: eta=0.35 gives residual about 0.00452214; eta=0.45 gives bias about 0.02218588. These are diagnostic results, not new acceptance cases.

## Private achievability evidence

Eight pair-only continuous SLSQP starts were run; seven converged. The best converged relaxation has bias **0.0239517305094**, residual **0.003808670665**, and S256 **0.006525293180**. Its linear calibration residual is about 2.3e-15 in conditional-probability units; family quadratic residuals are about 1e-12. The separately recorded tuple-based dense-transfer audit rechecks its curve and calibration residuals.

This is **not an integer witness**. Rounding the best relaxation breaks a weighted integer linear equality by one count. The saved searches did not find a valid discrete repair. Passing continuous metrics are neither a discrete feasibility certificate nor an upper bound. Thus **hard_open remains the correct status** at target 0.0239.

The saved feasible stratified baseline is a legal integer point even under these weaker pair-only constraints, but its bias is only about 0.02058961, so it is not a counterexample.

## Private validation entry point

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python ratchet2/check_selected_generation2.py ratchet2/champion_generation1.json
```

Expected exit status is 1, with exactly the two family-pair calibration checks failing. Numerical bias/residual/end-signal checks pass. The checker and all old witness/search material remain private. The public task should include only the revised scientific contract, ordinary nonwinning baseline, and its public evaluator/model.
