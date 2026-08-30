# Completed-champion robustness audit: generation 1 remains solved

All work here is private sidecar evidence. No participant, evaluator, target,
status, or generation file was edited. The completed champion still passes its
original contract. Standalone exhaustive calculations agree with its official
seven metrics within 2.21e-14. No ongoing fresh submission was inspected.

## Recommended option: one new operational condition, not a retroactive failure

A defensible new mode-B question is whether the same diagnostic false convergence
can occur when EVERY binary conditional is at least 0.001 and at most 0.999.
For this zero-bias architecture that is exactly row L1 <= ln(999). Keep the
original seven physical gates, beta interval, binary disorder and witness freedom.
Do not stack entropy, correlation, narrow-beta, or disorder-invariance gates merely
to remove the champion. This is a strengthened deployment condition, not evidence
that the old valid witness was invalid. A local conditional floor does not imply
a lower bound of 0.001 on a many-spin sector or guarantee global exploration.

No passing witness for the proposed floor has been established by this audit.
Launching it is defensible ONLY as an explicitly open construction mission, not
as a calibrated known-solvable task. Preserve generation 1 as solved; if a known
solvable next task is required, retain the solved task pending feasibility work.

## Actual champion: floor and beta evidence

The actual completed champion has beta=1.6, conditional floor about 0.000101029,
variance 0.016994462 and gradient infinity 0.000484875. Scaling all rows gives:

| Floor | Variance at beta=1.6 | Gradient infinity | Minimum variance over all beta in [1,3] |
| --- | ---: | ---: | ---: |
| 0.0001 | 0.01683208 | 0.000479936 | 0.01541498 |
| 0.0003 | 0.05097444 | 0.001439424 | 0.03590304 |
| 0.001 | 0.20183382 | 0.004793600 | 0.08705849 |
| 0.003 | 0.77175959 | 0.014342400 | 0.20024597 |
| 0.01 | 3.40788213 | 0.048570019 | 0.72351066 |

These continuous-beta minima are not grid guesses: for fixed q,
Var_q(beta E + log q) = beta^2 Var_q(E) + 2 beta Cov_q(E,log q)
+ Var_q(log q). Its clipped quadratic minimizer gives the reported minimum.
For floor 0.001 it occurs at beta=1.057922335 and still exceeds 0.05.
At floor 0.0003, changing beta restores all gates on the tested 0.05-spaced grid
from 1.20 through 1.55. Thus 0.0003 is not a substantive obstruction to this
champion. At floor 0.0001 it passes from 1.20 through 2.30 on that grid.

## A construction-level obstruction, not just a parameter-vector failure

Consider the champion's structural method: four nonadjacent unbiased free spins,
one unbiased backbone root, and the other eleven backbone spins independent
conditional on that root. The reference backbone alignment and all 16 free-spin
assignments form a ground-state coordinate cube; also include its spin reversal.
Let epsilon be a lower bound on every copy's two outcome probabilities.

No backbone vertex can neighbor more than two free spins. If it had d>=3 free
neighbors, flipping that vertex costs at most 2(4-d) on backbone bonds. Retuning
its d free neighbors lowers their previously zero-field energy by 2d. The net
change is at most 8-4d<0, contradicting ground-state membership. This argument
uses unit bond magnitudes and the independence of the free-site set.

Condition on all backbone spins. The free-spin contribution to reward has
conditional variance beta^2 sum_f h_f^2. Each free field h_f is a sum of four
signed backbone spins. Given the root, the other backbone spins are independent
and each has variance at least 4 epsilon(1-epsilon). At most two of the sixteen
free-to-backbone edges meet the root. The law of total variance therefore gives

    Var_q(R) >= 14 * 4 * beta^2 * epsilon * (1-epsilon).

At epsilon=0.001 and beta>=1, this is at least 0.055944 > 0.05. Thus changing
binary couplings, root, copy probabilities, or beta cannot rescue THIS four-free,
independent-copy ground-cube method under the proposed floor. It does not rule
out general triangular VANs, correlated or biased free spins, different basin
geometry, or another construction. In particular, this is not a general
impossibility theorem for the strengthened mission.

