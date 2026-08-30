# Input, objective and interface

`input/manifest.json` lists independent case directories. At replay, only one
case directory is mounted at `/input`; it contains `case.json` and `arrays.npz`.
Use `Atlas.load(directory)` from `atlas.py`. The module is importable in replay.
All needed constraints, energies, guide data, flux targets and baseline choices
are included in the received case. Do not assume filenames identify answers.

There are four scenarios, four candidates per vertex, rank two and ambient
dimension six. Grids are 8 by 8 or 9 by 8, with vertex `y*nx+x`. Candidates are
independently permuted at each vertex. Metadata holds integer budget, anchors
mapping vertex strings to candidate indices, scenario loss weights in the order
energy/overlap/dispersion/flux, positive normalizers and scenario weights,
integer target Chern numbers, and all numerical tolerances.

NPZ arrays (no pickle): `frames[S,V,C,6,2]` complex full-rank frames;
`energies[S,V,C,2]` sorted spectral multisets; `guide[S,V,2]` sorted guides;
`target_flux[S,V]` oriented plaquette flux; `costs[V,C]` integer acquisitions;
`seed_choices[V]` and `baseline_choices[V]` feasible integer atlases. Costs are
paid once per vertex, not once per scenario. Energies belong to a subspace as
an unordered multiset, not to specific columns of its arbitrary basis.

Orthonormalize each frame within its column space, `Q=F(F*F)^(-1/2)`.
For each directed +x and +y edge, including wrap edges, let `A=Q_u*Q_v`.
The edge losses are `-log(max(abs(det(A))**2,1e-30))` and the mean squared
energy difference. Each counterclockwise plaquette has ordered corners
`(x,y),(x+1,y),(x+1,y+1),(x,y+1)` modulo the grid. Its flux is the principal
argument of the determinant of the product of its four overlap matrices.
Flux discrepancy is the squared principal wrapped difference from target flux.
Vertex loss is mean squared energy difference from its guide.

Sum the four component losses over vertices/edges/plaquettes with the supplied
scenario weights to obtain `L_s`. Put `r_s=L_s/normalizer_s` and minimize
`J=max(r_s)+lambda_mean*sum(weight_s*r_s)/sum(weight_s)`.
Normalizers are frozen raw losses of the initial feasible acquisition atlas,
not fitted to submissions. The frozen baseline is deterministic feasible
best-improvement single-site descent, provided with its objective `J_base`.

Feasibility requires cost <= budget, every anchor, every selected edge
determinant magnitude >= `minimum_link`, and every flux at least `branch_margin`
from the principal-argument cut. In every scenario, `sum(flux)/(2*pi)` must
match `target_chern` within `chern_tolerance`. These are lattice Chern numbers
of the rank-two determinant bundle, not individual eigenvector phases.

Case gain is `1-J/J_base`. Family scores are mean case gain. The overall
score is the unweighted mean of family scores. Every case must be feasible
and have nonnegative gain; every family mean must be >= 0.08; overall >= 0.12.
There is no exact-answer comparison or tie-breaking requirement. Runtime,
startup, input loading and preprocessing count toward each 90-second limit.
The trusted evaluator recomputes all numbers; claimed metrics are not accepted.

Reports expose `core_score` (family-balanced gain), `worst_family_score`
(minimum family mean gain), `runtime_seconds` (sum of measured case wall times),
`resource_score` and its alias `runtime_resource_score` (fraction of executions
finishing successfully within the enforced resource envelope), and `reason`.
Gain scores are fractions, higher is better; zero is the frozen baseline.

# Physical scope

Families are gap/curvature hotspots, proximity to a band inversion, anisotropic
warping, and competing strain scenarios. Cases use lattice-regularized two-level
Dirac blocks plus a trivial occupied band and remote orbitals. Acquisition
candidates model imperfect spectral windows through subspace mixing and leakage;
one competing branch can alter topology. The same candidate index is selected
across all scenarios. These are synthetic downstream band-atlas instances, not
literal Kane-model outputs or a semiconductor parameter-fit benchmark. A nonzero
Chern class obstructs a globally smooth periodic frame; this task deliberately
asks only for local subspaces and gauge-invariant links.
