# Public mathematical and interface contract (ratchet 1, schema version 1)

This document, not any external publication or software default, defines the task.
Every numerical input is in the case dictionary. There are no hidden physical
parameters. The evaluator's reference uses exactly this contract.

## 1. Execution and JSON

Implement `solver.py` in the submitted directory. The runner calls
`solve(case: dict) -> dict` once in a fresh process for each case. It supplies only
this participant tree read-only and your submission writable, standard libraries,
NumPy, and SciPy. Private references and other cases are inaccessible. No network.
Limit: a strict 60-second worker wall alarm, 6 GiB address-space limit, one BLAS
thread. Worker CPU soft/hard limits are 61/62 seconds. The isolated runner allows
30 seconds of namespace-startup grace (90-second parent watchdog); this is not
extra solver compute time. Module import and `solve` execute inside the worker
budget. `workspace/` is optional scratch; the submitted entry point is root
`solver.py`, not a file inside `workspace/`.
Do not print large diagnostics; return finite built-in numbers/lists/dictionaries.
An optional top-level `metadata` dictionary is ignored. No file naming beyond
`solver.py` and no executable permission is required.

The input has keys `version`, `case_id`, `calibration`, `model`, `initial`,
`actions`, `budget`, `times`, and `audit`. The example is unlabeled and solely
demonstrates the schema. Arrays use the order given, not a sorted order.

Return:

```
{
  "bath": {"beta": 0|1|2, "amplitude": float, "cutoff": float,
           "floor": float, "eta": float},
  "audit": [
    {"real": [[float, ...], ...], "imag": [[float, ...], ...],
     "activity": [float, float, float]}, ...
  ],
  "predictions": {
    "ACTION_ID": {"gauge": [float, ...], "fidelity": [float, ...],
                  "electric": [float, ...], "density": [[float, ...], ...]}, ...
  },
  "selected_action": "ACTION_ID"
}
```

`audit` has one entry per supplied audit state (two), in the same order, with
64-by-64 real/imaginary matrices. Each prediction contains one entry per time;
`density` has shape `[number_of_times, 3]`. Predict **all and only feasible**
actions (extra predictions are ignored). The audit action need not be feasible.
The chosen action must be feasible. Missing/invalid components receive zero only
for that component; a timeout, exception, or non-dictionary result scores zero
for the case. Extra top-level keys are ignored. A missing action prediction makes
the dynamics component zero; it does not invalidate calibration or audit.

## 2. Bath inference

The two-sided spectrum already includes the system-bath coupling squared, has
angular-frequency units, is even in frequency, and has no extra 2 or 2π factor:

\[
 S_\theta(\omega)=\begin{cases}
 a,&\beta=0,\\
 a(\omega^2+\omega_c^2)^{-\beta/2}+b,&\beta=1,2.
 \end{cases}
\]

Bounds: `amplitude` a in [1e-5, 0.12], `cutoff` ωc in [0.12, 1.2],
`floor` b in [0, 0.02], and correlation `eta` η in [0,1]. For β=0 use the
canonical ωc=1 and b=0; these two entries are not fitted or separately scored.
S(0) is finite. β=2 denotes the regularized 1/f² limit, not an unregularized
infrared divergence. All frequencies, rates, energies, and times set ℏ=1.

Each calibration row has `omega`, `weight` (equal-length lists with nonnegative
weights summing to one), `mode` m in {-1,0,1}, `value` y, and `sigma` σ>0.
It measures a finite-band single-probe (m=0), normalized symmetric pair (m=1),
or antisymmetric pair (m=-1) rate. Its mean is

\[
 r(\theta)=(1+m\eta)\sum_k w_k S_\theta(\omega_k).
\]

Calibration values are synthetic independent Gaussian measurements, not exact
spectral samples and not empirical device measurements. Fit the model by minimizing
`sum_rows ((r-y)/sigma)**2 + k*log(number_of_rows)` over β and its bounded
continuous parameters, with k=2 for β=0 and k=4 otherwise. This is the prescribed
penalized least-squares fit, not recovery of the inaccessible generating truth.
Use smaller β to break objective ties within 1e-8. All frozen cases have a
well-separated winning model. Parameterization/optimizer choices are unrestricted.
Calibration scoring compares the fitted spectrum at 33 geometric frequencies
from 0.02 to 30, including zero as a 34th point, and η. It does not require exact
agreement in poorly identifiable amplitude/floor coordinates.

## 3. Gauge simulator and basis

There are L=3 sites and L=3 periodic links, dimension d=2^(2L)=64. Indices j
run 0,1,2 modulo L. Tensor order is `(matter0, link0, matter1, link1, matter2,
link2)`; the first qubit is the **most significant** bit of integer basis indices.
All matrices returned in `audit` use this computational basis, never an eigenbasis.
Z=diag(1,-1), X=[[0,1],[1,0]], n=(I-Z)/2, and a=|0><1|.
Operators with a site/link subscript act there and as identities elsewhere.
Links are in the electric basis, so hopping uses link X and electric energy Z.

