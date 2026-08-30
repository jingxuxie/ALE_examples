# Prospective NLP residual audit — generation-1 champion

**Decision:** the proposed structural residual objective has a genuine, measurable baseline gap. This is NOT a failure of the original generation-1 contract. LP conversion is validated. Difficulty and achievability of a replacement at 268 scalars still require construction/testing.

## Scope and original contract

- Read-only champion: `champions/generation_1/model.json`; deployment footprint **268 scalars = 264 coefficients + 4 knots**.
- Decoder, task and evaluator are the archived copies under `champions/generation_1/task_snapshot/`. The live participant/evaluator were not used or modified.
- The supplied original broad audit passes with maximum tolerance ratio 0.0012420287. On this sidecar's native-checked grid, the old value tolerance ratio is only 0.000352120167. No original acceptance condition is relabeled as failed.
- Samples: 80 coordinates at half-integer steps, t in [-24,-4.5] and [4.5,24], all three channels; derivative samples at t=+/-6,12,18,24. Reported maxima are sampled, not global supremum claims.

## Measured new-observable loss

The following errors use high-precision replay of the **actual stored binary64 coefficients**, then exact high-precision LP subtraction. Thus they already exclude ordinary binary64 evaluation/subtraction as the explanation. G-prime means differentiation with respect to t, not z.

| Endpoint/channel | Value worst t | Relative error in G | Derivative worst t | Relative error in G-prime |
|---|---:|---:|---:|---:|
| collinear/lc | -22.5 | 0.313563% | -24 | 148.864% |
| collinear/nlc | -23.5 | 0.0394697% | -24 | 7.72084% |
| collinear/nf | -22.5 | 0.201783% | -24 | 19.2663% |
| backward/lc | 24 | 0.00295827% | 24 | 0.403394% |
| backward/nlc | 23 | 0.00357675% | 24 | 0.0485163% |
| backward/nf | 23 | 0.0312292% | 24 | 2.79043% |

Rows are selected by mixed error, abs(error)/(1+abs(truth)), to avoid manufacturing a failure near a zero. The corresponding raw truth/prediction and mixed errors are in `results.json`.

A particularly clear witness is collinear lc at t=-24: native G-prime = -0.998449926726906, reconstructed G-prime = -2.484786765462122. The error is 148.864% relative, or 0.743745 in the mixed metric. Both native and reconstructed quantities are of ordinary finite size; this is not a zero-denominator artifact.

## Root causes by endpoint

**Collinear:** F has a dominant constant-plus-log LP term and an exponentially small q*G correction. Uniformly excellent approximation of F does not control that correction. Its residual derivative involves both delta-F-prime and delta-F, magnifying small spectral truncation/coefficient errors. At the worst lc value sample, density representation error is about 1.67e-11 while actual binary64 polynomial evaluation adds only 1.06e-15. Replaying the same coefficients at arbitrary precision does not repair the missing NLP information.

**Backward:** the LP polynomial is cubic for lc and quadratic for nlc/nf, so the compression objective is dominated by the large LP shape. Residual derivatives still lose up to 2.79% (nf) even though the density contract passes easily. At the lc t=24 sample, representation density error is 2.32e-11 versus 2.94e-13 from binary64 polynomial evaluation; stable binary64 subtraction adds about 0.0198 to G compared with 0.6135 representation-only error. Floating arithmetic matters at very tight future tolerances, but it is not the cause of the demonstrated baseline gap.

For either side q=z(1-z), exactly delta-G=delta-F/q and delta-G-prime=[delta-F-prime-(1-2z)*delta-F]/q. At |t|=24, 1/q is about 2.649e10. These are downstream conditioning identities, not a new defect inserted into the old decoder.

## LP and native validation

- `FORMULAS.md` gives the explicit Eq. (11)/(12) LP polynomials in the lc/nlc/nf basis, including the mandatory lc = fundamental + 2*adjoint conversion.
- Independent comparison with `authoring/endpoint_basis.py` at 240 dps gives coefficient disagreement at most 6.0e-241 and direct residual disagreement at most 6.2e-238.
- Same-domain native source values use 160 and 220 dps; maximum G disagreement is 4.03e-107. The fixed-70-dps/float wrapper is never used.
- G-prime uses independent five-point central stencils at h=1e-10/1e-14 and 160/220 dps; maximum refinement disagreement is 1.22e-43.
- Deep endpoints use 200/280 dps at t=+/-30,40,50,60. After subtracting LP, the residual converges to the complete NLP logarithmic polynomial of Eq. (11)/(12). The maximum scaled NLP remainder decreases from 9.65e-14 to 9.38e-27 on the left, and 4.22e-13 to 3.70e-26 on the right (|t|=30 to 60). Native precision disagreement at the hardest deep-left point is only 3.28e-69.
- All protected input hashes are unchanged. Results are numerical convergence checks, not interval-arithmetic proofs.

## Ratchet assessment and implementation cautions

**Scientifically legitimate:** accurate LP-subtracted endpoint values and slopes are different physical coefficient information, not an arbitrary tightening of the old density tolerance. The paper explicitly supplies the NLP expansions. The original champion demonstrably does not preserve this information, even when its arithmetic is replayed at high precision.

**Structurally feasible, not proven difficult at the proposed budget:** permitting per-interval density/collinear-residual/backward-residual charts avoids demanding impossible cancellation from a density-only deployment. Accurate residual calibration makes retraining meaningful. Reusing the same 268-scalar footprint, shared intervals and joint physical density/bin requirements creates a real allocation problem, but this audit does not construct a replacement or establish its fresh-agent hardness. Known analytic LP/NLP polynomials may make a well-designed residual representation compact; do not infer difficulty just from the old champion failing the new observable.

**Evaluate the residual chart directly.** A residual-chart model must return G and G-prime from that chart, not reconstruct F and then subtract LP again. Otherwise the evaluator reintroduces the very binary64 cancellation the chart is intended to remove. Reconstruct F as F_LP+q*G for original physical values, derivatives and finite-bin integrals; use the analytic q-prime and F_LP-prime in the chain rule.

**Keep exact geometry.** F_LP is (1-z)*P_left(log z) or z*P_right(log(1-z)), not just P. Dropping these factors or replacing log(epsilon) by -abs(t) changes genuine NLP coefficients. Evaluate both logistic tails and their logarithms stably, without forming the tiny right tail as binary64 1-z.

**Specify transitions and scoring before freezing.** Retain physical F/F-prime checks on both sides of chart knots, explicitly state that residual derivatives are t derivatives, evaluate G in the declared endpoint zones t<-4 or t>4, and preserve the original physical finite-bin observable rather than treating an integral of G as equivalent. A mixed residual metric avoids exaggerated errors at genuine zeros. No numerical tolerance or new generation is frozen by this sidecar.

## Artifacts and reproducibility

`audit.py` reproduces the source/model comparison; `results.json` contains every sample and deep-limit check; `independent_basis_check.json` records the independent LP comparison. Native work took approximately 10.06 seconds once sandbox startup was bypassed with approved scoped execution. All writes are confined to this directory.
