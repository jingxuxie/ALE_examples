# Hidden prediction: fermionic spectra

## Mission
Recover positive, normalized single-particle spectral measures from noisy
imaginary-time correlations and their full covariance. Generalize across
coherent quasiparticles, Hubbard metals, Mott insulators, pseudogaps,
asymmetric continua and multiband continua. These are physically motivated
simulations, not exact microscopic Hamiltonian solutions.

## Assets
`input/` supplies 1,536 labeled training cases, 192 labeled validation cases,
the complete `DATA_CONTRACT.md`, forward-model and scoring definitions.
`baseline/solve.py` is a runnable deterministic reference. Develop your
submission in a separate writable directory; participant assets are read-only.

## Interface
Submit a directory containing `solve.py` and any model assets. The evaluator
invokes `python3 solve.py INPUT_NPZ OUTPUT_NPZ` once for a 192-case batch.
Write exactly `sample_id`, normalized `spectral_mass`, and ordered 10/50/90%
`low_mass_quantiles` arrays. Shapes and conventions are in the data contract.
Public assets are available read-only at `/public/input` during evaluation;
your directory is `/submission`, with scratch at `/tmp`. Use the provided
absolute output path. Hidden labels and evaluator files are inaccessible.

## Objectives
Pass requires **core_score >= 90** and **worst_family_score >= 85**, valid
predictions and compliance with resources. Scores combine normalized
Wasserstein distance, low-energy spectral mass, band weights, effective
gap error and proper quantile loss. Higher is better; 100 is exact recovery.
The fixed independent hidden split and target do not change between attempts.
No passing solution is promised. Full equations are in `input/`.

## Resources
Python standard library, NumPy and SciPy; no GPU or network. One CPU core,
120 seconds wall time per hidden batch, 2 GiB per-process address-space limit.
Submission assets must be under 100 MB; public assets are approximately 31 MB.
Runtime is evaluator-measured, never accepted from predictions.
