# Private generation-2 ratchet

This sidecar writes only below `concept_2/adversary/ratchet_1`. The preserved
generation-1 algorithms/design/score, participant, evaluator, and generation-1
participant/evaluator archives are not modified. No fresh agents were launched.

## Proposed handoff

`proposal/freeze.json` identifies the selected public `device.json` / `target.npz`
and the separate private witness, with SHA-256 hashes. Adoption by the parent is
required: this sidecar does not install a generation-2 participant or evaluator.
The proposed acceptance thresholds remain **core >= 0.96**, **worst >= 0.94**,
with the unchanged official checker and 120-second verification limit.

## Physical sweep

The 12-case factorial uses the same 12x12 lattice, 64 candidate sites, 24 normal
sites, eight probes, and three operating conditions. Broadening is 0.004, 0.008,
0.02, or 0.04; pin potential is 1.65, 3.2, or 6. Additional controls are the
unchanged generation-1 problem and 14x14 / 16x16 versions of the physical cavity.
The final candidate deliberately does not increase lattice or design dimension.

Every non-control witness is a deterministic open U-shaped inclusion cavity,
not a random fingerprint selected after seeing optimizer failures. It has a
continuous superconducting complement. The same witness is reused across the
12-case parameter factorial, separating potential/linewidth effects from
pattern identity. Its recipe is private in each case's `metadata.json`.

The public spectrum is uniform on [-0.3, 0.3], with energy step at most eta/2,
at least four samples across a Lorentzian FWHM. This near-zero spectral window
is identical for the full factorial. Before fitting, a full [-0.9,0.9] pilot was
verified and then uniformly narrowed for the initial sidecar runtime budget.
No energy point was selected from the particular witness eigenvalues. The
candidate diagnostics additionally rescore on 2x and 4x finer uniform grids.
The model retains open boundaries, the prescribed chiral gap, finite onsite
inclusions, and all original operating conditions. It is the supplied finite
BdG surrogate, not a self-consistent SuperConga calculation.

## Champion fidelity and portfolio

The source is the fresh generation-1 agent's construction/research algorithm,
captured before it cleaned scratch (provenance provided by the parent). Its
final submitted artifact contains only `design.json`; the preserved algorithm
is distinct from that artifact. This ratchet reruns the algorithm from blind
starts against every new public target, not merely the old static layout.

`adapter.py` executes the original frozen source with only the substitutions
listed in `adaptations.json`: dynamic candidate/budget counts, density-based
initialization, explicit ASSETS/OUTPUT paths, and shape-dependent diagnostics.
The analytic resolvent Jacobian, bounded `least_squares`, original tolerances,
top-budget projection, and original smoothing/CDF/binary continuation schedules
are retained. `ASSETS` can override the case assets directory.

All cases start with three direct runs (seeds 0, 17, 71), each capped at 200
function evaluations. Finalists receive original continuation schedules, each
stage capped at 200; selected finalists also receive three more independent
direct starts (101, 211, 307), each capped at 400. Early solver convergence is
recorded, not counted as exhausting the cap. Each stage preserves the relaxed
array, projected pattern, independent score, validity, actual evaluations,
wall runtime, and process CPU runtime. All numerical workers use one BLAS thread.

`summary.json` summarizes completed runs. `batch_*.json` contains elapsed batch
wall times; summing per-run times is aggregate optimizer time, not sidecar wall
time. `cases/*/runs/*/stage_*.json` gives unclipped RMSE even when the public
score saturates at zero. `result.json` appears only after all stages of that
run finish. Logs and partial stage records remain available for running jobs.

## Independent checks and interpretation

Every witness passes the official fabrication validator and independently
constructed Hamiltonian/LDOS checker. Verification also compares matrix entries,
Hermiticity, particle-hole eigenvalue pairing, direct complex-resolvent LDOS,
adapted forward responses, and finite-difference checks of both the plain and
transformed analytic Jacobians. Selected cases additionally execute the original
`evaluate.py` unchanged with its ROOT redirected to a private frozen mirror.
The ordinary participant/evaluator paths remain untouched.

Diagnostics report subgap eigenvalue spacings, electron-hole mixing and cavity
weights, observed LDOS peaks, gap-off differences, Jacobian condition numbers,
and an oracle line profile. Oracle witness-local recovery is explicitly marked
and excluded from blind portfolio success counts. It demonstrates that a valid
solution remains accessible locally, not that a blind search can find it.

The failure clusters are:

1. **Narrow linewidth:** the weak-potential cavity is recoverable at larger eta
   but direct starts fail at eta=0.004, despite resolved sampling and checked
   derivatives. Extended CDF continuation DOES recover eta=0.004 at V=1.65;
   linewidth alone is therefore not the selected ratchet mechanism.
2. **Strong inclusions:** increased potential creates poor relaxed basins and
   large rounding losses, even at eta=0.04. Continuation and exact count
   penalties are tested, and failures persist in fabrication-valid projections.
3. **Geometry scaling:** the larger cavities are controls, not the selection
   criterion. Candidate hardness is not based on a hardcoded count or path.

These are measured champion failures, not a proof of hardness or a claim that
the next fresh one-hour solver will fail. The parent should launch that attempt
only after adopting the proposed public files and freezing the new generation.

## Reproduction

From the task root, with NumPy and SciPy installed:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 concept_2/adversary/ratchet_1/sweep.py generate --workers 15
PYTHONDONTWRITEBYTECODE=1 python3 concept_2/adversary/ratchet_1/sweep.py run --workers 30
PYTHONDONTWRITEBYTECODE=1 python3 concept_2/adversary/ratchet_1/sweep.py run --cases u12_eta0.02_v6 --modes smooth cdf binary --seeds 10 --nfev 200 --workers 3
PYTHONDONTWRITEBYTECODE=1 python3 concept_2/adversary/ratchet_1/sweep.py run --cases u12_eta0.02_v6 --modes direct --seeds 101 211 307 --nfev 400 --workers 3
PYTHONDONTWRITEBYTECODE=1 python3 concept_2/adversary/ratchet_1/analyze.py u12_eta0.02_v6 --freeze
```

Existing completed run directories are resumed by skipping them. For a wholly
independent timing replication, use a new copy of the sidecar directory rather
than overwriting this evidence packet. The archive hash snapshot is recorded
after the parent created those archives and checked again before proposal freeze.
