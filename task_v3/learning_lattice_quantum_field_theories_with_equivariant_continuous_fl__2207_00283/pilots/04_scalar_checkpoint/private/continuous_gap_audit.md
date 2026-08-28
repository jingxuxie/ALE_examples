# Continuous-flow accuracy: bounded sidecar audit

Scope: read-only inspection on 2026-08-27 PDT, apart from this document. No
model execution, benchmark, new case, scoring change, or participant change.
The main runner's ongoing refinement audit was not launched or duplicated.
Paths below are relative to the pilot directory unless stated otherwise.

## Finding

**Discretization error is source-grounded, but the present evidence primarily
exposes an oracle/contract qualification, not a demonstrated failure of the
submitted implementation or a new hard numerical regime.**

The public contract says to solve the continuous IVP without mandating an
integrator, while disclosing—and grading against—100-step RK4 references.
The submission deliberately implements that same discretization efficiently.
Main's reported isolated scores, approximately 0.99698 initially and 0.99116 on
challenge, therefore establish excellent checkpoint/reference agreement and
runtime, not convergence to the continuous solution. Selecting 100 steps was
a reasonable response to the disclosed reference, not evidence of misconduct.

Existing L32 refinement results already show small, nonzero reference bias.
Its consequences for L64 and conditional transfer remain pending in the main
audit. Neither the failed assertion alone nor near-perfect reference scores
settle that question. Public files should remain frozen; do not retrospectively
reinterpret the submission as having violated an undisclosed convergence test.

## What Appendix C actually establishes

[P] Gerdes et al., *Learning Lattice Quantum Field Theories with Equivariant
Continuous Flows*, arXiv:2207.00283v3, section 4, printed p. 7; Appendix C,
printed pp. 13–14, especially Figure 8 on p. 13. Checked against the arXiv PDF;
the retained source copy is `../../private/sources/paper.pdf`.

Section 4 normally uses 50-step RK4. Appendix C studies maximum forward/reverse
round-trip error over 4096 Gaussian latent samples for trained single-theory
models. It reports float32 RK4 saturation near 60 steps, further improvement
with float64, and approximately 1e-6 round-trip error for 100-step float64
Tsit5. It explicitly permits changing steps, method, or precision after
training, and relates discretization error to Monte Carlo statistical error.
It does not present proposal integration as the primary bottleneck. [P]

**Interpretation:** this supports checking convergence, but does not certify
100-step RK4 for this pilot's componentwise density metric, conditional
transfer, arbitrary reverse inputs, or every allowed field. A round trip is
also not an independent bound on either one-way flow or transported density.

## Contract and implementation anchors

- `participant/input/SPEC.md:102` defines exact instantaneous divergence and
  partial coupling derivatives; `participant/input/SPEC.md:110` defines the
  forward/reverse state and density IVP. `participant/input/SPEC.md:119` calls
  the IVP the numerical target, but also identifies 100-step RK4 references
  and separate refinement checks. This is the material tension.
- `participant/input/SPEC.md:179` and `private/evaluator.py:77` define smooth
  relative-error quality, with transport scale 2e-4. There is no zero-penalty
  band below that scale. `private/evaluator.py:87` averages RMS and maximum
  relative errors; `private/evaluator.py:166` scores transported density
  changes rather than letting the initial density mask errors.
- The public starter itself uses adaptive `solve_ivp` with rtol=1e-7 and
  atol=1e-9: `participant/workspace/solve.py:47`. This reinforces that a
  different integration scheme is legitimate, although it does not certify
  that starter's accuracy in the evaluator's norm.
- `attempt/initial/solve.py:201` precomputes time-dependent kernels at all
  2N+1 RK4 stage times. `attempt/initial/solve.py:218` defaults to N=100 and
  implements the four classical stages and density quadrature;
  `attempt/initial/solve.py:249` invokes it without changing that default.
  There is no step-doubling test or adaptive error controller on this path.
