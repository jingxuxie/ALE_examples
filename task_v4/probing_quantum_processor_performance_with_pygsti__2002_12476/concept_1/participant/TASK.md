# Keep characterization usable after circuit-record loss

Design a resource-constrained characterization campaign for a quantum processor whose operating point is uncertain. The campaign must retain useful local information when any three complete circuit records are lost, without sacrificing normal-operation efficiency.

Provided assets are a physical simulator and operating-point sampler, 840 candidate experiments, a public development ensemble, and the previous-generation champion as a runnable baseline. The physical model includes coherent gate errors, decoherence, and nuisance readout parameters. The supplied champion is not a passing solution for this generation.

Submit one static `design.json` containing exactly `{"batches": [...]}`: one integer allocation per candidate, in input order. The interface and scoring definitions are in `input/README.md` and `input/contract.json`. Run `python baseline/solve.py --output PATH` to emit the baseline and `python workspace/check.py PATH` to evaluate development performance. Submitted code is never executed.

The mean worst-three-loss A-risk must be at most **four times** the champion's intact mean A-risk, and at most **five times** its intact mean within every operating regime. Your intact mean A-risk must remain within **1.20 times** the champion's. Scores are inverse risk-inflation ratios; larger is better. Hidden evaluation uses 600 operating points from the disclosed sampler, equally divided among six regimes.

Resource limits: one hour of solving time, no network, 1,600,000 execution ticks, at most 24 distinct circuits, at most 48 batches per circuit, and 64 shots per batch. No adaptive reallocation or cost refund follows a loss. These are local Fisher-information objectives, not a finite-shot estimation guarantee. No report is required.
