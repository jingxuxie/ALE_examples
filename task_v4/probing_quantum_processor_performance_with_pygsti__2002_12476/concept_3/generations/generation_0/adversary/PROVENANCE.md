# Private generation record

Primary verification mode: D, hidden prediction. This directory, the evaluator,
its hidden directory, attempt records, and champions must not enter the fresh
agent's filesystem allowlist. Only `participant/` and its empty writable attempt
directory are participant inputs. The main session owns runner isolation and
the empirical hardness decision. No fresh-agent invocation occurred here.

## Paper connection

Nielsen et al., *Probing quantum processor performance with pyGSTi*,
arXiv:2002.12476 (2020), discusses drift analysis in section V.A.4, model testing
and validity in V.B.4, context comparisons in V.B.7, and custom physical model
parameterizations in V.C. The task extends that modeling question to predictive
transfer, not to reproduction of the package's GST algorithm.

Sources inspected on 2026-08-28:
- https://arxiv.org/pdf/2002.12476
- https://github.com/sandialabs/pyGSTi
- https://github.com/sandialabs/pyGSTi/blob/master/pygsti/models/model.py
- https://pygsti.readthedocs.io/en/develop-with-notebooks/markdown/objects/ModelParameterization.html
- https://pygsti.readthedocs.io/en/docs-preview/markdown/guides/drift/DriftCharacterization.html

No source code or data are copied from these projects. This is a newly generated
classical-quantum hidden-state model with fixed public physical structure. It is
not claimed to model a real device dataset, and there are no hidden releases or
repository facts the participant must discover.

## Information and fairness

Device parameters, seeds, exact labels, the fast simulator, density-matrix audit,
and counterfactual diagnostics are generation privileges. The physical model,
parameter bounds/distribution, circuit contexts, and development counts are
public. Four fixed devices occur in every split. Query generation has seeds
independent of parameters and binomial sampling, with no performance-based
selection. Training and development counts jointly contain over 37 million shots
per device, with all preparations, all measurement axes, all announced circuit
families, and a broad time interval. Exact totals are in the dataset summary.

The frozen targets were specified before dataset evaluation or fresh attempts.
No target was relaxed after observing the baseline. A perfect prediction vector
used inside evaluator audits is only an internal consistency test. It is not a
participant solution and does not demonstrate recoverability. Local Fisher
information, if reported, is likewise a local diagnostic, not proof of global
identifiability. Solvability remains unknown unless a data-only fit passes.

## Commands

From concept_3, with `PYTHONDONTWRITEBYTECODE=1` and BLAS thread count limited:

```
python adversary/build_data.py
python participant/baseline/predict.py --input participant/input --output adversary/baseline_predictions.json
python evaluator/evaluate.py --submission adversary/baseline_predictions.json --output adversary/baseline_score.json
python adversary/audit.py
python adversary/diagnostics.py
python adversary/freeze.py
```

The generator refuses to overwrite existing datasets unless explicitly asked.
Do not rebuild any launched generation. The evaluator accepts only static JSON,
uses no participant imports, rejects symlink and other non-regular submissions,
opens files with O_NOFOLLOW when supported, and never executes candidate code. Its runtime is
scoring time; training runtime and resource limits are the main runner's
responsibility: eight allowed CPUs and an 8 GiB RLIMIT_AS address-space limit
per process, not an aggregate-RAM budget.

After a fresh failure, use `hard_open_candidate` unless a genuine data-only
passing solution is known. A known-parameter physical oracle alone is not such
a solution. After success, the main session may run the champion ratchet.
