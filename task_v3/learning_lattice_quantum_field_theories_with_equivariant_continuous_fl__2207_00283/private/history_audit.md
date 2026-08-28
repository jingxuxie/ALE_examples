# bijx source/history audit

Audit date: 2026-08-27. Scope: the local clone at `private/sources/bijx`, its Git history, modules, and tests. No upstream fetch, source checkout/change, test execution, or agent run was needed for this audit. Paper interpretation, runner design, gauge-physics validation, and checkpoints are outside this audit. Pilot construction, subsequently requested, is separate and confined to `pilots/01_adjoint_composition`.

## Provenance and instructions

- Clone origin recorded by Git: `mathisgerdes/bijx`; non-shallow history; clean source worktree at inspection.
- Inspected HEAD: `f476c5b4a3d51cb4b2883a17cef8bd5501f211cd`, author/committer date `2026-08-23T17:25:37-04:00`. This is the local HEAD, not a claim about the present upstream tip.
- Checked task ancestors and clone descendants for `AGENTS.md`; none were found in the inspected scope.
- Dates below are Git author dates with their recorded timezone, not inferred publication dates. Author and committer dates coincide for the principal fixes.
- File/line references without a revision refer to inspected HEAD. Historical behavior is established by `git show`, `git log`, and `git blame`, not assumed from commit subjects.

| Defect / change | Fixed revision | Recorded date | Immediate pre-fix revision |
|---|---|---|---|
| RK4 normalized-time duration factor | `74828bc91a8107d4dcc3ad91230ef41b40522674` | 2026-08-21 20:43:38 -04:00 | `46537bc05f2db79e6ab949a37f6a70cc32df1886` |
| CG algebra projection and uncalled hooks | `73e4daa1f7f1cee6b1863e781d275d6c67876cd1` | 2026-07-31 22:51:48 +09:00 | `ab5565b9d5cfef841b150dd8b7095d2fb4755812` |
| Guard accidental special projection of 1x1 states | `46537bc05f2db79e6ab949a37f6a70cc32df1886` | 2026-08-21 20:18:55 -04:00 | `73e4daa1f7f1cee6b1863e781d275d6c67876cd1` |
| Kernel resize alignment / edge attenuation | `555423faad970592d63b4b93f16e90f7e9093c92` | 2026-06-30 18:18:06 -04:00 | `1952a4e5880b8f062fd66cfe1bc0008bc1055144` |
| Spectral log-density sign | `7dd214c47e6cb9e13bcf8c77d954acec146840dc` | 2026-03-11 17:40:17 -04:00 | `fa7058d6f710c60976ba1330ae6ed9ec2ef705d9` |
| Later spectral channel layout/counting fixes | `7080c16eff73e339ec4a7ad12594c64093199ba0` | 2026-08-23 17:12:17 -04:00 | `74828bc91a8107d4dcc3ad91230ef41b40522674` |

## 1. RK4 duration: primal and derivative errors, not an RK4-tableau error

**Source:** `src/bijx/bijections/continuous.py:192`, `ContFlowRK4.solve_flow`; low-level adjoint at `src/bijx/solvers.py:369`, `_rk4_odeint_rev`.

The wrapper solves on an auxiliary interval `[0,1]`, evaluates the physical field at `t_start + s * delta_t`, and before the fix multiplies both state velocity and log-density velocity by `where(delta_t < 0, -1, 1)`. The correct multiplier is the signed duration itself. `74828bc` changes only this wrapper; it does not repair the RK4 tableau or rewrite the custom VJP.

For an autonomous linear field `dx/dt = a*x` on `D` real coordinates, the intended result is `exp(a*delta_t)*x` and density increment `-D*a*delta_t`. The pre-fix wrapper instead uses `exp(a*sign)*x` and `-D*a*sign` (up to integration error). Its endpoint sensitivity away from zero is zero for this autonomous example, whereas the intended duration sensitivity is nonzero. Parameter and input gradients are those of the wrong-duration map. At zero duration, the old `where` selects +1 and evolves the state instead of returning the identity. A time-dependent field also exposes incorrect absolute-time handling in proposed partial fixes that merely rescale parameters.

**History:** `c76154f9fdc48ec4aa5e907e0bb10613dfa57ee8` (2025-08-04 16:44:50 +02:00) introduced normalized-time integration with `jnp.sign(delta_t)` to repair reverse integration. `a3f1fa52cc3bf22f84c30f6814c8334e4125802b` (2025-08-04 17:44:33 +02:00) changed that sign to `where` and documented the static step size. Neither includes duration magnitude. Thus reverse-direction correctness and differentiability were previously patched without restoring the full change of time variable.

