# Correlated Ramsey protocol v1

## 1. Physical model and units

There are two labeled qubits; exchanging their labels is not a symmetry of the actions. In units with time in microseconds and ordinary frequencies in MHz,

`H / hbar = pi * (f1 Z1 + f2 Z2 + coupling Z1 Z2)`.

During one shot the Hamiltonian additionally contains `(delta1 Z1 + delta2 Z2)/2`. The angular-frequency offsets are jointly Gaussian, with mean zero, standard deviations `sigma1`, `sigma2` in radians/microsecond, and correlation `rho`. Each pair is constant during that shot and independently redrawn for every new shot. There is no drift, inter-shot memory, or unmodeled noise. The evaluator integrates this Gaussian noise exactly, then samples the resulting binary probability. It does not draw one shared offset per batch.

Ideal preparation and known analysis rotations are available. Effective preparation/readout visibility and offset are represented by the physical noisy equatorial readout observable

`A_i(phi) = bias_i I + visibility_i (cos(phi) X_i + sin(phi) Y_i)`.

Its two POVM effects are `(I +/- A_i)/2`. All permitted parameters satisfy `abs(bias_i)+visibility_i < 1`. This is an **effective SPAM** model: only the displayed visibility/offset combinations are to be estimated, not an unidentifiable decomposition into preparation and measurement errors. The spectator preparation and available Bell preparation are assumed ideal. There are no unknown control-angle or spectator-preparation errors. Local readout channels act independently; correlated noise is in the Gaussian evolution channel, not an extra correlated detector error.

The parameter order used by the Python simulator is:

| Name | Global allowed range | Unit |
| --- | --- | --- |
| `f1`, `f2` | [0.25, 2.15] each | MHz |
| `coupling` | [0.015, 0.22] | MHz |
| `sigma1`, `sigma2` | [0.08, 0.46] each | radians/microsecond |
| `rho` | [-0.90, 0.90] | dimensionless |
| `visibility1`, `visibility2` | [0.48, 0.90] each | dimensionless |
| `bias1`, `bias2` | [-0.09, 0.09] each | dimensionless |

## 2. Action space and exact probabilities

An action chooses a mode, a real time in `[0,6]`, a real analysis phase in `[-pi,pi]`, and an integer shot count in `[1,1024]`. Time and phase are continuous binary64 numbers, not a prescribed grid. There is no extra time cost beyond the query and shot budgets. Each action returns only the number of positive and negative outcomes.

Every mode has positive-outcome probability

`p = (1 + B + V exp(-D time^2/2) cos(2 pi F time - phase))/2`.

| Mode | Preparation and observation | F | D | V | B |
| --- | --- | --- | --- | --- | --- |
| `q1+` | qubit 1 in `+X`, spectator 2 has `Z=+1`; read qubit 1 | `f1+coupling` | `sigma1^2` | `visibility1` | `bias1` |
| `q1-` | same, spectator `Z=-1` | `f1-coupling` | `sigma1^2` | `visibility1` | `bias1` |
| `q2+` | qubit 2 in `+X`, spectator 1 has `Z=+1`; read qubit 2 | `f2+coupling` | `sigma2^2` | `visibility2` | `bias2` |
| `q2-` | same, spectator `Z=-1` | `f2-coupling` | `sigma2^2` | `visibility2` | `bias2` |
| `bell+` | `(00+11)/sqrt(2)`; parity of `A1(phase)` and `A2(0)` | `f1+f2` | `sigma1^2+sigma2^2+2 rho sigma1 sigma2` | `visibility1 visibility2` | `bias1 bias2` |
| `bell-` | `(01+10)/sqrt(2)`; same parity observation | `f1-f2` | `sigma1^2+sigma2^2-2 rho sigma1 sigma2` | `visibility1 visibility2` | `bias1 bias2` |

For Bell modes, positive means positive parity; the individual detector bits are not returned. The coherent ZZ term cancels in the Bell coherences. At time zero, appropriate phases distinguish SPAM offsets and visibility. Local modes alone cannot determine `rho`. All unknowns are identifiable using the available continuous-time, phased local and Bell actions; small finite datasets can still have separated frequency-alias likelihood modes.

`simulator.probabilities(theta, actions)` returns positive probabilities. Actions passed to this numerical helper need only `mode`, `time`, and `phase`. With `jacobian=True`, it returns `(probabilities, derivative)` in the stated parameter order. `sample_prior(family, numpy_rng)` generates a public training parameter vector. You may simulate as many local synthetic examples as fit your compute allocation; they do not reveal hidden outcomes.

## 3. Disclosed prior families

`U(a,b)` means a continuous uniform distribution. Unless a dependence is stated, all draws within a family are independent. Each hidden family has exactly six independently generated parameter vectors. Episode order is fixed and shuffled, and neither index nor family is sent to the strategy. Bounds on final estimates are the global ranges, not the narrower family supports.

