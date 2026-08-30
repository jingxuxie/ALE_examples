# Final isolation audit v3 — fifteen completed attempts

Updated 2026-08-28T22:32:36.531262+00:00. **Verified with documented historical and attestation limits; no concrete new isolation blocker observed.**
Coverage is **A v1–v6, C v1–v8, D v1**: thirteen accepted historical runs inherited from v2, plus newly inspected completed A generation-2 v5/v6. No scores, achievability or hardness are certified here.

## New completed runs

| Run | Actual client model / effort | Elapsed seconds | Exit / timeout | Output files |
| --- | --- | ---: | --- | ---: |
| A G2 v5 | ultima-alpha / high | 2688.451266938 | 0 / false | 191 |
| A G2 v6 | ultima-alpha / high | 3417.253506517 | 0 / false | 286 |

Actual startup headers report Codex **0.150.1**, provider `openai`, approval `never`, custom permissions and the participant working directory. Sessions are `01a04a3f-15bc-74d3-9f80-9be13e1b5690` and `01a04a3f-18cc-7163-9523-5861b8a92571`, distinct from one another and all thirteen inherited IDs. Exact commands and prompts match the reviewed launcher; no resume is used. The JSON lists all fifteen completed runs and their evidence epochs. All fifteen completed normally below 3600 seconds; the maximum is **3417.253506517 seconds**.

Completed metadata and bounded startup samples, not ongoing artifacts, were read. Entire completed session logs were hashed but not replayed. Startup stdin notices or early delayed/unsuccessful shell commands are not classified as a failure of the completed attempt.

## Freeze and public isolation

Both launch participant maps match the prelaunch G2 freeze at **2026-08-28 21:20:39.032140 UTC**, preceding both launches. Both final manifests record the participant unchanged. Current **16/16 public files** and **51/51 frozen asset pins** match; calibration hash remains `e11ed03ca6ab38cf42c2afc61660793bcc8d0013e4bf22b52b64cf60ec5b2b14`.

Freeze: `concept_1/adversary/ratchet_2_admission/freeze_manifest.json`; SHA-256 `b1d9c9deb0f1384ef816a85b224f6b6b21550132e2da6c25aaf5ebe6d6738ff6`.

The public tree has no symlinks, special entries, bytecode/cache files, private states/logs or development artifacts. It remains the reviewed four legitimate prior-champion production modules in each baseline/workspace, documentation, scoring and three examples. Its provenance is additionally bound to the accepted `authoring/ratchet_two_review.json`. G2 is compared against its own freeze; legitimate preparation after the G1 archive is not misclassified as mutation of G1.

The supplied wrapper exposes read-only participant plus initially-empty writable output as its benchmark roots, with minimal OS and explicit Codex runtime reads. Evaluator/hidden labels, adversary, champions, other submissions, authoring and prior task versions are not allowlisted. The harness rejects nonempty output and existing audit directories, and records both checks. This is construction and manifest evidence, not an independent initial-directory snapshot or continuous mount trace.

## Stable outputs and post-stop checks

Both **complete output trees, 477 regular files**, match their completed launcher manifests. Full content and recorded file/directory metadata are stable across samples:

- First: **22:25:15.528088–22:25:15.581086 UTC**, August 28, 2026.
- Second: **22:25:29.190614–22:25:29.252654 UTC**.
- Separation from the first completed sample to the next start: **13.609513323 seconds**.

There are no output symlinks, special entries or caches, no mismatch, no file changing during hashing, and no observed post-completion/deadline file mtime. Mtimes are mutable corroboration, not a trusted write log. Canonical complete-output hashes are:

- v5: `133b717c5692d889b8aacc8c52b5e291b13ede76dfde64881161e1b93d86d4db`.
- v6: `249826051cfe6e1bc79b23096ccd36e0de27bc3144e7879478b1a9b7be2a0ed9`.

Read-only host-scope process snapshots saw **13,987 / 13,938 visible processes**, inspected **11,813 / 11,746 descriptor entries**, and observed neither recorded launcher PID, a live launcher group/session survivor, an original-output working directory, nor a writable original-output descriptor. No process was killed or signaled. Matching is restricted to the original v5/v6 source-output roots; trusted grader `/tmp` copies are not classified as fresh writers. Successful samples occurred after grading was reported complete and found no matching grader-command reference; no grading or portfolio report was opened.

**Visibility limits:** the two scans had 37/10 process-stat failures, 7/27 command-or-cwd failures, 7/27 descriptor-directory failures and one descriptor-link race each. They inspect active same-UID descriptors, not every other-UID process. `/proc/1/ns/pid` is inaccessible; an initial read-only collection stopped there and was repeated with that field explicitly unavailable. No 90-second scan or 4096-descriptor-per-process cap was reached. These samples cannot rule out every inaccessible, dormant or namespace-aliased writer. The claim is **none observed**, not universal quiescence attestation.

The work limit is **3600 seconds**, not 3610. The additional ten seconds is termination cleanup only. Neither new run reached that path. An observed detached writer, output mismatch or post-stop mutation would be infrastructure/provenance-inconclusive, not scientific difficulty; none was observed.

## Runner epochs and inherited qualifications

- **Earlier eleven:** A v1/v2, C v1–v8 and D v1 inherit runner SHA-256 `9625e083fce46db66609c63bca91b7177bd6165ac79e2efbfb02c8cc5aa43da3`.
- **Later four:** A v3–v6 use `06f4693741de6587283d2cf78d91895e5a74c1230c9960b5457f8cc536cf0394`; new v5/v6 actual metadata and G2 freeze match current bytes. Its numerical thread-ceiling additions were already reviewed in v2; filesystem/network selectors remain the reviewed construction.

Current harness and freeze-builder hashes also match the freeze. The inherited restricted-network-default finding stands for the unchanged selectors and matching client version. No new config sweep, network probe, kernel/backend/remote-weight attestation or exhaustive log replay is claimed.

Historical C generation-0/1 public bytecode hash-coverage gaps remain preserved: cached code matched authorized original public checker code, while generation-1 cache was stale against adjacent source. This is not an observed privileged construction-code leak. Original C baseline source was authorized; later tensor-only provenance and retrospective mount/config/context limits are inherited unchanged from v2, not newly replayed.

## Preservation and conclusion

The original audit and v2 JSON/Markdown remain byte-identical; their four hashes and the thirteen inherited records are bound in the new JSON. Old output trees were not redundantly rehashed. **Only `authoring/final_isolation_audit_v3.json` and `authoring/final_isolation_audit_v3.md` are written.** No source/public/evaluator/status/attempt edit, agent launch, process signaling, numerical simulation, grade, test or portfolio inspection was performed.

**Fifteen completed-run operational isolation/provenance assurance is supported within the stated bounds. No concrete new blocker is observed. Scores, scientific achievability and hardness remain separate from this audit.**
