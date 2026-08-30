# Evaluator integration (not participant material)

The only entrant-visible tree is `participant/`. Hide this evaluator directory,
all attempts, champion/adversary artifacts, report paths, other submissions, and
parent process memory. The oracle and hidden generator live in the parent;
each policy process receives only the public hello and noisy scalar observations.
No case seed, family label, exact mean, tail, or true parameter is sent to it.

From `concept_3/`:

```
python evaluator/evaluate.py --submission participant/baseline \
  --report attempts/baseline_report.json --split calibration-v1 --per-family 4 \
  --allow-unsandboxed

python evaluator/evaluate.py --submission attempts/v_1 \
  --report attempts/v_1.evaluation.json --split tournament-v1 --per-family 8 \
  --sandbox-wrapper /absolute/path/to/authoring/sandbox.py
```

The wrapper is invoked once per instance as:

```
python sandbox.py --submission DIR --participant DIR --scratch DIR \
  --entry policy.py --seconds 45
```

It must preserve stdin/stdout and make `participant/workspace` importable, as
main's wrapper does via `PYTHONPATH`. `radial_public` locates the public input even
when the wrapper clears `RADIAL_INPUT` and changes cwd to scratch, including
when the workspace helper is copied into a differently located submission. Input/output are
bounded and deadlines are enforced by the
parent independently of the wrapper. Use filesystem, process-memory/proc, network,
and syscall isolation plus memory/CPU limits externally. `close_fds=True`, a new
process group, controlled environment, and a fresh scratch directory are supplied.
The evaluator itself is NOT an OS sandbox. `--allow-unsandboxed` is only for
trusted author-written diagnostics and can never produce an official pass.
Default wrapper autodetection: `../authoring/sandbox.py` relative to concept_3.
The 24-case baseline successfully ran through main's actual Landlock/seccomp
wrapper during calibration. A relocated-submission smoke test is also supplied.

Default time limits: 45 seconds/case, 15 seconds/response; configurable for author
diagnostics, but main should freeze these for all entrants. No subprocess is
reused across cases. Stdout after an answer, abnormal exit, and a process that
does not terminate are failures, not silently accepted answers.

`hidden/generator.py` derives independent parameter and observation-noise seeds
using HMAC labels for split/family/repetition, then shuffles by an independent
HMAC. The realized parameters remain deterministic for a fixed key and split.
Replace `hidden/seeds.json` or supply `--seed-file FILE` before the fresh run;
do not transmit the key or split seed through the policy's argv/environment.
Keep the same fresh key across compared policies. No tournament split is used
in author calibration. Balance all six known families at >=8 cases/family.

Reports expose scores, family aggregates, and opaque IDs after child termination,
not parameter vectors. Invalid cases cause `valid=false`, `passed=false`, score
zero. Harness failures (missing sandbox, missing entry) terminate with an error;
do not call them scientific failures. Target SHA256 is included in each report.
Freeze/hash participant and evaluator trees before launching fresh authoring.

All aggregate reports include `reason`, `runtime_seconds`, `runtime_score`, and
`worst_family_score`. Runtime is the sum of parent-measured per-case elapsed time,
including process startup. Runtime score is `100*max(0,1-runtime_seconds/(45*N))`;
it is diagnostic only and does not change the frozen scientific acceptance rule.
Worst-family score is `100/(1+worst_family_loss)`. Invalid or incomplete suites
have zero core/runtime/worst-family scores and an explicit failure reason;
their measured runtime is still reported. Per-case runtime and reason are also
recorded. Main owns the new-key official 48-case baseline before fresh authoring.
