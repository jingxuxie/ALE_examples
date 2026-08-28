# Protocol v1

## Input and physical scope

All indices are zero-based on a periodic ring of even length `length`. Matter
site j and link j (joining j to j+1) are distinct two-level systems. Site and link
offsets in a channel are reduced modulo length. Every case supplies `id`,
`family`, `model`, `length`, `target`, `channels`, and `hardware`.

The task concerns first-order matrix elements from **every basis state in the
target sector**, not just one initial product state. It does not certify arbitrary
higher-order products of errors or the interacting time evolution. An error
channel is a separate physical mechanism. Its terms add coherently; different
channels are NOT summed together before testing reachability. Nonzero amplitude
size does not weight a constraint. All amplitudes are exact small binary
fractions, and cancellation tolerance is 1e-12.

Each channel is `{id, anchors, terms}`. An instance is `(id, anchor)`. Each term
is `{amplitude: [real, imag], ops: [[kind, offset, name], ...]}`. `kind` is `m`
(matter) or `l` (link). Factors in a term act on distinct degrees of freedom and
commute. Omitted factors are identities. Terms need not individually be
Hermitian; the supplied entire channel is Hermitian. Do not append an extra
Hermitian conjugate. A channel may be gauge preserving or cancel exactly.

## Basis and matrices

Matter basis is `|0>, |1>` with occupation n. The operator matrices, with output
row and input column, are:

```
I      = [[1,0],[0,1]]
raise  = [[0,0],[1,0]]
lower  = [[0,1],[0,0]]
n      = [[0,0],[0,1]]
x      = [[0,1],[1,0]]
y      = [[0,i],[-i,0]]
z      = [[-1,0],[0,1]]
```

For `model="u1"`, links use this same table, with electric flux
`s_j^z=(2 b_j-1)/2`. The target is always zero and

```
G_j = (-1)^j [n_j + s^z_(j-1) + s^z_j]
P_j = G_j,                 H_protect / V = sum_j c_j P_j.
```

Thus target link bits determine `n_j=1-b_(j-1)-b_j`. Two adjacent link bits
equal to 1 are forbidden. Every locally fixed link assignment without that
forbidden pair extends to a target ring state by setting unfixed links to 0.
Check forbidden pairs even at a site not explicitly acted upon. In the physical
basis the matter coefficient is `(-1)^j c_j`; the coefficient of link Pauli z
is `[(-1)^j c_j+(-1)^(j+1)c_(j+1)]/2`. This is single-body protection.

For `model="z2"`, matter still uses the table above, but links use an electric-X
eigenbasis with eigenvalue `x_j=2 b_j-1`. Their laboratory operators are:

```
I      = [[1,0],[0,1]]
x      = [[-1,0],[0,1]]
z      = [[0,1],[1,0]]
y      = [[0,-i],[i,0]]
raise  = (x + i*y)/2 = [[-1/2,1/2],[-1/2,1/2]]
lower  = (x - i*y)/2 = [[-1/2,-1/2],[1/2,1/2]]
```

The supplied `target[j]=g_j` is +1 or -1. Define

```
G_j = (1-2*n_j) x_(j-1) x_j
W_j = x_(j-1) x_j + 2*g_j*n_j
P_j = W_j-g_j,             H_protect / V = sum_j c_j P_j.
```

Every link assignment extends uniquely to the target through
`n_j=(1-g_j*x_(j-1)*x_j)/2`. On target states W_j=g_j. Off target,
G_j and W_j are DIFFERENT: the same sector transfer can have different penalty
transfers. The protection requires one density term and one two-link XX term
per site, not single-body terms alone. No fixed total-particle-number restriction
is imposed in either model.

## Required certificate

For each nonzero matrix element `<out|channel|in>`, with `in` in the target,
calculate `sector[j]=G_j(out)-G_j(in)` and
`penalty[j]=P_j(out)-P_j(in)`. Ignore an element only if its entire sector vector
vanishes. The certificate is the SET of distinct ordered pairs
`(sector, penalty)` for each channel instance. Do not identify a row with its
negative. Do not include multiplicities, amplitudes, or gauge-preserving rows.
Use ascending sparse lists of `[site, nonzero_integer]`; an absent component is
zero. Include every channel instance exactly once, including empty ones:

