# Trusted operator/response reference

This directory is private. Never mount it into a participant execution.
`oracle.py` executes official source on the numerical case, not an answer lookup.
The precomputed NPZ files let ordinary evaluation run without installing the
reference package into the contestant environment.

Run from the task root (the parent of `pilots`):

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 authoring/wb_reference_env/bin/python pilots/02_operator_response/private/reference/build.py
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 authoring/wb_reference_env/bin/python pilots/02_operator_response/private/reference/validate.py
/usr/bin/python3 pilots/02_operator_response/private/evaluator.py --submission pilots/02_operator_response/attempt --split test --output pilots/02_operator_response/private/reference/weak_test.json
```

The evaluator uses the parent's `authoring/sandbox_exec.py`, 180 seconds and 8 GiB
per case, and refuses an unsandboxed fallback. The helper always uses system
Python inside bwrap, regardless of the evaluator's interpreter. Namespace
permission errors require an escalated host invocation of the same evaluator
while retaining bwrap isolation.

The original official source and tutorial checkouts are pinned in
`source_manifest.json` with data SHA-256 and exact package versions. Executed
modules `symmetry/sym_wann_2.py`, `formula/covariant.py`, and
`calculators/dynamic.py` are checked byte-for-byte against the source checkout at
build time. `System_R.symmetrize2`, `Data_K_R`, `Omega`, and `Formula_OptCond`
provide the reference physics. No custom Berry solver generates the reference.
An independent central-difference spectral-projector and position-connection
check verifies the raw Berry and complex optical kernels in each displayed
frame and orbital order, without calling the reference response implementation.

`manifest.json` reserves Te for test and Te plus a fresh magnetic Fe family for
challenge and confirmation. Te uses all 24 spinor WFs and the nonsymmorphic
screw-group action. Magnetic bcc Fe uses all 18 WFs in the official
`sp3d2`/`t2g` hybrid basis, not a relabelled Te model. The latter two splits use
different proper Cartesian frames, spin orders, and disjoint momentum
coordinates. No model coefficients or noise are invented.

The kernel is the full complex interband Kubo numerator, not frequency-integrated
conductivity. Raw-model response and repaired-model response are separate score
channels. `validation.json` records independent official reexecution, R-order
invariance, Hamiltonian Hermiticity, optical Gram positivity, momentum parity, and an
independent Fourier energy check. It is not a contestant-visible fixture.

The official Te position storage is not exactly R-adjoint-Hermitian. This is
preserved, not silently corrected in the coefficient reference. Official
`data_K/data_K_R.py:Xbar` uses `hermitian=True` for `AA` in response evaluation.
The public schema states this convention; the independent finite-difference
check uses the Hermitian Fourier connection, too. Stored-AA adjoint residuals
are diagnostics, not an incorrectly imposed invariant.

The supplied Hamiltonian-only workflow has score zero by calibration, and exact
physics scores one. The eight relative-error channels have fixed numerical
tolerances; each smooth quality uses its own weak-reference error scale. The
weighted quality is affinely normalized between the weak and exact endpoints.
Material families receive equal weight, independent of orbital count or bytes.
This calibration does not hide a binary pass threshold.

Qualified results: official reexecution scores 1.000 in all five cases; the
isolated public starter scores 0.000 with return code 0 and no report errors on
all splits. At Cartesian finite-difference step `5e-5`, maximum raw Berry and
optical relative errors are respectively `2.483e-7` and `2.201e-7`, with
approximately quadratic convergence. The public smoke invariant check passes.

Sources:
- https://github.com/wannier-berri/wannier-berri/tree/e046ddc4bfe026ba1f9af2376f04babac5677425
- https://github.com/wannier-berri/WannierBerri-tutorial/tree/efe56e5b312a903bdbf06dcfc7b5fb8bb44c2afb/tutorials/5_symmetrization
- https://tutorial.wannier-berri.org/tutorials/5_symmetrization/tutorial_symmetrization-solution.html
