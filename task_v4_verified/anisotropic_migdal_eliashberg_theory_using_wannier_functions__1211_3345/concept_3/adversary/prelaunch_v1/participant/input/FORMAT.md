# Format and mathematical contract — version 1

All energy variables are in units E0 = 2 meV; kB = 1. The common temperature
is 0.04 E0. All stored numeric arrays are float64 except integer indices and
family labels. Load with `allow_pickle=False`. Batch size is arbitrary; do
not assume row order or identify a row by its position.

## Files

`train_features.npz` / `train_labels.npz`: 384 paired examples, 96 per family.
`validation_features.npz` / `validation_labels.npz`: 64 independent paired
examples, 16 per family. Hidden evaluation uses 64 further independent
examples, 16 per family, with a fresh random permutation. All splits use
the **same** sampler, parameter bounds, quadrature, noise law, and resolution;
there is no hidden parameter extrapolation or sample rejection.

Input archive keys:

| Key | Shape | Meaning |
| --- | --- | --- |
| `observed` | (B,2,2,N) | dimensionless noisy normal/anomalous data |
| `sigma` | (B,2,2,N) | marginal Gaussian standard deviations |
| `omega` | (N,) | positive Matsubara energies |
| `matsubara_indices` | (N,) | integer fermionic indices |
| `temperature` | () | 0.04 |
| `noise_correlation` | () | 0.4 |
| `probe` | (2,3) | fixed orbital-projection factors |
| `bin_edges` | (15,) | last edge is positive infinity |
| `resolution` | () | extra Lorentzian HWHM 0.4 |
| `format_version` | () | integer 1 |

N = 64. Indices are the sorted union of 0,...,23 and the rounded 40-point
geometric sequence from 25 to 511, as constructed in `generator.py`.
omega_n = (2 n + 1) pi T. Index gaps do not change the noise law: correlation
is defined along **stored frequency position**, not the integer index.
Probe order is fixed; channel 0 is -omega Im G_11(i omega), and channel 1
is -omega Re F(i omega). There are no noisy imaginary components of F.

Label archives contain `spectral_mass` (B,2,14) and `family` (B,) in 0,...,3.
**Output**: exactly one NPZ key, `spectral_mass`, shape (B,2,14), a real numeric
array, every entry in [0,1], summing to one along the last axis within 1e-6.
NaN, Inf, complex/object arrays, missing/extra keys, wrong shapes, symlinks,
oversized archives, unsuccessful exit, and timeout invalidate the submission.

## Complete finite-quadrature spectral family

The definitions below, including quadrature, define the mathematical model
exactly. This is a many-mode, anisotropic BCS/Nambu spectral surrogate with
positive phonon-like replicas. It is not claimed to solve the nonlinear
Migdal–Eliashberg equations. In particular the replicas phenomenologically
represent incoherent quasiparticle weight, not a fitted alpha^2 F.

Let u_0,...,u_31 be independent Uniform[0,1] variables. Unused entries are
ignored. Family f is balanced across each split. Families 0,1,2 have two
sheets and family 3 has three. Names are respectively `split_coherence`,
`overlapping_anisotropy`, `satellite_rich`, and `three_sheet`.

For two sheets w=(0.25+0.5u_0, 0.75-0.5u_0). For three sheets,
w_0=0.18+0.3u_0, w_1=(1-w_0)(0.3+0.4u_1), w_2=1-w_0-w_1.
Probe factors P=[[1,1,1],[0.45,1,1.65]], restricted to active sheets;
v_pb = P_pb w_b / sum_c P_pc w_c. The second probe is a different positive
orbital mixture, **not** a measured sheet-resolved spectrum.

Use theta_j=2pi(j+1/2)/16, j=0,...,15. Let (x_l,q_l) be the 32-point
Gauss–Legendre rule on [0,1], so sum_l q_l=1. It represents the symmetric
normal-state dispersion +/- W_b x_l. Each theta has weight 1/16.
The finite rule is part of the known model, not an undisclosed discretization.

For each sheet b, write t_k=u_(6+8b+k), k=0,...,7. Its mean gap d_b is
uniform on the following interval by affine interpolation with t_0:

| Family | Sheet 0 | Sheet 1 | Sheet 2 |
| --- | --- | --- | --- |
| 0 | [0.65,1.25] | [1.8,3.1] | absent |
| 1 | [1.0,1.8] | [1.55,2.6] | absent |
| 2 | [0.8,1.5] | [1.8,2.9] | absent |
| 3 | [0.6,1.2] | [1.35,2.1] | [2.35,3.2] |

Define a_b=0.04+0.30t_1 for family 1, otherwise 0.015+0.18t_1;
c_b=-0.09+0.18t_2; W_b=4.5+2.5t_5;
Delta_bj=d_b[1+a_b cos(2theta_j)+c_b cos(4theta_j)];
E_bjl=sqrt[(W_b x_l)^2+Delta_bj^2]; h_bjl=Delta_bj/E_bjl.
All gaps are strictly positive. Lifetime gamma_b=0.025+0.13t_3 in family 1,
otherwise 0.025+0.075t_3.

