# pyGSTi-seeded hardness discovery

Only a concept's `participant/` tree is a solving asset. Evaluators, hidden data,
authoring sources, adversarial searches, attempt logs, and generation archives
are private. The three primary verification modes are A (baseline improvement),
B (counterexample), and D (hidden prediction).

## Scoring artifacts

From this directory, each evaluator accepts:

```
python concept_N/evaluator/evaluate.py --submission ARTIFACT --output SCORE.json
```

The artifacts are `design.json`, `witness.json`, and `predictions.json` for
concepts 1, 2, and 3 respectively. No submitted executable is loaded. The
baseline invocation and current score contract are in each `participant/TASK.md`.

The validated scoring runtime is Python 3.10.12, NumPy 1.21.5, and SciPy 1.8.0;
the two library versions are pinned in `requirements-evaluator.txt`. pyGSTi is
not required or installed in the tested runtime. Numerical and physical checks
are retained with each evaluator's private evidence.

For a recorded, completed tournament attempt, use the immutable-asset checks:

```
python authoring/score_attempt.py concept_1 --attempt v_1
```

Historical scored generations remain reproducible under `generations/` after a
champion ratchet. `champions/` contains validated static artifacts, not private
test answers. A current champion may be repackaged as the public baseline, but
its work logs and private challenge results are never exposed.

## Isolation and evidence

`authoring/run_fresh.py` invokes the supplied allowlist runner, not edited by this session, with
`ultima-alpha`, a fresh runtime, ephemeral history, read-only participant assets,
an initially empty writable attempt directory, disabled command networking, and
a 3,600-second deadline. Native isolation checks are in
`authoring/isolation_audit.json`. Every attempt records hashes and launch/exit
metadata beside its output directory. CPU affinity and per-process address-space
limits are recorded where prescribed.

The shared runner's numerical-thread defaults changed during the tournament.
Both exact versions and a verified diff are preserved under `authoring/`; the
filesystem and networking isolation settings did not change.

The paper, official source snapshots, concept inventory, and review of the older
local task are private authoring evidence. Independent simulator checks,
malformed-input tests, baseline scores, search results, and achievability evidence
are in each `adversary/` directory. An internal perfect-label check is not treated
as a solution to the prediction task.
