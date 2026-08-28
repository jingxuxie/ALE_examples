# ALPS statistics / DMFT / continuation research sidecar

Inspected 2026-08-27. Research only: no pilot, build, simulation, or participant run; no duplicate ALPS clone. GitHub REST commit metadata and raw source were downloaded to /tmp after approved network escalation. Findings below are static-source findings, not locally reproduced numerical results.

## Selection map and provenance limits

- A is the proposed c01_stats reference. It has an actual upstream joint-ratio jackknife implementation, but no ready-made signed, correlated, unequal-length replica fixture was located.
- B+C+D form a strong c02 multicomponent DMFT historical-fault candidate. C and D include upstream executable numerical regression tests; B does not include its downstream sign-linearity test.
- F supports c04 matrix continuation plus Dyson. This is a later author-group followup, not a fix merged into ALPS 2.0.
- E is a separate Maxent covariance candidate; G and H are narrower reserves.
- The c03 MPS lane was not investigated by this sidecar.
- ALPS fixes below concern later repository revisions. This investigation does not establish that each fault was already present in the released 2011 ALPS 2.0 tree.

## A — Signed correlated nonlinear Monte Carlo statistics

Starting artifact: ALPSCore v2.3.2, commit fccd5403b08c4e5c450229714d28be5ca4a07229, with the existing test data in alea/test/dataset.hpp and the VAR(1) uncertainty-propagation tutorial. A signed application needs aligned numerator/sign streams; a dataset generator would be new task material, not an upstream signed reference fixture.

Privileged solution artifact: alea/test/transform.cpp already defines transformer_ratio and TEST(twogauss, ratio). It accumulates both correlated inputs together in batch_acc<double>(2), finalizes once, then invokes transform(jackknife_prop(), transformer_ratio, result). Use that real implementation for the signed numerator/sign ratio, rather than independently implementing a supposedly equivalent estimator. tutorials/alea/uncertainty_prop/main.cpp supplies autocorr_acc, batch_acc, a seeded VAR(1) process with coefficient 0.97, analytic mean/autocorrelation checks, and nonlinear propagation. Its inverse transform is the inverse of a mean, not an average of pointwise inverses.

Central scientific outcome: a sign-reweighted observable and uncertainty retaining numerator/denominator cross-correlation and Markov-chain autocorrelation; distinguish statistical disagreement between replicas from apparent disagreements caused by underestimated errors.

Independent bottlenecks: (1) correlated sampling and batch-size/error convergence; (2) nonlinear ratio propagation preserving common numerator/sign batches. Unequal-replica pooling is not established by the ratio test and must not be invented as an extra reference contract. Start with per-replica outputs or explicitly source the chosen pooling operation.

Feasibility: actual C++ library and upstream tests exist. ALEA's CMakeLists requests Boost, Eigen, HDF5, alps-utilities, and alps-hdf5; it is not a standalone header-only oracle. MPI is unnecessary for the serial ratio example. No build was attempted. Do not treat mc/test/signed_obs.cpp as a signed statistical benchmark: its two measurements are both constant 1.0. Do not use open issue #657 as a proven MPI bug/fix pair: its reproducer does not show an MPI reduction.

References:
- https://arxiv.org/abs/1811.08331
- https://api.github.com/repos/ALPSCore/ALPSCore/git/ref/tags/v2.3.2
- https://github.com/ALPSCore/ALPSCore/blob/fccd5403b08c4e5c450229714d28be5ca4a07229/alea/test/transform.cpp
- https://github.com/ALPSCore/ALPSCore/blob/fccd5403b08c4e5c450229714d28be5ca4a07229/tutorials/alea/uncertainty_prop/main.cpp
- https://github.com/ALPSCore/ALPSCore/blob/master/mc/test/signed_obs.cpp
- https://github.com/ALPSCore/ALPSCore/issues/657

## B — CT-HYB Legendre sign consistency

Starting artifact: ALPS commit 73b3310067a2a332bab1a4da871874f3cf71d3a8; applications/dmft/qmc/hybridization/hybmatrix.cpp.

