# Honeycomb memory hardness discovery

Three paper-seeded concepts use different primary verification modes:

| Concept | Mode | Artifact / interface |
|---|---|---|
| `concept_1` | A: baseline improvement | Submission directory containing `solve.py`; predict logical-frame bits from source-native noisy circuit syndromes. |
| `concept_2` | C: design construction | `design.json`; a 24-site local-Clifford supercell, checked by exact all-four-logical erasure correctability. |
| `concept_3` | D: hidden prediction | Submission directory containing `solve.py`; predict held-out aggregate experiment probabilities. |

Each participant contract is `concept_N/participant/TASK.md`. Detailed formats live under its workspace. Hidden data, generator privileges, search results, and fresh-agent logs are outside participant trees.

## Scoring environment

The validated environment is Linux x86-64, Python 3.10, NumPy and SciPy, with Landlock and libseccomp available. Concept 1 vendors its Stim/PyMatching dependencies inside the participant workspace. Concept 2's evaluator and participant checker use only the Python standard library. Concept 3 vendors NumPy and uses the host SciPy. No external solver service is needed to score an existing package.

From this directory:

```
python concept_1/evaluator/evaluate.py /path/to/submission --output score.json
python concept_2/evaluator/evaluate.py /path/to/design.json --output score.json
python concept_3/evaluator/evaluate.py /path/to/submission --output score.json
```

Executable submissions run with a cleared environment, read-only participant/submission access, isolated writable scratch space, network/process-inspection denial, one CPU core, and declared wall/memory limits. Concept 2 executes no submitted code and rejects links, special files, malformed schemas, and oversized artifacts.

The fresh-agent harness `authoring/run_tournament.py` calls the supplied `run_allowlisted_codex.sh` without editing it, with model `ultima-alpha`, high effort, a read-only participant tree, an initially empty writable attempt directory, and a 3,600-second limit. Logs and complete timing/provenance records are siblings of attempt directories, not agent-visible assets. The archived stdin-only startup retry did not reach inference and is excluded from scientific attempt counts. An external shared-runner update added four-thread numerical-library ceilings before the final independent design replication; both runner versions are archived, and `authoring/runner_version_audit.json` verifies that their file/network isolation is identical.

## Generations and evidence

Targets and hidden tests are frozen before each fresh attempt. A solved generation is preserved before a ratchet; its best submission is copied into `champions/generation_N`. For archived executable evaluators, the shared launcher is restored by:

```
python authoring/replay_generation.py concept_2 1 concept_2/champions/generation_1/design.json
```

Concept 2 generation 2 keeps the original 0.85 core / 0.60 worst-group thresholds but replaces nominal erasure profiles with the independently confirmed dense-IID failure regime. Its 36,864 hidden supports are new. The known nominal private design does not establish achievability of this dense generation.

Per-concept `status.json` and attempt score files record the empirical outcome. `authoring/provenance.json`, evaluator validation records, and `adversary/` distinguish source-native evidence, private searches, and unknown achievability. A failed private search is not an impossibility proof.
