# Static witness interface

The only submission artifact is UTF-8 JSON with exactly these keys:

```json
{"version": 1, "gate_parameters": [[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0]], "circuit": "IXY..."}
```

The ellipsis is illustrative, not a valid gate. Rows are ordered `I, X, Y`; each row is `[phi, Re(a), Im(a), Re(b), Im(b)]`. Values must be finite JSON numbers, not booleans. The phase lies in `[-pi,pi]` and `sqrt(|a|^2+|b|^2) <= 0.04`. The circuit is a chronological string of exactly 64 symbols from `IXY`, with at least four of each symbol, and cannot equal a calibration circuit. Duplicate keys, extra fields, and nonstandard JSON constants are rejected. File and directory symlinks are not accepted.

## Physical processor

Basis states are `|0>, |1>, |2>`. The initial state is `|0><0|`, freshly prepared for each complete circuit. There is no reset inside a circuit. Let `R_I = identity(2)`, `R_X = exp(-i*pi*PauliX/4)`, and `R_Y = exp(-i*pi*PauliY/4)`. For each gate,

```
H = [[0, 0, a], [0, 0, b], [conj(a), conj(b), 0]]
U = exp(-i*H) @ block_diag(R_gate, exp(-i*phi))
```

Every occurrence of a label uses the same unitary. The outcome-0 effect is `E0 = 0.005*identity(3) + 0.99*|0><0|`; the other outcome is its complement. No postselection occurs. Final leakage is `rho[2,2]` before readout noise.

## Supplied reported model and screen

The team uses the two-dimensional CPTP reset reduction of each physical gate, not the ideal gate and not a participant-chosen fit. Write `A = U[:2,:2]`, and let the only nonzero row of the 2-by-2 matrix `B` be `B[1,:] = U[2,:2]`. The reported gate is

```
Phi(rho) = A @ rho @ A.conj().T + B @ rho @ B.conj().T
```

The reported model starts in `|0><0|` and uses `E0 = 0.005*identity(2) + 0.99*|0><0|`. It predicts **every** circuit by composing these same maps. It reproduces a gate's reset-reduced one-step behavior, but it does not carry a leakage state between gates. `workspace/screen.py` supplies this method, including its acceptance rule.

`calibration.json` contains explicit circuit strings grouped into seven named families: exhaustive words of length at most four, five streamlined-GST germ/fiducial families, and independent fixed random guards. Each family is a list without duplicate strings; if a string belongs to several families it participates in every corresponding family statistic. Preparation and measurement fiducials use the same imperfect gates as the rest of the circuit. Calibration errors are exact outcome-probability differences, not sampled counts or chi-square statistics.

For **each** scenario in `specification.json`, multiply all four coupling coordinates by `coupling_scale`, then add `phase_shift` to the phases and construct both models anew. A scalar phase shift applies to all three gates; a three-element list applies separately in `I, X, Y` order. The 21 enumerated scenarios retain the original five common-mode checks and add the 16 corners formed by independent phase shifts of ±0.008 radians and coupling scales 0.98 or 1.02. These enumerated scenarios, not an entire continuous uncertainty interval, define robustness. Nominal parameter bounds apply to the submitted rows before perturbation.

The screen accepts when, in every scenario, every calibration absolute error is at most **0.005**, and the RMS error within **each** calibration family is at most **0.002**. Falsification additionally requires an absolute held-out outcome-0 prediction error of at least **0.065** and final leakage at most **0.01**, in every scenario. The same submitted circuit is used in all scenarios. Arithmetic comparisons allow `1e-10` tolerance.

## Measurements and scoring

`python workspace/screen.py --witness /path/to/witness.json` prints JSON. `core_score` is nominal held-out absolute error; `worst_family_score` is its minimum over the 21 tolerance scenarios. Larger is better, but neither score overrides a failed constraint. `valid` means a structurally valid physical input; `passed` means all acceptance and falsification conditions hold. Results include `runtime_seconds`, `reason`, per-scenario probabilities, calibration family maxima/RMS values, and final leakage. There are no undisclosed scientific acceptance criteria. The authoritative evaluator uses a separate density-matrix/matrix-exponential implementation and an immutable copy of the input assets.
