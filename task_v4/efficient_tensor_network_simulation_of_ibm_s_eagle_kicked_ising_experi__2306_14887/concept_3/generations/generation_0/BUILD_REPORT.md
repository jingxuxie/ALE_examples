# Initial builder report

## Ready for an isolated fresh attempt

Mode C: robust finite-depth many-body **control witness construction**.
The fixed target is GHZ+ fidelity **>=0.95 in every one of 63 scenarios**.
A private passing witness exists. No fresh model/agent was run; empirical
hardness is untested. Main owns fresh launching, logging, and final status.
The source-inspired gate convention and the intentional split-matching,
two-group control generalization are explicit in `participant/input/protocol.md`.

The 12-qubit initial state is `|+>^12`; the 24 layers use fixed nominal
`exp(+i*pi*ZZ/4)` matching gates followed by bounded RX angles in `[-pi,pi]`.
Fractional calibration bounds are +/-2.5% for each kick group, +/-1.5%
common bond gain, and +/-0.5% independently on each edge. No range or
threshold reduction was made to obtain the final passing result.

## Measured exact scores

| Artifact | Core minimum | Worst-family minimum | Held-out minimum | Overall minimum | Mean | Pass |
|---|---:|---:|---:|---:|---:|---|
| Public nominal-only baseline | 0.7902458098 | 0.7537925018 | 0.8613624659 | 0.7537925018 | 0.8813312316 | No |
| Private robust witness | 0.9679958737 | 0.9595128625 | 0.9758677360 | 0.9595128625 | 0.9806519613 | Yes |

The public baseline attains nominal fidelity 0.9999999999594718 but fails
robustness substantially. Its public training minimum is 0.889679564487807;
it uses one nominal-only finite-difference L-BFGS-B run, 56 iterations,
1650 forward calls, fixed seed 148873, and tied global kicks. This is a
useful warm start, not a straw-man random artifact or robust solution.

The final feasibility path first obtains nominal fidelity
0.9999999999944362 from seed 44 and low-amplitude tied initial angles
(71 iterations, 113 gradient evaluations, 2.31 seconds). A subsequent
two-group nine-scenario smooth-min optimization takes 337 iterations and
367 gradient evaluations in 96.62 seconds on one CPU thread. Its training
minimum is 0.9679958736677285. The final 63-case result is computed by the
independent checker, not by the optimization kernel. Logs and intermediate
artifacts are in `champions/private_search/`; reproducible commands are in
`AUTHORING.md`.

Earlier unrestricted-angle starts had poor local minima, and a high-angle
nominal initialization followed by robustness optimization only reached
0.8961617692 on the full test suite. The lower-amplitude continuation was
needed for the passing construction. This supplies a concrete nonconvex
search failure/success contrast, not an empirical fresh-agent hardness claim.

## Audits

- Nine independent 4-qubit dense Kronecker gate tests: maximum error 0.
- Eighteen full 12-qubit circuit/state comparisons between vectorized
  public evolution and trusted gate contractions: max error 5.37e-16.
- Maximum norm deviation in that audit: 1.65e-14; global-X parity error:
  9.31e-17. Neither simulator normalizes away error.
- The unsplit all-edge Clifford alternative has verified conserved
  sublattice parity and GHZ fidelity bound 1/2. The split matching
  commutator has norm 2, removing that particular obstruction.
- Seventeen hostile/missing artifact cases are rejected, including NaN,
  infinity, booleans, strings, huge integers, wrong shapes, invalid bounds,
  duplicate keys, extra fields, malformed JSON, oversize files and symlinks.
- Adjoint finite differences at eight coordinates and two scenarios have
  maximum absolute error 5.30e-13; optimization/public fidelity disagreement
  is 3.26e-19 in the independent cross-check.
- An additional 256 boundary-disorder scenarios, not added to the frozen
  suite, have witness minimum 0.9595198085 and mean 0.9702483872. These are
  spot checks, not a proof of the continuum robust minimum.

The trusted evaluator uses only its own constants and scenario file and
does not import participant functions/configuration. It reads JSON only,
executes no submission code, validates finite numeric types and bounds,
and verifies its private scenario digest. The frozen manifest covers all
public contract/assets and the trusted checker. The source-inspired
physical model was checked against arXiv:2306.14887v3, Eq. (1).

## Resources and handoff

The final launch package is `participant/{TASK.md,input,workspace,baseline}`;
the private suite is `evaluator/hidden/scenarios.json`. Relocation preserves
the exact scenario and baseline bytes and both full-suite scores. The
packaging audit stages only the public package, runs its baseline/scorer,
and checks the required result schema for valid and invalid artifacts.
`core_score`, `worst_family_score`, `resource_score`, `runtime`,
`runtime_seconds`, and `reason` are present in both result branches.
The final manifest covers the relocated paths; the original 0.95 physical
threshold and calibration family remain unchanged. See
`adversary/package_audit.json` and the launch-ready initial `status.json`.

NumPy 1.21.5 / SciPy 1.8.0; private C++17 adjoint compiled with `g++ -O3`.
All numerical runs use one BLAS/OpenMP thread. The full independent checker
takes approximately 1.3–2.2 seconds per artifact on this host, retaining
only a 4096-amplitude state and small temporary gate contractions. The
private gradient stores 25 state vectors per scenario and processes
scenarios serially. No GPU or network is needed to solve or check the task.

Expose only `participant/` and `attempts/v_1/` in the fresh environment.
The public package has `TASK.md`, `input/`, `workspace/`, and `baseline/`;
private scenario bytes are in `evaluator/hidden/scenarios.json`.
Keep `champions/`, `evaluator/`, `adversary/`, `attempts/`, the manifest,
and builder documents private, except the reserved fresh attempt directory.
The saved witness must never be accessible
to the fresh agent. Verify `freeze_manifest.json` before/after evaluation
with `python adversary/verify_freeze.py`.
