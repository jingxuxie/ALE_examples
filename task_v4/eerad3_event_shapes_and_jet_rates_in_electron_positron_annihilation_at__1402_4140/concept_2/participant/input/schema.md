# Public witness contract, version 1

## Submission and interface

Submit one UTF-8 JSON object with exactly the key `events`, whose value is a list
of exactly two events. An event is a list of exactly five `[E,px,py,pz]` rows.
Every component is a finite JSON number (integers allowed; booleans, strings,
NaN, Infinity, duplicate keys and extra metadata are rejected). Maximum file
size: 16384 bytes. All component magnitudes must be <=1+1e-10; this is a redundant
sanity bound for the normalized physical events. No rounding before submission.
Use full float64 precision. Events are unordered; parton identities are irrelevant.

From the concept directory, the evaluator interface is:

```text
python3 evaluator/evaluate.py --submission PATH --output metrics.json
```

It prints the metrics, optionally writes them, and exits 0 for a pass, 1 for a
rejected or unsuccessful witness. It never executes participant code or uses
participant-supplied shape values. Generate anywhere within the public workspace;
the actual result is the JSON, not a prescribed solver implementation.

## Physical cuts (each event, no repair or rescaling by the evaluator)

- Q=1: `abs(sum(E)-1) <= 1e-10`.
- CM: Euclidean norm of `sum(p)` is <=1e-10.
- Massless: `max(abs(E-|p|)) <= 1e-10`.
- Every energy is >=0.03, not merely nonnegative.
- Every pair has `sij = 2*(Ei*Ej-pi dot pj) >= 1e-4` (Q=1 units).
- Every event has `y45 >= 1e-4`, so separation is not a vanishing denominator.
- Each thrust hemisphere contains at least two partons (a 2+3 partition), so
  the task cannot exploit the dependent `rho_H=tau` and `B_T=B_W` in 4+1 events.

## Definitions

Four-vectors use the (+---) metric. All denominators use the event's actual
`Q=sum(E)` (already required to equal 1 to tolerance).

- `T = max_unit_n sum_i |pi dot n| / Q`, `tau=1-T`. The public calculator
  enumerates the 16 sign sums with first sign +1. In exact five-body CM phase
  space the independent implementation can equivalently maximize `2|sum_S p|/Q`
  over the five singletons and ten pairs. Complementary hemispheres/signs are
  the same axis, not distinct maxima.
- `Theta_ab = sum_i pi_a*pi_b/Ei / Q`; `C=3*(lambda1*lambda2 +
  lambda1*lambda3 + lambda2*lambda3)` for its eigenvalues. The implementations
  use equivalent matrix invariants rather than unstable eigenvalue ordering.
- Assign particles to the two signs of `pi dot n_T`. `rho_H` is the larger
  hemisphere invariant mass **squared**, divided by Q², not its square root.
- Each hemisphere broadening is `sum_i |pi cross n_T|/(2Q)`.
  `B_T=B_plus+B_minus`, `B_W=max(B_plus,B_minus)`.
- Durham: start with all five four-vectors. At each multiplicity, minimize
  `dij=2*min(Ei²,Ej²)*(1-cos(theta_ij))/Q²`, where the angle uses the **spatial
  norms**, including for massive pseudojets. Merge by four-vector addition
  (**E scheme**); do not project a merged pseudojet back onto the light cone.
  `y45`, `y34`, `y23` are the raw minimum distances at 5→4, 4→3, 3→2.
  They are not a running maximum, logarithms, or ycut-scan transition proxies.

These choices follow `getCD`, `getT`, `getjet(...,2,1)` in EERAD3 v1
`src/ecuts.f` and the official release `src/analyses/eventshapes.f` and
`src/analyses/jetalgo.f`. The public calculator is provided so participants need
not obtain or compile the Fortran distribution. The Fortran stores [px,py,pz,E];
the witness interface deliberately uses [E,px,py,pz]. The CM-normalized formula
for hemisphere masses in the original source is equivalent to the one here.

## Numerical regularity cuts (each event)

All are absolute thresholds in Q=1 units, imposed to exclude unstable ties,
hemisphere boundaries and undefined directions, not to narrow the physics:

- The largest and second-largest of the 15 singleton/pair thrust candidates
  differ by at least 1e-7 in T. This is the `thrust_gap` diagnostic.
- `min_i abs(pi dot n_T) >= 1e-6` (`hemisphere_margin`).
- At **each** of multiplicities 5,4,3, the second-smallest pair distance minus
  the smallest is >=1e-8; `merge_gap` is the minimum of these three gaps.
- Every active spatial pseudojet norm at multiplicities 5,4,3 is >=1e-8.
- Trusted recalculation of all six shapes **and y34 and y45** must agree to
  absolute error <=2e-10 under every one of the 120 parton permutations, three
  fixed proper rotations, and each rotation combined with permutation
  `[2,0,4,1,3]`. The rotation quaternions, in [w,x,y,z] order before normalization,
  are `[1,2,3,4]`, `[3,-1,4,2]`, `[2,5,-3,1]`. Rotated events also retain the
  massless and CM residual bounds. There are 126 checks per event.

No planarity, flavor, orientation, shape-window, y34-matching or minimum
inter-event coordinate-distance cuts are imposed. The y45 difference already
excludes pure rotations/permutations/copies. No relative matching tolerance or
extra allowance is added at any threshold; aim for margin, not equality.

The authoring/search budget is one hour. Task assets are read-only in a fresh
attempt; write all search code and the final witness in the assigned output
directory. The evaluator reads only the final JSON; it does not execute a search
or infer its runtime from a claimed timing field.

## Success and scores

Let `delta` be the maximum absolute discrepancy of the six shapes and
`R=max(y45_A,y45_B)/min(y45_A,y45_B)`.

- `valid`: file structure, all physical/regularity cuts and invariance checks pass.
  This does not imply the requested counterexample has been found.
- `passed`: valid, `delta<=1e-7`, and `R>=3`.
- For valid events, `M=1` if `delta<=1e-7`, otherwise `M=1e-7/delta`;
  `S=min(1,max(0,(R-1)/2))`. `core_score=M*S` and
  `worst_family_score=min(M,S)`. Physical and invariance family scores are 1.
- Invalid data gets zero core and worst-family scores. Identical copies have
  `S=0` even when physically valid. Scores near zero are not evidence of solving.
- `runtime_score=1` is neutral for this data-only witness task, including
  rejected submissions. The evaluator reports its own `evaluation_seconds` but
  cannot infer generation time from a JSON. The 300-second/1-CPU/2-GiB generation
  budget is an external runner limit, not a hidden or self-reported scoring gate.
- `reason` explains rejection or unmet targets. Diagnostics include the trusted
  observables, physical residuals, component errors and ratio when available.

All acceptance gates are disclosed here. The machine-readable constants are in
`contract.json`; evaluator-owned constants cannot be altered by editing that file.