**Coverage:** `tests/test_bijections_advanced.py:132`, `test_cont_flow_roundtrip`, uses `[0,1]` and only checks inverse consistency/finiteness. `tests/test_nnx_pytree_compliance.py:252` checks pytree behavior, not duration sensitivities. Low-level `odeint_rk4` checks do not exercise this wrapper. `74828bc` adds no regression test. A forward/reverse round trip can pass for the wrong autonomous flow even at nonunit duration.

**Independent checks:** physical endpoint values; absolute density; gradients with respect to both endpoints, field parameters, and input; negative and zero duration; shifted nonautonomous intervals. Use reverse-mode/finite differences or analytic answers, not `jacfwd` through a `custom_vjp` function. A continuous adjoint approximates continuous sensitivities, so do not demand exact derivatives of a coarse discrete RK4 map.

**Difficulty:** the actual fix is a one-line multiplier replacement, plus deletion of the unused sign. Rich evaluation is justified; calling this isolated repair intrinsically hard is not.

## 2. CG: genuinely interacting projector and dispatch defects

**Source:** `src/bijx/cg.py:380`, `UnitaryDeriv.project`; `src/bijx/cg.py:521`, `crouch_grossmann_step`; `src/bijx/cg.py:752`, adjoint-state manifold routing.

Before `73e4daa`, the special algebra projection subtracts `trace(x)/n` from **every entry**, not along the identity, then takes the anti-Hermitian part. For `x = i*I`, it returns `i*(I-J)` with `J` the all-ones matrix, instead of zero. Both matrices can be anti-Hermitian and traceless: checking those invariants alone does not identify the correct orthogonal projection. The fixed function takes the anti-Hermitian part and subtracts `trace/n * I`.

Separately, `post_stage` and `post_step` methods existed but the CG stepper never invoked them. The fix projects each intermediate state before evaluating its vector field, and calls `post_step` on the final update. Fixing only the formula leaves configured projection inactive; wiring only the hooks activates the incorrect projector. The backward solve reuses this stepper with `derivative_type()` for the adjoint and argument cotangents, so the two changes have a real implementation-level interaction.

**Introduction:** blame attributes the bad projector and projection-method definitions to `b19bddee23043ab59e124c461eadb9d0fe770273`, 2025-10-15 23:08:18 +02:00, the `ManifoldType` API refactor.

**Coverage:** `73e4daa` adds `TestManifoldProjection` at `tests/test_solvers.py:608`: scalar-identity and reference-projector comparisons, plus `ZeroingStep`/`ZeroingStage` subclasses that demonstrate hook dispatch. The older `test_gradient_flow_through_integration` at line 219 uses default-disabled projection and only one constant generator. No new test combines enabled manifold/adjoint projection, nontrivial state dependence, and sensitivity accuracy.

**Contract boundaries:** defaults have both projection flags false; `special=True` alone does not enable projection. Derivative projection requires `transport_adjoint=True` (`cg.py:440`). The API requires the vector field to supply Lie-algebra values (`cg.py:539`); these hooks project **states**, not automatically every raw vector-field output. An evaluator that demands arbitrary ambient vector fields be repaired would invent a different task.

**Post-fix trap:** after hooks are wired, accidental projection of U(1) represented as 1x1 matrices with `special=True` erases phases or algebra values. `46537bc` raises explicit errors in both `Unitary.project` and `UnitaryDeriv.project`; it does not implement new U(1) dynamics. The state and derivative objects have independent `special` defaults, so setting only the state object to `special=False` is insufficient when derivative projection is enabled. The guard has no added test. This is a configuration/validation follow-up, not evidence that all correctly configured U(1) integration was broken.

**Difficulty:** projector arithmetic and hook wiring are small, directly exposed patches. Their combination is more defensible than pairing unrelated solvers, but genuinely hard adjoint/geometric validation remains to be demonstrated independently; the shipped sentinel tests alone are easy.

## 3. Kernel resize: true parity bug and incomplete post-fix coverage

**Source:** `src/bijx/nn/conv.py:341`, `resize_kernel_weights`; `ConvSym.__call__` at line 582.

The old helper wraps an extra edge for growing even dimensions, halves edge values for **every** even old dimension (including unchanged or shrinking dimensions), then pads/crops with a different centering convention. For a floating 1D kernel `[a,b,c,d]`, a same-size request becomes `[a/2,b,c,d/2]`: a concrete no-op corruption. Growing even kernels also splits weights across distinct spatial offsets instead of preserving the convolution operator.

