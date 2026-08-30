# Recommended generation 2: native-family-stratified calibration

Status: **hard_open**. No passing generation-two integer witness is known. This is one proposed public ratchet, not three. The three private search ablations do not establish impossibility or participant difficulty.

## Preserve generation 1

Keep its artifact schema, 192 integer counts, denominator 3000, row sums and bounds, four-qubit gate ensemble, nominal CNOT probability 0.4, layer infidelity 0.02, depth grid 0,2,...,256, exponential fitting procedure, bias target 0.0244, maximum residual 0.004, and minimum final signal 0.005. Keep all existing calibration checks. Do not tighten the bias threshold, introduce larger integer denominators, or change public scoring across noise rates.

## Add only native-family calibration

Let S denote the 24 single-qubit gate classes and C denote the eight CNOT classes. Embed each row as counts c_L(Q) over global nonidentity Paulis. Ideal Clifford conjugation ignores signs.

For every global Pauli Q require the following **unweighted** family sums:

- Sum over S of c_L(Q) equals 120 for a weight-one Pauli and zero otherwise.
- Sum over C of c_L(Q) equals 16 for a weight-one Pauli, 8 for a weight-two Pauli on a ring edge, and zero otherwise.

Also require these **unweighted** family inverse-pair overlaps:

- Sum over L in S and Q != I of c_(L^-1)(Q) * c_L(L Q L^-1) equals **28800**.
- The analogous sum over L in C equals **1920**.

These are separate calibration experiments on the two native gate families. They use the existing small counts. No new high-degree or giant-integer moment is introduced. Given the generation-one constraints, only one family of mean-channel equalities and one family-overlap scalar are independently new. The linear-constraint rank grows from 79 to 87, and there are two independent quadratic overlap equalities instead of one.

## Why this is a physical ratchet

With CNOT probability eta, the average noise channel is (1-eta)*E_S + eta*E_C. Matching both family channels guarantees baseline calibration matching for any eta, rather than compensation at eta=0.4 only.

Define kappa_S as the single-family overlap divided by 24*60^2, and kappa_C as the CNOT-family overlap divided by 8*60^2. For a common modeled layer infidelity epsilon, the depth-two mirror entanglement fidelity is

    (1-epsilon)^2 + epsilon^2 * ((1-eta)*kappa_S + eta*kappa_C).

The new overlap conditions give kappa_S=1/3 and kappa_C=1/15, the baseline values. Thus depth-two calibration also matches for every sampler mixture, and for every epsilon if the same conditional stochastic noise is uniformly rescaled. This is a statement about calibration, not a claim that the fitted bias or residual must remain unchanged. Scoring stays at eta=0.4 and epsilon=0.02.

The strengthened scientific conjecture is: even after native-family-stratified first-moment and inverse-pair calibration, a near-exponential mirror decay cannot underestimate the common layer infidelity by at least 2.44%. It is a quantitative test inspired by the paper, not a theorem attributed to it.

## Actual champion failure

The generation-one champion is genuinely valid under its original contract. Independent verification reproduces bias 0.02452293449 and residual 0.00391242715.

It fails the new contract by substantial, exact calibration defects:

- Maximum single-family marginal count defect: **48**.
- Maximum CNOT-family marginal count defect: **24**.
- Single-family overlap: **25466**, not 28800.
- CNOT-family overlap: **3587**, not 1920.

The original overlap passes only because 25466 + 2*3587 = 32640. The mean-channel defects similarly obey Delta_S(Q) + 2*Delta_C(Q) = 0. These are native-family compensation effects, not violations of Markovianity or constant layer infidelity.

Independent dense-transfer checks at nearby sampler settings show the operational sensitivity:

| CNOT probability | Relative bias | Maximum residual | Original numerical gates |
| --- | --- | --- | --- |
| 0.35 | 0.02734105 | 0.00452214 | Residual fails |
| 0.40 | 0.02452293 | 0.00391243 | Pass |
| 0.45 | 0.02218588 | 0.00343081 | Bias fails |

These off-nominal checks diagnose a limitation of transferability. They do not retroactively invalidate the generation-one win, and they are not additional generation-two scoring cases.

## Three root-cause clusters

1. Native-family compensation: the main actionable failure above. Sampling-weight changes alter which calibration defects cancel.
2. Noise-strength dependence: with a depth horizon scaled inversely with epsilon, bias is 0.00720018 at epsilon=0.005, 0.01380437 at 0.01, 0.02452293 at 0.02, and 0.03883121 at 0.04. This is ordinary finite-noise correction behavior, not evidence of a checker bug. Do not demand the same bias floor as epsilon approaches zero. At epsilon=0.022 the residual reaches 0.00430929, showing that signal-shape and bias limits define a restricted error regime.
3. Higher-depth spectral curvature: short calibration is not sufficient to fix the whole curve. At depth 16 the champion exceeds the baseline polarization by 0.00030475139; at depth 32 by 0.00076720449. Fits on depths 0..32 and 64..256 give biases 0.01361279 and 0.03393306, with residuals 0.000902524 and 0.000167436. This is compatible with stationary Markovian noise. Additional tiny short-depth tolerances would risk an arbitrary precision squeeze, so they are not recommended for this ratchet.

## Achievability evidence and caution

Twenty-four continuous multistart searches were run, eight per ablation, with the original scoring thresholds unchanged. Best converged biases were:

- Separate family means only: **0.02374929050**.
- Separate family depth-two overlaps only: **0.02395173051**.
- Both, the recommended contract: **0.02366557422**.

These are discovered continuous candidates, **not upper bounds**, and not accepted integer witnesses. Some starts hit their iteration limit. Pair-only integer rounding/repair attempts did not produce a passing artifact. No claim of guaranteed solvability follows from this search. Keep the task marked hard_open, or retain the archived generation-one task if a planted-solvable benchmark is required. Do not lower or squeeze thresholds to manufacture a result without explicitly revising the scientific claim.

`stratified_feasible_baseline.json` is an integer artifact satisfying all new calibrations but missing the unchanged bias target. It demonstrates a nonempty admissible class, not a passing counterexample.

## Reproduce privately

From the parent adversary directory:

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python ratchet2/stress.py ratchet2/champion_generation1.json
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python ratchet2/independent_audit.py ratchet2/champion_generation1.json
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python ratchet2/check_generation2.py ratchet2/champion_generation1.json
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python ratchet2/family_search.py --starts 8 --stratify-pairs
```

The generation-two checker exits 1 for the old champion, as expected. All sidecar work is private; no participant/evaluator files or generation-one evidence were modified.
