# Source-grounded reference

Only `participant/` is public. In particular, neither this directory nor
`attempt/strong` or `attempt/frozen` belongs in a participant mount.

The original `jaxlft` sources are copied from the retained
`private/sources/continuous-flow-lft` checkout. `vendor/later_conv.py` is the
author's later `bijx/src/bijx/nn/conv.py`, including resize fix 555423f.
`provenance.json` pins commits and source/archive hashes. `build.py` exports
the three actual author checkpoints from `phi4_parameters.zip`; no parameters
are synthesized, pruned, retrained, or substituted. The only supplied pickle
read is of that trusted author archive during build; all execution inputs use
pickle-free NPZs.

## Adaptations, not replacement solutions

- `ode.py` imports `tree_leaves`/`tree_map` from `jax.tree_util`, and passes the
  current `api_util.debug_info` argument to `ravel_first_arg`, matching the
  installed JAX ODE wrapper. All RK4 arithmetic and reverse-flow signs remain
  unchanged. No custom adjoint differentiation is used by this pilot.
- Haiku parameters and inputs are promoted to float64. Native execution calls
  the original `Phi4CNF`/`Phi4CNFConditional`, feature contraction, analytic
  divergence, convolution and RK4 directly. The stored reference uses 100
  steps; the architecture's original default is 50. The separate 100/200-step
  check failed its strict refinement assertion. `refinement_audit.py` retains
  further 100/200/400-step comparisons without replacing frozen answers.
  These qualify the continuum claim, not faithful 100-step execution; see
  `../continuous_gap_audit.md` and the root report. No hardness claim is based
  on this author-side ambiguity.
- Row-aligned lambda vectors are vmapped over the original scalar coupling
  entry point. This avoids depending on the original vector-lambda reshape
  convention and introduces no mathematical change to individual rows.
- The transfer profile composes the author's original `pad_kernel_weights`
  boundary-split lift, the later `resize_kernel_weights`, and later `ConvSym`.
  Its physical displacement and normalization are fully public. This is a
  supported deployment composition, not an assertion that a conditional L64
  model was trained. The NumPy resizing functions run on labels and unit
  weights outside JIT; their resulting gather/scaling map is applied to the
  original dynamically contracted kernel. This permits JIT and JVP without
  rewriting the author's tensor contraction or analytic trace. The original
  zero-displacement coefficient remains the correct diagonal after this lift.
- Conditional derivatives use JAX JVP through the original scalar vector
  field, including all three occurrences of Gaussian coupling interpolation.
  Kernel output is captured at the convolution boundary, not reconstructed
  with an independent proposed solution.

The public starter is a separate, deliberately slow NumPy implementation of
native fixed-model inference. It materializes the full spatial Jacobian and
uses its trace, then a SciPy IVP solver. Conditional and transfer branches are
left to the participant. The privileged `attempt/strong` wrapper is an oracle
self-test, not a participant solution. `attempt/frozen` is an empirical
ablation: it calls the author architecture but freezes all conditional inputs
at lambda=5, so it cannot obtain the nonzero coupling derivative by merely
adding a fast convolution and an ODE solver.

## Build and run

From this pilot directory, use:

```
PY=participant/input/runtime/bin/python3.12
taskset -c 40-43 "$PY" build.py --stage all
taskset -c 40-43 "$PY" private/reference/validate.py --refine
"$PY" private/evaluator.py --submission attempt/strong --trusted-reference --calibrate-reference --report attempt/strong-test.json
"$PY" private/evaluator.py --submission attempt/strong --trusted-reference --calibrate-reference --pool challenge --report attempt/strong-challenge.json
"$PY" private/evaluator.py --submission participant/workspace --report attempt/dense-test.json
"$PY" private/evaluator.py --submission attempt/frozen --trusted-reference --report attempt/frozen-test.json
```

`build.py --stage assets` rebuilds the manifests; run `--stage references`
afterwards to fill them with precomputed answers and calibrated timings.
Do not rebuild assets while evaluating. The builder uses the provided
`/tmp/ale_python/cpython-3.12.12-linux-x86_64-gnu/bin/python3.12`; the evaluator
prefers the dependency-only public runtime. Neither creates or modifies that
runtime. References and submissions are pinned to cores 40-43, with four
compute threads and CPU JAX. Reference files and per-case timing logs are
retained, as are empirical reports in `attempt/`.

The evaluator now launches every case through `bwrap --unshare-all`, exposing
only the public participant tree, the submission, staged request/output files,
and system libraries. Public/submission directories are also mounted read-only
at their original absolute paths and their `/home`/`/srv/home` aliases; no
parent or private directories are mounted. `ALE_INPUT_DIR` remains `/task/input`.
It clears the environment and disables network access.
Launch it outside a parent sandbox that forbids NETLINK/user namespaces. There
is no unisolated fallback. The timeout floor is 60 seconds to accommodate cold
shared-filesystem imports. Runtime calibration executes the actual author
solver using the SAME public interpreter, mounts and environment as ordinary
submissions. Explicit trusted-reference mode additionally mounts only the
author adapter and vendor code, never expected answers, and is restricted to
the two private oracle wrappers. Calibration updates timing denominators but
does not regenerate or replace the already checked numerical answers.

The final continuous-reference audit preserves seven serially completed
transport cases and three further cases run concurrently on separate four-core
allocations. `ALE_REFERENCE_CORES` changes only author-audit affinity; scored
calibration and evaluation retain cores 40-43. The integration arithmetic is
unchanged. `merge_refinement.py` combines the ten completed records and
records the intentional author-only interruption used to parallelize them.

The empirical identity baseline is also an isolation smoke test: it asserts
that host task paths and private author code are unavailable. Reports retain
the numerical/runtime score and, when `empirical_anchors.json` is present,
an additional unclipped weak-to-strong normalization against actual measured
baseline/reference executions. These anchors are descriptive, not another
accuracy threshold or a replacement for the independent scientific scores.