Privileged solution artifact: commit 272d6e3531c2b0d2a60f3e53b0898b74b72aa698, same file, hybmatrix::measure_Gl. Removes the configuration sign from M_ji because bubble_sign already contains it. PR #99 merged July 22, 2026, as 20ba7ff3160fade5603fa5965e11efa7bda43e10.

Central outcome: consistent sign-weighted Gl/Fl versus G/F estimators; pre-fix Legendre contributions lose the sign through its square.

Independent bottlenecks: (1) configuration-sign weighting; (2) the separate fermionic imaginary-time-wrap sign and Legendre representation consistency. Their validation should not rely solely on a sign-free run.

Feasibility: deterministic sign reversal on the same hybridization matrix provides a cheap production-code invariant. Important limitation: the PR explicitly says no runtime reproducer or signful reference dataset is included; its downstream test scaffolding was not ported. Do not advertise that test as present upstream. Stronger as a component of B+C+D than alone.

References:
- https://github.com/ALPSim/ALPS/commit/272d6e3531c2b0d2a60f3e53b0898b74b72aa698
- https://github.com/ALPSim/ALPS/pull/99

## C — Multiband antiferromagnetic DMFT self-consistency

Starting artifact: parent 18d8474e9150a5d8a4cdccf32c538471dc9f7b17, applications/dmft/qmc/hilberttransformer.C. For a combined historical baseline, B's 73b3310067a2a332bab1a4da871874f3cf71d3a8 precedes this fix as well.

Privileged solution artifact: commit 2fa76e234a64cefa0ccb00a7b82b0d85a2f3023e; production hilberttransformer.C plus applications/dmft/qmc/dmft_hilberttransformer_afm_multiband_numeric.C and its CMake target. The former loop skipped later flavor pairs; the fix traverses every pair.

Central outcome: both orbital bands receive the AFM bath update; identical-band inputs retain pair symmetry instead of silently freezing the second band.

Independent bottlenecks: (1) flavor-pair indexing in the AFM branch; (2) constructing/reaching the multiband DOS-file path and validating its numerical Hilbert transform. The stock single-band case cannot expose the defect.

Feasibility: especially strong executable reference. The source test uses FLAVORS=4, ANTIFERROMAGNET=1, an 11-point identical two-band DOS, and a pair-symmetry check. The commit reports approximately 1.8 pre-fix asymmetry, not a measurement reproduced here. The test links dmft_qmc_impl under LAPACK_FOUND. Multiband reachability is through DOSBandstructure; do not substitute lattice bandstructures that reject this flavor count.

Reference: https://github.com/ALPSim/ALPS/commit/2fa76e234a64cefa0ccb00a7b82b0d85a2f3023e

## D — Off-diagonal Fourier transform and high-frequency tails

Starting artifact: parent 73b3310067a2a332bab1a4da871874f3cf71d3a8, applications/dmft/qmc/fouriertransform.C.

Privileged solution artifact: commit e2e9e16e18f3e54855e438274d463f5c046d9651; production fouriertransform.C plus applications/dmft/qmc/dmft_fouriertransform_offdiag_numeric.C and its CMake target. A guard checked the truthiness of c3 instead of c3==0, zeroing a channel with c1=c2=0 but nonzero c3.

Central outcome: retain off-diagonal imaginary-time Green-function structure carried by its high-frequency moments.

Independent bottlenecks: (1) branch selection for a nonzero third tail coefficient; (2) numerical Fourier/tail-subtraction convention and endpoint checks. Use the actual numerical source test to determine expected conventions.

Feasibility: deterministic upstream executable reference, no impurity Monte Carlo sampling needed. Combine with C for an especially source-grounded c02 pilot; keep B's missing test-scaffolding limitation explicit.

Reference: https://github.com/ALPSim/ALPS/commit/e2e9e16e18f3e54855e438274d463f5c046d9651

## E — Maxent covariance activation and whitening

