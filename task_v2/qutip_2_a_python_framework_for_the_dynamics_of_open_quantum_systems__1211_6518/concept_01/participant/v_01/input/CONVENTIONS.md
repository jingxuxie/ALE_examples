# Physical and representation contract

All quantities use hbar = 1 and angular-frequency units. Arrays are complex128
unless naturally real. A JSON manifest points to one NPZ file through `arrays`
(resolved relative to the manifest). Required NPZ keys:

`H0`, `h_ops`, `c_ops`, `a_ops`, `rho0`, `e_ops`, `times`.
Empty operator collections have shape (0, dimension, dimension). All matrices
are in the same supplied laboratory basis; no assumption of real entries,
diagonal observables, product basis, or pure initial state is valid.

The Hamiltonian is H0 plus the sum of h_ops times `h_coeffs` evaluated at the
**absolute** time. `c_coeffs` multiply c_ops as complex **amplitudes**. A
prescribed collapse operator C contributes C rho C-dagger minus one half of
the anticommutator of C-dagger C with rho. The initial state is rho0 at times[0].
Expectations use Tr(O rho). Coefficients are specified by the supplied loader:
constant, sin, cos, gaussian, decay, steps, or carrier. For steps, an edge
belongs to the interval on its right. The coefficient specifications are the
physical controls, not suggestions about an integration mesh.

`physics` has three values:

- `lindblad`: use the explicit time-dependent Hamiltonian and collapse operators.
  No spectral bath is present.
- `redfield`: H0 is static. Each Hermitian a_ops element couples to an independent
  stationary bath with the matching `baths` spectrum. The target is the usual
  second-order Born--Markov Redfield equation, without Lamb shift. If `secular`
  is false, retain the nonsecular terms; if true, retain equal Bohr-frequency
  sectors including coherent interference within exact degeneracies. Distinct
  frequencies separated by more than 1e-7 are not equal. Independent baths
  must not be coherently merged. No additional collapse operators are present.
- `floquet`: the Hamiltonian is periodic with `period`, and the stationary
  baths couple through a_ops. The target is the weak-coupling, **fully secular
  Floquet--Markov** equation, no Lamb shift. Secularization is by physical
  transition frequency including drive harmonics, retaining interference
  within equal-frequency sectors and all diagonal/dephasing contributions.
  This is not an instantaneous-energy-basis equation, a static-H0 equation,
  or just a population rate model. Laboratory micromotion and initial
  coherences are part of the observable dynamics. Results must be independent
  of quasienergy branch choices. Drive harmonics must be converged.

The real two-sided function S(w) is the Fourier transform of the bath correlation
function. Positive w means energy released **by the system**. Its value itself
is the transition-rate multiplier; **do not insert a further 2*pi**. All bath
operators are Hermitian; complex Hermitian matrices are allowed. Available
spectra (definitions, not measured labels) are implemented in `oqs/baths.py`:

- `thermal`: Ohmic density with exponential ultraviolet cutoff, temperature T,
  and the Bose emission/absorption factors. The limit S(0) = eta*T.
- `filtered`: the same density multiplied by the specified positive Lorentzian
  filter plus a nonnegative floor. The filter multiplies the zero-frequency
  limit as well.
- `flat`: symmetric white noise at the stated strength.

Zero temperature permits no absorption. Finite temperature obeys
S(-w) = exp(-w/T) S(w). These spectra specify the Markov model, including for
filtered baths; you are not asked to solve a finite-memory bath model.

For `process: true`, additionally return the linear map on **all** input
operators over [times[0], times[-1]], in column-vectorization convention:
vec_F(rho_final) = channel @ vec_F(rho_initial). The unnormalized Choi matrix is
sum_(i,j) |i><j| tensor E(|i><j|), with the input subsystem first. It has trace d
for a trace-preserving channel. The output still includes the rho0 trajectory.
State outputs are never in an energy or Floquet basis.

`family` and `id` are identifiers for grouping experiments, not mathematical
instructions. The physics is specified by matrices, coefficients, and baths.
The evaluator can rename identifiers and rotate all operators consistently.
