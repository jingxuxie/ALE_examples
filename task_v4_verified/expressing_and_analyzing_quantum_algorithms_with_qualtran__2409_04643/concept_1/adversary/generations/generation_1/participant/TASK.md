# Resource-aware scheduling of hierarchical quantum programs

Improve the supplied scheduling baseline for register-level quantum compute
graphs. Choose legal serial execution orders that reduce both peak logical
qubits and qubit-time without changing any operation or connection.

The workload bank, resource contracts, baseline scheduler and public diagnostic
checker are supplied locally. This is a resource-analysis model of atomic bloqs;
it does not ask you to synthesize their internal circuits. See
`workspace/interface.md` for the executable and artifact contracts.

Write `schedules.json` in your output directory. The evaluator checks every
dependency and independently reconstructs register liveness and internal
workspace costs. Passing requires a geometric-mean improvement ratio of at least
1.70, every workload family's ratio at least 1.18, and no workload's peak
qubit count more than 5% above baseline. Improvement means baseline cost divided
by submitted cost; a ratio of 1.70 is about a 41% reduction in resource cost.

You have one hour, four CPU threads and 8 GiB working memory. There is no network
access. Submitted artifacts are limited to 16 MiB. Scores measure physical
resource proxies, not the speed of your search. No changes to the supplied
workloads or baseline are evaluated.
