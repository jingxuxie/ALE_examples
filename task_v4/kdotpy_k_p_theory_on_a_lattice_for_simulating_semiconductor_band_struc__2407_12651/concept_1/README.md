# Concept 1: robust topology-constrained band atlas improvement

Mode A: improve a fixed feasible baseline, not recover a hidden exact optimum.
All public assets live in `participant/`; hidden cases, development evidence,
privileged control and status are separate and must never be solver-allowlisted.
The four public and eight hidden cases cover four scientific regimes, each with
four scenarios, four candidates and rank-two subspaces on a torus.

Run commands from this concept directory with `/usr/bin/python3 -B` and
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1`.

```sh
python3 -B adversary/test_atlas.py
timeout --kill-after=5s 45s python3 -B evaluator/preflight.py --output adversary/replay_preflight.json
python3 -B evaluator/evaluate.py --submission participant/baseline --split hidden --output attempts/baseline_hidden.json
python3 -B evaluator/evaluate.py --submission champions --split hidden --output adversary/champion_hidden.json
python3 -B evaluator/evaluate.py --submission attempts/NEW_ATTEMPT --split hidden --output attempts/NEW_ATTEMPT.evaluation.json
```

The preflight runs only a dummy Python submission using public, nonsecret
positive and negative canaries. It checks dependency availability, allowed
reads/writes, direct private/sibling canary denial, symlink escape denial,
public-input write denial, separate network/PID namespaces and environment
cleanliness. It opens no authentication or private scientific files. This
certifies only the evaluator configuration, not a fresh Codex session's startup
context or other tools. The controller must perform its own exact-tool preflight
before launching any agent. If the outer default sandbox hangs, escalate the
trusted controller command; never execute solver code without inner isolation.

Replay uses bubblewrap with isolated network, PID, mount and IPC namespaces,
minimal system runtime mounts including BLAS alternatives, clean environment,
four-core affinity, 2 GiB address space, bounded output and a 90-second deadline.
The evaluator takes a submission snapshot, mounts it read-only, and accepts only
a small regular JSON file containing integer choices. It never imports the
submission. Hidden labels/scorer paths, sibling attempts and host home are not
mounted. Runtime includes startup and preprocessing. Failures are recorded,
not retried unsandboxed. Freeze verification detects changes to packaged code,
inputs, policy and generator before subsequent scoring.

The authored champion uses only received case data at replay, but its design was
informed by private development cases. It is not independent fresh-agent evidence.
Targets are chosen once from measured headroom before any such attempt and stored
in `participant/workspace/policy.json` and `frozen_manifest.json`. `status.json`
reports raw baseline/control performance and remaining screening requirements.

Source grounding: kdotpy paper arXiv:2407.12651, shared release 1.4.1 Berry and
overlap postprocessing, and the gauge-invariant lattice construction of Fukui,
Hatsugai and Suzuki (arXiv:cond-mat/0503172). The prior local task's objective
definitions informed this new implementation, but its exact-answer grading and
prior agent context are not inherited. These cases are explicitly synthetic
downstream acquisition proxies, not claims of real-material accuracy.