`model` contains length-three arrays `hopping`, `phase`, `electric`, `mass`,
`error_hop`, `error_link`, `crosstalk`, `matter_weight`, `link_weight`,
`matter_sign`, `link_sign`, plus scalar `lambda` and `kappa`.

\[
 H_0=\sum_j[J_j e^{i\phi_j}a_j^\dagger X_{\ell_j}a_{j+1}
             +J_j e^{-i\phi_j}a_{j+1}^\dagger X_{\ell_j}a_j
             -h_j Z_{\ell_j}+\mu_j n_j],
\]
\[
 H_1=\sum_j[u_j(a_j^\dagger a_{j+1}+a_{j+1}^\dagger a_j)
                      +v_j X_{\ell_j}].
\]

Each state specification has parallel lists `indices`, `real`, `imag`; amplitudes
are real+i*imag at those indices and zero elsewhere. All provided states are
normalized. `initial` has support within one joint eigenspace of
`K_j=Z_matter_j Z_link_(j-1) Z_link_j`. Let k_j be the ±1 eigenvalue of K_j
on the **first** listed initial basis index. Define `q_j=(I-k_j*K_j)/2` and
`Q=sum_j(q_j)/L`. Thus initial gauge violation is zero, Q lies in [0,1], and
`[H0,q_j]=0`. No projection to a fixed particle-number or gauge sector is allowed
for the noisy evolution. Matter bath flips can change particle number.

An action has `id`, `strength` V>=0, and length-three `coefficients` c.
Its cost is `V**2 * sum(c_j**2)` and it is feasible iff cost<=budget+1e-10.
There is always a feasible zero-strength action. The implemented Hamiltonian is

\[
 H_s=H_0+\lambda H_1+V\sum_j c_jq_j
             +\kappa V^2\sum_j d_j c_j^2 n_j,
\]

where d=`crosstalk`. This known gauge-preserving actuator detuning can distort
the intended dynamics even when gauge violation is small. Signed coefficients
are intentional: they can create degenerate unprotected transitions. Budget is
a hard constraint, not an extra objective penalty.

## 4. Spatial channels and the complete secular generator

For either species t=matter,link, let A_tj be X on that qubit, r_tj its positive
`*_weight`, and s_tj its known ±1 `*_sign`. The two species' baths are independent.
For each species use **four independent** Hermitian operators:

\[
 B_{tj}=\sqrt{(1-\eta)r_{tj}} A_{tj}\quad(j=0,1,2),\qquad
 B_{tC}=\sqrt{\eta}\sum_j s_{tj}\sqrt{r_{tj}}A_{tj}.
\]

Every B uses the same S(ω); there is no division of the collective operator by
sqrt(L), and no additional η in the rate. This fixes the cross-spectrum to
`S(ω)*sqrt(r_j*r_k)*[(1-η)δ_jk+η*s_j*s_k]` within each species.
η=0 is independent noise; η=1 is purely collective. Do not sum species before
forming the dissipator.

Diagonalize the **full Hs**, including coherent errors and crosstalk. Let P_e be
its energy projectors. For numerical grouping only: sort eigenvalues ascending;
start a cluster at the smallest unassigned value and include subsequent values
within 1e-9 of that cluster's **first** value, then replace the cluster's values
by their arithmetic mean. Form every ordered energy-pair gap E_source-E_dest,
sort the gaps, and apply the same first-value clustering rule with 1e-8 tolerance.
The frequency of a gap cluster is its arithmetic mean **over all d² ordered
eigenvector-index pairs, including pairs whose channel matrix elements vanish**.
The maximum energy/frequency clustering uncertainty is far below scoring scales;
cases do not sit on a clustering boundary.