- Larger feature-volume workloads dispatch at
  `attempt/initial/solve.py:220` to `attempt/initial/fast_transport.py:50`.
  Its four-stage loop and outer N-step loop are at
  `attempt/initial/fast_transport.py:81` and
  `attempt/initial/fast_transport.py:107`. Float64 is enabled at line 11.
  This is still fixed-step RK4, not a different higher-order integrator.
  The half-step grid evaluates the time basis at RK stages; it is not evidence
  of an additional coarse, piecewise time interpolation.
- The author adapter defaults to 100 steps at
  `private/reference/author.py:80`, passing `int_steps` at line 91.
  The original implementation exposes configurable integration in
  `../../private/sources/continuous-flow-lft/jaxlft/cnf.py:146`, and classical
  RK4 in `../../private/sources/continuous-flow-lft/jaxlft/ode.py:65`.
  Thus 100 is a pilot reference choice, not an immutable trained parameter.

The fast backend also contains a sine/cosine approximation and a large-phase
fallback (`attempt/initial/fast_transport.py:14` and line 69). No accuracy claim
about extreme phases is made here. Crucially, the main refinement audit calls
the **author** implementation at different step counts, not this backend;
author-to-author refinement differences cannot be attributed to the submitted
FFT or trigonometric approximation (`private/reference/refinement_audit.py:34`).

## Numeric evidence available during this inspection

The existing `private/reference/refinement_validation.log` ends at the
assertion in `private/reference/validate.py:77`. That check uses a maximum-only
error normalized with a floor of 1 (`private/reference/validate.py:14`) and a
2e-5 cutoff. It is not the evaluator's mixed RMS/maximum norm or its 2e-4
transport scale. The bare traceback neither identifies the failing case nor
records the error magnitude. Its failure is a convergence warning, not by
itself proof of a specified grading-accuracy violation.

The read-time snapshot of `private/reference/refinement_audit.json` contained
two completed records: `test/forward32` and `test/reverse32`. These are results
already produced by main, not computations performed by this sidecar:

| Existing case/output | 100 vs 400 relative error | Audit diagnostic quality | 200 vs 400 relative error |
|---|---:|---:|---:|
| forward32 / phi | 1.10994e-5 | 0.947421 | 5.27081e-7 |
| forward32 / logp change | 2.94344e-6 | 0.985496 | 1.30988e-7 |
| reverse32 / phi | 4.59593e-6 | 0.977537 | 1.64196e-7 |
| reverse32 / logp change | 9.15201e-7 | 0.995445 | 6.83351e-8 |

Precise data anchors are the JSON records with those `id` values, keys
`100_vs_400` and `200_vs_400`, then `phi`/`logp`. The audit metric is implemented
at `private/reference/refinement_audit.py:8`. Its target in this table is the
400-step result; scoring a 400-step candidate against the current 100-step
golden reverses the normalization target. The displayed qualities are therefore
diagnostics, not newly measured submission grades.

The smaller 200-to-400 increments support convergence, but do not prove 400
steps is exact or establish a uniform convergence order. Already, an error of
order 1e-5 matters to a smooth quality score even though it is below 2e-4.
Matching the 100-step algorithm can receive higher quality than approaching
the IVP more closely. Tightening tolerances against the same biased goldens
would strengthen that incentive, not demonstrate a harder scientific task.

**Pending:** remaining L64/conditional/directional results, certification that
the finest results are sufficiently resolved, and the cost of any refinement
in the submitted fast implementation. This audit does not wait for or predict
those measurements.

## Input distribution and natural counterexample regions

Distinguish the public API from the private case generator. The public API
specifies B=1 or 2, lattice/profile ranges, physical couplings, and no explicit
field-amplitude bound (`participant/input/SPEC.md:135`). It does not promise a
particular sampling law. The only public example is a probe, copied at
`build.py:153`; there is no public transport convergence example.

