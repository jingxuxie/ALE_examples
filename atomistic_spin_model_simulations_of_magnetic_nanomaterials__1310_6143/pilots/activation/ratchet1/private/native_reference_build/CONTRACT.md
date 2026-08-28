# Ratchet1 reference handoff contract

All paths are relative to `pilots/activation/ratchet1/` unless stated otherwise.
Main owns participant, evaluator, numerics, isolation and root-private metadata.
This builder writes only `private/native_reference_build/`, `private/reference/`, and
`private/challenge_pool/`; public input-only copies live in the authoring sidecar.

## Cases and solutions

The physical input schema is unchanged: `schema_version: 1`, `case_id`, `family`,
`seed`, `n_spins`, `boundary: "open"`, `exchange_meV` (N-1),
`anisotropy_meV` (N by3by3 symmetric Cartesian tensors), `field_meV` (3),
`mu_s_muB`, `temperature_K: 0.5`, `time_limit_seconds: 90.0`,
`minimum_a` and `minimum_b` (N by3 unit spins). Memory allowance is2GiB.

The Hamiltonian remains
`E = -sum J_i s_i.s_(i+1) -sum s_i^T Q_i s_i -sum h.s_i`, in total meV.
The output JSON contains exactly `saddle`, `barrier_meV`,
`eigenvalues_min_meV`, `eigenvalues_saddle_meV`, and `log_omega0`.
Both full spectra have2N sorted eigenvalues, including the unstable eigenvalue.
`log_omega0 = 0.5*(sum(log(lambda_A/1meV)) -
sum(log(positive_lambda_saddle/1meV)))`; it is not the dynamical attempt rate.

Each case directory contains `case.json`, `solution.json` (plain JSON lists),
and `validation.json`. The latter includes `validated: true`,
`reference_runtime_seconds`, native sparse HTST, residual/inertia/FD checks,
two native basin descents, compared mechanisms and provenance. Long cases have
a same-parameter N128 native dense-HTST cross-check in the build directory.

Initial manifest: `private/reference/initial/manifest.json` (six cases).
Challenge manifest: `private/challenge_pool/challenge/manifest.json` (three new seeds).
Manifest `sha256` keys are relative to the ratchet1 root, matching the original
pilot convention; `cases` also gives explicit case/solution/validation paths.
The manifest is incrementally published during generation; check the case count.

Initial families/counts are boundary_localized N1536/2048,
soft_interface N2048/2304, and coherent_control N8/12. Challenge uses the same
families at N1792/2176/11, with a separate fixed seed stream. Each seed changes
exchange, easy anisotropy and field independently; boundary softening and
interface exchange modulation also vary. This is not merely energy rescaling
or lengthening the original frozen cases.

Public examples: `authoring/activation_scale_probe/public_inputs/small.json`
and `long.json`, N8 and N1536, with `family: "unlabeled"`, `seed: 0` and no
solutions. Their physical parameters do not overlap ratchet1 held-out cases.

## Native certification and limitations

Pinned private Spirit revision: `e82250d3b14411c2c2fa292d143f13e3e111ad8c`.
No upstream implementation is modified. Native LLG prepares perturbed endpoints;
native climbing GNEB refines a trusted-family continuation seed. Exact Cartesian
planar tangent Hessians separate into two tridiagonal blocks, whose full spectra
are computed independently with LAPACK. Native sparse HTST checks Omega0 on
every long case, and dense HTST checks full spectra on small matching cases.
Both unstable-mode downhill directions must reach the distinct supplied minima.

Both left and right boundary mechanisms are natively certified and compared
for every long case, including close barriers. The lower certified barrier is
stored. Short coherent controls additionally run cold21-image native GNEB from
left/right moving-wall initial paths. This is the lowest of tested mechanisms,
not an exhaustive global-minimum proof. No rotated-anisotropy HTST is claimed.

Reference timing is honest **warm** authoring work, including preparation,
small dense cross-check and competing-mechanism checks. Cold small-path timings
are separate in validation; no long-chain cold native timing is claimed.
No physical residual/scoring tolerance is tightened. Float32 native energy
getter cancellation is checked using its total-energy rounding bound.

## Reproduction

Set `PYTHONPATH=authoring/python_runtime`, `OPENBLAS_NUM_THREADS=1`,
`OMP_NUM_THREADS=1` and `PYTHONDONTWRITEBYTECODE=1`. Then use
`/usr/bin/python3 -B private/native_reference_build/build.py --split initial`
or `--split challenge`. The process imposes a2GiB address-space limit; each
complete per-case native reference including mechanism checks must take<90s.
Logs, stage outputs, source hashes and manifest hashes remain in this directory.
No fresh agent is launched and no old pilot artifact is modified.

The finished build directory was moved under `private/` after all build jobs
exited. Historical logs retain the original absolute launch paths; the entry
point and artifact references now use the private location. Relocation
provenance preserves the exact generator hash used for the original builds
alongside the path-corrected rebuild script hash. Main chooses/copies its own
public examples; the input-only sidecar copies are optional, not canonical.
