# Source inspection

Inspected on August 27, 2026. All source material remains private. There is no
participant directory and the paper was not exposed to a participant.

## Primary sources and local artifacts

- Original paper: https://arxiv.org/abs/1411.0660; archived as `sources/paper.pdf`.
- Original source archive: https://arxiv.org/src/1411.0660; archived as
  `sources/source.tar` and extracted locally. The archive contains `mbl.tex`,
  `mbl.bbl`, and eight figure PDFs. It contains no tabular disorder realizations,
  eigenpairs, raw measurement files, simulation code, or analysis scripts.
- Author publication list: https://dluitz.github.io/publications/; inspected for
  an associated data/code release. Its original-paper entry does not link raw
  data. This is not a claim that no such data exists anywhere.
- Later same-author implementation: https://bitbucket.org/dluitz/sinvert_mbl/.
  Repository metadata is saved as `sources/repository.json`, the source archive
  as `sources/sinvert_mbl.tar.gz`, and commit history as `sources/commits.json`.
  The downloaded revision is `706838f3e656`, dated September 17, 2019.
- The later code accompanies *Shift-invert diagonalization of large many-body
  localizing spin chains*, https://arxiv.org/abs/1803.05395 and
  https://scipost.org/SciPostPhys.5.5.045/pdf. It is a 2018 pedagogical release,
  not an authenticated snapshot of the 2014 paper's full production pipeline.
- The unmodified extracted repository is
  `sources/dluitz-sinvert_mbl-706838f3e656/`. Its original GPL license and notices
  are retained. No upstream code was redistributed into a participant task.
- Standard solver documentation consulted:
  https://docs.scipy.org/doc/scipy-1.8.0/reference/generated/scipy.sparse.linalg.eigsh.html
  and
  https://docs.scipy.org/doc/scipy-1.8.0/reference/generated/scipy.optimize.least_squares.html.

## Central workflow, rather than an abstract-inspired proxy

The workflow is fixed-magnetization basis construction, sparse Hamiltonian
assembly, extremal eigenvalue estimation, realization-specific energy targeting,
interior eigenpair extraction, eigenstate observables, disorder-level aggregation,
and finite-size inference. The quantities must agree scientifically; successful
eigenvalue extraction alone does not reproduce the paper's central claim.

The important source locations in `sources/mbl.tex` are:

- Lines 151 onward: level statistics and nearby-wavefunction KL divergence.
- Lines 172 onward: entanglement and subsystem magnetization fluctuations.
- Lines 184 onward: participation entropies and the distinction between
  real-space area laws and localization in configuration space.
- Lines 200 onward: spectral transformation, extremal energies, selected
  eigenstates, and disorder sampling. The production calculation reaches 22
  spins; the computational work is not equivalent to a few small matrices.
- Lines 216 onward: independent units for uncertainty are disorder realizations,
  not correlated eigenvectors from one realization.
- Lines 364 onward: finite-size collapse, cubic approximations, fit-window and
  minimum-size sensitivity, and bootstrap uncertainty.
- Lines 419 onward: dynamical spin fraction.

These are source locators, not a copied participant-facing implementation manual.

## What the available code does and does not provide

`src/Basis.h` enumerates bit-coded states and MPI ownership ranges.
`src/Hamiltonian.h` assembles diagonal and spin-exchange entries.
`src/Operator.h` applies local magnetization.
`src/sinvert.cc` already connects the model to PETSc/SLEPc, estimates spectral
extrema, targets the spectrum center, and exposes wavefunctions.
`src/conf/` and `src/CMakeLists.txt` provide the build setup.

The repository describes itself as a basic demonstration. It is not a complete
archived experiment workspace: no ensemble dataset, uncertainty pipeline,
finite-size-fitting program, regression-test suite, or failure reproducer was
found. The metadata says issues are disabled. Inspected history includes
Matrix Market output and wavefunction-access additions, but does not furnish a
scientific pre-fix regression suitable for a research-repair task.

PETSc/SLEPc Python bindings and matplotlib are absent in the inspected local
Python environment; NumPy, SciPy, pandas, Pillow, h5py, and numba are present.
This is an environment observation, not a hardness claim or a reason to score an
agent as failing. A pilot would need its dependencies packaged or validated.

## Where genuine research effort lies

The production workflow combines expensive interior eigenpairs at large Hilbert
dimension, extensive disorder sampling, and careful interpretation of finite-size
evidence. Its difficult scientific conclusions cannot be certified by a
single-realization toy calculation. Conversely, bounded numerical versions can
be addressed with well-established solver calls and observable reductions.
The screening therefore separates computational feasibility from a claim of
frontier-agent hardness.
