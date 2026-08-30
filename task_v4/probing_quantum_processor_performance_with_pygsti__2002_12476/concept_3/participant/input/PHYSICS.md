# Disclosed device distribution

This is synthetic system identification, not a claim about a particular hardware
platform. The motivation is the distinction between a fitted stationary gate set
and a useful predictive model in *Probing quantum processor performance with
pyGSTi*, sections V.A.4, V.B.4, V.B.7, and V.C. No pyGSTi installation is needed.

## Experimental semantics

Four independently sampled, fixed devices (IDs 0, 1, 2, 3) share exactly the model
class below. Parameters do not change between splits. Each row describes many
independent shots of one circuit at a known normalized acquisition time `time`.
Time is constant during a circuit. Each shot resets the qubit, the two-component
deterministic pulse memory to zero, and the classical environment to its specified
time-dependent distribution. No state persists across rows or shots. Row order
does not convey additional history. Counts are independent binomial draws.

Preparations are the six Bloch vectors `+X,-X,+Y,-Y,+Z,-Z`, multiplied by the
**known** purity 0.985. Measurements are along **known** positive X, Y, or Z axes.
Readout false-one probability is 0.008, and false-zero probability is 0.013,
identical for all devices. These preparation and measurement operations are not
members of the noisy circuit alphabet and do not update memory.

The five unit-duration gates, executed left to right, are:

| code | ideal action | pulse input `(u_x,u_y)` |
|---|---|---|
| 0 | identity | (0,0) |
| 1 | +pi/2 about X | (1,0) |
| 2 | -pi/2 about X | (-1,0) |
| 3 | +pi/2 about Y | (0,1) |
| 4 | -pi/2 about Y | (0,-1) |

Use the right-handed Bloch convention: a positive X rotation sends +Z toward -Y.
`R(v)` denotes the 3D rotation by angle `norm(v)` around axis `v/norm(v)`;
`R(0)=identity`. Angles are radians.

## Hidden but fixed physical parameters

There are 54 continuous parameters per device. All draws below are independent
uniform draws over the stated intervals, including separate array entries. The
four actual draws and all random seeds are private. No additional selection by
hidden test performance was applied. Bounds and parameterization are public so
the difficulty is inference and prediction, not discovering missing physics.

| parameter | shape | sampling interval |
|---|---|---|
| `gate_bias` | (5,3) | [-0.018, 0.018] |
| `latent_vector` | (3,) | X,Y: [-0.008,0.008]; Z: [0.028,0.062] |
| `memory_matrix` | (3,2) | X,Y rows: [-0.030,0.030]; Z row: [-0.070,0.070] |
| `retention` | (2,) | [0.82,0.97] |
| `drift_sin`, `drift_cos` | (3,) each | X,Y: [-0.009,0.009]; Z: [-0.018,0.018] |
| `frequency` | scalar | [0.8,1.5] cycles across the acquisition interval |
| `transition` | (2,4) | column 0: [-5.8,-3.8]; 1: [-0.8,0.8]; 2: [-1.1,1.1]; 3: [-0.5,0.5] |
| `reset` | (3,) | coefficient 0: [-0.8,0.8]; 1: [-1,1]; 2: [-0.7,0.7] |
| `gamma` | (5,) | [0.0001,0.0012] |
| `depolarization` | (5,) | [0.0001,0.0009] |

## Within-shot evolution

The classical state is `state in {0,1}`, with signs -1 and +1 respectively.
Initially, `Pr(state=1) = sigmoid(reset dot [1, 2*time-1, sin(2*pi*time)])`.
Pulse memory `memory=(0,0)` is deterministic given the pulse history.

For each gate `gate`, in this exact order:

1. In each classical state, apply the ideal gate to the qubit Bloch vector,
   followed by the error rotation `R(error)`, where

   `error = gate_bias[gate] + sign(state)*latent_vector`

   `        + memory_matrix @ memory`

   `        + drift_sin*sin(2*pi*frequency*time)`

   `        + drift_cos*cos(2*pi*frequency*time)`.

2. Apply amplitude damping toward +Z with rate `gamma[gate]`: X and Y multiply
   by `sqrt(1-gamma)`, and Z becomes `(1-gamma)*Z + gamma`. Then depolarize:
   multiply all three Bloch coordinates by `1-depolarization[gate]`.

3. Update the classical state independently of the quantum state conditional on
   its current classical state. Define

   `features = [1, gate != 0, memory_x-memory_y, sin(2*pi*time)]`.

   `p01 = sigmoid(transition[0] dot features)`;
   `p10 = sigmoid(transition[1] dot features)`.

   The row-stochastic transition matrix is `[[1-p01,p01],[p10,1-p10]]`.
   Crucially, quantum states conditioned on the classical state are generally
   different: mixing must retain their correlations. Each branch applies a
   completely positive trace-preserving qubit channel, and transition weights
   are always probabilities.

4. Set `memory = retention*memory + (1-retention)*pulse_input[gate]`
   elementwise. The rotation and transition above used the **old** memory.

After the last gate, marginalize the environment. For the resulting normalized
Bloch vector `bloch` and unit measurement vector `axis`, the reported outcome-one
probability is

`0.008 + (1-0.008-0.013)*(1-axis dot bloch)/2`.

An exact physical forward model exists, but parameter recovery is an inverse
problem with correlated latent branches, multiple timescales, drift, finite-shot
noise, and long-circuit phase sensitivity. The true parameters are not supplied.

## Characterization and shift

Every device has full six-preparation/three-measurement empty and single-gate
calibration at nine times, plus 6,144 circuit observations. Non-calibration rows
include random words and all four scored families. Most training lengths are
4--96; one quarter are 112--192. Training acquisition times are the 17 equally
spaced points in [0,1]. Calibration rows have 32,768 shots; other training rows
have 8,192 or 16,384 shots. There are 128 development and 512 test queries in
each device/family cell. Development lengths are 144--288 with 65,536 shots;
test lengths are 288--512. Some shortest realizations differ slightly because
complete motifs are retained. Development and test times are independent
continuous draws inside [0.02,0.98], never future-time extrapolations.

The announced families are `germ_repetition` (short motifs repeated many times),
`refocusing` (idle intervals and signed pi/2 pulse pairs), `burst_switching`
(long runs of different signed controls), and `drift_transfer` (these structures
at independently drawn acquisition times, with varied prefixes and suffixes).
Preparations, measurements, complete gate strings, times, devices, and family
names are public for every query. Both development and test draw from these
same construction rules, with greater test depth; no unknown family or mechanism
is introduced. Query generation is independent of the device parameters.