| Draw | `resolved` | `close_coupled` | `low_visibility_spam` |
| --- | --- | --- | --- |
| Frequencies | draw `f1,f2` independently from `U(.35,2.05)`; reject the pair until `abs(f1-f2)>=.35` | `f1~U(.45,1.90)`; `f2=f1+U(.025,.10)` | same independent frequency draws as resolved, but reject until gap is at least `.15` |
| Coupling | `U(.025,.16)` | `U(.10,.20)` | `U(.025,.20)` |
| Each sigma | `U(.10,.28)` | `U(.16,.34)` | `U(.24,.44)` |
| Correlation | `U(-.65,.65)` | equiprobable sign times `U(.40,.85)` | `U(-.85,.85)` |
| Each visibility | `U(.78,.90)` | `U(.68,.88)` | `U(.50,.68)` |
| Each bias | `U(-.06,.06)` | `U(-.08,.08)` | `U(-.085,.085)` |

Public examples use different, disclosed seeds. The hidden parameter vectors, their generation seeds, and outcome seeds remain evaluator-only. There is no additional hidden family, noise channel, or measurement option. The suite is not regenerated per submission. Repeated actions in an episode obtain new independent shot samples, not cached counts.

## 4. Process interface

The evaluator launches `[python, -u, solution.py]` in a fresh temporary submission directory, with a fresh `input/` copy. A strategy may import that local simulator. One process lives for the entire episode; there are 18 launches for the hidden suite, not one launch per query. Submission modules are never imported by the evaluator.

Initial input has `type="start"`, `protocol="correlated-ramsey-v1"`, `budget`, `wall_seconds`, `cpu_seconds`, `memory_mib`, `bounds`, `modes`, `time_range`, `phase_range`, `families`, and `remaining`. `simulator.metadata()` gives the complete structure. No seed, truth, episode identifier, or family label is included.

Reply with exactly these keys for an experiment:

```json
{"type":"experiment","mode":"q1+","time":0.73,"phase":1.5707963267948966,"shots":128}
```

The next input is, for example:

```json
{"type":"observation","action":{"type":"experiment","mode":"q1+","time":0.73,"phase":1.5707963267948966,"shots":128},"counts":[72,56],"remaining":{"queries":47,"shots":6016}}
```

The displayed counts are illustrative, not a hidden observation. `counts[0]` is positive and `counts[1]` negative. Their sum is exactly the requested number of shots. An action costs one query regardless of its shot count. You may use fewer than the available queries or shots, but may never exceed either budget. Once either budget is exhausted, the next response must be an estimate.

End with exactly the following structure, using your own estimates:

```json
{"type":"estimate","parameters":{"f1":1.0,"f2":1.2,"coupling":0.1,"sigma1":0.2,"sigma2":0.25,"rho":0.0,"visibility1":0.8,"visibility2":0.8,"bias1":0.0,"bias2":0.0}}
```

All ten keys are required and extra keys are rejected. Numbers must be finite JSON numeric values, not booleans or numeric strings. Duplicate JSON keys, `NaN`, infinities including `1e309`, malformed JSON, and out-of-range values are rejected. Emit one newline-terminated response for each received message. Do not pipeline queries or print explanations to stdout. Maximum response line: 16,384 bytes. Exit with status zero within one second of the final estimate and within the episode wall limit; no trailing output is allowed. Stderr is discarded by the evaluator.

The wall clock spans the episode interaction, including fitting. CPU/address-space/file-size/open-file limits apply to the process. Numeric libraries run with one thread. There is no persistent state shared between episode working directories. The integration harness may additionally isolate filesystems, processes, and networking. Direct access to private evaluator state is prohibited regardless of local runner configuration.

## 5. Exact objective

For parameter order above, the scale vector is

`s = [.025, .025, .018, .075, .075, .32, .09, .09, .065, .065]`.

Let `L_param = mean(min(((estimate-truth)/s)^2,16))`, averaging all ten coordinates. The predictive grid is **all six modes**, **49 equally spaced times from 0.125 through 6.0 inclusive**, and phases **0 and pi/2**, for 588 equally weighted probabilities. There are no fresh sampled outcomes in this predictive score. Let `L_pred` be the mean squared difference between the estimated and true positive probabilities on this grid.

`episode_score = 100 exp(-0.45 L_param - 0.55 L_pred / 0.04^2)`.

All calculations use float64. `simulator.score_estimate` is the executable specification. This criterion rewards both coherent identification and useful prediction, while retaining explicit penalties for poorly identified SPAM/correlation parameters. It does not average or forgive label permutations.

The overall mean averages all 18 episode scores, including zeros for invalid episodes. The worst-family score is the minimum of the three family means, each over six episodes. A hidden submission passes if and only if every episode is valid, mean is at least `OBJECTIVE.json:target.mean`, and worst-family mean is at least `OBJECTIVE.json:target.worst_family`. The target is frozen before any fresh-agent attempt. Runtime is reported, and exceeding a per-episode resource limit is an invalid episode. There is no additional leaderboard weighting or secret threshold.

`--public` uses one disclosed example from each family and the same score/resource limits; a public pass is only a smoke test and never substitutes for hidden evaluation.
