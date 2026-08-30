# Final isolation audit: eleven completed attempts

Extended at 2026-08-28T16:00:32.776286+00:00. Scope: A v1/v2, C v1-v8, and D v1. This extension adds only four completed runs; no new agent, submitted program, evaluator, or network probe is run.

**Conclusion: supported with the stated evidence limitations; no observed isolation violation.** All eleven launch records and reviewed startup headers identify `ultima-alpha`, high effort, provider `openai`, Codex `v0.150.1`, approval `never`, and custom permissions. Eleven session IDs are distinct. All return zero without timeout, within 591.761-1757.175 seconds (under one hour). This is an isolation/provenance conclusion, not a grading or hardness determination.

| Attempt | Frozen target | Seconds | Session ID |
|---|---|---:|---|
| A v_1 | A launch freeze | 1663.328 | `01a048ef-e385-7c33-95af-e71a3ad755dd` |
| A v_2 | A launch freeze | 1757.175 | `01a048ef-e1f5-77f2-9b7d-b200d5557bc6` |
| C v_1 | critical-vacuum-v1 | 863.229 | `01a0484e-f57f-7f82-9b4c-78db937e61a7` |
| C v_2 | critical-vacuum-v1 | 756.549 | `01a0484e-e8ea-7cc0-aff9-798c10c19066` |
| C v_3 | critical-vacuum-v2 | 612.896 | `01a0486f-93d3-75d2-a2ae-320b0a088eb2` |
| C v_4 | critical-vacuum-v2 | 927.579 | `01a0486f-92c2-7f20-a123-9a14da336647` |
| C v_5 | critical-vacuum-v3 | 691.938 | `01a048b0-2b9e-76c2-be4d-11bbc5bd6d7f` |
| C v_6 | critical-vacuum-v3 | 668.098 | `01a048b0-2b73-7f71-a7da-5e7853b9dd43` |
| C v_7 | critical-vacuum-v4 | 591.761 | `01a048f2-6cc8-7010-884c-028fc9fcd566` |
| C v_8 | critical-vacuum-v4 | 758.220 | `01a048f2-6cbf-7750-87d8-2f5b31005b2e` |
| D v_1 | phi4-gap-v1 | 668.210 | `01a04872-cbcd-77f2-b5e9-86fdac262020` |

## Four newly verified runs

- A v_1: **1663.328 seconds**, return 0, no timeout, immutable participant; freeze precedes launch by 0.252798 seconds.
- A v_2: **1757.175 seconds**, return 0, no timeout, immutable participant; freeze precedes launch by 0.244957 seconds.
- C v_7: **591.761 seconds**, return 0, no timeout, immutable participant; freeze precedes launch by 360.916001 seconds.
- C v_8: **758.220 seconds**, return 0, no timeout, immutable participant; freeze precedes launch by 360.908614 seconds.

- **A freeze:** `concept_1/adversary/launch_freeze.json` at `2026-08-28T15:14:31.276608+00:00`; all 14 public regular files equal both launch manifests and the current complete public tree. Its prelaunch runner/tournament hashes match the reviewed files.
- **C freeze:** `concept_2/adversary/ratchet_3/freeze_manifest.json`, created `2026-08-28T15:11:18.096044+00:00`; all 10 public regular files equal both launch manifests and the current complete tree. The frozen and actual public contract is **critical-vacuum-v4**, ratchet generation 3, for v7/v8.
- Neither new public surface contains symlinks or bytecode. A two-file baseline bytecode quarantine is under `concept_1/adversary/public_cache_quarantine`, outside the agent allowlist. C public bytecode is absent; its separate private-evaluator cache quarantine and record are also outside the allowlist. Every current public regular file is included in this extension's hash comparison.
- All **385 recorded output entries** still match, including the original 125 across seven older runs (1,706,004 bytes rehashed).
- Current C baseline inventory is only `README.md` and `state.npz`; its exact SHA-256 `036e6d9068edb0ac38ce3d3fc4bd935dffcd0b86189f5af25bc4b2f46dde0bea` matches the new freeze and launches. Private champion/portfolio construction code is not reopened. Earlier g1/g2 numeric baseline inspections remain historical evidence in the JSON.

## Preserved isolation controls

- The identical reviewed wrapper starts new `exec --ephemeral` sessions. The launch guard records empty outputs; the filesystem profile allows only the selected participant read-only and that attempt output writable, plus necessary OS/Codex runtime. Private evaluator, labels, adversary, champions, other submissions, authoring and prior generations are not allowed benchmark inputs.
- The existing **restricted shell-network** finding stands unchanged. Missing `network.enabled` does not enable internet; web search is separately disabled. The prior 20-config review was not repeated. No live egress test was added; the optional actual Codex-sandbox preflight remains documented in the JSON.
- Public original-generation baseline construction code, mode-C exact observables/checker, and D training/development labels remain authorized inputs. Their intentional publication is not private-asset leakage.

## Bounded methods and caveats

- Only four new headers and bounded log tails were reviewed; new logs were hashed as evidence, not replayed. None of the seven old session logs was reopened or rehashed. No A/C grading record was read, and A grading was neither awaited nor inferred. No private portfolio was inspected.
- The historical `__pycache__` manifest gap remains confined to C g0/g1: their cached bytes were identified earlier as the original public checker, not privileged optimizer code. New A/final-C full public file comparisons have no such current omission.
- The report is operational provenance, not an exhaustive kernel/syscall or historical shared-controller-context attestation. A now has a matching prelaunch harness snapshot; the original seven-run evidence limitations remain. Explicit model arguments and matching headers suffice for requested model provenance; **remote-weight attestation is not required**.
- `Reading additional input from stdin...` appears in all eleven startup headers and is not a failed attempt. All eleven completion records are normal; scientific scores are a separate question.

Only `authoring/final_isolation_audit.json` and `authoring/final_isolation_audit.md` are updated. No participant, evaluator, attempt, champion, supplied runner, or other artifact is modified. The JSON retains original evidence and adds the four freeze chains, session records, complete public manifests, quarantine references and bounded output rechecks. No hardness claim is made.