Starting artifact: CQMP/Maxent issue #39 describes COVARIANCE_MATRIX being ignored because the parameter was not defined. A separate exact pre-fix revision is e149f808d6096ebc94d61d70ae294bdffaf46aee, before the sigma correction.

Privileged solution artifacts: ee0f21274416d44367ca5a97a616d2cf94cdcb68 fixes the covariance parameter definition; 673cb34fdfa05209d8b420f4efbc3ea1a6cc2b47 fixes src/maxent_params.cpp to use sqrt(abs(eigenvalue))/NORM for sigma rather than abs(eigenvalue)/NORM, also changing the cutoff. Followup affb036b7a9526a1ac4f916c87038d2d31772a0f repairs covariance tests. Pin the linked commits rather than silently mixing release assumptions.

Central outcome: continuation uses the intended correlated likelihood instead of ignoring the covariance file or mistaking variance for standard deviation.

Independent bottlenecks: (1) enabling and reading the covariance input; (2) eigenspace whitening and variance-versus-standard-deviation normalization. A diagonal-covariance versus error-vector equivalence check is available in upstream history, commit 7cf8cc38322916bea13ebdc76f4bf500b330e007.

Feasibility: real application and covariance test history exist, but C++/ALPSCore dependencies are heavier than MiniPole. This is a stronger historical multi-fix continuation candidate than a generic request to recover arbitrary spectral peaks.

References:
- https://arxiv.org/abs/1606.00368
- https://github.com/CQMP/Maxent/issues/39
- https://github.com/CQMP/Maxent/commit/ee0f21274416d44367ca5a97a616d2cf94cdcb68
- https://github.com/CQMP/Maxent/commit/673cb34fdfa05209d8b420f4efbc3ea1a6cc2b47
- https://github.com/CQMP/Maxent/commit/affb036b7a9526a1ac4f916c87038d2d31772a0f
- https://github.com/CQMP/Maxent/commit/7cf8cc38322916bea13ebdc76f4bf500b330e007

## F — Matrix continuation plus Dyson consistency

Starting artifact: official Green-Phys/MiniPole examples/MPM/example.ipynb. It supplies an explicit two-orbital fermionic example with Gaussian diagonal spectra and sign-changing off-diagonal spectra, beta=100, and 500 nonnegative Matsubara points. This is an existing example, not a fabricated claim of matrix support in the ALPS 2.0 Maxent code.

Privileged solution artifact: Green-Phys/MiniPole commit 15e4a541d652d2584fd4680413d11b5571f78d9b, dated February 27, 2026. Core paths: mini_pole/mini_pole.py, mini_pole/esprit.py, mini_pole/green_func.py; returned pole_weight has shape (M,n_orb,n_orb), pole_location shape (M,). The implementation uses common poles for matrix elements. Dyson-related application paths: examples/MPM_DLR/cal_band_dlr.py and examples/MPM_DLR/plt_band_dlr.py.

Central outcome: retain off-diagonal spectral/self-energy information and compare direct continuation of G with G reconstructed by matrix Dyson inversion after continuing Sigma. The 2021 Caratheodory paper explicitly establishes the scientific importance of this commutation test. That does not guarantee an arbitrary noisy MiniPole run will satisfy it.

Independent bottlenecks: (1) ill-conditioning, noise tolerance, and shared-pole extraction including sign-changing off-diagonal entries; (2) correct matrix Dyson inversion, static self-energy offsets, and matching real-frequency broadening. The second check is a proposed combination of existing references, not an already verified notebook assertion.

Feasibility: best light-dependency continuation option. setup.py declares NumPy/SciPy and Python >=3.8; README additionally lists matplotlib/kneed, so audit imports rather than trusting package metadata alone. Avoid the Si DLR example unless its external Si_dlr.h5 is fetched: it is linked from Google Drive and is not in the inspected repository tree. No claim that MiniPole always enforces positive semidefiniteness or exact Dyson commutation under noise. Use spectrum-matrix Hermiticity/causality as checks, not elementwise positivity of off-diagonals.

