# Model and protocol v1

## Exact reduced physics

Sites are `site = 8*y + x`, with integer `x,y` in 0…7, open boundaries and lattice
spacing one. Energies and impurity strengths are in units of nearest-neighbor
hopping `t=1`. In the `(c_up, c_down†)` spin block,

    h_ij = (V_i - mu) delta_ij - t [i,j nearest neighbors]
    H = [[h, D], [D†, -h*]]
    D_ij = delta_ij Delta_i
    Delta_i = Delta0 product_a tanh(|r_i-R_a|/xi)
              exp(i sum_a atan2(y_i-Y_a, x_i-X_a))

`mu=-0.7`, `Delta0=0.55`, `xi=1.15`. This imposed onsite s-wave singlet texture
models pinned cores, not a self-consistent stable vortex solution. There is no
Peierls field, Zeeman term, magnetic impurity, screening, or gap relaxation.
The finite matrix is diagonalized exactly up to floating-point error.

The per-spin electron LDOS, not doubled spin-summed DOS, is

    rho_i(E) = sum_n |U[i,n]|² eta / (pi ((E-lambda_n)² + eta²))
             = -Im[(E+i eta-H)^(-1)_(i,i)] / pi

The sum runs over **all** 128 eigenstates; do not double-count positive/negative
states. `eta=0.065`. The allowed 41 energies are `-2.4 + 0.12*energy_index`.
No observation noise is added; responses are rounded to 12 decimal places.
Residual tolerances around `1e-9` safely exceed instrument rounding.

## Complete prior

Only the 36 interior sites (`x,y` in 1…6) may host impurities. Distinct supports
are sampled without replacement. Independently for every impurity, the sign is
equiprobable ± and the magnitude is continuous uniform on [0.55,1.6]. Strengths
are onsite scalar potentials with no spin dependence. Counts are unknown.

The three equally weighted evaluation families are:

- `dispersed`: count uniformly 4 or 5; support uniform among all interior sites.
- `crowded`: count uniformly 6 or 7; support uniform among all interior sites.
- `clustered`: count uniformly 5, 6, or 7; independently choose a 4×4 interior
  window's lower-left x,y uniformly from {1,2,3}, then sample support in that window.

For every family, independently draw vortex count uniformly from {0,1,2}, then
choose that many distinct centers uniformly from nine candidates. Center ID is
`3*row+column`, with x,y values {1.5,3.5,5.5}. All vortices co-rotate; there are
46 possible unordered configurations. The family is NOT announced. The evaluator
uses the exact `draw_scene(seed,family)` algorithm with private deterministic
seeds. Seeds, episode IDs, and family labels are absent from instrument metadata.
The public sampler is unlimited training data; no secret physics or hidden catalog.

Global pairing phase is fixed to zero, and circulation sign is canonicalized to
+1: simultaneous reversal is LDOS-equivalent here. Impurity/vortex permutations
are ignored. Rotations/reflections are NOT quotiented because query coordinates
are fixed in the laboratory frame. Do not report gauge angles or winding signs.

## Local Python API

From the participant directory, add `workspace` to `sys.path` and import `bdg`.
`scene = {"impurities":[{"site":9,"strength":0.8},...],"vortices":[0,8]}`.

- `simulate(scene, actions)` returns one LDOS value per action for an explicit scene.
- `ldos_table(scene)` returns the full 64×41 LDOS table for an explicit scene.
- `draw_scene(integer_seed, family)` returns labeled synthetic training data.
- `sectors()` returns all 46 vortex configurations.
- `hamiltonian(potential, vortices, gap=None, phase=0, winding=1)` exposes the matrix.
- `predict_potential(potential, vortices, actions, jacobian=True)` returns values
  and the exact resolvent-identity Jacobian with respect to the 36 interior
  potentials; useful for continuous relaxations of the discrete support search.
- `potential_of(scene)`, `pairing(vortices, ...)`, `resolvent_ldos(scene,actions)`
  and `uniform_actions(count=56,seed=1701)` support diagnostics.
- `validate_scene(scene,prior=True)` validates final answers. With `prior=False`
  the local simulator permits 0…36 impurities and arbitrary finite real strengths
  so normal/uniform limits and dense optimizer relaxations remain accessible.
  Vortex IDs remain constrained. `hamiltonian` accepts any real length-64 potential.

