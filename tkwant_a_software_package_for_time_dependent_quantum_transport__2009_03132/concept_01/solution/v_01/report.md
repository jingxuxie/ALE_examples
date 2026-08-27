# Qualified release: bounded open-system pulse simulations

## Diagnosis and repair

The release candidate's finite equilibrium occupation does not represent independent incoming reservoirs, and directly damping every occupied wavefunction removes the stationary sea. Smooth late-time decay is therefore not evidence of outgoing-wave accuracy. The replacement initializes lead-resolved continuum states through retarded embeddings, completes the initial spectrum with occupied localized states, and propagates the time-dependent deviation rather than the stationary background. The phase convention and oriented-current routine are retained and checked independently.

The first independent short-time comparison exposed a separate error in our repair: searching for bound states only in the short dynamical lead extension omitted a shallow occupied level. Increasing time-integration accuracy did not repair the initial density. We separated the stationary localization calculation from the dynamical boundary length and repeated both equilibrium spectral and independently propagated finite-system checks. The independent DOP853 transient discrepancy after that repair is below 7e-7. Those checks are private reference-development evidence; the delivered public claims below are derived from this package's reproducible tables.

A later independent audit found that even two longer finite localization domains could miss the same exceptionally shallow scalar-lead pole. Scalar-lead out-of-band states are now obtained from the retarded secular equation and normalized with the self-energy derivative, including their infinite tails. A 1,024-cell-per-lead sparse Hermitian calculation independently verifies that pole and its central probability. Finite localized-state searches remain in use for dark states embedded in the continuum and for the separately checked multiorbital contacts. This correction changes no physical input or scoring tolerance.

## Experiments and supported interpretation

`results.csv` is the six-case production study. `ablation.csv` contains a conservative numerical refinement and a distinct continuum-only ablation. The latter holds time stepping, quadrature policy and dynamic boundary fixed, changing only occupation of the normalizable sector. It removes 1.93677138 particles from the initial central charge of the sidebranch experiment. This supports claim `localized_weight`; it does not imply every post-pulse oscillation is a bound state or that all continuum errors are absent. The primary figure shows distinct transient bond currents, not only central charge offsets.

The cavity final-charge comparison supports `cavity_refinement`. Agreement of these two calculations is not treated as an oracle. Absolute initial density, non-equilibrium stationarity and independent small-system propagation provide different checks. The stationary control supports `stationary_control`; conservation alone would not validate the reservoir occupations.

`scaling.csv` and the resource figure retain measured short/long-horizon runtime and resident-memory values. Claim `horizon_cost` accurately describes this implementation: the reflection-safe lead extent grows with the requested horizon and the spectral resolution also depends on it. The implementation is practical in the stated envelope, not a claim of asymptotically optimal boundary compression. RSS from the batch process is a high-water mark and can include an earlier case's allocation; external grading independently measures the complete process.

## Reproduction and limitations

Run `bash run.sh --cases SUITE --output DIRECTORY --config production` from any directory. Run `workspace/experiment.py --input INPUT_DIRECTORY --output OUTPUT_DIRECTORY` with one numerical thread to regenerate the evidence tables and figures. The `conservative` configuration refines temporal, spectral and dynamical-boundary resolutions and independently extends the bound-state localization domain. The `ablation` configuration omits occupied bound states only.

The numerical policy is qualified for the stated finite energy/time envelope. Very shallow levels outside that envelope, exponentially narrow unresolved resonances, lower temperatures with much longer requested times, or more lead channels require further convergence work. There is no Markov, wide-band, Fermi-level-only, partitioned-quench or family-ID-specific shortcut. Figures are generated from retained CSV and NPZ source data; no aesthetic property is an accuracy metric.
