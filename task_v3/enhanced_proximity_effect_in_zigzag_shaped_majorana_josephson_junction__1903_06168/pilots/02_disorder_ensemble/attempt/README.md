# Disorder-resilient junction audit

Run the submission with Python 3.10 and the supplied numerical dependencies:

```sh
python solve.py --input ../participant/input/request.json --output result.json
```

`--verbose` optionally writes convergence and timing diagnostics to stderr.
The JSON output contains only the requested `results` entries, with disorder
half-widths and gaps in meV. Case identifiers do not enter the calculation.

## Physical model and calibration

The executable imports the read-only `participant/workspace/clean_model.py`
and calls its `make_system` and `parameters` functions. A local `workspace/`
beside `solve.py` is also supported. No model parameters or mesh spacings are
changed. The supplied `random_field.field(U, salt)` is evaluated at each site's
physical coordinates, and its potential multiplies `diag(1, -1, 1, -1)` in
every region of the finalized Hamiltonian.

The calibration is evaluated in SI units:

```
v_F = sqrt(2 mu / m_dis)
rho_site = a^2 m_dis / (pi hbar^2)
U = sqrt(3 hbar v_F / (2 pi rho_site mfp))
```

Here `m_dis = 0.023 m_e`, `mu = 10 meV`, and `a = 10 nm`; the final `U` is
converted back to meV. The forward model retains its distinct `0.02 m_e`
effective mass. This calibration is not used as a gap or a broadening model.

## Spectral calculation

An exact unitary change of Bloch gauge distributes the full-cell phase across
the 390 longitudinal grid steps. This makes interpolation smooth without
changing any eigenvalues. A spatial nested-dissection permutation and sparse
shift-invert LU/ARPACK calculations obtain low-energy eigenpairs at five
initial phases. The eigenpair residuals are checked explicitly.

The sampled eigenvectors form an orthonormal reduced basis. The solver
projects the square of the Hamiltonian, so its interpolated absolute energies
are variational upper bounds, without spurious zero Ritz values from mixing
positive and negative high-energy states. It searches the entire phase
interval and validates candidate minima using additional full sparse
eigensolves, enriching the basis when needed. Particle-hole symmetry makes
the absolute lowest energy even in phase, so `[0, pi]` covers the full Bloch
zone. The reported gap is a validated full-matrix eigenvalue, not just the
interpolation result.

BLAS thread counts are set to one before importing NumPy or SciPy. No dense
full-system matrix is constructed, and no persistent cache is required.

## Validation

The supplied request produces `U = 1.5995099604245393 meV` and
`gap = 0.049938820975069645 meV`, with the minimum near full-cell Bloch phase
`2.051752431`. A repeated execution produces byte-identical JSON. The complete
CLI run takes 91.11 seconds and peaks at about 870 MiB resident memory, with a
12 GiB address-space limit imposed during the test.

Additional clean-like, scattering-dominated, and phase-biased cases are
recorded in `validation_results.json`. Each is checked against four additional
full-matrix sparse spectra between the initial sample phases. A direct
comparison against the original Kwant Bloch Hamiltonian also verifies the
uniform-gauge transformation, to a matrix-norm difference below `4e-12`.