`555423f` replaces this with a per-axis shift `floor((new-1)/2) - floor((old-1)/2)`, centered zero padding, or aligned cropping. Under the stated convolution convention, tap `j` has offset `floor((K-1)/2)-j`. Shrinking is not generally operator-preserving: it discards support. The same commit also adds the optional `kernel_params` override to `ConvSym.__call__`; that API extension is not the resize correction.

The caller implementation was refactored in `fad46c8da4504b71fe2f63f34a22de1edafe12d6` (2026-05-19 14:45:57 -04:00), including image-size cropping and proxy delegation to `nnx.Conv`. Prefer a pre-June-fix baseline after this refactor when comparing the exact resize convention, rather than mixing arbitrary historical convolution versions.

**Tests arrive later:** `ab5565b9d5cfef841b150dd8b7095d2fb4755812`, 2026-06-30 18:38:22 -04:00, adds same-shape, convolution-preservation, and supported-crop regressions. `555423f` itself changes only the source file.

**Important coverage flaw, established by source indexing:** `test_resize_kernel_weights_preserves_convolution` (`tests/test_neural_networks.py:108`) supplies shape `(11,1,1)` to a **1D** convolution; `ConvSym` takes the final spatial axis before channels, so this is batch 11, spatial size 1. Every kernel is cropped to one tap. The purported 2D example supplies `(9,9,1,1)`, yielding batch 9 and spatial shape `(9,1)`, not `(9,9)`. The shrinking test at line 138 repeats the 1D layout. These checks do not establish full intended periodic-lattice action. The same-shape multi-parity test remains useful and does catch the attenuation defect.

**Remaining boundary to investigate, not a confirmed runtime failure:** automatic `ConvSym` cropping still starts at `(old-effective)//2` (`conv.py:610`), while the corrected helper starts at `floor((old-1)/2)-floor((effective-1)/2)`. These differ for old odd/effective even sizes, e.g. 5→4 uses 0 versus 1. Hence do not assume arbitrary oversize-kernel parity transitions satisfy the newly documented offset convention. The current resize tests avoid real multidimensional oversize lattices. This discrepancy was not executed or repaired in this audit.

**Composition limit:** a source search finds no production invocation of `resize_kernel_weights` outside its definition/docstring. Kernel transfer is an explicit external operation, not something ordinary CNF integration automatically performs. `ConvVF.__call__` (`src/bijx/bijections/conv_cnf.py:127`) derives its local divergence from orbit-zero weights and then calls the convolution; a transfer task must preserve the orbit/local-tap contract too. Arbitrary refolding into new symmetry orbits is not guaranteed to preserve an arbitrary old kernel. The helper also uses NumPy: differentiability through the offline resize itself is not its current promise.

**Difficulty:** more substantive than a sign flip but still a short indexing correction. Full parity/operator/analytic-divergence interaction may support a stronger task, provided the additional behavior is validated rather than assumed.

## 4. Density scaling: sign fix, then later channel-layout/counting fixes

**Historical source:** `7dd214c^:src/bijx/bijections/fourier.py`, `SpectrumScaling.scale` and `apply`. The FFT map is correct for a valid channel-free spectrum, but `apply` adds the forward log-Jacobian to log density instead of subtracting it. `7dd214c` flips forward/reverse signs. With uniform scale `s>0` in `D` independent real coordinates, forward density must change by `-D*log(s)`; the old result is `+D*log(s)`.

The commit describes a constant offset irrelevant for most training. Qualify that claim: it is constant in the sample only when the spectrum is fixed. Absolute likelihoods remain wrong, and a learnable scale has a wrong density gradient. A forward/inverse round trip cancels either sign convention and therefore cannot validate absolute density. Common normalized importance weights also erase a common density offset.

**Evolution:** `159ccef92893448c9fda7994825a725956a5db76` (2026-05-19 16:26:49 -04:00) removes `scale` and delegates to `complex_affine_apply`. Its forward `-delta_ld` / inverse `+delta_ld` convention survives at `src/bijx/bijections/affine_complex.py:57`. Do not attempt to apply the old one-line hunk literally to the latest `SpectrumScaling`.

**Post-sign-fix gap:** `7080c16` also repairs channel-layout handling, independently of its momentum construction work. `SpectrumScaling._broadcast_scaling` and `apply` (`src/bijx/bijections/fourier.py:108`) align spatial/channel axes and broadcast log scales to the entire event shape before summing real-FFT multiplicities. Previously a shared spectrum could fail broadcasting or, in coincidentally compatible shapes, act along the wrong axis; its density contribution was not multiplied per channel. Per-channel spectra lacked an explicit `space_dim` contract. This is a materially richer density-scaling follow-up than the March sign flip. Momentum/gauge-physics implications are left to the main audit.

