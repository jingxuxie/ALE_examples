# Generation-two trusted evaluator

From the generation-two root:

```
OPENBLAS_NUM_THREADS=1 /usr/bin/python3 -B evaluator/evaluate.py /path/witness.json --output result.json --summary-only
```

Only the artifact is untrusted. Neither submitted code nor participant checker,
graph, or spec files are loaded by the trusted oracle. Every one of 2,265 points
is evaluated by the generic full-state native DP, not just sampled audits.
`hidden/oracle.py` independently reconstructs all graph masks, calibration
directions, probability vectors, derivative bounds, and targets.

The native source is `hidden/full_state.cpp`; `hidden/full_state.so` is built for
the current Linux host. It uses positive probability and min-plus recurrences.
An invertible GF(2) basis identifies independent edge masks, expands their states,
then applies the remaining XOR transitions to all 2**21 states. This changes
state coordinates and edge order, not the distribution or logical classes.
Probabilities/costs of each paired XOR state are saved before either is updated.
There is no fast-math, Fourier cancellation, reference solution, or truncation.

Rebuild before any freeze only, if infrastructure requires it:

```
TMPDIR="$PWD/adversary/tmp" g++ -O3 -std=c++17 -fPIC -shared evaluator/hidden/full_state.cpp -o evaluator/hidden/full_state.so
```

Evaluation uses one native thread and substantially less than 1 GiB. Allow a
nominal 900 seconds, separate from each fresh model's 3,600 wall seconds. The
shared host can delay work; no short internal watchdog invalidates an artifact.
Reports include wall/CPU time, resident memory, and standardized scores/reasons.
Infrastructure failures are not scientific counterexample failures.

Expose only a clean copy of this generation's `participant/` to each independent
fresh attempt. Do not expose the parent concept tree, original attempts, this
evaluator, or any adversary directory. Use a clean trusted evaluation process
without participant-controlled module paths. `hidden/frozen_manifest.json`
records pre-launch public/trusted hashes. No runner is launched by this build.
