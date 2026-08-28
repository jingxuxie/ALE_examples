# Interface

Run `python solve.py --input request.json --output result.json` offline. Python 3, NumPy, SciPy, mpmath, and a C++ compiler are available. Runtime allowance: 120 seconds per case, one CPU thread, 2 GiB resident memory. A request is independent of other requests.

Complex arrays are encoded as `{"real": nested_list, "imag": nested_list}`. Input fields:
- `iw`: positive imaginary-frequency ordinates, strictly increasing. `G_iw` has shape `(len(iw), orbitals, orbitals)`.
- `moments`: coefficients M0, M1, M2 in `G(z)=M0/z+M1/z**2+M2/z**3+...`. M0 is the identity.
- `h0`: Hermitian matrix defining the bare propagator `G0(z)=(z I-h0)^(-1)`.
- `omega`: real frequencies where reconstruction is requested, and positive `eta` defining `z=omega+i*eta`.
- `support`: an interval containing the spectral support. `absolute_data_error` bounds numerical error in each supplied complex datum; it is not an independently sampled error bar.

Return `G_retarded` and `Sigma_retarded` in the same complex encoding, each of shape `(len(omega), orbitals, orbitals)`. They represent the full matrices, not their elementwise imaginary parts. The self-energy convention is `Sigma(z)=z I-h0-G(z)^(-1)`. The spectral matrix is `-(G-G.conj().T)/(2j*pi)` at each frequency, and must be positive semidefinite. Conjugation/transposition must not be confused with taking the imaginary part entrywise.

Cases include 2–4 orbitals, noncommuting orbital mixing, finite bath spectra, and smooth tight-binding bands; 60–180 imaginary frequencies, and 161–401 real frequencies. Data are given in arbitrary fixed orbital bases. Finite and continuous spectra need not admit the same useful approximation order. The example is unlabeled and is only an I/O check.

Scoring separately measures the full propagator, off-diagonal coherence, self-energy, and negative spectral weight. Errors are normalized against the supplied weak baseline and compared continuously with independently computed reference values. Correctness on one branch does not compensate for failing another; per-family and worst-family results are reported. The submitted program never receives the generating Hamiltonian, reference arrays, or family labels.
