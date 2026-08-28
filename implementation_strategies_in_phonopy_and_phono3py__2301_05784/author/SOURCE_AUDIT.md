# Source audit and boundaries

The local audit date is 2026-08-27 America/Los_Angeles (2026-08-28 UTC).
The three official repository revisions and actual imported private package
versions are recorded in `provenance.json`. Moving `main` URLs are not used as
unversioned numerical oracles.

## Concrete solution-bearing changes

| Capability | Verified official artifact |
|---|---|
| Joint constrained FC estimation | symfc v1.5.4, `7b774611f10a5930c9e760a759e304020217c087`; paper arXiv:2403.03588 |
| Three-origin cubic lattice sum | phono3py v2.9.0 introduction; v3.0.2 default; explicitly enabled C API in pinned v3.19.2 |
| Restored three-origin CLI default | `86f0d8ddef2d238b0c9e35a03e9fd518156491ab`, regression `ba33a48120d93f9b657288faff3af9d1007b7d1d`, v3.23.0 |
| Analytic Gonze–Lee derivative | phonopy `e0e7cff353bccfed8bce258ea84502347205689a`, backend `01ee047591d3dd13437b123cf053bb7ae039de40`, default `94a79bd0d420bb93bf9547c53c6a76dd2284cf1e`, v4.1.0 |
| Symmetry-preserving mesh fallback | phono3py `67d21b84609c25afc9407520cbe23b66f0c74751`, v3.20.0; phonopy `fffc8f1ae5aaba69ffa0f2e25a6b4cf332d5d949`, PR812, v4.0.0 |
| Stable degenerate heat-capacity matrix | phono3py `02f5028984f227d8ce213b5e4186e28ff015c4f5`, merge `0b5de7901b458b2b4ffaad29560836be737f527b`, PR596, 2026-08-20 |
| Collision-matrix OpenMP race | phono3py `e3421cf4661f06627be66a27ee5d3560c5e4d160`, `c6f5cab9cbdc16f3707a036f8bae3b57fcc24121`, v3.12.2 |
| Structure-factor conjugation | phonopy `1c34ae7198b868ca4a7d4efa1a0385e4a653f9be`, PR605, v2.41.2 |

The CLI r0 regression does not imply the underlying C kernel or every API call
was broken. The cubic build must verify numerical differences between explicit
on/off execution. The polar change is an accuracy/performance opportunity, not
evidence of a large published conductivity discrepancy. Generalized grids were
already described in the target paper; their private gap is the withheld official
implementation (and later integration), not a falsely claimed new invention.

## Data and adjacent applications inspected

- symfc official tests contain real displacement-force datasets for NaCl, GaN,
  Si, SiO2 and SnO2, plus stored force-constant checks.
- phono3py `example/NaCl-rd/phono3py_params_NaCl.yaml.xz` includes 100 cubic
  snapshots of 64 atoms and two harmonic snapshots of 512 atoms. MgO random
  and AlN332 fixtures provide distinct crystal families and supercells.
- phonopy NaCl, SnO2 and TiO2 force/Born-charge fixtures support anisotropic polar
  tests. `AgNO2_cell.yaml` provides a real oblique-lattice mesh witness.
- Official Wigner La2Zr2O7 inputs include cached linewidths; this offers a genuine
  population/coherence model discrepancy without new expensive DFT calculations.
- Later pypolymlp/symfc SSCHA workflows, KCl models and SrTiO3 datasets were inspected
  as alternative model-mismatch routes. A toy SSCHA force field alone is not
  evidence of real-material agreement.
- A further physical-family route is long-range multipoles plus rotational
  invariance (elphmod v0.27 and Materials Cloud 2022.111). It was not built under
  the four-concept cap; it is not being reported as empirically easy.

## Fairness and isolation

All public baselines are explicitly restricted adapters/ablations, not claimed
to be byte-for-byte historical repositories. No solution-bearing official package
is installed in the system environment visible to attempts. Private packages are
under `author/runtime*`. The requested runner is unmodified and invoked with
`--task-read-only --model ultima-alpha --effort high`, one hour maximum per attempt.
The evaluator separately mounts only the submitted files, public participant
assets, one unlabeled input and an output directory. It unshares network and PID
namespaces. The executable isolation probe verifies NumPy/SciPy availability,
private-file denial and network denial; its report is retained.

Dataset scaling, performance claims and acceptance are contingent on actual
measurements in the per-concept manifests and evaluation reports, not this audit.
