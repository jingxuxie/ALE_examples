# Exact forward model

## Conventions and trusted controls

The basis is `|control,target> = |00>, |01>, |10>, |11>`. Strings are tensor products in this order: `ZX = Z_control ⊗ X_target`. In Qiskit label notation these can be regarded as control = qubit 1, target = qubit 0. This is not the argument order of Qiskit's `cx(0,1)`.

Pauli X = [[0,1],[1,0]], Y = [[0,-i],[i,0]], Z = diag(1,-1). Preparations `X+`, `X-`, `Y+`, `Y-`, `Z+`, `Z-` refer to the signed eigenstates of these matrices. The handedness, signs, local phase frames, time origin, and time scale are **trusted**; there is no hidden axis rotation, unknown time offset, or control-label swap. The only preparation error is the positive isotropic visibility below. The binary readout contrast is strictly positive. Thus a hidden phase/sign gauge is not part of this task.

All times and angular frequencies are dimensionless reciprocal units; there is **no extra factor of 2π**. All parameters remain fixed within an episode. There is no drift, time rounding, pulse ramp, or unknown drive amplitude.

## Hamiltonian and channel

`H = (omega_ix IX + omega_zx ZX + omega_iz IZ + omega_zz ZZ + omega_zi ZI)/2`.

`U(t) = exp(-i t H)` is the exact exponential of the sum. The terms generally do not commute. For a control Z eigenvalue `s ∈ {+1,-1}`, define `a_s = omega_ix+s omega_zx`, `d_s = omega_iz+s omega_zz`, `r_s = sqrt(a_s²+d_s²)`. The corresponding target block is

`U_s(t) = exp(-i s omega_zi t/2) [cos(r_s t/2) I - i (sin(r_s t/2)/r_s)(a_s X+d_s Z)]`.

The zero-frequency limit of `sin(r_s t/2)/r_s` is `t/2`. The relative phase between the two blocks matters for superposed control preparations; the ZI coefficient is not observable using only control Z eigenstates and target-only readout.

For preparation axes A, B and signs a, b, with visibility v:

`rho_prep = [(I+a v A)/2] ⊗ [(I+b v B)/2]`.

Evolution includes a global depolarizing semigroup with rate gamma:

`rho(t) = exp(-gamma t) U(t) rho_prep U(t)† + (1-exp(-gamma t)) I_4/4`.

This is exactly the solution of `dot(rho) = -i[H,rho] + gamma (I_4 Tr(rho)/4-rho)`. It is a deliberately specified, completely positive effective decoherence model, not a claim that transmons have only global depolarization or that local amplitude damping commutes with this H.

For any allowed nonidentity Pauli product M, the positive-outcome probability is

`p_plus = [1 + readout_bias + readout_contrast Tr(M rho(t))]/2`.

This specifies a **binary parity meter**, including when M has weight two. It is not a model of two separately corrupted readout bits. Its classical confusion probabilities are `P(reported+ | ideal+)=(1+bias+contrast)/2` and `P(reported+ | ideal-)=(1+bias-contrast)/2`; the public bounds ensure both are valid. The observed count is exactly `Binomial(shots,p_plus)`, conditionally independent across queries. No underlying probability, shot record, or hidden parameter is returned.

## Parameters and scoring

The parameter order and inclusive bounds are in `config.json`. The nuisance order is `[prep_visibility, readout_contrast, readout_bias, decay_rate]`. Contrast and visibility are positive, with no negative-contrast sign ambiguity. Both single- and two-qubit observables are available, so preparation and measurement contrast need not be conflated: at zero time their amplitudes are proportional to `contrast*v` and `contrast*v²` respectively.

For an estimate in the published Hamiltonian bounds, an episode's error is

`NRMSE = sqrt(mean(((estimate - true_omega)/[0.5,0.25,0.5,0.25,0.5])²))`.

These fixed calibration scales, not episode-dependent relative errors, emphasize the entangling coefficients without dividing by a near-zero true coefficient. The aggregate is the arithmetic mean of episode NRMSEs; the worst-family score is the largest of the four family means. Smaller is better. Passing requires both inequalities in `config.json` and valid completion of all 32 episodes. Invalid episodes receive NRMSE = 30 and fail validity. The maximum error of any two in-bounds coefficient vectors is below 30. Reported core score equals mean NRMSE, not a differently normalized reward. Runtime is reported separately and is not traded against accuracy; the hard limits always apply.

`resource_score` is the fraction of episodes completing protocol-validly within all hard resource limits, in `[0,1]`. It does not compensate for recovery error. Sandbox startup failure is reported as an infrastructure error with no quality score, not as a hard calibration episode. Solver and startup wall times are reported separately.

The task does not claim that the target has been achieved. See baseline measurements for empirical context; the achievable frontier remains open unless a separately validated controller passes. Independent dense-exponential checks and full nine-parameter Jacobian-rank checks are part of the private evaluator selftests.
