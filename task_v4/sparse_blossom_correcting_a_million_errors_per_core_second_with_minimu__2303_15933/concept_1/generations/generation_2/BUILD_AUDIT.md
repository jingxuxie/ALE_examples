# Generation two build audit

Status: READY for main review and a fresh one-hour run. No fresh runner was launched by the builder.
This is ratchet 1 of at most 3. The original generation remains frozen and unchanged.

## Frozen objective and baseline

- Promoted generation_1 Python/C++ code, Makefile and native binary are byte-identical in `participant/baseline/`.
- 20% fewer pooled joint-logical failures; 15% fewer on independent holdout; no family failure-count increase; paired absolute 95% lower endpoint above zero.
- 3,072 hidden shots, six known cases, three families. Public calibration has 1,536 independent labeled shots.
- Baseline: 427/3072 failures. Challenge 212; holdout 215. Family counts: spatial pairs 108, known nonuniform crosstalk 113, space-time pair memory 206.
- The old two-pass correlated PyMatching decoder has 1,292 failures on these same hidden draws; it is not the new scoring baseline.
- Full-suite qualification CPU: 105.534025, 92.419149 seconds. Frozen reference is the maximum, 105.534025 seconds.
- Frozen CPU cap: **132 seconds**, computed as ceil(1.25 times that reference). One process/thread; 6 GiB address space; 900 s wall watchdog. Fresh coding time remains one hour.
- Final evaluator baseline CPU: 107.96356 seconds; core/worst-family scores 0; resource score 1.0; valid FAIL, not INVALID.
- Freeze SHA-256: `73380049169bc128b0f5ea7003691123995b0279b1ce933396f72208d743fd09`. `participant/input/target.json` matches `evaluator/hidden/frozen.json` and is checked by the evaluator.

## Scientific selection and controls

33 private stress regimes were screened. Only the corrected C-contiguous, reference-verified screen (37 failures/1,056 shots) is included as evidence. The earlier invalid output-buffer run is explicitly excluded.

The chosen independent confirmation has 101 champion failures/768 shots. Quadrupling ensembles reduces this to 95 at 4.65 times CPU; on the smaller pilot it reduces 58 to 45 at 4.93 times CPU. This discrepancy and the paired uncertainty are retained, not hidden.

At 1.25 times CPU, optimistic case-wise label-oracle parameter choices remove only 3.96% on confirmation (5.17% on pilot). Compiler-only changes remove none. Eight likelihood-temperature choices remove at most 1.98% uniformly; their optimistic case-wise label oracle removes 6.93%. A low-confidence fallback to correlated matching gives no uniform confirmation improvement and at best two failures saved with case-wise label-oracle routing. More BP iterations, wider search, forced list decoding, and a local X/Z/Y marginalization were also checked privately.

Residuals concentrate in spatial-pair-coupled, list-search inference. The noisy temporal case retains confidently wrong *truncated-list* scores. Fault-component and detector-hotspot associations are descriptive, not causal proofs or Bayes bounds. Private raw summaries, paired reports and residual diagnostics are in `evaluator/hidden/evidence/` and `evaluator/hidden/scientific_selection.json`.

**No qualified passing solution exists.** This is explicitly a hard open improvement target, not an achievability claim. Expensive knobs show some approximation headroom but do not certify a 20% improvement within budget. No new candidate was scored on the new hidden data during selection.

## Sampling, isolation, and validation

Every label is L e mod 2 for an unconditional independent Bernoulli mechanism vector e; syndromes are H e mod 2. All 18 seed streams were committed before any decoding. There is no hard-shot filtering, rejection, class balancing or seed search. Actual nonuniform probabilities and the full DEM are public; sampled hidden labels and seeds are not.

The trusted parent snapshots only the candidate's directory. Isolated attempt/champion/adversary candidate subdirectories are allowed; privileged ancestry, collection roots, symlinks and nonregular artifacts are rejected. Candidate input contains only syndromes plus known model assets. Hidden data never enter the worker mount. The full worker JSON/NPZ interface is documented publicly for main's audit.

Evaluation uses bwrap with private user/PID/network namespaces, `--as-pid-1`, a private proc/dev/tmp, and explicit read-only participant/submission/request mounts. Seccomp blocks process/thread creation and cross-process memory access. Host environment is cleared. CPU is measured by trusted parent wait4, not worker-reported metadata. A trusted two-second CPU burn increased measured CPU by 2.369420 seconds before freeze. No isolation fallback is permitted.

All 11 scientific/unit tests and all final validation checks pass. They cover Stim parity semantics, four independent logical homologies, unconditional sampling moments, exact seed reproduction, baseline identity and batch invariance, strict prediction schema, submission-path rules, self-contained runtime, freeze integrity, CPU accounting, and valid-failure versus invalid-output handling. Raw reports are under `attempts/`.

All 39 original frozen artifacts and the original champion code hashes still match. Bundled runtime is about 313 MiB of real files, not external symlinks; `/usr/bin/python3` loads it in isolation. The original frozen task and no other concept were edited.

## Main handoff

Run from a context allowed to create the bwrap namespaces (an escalated exec outside the parent sandbox is required on this host):

```
/usr/bin/python3 evaluator/evaluate.py --submission attempts/v_1/submission.py --split both --report attempts/v_1_result.json
```

The paths above are relative to generation_2. Preserve the candidate snapshot before hidden evaluation and avoid adaptive holdout reuse. `valid=true, passed=false` is an ordinary target failure; invalid submissions have separate status and reason. The private evaluator, hidden data, seeds and stress portfolios must never be mounted for the fresh coding agent. Only `participant/` and its output directory belong in that agent's filesystem view.
