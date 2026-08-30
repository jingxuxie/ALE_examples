# Generation 3: final selected-champion ratchet

This is the final E generation. Original and generation-2 participant/evaluator
assets are unchanged. No fresh agent is launched by this builder. All policies
and accuracy results here are privileged qualification, never fresh champions.

## Basis: the actual selected generation-2 champion

Main selected fresh **v1**, not provisional v2: official mean .05015128124106103,
worst .062246142645026925, maximum CPU 26.083223 seconds. The exact 88-file source
is preserved in `participant/baseline/previous_champion/`; its solution SHA-256 is
`7b360851aac14d7b2d3f658fe3586f9504b47aa014b17c707aec1e7c346e4813`.
`adversary/selected_champion_manifest.json` records every original file hash.
The supplied native libraries and C++ sources are preserved, not rebuilt.

Mandatory isolated stress used independent runtime copies of that exact source
on all three connected topologies at D24, D28, D36, and D44. All twelve fail
before requesting a shot at `solution.py:46`: the full raw-count array alone is
4.625 GiB at D24 and 82 GiB at D28, exceeding the unchanged 3 GiB address cap.
The D24/D28 controls are below the signed 32-bit syndrome boundary. This is a
reproduced dense-storage scaling failure, not an inference from a guessed
algorithm, a simulator-width defect, or a statistical impossibility. The source
also allocates a full-outcome mapping and has distinct int32 conversions; neither
is needed to establish the below-boundary failure. Complete source hashes remain
unchanged after every control.

The provisional v2 stress and its modified diagnostic variant are exploratory
history only and are **not** the basis of this ratchet. In particular, a modified
composite-gradient posterior correction does not establish a fundamental
information failure. Raw selected-v1 control reports are retained under
`adversary/validation/selected_champion_controls/`.

## Scientific scope and fixed targets

Twelve newly sampled hidden episodes cover connected ladder, patch, and
triangular graphs at D28, D32, D36, and D44. All detectors participate; channel
count scales from 88 to 179. Maximum locality-graph degree is six, and each
channel's combined primary/alternate support has diameter at most two and size
at most four. This is not inactive padding. The conditional Bernoulli parity
law, unobserved shared mode, local aliases, rate bounds, gain-ladder interventions,
40,000-shot budget, and 60-CPU-second/3-GiB caps retain the previous construction.
Only sparse syndrome histograms cross the worker boundary.

Targets **mean <= .090 and worst regime/family <= .140** were declared at
2026-08-28 19:29:48 UTC, before qualification on the new fixtures. Initial
larger-graph controls were uniform .10561/.13796 and adaptive .07920/.11879;
the old .075 mean was not asserted feasible. `adversary/target_proposal.json`
preserves this rationale and the originally proposed numerical rules. Sealing
changes metadata only, not any numerical criterion, rate, fixture, or noise seed.

Public graph generation, private rates, and sampling noise use separately drawn
seeds. All twelve independently sampled cases are retained without accuracy
filtering. Public training cases are separate. Hidden seeds and rates remain in
the trusted parent; no participant module or native library is loaded there.

## Qualification on the twelve final hidden fixtures

| Policy | Mean | Worst cell | Max CPU | Outcome |
| --- | --- | --- | --- | --- |
| Private latent-blind robust active policy | .0701815715 | .1135830652 | 25.574969 s | Pass |
| Same inference, uniform allocation | .1043582374 | .1598438174 | 8.747921 s | Fail |
| Supplied bounded weak moment baseline | .1336740595 | .2109861897 | 4.344157 s | Fail |

All 36 completed episodes are valid and obey the same observation API, query,
shot, CPU, memory, and isolation rules. The private active policy imports only
its own mathematical helper, receives the public spec and queried syndromes,
fits its pilot observations, allocates later shots from those fits, and returns
positive rates. It has no hidden rate initialization, held-out fixture access,
truth-dependent allocation, or feedback from the scorer. Each episode has an
independent submission copy. This is an actual passing latent-blind witness,
not Fisher evidence relabeled as a solution. It remains private, not a supplied
starter. Reports are `adversary/validation/{robust,uniform,weak_bounded}_report.json`.

The initial unbounded weak-baseline draft was stopped after a CPU-limit failure.
The supplied final version has a process-time optimization guard, was separately
run over all twelve cases, and is the `weak_bounded` row above. Earlier partial
logs are retained as development history, not qualification results.

## Identifiability and information checks

