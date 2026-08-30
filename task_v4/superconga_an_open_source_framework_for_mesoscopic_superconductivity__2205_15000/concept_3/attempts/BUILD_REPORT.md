# Generation 1 builder results

Model and absolute target were fixed before private baseline evaluation, and are
unchanged for the first fresh attempt. No seed was rejected based on performance.
The documented 4–7 impurity range is retained: exact recovery occurred on public
crowded scenes as well as eight of twelve private draws, and local competitors
are spectrally distinguishable. This does not establish universal solvability.

## Baseline

Uniform 56-point policy; 46 vortex configurations; dense sparse-regularized
nonlinear fits followed by discrete support extraction and strength refinement.

| Metric | Public calibration (6) | Private full suite (12) |
|---|---:|---:|
| Joint reconstruction / core | 0.666667 | 0.666667 |
| Worst-family joint reconstruction | 0.5 | 0.5 |
| Mean support F1 | 0.848485 | 0.884432 |
| Relative strength error | 0.256687 | 0.224137 |
| Exact vortex configuration | 1.0 | 0.916667 |
| Diagnostic quality | 0.867646 | 0.866960 |
| Mean / maximum wall seconds | 6.96 / 7.73 | 7.33 / 9.38 |
| Protocol failures | 0 | 0 |
| Absolute target | not met | not met |

The baseline fails core, support, and strength gates. It does not already solve
the task. Its substantial spare CPU budget is a hardness risk: multistart or
better support search may suffice without adaptivity. This generation must be
judged empirically, not advertised as a demonstrated adaptive-sensing barrier.

## Physics and interface validation

18 unittest methods cover Hermiticity; class-C particle-hole operator and paired
spectrum; direct diagonalization vs resolvent vs table LDOS; analytic finite-open-
lattice normal and uniform-gap limits; spectral-weight normalization; global
phase and time-reversed winding equivalence; analytic Jacobian finite differences;
input/prior constraints; full strength-error accounting; independent worst-family
gating; partial-suite nonpass; immutable public metadata; frozen snapshot parity;
and isolated protocol/mount/resource behavior. Protocol tests include repeated
fresh scratch, read-only participant/submission, invalid values/keys, oversized
stdout/stderr, output after final, nonzero exit, EOF, query overflow, and deadlines.
Observation writes are nonblocking to avoid a client deadlocking the host by
refusing to read stdin. The public practice harness also completes a labeled
JSONL episode independently of private evaluator code.

## Identifiability and query-design diagnostics

There are 493,642,974 support/sector combinations before continuous signed
strengths. Six public cases were checked against all one-impurity site relocations,
single sign flips, 0.15-strength perturbations, and all other vortex configurations.
The eight closest wrong discrete scenes per case were locally refit in strength.
The minimum remaining RMS discrepancy was 0.01090, far above noiseless instrument
rounding of 5e-13. True-support Jacobians were full rank in these samples.

An explicitly **oracle-assisted** maximin measurement-design diagnostic improved
the closest finite-candidate RMS separation by 2.57×–5.64× compared with 56 uniform
points. It constructs alternatives around the truth and is not a submitted
adaptive policy, global ambiguity proof, or proof of necessity for adaptation.
See `identifiability.json` for all cases and caveats.

## Remaining limitations

No full-target passing solver is known at builder freeze. Stronger inference may
make this generation easy; there is no artificial claim of hardness. The small
suite has coarse 25-percentage-point family steps. The prescribed s-wave gap,
neglect of Peierls phases/screening, discrete pinned core centers, and noiseless
measurements make this a controlled microscopic diagnostic, not material realism.
The official-listed BdG comparison predates the SuperConga paper (2020 vs 2022).

## Fresh-session handoff

Generation 1 was frozen on August 27, 2026 before the first fresh launch. The
parent's allowlisted launcher started `ultima-alpha`, xhigh effort, with a one-hour
limit and an initially empty `attempts/v_1/`. Only the read-only participant tree,
that output directory, and allowed system runtime are available to the tested
agent. The session is not given this report, baseline private scores, hidden
draws, or evaluator source. `v_1.launch.json` records the asset hashes and exact
command; `v_1.exit.json` appears when the process finishes.

To score the completed submission through the same frozen isolated evaluator:

    OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python evaluator/evaluate.py --submission attempts/v_1 --split evaluation --output attempts/fresh_v1_score.json

Run this with outer sandbox escalation. Until that full report exists, the
empirical hardness decision and full-target solvability remain pending. No
champion or ratchet generation has been created by the builder.
