# Numerical interface

## Execution and representation

Run `python attempt/solve.py --input input.json --output output.json`. Submit one self-contained Python file; do not depend on sibling files, network access, or the working directory. Python 3, NumPy, and SciPy are available. A fresh process handles each case, with 120 seconds wall time. The evaluator copies only the submitted file and that case's input into a temporary working directory. Outputs must be finite JSON numbers with exactly the specified array shapes. Complex numbers are `[real, imaginary]`, never strings. A missing field, malformed JSON, wrong shape, nonnumeric value, nonfinite number, nonzero exit, or timeout gives the entire case zero. Extra output fields are ignored.

Every input has `family`, choosing one of the three interfaces below. All indices are zero based. All frequencies are positive fermionic Matsubara frequencies `omega[n]=(2*n+1)*pi/beta`, `z[n]=i*omega[n]`. Flavors are the outermost index, then frequency; complex pairs are innermost. No self-consistent impurity simulation or stochastic sampling is requested: perform the deterministic integration/measurement step on the supplied data.

## `fourier`: tail-aware matrix-entry transform

Inputs: `beta>0`, integer `n_tau`, and `channels`. Each channel contains `sites: [row,column]`, `moments: [c1,c2,c3]`, and `iw`, an `[N,2]` array. Every channel has the same `N`, and `n_tau>2*N`. All coefficients are real, `c1=1` for diagonal entries and `c1=0` otherwise. Entries have the real-Hamiltonian convention `G(-i*omega)=conj(G(i*omega))`. Channels need not be a complete square matrix.

Define

```
M(z) = c1/z + c2/z**2 + c3/z**3
T(tau) = -c1/2 + c2*(2*tau-beta)/4 + c3*tau*(beta-tau)/4
r[n] = G(z[n]) - M(z[n])
tau[j] = beta*j/n_tau
```

The target is the **finite-frequency, tail-regularized transform**, not an extrapolation of unknown frequencies:

```
G_tau[j] = T(tau[j]) + (2/beta)*Re(sum_n exp(-z[n]*tau[j])*r[n])
```

Use this for `0 <= j < n_tau`; set `G_tau[n_tau]=-c1-G_tau[0]`. The endpoint at zero is `0+`, the last is `beta-`. Every supplied channel is active. In particular, three zero tail coefficients do **not** imply an identically zero Green function; legitimate off-diagonal resolvents can start at order `1/z**4`. Do not discard such channels. There is no disabled-channel sentinel.

Also return the tail-subtracted round trip, using only the left endpoints:

```
G_roundtrip[n] = M(z[n]) + (beta/n_tau) *
    sum_(j=0..n_tau-1) exp(z[n]*tau[j])*(G_tau[j]-T(tau[j]))
```

Outputs: `g_tau` of shape `[channels,n_tau+1]`, and `iw_roundtrip` of shape `[channels,N,2]`. Components score diagonal time data, off-diagonal time data, and the full frequency round trip separately. Tail subtraction and endpoint conventions are part of the target, not discretization freedoms.

This family extends the old bare matrix Fourier interface. Concrete historical production transformers used one site. The task does not interpret the old three-moment short circuit as a physical rule.

## `afm`: multiband Hilbert integral and Weiss update

Inputs: `beta`, `mu`, `h`, `n_tau`, arrays `g0_iw` and `g_iw` of shape `[F,N,2]`, and `dos` of length `F/2`. `F` is even. Adjacent flavors `(2*b,2*b+1)` are one band's two opposite AFM sublattices/spins; neither flavors nor bands may be averaged together.

Each DOS entry has equal-length real arrays `energy` and `weight`. Weights are positive, sum to one, and describe an even discrete measure. **The supplied nodes and weights define the integral exactly**; no DOS fitting, Simpson reinterpretation, or extra normalization is intended. Nodes/weights may differ by band. Let `m2[b]=sum_q weight[b,q]*energy[b,q]**2`.

For every band and frequency:

```
Sigma[f,n] = 1/g0_iw[f,n] - 1/g_iw[f,n]
a = 2*b
d = 2*b+1
zeta_a = z[n] + mu - h - Sigma[a,n]
zeta_d = z[n] + mu + h - Sigma[d,n]
I = sum_q weight[b,q] / (zeta_a*zeta_d - energy[b,q]**2)
G_lattice[a,n] = zeta_d * I
G_lattice[d,n] = zeta_a * I
G0_new[f,n] = 1 / (1/G_lattice[f,n] + Sigma[f,n])
Delta[f,n] = z[n] + mu + field[f] - 1/G0_new[f,n]
```