**Coverage:** old `test_spectrum_scaling_basic` at `tests/test_bijections_advanced.py:305` checks finiteness, shapes and inverse consistency. Dense-Jacobian absolute-density checks, shared-spectrum channel counting, and per-channel tests appear with `7080c16` at lines 413, 436 and 454. The latter explicitly distinguishes repairing Fourier multiplication from repairing determinant multiplicity. Valid spectra are essential: inconsistent conjugate pairs do not define the promised invertible real-field map.

**Difficulty:** March sign correction is trivial. Axis inference, shared/per-channel scaling, real degrees of freedom, density and parameter gradients give a more substantial coupled contract, but the official patch and tests still reveal the solution if the full fixed history is participant-visible.

## Suggested pairings and independent scoring

1. **Best small authentic scalar pairing: duration adjoint + spectral density composition.** Both are simultaneously present at `fa7058d` (2026-03-11). Compose a valid spectral transform with a time-dependent nonlinear scalar/vector CNF, and reverse in the opposite order. Separately measure endpoint values, time/parameter/input gradients, absolute density, and inverse branches. Use nonunit signed and shifted intervals; include nonzero learned scaling so density gradients matter. Two independent one-line historical repairs remain two easy repairs: the composition is diagnostically useful, not proven hard. A richer variant pairs duration with the later channel-counting defect, but must identify its different pre-fix baseline and API instead of pretending it is the March sign bug.
2. **Strongest intrinsic interaction: CG hook dispatch + algebra projection, optionally guarded 1x1 behavior.** The same stepper and its adjoint route depend on both fixes. Distinguish correct projector values from mere membership invariants, actual stage/step dispatch, and sensitivity accuracy. Do not use a geometry-incompatible arbitrary sentinel as the oracle for real manifold gradients. Keep this separate from scalar RK4 unless a real mixed workflow needs both.
3. **Conditional larger scalar pairing: kernel transfer + nonunit CNF duration + absolute density.** A transferred periodic convolution can change both the vector field and its divergence; wrong time magnitude then changes how those errors accumulate, while a scaling-density sign error is invisible in samples. This can be coherent if transfer is explicitly part of the contract. It is not established by current code that an ordinary flow invokes resizing; use genuine spatial axes and validate operator/divergence behavior. Do not count batch-shaped pseudo-lattice tests as evidence.
4. **Avoid indiscriminate four-bug bundles.** RK4 and CG are alternative backends; spectral scalar scaling does not automatically apply to matrix group states; resizing is offline. Requiring all four without a real shared data path creates breadth, not intrinsic difficulty.

An independent score should have separate numeric families, rather than a single all-or-nothing integration test. References should come from analytic small systems, dense Jacobians of valid finite-dimensional maps, or a separately validated high-accuracy solve; test pre-fix and official post-fix sources under the same runnable dependency environment. Grade absolute density, not just inverse cancellation or ESS. For each family, establish a genuine weak baseline and fixed-source strong baseline and expose continuous error-sensitive scores rather than arbitrary pass thresholds. These are evaluation recommendations, not measured pilot results in this document.

## Baseline / environment cautions

- At `fa7058d` all four historical defects coexist, but APIs differ from HEAD. At `1952a4e` RK4/CG/resize defects coexist while density sign is already fixed. At `ab5565b` only RK4/CG among those principal bugs remain. At `46537bc` RK4 remains and the later spectral channel fix is still absent. At `74828bc` duration is fixed; channel support remains pre-August-23. Do not manufacture a claimed historical state by mixing unrecorded reversions.
- `73e4daa` bundles numerical fixes with relocation-compatible `valid_jaxtype` imports. `f476c5b` removes deprecated JAX ODE internals and inlines `_ravel_first_arg`. These are dependency confounders, not extra scientific difficulty. `pyproject.toml` has broad lower bounds (`jax>=0.5`, `flax>=0.12.1`, `diffrax>=0.6.2`) rather than a full lock. A clean numerical comparison must run both versions, not reward fixing an import error.
- Root `conftest.py` enables JAX x64. Solver tolerances and adjoint comparisons require deliberate precision and integration-error control.
- Full `.git` history and latest tests expose the tiny fixes directly. A participant artifact should preserve authentic pre-fix code and provenance privately, without handing over fixed source, fix-identifying commit messages, or a labeled large hidden set.
- Audit validation is static. No pre/post runtime success, gradient accuracy, scoring calibration, or hard-task success rate is claimed here. The separately requested pilot must supply those measurements before being called ready.
