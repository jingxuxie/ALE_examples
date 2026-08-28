# Finite-memory thermal spin solver

Run the self-contained submission with:

```sh
python solve.py CASE.json OUTPUT.npz
```

NumPy and `g++` are required. The supplied evaluation environment provides both.
The entry point embeds its C++ kernel and builds it in a temporary directory
beside the output. Compiler temporaries use that directory too. Nothing is
written to the input or submission directories during evaluation, unless the
output was explicitly placed there. Numerical libraries are restricted to one
thread.

## Physics and numerics

- Initialization and periodic six-neighbor geometry reproduce `common.initialize`.
  Exchange is divided by the receiving site's moment, anisotropy contributes
  `2 K Sz / mu`, and the applied field is not divided by the moment.
- The coupled equations evolve all three spin components and all six oscillator
  variables. There is no independent Gilbert term. Equilibrated and empty
  memory start exactly as specified.
- The internal oscillator velocity is `W / omega0`, improving error scaling
  without changing the equations. Output converts back to `W`.
- A compiled eighth-order DOP853 integrator controls the largest scaled local
  error over every site and component. Default relative and absolute
  tolerances are `1e-8` and `1e-10`; the oscillator absolute tolerance is scaled
  by `A / omega0**2` for nonzero coupling. Accepted spins are projected to unit length.
  Integration stops at every forcing knot and requested sample time.
- Gaussian draws retain site/component/time order even when generated in
  batches. The prescribed real FFT filter is applied in double precision.
  Only the used prefix of each record is retained, in time-major order. Large
  prefixes use a disk backing file with bounded working memory instead of a
  full-size memory mapping.
- Quantum and zero-point-subtracted spectra use `expm1` to avoid cancellation
  at low temperature. Their zero-frequency and zero-temperature limits are
  explicit. There is no white-noise ultraviolet addition.
- Covariance is the inverse real FFT of `2 P / coarse_dt`, sampled at the
  requested integer lags. It is the exact ensemble covariance of the specified
  discrete Gaussian record, including DC and Nyquist multiplicities, not a
  sample estimate or continuum integral.

## Validation

`validate.py` independently constructs the spectra and forcing and integrates
the original, unscaled nine-variable equations with SciPy DOP853 at much
tighter tolerances. It checks classical, quantum, and nozero baths; zero
temperature; two competing magnetic sublattices; moment contrast; both memory
initializations; odd FFT lengths; stiff overdamped memory; zero-duration runs;
and sample times between forcing knots. Additional checks compare batched and
disk-backed forcing with a single full Gaussian draw, and compare covariance
with an explicit weighted cosine sum. Analytic checks cover free precession
and underdamped, critically damped, and overdamped oscillator restart states.

`benchmark.py` creates public-input-derived stress tests with 46,656 spins and
enforces a 1.5-GiB address-space limit. Set `SPIN_SOLVER_STATS=1` to print accepted
and rejected step counts and right-hand-side evaluation counts.
The stiff two-material test took 32.3 seconds in this environment, including
compilation and noise generation. The forced disk-backed long-record test took
14.6 seconds. Both stayed below approximately 165 MiB peak resident memory,
including the compiler's peak as reported by `/usr/bin/time`.

## Scientific limitations

This solves the stated finite, periodic, discretely filtered bath with linear
interpolation, not an infinite-bandwidth continuum bath. Its numerical
integration error is controlled but nonzero. The prescribed quantum spectrum
acts on classical unit spins; it is not a full quantum many-spin calculation.
Very extreme unbounded stiffness or unusually long input records can require
more computation than the stated execution allowance; the implementation does
not silently substitute Markovian dynamics or truncate the required noise.