An exhaustive integer check of all 65,536 free-site subsets additionally shows
that nonadjacency plus the necessary at-most-two-free-neighbors condition allows
at most four free sites on this torus. Counts by free dimension 0..4 are
1,16,88,144,36; dimensions >=5 have zero candidates. Consequently the saturated
copy/unbiased-ground-cube template at epsilon=0.0001 has maximum entropy
5 ln(2) + 11 h(0.0001) = 3.47696722. This is not a bound on general VAN entropy.

## Generic disorder does NOT eliminate the method

For each amplitude, 32 independent continuous relative-magnitude perturbations
were used, with mean magnitude exactly 1 and each magnitude in [1-delta,1+delta].
Signs and frustrated plaquettes are preserved. All 160 perturbed champion
Hamiltonians have only the spin-flip pair of ground states within 1e-9 numerical
tolerance, so the large exact ground degeneracy is lifted.

At 1% perturbations the unchanged champion fails the gradient gate in 32/32
trials. However, changing just the four former free-spin/root weights to their
conditional fields restores ALL seven metric gates in 32/32 trials. The same
adjustment succeeds in 32/32 at 0.1%, 0.3%, and 3%, and 26/32 at 10%.
At 1% the median adjusted variance is 0.01701047 and gradient is 0.000485643.
These nonbinary Hamiltonians are outside the original submission schema: the
reported successes concern its physical metric inequalities, not official
structural validity. Requiring the SAME q to stay stationary after changing its
Hamiltonian would test parameter invariance, not absence of the collapse method.

## Entropy and correlation feasibility survey

The seeded survey covers 512 admissible random binary torus models at beta=1.
Observed target entropy ranges from 1.299203 to 6.448072 nats; median 4.038253.
The maximum ground-cube free dimension distribution is 0:85, 1:202, 2:180,
3:44, 4:1. This is a sample, not an exhaustive bound on target entropy.

For any fixed model, equilibrium entropy decreases with beta. Also the original
energy and KL gates imply H(q) <= H(p)-0.08, since
D(q||p)=E_q U-E_p U+H(p)-H(q), |E_q U-E_p U|<=0.32, and D>=0.4.
Raising the proposal entropy target to 6.5 is unsupported by this survey; random
sampling does not prove it impossible. The observed high-entropy tail shows that
moderately higher entropy is not immediately excluded, but supplies no full VAN
witness meeting the strengthened simultaneous gates.

510/512 models have some radius-4 antipodal sector of mass at least 0.35. One
explicit saved model has target entropy 6.265936, sector mass 0.440946, sector
conditional entropy 5.206908, and entropy 4.513761 after selecting one of the two
antipodal balls. That oriented sector's total correlation is 1.992109 nats.
Hence high-entropy, nonproduct equilibrium sectors really exist. Correlation
induced by conditioning on a Hamming ball must not be misrepresented as an
unconditional physical-correlation certificate. Neither this example nor the
survey proves that a VAN can miss that sector while passing all other gates.

## Reproducible evidence

- `audit.py`: private-witness sweeps and seeded 512-model survey, 35.0 seconds.
- `champion_audit.py`: completed-champion crosscheck, floor/beta/disorder audit,
  17.2 seconds; no evaluator imports.
- `ground_cube_bound.py`: exhaustive necessary-geometry check.
- `champion_summary.json`, `champion_floor_summary.json`,
  `champion_beta_profiles.json`, `champion_bond_perturbations.json`.
- `summary.json`, `binary_instance_survey.json`, `ground_cube_geometry.json`.

The recorded frozen-file audit reports no changed participant/evaluator/test
files. The original champion SHA-256 is
`b2db21f2d2e32ae5d68dd60e319968ddad2fa29e2ffd20b2939d2e66eb66e478`.
