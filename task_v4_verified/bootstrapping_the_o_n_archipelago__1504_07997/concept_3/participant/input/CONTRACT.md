# Exact experiment contract — REDUCED model

Paths in this document are relative to the participant directory.

Implement `workspace/policy.py`: a sequential experimental-design policy with
**72 scalar measurements per instance**, not a full 3d crossing/CFT solver.
The paper seed is *Bootstrapping the O(N) Archipelago*, arXiv:1504.07997.
Shared OPE-vector ratios motivate the matrix residues below. Our strengths are
reduced-model OPE proxies, **not** extracted CFT data or current central charges.

## Experiment

You observe a positive 2×2 matrix Laplace transform (radial coordinate `r=exp(-t)`):

```
G(t) = a0 v(theta0)v(theta0)^T exp(-delta0 t)
     + a1 v(theta1)v(theta1)^T exp(-(delta0+gap)t)
     + integral_[3,infinity) exp(-Delta t) dT(Delta)
v(theta) = (cos(theta), sin(theta)),    dT >= 0.
y = u^T G(t) u + Normal(0, sigma(t)^2)
sigma(t) = 1.2e-5 + 2.5e-4 exp(-1.1t).
```

Each call chooses any real `t` in `[0.25,6]` and any real unit direction `u` in
two dimensions. Noise is independent across calls, with the same known sigma
for all directions. A repeated query costs another call and gets fresh noise.
There is no noiseless matrix/tail/derivative query. Early times have stronger
signal but unknown positive tail; late times suppress tail but lose signal.
Matched probes and probes nulling a dominant state have different information
about strength, mixing angle, and the spectral gap. No family label is supplied.

Infer these four quantities for the *lowest-energy* state, not the largest residue:

| Key | Meaning | Error scale |
|---|---|---:|
| `delta0` | lowest radial exponent | 0.05 |
| `log_gap` | natural log of positive separation | 0.35 |
| `log_a0` | natural log of squared low OPE-vector norm | 0.25 |
| `theta0` | projective OPE mixing angle, modulo pi | 0.15 rad |

The OPE-vector ratio is `tan(theta0)` where finite. Scoring the angle avoids an
artificial divergence at a dark channel. The sign of the whole vector is irrelevant,
but the relative sign of its two entries is observable by mixed probes.

## Known resource family and training

`input/model.py` is the exact public generator and simulator. It has no hidden
resources. All family distributions, tail distributions, and noise are public;
only evaluation seeds and realized parameters are private. Families have equal
weight; test suites are balanced and shuffled.

| Family | Special feature (other parameters use common defaults) |
|---|---|
| regular | common defaults |
| dark_state | a0 log-uniform [.15,.4], a1 [1.2,2]; directions nearly orthogonal |
| near_degenerate | gap uniform [.045,.12]; angular separation [.65,1.3] |
| aligned_residues | separation [.075,.18], gap [.45,.8]; a0 [.5,1.2], a1 [.6,1.8] |
| weak_low | a0 [.045,.1], a1 [.9,1.8], gap [.5,.85], separation [.55,1.25] |
| tail_nuisance | tail trace log-uniform [4,10] instead of [.4,2] |

Common defaults: delta0 uniform [.8,1.15], gap uniform [.35,.8], a0 log-uniform
[.5,1.4], a1 log-uniform [.5,1.5]. All weight intervals in the table are
log-uniform; gaps/separations are uniform. theta0 is uniform modulo pi and
separation has random sign. Dark separation is pi/2 + uniform[-.06,.06].
Hard features are **not** compounded arbitrarily: aligned poles are not also
nearly degenerate, and the weak state has a substantial gap. The low-state labels
are identifiable; exact degeneracies and zero residues have zero probability.

The tail has 4–10 rank-one positive atoms with Dirichlet(.7) relative weights,
energies uniform [3,8], except the first energy uniform [3,3.3]. A uniform
[.15,.45] fraction of total tail trace belongs to a full-rank positive matrix
times a shifted Gamma spectral density. Its Laplace factor is
`exp(-3t)/(1+s*t)^k`, `s` uniform [.35,.9], `k` uniform in {1,2,3}. Its random
eigenbasis and trace fractions uniform [.1,.5] are public in the generator.
Thus the tail is not just another fixed pole. Its trace is at most 10 and its
support starts at 3, so `||T(t)|| <= 10 exp(-3t)` is a valid public bound.

