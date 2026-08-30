# Feasibility evidence, not an impossibility certificate

The fixed overall target remains 20%, with every family at least 8%.
No certified lower bound on optimal schedule cost was established in this
refinement. No conclusion of mathematical or resource-bounded impossibility
is supported. Retaining `hard_open` is consistent with the evidence.

The actual portable bundle has 30 exact-checker-valid schedules: core
0.18069244983155353, worst family 0.0934956685364029, total cost 283699
against baseline total 345617. It consumed 84.3873847220093 seconds wall,
66.95658399999999 seconds CPU, and 78168 KiB sampled aggregate address space
in the one-CPU direct authoring test. Official isolation validation is
separate. These schedules are upper bounds on optimal achievable cost, not
lower bounds that could rule out cheaper schedules.

The per-instance minimum across completed experiments is stored and
exact-checked in `summary.json`. That union is an offline cost-potential
result, not a runtime-compliant hidden-table submission. It also does not
reach 20%. The configuration-selector prediction (approximately 0.18074647)
is not the measured wrapper score; time-bounded searches can return slightly
different plans when actually composed.

Wider beams, longer lookahead, alternate heuristics, forward/reverse joins,
and runtime portfolios produced modest gains over fresh v2. Some wider
variants timed out. This is empirical evidence about these implementations
and configurations only, not a bound on every generic planner, not an
optimality certificate, and not proof of target infeasibility. No external
solver certificate or exhaustive state-space proof is claimed.
