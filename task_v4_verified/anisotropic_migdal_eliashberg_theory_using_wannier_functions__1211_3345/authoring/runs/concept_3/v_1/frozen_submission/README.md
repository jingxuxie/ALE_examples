# Sheet-resolved spectral continuation

Run `python solve.py --input INPUT.npz --output OUTPUT.npz`.
The output archive contains only `spectral_mass`, with the required normalized
active sheets and zero inactive padding. Runtime dependencies are Python,
NumPy, and SciPy. Assets are located relative to `solve.py`, independently of
the current working directory.

Two-sheet cases use the disclosed causal forward family, analytic derivatives,
AR(1) whitening, bounded regularized fits, family averaging, and posterior
sampling. Targets use the exact 32-point dispersion quadrature and the specified
Lorentzian instrumental resolution.

Three-sheet cases use an ensemble of conditional spectral estimators trained
on 300,000 simulated examples from the disclosed family. The simulation seeds
are 13715 and 822738. Frequency compression preserves the whitened noise law;
training adds fresh noise at the disclosed amplitudes. The packaged networks
run directly in NumPy; no training framework is needed at inference.

`isolation.json` records the two canary file-open error classes.
`validation.json` records the final public validation checks and measured
single-process resource use. The public core and tail limits are met, but the
worst-family error remains above the requested 1.25 limit. No hidden-test
accuracy claim is made.