\[
 B_\alpha(\omega)=\sum_{e'-e\text{ in frequency cluster }\omega}
                      P_e B_\alpha P_{e'},
\]
\[
 \mathcal D_\theta(\rho)=\sum_{\alpha,\omega} S_\theta(\omega)
 \left[B_\alpha(\omega)\rho B_\alpha(\omega)^\dagger
   -\tfrac12\{B_\alpha(\omega)^\dagger B_\alpha(\omega),\rho\}\right],
 \qquad \dot\rho=-i[H_s,\rho]+\mathcal D_\theta(\rho).
\]

Keep positive, negative, and zero frequencies. Sum amplitudes at equal frequency
**before** forming each dissipator: separate rank-one jumps incorrectly erase
degenerate-transition interference. Do not merge unequal frequencies, even for a
white spectrum. No Lamb shift, thermal factor, nonsecular cross-frequency terms,
or state-dependent rate is included. The density matrix is not renormalized or
projected during evolution. This is a specified Markov/secular effective model,
not an exact non-Markovian simulation of a classical 1/f process.

## 5. Independent rate audit

`audit` supplies its own `action`, exact `bath`, and two `states`. Use the same
model Hs but this supplied bath, **not the bath you fitted**. For each audit state
ρ=|ψ><ψ|, return real and imaginary parts of D(ρ), **without** the commutator.
Also return the three jump activities
`sum S(ω)*Tr[B(ω) ρ B(ω)†]`, binned by |ω|<=1e-8 (zero),
1e-8<|ω|<2 (slow), and |ω|>=2 (fast). They are nonnegative and include elastic
jumps. They are not the purity derivative or total escape rate. Audit probe
states can span gauge sectors; these are calibration probes, not initial states
for the intended gauge simulation. Matrix output makes eigenvector phases and
degenerate-space rotations irrelevant to scoring.

## 6. Predict and choose

For each feasible action evolve the initial pure state using your inferred bath.
The reference evolves using the minimizing calibration fit, not generating truth.
Times are increasing, uniformly spaced, start at zero, and have
8000 <= T=times[-1] <= 20000. There are seven supplied sample times. The same
Hamiltonian, spectrum, generator, and objective apply over this entire interval;
no short-time expansion or steady-state replacement defines the target.
At each time return:

- `gauge` = Tr(Qρ).
- `fidelity` = <ψ_ideal(t)|ρ(t)|ψ_ideal(t)>, where
  |ψ_ideal(t)>=exp(-i H0 t)|ψ_initial>. This is unsquared pure-state overlap,
  not Uhlmann's root fidelity and not fidelity to the protected Hamiltonian.
- `electric` = sum_j Tr(Z_link_j ρ)/L.
- `density` = [Tr(n_0ρ),Tr(n_1ρ),Tr(n_2ρ)].

Select the feasible action minimizing
`R = trapz(0.45*gauge + 0.55*(1-fidelity), times) / T`.
The evaluator scores the selected action using its precomputed reference risk,
not your reported curves. True risk ties within 1e-10 can be broken by input
action order; regret scoring accepts any actual tie equally. There is no reward
for a confidently incorrect risk estimate.

## 7. Continuous scoring and tolerances

Four components have weights calibration .25, audit .30, dynamics .30, decision .15.
Let starred values denote the reference. Raw nonnegative errors are:

- calibration: mean over the 34 specified frequencies of
  `log(S/S*)**2`, plus `4*(eta-eta*)**2`.
- audit: average over probes of half the relative squared Frobenius error of
  Dρ (denominator `||Dρ*||F**2+1e-16`) plus half the relative squared activity
  vector error (denominator `||activity*||2**2+1e-16`).
- dynamics: average over feasible actions of the mean squared error over all
  times and six channels `[gauge,fidelity,electric,n0,n1,n2]`. Electric is divided
  by 2 before computing this error; the other quantities already have range one.
- decision: `max(0,R*(selected)-min_feasible R*)`.

For each component `score=1/(1+error/anchor)`. The anchor is
`max(error_of_frozen_weak_baseline, floor)`, with floors respectively
`0.01, 0.01, 0.0001, 0.002`. The fixed weak baseline is actually evaluated: white
fit with η=0 and amplitude equal to the median single-probe measurement clipped
to [1e-5,0.12]; independent local channels; largest-cost feasible protection.
It uses the fully secular generator of section 4 with that constant spectrum and
η=0, under the correct Hs. For the independent audit it instead uses the constant
S_supplied(1) at every frequency, again with η=0; this audit surrogate is not a
calibration fit and need not satisfy fitted-amplitude bounds. It retains the
prescribed degenerate-frequency grouping. Thus this baseline neglects spectral
color and spatial correlation, not all dynamics. Its actually measured per-case
errors are frozen before participant attempts. Weak-to-reference errors are private normalization
constants, not hidden task definitions. Exact reference scores 1; a nonzero
error is never clipped to 1 or 0, and errors smaller than a floor still matter.

All comparisons are continuous; there is **no exact parameter, float, or textual
matching gate**. Practical numerical targets: spectral relative error below 1e-3,
audit relative Frobenius error below 1e-3, observable absolute error below 2e-4,
trace/Hermiticity error below 1e-8, and density eigenvalues >=-1e-8. These targets
are guidance, not pass/fail gates. Invalid shapes/nonfinite values affect the
corresponding component as specified in section 1.

The evaluator reports `mean_core` (mean weighted case score), `family_scores`,
`worst_family` (minimum family mean), `component_scores` (case means), and `cases`.
It additionally reports `score=0.7*mean_core+0.3*worst_family`. Families cover
white/coherent competition, 1/f correlation crossover, and 1/f² degeneracy.
There are six private screening cases, two per family, and three separately
reserved confirmation cases, one per family. No additional challenge split is
allocated for this ratchet. Confirmation is not a development set. Only the
single unlabeled example is public; all scientific conventions are given here.
