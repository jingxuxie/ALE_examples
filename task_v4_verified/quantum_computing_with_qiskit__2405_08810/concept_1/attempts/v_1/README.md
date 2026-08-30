# Hardware-aware symbolic phase compiler

Run `python3 solution.py`. The process accepts one workload JSON object per line
on standard input and flushes one circuit JSON object per workload to standard
output. It has no dependency on the supplied baseline or checker at runtime.

## Submission files

- `solution.py`: streaming launcher, compilation deadline, and fallback handling.
- `engine`: prebuilt Linux x86-64 compiler executable.
- `engine.cpp`: C++17 source for the compiler.
- `reference.py`: self-contained native-tree implementation used for the safe
  fallback, not a copy of the supplied baseline.

The executable is included, so compilation is normally unnecessary. To rebuild:

```sh
g++ -O3 -std=c++17 -static-libstdc++ -static-libgcc engine.cpp -o engine
```

The launcher also attempts a bounded rebuild if the executable is missing.

## Method

The compiler tracks all requested parities in the current invertible Boolean
basis. Calibration-weighted Steiner-tree approximations expose parities using
native CX operations, with exact remote-CX expansions where those are cheaper.
Rotations are emitted opportunistically, once each, whenever their exact symbolic
parity appears on a qubit.

A bounded portfolio varies trees, roots, term ordering, and lookahead. It can
backtrack to earlier Boolean bases rather than allow completed parity groups to
make unrelated groups expensive. Each candidate restores the identity using
either its inverse history or a separate exact linear synthesis. Commuting-gate
cancellation and dependency-aware scheduling reduce native cost and makespan.
Every improving candidate is checked for legal edges, exact rotation masks,
unique term indices, operation count, and identity output before selection.

Search normally lasts 8.3 seconds per workload. The launcher imposes a 12-second
workload deadline on the subprocess path and uses independent native parity
trees if the engine fails or times out. Only Python's standard library and the
included executable are needed; there is no network access, external calibration
data, or workload-specific circuit table.

## Validation

`validation_report.json` records the measured development results:

- All four public workloads pass the supplied semantic/cost checker.
- Public mean cost reduction: **57.96%**; smallest public reduction: **48.37%**.
- All 60 randomized topology/parity tests pass.
- Thirteen fallback checks, including the all-singleton boundary case, pass.
- Four synthetic maximum-size cases (`n=28`, 96 terms) pass, with reductions
  between **47.30% and 69.59%**.
- Maximum observed full-budget response time: **8.51 seconds**.
- Peak measured child resident memory: **54,592 KiB**, approximately 53 MiB.

These are public and synthetic measurements, not claims about hidden test scores.
Time-bounded search can produce slightly different results across machines.

`circuits.jsonl` contains the validated public responses. In the documented
evaluation layout, the supplied checker can be run with:

```sh
python3 /task/workspace/check.py /task/input/examples.jsonl circuits.jsonl
```

The development test scripts use the `ASSETS` environment variable to locate the
participant assets; the submitted launcher does not use it.