```
{
  "certificate": [
    {"channel": "identifier", "anchor": 0,
     "transfers": [{"sector": [[0,1],[1,-1]],
                    "penalty": [[0,1],[1,-1]]}]},
    {"channel": "another_identifier", "anchor": 0, "transfers": []}
  ],
  "analog": {"ticks": [integer_for_each_site]},
  "digital": {"ticks": [integer_for_each_site], "phase_tick": integer}
}
```

This is a format example, not an answer to a supplied case. The independent
judge factors local operator support, neighboring constraints, and extendability.
No full-system state vector is needed. Certificates are not trusted as input to
the robustness score.

## Hardware and schedules

`hardware.denominator=Q`, `caps[j]`, `uncertainty[j]=epsilon_j`,
`bandwidth=B`, `phase_denominator=D`, and `phase_ticks` are supplied. Choose
integer ticks `q_j` with `|q_j| <= caps[j]`; `c_j=q_j/Q`. Analog and digital
vectors are separate. The cap is a nominal DAC limit; actual coefficients may
lie in `[c_j-epsilon_j,c_j+epsilon_j]`. All sites can have either sign or zero.
No resizing, unbounded rational encoding, or rescaling V is allowed.

B is a fixed local hardware bandwidth unit: B=1 for U1, B=2 for Z2, accounting
for the density coefficient 2*g_j*c_j. It is NOT the extensive many-body
spectral width and does not change with the selected vector.

The analog schedule holds these coefficients fixed. The digital schedule repeats
the diagonal kick `exp(-i*phi*sum c_j P_j)` once per cycle, with
`phi=pi*phase_tick/D` and `phase_tick` chosen from `phase_ticks`. This is the
protection-layer quasienergy problem, not an assertion about the spectrum of an
unspecified interacting Floquet unitary. The allowed clock window is part of
the input; taking an arbitrarily short step is not allowed.

## Independent robustness evaluation

Pool every reachable NONZERO penalty vector across channels, merge duplicates
and overall-sign equivalents, and call the resulting set R. Each row is counted
once, irrespective of repeated templates or amplitudes. A zero penalty vector
for a nonzero sector transfer would count once as a zero-gap constraint.
For every r in R define

```
d_r = sum_j r_j c_j
e_r = sum_j abs(r_j) epsilon_j
analog_margin_r  = max(0, abs(d_r)-e_r)/B
digital_margin_r = max(0, dist(phi*d_r, 2*pi*Z)-abs(phi)*e_r)/pi
raw_quality      = 0.75*min(margins) + 0.25*mean(margins)
```

`dist(theta,2*pi*Z)=abs((theta+pi) mod (2*pi)-pi)`. The uncertainty correction
is the exact worst-case distance for this scalar interval, separately for each
row. In particular, a large unwrapped gap can have zero digital margin.

Each case has pre-frozen weak and strong feasible anchors b<h, separately for
the two schedules. With t=(raw_quality-b)/(h-b), the score is
`S=0.5*(1+x/sqrt(1+x*x))`, where `x=(2*t-1)*9/sqrt(19)`.
This continuous increasing score is 0.05 at the weak anchor and 0.95 at the
strong anchor, and does not clip improvements beyond the reference. Invalid
controls receive zero for that schedule. Reference anchors need not be optimal.

Certificate scoring reports micro-F1 on sector rows and on joint
(sector,penalty) rows separately. Every empty instance contributes one distinct
empty token. Missing instances miss their rows, spurious rows hurt precision,
and duplicate instances or malformed certificate schema make both F1s zero.
Identical rows repeated within an instance are treated as a set. Algebra score
A is the mean of those two F1s. Case score is `(A*S_analog*S_digital)^(1/3)`.
Reports include every component, minimum and mean margins, overall mean, each
family mean, and worst family mean. A parse failure or timeout scores zero.

## Execution

Place `solver.py` at the submitted directory root. It may import sibling files.
`solve(case)` must return a finite JSON-serializable dict. Each case is run in a
fresh process, with 60 seconds including import and JSON handling, on one CPU.
The entire response must be at most 32 MiB. Python 3.10, NumPy 1.21.5, and
SciPy 1.8.0 are the validated environment. Do not use private files. The trusted
local evaluator supports
`--submission DIR --split screening|challenge|confirmation --output JSON`;
an optional `--participant DIR` overrides the participant mount. The shared
isolated runner executes submissions; isolation setup failures abort evaluation
rather than score as solver failures.
