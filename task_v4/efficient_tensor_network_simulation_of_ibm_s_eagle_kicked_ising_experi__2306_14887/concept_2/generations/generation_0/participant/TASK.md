# Physical false convergence on one heavy-hex plaquette

## Mission
Find a **robust counterexample to the supplied finite-bond observable-convergence
heuristic**, using a real kicked-Ising circuit on the 12-cycle. Verification mode
is **B: COUNTEREXAMPLE / FALSIFICATION**. This is not a falsification of
arXiv:2306.14887, its BP algorithm, or a rigorous MPS truncation-error bound.
That paper distinguishes finite-bond convergence from uncontrolled BP loop error;
this task isolates a deliberately convergence-only diagnostic for an OBC MPS.

## Physics and interface
Start in `|000000000000>`. Each layer applies global
`Rx(theta)=exp(-i theta X/2)`, then `exp(+i pi ZZ/4)` on every cycle edge,
including `(11,0)`. There are no noise channels or tunable ZZ couplings.
Measure the spatially averaged nearest-neighbor correlator
`O = (1/12) sum_j Z_j Z_((j+1) mod 12)` (JSON name `zz1`).

Submit a directory containing **`witness.json`**, with exactly these keys:

```json
{"schema_version":1,"depth":24,"knots":[0.7,0.7,0.7,0.7,0.7,0.7],"observable":"zz1"}
```

The example illustrates syntax, not a solution. `depth` is an integer in
`[12,48]`. Six real knots lie in `[0.12,1.45]`; linearly interpolate them at
`depth` equally spaced times in `[0,1]`, including both endpoints. The same pulse
acts on every qubit. Every evaluated waveform must have adjacent-angle changes
at most `0.12` radians. All pulses are strictly within `(0.1,1.47)`, excluding
zero-field and exact Clifford echoes. Files are limited to 16 KiB; duplicate keys,
nonfinite numbers, booleans as numbers, symlinks, and extra keys are invalid.

## Frozen objective
Evaluate five public families: nominal `theta(t)`, offsets `theta(t) ± 0.002`,
and tilts `theta(t) ± 0.002*(2t-1)`. The same witness must satisfy all five.
These are discrete robustness tests, not a certificate for a continuous box.

For each family, evolve **three independent MPS states**, at `chi=4,8,16`.
Let their estimates be `m4,m8,m16` and the exact statevector result be `m*`.
The supplied heuristic declares convergence when
`delta = max(abs(m8-m4), abs(m16-m8)) <= 0.008`, and reports `m16`.
Win by simultaneously making **`delta <= 0.008` and `abs(m16-m*) >= 0.15`**
in every family: an error at least 18.75 times the allowed convergence spread.
Discarded weights are reported but intentionally not used by this heuristic.

For each family define `r=min(error/0.15, 0.008/max(delta,1e-15))` and
`score=100*min(1,r)`. `core_score` is the nominal score;
`worst_family_score` is the minimum over five families. `passed` requires both
thresholds in every family. `valid` describes the artifact/physical constraints,
not success. Invalid submissions score zero. `resource_score=100*12/depth`
is a deterministic depth-efficiency tie-break, not measured search cost.

## Assets and resources
- `input/target.json`: complete frozen constants and constraints.
- `input/example_witness.json`: valid-format starting point.
- `workspace/simulator.py`: auditable exact and actual circuit-MPS evolution.
- `workspace/protocol.py`: public interpolation, robustness, and scoring.
- `baseline/search.py`: runnable grid/random baseline; improve freely.

The MPS represents sites in order `0..11`. Each full layer is applied exactly
using rank-two ZZ expansions, including a long-range closing-edge MPO.
Then right-to-left QR establishes the Schmidt metric and left-to-right SVD
compresses to `chi`, normalizing after each cut. Degenerate Schmidt subspaces
use deterministic projected-coordinate bases. There is no BP contraction or
artificial error formula. Final MPS observables are contracted without further
approximation. Only NumPy and SciPy are needed; no accelerator or network.
Use modest CPU parallelism (one BLAS thread per worker; at most four workers).
A 10-minute search is a suggested starting budget, not an evaluator-enforced
limit. The bounded circuit and data-only artifact bound evaluation work.

From the participant directory:

```bash
python baseline/search.py --submission submission --trials 48 --seed 14887
```

The host privately invokes, from the package root,
`python -I evaluator/evaluate.py --submission DIRECTORY --output JSONPATH`.
The checker recomputes all results using
trusted resources, ignores claimed scores, and never executes submission code.
You may edit workspace search tools; edits cannot change the evaluator's frozen
simulator, oracle, constraints, or scores. Return only the submission directory.
