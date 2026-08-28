# Primary-source audit

Inspected August 27–28, 2026 (local authoring timezone America/Los_Angeles).
This is a source-mining record, not a claim that every suggested feature was
implemented in a pilot. Exact pilot scope and reference validation take precedence
over preliminary candidate descriptions.

## Paper, adjacent methods, and data

- The target is arXiv:1310.6143, submitted October 23, 2013. Its 25-page PDF,
  including appendices A–C, was inspected. No separate supplement was located.
  Surface anisotropy, ultrafast dynamics, exchange bias, and extended parallel
  systems motivated distinct candidate directions; they are not all pilot tasks.
- The official VAMPIRE repository was cloned with history and branches. The
  checked-out main revision is `525bc27e`; its documentation says version 7.0.
  This is distinct from GitHub's separately maintained release list: the API
  snapshot still lists v6.0 as the latest published GitHub release. Neither is
  silently treated as the quantum implementation used for reference generation.
- The 2025 adjacent quantum-thermostat paper arXiv:2508.11315 and its January 2026
  author data archive were inspected. `../ASD_Zenodo.zip` is the archive from
  Zenodo record 18391022, verified against MD5
  `52095bc41d9bd8b108834690f67e3e81`. `../archive_inventory.txt` records notebooks
  and Ni/Gd/SpiDy/VAMPIRE datasets. These measured/author curves were not secretly
  substituted for the newly generated transient cases in the quantum pilot.
  The code cells of `Fig2.ipynb` and `Fig8and9.ipynb` were also inspected: they
  load classical/quantum/no-zero-point Ni data, Lorentzian DOS and experimental
  DOS inputs, and independent SpiDy/SpiCy transient and steady-state outputs.
  Plot-specific temperature rescalings are visible in the former notebook;
  the pilot does not claim to reproduce or infer these experimental fits.
- Spirit's 2019 paper arXiv:1901.11350 and official code supply GNEB, minimum-mode
  following and HTST. The pinned native build is v2.2.0,
  `e82250d3b14411c2c2fa292d143f13e3e111ad8c` (March 17, 2023). The published v2.1.0
  release of December 21, 2020 explicitly introduced sparse HTST without dipole
  interactions, a relevant privileged solution for long-chain activation.
- The constrained-Monte-Carlo paper arXiv:1006.3507 predates the review. Its gap is
  an official participant-hidden implementation, not a falsely claimed later
  publication. Official workshop anisotropy inputs informed the thermal cases.
- The hierarchical-dipole archive at Zenodo record 3669966 and official dipolar
  branches were inspected but not built as an additional concept.

## Issues, pull requests, and releases

The adjacent JSON files preserve the public GitHub API responses: the first 100
all-state VAMPIRE pull requests and issues, the first 100 all-state Spirit issues
(which include pull requests), and the first ten releases of both projects.
This is a bounded audit, not an exhaustive review of every issue ever filed.

- VAMPIRE PR #99, merged August 22, 2023, is the actual parallel spin-accumulation
  repair `ed2f0719f08dc52bec35a93568503dfe18a19e13`: an erroneous MPI synchronization
  caused spin-torque overestimation. PR #98 is closed without a merge. The fixed
  commit is evidence for direction A; the transport pilot instead tests the
  distinct material/sublattice sequence documented in its private provenance.
- PR #121 merged into `quantum-thermostat` on February 7, 2025. PR #124 describes
  faster, lower-memory noise generation and an MPI implementation, but is closed
  **without** a merge. Its presence is not evidence that the pinned reference
  branch builds unchanged. The quantum pilot explicitly documents the upstream
  material-argument integration problem and validates its equation-level port.
- Open issue #109 asks how to apply spin-polarized current; #80 reports a finite
  transition temperature in a nominally isotropic two-dimensional model. These
  are application/diagnostic leads, not independently verified post-fix oracles.
- Issue #140, opened April 4, 2026, reports version-7 tests/compiler problems.
  Clerical build failures are not used as a task-hardness criterion.
- Open PRs #119 (multilayer two-temperature model), #102 (longitudinal spin
  fluctuations), and #137 (spin-lattice changes) were examined as adjacent
  integration leads. They did not authorize a fifth concept.
- Spirit's release metadata and issue list were checked for GNEB/HTST, anisotropy
  and performance limitations. The discovered rotated-anisotropy Hessian issue
  in the pinned source is excluded from the native-validated activation cases,
  rather than used to manufacture a participant failure.

## Source locators

- https://arxiv.org/abs/1310.6143
- https://github.com/richard-evans/vampire
- https://github.com/richard-evans/vampire/pull/99
- https://github.com/richard-evans/vampire/pull/121
- https://github.com/richard-evans/vampire/pull/124
- https://github.com/richard-evans/vampire/issues/80
- https://github.com/richard-evans/vampire/issues/109
- https://github.com/richard-evans/vampire/issues/140
- https://github.com/richard-evans/vampire/releases
- https://arxiv.org/abs/2508.11315
- https://zenodo.org/records/18391022
- https://zenodo.org/records/3669966
- https://github.com/spirit-code/spirit
- https://github.com/spirit-code/spirit/releases/tag/v2.1.0
- https://arxiv.org/abs/1901.11350
- https://arxiv.org/abs/1006.3507
- https://vampire.york.ac.uk/resources/workshop2017_day2.pdf
