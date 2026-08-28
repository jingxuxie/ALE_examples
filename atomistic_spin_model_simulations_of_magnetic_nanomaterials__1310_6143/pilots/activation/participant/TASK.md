# Thermally activated reversal of finite spin chains

Compute the lowest index-one transition state connecting the supplied metastable
minimum A to minimum B, its activation barrier, and the tangent fluctuation
spectra controlling the harmonic transition-state prefactor.

Cases include short-chain coherent reversal, longer-chain domain-wall
nucleation, and nonuniform exchange-spring textures. The open-boundary atomistic
Hamiltonian, units, output definitions, limits, and scoring are in
`input/FORMAT.md`. Both locating the transition state and resolving its soft
fluctuation modes matter; a good energy alone is insufficient.

Implement `solve.py` in your submission directory. It must support
`python solve.py CASE.json OUTPUT.npz` (JSON output is also accepted).
The supplied `workspace/energy.py` provides energy, Euclidean/tangent gradients,
and ordinary downhill relaxation, not a transition-state or spectrum solver.
The ordinary-relaxation baseline does not solve either requested bottleneck.

Evaluation uses independent cases, process-level runtime limits, and calibrated
continuous scores for barrier, stationarity/inertia, spectra, and harmonic
prefactor, aggregated across mean and worst-performing families. Do not read
private reference data or import the private reference library. No internet or
external reference executable is required.
