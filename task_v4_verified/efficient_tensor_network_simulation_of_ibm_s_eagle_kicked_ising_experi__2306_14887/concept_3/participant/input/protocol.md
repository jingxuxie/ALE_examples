# Binding physical and submission contract — generation 1

## State, graph, controls, and chronology

Sites `0,...,11` form one isolated 12-cycle heavy-hex plaquette; edge `j`
joins `j` to `(j+1) mod 12`. Site zero is the least significant basis bit.
The kick groups are `A={0,1,3,6,8,11}` and `B={2,4,5,7,9,10}`. Start in
`|+>^12` and target the fixed-phase state
`GHZ+ = (|0^12> + |1^12>)/sqrt(2)`.

For zero-based layers `l=0,...,23`, apply **D_l, then K_l, then E**:

```
D_l(s) = product_{j mod 2 = l mod 2}
         exp(+i (pi/4) [1 + c(s) + d_j(s)] Z_j Z_(j+1))
K_l(s) = product_v exp(-i theta[l,g(v)] [1 + e_g(v)(s)] X_v / 2)
E(s)   = product_v exp(-i delta_v(s) Z_v / 2)
|psi_s> = E(s) K_23(s) D_23(s) ... E(s) K_0(s) D_0(s) |+>^12
F_s = |(<0^12| + <1^12|) psi_s / sqrt(2)|^2
```

Only the 48 `theta` values are controls, each in `[-pi,pi]`. Zero kicks do
not skip ZZ or drift. The six ZZ gates in each matching, matching schedule,
and nominal strength are fixed. The drift interval occurs after **every**
layer, including the last. No final correction, GHZ phase fitting,
measurement, postselection, adaptive or scenario-specific control is allowed.

## Public uncertainty family

All parameters are independent and static for the entire sequence:

- Group gain errors `e_A,e_B in [-0.025,0.025]`.
- Common ZZ gain error `c in [-0.015,0.015]`.
- Each edge residual gain `d_j in [-0.005,0.005]`.
- Each site drift `delta_v in [-0.01,0.01]` **radians per layer**.

The first three are fractional multiplicative calibration errors; delta
is an actual Z-rotation angle, not a fractional error or kick control. The
27 coordinates define the binding family. Common ZZ plus local residual
can reach +/-2% total bond error. Both group kicks may coincide while their
errors differ. There is no shot noise or decoherence.

`E` defines a lumped fixed-duration residual-precession interval per layer,
not simultaneous detuning during the idealized RX/ZZ gates. If the interval
has duration tau, `delta_v = Delta_v * tau` for angular detuning Delta_v;
no hardware-specific tau is assumed. Scenarios use the keys `gain_a`,
`gain_b`, `zz_common`, `zz_local` (12 values), and
`z_drift_radians_per_layer` (12 values). The public simulator treats an
omitted drift field as zero for backward-compatible nominal calls; all
published and trusted scenarios specify it explicitly.

## Frozen objective

Pass iff `min_s F_s >= 0.95` over **all 223 frozen scenarios**. No averaging,
rounding tolerance, phase optimization, or normalization can hide a failure.
The score is that minimum, not a certification of the continuous family.

The suite contains 63 zero-drift calibration cases; 16 nominal-calibration
structured/local drift cases; 64 joint coherent corner/stress cases; 16
adversarial joint-error cases; and 64 held-out local-disorder cases. It
includes uniform, alternating, group-correlated, half-ring, and localized
fields, together with mixtures of calibration errors. All cases stay within
the published family. The 31 public examples are not the whole suite.

The checker uses independent complex128 gate contractions with 4096
amplitudes, no truncation or sampling. Norm is checked in every scenario.
Global-X parity is checked **only for zero drift**: nonzero Z drift breaks
that symmetry and its resulting parity change is not a checker error.

## Source-inspired generalization

Tindall et al., *Efficient tensor network simulation of IBM's Eagle kicked
Ising experiment*, arXiv:2306.14887v3, Eq. (1), supplies the fixed
`exp(+i*pi*ZZ/4)` and transverse-RX gate convention. This task deliberately
uses an isolated plaquette, alternating bond matchings, two kick groups,
and residual local Z precession. It is a control-design generalization,
not a reproduction of the original experiment. The matching schedule
avoids an extra sublattice-parity obstruction of the simultaneous all-bond
Clifford layer on this ring. The specified input must not be replaced by
`|0>^12`.

## Artifact and CLI

Submit `pulses.json`: a UTF-8 JSON object with exactly `schema_version`
(integer 1) and `angles` (24 lists of two finite numbers). The angle
bounds are strict. Booleans, strings, nulls, duplicate keys, extra fields,
NaN/infinity, wrong shapes, symlink artifacts, and files over 65536 bytes
are invalid. Only JSON is read; submission code is never executed.

The trusted harness runs:
`python evaluator/evaluate.py --submission DIRECTORY --output JSONPATH`.
Both valid and invalid results include `valid`, `passed`, `score`,
`core_score`, `worst_family_score`, `resource_score`, `runtime`,
`runtime_seconds`, and `reason`. Core/worst-family scores are their minimum
fidelities, or zero for invalid artifacts. Core comprises 31 cases;
worst-family comprises 104; held-out comprises 88. The overall score still
requires every case, including held-out cases, to pass.

`resource_score` is 1 for a valid fixed-size artifact completing exact
checking, otherwise 0. It is not a timing bonus. Runtime is checker wall
time, not search time. Valid results also include family/subfamily minima,
hashes, norm errors, and the zero-drift parity-check count. Valid artifacts
return exit code 0 even below target; malformed artifacts return code 2
and zero scores. Trusted checker failures are not participant failures.
Use a separate result path, not the submitted artifact itself.