Actual case generation starts from independent standard-normal fields
(`build.py:133`). Reverse cases instead use 0.38 times that noise plus a
0.18-amplitude sinusoid, and arbitrary carried densities (`build.py:134` and
line 145). They are not demonstrated draws from the learned output distribution.
Transport cases are single-row trajectories (`build.py:109` and line 122).
Existing conditional transports use physical couplings 4.46, 5.54, 5.91 and
4.09. Coupling midpoint/endpoints and odd-transfer examples are currently
**probes**, not time-integration stress tests (`build.py:118`).

Natural places to assess an existing numerical gap are therefore:

1. The already present Gaussian-input native L64 forward trajectories, and
   ordinary Gaussian draws for the same released models. Broader coverage of
   that distribution is source-supported by Appendix C, not a license to
   manufacture enormous fields or cherry-pick pathological states.
2. Reverse execution on actual forward-model images, alongside the already
   specified reverse inputs. The former has a direct sampling interpretation;
   the latter is valid API coverage but cannot stand in for model-distribution
   evidence. A self-consistent round trip alone still cannot certify density.
3. The already present conditional L32 and explicitly allowed L32-to-L64
   transfer transports, including their existing couplings. No new trained
   conditional L64 checkpoint should be implied (`participant/input/SPEC.md:20`).

These are candidate regions for interpreting main's measurements, **not new
hard cases proposed or generated here**. Physical criticality does not itself
prove stiffness of the learned ODE. Gaussian interpolation is smooth, and
lambda is fixed along a trajectory (`participant/input/SPEC.md:47` and
line 113); crossing a basis midpoint is not a numerical event requiring an
ODE step transition. Odd/even resizing is a geometry issue, not automatically
a time-resolution issue.

## Claims that survive, and the ratcheting decision

Final main-session follow-up: all ten 100/200/400-step reference audits have
completed. Mean/minimum output quality is 0.96482473/0.83904877 for 100 versus
400 steps and 0.99802920/0.99107039 for 200 versus 400. The unchanged fresh
submission was separately re-executed against the 400-step answers at the
original thresholds: initial mean/worst family 0.98841780/0.95374110,
challenge 0.98341262/0.92946041, with no execution failures. These are
diagnostics, not replacement grades or new fresh-agent confirmations. They
strengthen the rejection decision while retaining the continuum qualification.

The source/checkpoint grounding, full lattice and feature sizes, measured
speed, and faithful **100-step execution** remain valid claims. Instantaneous
vector-field, exact-trace, coupling-derivative and geometric-kernel scores do
not depend on solving the transport IVP. These probe branches account for
70% of the specified group weight (`participant/input/SPEC.md:173`); a transport
qualification does not erase their evidence or the implementation work.

What is not yet certified is a uniform continuous-flow error budget, an exact
finite-step likelihood, or sufficiently small bias in physical observables.
Integrating the exact instantaneous divergence numerically does not make that
quadrature exact. Nor does it automatically equal the exact log determinant
of the finite-step RK4 state map. Those distinctions qualify claims; they are
not a proposal to introduce a new discrete-Jacobian task.

A source-grounded accuracy/cost ratchet would require main to demonstrate a
material, convergent error on ordinary inputs in an existing supported regime,
with the finest-reference uncertainty below the stated accuracy budget, and
then establish a meaningful cost/accuracy distinction for the fast submitted
solver. That would remain within checkpoint execution. It would first require
an unambiguous continuous target and trustworthy oracle, not merely a smaller
tolerance around 100-step results. If uniform additional RK4 steps resolve the
entire issue comfortably, this is routine numerical refinement, not evidence
of a new frontier-level bottleneck. No such hardness claim is justified by the
two completed L32 records or the failed assertion alone.

**Handoff:** retain the current scores as reference-execution results. Treat
the continuum claim as qualified pending main's existing audit. Do not change
the frozen public contract, create counterexamples, or rewrite scoring on the
basis of this sidecar.
