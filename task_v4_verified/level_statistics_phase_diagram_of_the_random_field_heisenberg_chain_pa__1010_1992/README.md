# Pal–Huse hardness discovery

The selected retained task is **concept_2: spectrally matched disorder layouts**,
verification mode C. Its two isolated one-hour `ultima-alpha` attempts fail the
fixed hidden robustness requirements, while a private portfolio design passes
every requirement. `concept_2/status.json` records the evidence and decision.

`FINAL_REPORT.md` and `status.json` summarize all three concepts after the
tournament and ratchets. The participant mission for each concept is its
`participant/TASK.md`; the complete executable definitions are in the provided
input and workspace files. No asymptotic many-body-localization phase claim is
graded. The counterexample concept challenges an explicitly supplied proxy,
not a claim attributed to the paper.

## Separation

For a fresh solver, expose **only one concept's `participant/` directory** and
an empty writable submission directory. Everything else is organizer-private:
evaluators, hidden data, attempts, champions, adversarial searches, source
archives, and authoring scripts. Do not distribute this complete discovery
directory to participants. The tested sessions use the requested allowlist
runner, no shared main-session context, no network, and a 3,600-second limit.

After a ratchet is completed, the canonical `participant/` and `evaluator/`
trees contain the final tested generation. Historical frozen generations and
their original attempt logs remain available under `generations/`. Attempt
metadata identifies the exact task snapshot and checksums; promotion preserves
the original invocation and adds snapshot locations.

## Run the selected baseline and evaluator

From this directory, with Python, NumPy, and SciPy available:

```bash
python3 concept_2/participant/baseline/solve.py --output /tmp/pal_huse_baseline/design.json
python3 concept_2/evaluator/evaluate.py --submission /tmp/pal_huse_baseline --output /tmp/pal_huse_baseline_score.json
```

Reproduce the privileged achievability certificate, without executing any
submitted code:

```bash
python3 concept_2/evaluator/evaluate.py --submission concept_2/adversary/portfolio_candidate --output /tmp/pal_huse_portfolio_score.json
python3 authoring/audit_portfolio.py
```

Concept 1 evaluates a directory containing `predict.py` with the
`--submission DIRECTORY --output REPORT.json` interface. Its inference sandbox
requires Linux `bwrap`, `taskset`, `prlimit`, and libseccomp; numerical Python
dependencies include scikit-learn and joblib. A namespace or sandbox failure is
reported as an infrastructure error, not scientific failure. Concept 3 uses
`python3 concept_3/evaluator/evaluate.py WITNESS.json --output REPORT.json`.

## Evidence

- `authoring/discovery.md`: ten considered concepts and inspected sources.
- `authoring/physics_audit.json`: independent Hamiltonian and observable checks.
- `authoring/isolation_audit.json`: inference filesystem, network, and CPU isolation.
- `concept_*/adversary/`: committed targets, search evidence, and private certificates.
- `concept_*/attempts/v_*.run.json`: limits, isolation, timing, and artifact hashes.
- `concept_*/attempts/v_*.score.json`: actual evaluation results.
- `authoring/final_audit.json`: completed-package audit, produced by
  `python3 authoring/audit_package.py --final`.
