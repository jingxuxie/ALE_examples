# Causal superconducting spectral windows

Infer **sheet-resolved** real-axis quasiparticle spectral weight from noisy, mixed-probe normal
and anomalous Matsubara Green functions. The hidden systems have multiple
superconducting gaps, angularly varying lifetimes, and phonon-like satellite
branches. Recover experimentally interpretable, **finite-resolution integrated
spectral weights for each Fermi sheet**, not microscopic latent parameters or
infinitely sharp peaks. The number of sheets is given, but mixture weights,
gaps, lifetimes, and replica parameters are not. A probe-average reconstruction
does not answer the task. Sheet spectra are scored as an unordered set, using
one whole-sheet permutation per case. Instrumental FWHM is 0.24 meV.

Implement `solve.py --input FILE --output FILE`. Both files are NumPy NPZ
archives; the output contains only `spectral_mass`. The complete interface,
forward map, distribution, resolution, and scoring rule are in `input/FORMAT.md`.

Resources: public training and validation feature/label pairs, the exact public
simulation specification and runnable generator, and a regularized baseline.
Only `participant/` is public. You may generate more training data from the
disclosed family. Hidden seeds, parameters, and labels are not available.

The fixed test has 64 cases. One invocation receives all cases and has **180
CPU seconds, 1 thread, and 4 GiB address space**, without network, GPU, or child
processes. The generous wall ceiling is 3600 seconds to tolerate host load;
CPU time, not host scheduling delay, is the computational limit. Python,
NumPy 1.21.5, and SciPy 1.8 are available. Package any fitted assets with your
solution. `ALE_PUBLIC_INPUT` points to the read-only public `input/` directory.
The output must be finite, nonnegative, and normalized.

Pass all three fixed limits: core error <= 1.00, worst-family mean <= 1.25, and
case-error 90th percentile <= 1.75. The reference scale is 0.6–1.2 percentage
points of each sheet's normalized spectral weight per window, not decimal-level reconstruction
of an unresolved spectrum.

Scientific seed: E. R. Margine and F. Giustino, arXiv:1211.3345, sections II.3
and III.2. This is a causal spectral-surrogate continuation benchmark, **not**
an ab-initio material prediction or a self-consistent Eliashberg solver.