`adversary/validation/science.json` validates every hidden case: graph connectivity,
all-active incidence, local support, full-rank all-action log-rate Jacobian,
rank-deficient reference aliases resolved by interventions, independent
small-marginal convolution, analytic-gradient finite differences, an independent
sampler check, and exact cross-feature/shared-mode covariance-aware information.
Two non-oracle noiseless starts recover all log rates within .02. These are
local/numerical identifiability checks, not a global-identifiability theorem.
The information calculation is local-moment information, not claimed full-state
Fisher. Finite-sample feasibility comes from the latent-blind witness above.

A separate diagnostic independently reconstructs the selected v1's public
random binary projection using width-correct arithmetic. Its **full joint**
16-bit projected Fisher, not just a few parity means, has uniform mean log-SD
.11595 at triangular D28 and .16910 at D44; true-rate optimized allocations give
.08773 and .13805, respectively. The D44 optimized worst-family log-SD is .21277.
This supports a representation/information concern beyond storage, but it is an
asymptotic preparation-case diagnostic, not the official scoring metric, a
lower bound on arbitrary estimators, or evidence of the unmodified program's
accuracy (that program fails before querying). Oracle allocations are explicitly
not qualified policies. Full details and limitations are in
`adversary/validation/selected_projection_information.json`.

## Infrastructure and public workflow

The hidden worker uses mandatory bwrap isolation: system directories readonly,
private proc and tmpfs, participant readonly, and only the exact submission leaf
writable. Sibling attempts, logs, private rates, and the ALE tree are not mounted.
The existing isolated supervisor meters actual descendant CPU with authenticated
reporting. The two-second CPU burn measured 2.396857 seconds including overhead;
the one-second RLIMIT_CPU probe was terminated. The 4-GiB allocation and mount
visibility probes pass. `attempts/v_1`-style leaves are accepted while the parent
attempts directory is rejected. Wall allowances are 300 seconds startup plus
900 seconds active time, not a tight loaded-host wall benchmark.

The Python-int independent XOR sampler equals the int64 sampler on all twelve
new fixtures; sparse JSON roundtrips exactly, every bit is active, and observed
syndromes cross the signed 32-bit boundary where appropriate. All D<=44 codes
also fit exactly in binary64 integer range. See `validation/width_audit.json`.

The largest public D44 triangular episode was tested inside a participant-only
allowlist using actual launcher paths, a readonly participant directory, and a
writable attempt leaf. `input/local.py` uses ordinary subprocesses without
nested bwrap and completes successfully. It is development scoring, not resource
certification. TASK contains no expected failure diagnosis or prescribed solver.

## Dependencies and launcher

Fresh allowlist: this generation's `participant/` readonly and the actual writable
attempt directory, using `:minimal`; do not expose `adversary/` or `evaluator/`.
Use `/usr/bin/python3`, NumPy and SciPy from `/usr/lib/python3/dist-packages`.
The evaluator needs `/usr/bin/bwrap` outside the fresh parent sandbox. Its exact
worker command is `/usr/bin/python3 /submission/solution.py`. No pip install,
network access, new runtime package, or hidden bridge is required. The preceding
champion already accepts the sparse observation API. Its supplied kernels need
standard `libstdc++.so.6`, `libm.so.6`, `libmvec.so.1`, `libgcc_s.so.1`, and
`libc.so.6`, available through the readonly system mounts.

From the generation directory, the main evaluator command is:

```
/usr/bin/python3 evaluator/evaluate.py --submission "$ATTEMPT_DIR" --output "$REPORT_PATH" -- /usr/bin/python3 /submission/solution.py
```

The output path must be outside the mounted submission leaf if it is private.
Do not run this hidden evaluator inside a fresh participant allowlist. Public
testing instead uses the relative command in TASK with a launcher-provided
`ATTEMPT_DIR`. `adversary/finalize_package.py --verify` checks the final package.

Post-seal CLI smoke checks exercise that exact evaluator entry point and its
integrity guard: the supplied weak baseline completes a public D28 case validly
in 1.132314 CPU seconds; the unchanged selected champion fails before any query
on the new private D28 case in .786084 CPU seconds. These one-case reports are
explicitly not full-suite qualifications and do not replace the twelve-case
control reports. Their artifacts are `validation/cli_weak_report.json` and
`validation/cli_previous_report.json`.

## Primary-source motivation

Inspected primary sources: Higgott and Gidney, *Sparse Blossom*,
arXiv:2303.15933, and Takou and Brown, *Estimating decoding graphs and hypergraphs
of memory QEC experiments*, arXiv:2504.20212. The former motivates efficient
matching-based decoding; the latter explicitly studies graph/hypergraph error
rate estimation from syndrome statistics. This benchmark is a synthetic active
calibration extension, not a claim to reproduce either paper's hardware,
performance, or physical noise model.