Run `python input/sample.py --family weak_low --seed 123` from the participant
directory for a labeled training sample. You may import `model.generate`,
`model.Oracle`, and `baseline_impl` to train on arbitrarily many public seeds.
Do not access evaluator files, other submissions, hidden suites, or the network.

## Interactive protocol (stdin/stdout, UTF-8 JSONL)

The evaluator starts a **new process for each instance**; the tournament wrapper
uses scratch as the working directory. `import radial_public` adds public input to
the module path; it is provided via the read-only participant workspace on
`PYTHONPATH`. Without the wrapper, `RADIAL_INPUT` names the input directory.
The helper also supports a copied workspace by locating input through the
wrapper's public `PYTHONPATH`, rather than depending on the submission's location.
Only scratch is writable in the tournament sandbox. Allowed numerical libraries: numpy, scipy,
mpmath and Python standard library; no cvxpy. Use CPU, one BLAS thread.

1. Read one `hello` line (format in `input/protocol.py`). It has the common budget,
   t range, target names, scales, noise law, and family mixture, **no case secrets**.
2. Print and flush a query, then read its reply before issuing another:
   `{"type":"measure","t":3.1,"u":[0.6,0.8]}`.
3. Reply: `{"type":"observation","index":1,"y":0.042,"sigma":0.0000203,"remaining":71}`.
   The shown values are schematic, not a reference datum. Negative noisy y is valid.
4. After at most 72 queries, print one final answer and exit with code zero:

```
{"type":"answer","estimate":{"delta0":1.0,"log_gap":-0.7,"log_a0":-0.3,"theta0":0.2},"radius90":{"delta0":0.04,"log_gap":0.3,"log_a0":0.2,"theta0":0.1}}
```

`radius90` is a central **90% marginal** interval half-width in the stated
coordinates. For theta it is a circular arc; canonicalize the center to
`[-pi/2,pi/2)` and keep its radius at most pi/2. Other radii must be in
`[1e-6,100]`, estimate magnitudes at most 1e6. Unit-vector tolerance is 1e-6.
Types/keys are exact: no bools as numbers, nonfinite values, duplicate keys,
extra fields, extra stdout, or unterminated lines. Diagnostics go to stderr.
Limits: 16 KiB/line, 1 MiB total stdout, 64 KiB stderr, 15 seconds between
protocol messages, 45 seconds total per instance, exit within 2 seconds of answer.
Malformed output, exhausted budgets, crashes, and timeouts invalidate the run.
You may answer early; unused calls earn no bonus.

## Frozen score and target

Frozen caps: robust loss **0.165**, worst-family point loss **0.22**; coverage floors
**0.80 overall**, **0.60 per family**. The 24-case pre-fresh baseline has robust
loss 0.2265248300, so the robust cap requires a 27.16% improvement on that reference.
`input/target.json` is authoritative. For each target, let `e` be absolute error
(shortest circular error for theta), `h` its radius, and `s` its error scale.
Point loss is `e/s`; interval loss is `(2h + 20 max(e-h,0))/(4s)`. Combined
loss is `.7*point + .3*interval`, averaged over the four targets. Wide intervals
are penalized, so reporting the whole prior range does not solve calibration.

Average per family. Robust loss is `.35*mean_family_loss + .65*worst_family_loss`;
`core_score=100/(1+robust_loss)`. A pass requires all cases valid, the frozen robust
loss and worst-family point-loss caps, overall and worst-family coverage floors,
and an official isolated suite of at least eight cases per family. Calibration
coverage is the fraction of the four marginal intervals covering their targets.
No truth or score is returned while your process is alive. There is no hidden
bonus for recognizing family names, nor any requirement to recover the tail.

The target is frozen against a pre-fresh baseline, not adjusted after tournament
results. Operational achievability is unproven; privileged local-information
diagnostics, if supplied, are not a reference policy or a solvability guarantee.
