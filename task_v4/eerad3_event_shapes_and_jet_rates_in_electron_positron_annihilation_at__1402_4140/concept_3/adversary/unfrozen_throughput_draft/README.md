# concept_3 — unique-event EERAD3 mapping repair

Generation two is being calibrated for main review, never frozen or launched
by these scripts. Only `participant/` is public. Prior submissions, private
artifacts, hidden seeds/references, evaluator code, and operator status must
not be exposed to a participant.

## Active target

- 10,004 distinct momentum inputs, all executed exactly once per native process.
- All original 104 correctness cases and the complete 1,724-case intermediate
  corpus remain unchanged as a prefix; every measured output record is checked.
- Original physical/numerical gates, including orientation uncertainty, remain.
- Public and trusted wrappers use the same B4 aligned struct-of-arrays protocol
  and `eerad3_batch(void*,void*,int32_t)` shared-library entry. Trusted code
  prepares resident shared arrays before loading any submitted library; small
  per-event copies preserve mutable Fortran argument semantics. The kernel ABI
  and three source-native files remain unchanged.
- Five alternating paired CPU ratios use a read-only in-namespace supervisor.
  Compiled /work is read-only at run time; all writable state is fresh per run.
- The predeclared threshold is min(8, 0.45 * the smaller of two independently
  measured incumbent paired medians), rounded downward to 0.001 and fixed
  only after repeatability and private-margin checks, before any fresh attempt. See target.json/RESOURCE.json
  for the actual calibrated limit, not the archived 18x repetition-based proposal.
- Trusted per-run user/system CPU and wall seconds diagnose timing overhead;
  evaluator errors always include zero scores, valid=false, and a separate
  invalid-submission/environment/measurement classification.
- The only subtraction is trusted child setup before library loading: its CPU
  record travels on a private pipe closed before candidate code starts. Parent
  kernel accounting independently charges all constructors, native work, and
  descendants. Reports expose native, full-child, and excluded-setup CPU.

## Operator commands

```sh
python3 adversary/ratchet_unique.py audit
python3 evaluator/evaluate.py --artifact participant/workspace --output adversary/local_unique_baseline.json
python3 evaluator/evaluate.py --artifact adversary/adaptive_wide --output adversary/local_unique_adaptive.json
```

Native builds/evaluations require host escalation when the outer sandbox blocks
bubblewrap netlink setup. Native code still runs under bwrap --unshare-all with
no access to hidden or host task files. No unsandboxed evaluation fallback exists.

## Evidence and reproduction

`adversary/generation_2_science.md` derives an independent rest-frame sphere
oracle and documents the valid light/doubly-soft-radiator failure region.
`adversary/unique_production_batch/validation.json` records 140/190-digit
geometric, 160-digit direct-DAK, and 180-digit independent rest-frame checks.
`adversary/generation_2_unique_*_score.json` are the active scores;
`adversary/generation_2_unique_controls.json` covers orphan CPU accounting,
timer interposition, read-only storage, fresh tmpfs, complete binary checking,
and rejection of prepopulated all-zero records after an early native exit.
The constructor probe verifies library initialization runs only in the timed
child and its CPU is charged, not hidden in trusted setup.
`adversary/check_binary_contract.py` verifies the public encoder against the
entire trusted corpus, strict B4 decoding, and all evaluator exception schemas.
`adversary/generation_2_unique_preparation.json` commits the active package;
`status.json` states readiness and the private feasibility result.

The preparation sequence is `prepare_unique_batch.py`, then
`ratchet_unique.py stage`, `ratchet_unique.py controls`,
`ratchet_unique.py calibrate`, `ratchet_unique.py repeat`,
`ratchet_unique.py finalize`, and `ratchet_unique.py audit`, all under
`adversary/`. The current two-campaign policy was separately declared with
`ratchet_unique.py predeclare` before either sealed-input campaign.
Measurement commands cannot commit a target. Stage/commit must precede any
fresh attempt and are not intended to overwrite a committed/frozen target.
Main reviews and performs the actual generation freeze and fresh attempt.

## Preserved history

`adversary/generation_1_snapshot/` preserves all 40 original sealed files plus
status and the seal itself. Generation one's actual champion is private.
`adversary/generation_2_repeated_proposal/` preserves the superseded 1,724-case
repeated-work proposal. Do not use its reports, `prepare_generation_2.py`,
`validate_generation_2.py`, or the original scaffold/freeze routines to evaluate
or overwrite the active unique-event target. There is no generation-two freeze
and no new agent launch in this preparation.

`adversary/unique_small_record_draft/` preserves the rejected small-record
binary-I/O draft and its noisy timing evidence. Its 1.31–5.46x incumbent ratios
do not justify hardness and were never converted into a committed target.

`adversary/bulk_pipe_draft/` preserves the intermediate bulk-read/pipe-input
measurements. Its 4.684x incumbent median is diagnostic, not active hardness
evidence. The intermediate sealed-input allocating draft is separately preserved
in `adversary/allocating_memfd_draft/`. Its 2.903x incumbent median, 1.55–8.59x
paired spread, and large native page-allocation/copy overhead do not establish
resource hardness. The active B4 resident-array evaluator charges all native
library loading, constructors, data access, output stores, arithmetic, and
descendant user+system CPU. No submitted code executes during trusted setup.
`adversary/mmap_child_draft/` preserves the rejected child-mapping backend and
its noisy 2.061x incumbent median. Neither old draft fixes the active budget.