The public API has no hidden instrument state, file loader for private scenes,
or observation callback. It does not consume instrument query budget.

## JSONL session

The host writes exactly one initialization line and flushes:

    {"type":"metadata","protocol":"ldos-jsonl-v1","model":{...},"target":{...}}

`model` is exactly `input/model.json`; `target` is exactly `input/target.json`.
Only those public objects are transmitted, independent of the scene. Then:

    agent: {"type":"query","site":27,"energy_index":20}
    host:  {"type":"observation","query_index":1,"site":27,"energy_index":20,"value":0.123456789012,"remaining":55}

Choose later queries after reading observations. One action is one scalar, not
a full spectrum or batched action. Repeated queries are permitted and cost one
each. Indices must be JSON integers (not booleans/floats). Query index is 1-based.
After zero to 56 queries, send:

    {"type":"final","estimate":{"impurities":[...],"vortices":[...]}}

Final estimates must contain 4…7 unique allowed sites, strengths within the public
signed prior, and 0…2 unique vortex IDs. An early final is legal. Read no final
score from stdin; exit successfully after final. Every object has exactly the
keys documented here. NaN/Infinity, duplicate JSON keys, oversized lines (>64 KiB),
extra keys, batched queries, extra output after final, EOF before final, a 57th
query, nonzero exit, and time/resource violations fail the episode. stderr is for
diagnostics only and is bounded separately. Every output line must be flushed.

## Metrics and frozen pass

Let S be true support and T estimated support. Support F1 is `2|S∩T|/(|S|+|T|)`.
On all 64 sites, with zero for absent impurities, the relative strength error is
`||Vhat-V||_2 / ||V||_2`. Thus missed and spurious sites, wrong signs, and inaccurate
strengths all count; this is NOT error only on correctly located impurities.
Vortex accuracy is exact equality of unordered center-ID sets, including count.
Sector/count-only accuracy is reported as a diagnostic, not substituted for it.

An episode's joint success is the conjunction in `input/target.json`. The core
is mean joint success over all 12 episodes; worst-family success is the minimum
of the three family means. The overall pass is the conjunction of **all** suite
thresholds, including zero protocol failures. A diagnostic quality score is
`0.45*F1 + 0.25*max(0,1-strength_error) + 0.30*vortex_exact`; it is not the target.
On protocol failure: joint=0, F1=0, strength_error=2, vortex_exact=0, quality=0.

## Submission and local practice

Create `output/solve.py` and place any submission helpers in `output/`. The entry
belongs directly in the absolute output directory if your runner provides one.
The submission path is never the read-only participant working directory. The entry
is invoked using Python; a shell script is not needed. During evaluation the
submission directory is `/submission`, public assets are `/participant`, and
`PYTHONPATH=/participant/workspace:/participant`. Both code trees are read-only.
Only `/tmp` and `/output` are writable scratch locations, recreated every episode.
In particular, compile any acceleration into scratch rather than beside your
source. Resolve assets relative to `__file__` or `/participant`, not cwd. Set
BLAS thread counts to one before NumPy imports. No persistent cache or external
service is allowed. The `output/` submission tree and sandbox `/output` scratch
mount are different directories.

From the participant directory, using only shipped public assets:

    OPENBLAS_NUM_THREADS=1 python workspace/run_local.py --submission baseline --split calibration --case 0
    OPENBLAS_NUM_THREADS=1 python workspace/run_local.py --submission output --split train --report local_report.json

`run_local.py` runs the same metadata/query/observation/final exchange with known
public labels and reports reconstruction metrics. It starts a fresh process for
each case, applies time and memory limits, and bounds stdout/stderr. It is a
practice harness, not a security sandbox or an official evaluation; public labels
are accessible locally. `--case` is a zero-based case index; omit it to run all
six cases of the selected split. The baseline submission root contains `solve.py`,
which calls `uniform.py`. You can generate unlimited additional scenes with
`draw_scene`; local simulator calls always require explicit latent parameters.

The baseline chooses 56 uniformly random action-grid points with a fixed public
policy seed, then enumerates vortex configurations with a sparse nonlinear
potential fit. It does not use labels or adapt its measurements. The physics
tests and finite-candidate identifiability diagnostics are builder checks, not a
proof that an arbitrary submitted algorithm can attain the target in 90 seconds.
