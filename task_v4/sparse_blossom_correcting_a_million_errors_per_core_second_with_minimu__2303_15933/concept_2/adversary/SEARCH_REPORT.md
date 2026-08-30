# Privileged search and feasibility report

DO NOT EXPOSE this directory, native code, logs, witness, or report to participants.

## Research and interpretation

Primary sources were inspected on August 28, 2026: Sparse Blossom
arXiv:2303.15933v2 sections 2.1–2.3; Bravyi–Suchara–Vargo arXiv:1405.4883;
Smith–Brown–Bartlett, DOI 10.1038/s42005-024-01883-4; and Lin arXiv:2510.06531.
The target falsifies a universal logical-confidence surrogate inference, not
Sparse Blossom's matching correctness or any cited paper's theorem.

## Private calibration

The fixed 5-column by 4-row graph was selected before search. Independent
bounded Bernoulli rates and a spatially spread syndrome were optimized in
the native `search.cpp` frontier oracle. It uses 32 frontier states, sums
nonnegative probabilities, and minimizes physical costs. Private annealed
coordinate/syndrome proposals optimize contrary log odds while penalizing
small weight gap, small syndrome mass, and excessive mean rate, initially
at scales 0.95, 1, and 1.05. This is a private generation technique, not a
participant asset. The final 21-anchor certificate is stricter and is
verified separately. No best witness was placed in participant files.

Seed 230315933; 12,590,228 evaluated mutation proposals;
5,105 restarts. Requested wall budget: 240 seconds, checked
between restart batches; exact CPU time was not instrumented. The log ends
with a completion record. Native trials are not fresh model attempts.

## Frozen feasible targets

Frozen at 2026-08-28T16:19:32.826770+00:00, before any fresh launch. Final targets are gap
1.08 nats, opposite posterior 0.85, and syndrome mass 0.0000175 over the
whole interval [0.95,1.05]. The generic 2**21-state oracle independently
recomputes every anchor; it never imports the frontier checker or witness.

Known private core score: 1.00945632145758. Certified gap:
1.09021282717419; opposite posterior:
0.858592825592011; syndrome probability:
1.79178909486033e-05. Passed: true.

This demonstrates actual feasibility, not a conjectured open target. It
does not establish optimality or fresh-agent difficulty. Strong entropy
inversion survives a continuous 10%-wide global probability-scale range.
The certified effective-multiplicity ratio exceeds 18.063.

## Audit and asymmetry

The audit checks all anchors against the independent oracle for known and
baseline artifacts, random graphs' rate vectors on the fixed topology,
extended precision, exhaustive small-graph enumeration, mass normalization,
logical distance, incidence ranks, 1,001 interior scales, and malformed
artifacts. See `audit_report.json`. The public baseline is now a completely
deterministic fixture, not the early optimized `discovery_weak.json`; that
early hit remains private and is never copied into the final public set.

Reproduction, from the concept root, with all outputs local:

```bash
TMPDIR="$PWD/adversary" g++ -O3 -std=c++17 adversary/search.cpp -o adversary/search
./adversary/search 240 230315933 adversary/reproduction > adversary/reproduction.log
/usr/bin/python3 -B evaluator/evaluate.py adversary/known_witness.json --output adversary/recheck.json
/usr/bin/python3 -B adversary/audit.py
```

Do not overwrite or ratchet the frozen contract after launch. Two fully
independent one-hour model attempts are planned by the operator, not run.