There are three replica indices r=0,1,2. Global shifts are
Omega=(0,3.2+2.3u_2,6.7+3.3u_3) and angular dispersions
D=(0,0.1+0.5u_4,0.15+0.75u_5). For family 2 set
s_b1=0.15+0.18t_6, s_b2=0.07+0.11t_7; otherwise
s_b1=0.025+0.13t_6, s_b2=0.01+0.09t_7. Set s_b0=1-s_b1-s_b2.
All replica weights are positive. For each component k=(b,j,l,r),

    e_k = E_bjl + Omega_r + D_r cos(2theta_j + 0.3b)
    gamma_k = gamma_b[1+0.55t_4 cos(2theta_j+0.7)] + 0.025x_l^2 + 0.13r
    h_k = h_bjl
    m_pk = v_pb s_br q_l / 16.

All e_k and gamma_k are positive, 0<h_k<=1, m_pk>=0, sum_k m_pk=1.
Define positive-semidefinite Nambu residues
R_k^+ = (I+h_k tau_x)/2 and R_k^- = (I-h_k tau_x)/2. They are the
average of the usual BCS projectors at opposite normal dispersions. For
Im z>0, the retarded Green matrix is

    Ghat_p(z) = sum_k m_pk [R_k^+/(z-e_k+i gamma_k)
                           + R_k^-/(z+e_k+i gamma_k)].

Thus the matrix spectral measure -Im Ghat/pi is positive semidefinite,
integrates to I, has particle-hole symmetry, is analytic in the upper half
plane, and has z Ghat(z) -> I. Finite lifetimes give Lorentzian tails; no
compact spectral support or finite second-moment assumption is made.
The anomalous component is odd in real-axis spectral energy and need not
itself be a positive scalar measure. On the imaginary axis,

    X_p0n = sum_k m_pk omega_n(omega_n+gamma_k)
                       / [(omega_n+gamma_k)^2+e_k^2]
    X_p1n = sum_k m_pk omega_n h_k e_k
                       / [(omega_n+gamma_k)^2+e_k^2].

These are the exact clean data behind `observed`. Each case draws a noise
amplitude A log-uniformly on [1e-6,4e-6]. The reported marginal sigma is
A (1+0.35c)[0.6+0.4/(1+omega_n/6)] for channel c, equal across probes.
Independently for each case/probe/channel, draw epsilon_0~N(0,1),
epsilon_j=0.4 epsilon_(j-1)+sqrt(1-0.4^2) z_j with independent z_j~N(0,1).
Observed X = X_clean + sigma epsilon. No calibration drift is hidden.

## Real-axis target and resolution

The electron DOS per normalized probe is rho_p(E)=-Im G_p,11(E+i0)/pi.
It is even and integrates to 1 over the whole real line. The scored density
is the Lorentzian-convolved DOS with **additional HWHM eta=0.4 E0**; its
instrumental FWHM is 0.8 E0 = 1.6 meV. Targets are the weights in symmetric
energy windows, integrating the resolved density over a<=|E|<b. Edges are

    [0, .75, 1.25, 1.75, 2.25, 2.75, 3.5, 4.5, 6, 8, 10, 13, 17, 23, infinity].

They describe subgap filling, gap/coherence regions, and broad satellite
weight. They do **not** ask for peak locations or unsmoothed peak heights.
For each component let H=gamma_k+eta and

    C(t;e,H) = [atan((t-e)/H)+atan((t+e)/H)]/pi,
    C(0)=0, C(infinity)=1.
    target_pj = sum_k m_pk [C(edge_(j+1);e_k,H)-C(edge_j;e_k,H)].

The final tail bin must be included. Every probe's target sums exactly to 1.

## Fixed score

Let s_j=[.008,.008,.008,.008,.008,.008,.008,.010,.012,.012,.012,.010,.008,.006].
For each case i, error_i=sqrt(mean_(p,j) [(prediction-target)/s_j]^2).
Core is mean_i error_i. Worst-family is max_f mean_(i:family_i=f) error_i.
Tail is NumPy's linearly interpolated 90th percentile of case errors.
Success requires core<=1, worst-family<=1.25, tail<=1.75 **and** valid output
within the runtime/resource limits. All probes/windows have equal weight
after scaling. There is no leaderboard-dependent threshold or hidden bonus.

## Running public resources

From `participant/`:

    OPENBLAS_NUM_THREADS=1 python baseline/solve.py --input input/validation_features.npz --output workspace/prediction.npz
    OPENBLAS_NUM_THREADS=1 python input/generator.py --seed 123 --per-family 16 --output-dir workspace/synthetic

Generator seeds in examples are public and are never hidden-test seeds.
In evaluation, `ALE_PUBLIC_INPUT` is the absolute public resource directory;
candidate working directory is scratch, not the submission directory. Use
`Path(__file__).resolve().parent` for packaged assets. Pure single-process
Python is required: no external executable, network access, or subprocess.
The sandbox enforces one thread, 180 CPU seconds, 4 GiB address space, with
a 3600-second wall ceiling. Hidden labels and family tags are retained by the parent evaluator. Neither
the family tag nor the generating parameters is a candidate input.

## Scientific provenance and limitation

Margine and Giustino, *Anisotropic Migdal–Eliashberg theory using Wannier
functions*, arXiv:1211.3345 (2012), II.3 and III.2 motivate recovering
real-axis superconducting behavior from imaginary-axis functions. The paper
discusses approximate Padé and more expensive iterative continuation. The
present distribution and forward map are original benchmark definitions;
they are not the paper's EPW data. Causality and sum rules follow from the
positive Nambu residues above, independently of any continuation algorithm.

Identifiability at the scored resolution is audited privately against this
specific family/noise law. The finite resolution is not a claim that arbitrary
causal spectra can be uniquely inferred from finitely many noisy observations.
