# Source-scale search audit: completed

## Finding

Two Cartesian same-Hamiltonian regimes support an honest scale extension:
boundary-localized domain-wall nucleation and an x-easy/z-easy exchange-spring
interface followed by long uniform bulk. This is **not persistent hardness**:
standard structured linear algebra, sufficiently resolved localized paths, and
size-appropriate downhill iteration budgets solve both N2048 prototypes cold
in under 20 seconds. No nonplanar extension or model launch was needed.

| Diagnostic at N2048 | Boundary | Soft interface |
|---|---:|---:|
| Native warm reference, including minimum preparation where needed | 11.412 s; separately bounded rerun 10.24 s | 10.314 s |
| Old 45-image moving-wall branches, both directions | return without any eigensolve | return without any eigensolve |
| Structured eigensolver only, original uniform-first search | exceeds 90 s | exceeds 90 s |
| Structured 97-image moving-wall search, 8192 downhill iterations | 17.630 s | 19.832 s |
| Recovered barrier error | 2.65e-12 meV | 9.80e-13 meV |
| Recovered full-spectrum maximum error | 3.85e-12 meV | 2.20e-11 meV |

The prior actual immutable isolated submission times out at N2048 and succeeds
at N512. The private structured diagnostic is a separate profiling experiment,
not another isolated submission result or a native saddle reference.

## Independent bottlenecks and empirical compression

1. **Path localization:** the unchanged old `initial_path` and `string_search`
   with 45 images genuinely return no candidate on both moving-wall branches
   before any eigenvector-following call. At N2048 the boundary first sampled
   interior image is already below A; interface paths can also lose their
   interior maximum during redistribution. An observer stops other paths only
   when eigenvector following would begin. These endpoint exits are not imposed
   by that observer. At 97 images, following becomes reachable.
2. **High-index coherent starts and curvature cost:** replacing all-eigenvector
   steps by a tridiagonal solve plus selected-mode corrections still exhausts
   90 seconds on uniform-first searches. The initial high-index regions require
   as many as 383/394 corrected modes. No dense fallback was invoked. This does
   not prove every possible banded implementation would fail; it measures this
   algebraically equivalent replacement with otherwise unchanged search logic.
3. **Connectivity propagation:** the 97-image boundary search finds the native
   saddle with residual 2.89e-15 meV and exactly one unstable mode, but the old
   1600-step L-BFGS cap stops a propagating wall with residual 0.433 meV. Its
   connectivity rejection is a false negative, not an incorrect saddle. With
   8192 allowed iterations, the descents finish in 5155/5274 iterations for the
   two families, matching both endpoint basins. No residual tolerance changes.

Thus the successful diagnostic changes path selection/resolution and relaxation
budgets as well as the eigenkernel. It skips the unproductive coherent-first
branch for these localized regimes. The three effects should not be collapsed
into either a claim of intrinsic new difficulty or a claim of only dense cost.

The structured step uses `-H^-1 g` plus exact selected-mode corrections for the
old eigenvalue clipping and unstable-direction convention. Eight checks at N40
and N128 compare with complete eigendecompositions: maximum relative step
error 6.71e-9 (the worst case has a nearly singular random Hessian). These are
algorithm checks, not physical oracle tolerances.

The two cold boundary-direction candidates have barriers 1.47876011515 and
1.49864936059 meV. The smaller matches the independent native left-boundary
reference. This is evidence about a close competing right-boundary mechanism,
not a proof that no other saddle exists.

## Native evidence and limitations

`interface/N128`, `interface/N512`, and `interface/N2048` contain native climbing
GNEB, sparse HTST, full tangent spectra, finite differences and both native
downhill descents. The small same-family N128 case also compares complete native
dense HTST spectra. At N2048 the interface residual is 3.71e-11 meV, the first
two tangent eigenvalues are -0.132514 and 0.496420 meV, log-Omega discrepancy is
1.47e-8, and both downhill endpoint errors are below 3.32e-9. There are no zero
modes in either tested regime. Cartesian anisotropies avoid the pinned native
rotated-tensor Hessian defect; no native rotated-HTST claim is made.

The native reference is **warm continuation** from a trusted localized frozen
saddle, not a cold global path search. Full-chain refinement and full-chain
descents certify the result after padding, rather than assuming locality.
Native float32 energy getter discrepancies are checked against the total-energy
rounding bound; the independently accumulated local energy difference retains
double precision. T=0.5 K gives barrier/kBT about 34.3 and 21.2 for the two
prototypes. No experimental-rate or quantum-tunneling assertion is intended.

Spirit revision: `e82250d3b14411c2c2fa292d143f13e3e111ad8c`.
The native APIs are `simulation.start(... METHOD_GNEB, SOLVER_LBFGS_OSO)`,
`htst.calculate(..., sparse=True)`, and downhill `METHOD_LLG` with
`SOLVER_LBFGS_OSO`. Implementations are `core/src/engine/Method_GNEB.cpp`,
`Sparse_HTST.cpp`, `HTST.cpp`, and `Hamiltonian_Heisenberg.cpp` in the unchanged
private Spirit checkout. `../reference.py` contains the reference wrapper.

`heldout/` contains six **provisional scouting cases**, seeds 826801--826806,
not the later ratchet1 cases. Each has an N128 native dense cross-check. They
must not be silently relabeled as fresh ratchet confirmation data.

## Reproduction and artifacts

Use `/usr/bin/python3 -B`, pinned `authoring/python_runtime` on `PYTHONPATH`,
and `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1`.

```sh
python -B interface_reference.py
python -B path_audit.py ../N512 ../N2048 interface/N2048
python -B structured_diagnostic.py --validate ../N2048
python -B structured_diagnostic.py interface/N2048
python -B structured_diagnostic.py ../N2048 --images 97 --directions 1 -1
python -B structured_diagnostic.py ../N2048 --images 97 --directions 1 -1 --relax-iterations 8192
python -B structured_diagnostic.py interface/N2048 --images 97 --directions 1 -1 --relax-iterations 8192
```

All authored/generated changes for this follow-up are confined here:
`interface_reference.py`, `path_audit.py`, `structured_diagnostic.py`,
`heldout_references.py`, `finish_sidecar.py`, this document, the byte-identical
private `old_solver.py` snapshot, `interface/`, `path_audits/`,
`structured_profiles/`, `structured_step_validation.json`, `heldout/`, `logs/`,
`result.json`, and `provenance.json`. Initial pilot files, original submission,
evaluator and upstream source remain untouched.
