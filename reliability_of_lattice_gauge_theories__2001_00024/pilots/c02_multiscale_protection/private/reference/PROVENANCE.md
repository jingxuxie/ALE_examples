# Provenance and anti-compression decision

Source gap: arXiv:2001.00024 finite exact-diagonalization reliability study to
arXiv:2104.07040, Eqs. (1)--(6), higher-spin/thermodynamic reliability. Spatial
inhomogeneity and calibration are motivated by the actual experiment
arXiv:2003.08945, Methods. This benchmark's calibration fixtures and finite open
chains are new, disclosed packaging; they are NOT original experimental data.

The privileged solver uses an existing quimb 1.10.0 TEBD implementation.
It does not contain a newly invented many-body algorithm or recovered author
code. References are precomputed, step/bond checked, and compared to independent
dense evolution on small systems. The large finite chains are not represented
as literally infinite systems or infinite-time results.

Can one fixed general solver handle all cases? Dense propagation cannot at
32--64 cells with local dimension 4--6. TEBD can propagate each fully specified
Hamiltonian but cannot infer the omitted coherent faults from calibration by
itself. Calibration and spatial correlated propagation are independently scored.
Both the strong-penalty and weak/inhomogeneous branches are needed. A small-ring
leakage fit is an explicit baseline to investigate, not an assumed failure.

The starting artifact supplies a correct small-cluster Hamiltonian and dense
propagator. Missing capabilities are inverse calibration and large correlated
evolution. It deliberately does not inject a fake historical bug. Reference
engine dependencies stay outside the participant tree. No public labeled
training corpus is provided.

Physical conventions and all measurement meanings are in the public protocol.
The score has no tolerance plateau: each block receives exp(-ln(10)*error/scale),
where scale is the precomputed weak baseline error with a documented minimum.
Thus a weak baseline block is approximately 0.1 and a zero-error reference is 1.

References:
- https://arxiv.org/abs/2001.00024
- https://arxiv.org/abs/2104.07040
- https://arxiv.org/abs/2003.08945
- https://quimb.readthedocs.io/en/latest/examples/ex_TEBD_evo.html
- https://github.com/jcmgray/quimb

## Independent charge-conserving reference engine

`charge_engine.py` uses the existing physics-tenpy 1.1.0 block-sparse TEBD
implementation, pinned privately. This is a second library implementation, not
new participant-visible scaffolding. Small-system agreement with dense evolution
is recorded in `charge_engine_small_validation.json`; large comparisons are
written separately in `charge_checks/` only when actually completed.

The conserved quantity is Q = sum_j (-1)^j n_j, NOT the individual Gauss laws.
Both neighboring matter lowering/raising terms change the two opposite-signed
charges equally; link errors carry no matter charge. All on-site terms commute
with Q. Thus enforcing Q=0 is exact for the specified initial state and retains
gauge-violating dynamics. Every two-site charge commutator is measured explicitly.
The library's ordinary U(1) block sparsity accelerates a proven invariant; it does
not project out the faults the benchmark asks participants to predict.

- https://tenpy.readthedocs.io/en/v1.1.0/reference/tenpy.algorithms.tebd.TEBDEngine.html
- https://tenpy.readthedocs.io/en/v1.1.0/reference/tenpy.models.model.NearestNeighborModel.html
- https://tenpy.readthedocs.io/en/v1.1.0/reference/tenpy.networks.site.Site.html
