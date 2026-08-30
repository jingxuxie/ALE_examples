# Stim hardness-discovery package

Three concepts use modes A (baseline improvement), B (counterexample), and C (witness construction). `DISCOVERY.md` records source provenance, candidate selection, and decision rules. Each concept's `participant/TASK.md` is the complete participant-facing mission; its `evaluator/`, `adversary/`, other attempts, and private witnesses must never be given to a tested agent.

The primary retained task is `concept_3/participant/TASK.md`: exact, resource-constrained Clifford construction on a 36-qubit grid. Both independent fresh attempts miss the fixed resource bounds, while a privately validated native circuit passes them. The other concepts retain their own complete task packages and empirical records.

## Environment and isolation

Generation and evaluation were exercised on Linux with Python 3.10, NumPy 1.21.5, SciPy 1.8.0, a system C++ compiler, libseccomp, and unprivileged user/mount/PID namespaces. `authoring/vendor/` contains the pinned generation-only Stim 1.15.0 verifier. `authoring/stim_source/` is an additional generation-only source archive, not a participant dependency.

`authoring/ISOLATION.md`, `isolation_audit.json`, and `timing_audit.json` document the allowlist, private-root launcher, hidden-file/network denial, and resource enforcement. There is no unsafe execution fallback. Infrastructure errors invalidate an execution; they are not agent failures. Concept 1 gets 45 seconds of **solver** wall time after sandbox setup, with a separate 60-second setup allowance.

Fresh attempts invoke the unchanged supplied `run_allowlisted_codex.sh`, model `ultima-alpha`, reasoning effort `xhigh`, in a new runtime. The only task data mounted are read-only `participant/` and an initially empty writable `attempts/v_N/`. The one-hour limit is enforced by the outer supervisor. Credentials and runtime state are neither participant assets nor retained submissions.

## Evaluating

Run commands from this directory. Do not run a submitted Python program on the host.

```
python3 concept_1/evaluator/evaluate.py concept_1/attempts/v_1 --output concept_1/adversary/recheck_v_1.json
python3 concept_2/evaluator/evaluate.py --witness concept_2/attempts/v_5/witness.json
python3 concept_3/evaluator/evaluate.py --submission concept_3/attempts/v_1 --report concept_3/adversary/recheck_v_1.json
```

Concept 1 executes the solver in the audited sandbox on each hidden current input. Concepts 2 and 3 read static artifacts and never execute submitted code. Their public checkers expose the same mathematical acceptance conditions. Empty/malformed artifacts do not pass.

Baseline entry points are `concept_N/participant/baseline/solve.py`. Concept 1 takes `--input INSTANCE.json --output ANSWER.json`; the witness baselines take `--output ARTIFACT.json`. Private passing witnesses, when present, are in `evaluator/hidden/` and are not baseline assets. `freeze.py CONCEPT --verify` checks generation 1; concept 2's current generation requires `--generation 2`. Its solved generation-1 participant and evaluator are preserved in `concept_2/adversary/generation_1/`; use that archived evaluator for attempts v_1 and v_2, not the current 36-fault model. Attempts v_3 and v_4 were blocked before any model call by the runner hash guard and are not scientific attempts. The actual generation-2 attempts are v_5 and v_6.

The provided shared runner was changed externally during the tournament. `authoring/runner_change_audit.json` and byte-matched snapshots establish that only comments and numerical-library thread settings changed, not access controls. Earlier sessions had already execed Codex and retained their original environment. Later launches use the re-audited current runner. This session did not edit the shared runner.

The final empirical outcomes are recorded in each `status.json` and the root final report. A score below the fixed target is not a proof of impossibility. Only an independently validated passing artifact or resource-compliant implementation demonstrates achievability.
