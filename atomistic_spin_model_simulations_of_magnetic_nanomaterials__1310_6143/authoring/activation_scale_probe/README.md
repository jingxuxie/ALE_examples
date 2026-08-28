# Activation source-scale probe

## Result: a time-limit counterexample at N=2048

The immutable submitted solver remains scientifically accurate at N=512, but
times out on the same domain-wall family at N=2048. Native Spirit plus standard
structured eigenspectrum calculation certifies the long-chain reference and
completes under the same 90-second/2-GiB computational limits.

| Case | Native reference | Immutable submission |
|---|---|---|
| N=512 | 0.552 s total reference work; sparse HTST 0.131 s | 12.621 s harness / 11.25 s compute; correct full answer |
| N=2048 | Initial 11.412 s; independent bounded rerun **10.24 s**, **90,568 KiB** peak RSS | **90 s timeout**, 98.653 s total harness elapsed including startup/termination; no output |

N=2048 submission peak sampled RSS is 135,008 KiB and peak sampled virtual size
260,868 KiB: this is **not a memory-limit failure**. Source inspection shows
repeated complete planar eigenvector calculations and later full dense tangent
Hessian solves, but no internal profile was collected. Do not attribute the
timeout conclusively to one particular routine.

At N=512, independently recomputed submitted residual is 1.64e-14 meV,
inertia is one negative/no zero modes, barrier error is 7.6e-15 meV, and reported
spectra agree with an independent full-3D banded Hessian to 4.8e-14 meV. At
N=2048, core accuracy is **unknown**, because the process produced no completed
answer. A timeout is not evidence of a wrong physical answer.

## Scientific construction and certification

The starting state is the frozen native N=40 case
`pilots/activation/private/reference/initial/initial_domain_wall_01_731101`.
Only chain length changes: the same exchange, Cartesian easy-z/hard-y
anisotropy, transverse/longitudinal field, and reduced anisotropy at the left
boundary are retained. Uniform bulk is appended; no additional random family
or physical interaction is introduced. Case JSONs are copied into this sidecar.

The localized saddle is padded with the metastable bulk, then refined/confirmed
by **unchanged native Spirit climbing GNEB** with three images. The maximum
spin correction is about 2.01e-8. Native HTST requires residual below 1e-8 meV;
GNEB convergence is set to 1e-11 to satisfy that native requirement, not to
tighten the pilot scoring tolerance. No upstream method or frozen artifact is
modified, and rotated-anisotropy tensors are avoided.

For planar spins `(sin(theta),0,cos(theta))`, the exact 3D tangent Hessian
separates into two symmetric tridiagonal blocks, using polar tangent
`(cos(theta),0,-sin(theta))` and normal tangent `(0,1,0)`. Diagonal blocks are
the projected Cartesian Hessian minus the spinwise Lagrange multiplier;
off-diagonal couplings are `-J cos(theta_i-theta_j)` and `-J`, respectively.
SciPy/LAPACK `eigh_tridiagonal` computes all 2N eigenvalues; this is standard
linear algebra, not a replacement saddle-search method. An independent
arbitrary-3D `eig_banded` construction checks the submitted N=512 result.

Native **dense HTST at N=40 and N=128** validates both complete spectra.
Native **sparse HTST at N=40,128,512,2048** independently validates Omega_0;
the largest log-Omega discrepancy is below 1.6e-8. Sparse HTST does not expose
all eigenvalues, hence the separate exact structured spectrum calculation.
The native implementation is `core/src/engine/Sparse_HTST.cpp`; the official
API is `htst.calculate(state, 0, 1, n_eigenmodes_keep=0, sparse=True)`.

At N=2048 the certified saddle residual is 6.44e-12 meV, there is exactly one
negative eigenvalue and no zero modes, and native downhill LLG from both signs
of the unstable mode reaches the two full-chain endpoint basins (maximum
endpoint error below 2.7e-9). Finite-difference Hessian-vector checks are also
recorded. `validation.json` includes every check and individual stage runtime.

The cancellation-resistant barrier is **1.47876011515 meV** at every length.
Native float32 energy getters give 1.47900390625 meV at N=2048: their total-energy
rounding bound is 0.0010783 meV, larger than the observed 0.0002438 meV difference.
This precision effect is documented, not hidden by an arbitrary tolerance.
The barrier contribution beyond site 40 is below 4e-13 meV in magnitude, but
locality is **verified after full-chain refinement**, not assumed to certify
the Hessian or connectivity. T=0.5 K gives barrier/kBT about 34.3 for classical
rare-event interpretation; no quantum correction or experimental rate is claimed.

## Interpretation limits

- These sizes are outside the frozen pilot's original N=6..40 range. This is
  a prospective scale-extension prototype, not a retrospective ranking change.
- Native timing uses a trusted localized continuation seed, whereas the old
  submission searches from endpoint inputs. It is not an equal cold-start
  global-search speed comparison. The user-authorized locality construction
  is a feasibility advantage that a future solver could also exploit.
- Three-image GNEB confirms the stationary saddle; it does not resolve a full
  long transition path. Both full-chain downhill branches are checked natively.
- No exhaustive global-lowest-barrier proof is claimed. Independent cold
  submitted search at N=512 nevertheless finds the same saddle/barrier/spectrum.
- Trusted native reference uses explicit CPU/address-space limits and external
  timeout, but is not inside the submission's bubblewrap namespace. The old
  solver uses the unchanged shared isolated harness; reported elapsed includes
  startup and cleanup, while native stage times are separately identified.
- No pilot scoring, helper, submission, frozen reference, or core source was
  changed. No new model was launched. Only this directory is owned/written.

## Files and reproduction

`result.json` aggregates results; `provenance.json` contains hashes of scripts,
artifacts, immutable submission, seed, native sources/library, and shared
harness. Source revision: `e82250d3b14411c2c2fa292d143f13e3e111ad8c`.
Submission SHA-256:
`252500c16f8aa286173b42139f0cc1686627788dcde93ad46f081b89771e4656`.

Use the existing pinned `authoring/python_runtime` on `PYTHONPATH`, set
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1`, then:

```sh
python -B reference.py --sizes 40 128 512 2048
timeout 90 python -B bounded_reference.py
python -B run_submission_probe.py --sizes 512 2048
python -B finish_report.py
```

The submission probe needs escalation outside a nested parent sandbox for
bubblewrap. It refuses to overwrite a completed output; use a separately
versioned probe directory for repeated trials. `N*/case.json`, `reference.npz`,
`validation.json`, `submission_result.json`, and `logs/` preserve the evidence.
No N=4096 case was needed once a valid N=2048 time-limit counterexample existed.
