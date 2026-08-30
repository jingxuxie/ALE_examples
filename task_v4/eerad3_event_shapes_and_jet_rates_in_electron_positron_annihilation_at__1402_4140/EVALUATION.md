# Reproducing the discovery evidence

All paths below are relative to this package. Python 3, NumPy, SciPy,
scikit-learn, mpmath, gfortran, a C++ compiler, and bubblewrap are available in
the generation environment. The executable-code evaluators require a Linux
host that permits bubblewrap user/PID/network namespaces. A restrictive outer
sandbox can prevent namespace creation; that is an infrastructure failure,
not a participant failure. Do not disable the evaluator's isolation.

Current-generation evaluation interfaces:

```
python3 concept_1/evaluator/evaluate.py SUBMISSION_DIRECTORY --report SCORE.json
python3 concept_2/evaluator/evaluate.py --submission WITNESS.json --output SCORE.json
python3 concept_3/evaluator/evaluate.py --artifact SOURCE_DIRECTORY --output SCORE.json
```

The prediction baseline is `concept_1/participant/baseline`. The witness
baseline and workspace-repair baseline are documented in their participant
trees. Baseline/champion and fresh-attempt score records are separate from
the participant assets.

Each `adversary/frozen_generation_N.json` seals the participant and evaluator
files before a fresh run. Earlier generations are preserved in corresponding
`adversary/generation_N_snapshot` directories. Use their evaluator and hidden
data when reproducing an earlier generation, rather than the current target.
`research/audit_package.py` checks these seals and the minimal package layout.
It also checks the actual model/session headers and that saved submissions
have not changed since their fresh sessions ended.

Concept 3's final release includes a conservative resource-instrumentation
audit of generation one. Its original cases, numerical tolerances, repetition
count, and 18x threshold remain unchanged. The trusted parent now accounts
for native child and descendant CPU instead of trusting a submitted program's
TIME value. The original sealed evaluator and original scores remain in the
generation-one snapshot and attempt records; separate audited scores and the
`adversary/audited_release.json` manifest identify the released instrumentation.
The uncommitted throughput proposals failed measurement-stability controls;
they are not task generations, fresh attempts, or evidence of hardness.

`research/run_attempt.py` invokes the supplied allowlisted runner with the
requested model, a read-only participant tree, an initially empty output
directory, and a 3600-second wall limit. Runner logs, model/timeout records,
input hashes, and output hashes are saved outside the writable attempt tree.
Private solvers, native oracle sources, search cases, hidden labels, earlier
attempts, and generation research are not mounted into a fresh session.