Here `field[even]=-h`, `field[odd]=+h`. All inversions in these equations are scalar complex reciprocals. The DOS measure, field convention, and pair mapping must remain attached to the correct band. Do one update, with no mixing or iteration.

Return `weiss_tau` by applying the `fourier` transform to each diagonal channel of `G0_new`, with moments `[1,-a_f,a_f**2+m2[b]]`, where `a_f=mu+field[f]`. These are the declared Weiss high-frequency moments for this bipartite step.

Outputs: `lattice_iw`, `weiss_iw`, and `hybridization_iw`, each `[F,N,2]`, plus `weiss_tau`, `[F,n_tau+1]`. Each output is a separately scored component. This is a coupled lattice-to-frequency-to-time pipeline, not just a flavor dispatch test.

## `legendre`: signed configuration estimator and reconstruction

Inputs: `beta`, positive integers `n_legendre=L`, `n_iw=N`, and `configurations`. A configuration has `sign` equal to `+1` or `-1`, positive `weight`, arrays `c_times` and `cdagger_times` of equal length `K`, a real `[K,K]` array `matrix`, and real `f_prefactor` of length `K`. Times lie in `[0,beta)`. The matrix index convention is **`matrix[j][i]=M_ji`**, with `i` indexing `c_times` and `j` indexing `cdagger_times`. Configuration sizes can differ.

Define `D=sum_config weight*sign`; supplied cases have `D>0`. `weight` is the multiplicity/statistical weight before sign reweighting, not an already signed weight. For every configuration and ordered pair `(i,j)`, set

```
u = c_times[i] - cdagger_times[j]
wrap = -1 if u < 0 else +1
if u < 0: u = u + beta
x = 2*u/beta - 1
```

For the ordinary Legendre polynomial `P_l`, the requested normalized coefficients are

```
G_l = -sqrt(2*l+1)/(beta*D) *
      sum_config weight*sign * sum_ij wrap*M_ji*P_l(x)
F_l = -sqrt(2*l+1)/(beta*D) *
      sum_config weight*sign * sum_ij wrap*M_ji*f_prefactor[i]*P_l(x)
```

Apply the configuration sign exactly once, separately from the fermionic wrap sign. These are standard normalized coefficients; raw historical measurement arrays omit `sqrt(2*l+1)` until evaluation. The configurations are deterministic estimator fixtures, not a demand to generate a physical Monte Carlo history; their reconstructed functions need not be causal.

Use the finite polynomial reconstruction, **not** the direct untruncated event-frequency estimator:

```
G_L(tau) = sum_(l=0..L-1) sqrt(2*l+1)*G_l*P_l(2*tau/beta-1)/beta
F_L(tau) = sum_(l=0..L-1) sqrt(2*l+1)*F_l*P_l(2*tau/beta-1)/beta
G_iw[n] = integral_0^beta exp(z[n]*tau)*G_L(tau) d tau
F_iw[n] = integral_0^beta exp(z[n]*tau)*F_L(tau) d tau
Sigma_iw[n] = F_iw[n]/G_iw[n]
```

Inputs guarantee nonzero `G_iw` for this definition. `f_prefactor` already includes any interaction prefactor; add no extra `U`, minus sign, or Hartree subtraction.

Outputs: `g_legendre` and `f_legendre`, each `[L]`; `g_iw` and `sigma_iw`, each `[N,2]`. The four outputs are separately scored.

## Bounds and scoring

Cases have `1<=beta<=40`, at most 12 flavors, 12 Fourier channels, 40 positive frequencies, 512 time intervals, 256 DOS nodes per band, 32 Legendre coefficients, 24 configurations, and 6 operators of either type per configuration. Double precision is sufficient.

Each component's error is the RMS error of its flattened real JSON representation, divided by `max(1,RMS(reference))`. Its score is `1/(1+error/scale)`. Fixed private scales are anchored to the runnable weak adapter and an independently checked strong reference: `scale=max(weak_error/4,1e-8,100*strong_crosscheck_error)`. Scores have no tolerance plateaus or clipping near one. Components, cases, and families are equally averaged at their respective levels; the two splits are family balanced. Missing/malformed outputs get zero rather than a partial score. Family means and the worst family are reported in addition to the overall mean.