References:
- https://arxiv.org/abs/2410.14000
- https://arxiv.org/abs/2107.00788
- https://github.com/Green-Phys/MiniPole/tree/15e4a541d652d2584fd4680413d11b5571f78d9b
- https://github.com/Green-Phys/MiniPole/blob/15e4a541d652d2584fd4680413d11b5571f78d9b/examples/MPM/example.ipynb
- https://github.com/Green-Phys/MiniPole/blob/15e4a541d652d2584fd4680413d11b5571f78d9b/mini_pole/mini_pole.py
- https://github.com/Green-Phys/MiniPole/blob/15e4a541d652d2584fd4680413d11b5571f78d9b/examples/MPM_DLR/cal_band_dlr.py

## G — Weighted batch variance and replica-comparison pooling

Starting artifact: ALPSCore parent 6c05d6ed2815a782d4d1c356d22a49b67598f9a4 before weighted-batch semantics change; separately parent 03f124acedd7145d25ed4be4e3e779c3d78e6112 before pooling fix.

Privileged solution artifacts: 202df5226dd2abb244cf42bc482da92e69752aee changes batched variance conventions consistently across covariance.hpp, variance.hpp, transform.hpp, autocorr.cpp, and twogauss.cpp. Commit 63701aa0b1b03d836db333848a0ca730a8109968 fixes missing parentheses in alea/include/alps/alea/internal/pooling.hpp so the combined variance numerator is divided by its common degrees-of-freedom denominator.

Central outcome: meaningful uncertainty propagation and comparison of independent run means, rather than batch-size-dependent variance scale or malformed pooled variance.

Independent bottlenecks: (1) variance of batches versus ensemble variance and effective observation counts; (2) correct variance pooling for comparison. Do not equate this pooling function with concatenating raw Markov chains or with a general arbitrary-weight replica estimator.

Feasibility: deterministic numeric library checks, no physical simulation required. Useful strict pre/post fallback if A's signed replica fixture proves insufficiently source-grounded, but scientific breadth is narrower.

References:
- https://github.com/ALPSCore/ALPSCore/commit/202df5226dd2abb244cf42bc482da92e69752aee
- https://github.com/ALPSCore/ALPSCore/commit/63701aa0b1b03d836db333848a0ca730a8109968

## H — Maxent linear-grid endpoint / spectral normalization

Starting artifact: ALPS parent 73b3310067a2a332bab1a4da871874f3cf71d3a8, tool/maxent_parms.cpp, linear FREQUENCY_GRID.

Privileged solution artifact: c21145dcc5f9f14ed235e12482ff7f3118cd0373 fills all nfreq+1 knots instead of nfreq and changes their spacing accordingly. Includes tool/maxent_linear_grid_numeric.cpp and its CMake target.

Central outcome: finite real-axis spectra with sensible spectral weight rather than NaNs from a malformed terminal bin and default-model normalization.

Independent bottlenecks: (1) knot/bin discretization and positive integration widths; (2) end-to-end entropy/default-model normalization and spectral sum rule. These are sequential layers of one root defect, so this is weaker than the independently faulty stages in E or C+D.

Feasibility: upstream executable regression synthesizes two peaks, runs MaxEnt, reads the three output spectra from HDF5, checks finiteness, and checks the averaged-spectrum normalization to 0.05. That threshold is upstream, not invented here. No runtime was measured in this sidecar.

Reference: https://github.com/ALPSim/ALPS/commit/c21145dcc5f9f14ed235e12482ff7f3118cd0373

## c01 preparation gate

Before any pilot build, preserve the existing ratio transform, batch estimator, and autocorrelation conventions from the pinned ALPSCore release. Establish the actual reference build and its upstream ratio test first. Add signed streams only as clearly identified input fixtures; do not substitute independent-error propagation, an arbitrary replica weight rule, or a pointwise ratio average. If a strict historical-fault task is required instead of a later-method application, select G or the C+D DMFT pair. All compilation and numerical validation remain to be done.
