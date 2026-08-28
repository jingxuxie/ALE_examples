# Contract

All quantities are dimensionless; the gyromagnetic ratio, hbar, and kB are one.
Sites are a periodic simple-cubic lattice in NumPy C order. Unit spins have
material-dependent positive moment `mu`. Each undirected nearest-neighbor bond
has energy `-J[a,b] dot(Si,Sj)`; on-site energy is
`-K[a] Si,z**2 - mu[a] dot(field,Si)`. `exchange` is symmetric. The effective
field is minus the spin energy derivative divided by the site's moment.

The required continuum evolution is
`dS/dt = S cross (H_eff + B(t)/sqrt(mu) + V)`,
`dV/dt = W`, and `dW/dt = A*S - omega0**2*V - Gamma*W`.
`initial_memory="equilibrated"` sets `V=A*S/omega0**2`; `"empty"` sets it
to zero. W initially vanishes. `common.initialize` fixes the exact initial
spins and material assignment. Do not add an independent Gilbert damping term.

The two-sided bath spectrum is defined here as
`P(omega)=A*Gamma*abs(omega)*theta/((omega0**2-omega**2)**2+Gamma**2*omega**2)`.
For positive frequency, theta is `2*T/omega` for `classical`,
`coth(omega/(2*T))` for `quantum`, and `coth(omega/(2*T))-1` for `nozero`.
The zero-frequency value is the continuous limit. At T=0, quantum theta is one;
the other two spectra vanish. There is no ultraviolet white-noise tail.

For deterministic comparisons the forcing is a finite periodic Gaussian record,
not an unspecified random-number implementation. Let `coarse_dt=dt*decimation`
and `nfft` be the input FFT length. Initialize
`rng=numpy.random.default_rng(noise_seed)` and draw standard-normal numbers in
site, Cartesian-component, time order, shape `(N,3,nfft)`. For each channel,
take its real FFT, multiply frequency bin k by
`sqrt(2*P(2*pi*k/(nfft*coarse_dt))/coarse_dt)`, and inverse real FFT with length
`nfft`. Linear interpolation in time defines B, including at intermediate
integration times. Different materials use their own spectrum on their channels.
Draws may be batched without changing their order. The integration interval
never reaches the periodic seam. This protocol permits any convergent integrator;
it does not require reproducing the baseline's time discretization.

Output NPZ arrays, all finite float64:
- `spins`: final unit spins, shape `(N,3)`.
- `memory`: final V and W, shape `(N,6)`, ordered Vx,Vy,Vz,Wx,Wy,Wz.
- `trace`: unweighted mean spin vector per material at sample steps, shape
  `(len(sample_steps),number_of_materials,3)`; include step zero.
- `covariance`: exact discrete covariance of the defined bath record before
  division by sqrt(mu), shape `(number_of_materials,len(lags))`. This is the
  expectation over the Gaussian draws, not one realization's sample covariance.

Scoring separately measures spins/trace, memory/restart, and bath covariance.
Errors are normalized to the supplied classical baseline's error on each case;
the reference scores one and the baseline approximately one half. Family means
and the worst family are reported; incomplete outputs are not silently ignored.

Hidden cases vary lattice size, exchange sign, bath stiffness, temperature,
moment contrast, initial memory, and initial texture within this contract.
The public example is an input-only smoke test, not a labeled development set.

During evaluation the submission and participant workspace are read-only;
the output directory and `/tmp` are writable. Put runtime compilation and caches
there, or submit an already-built binary. `workspace` and `workspace/vendor`
are on PYTHONPATH. Do not bundle the provided numerical runtime into a submission.
The entry point is executed in a new process for every case, without network
access or access to any private case other than the current input JSON.
