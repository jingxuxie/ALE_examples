# Independent generation-2 evaluator review

**Verdict: evaluator valid; no blocking concerns.** The planted artifact is an
independently verified feasible exact witness. No false acceptance, numeric
tolerance bypass, hidden acceptance constraint, or evidence of task infeasibility
was found. This is a validity review, **not a hardness classification**.

## Scope and frozen identity

Read `participant/TASK.md`, `SPEC.md`, `check.py`, the schema/public target,
`evaluator/evaluate.py`, `validator.py`, and private hidden material including the
plant. Author staging code/results were inspected but not executed or adopted as
independent evidence. No attempts or champions were read, no active `v_3`/`v_4`
interaction occurred, and no web, subagent, or solver run was used. All writes are
inside this new review directory; pre/post hashes of existing participant and
evaluator files are identical. Python bytecode writes were disabled.

The installed public/private targets are byte-identical, SHA-256
`b9f166df0bb7597c695b05eb7d831f457f68f0c0311f6e5be0184d832b5211e3`.
Public/private validator sources are byte-identical and match the frozen manifest;
the planted hash also matches. The manifest records generation 2, frozen at
`2026-08-28T10:59:16.185366+00:00`. Attempt chronology was not independently audited.

## Exact physics and constraints

- Independently recomputed **all 4096 lags** using dense native-integer lag sums,
  not the grader's sparse-pair routine. Counts are exactly 3328/512/256, integer
  energy sum 1024, square sum 1536, with cyclic empty neighbors including 4095/0.
- For the repeated 8192-direction sequence, energy is `a[d % 4096]/2048`.
  Equal antipodal energies give total energy 1, exact momentum cancellation, and
  masslessness symbolically. Independent full-event unordered-pair enumeration,
  doubling off-diagonal contributions, reproduced **8192 directed bins and 4097
  angular bins** using integers only.
- Directed numerator is `2*c[d % 4096]` over `2048² = 4194304`, equivalently
  `c[d % 4096]/2097152`. Both endpoints have numerator 3072 and mass `3/4096`;
  each interior bin has mass `c[b % 4096]/1048576`. Directed and angular numerator
  sums are both 4194304. Self-pairs, antipodal pairs, and lag 2048 are retained.
- Strict key/version/type/length/count/spacing/size checks agree with the published
  contract. Grading is integer-exact over every lag and all four 1024-lag families;
  diagnostic errors give no partial core credit. JSON `-0` is accepted as integer
  value zero, a harmless semantic normalization rather than a tolerance bypass.

## Independent exercise

The bounded audit completed in approximately **38.4 seconds**, without search.
The private planted replay gives `valid=true`, `passed=true`, and both core and
worst-family score 1, with 4096 matched lags. **74 artifact probes** agree between
public/private validators: rotations/reflection, exact byte-cap acceptance,
over-cap rejection, feasible wrong autocorrelation, internal/wraparound adjacency,
malformed tokens/keys/JSON, recursion, nonfinite numbers, symlinks/FIFO/missing files,
and ignored submitted targets/helpers. A feasible label swap fails exact scoring;
its EEC L1 diagnostic also matches independent folded-histogram arithmetic.
**8192 single-lag probes** (+1 and -1 at every lag) fail with exactly the affected
family failing; an all-lag mutation also fails. **14 CLI probes** exercise both
drivers, including the following nonblocking findings.

## Nonblocking findings

1. **Symlink-loop reporting failure** (`evaluator/evaluate.py:55`,
   `participant/check.py:162`): with `--report`, a self-referential `design.json`
   symlink raises uncaught `RuntimeError` during `Path.resolve()`, producing exit 1
   and no rejection JSON. Without `--report`, it rejects normally with exit 0.
   This contradicts the ordinary-invalid reporting contract, but cannot pass an
   invalid witness. The runner must fail closed on nonzero exit or missing reports;
   a future fix should handle resolution errors before report-path comparison.
2. **Hardlink report alias bypasses overwrite guard** (`evaluator/evaluate.py:55`
   and `:61`; `participant/check.py:162` and `:167`): a report path hardlinked to
   `design.json` has a different resolved pathname but the same inode. Successful
   grading then overwrites the artifact with its report. Reproduced only on new
   review-local copies. This requires report-destination/inode control and does
   not turn a mismatching artifact into a witness. Keep reports in trusted separate
   directories; compare file identity as well as paths in a future hardening pass.

Neither issue changes the mathematical feasible set or blocks validity under a
trusted, fail-closed runner with protected evaluator/target/report directories.
Same-user permissions alone are not isolation. External one-hour enforcement,
participant isolation, tournament outcomes, and hardness remain the main session's
responsibility. No changes to existing code are proposed or applied here.

`result.json` contains the required top-level `evaluator_valid: true` and
`blocking_concerns: []`. Reproduction/evidence: `audit.py`, `physics.json`,
`planted.private.json`, `artifact_probes.json`, `cli_probes.json`, and
`protected_file_hashes.json`. Fixtures are private, plant-derived audit material;
do not include this directory in participant allowlists. The runner intentionally
expects a fresh fixtures directory rather than overwriting an earlier audit.
