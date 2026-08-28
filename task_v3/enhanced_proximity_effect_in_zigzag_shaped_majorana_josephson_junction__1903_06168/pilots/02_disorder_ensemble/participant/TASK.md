# Disorder-resilient junction audit

Extend the clean-junction workflow to calibrated spatial disorder and compute reliable low-energy gaps across the supplied device regimes. Preserve the physical model and report the disorder calibration separately from the spectral result.

Deliver `solve.py` in the attempt directory, invoked as `python solve.py --input request.json --output result.json`. The interface and resource envelope are in `input/CONTRACT.md`; the starting model is in `workspace/`. Correctness is assessed separately across clean-like, scattering-dominated, and phase-biased regimes. Do not substitute a broadening estimate for a spectral gap.
