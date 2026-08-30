# Device and executable protocol

Sites are 0,...,5 on a periodic ring. A one bit means spin up. Evolution stays
in the three-up-spin sector; states are ordered by increasing integer bit mask.
Write z_i=n_i-1/2. The Hamiltonian (hbar=1) is

```
H = sum_i J_i [ (S+_i S-_(i+1) + S-_i S+_(i+1))/2
                + Delta z_i z_(i+1) ]
  + sum_i K_(i mod 2) [ (S+_i S-_(i+2) + S-_i S+_(i+2))/2
                       + Delta z_i z_(i+2) ]
  + sum_i h_i z_i .
```

Each of the six first-neighbor and six second-neighbor bonds occurs once.
The independent parameter vector is in this order:

```
J0,J1,J2,J3,J4,J5, h0,h1,h2,h3,h4, Delta,K0,K1, e0,e1,e2,e3,e4,e5
```

`h5 = -sum(h0,...,h4)`. Parameter ranges are in `config.json`. Detector bit i
flips independently with probability e_i after the final computational-basis
measurement. Recorded outcomes therefore range from 0 to 63, including masks
outside the evolution sector. There are no other nuisance parameters.

At startup stdin supplies one JSON line with `type="start"`, `config` containing
the public config, and an arbitrary `device_id`. Do not infer parameters from
that identifier. Emit one JSON object per line, flushing output. Diagnostics
belong on stderr. To request an experiment, output

```
{"type":"query","preparation":21,"time":2.3,"phases":[0,0,0,0,0,0]}
```

`preparation` is any six-bit mask with three set bits. `time` is in [0,6].
There are six finite phases, each in [-pi,pi]. The device prepares that basis
state, evolves under H for time/2, applies exp(-i sum_i phases_i n_i), and
evolves for time/2 again. It returns a JSON line

```
{"type":"observation","counts":[...64 nonnegative integers...],"remaining":17}
```

Counts are multinomial with the configured shot count. The physical parameters
remain fixed through the interaction. Randomness is independent between
experiments. A query may be repeated and still costs one experiment. After
at most the query budget, output

```
{"type":"answer","parameters":[...20 finite values...]}
```

Answers must lie within the stated inclusive ranges. Per-device error is
sqrt(mean(((estimate-truth)/(upper-lower))**2)). Overall and regime errors are
means over devices, not pooled observations. Scores are 1-error, floored at
zero. All devices must finish validly to pass. The hidden suite covers smooth
near-uniform exchange, frustrated exchange, and strong field disorder, within
the same public parameter box. Regime membership is not supplied at runtime.

`workspace/physics.py` exports `LOWER`, `UPPER`, `STATES`, `hamiltonian`,
`probabilities`, and `predict_many`. `probabilities(parameters, experiment)`
returns the 64 exact observed-outcome probabilities, including detector error.
The local simulator accepts any admissible parameter vector, without a query
budget. The controller can import `physics` directly; evaluation puts the
supplied workspace on PYTHONPATH. Python 3, NumPy, and SciPy are available.
Evaluation starts a separate process for each device. No learned state carries
between hidden devices, but submitted model/data files may be used read-only.
