# Concept 3: Mode E, active detector-channel calibration

## Main-only launch instructions

**No fresh participant has been launched by this builder.** Fresh attempts and
fresh champions remain for main to create. Do not expose this file or any sibling
of `participant/` to the fresh coding worker.

The root for all commands below is:

```text
/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/sparse_blossom_correcting_a_million_errors_per_core_second_with_minimu__2303_15933/concept_3
```

Create `attempts/v_1` and allowlist **only** the public `participant/` read-only,
that exact attempt directory writable, and the system runtime via `:minimal`.
Use the main allowlisted-runner mechanism with a one-hour coding wall allowance.
Suggested fresh prompt:

```text
Read TASK.md and input/API.md. Build a standalone Python JSON-lines calibration program in your designated output directory as solution.py. You have one hour. Use /usr/bin/python3 with the installed NumPy/SciPy. Develop with input/local.py and disclosed training episodes. The participant tree is read-only; use the output directory for any scratch files. Do not attempt to run a hidden evaluator or nested bubblewrap. The official worker will see /participant and /submission. Return the path to solution.py.
```

Candidate worker command INSIDE evaluation:

```text
/usr/bin/python3 /submission/solution.py
```

Privileged evaluation command from the concept root, OUTSIDE the fresh coding
worker and outside any parent sandbox that blocks nested namespace creation:

```text
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 evaluator/evaluate.py --submission "$PWD/attempts/v_1" --output "$PWD/attempts/v_1_report.json" -- /usr/bin/python3 /submission/solution.py
```

The worker only receives its exact submission leaf, not `attempts/`, report files,
or private siblings. Never remove bubblewrap isolation to make a nested launch
work. Request an escalated outer evaluator launch instead. The public local
driver uses ordinary subprocesses and needs neither bubblewrap nor private files.

## Exact runtime allowlist requirements

- Interpreter: `/usr/bin/python3` (system Python 3.10).
- NumPy 1.21.5: `/usr/lib/python3/dist-packages/numpy`.
- SciPy 1.8.0: `/usr/lib/python3/dist-packages/scipy`.
- Standard library: `/usr/lib/python3.10`; native BLAS/LAPACK and loader libraries
  under `/usr/lib` and `/lib`, with `/lib64` available where present.
- Shell/utility runtime: `/bin`, `/usr/bin`; normal read-only system `/etc`.
- Privileged evaluator sandbox launcher: `/usr/bin/bwrap`.

`:minimal` plus these system roots suffices; no home virtualenv, Conda directory,
network, pip install, Stim, PyMatching, sklearn, or Torch is needed. The evaluator
explicitly binds `/usr /lib /lib64 /bin /etc` read-only. System runtime paths and
NumPy/SciPy imports have been exercised inside its bubblewrap worker.

## Final design and frozen targets

V2 has 12 independent private episodes, four per regime: six-detector chain,
seven-detector patch, eight-detector burst-alias motifs. There are respectively
22/24/26 unknown positive rates and four equally weighted channel families.
Twenty-nine interventions include shared-mode exposure mixtures, overlapping
alternative footprints, aliased reference channels, and rare-channel gain
ladders spanning amplification and saturation. Forty thousand shots, 64 queries,
and 4,000 shots/query are available per episode.

The fixed primary limit is **mean family log-RMSE <= 0.055**; the guardrail is
**worst regime/family log-RMSE <= 0.095**. Both and resource/protocol validity must
pass. The scorer emits `core_score`, `worst_family_score`, `runtime_score`, `valid`,
`passed`, and `reason`. Maximum CPU is 60 seconds/episode; wall is 900 seconds
after readiness plus 300 seconds for initialization, deliberately generous under
the overloaded host. CPU is measured in-namespace on the actual worker and its
descendants, not from the bubblewrap monitor. The signed meter and CPU cap have
been tested against a two-second process-time burn and a deliberate overrun.

Targets and episodes are hashed in `evaluator/hidden/freeze.json`; public numeric
targets are byte-identical in `participant/input/targets.json`. No targets may
change once main launches a fresh participant. The task is explicitly synthetic:
it calibrates rates rather than running an actual decoder or making hardware
claims. Paper grounding is recorded in `evaluator/hidden/SOURCES.md`.

## Generation history and actual feasibility

V1's initial .16/.27 targets were too easy: uniform ML scored .058526/.106343.
Before any fresh launch, v2 added the known four-level gain ladders and widened
rare rates using the same quantiles in every original episode. No episode or seed
was selected, discarded, or replaced. The .055/.095 targets were declared before
the v2 portfolio runs. Archived v1 reports are in `attempts/design_v1/`.

V2 full-suite evidence:

| Builder policy | Mean log-RMSE | Worst cell | Result |
|---|---:|---:|---|
| Supplied uniform allocation + full ML | 0.084158 | 0.164497 | FAIL |
| Private fixed Fisher design + full ML | 0.051378 | 0.083399 | PASS |
| Private adaptive A-optimal design | 0.049445 | 0.107327 | FAIL worst-cell guard |
| Private robust adaptive minimax design | 0.051130 | 0.079216 | PASS |

The fixed-design and adaptive passing programs receive **only the public hello
spec and query observations**. They use midpoint bounds for initialization, not
true rates or a true-rate schedule. They run through the identical bubblewrap
JSON-lines interface, use 40,000 shots, obey the query cap, and take under six CPU
seconds per episode. The fixed-design solution spends a deterministic schedule
chosen from the public Fisher model, then fits the observed histograms. This is
legitimate achievability evidence, not an oracle. Adaptation is permitted and
useful but not artificially required; a sufficiently good nonadaptive design
may pass. The supplied uniform baseline does not.

Private builder programs and reports live in `adversary/portfolio/`, NOT in fresh
champion directories. They are reference methods, not fresh attempts. Run the
passing fixed policy with submission `adversary/portfolio/reference` and worker
`/usr/bin/python3 /submission/solution.py --policy static`; the robust adaptive
policy uses `--policy robust`.

## Scientific and security audit results

- Full intervention Jacobian ranks: 22/22, 24/24, 26/26 in every hidden episode.
  Reference ranks: 16, 20, 20. Reference aliasing is real and interventions break it.
- Independent XOR-convolution versus analytic PMF discrepancy <= 8.9e-16.
  Finite-difference derivative discrepancy <= 2.8e-11.
- Event-level simulator and independent multinomial sampler pass parity-moment
  tests; maximum event-sampler standardized discrepancy is 3.67.
- Four noiseless, truth-independent starts per episode recover log rates within
  7.7e-5. This is a numerical ambiguity check, not a global identifiability theorem.
- Uniform 40k-shot Fisher local log-rate bounds aggregate to mean .07754/worst
  .13730; action-11-heavy allocation gives .11068/.24023. A true-rate diagnostic
  design gives .05157/.07434. These are local information diagnostics ONLY, not
  claims that an oracle's rates or schedule are available to a participant.
- Protocol tests cover private path/process visibility, supervisor non-dumpability,
  authenticated CPU accounting, CPU overrun, invalid shots/booleans/NaNs, and
  forged meter rejection. Hidden evaluator imports no participant code.
- The public training driver and a copied baseline work from a writable attempt
  directory with the read-only public model located through `DETECTOR_INPUT_DIR`.

Detailed reports: `adversary/science_report.json`, `adversary/inverse_report.json`,
`adversary/protocol_report.json`, `attempts/baseline_report.json`, and the private
portfolio reports. No success claim relies only on Fisher/true-rate diagnostics.
