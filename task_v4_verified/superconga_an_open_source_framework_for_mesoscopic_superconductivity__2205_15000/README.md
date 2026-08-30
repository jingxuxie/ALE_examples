# SuperConga hardness discovery

This directory contains three independent participant tasks, private evaluators,
baselines, isolated fresh-agent evidence, and champion/adversary records.
Only a concept's `participant/` directory and an initially empty attempt output
directory are exposed to a fresh session. Never distribute the paper checkout,
private data, evaluator, champions, adversarial search, or session transcripts
with the participant packet.

## Concepts

1. **A — Baseline improvement:** nonconvex near-critical-temperature GL vortex
   state optimization in pinned and perforated mesoscopic grains.
2. **C — Witness/design construction:** a fabrication-feasible normal-inclusion
   pattern realizing a multi-condition microscopic Andreev spectral fingerprint.
3. **E — Active experiment design:** impurity/vortex reconstruction from a limited
   number of adaptive microscopic LDOS measurements.

These are explicitly declared reduced models, not reproductions of native
SuperConga or claims of quantitative equivalence to its quasiclassical theory.

## Runtime

The validated host has Python 3.10, NumPy 1.21.5, SciPy 1.8.0, Linux
`bubblewrap`, and `libseccomp`. No CUDA, HIP, network access, or source-native GPU solver is needed
by participants. Code-submission evaluators create a fresh network-disabled
filesystem/PID sandbox per case or episode. Launch them from a host context
that permits creating those namespaces; they intentionally refuse an
unsandboxed fallback. One CPU is selected by affinity and BLAS threads are one.

Example evaluations, from this directory:

```sh
OPENBLAS_NUM_THREADS=1 python3 concept_1/evaluator/evaluate.py --submission concept_1/participant/baseline --report /tmp/superconga-gl-baseline.json
OPENBLAS_NUM_THREADS=1 python3 concept_2/evaluator/evaluate.py --submission concept_2/attempts/v_3 --report /tmp/superconga-spectral-replay.json
OPENBLAS_NUM_THREADS=1 python3 concept_3/evaluator/evaluate.py --submission concept_3/attempts/v_1 --output /tmp/superconga-tomography-replay.json
```

Use the matching archived generation of a changed task when replaying older
attempts. `status.json` records final generation and score provenance. Never
compare an old submission's score against a newly ratcheted target silently.
For archived GL/tomography evaluators, also set `PYTHONPATH` to the absolute
path of this directory's `authoring/` so they can locate the shared sandbox.
Keep replay reports separate from the original launch and evaluation evidence.

The final spectral packet is generation 3. Its two fresh one-hour submissions
are fabrication-valid but fail the fixed fidelity targets; the private design
in `concept_2/evaluator/hidden/feasible_design/` passes. It is retained as
`hard_verified_achievable`. Current concept decisions and complete generation
histories are recorded in their respective `status.json` files.

Tomography's original resource accounting was repaired without changing any
participant assets, simulator outcomes, thresholds, or champion source.
The corrected baseline and champion reports are in
`concept_3/attempts/checker_revision_2/`; historical CPU totals are not valid
whole-process-tree resource measurements. The corrected champion still passes.

Fresh sessions are launched by `authoring/launch.py`, using the user-provided
`run_allowlisted_codex.sh`, explicit `ultima-alpha`, xhigh reasoning, read-only
participant assets, ephemeral sessions, and a 3600-second wall cutoff.
Launch metadata and logs live beside, not inside, the attempt's writable output.

Scientific provenance and the ten-candidate selection record are in `authoring/`.
The final decision distinguishes a valid evaluator from a proven feasible
resource-bounded solver; an expensive energy witness alone does not establish
that a general solver meets its runtime budget.
