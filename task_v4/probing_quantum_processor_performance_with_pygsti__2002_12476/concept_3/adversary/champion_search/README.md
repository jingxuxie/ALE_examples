# Private champion robustness search

This directory is the only writable location for this search. The frozen
participant/evaluator and archived generations are not modified. No fresh-agent
runner is invoked; these are blinded reruns of the already learned champion.

The champion fits the disclosed 54-parameter model by bounded binomial-deviance
minimization with exact C++ reverse-mode derivatives. Its fixed initialization
and schedule fit depths <=24, <=64, all training counts, then training plus
development counts. Source copies in `solver/` are byte-identical to `attempts/v_1`;
the separate entry point redirects only public input/output paths and records
resources. Prediction generation omits nonessential covariance/report generation,
so an auxiliary-report failure cannot be mistaken for a scientific counterexample.

Each trial has new physical devices, independently sampled new characterization
circuits, independent binomial counts, and new development/test queries from the
unchanged acquisition generator. Every campaign has the full original sizes:
28,464 training rows, 2,048 development rows, and 8,192 test queries. Parameter
corner cases remain inside every original interval and preserve the same physics.
They target slow/fast fluctuators, asymmetry, long memory, large coherent drift,
weakly observable nuisance parameters, and signed-control cancellations.
Additional joint-corner campaigns place every scaled physical coordinate within
the outer eight percent of its allowed half-interval, with independently chosen
signs. These are explicit stress selections, not ordinary uniform draws, and
introduce no physics or acquisition change.

The native champion forward model accelerates private data generation only.
For every device and every split, 24 independent examples are cross-checked
against the original NumPy Bloch oracle. The prior independent density-matrix
audits remain applicable. True parameters/probabilities stay in each campaign's
`private/` directory and are inaccessible to the learner. A minimal bubblewrap
filesystem exposes only OS libraries, read-only solver/public input, an initially
empty output directory, and private scratch. Networking is unshared. Probes record
the lack of host-repository/private paths. Each device uses two OpenMP threads;
a four-device campaign uses eight allowed CPUs and 8 GiB RLIMIT_AS per process.

`run_trials.py` stores complete optimizer logs, stage checkpoints, learned
parameters/Jacobians, process CPU time/RSS, wall time, and isolation evidence.
`score_trials.py` applies the original fixed targets using private true
probabilities, then audits learning stages. Infrastructure/timeout/schema errors
are not counted as scientific failures. No target is tightened and no hidden
mechanism, impossible ambiguity, or training-data reduction is introduced.

An initial minimal-filesystem setup required two path/library adjustments
(`/work/solver` preserves the original module's parent-path assumptions, and
`/etc/alternatives` supplies the standard BLAS library symlinks). These were
pre-learner isolation-probe failures with empty outputs, not challenger results.

The current measured results and full per-campaign paths are in `summary.json`
and `campaigns/campaign_*/score.json`. Do not infer a new hard generation unless
there is a substantial, scientifically valid predictive failure.
