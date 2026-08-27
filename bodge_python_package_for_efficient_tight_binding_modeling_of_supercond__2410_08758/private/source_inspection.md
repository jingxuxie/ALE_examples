# Private source and shortcut audit

## Decision

Reject in Phase 1 with `no_frontier_hard_workflow_found`. Five concepts were
considered; none was selected for pilot construction. No reference was built,
no isolated agent was launched, and no empirical score is claimed. This applies
the explicit early-stop rule rather than substituting an untested task for the
requested frontier-hard candidate.

This is a judgment about the **five bounded task concepts below**, not a claim
that superconductivity research, Bodge, or every possible workflow using Bodge
is easy. An agent failure was neither observed nor inferred.

## What the paper actually contributes

The paper's central contribution is convenient, symmetry-aware construction of
real-space spin/Nambu tight-binding Hamiltonians. Its central engineering claim
is sparse construction with time and memory proportional to lattice size, with
performance comparable to Kwant. Extensibility through lattice iterators and
sparse/dense interoperability are also central. The main worked example builds
a conventional-superconductor/ferromagnet heterostructure.

The paper also demonstrates how a constructed Hamiltonian can feed LDOS,
diagonalization, free-energy, and user-written matrix-function calculations.
It distinguishes these conveniences from advanced observables that a user must
implement. It cites separate research papers for altermagnetic Josephson
transport and unconventional-superconductor-mediated impurity interactions.
Those citations are useful workflow leads, but are not an independently
validated equilibrium phase diagram or benchmark dataset in this paper.

## Official artifacts and reconstructable workflows

- `bodge/hamiltonian.py` contains the BSR skeleton, context-managed block
  population, sparse export, dense eigenproblem, spectral free energy, and
  sparse-resolvent LDOS. The pairing helpers already encode the conventional,
  triplet, and d-wave construction patterns.
- `bodge/lattice.py` exposes the site/bond/edge iterator extension points and
  explicit cubic coordinates. Reimplementing different connectivity would not
  by itself create an open-ended scientific problem.
- `misc/benchmark.py` constructs the same BdG systems with Bodge and Kwant,
  compares matrices, and records timings. It is a useful real performance
  artifact, but also supplies the direct implementation pattern and comparison
  method for a reproduction task.
- `tests/test_physics.py` contains gap existence/scaling, magnetic isotropy,
  spin-valve behavior, odd-frequency spectral features, temperature-dependent
  energy, p-wave edge states, and Josephson minigaps. These are valuable
  physical checks. They do not independently defeat the same eigensolver or
  resolvent applied to each model.
- The old development branch has connected `Hamiltonian`, `FermiMatrix`,
  Chebyshev, current, gap, and experiment scripts. In particular, `sns.py`
  sweeps expansion order, `superalter_cpr.py` constructs phase-dependent
  altermagnetic junctions, and `swave.py` performs accelerated gap iteration.
  The branch README explicitly warns that this is old, potentially incorrect
  research code rather than a supported release. That warning is not evidence
  of frontier difficulty, and its broken dependencies must not be scored as
  participant failures.
- `bodge/utils.py` on that branch already contains critical-temperature and
  gap bisection; `rkky_sp_open.py` computes orientation-dependent free energies;
  `rkky_plot.py` explicitly extracts effective interaction coefficients by
  signed sums. Exposing this workspace would expose the main proposed solution
  patterns. Removing them and asking for the same calculations would mostly
  turn the work into implementation of known algorithms.
- The s-wave feature branch and historical periodic-boundary fix were checked
  as possible incomplete/pre-fix workspaces. Neither supplied a source-grounded
  workflow that survived the shortcut audit.

The source manifest pins the release-era and inspected later commits separately;
the 2025 main-branch state is not represented as the exact October 2024 release.
The Git repository, including paper source history, is retained only under
`private/`. No participant workspace or public paper copy was created.

## Why the strongest-looking proposals were rejected

**Transport diagnosis:** Complex hopping, currents, spectral approximation,
gauge checks, and phase sweeps could make a realistic repair exercise. However,
for the bounded fixed-gap models grounded in the supplied scripts, the same
Fermi matrix and local trace contractions produce the required currents in
every proposed family. A dense control and the already-visible sparse
expansion provide a reusable implementation path. Larger systems, more phases,
or stricter tolerances would mostly increase cost rather than introduce new
scientific choices.

**Self-consistent equilibrium:** Adding branch selection, flux-winding states,
first-order transitions, and coupled transport could plausibly make a harder
research project. The bounded workflow actually reconstructed here is the
standard attractive s-wave gap iteration/temperature search, for which source
patterns already exist. The more ambitious project would require the benchmark
author to establish a new multi-family physical specification, thermodynamic
functional, validated equilibrium branches, and reference evidence not provided
by this paper. It was not selected on the assumption that such additional work
would automatically be frontier-hard.

**Impurity interaction inference:** The real code has a multi-stage simulation
and analysis pipeline, but its proposed bounded output is already a spectral
free-energy calculation followed by signed combinations or an ordinary linear
fit. Keeping the source exposes the extraction; hiding it leaves a standard
numerical exercise. Promoting nonbilinear, self-consistent impurity physics to
the core would change the scientific study rather than reproduce this paper's
central engineering claim.

## Gate audit and stopping rule

`private/candidates.json` records the contribution, real artifacts, three
plausible decision points, feedback loop, public evidence, prospective hidden
families, Pareto evaluator, shortcut, and failed gate for each concept. All
families are **proposals**, not generated cases or measured tests.

Physical heterogeneity does not establish algorithmic heterogeneity: the same
resolvent, Fermi function, gap map, or signed energy extraction remains applicable
across the proposed families. Adding tables, figures, reporting, mutations,
additional seeds, or a tighter one-hour limit would not remove these shortcuts.
These additions were therefore not made.

No package dependency failure, missing file, timeout, or undocumented convention
is being used as hardness evidence. In particular, the inspected host has
Python 3.10 while the package declares Python >=3.11; that would require an
environment fix if a pilot were selected, not a scored agent failure. The
rejection is based on task design, not the host environment.

Phases 2–5 are intentionally not entered. The final status is `rejected`, not
`reference_failed`, `moderate`, or `pilot_frontier_hard_candidate`.
