# Final isolation audit v2

Updated 2026-08-28T19:41:58.289267+00:00. **verified_with_documented_historical_and_attestation_limits**. This extends, but does not overwrite, the original eleven-run audit. Thirteen completed attempts are covered: A v1-v4, C v1-v8, and D v1. It is not a grading or hardness assessment.

## New completed runs

| Run | Actual header / effort | Elapsed seconds | Exit / timeout | Output files |
| --- | --- | ---: | --- | ---: |
| A generation 1 v3 | ultima-alpha / high | 2944.589869573 | 0 / false | 199 |
| A generation 1 v4 | ultima-alpha / high | 3342.360591723 | 0 / false | 23 |

Actual client headers report OpenAI Codex 0.150.1, provider `openai`, approval `never`, custom permissions, and the participant working directory. New session IDs are `01a049a7-99e0-70f1-b51d-d7e2488b595c` and `01a049a7-9824-7492-80e9-752236544264`, distinct from one another and all eleven historical IDs. Requested commands and exact prompts match the reviewed launcher construction. The startup stdin notice is not treated as a failure.

## Freeze and output integrity

Both launch participant maps match `concept_1/adversary/ratchet_1_admission/freeze_manifest.json:1`; both completed manifests record the participant unchanged. All 16 current public files match that prelaunch freeze, with no public symlinks, special files or bytecode caches. The six infra5 certificate source hashes still match; this audit does not rerun its 15 recorded runtime checks.

Both complete output trees match their completed launcher manifests. Two full content-and-metadata snapshots, separated by at least 12 seconds, are stable; no output symlinks or special entries were found. V3 also matches its earlier 19:29 UTC completed-only snapshot. New program hashes and canonical output-map hashes are recorded in the JSON report; graders should continue to bind to these completed manifests, not mutable later artifacts.

## Work limit and quiescence

The work limit is **3600 seconds**, not 3610. The harness's additional 10 seconds is timeout cleanup after process-group SIGTERM, followed by SIGKILL if needed. Neither new run used that timeout path: both exited voluntarily below 3600 seconds by recorded monotonic and UTC elapsed measures.

Read-only **host**, not ordinary nested-sandbox, process snapshots checked the recorded launcher groups, matching output working directories and open output descriptors. No live launcher-group survivor or writable output descriptor was observed in the inspected snapshots; no output mutation or post-deadline mtime was observed. Detailed snapshot times and inaccessible/vanished-process counts are recorded in JSON. These are bounded observations, not proof that every dormant or inaccessible detached process is absent. Mutable mtimes are corroboration, not a trusted clock or write log. Any observed detached writer or post-deadline mutation would make the run infrastructure/provenance-inconclusive, never evidence of hardness.

## Isolation and policy

The supplied wrapper's benchmark roots remain read-only participant plus initially-empty writable output, alongside minimal OS and explicit Codex runtime files. Evaluator, labels, adversary, champions, other attempts, authoring and prior task versions are not allowlisted. Launches use `codex exec --ephemeral`, not resume, with explicit ultima-alpha/high and no escalation or web-search tool. Empty-output assurance comes from the construction and recorded checks, not an independent launch-directory snapshot.

The original eleven-run wrapper hash and the new generation-1 wrapper hash are recorded separately; they are not conflated. The current wrapper matches the new freeze, including its numerical thread-limit additions. The previously established restricted-network default remains the finding for the matching Codex version and policy selectors. No new network probe or repeated config sweep was performed; this is not new per-run kernel/network attestation or remote-weight attestation.

## Preserved historical caveats

The original C generation-0/1 public bytecode coverage gap remains explicitly retained. Its cached code matched the authorized original public checker; the generation-1 cache was stale against its adjacent source. That is a manifest-coverage caveat, not an observed privileged-code leak. The original audit's C tensor-only baseline provenance, allowance for original-generation public baseline source, and retrospective mount/config/context limitations are inherited unchanged.

Only the new completed manifests, bounded startup samples, output hashes and fixed source/freeze evidence were inspected. Old logs were not replayed, old eleven output trees were not redundantly rehashed, and no grade, runtime regression, scientific query, fresh agent or submission edit was performed. Both original audit files retain their prior SHA-256 hashes. **No scientific success or hardness conclusion is made.**

## Concrete new issues

None observed within this bounded review.

Machine-readable evidence: `authoring/final_isolation_audit_v2.json:1`. Resource success-predicate review: `authoring/resource_guard_final_review.json:1` and `authoring/resource_guard_final_review.md:1`.
