# concept_3 — solved generation-one mapping repair

The actual generation-one ultima-alpha submission solves this task. No harder
ratchet survived validation: the proposed throughput target failed its declared
measurement-robustness policy, and the bounded countersearch found no champion
quality failure. There is one evaluated generation, zero ratchets, and no fresh
generation-two attempt. This concept is not retained as a hard survivor.

## Audited release

The public native sources, ASCII driver, original 104 correctness cases,
300 timing repetitions, three-trial medians, numerical tolerances, and fixed
18x resource allowance are restored from the sealed generation-one snapshot.
Only CPU instrumentation and associated validation/documentation are audited.

The immutable in-namespace supervisor uses nondumpable parent
`RUSAGE_CHILDREN` accounting, acts as a child subreaper, and counts full native
startup, I/O, computation, and all reaped descendants. Candidate-reported
`CPU_TIME`/`TIME` values are ignored. Runtime `/work` is read-only and `/tmp`
is fresh for each run. No new CPU pinning is imposed. Every trial's
oracle and metamorphic checks are applied. No new resource target is calibrated.

`status.json` contains the original fresh score and separate audited baseline,
private feasibility, and actual fresh-v1 scores. `adversary/audited_release.json`
seals the audited participant/evaluator files and unchanged target hashes.
Original evaluation records are never overwritten. Only `participant/` is public;
all private submissions, controls, references, and countersearches remain private.

## Validation and history

- `adversary/validate_audited_release.py all` reproduces scores and release controls.
- `adversary/release_audit_controls.json` records CPU spoof, orphan accounting,
  read-only execution, fresh storage, protected supervisor, and output-schema tests.
- `adversary/release_artifact_guard.json` verifies directory symlinks are rejected
  before any candidate source is copied.
- `adversary/release_audit_unit_controls.json` verifies covariance on all three
  trials and classifies pristine-baseline failures as infrastructure errors.
- `adversary/champion_quality_search/reference_summary.json` records all 12,000
  native/reference comparisons, zero failures, and ten independent oracle checks.
- `adversary/generation_1_snapshot/` preserves all 40 original sealed files.
- `adversary/unfrozen_throughput_draft/` preserves the rejected release draft;
  earlier timing drafts and their no-go evidence remain under `adversary/`.
- `adversary/idle_core_no_go.json` records main's final failed robustness check
  on an independently selected initially idle core; no new target is committed.

Native validation requires host escalation if the outer sandbox blocks bwrap
netlink setup. Candidate code still runs isolated; there is no unsandboxed fallback.
