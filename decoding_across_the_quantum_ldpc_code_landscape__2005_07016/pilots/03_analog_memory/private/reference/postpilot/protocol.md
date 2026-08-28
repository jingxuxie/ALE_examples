# Bounded post-pilot audit

This audit does not edit the participant, original attempt, scorer, reference
implementation, original challenge, or reserved holdout. All outputs go under
`private/reference/postpilot` or `private/challenge_pool/postpilot`.

First replay the unchanged submitted algorithm on the original challenge pool,
using the existing evaluator and its unchanged 120-CPU-second/1536-MiB budget.
Run a byte-identical copy of the complete attempt so compilation or caches cannot
modify the original attempt. Preserve source/library mtimes and hash all files.

Inspect the actual algorithm before considering at most two additional regimes.
Do not introduce a new distribution, contract restriction, scoring gate, or
threshold. Known-Gaussian ambiguity and temporal cancellation are not missing
mechanisms merely because the initial pilot was easy: the submission explicitly
builds their joint model and cancellation-preserving moves. Extra regimes are
optional and require a specific scientifically meaningful omission, not a desire
to force a failure. Do not generate a final holdout or a new model attempt.

Reference quality must be assessed as raw accuracy and genuine outperformance,
not merely its normalized score of one. A generic augmentation that robustly
solves this public contract is evidence to discard this candidate, not grounds
to tighten its runtime or perturb its specification.

Primary implementation anchors already inspected for this pilot:
https://arxiv.org/abs/2311.01328
https://doi.org/10.1103/PRXQuantum.5.020349
https://github.com/munich-quantum-toolkit/qecc/tree/949d2375548ed5ffc8f389afdfd01f9093e27780
The existing private manifests pin source files and the exact reference adapter.

