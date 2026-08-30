# Generation-two handoff: moderate background contamination

Status: **hard_open_candidate; solvability unknown; no passing tested implementation**.

## Selected public contract

Keep mode E, 256 bits, two hidden relabeled 16-site Rook/Shrikhande components,
RR/RS/SS labels, doublet errors, exact public simulator, 160 frames, 480 total
parities, eight parities/frame, mask weight 64, and 12s interaction / 8 CPU s /
512 MiB. Change only the three contamination probabilities to **1/8, 1/6, 1/4**.
The threshold remains 171/180 and at least 18/20 in each of nine cells.

## Evidence

- Original archived champion: **180/180**, mean **339.0778** queries, matching
  the archived result exactly. Mechanical adaptation reproduces every request
  and response on all 180 control cases; `validation_equivalence.json`.
- Parameterized champion, independent confirmation A: **161/180**;
  confirmation B: **166/180**. Both miss the overall and worst-cell
  thresholds. A uses the candidate manifest, B is a disjoint confirmation only.
- Unmodified evaluator CLI independently reproduces A; `official_champion_score.json`.
- Weak baseline on A: **75/180**. All runs are resource-valid.
- All **12** inherited model/protocol/isolation tests pass; `validation_contract.log`.
- Exploratory grids cover 0, 1/32, 1/16, 1/8, 1/6, 1/4, 1/3 at 480/360/300
  queries. Each grid has three samples per cell. The 360/300 paired repeats use
  exactly the 63 cases from 480; `sweep_summary.json` records discordant outcomes.
  No 1/2 contamination was needed. Exploratory seven-point priors are explicitly
  distinguished from the correctly narrowed three-point confirmation prior.

## Failure mechanisms

Across 360 confirmation episodes, 33 errors separate into the disjoint
clusters in `root_causes.json`: second-component acquisition/allocation failure,
frequency-ranked cores containing non-neighbors, and finite-sample inference
errors even with valid cores from distinct components. Budget saturation is
reported separately and is not asserted to be causal. These are neither stale
epsilon-grid failures nor mechanical budget overruns. A stronger policy needs
uncertainty-aware neighborhood/component discovery and allocation under noise;
no budget-respecting reference solution is claimed.

## Exact champion adaptation

`champion_parameterization.patch` and `parameterization.json` enumerate every
change. Read public contract at `/task/contract.json`; replace 160 with frame
limit, 153/110/120 with frame limit minus 7/50/40, and 470/472/477/370 with query
limit minus 10/8/3/110. Use contract per-frame limit for decoding and the exact
public epsilon hypotheses, preserving the original 1e-5 approximation only for
zero noise. Generalize three-way noise indexing and prior normalization for
exploratory grids. Source selection, discovery thresholds, likelihood formula,
posterior stopping, fallback, decoding and allocation algorithm are unchanged.
Absolute resource reserves are retained; no tuning on private confirmation
cases occurs. All champion code stays in private `policies/`, never public assets.

## Private isolation and promotion

Only the original public development JSON is mounted during every hidden sweep.
Private cases are loaded by the parent; bwrap mounts only system runtime paths,
the profile's three public input files, and the single policy file. There is no
`/proc`, evaluator, manifest, other submission, network or inherited environment.
The parent uses the original Device and evaluator; transcript recording and
exact policy replay happen only after scoring and are not revealed to the child.
Startup namespace initialization is outside the 12-second interaction timer.

Promote `candidate/participant/`, `candidate/evaluator/`, and `candidate/adversary/`
if retaining the supplied freeze hashes; otherwise regenerate the freeze manifest
after choosing release files. The adversary directory contains only inherited test
probes. `candidate_ready.json` is the index.
The private manifest is `candidate/evaluator/hidden/manifest.json`; preserve its
fresh pre-confirmation root seed rather than cherry-picking new hidden cases.
`candidate/evaluator/frozen.json` hashes the release assets. This worker has not
changed the live task, evaluator, attempts or champions, and launched no agents.

## Public development regeneration

The candidate contains 36 new independently generated public cases (four/cell),
not the original low-noise dev cases. From `candidate/participant`, run:

```sh
python3 -B workspace/generate_dev_cases.py --contract input/contract.json --output input/dev_cases.json --episodes-per-cell 4
```

This deterministically reproduces the JSON byte-for-byte without consulting a
private manifest. The public seed recipe and domain are in
`public_development_generation.json`; private/public overlap is zero. Public
development is descriptive and cannot certify the hidden threshold.

## Reproduction

From this private directory, the official confirmation command is:

```sh
python3 -B profiles/moderate480/evaluator/evaluate.py --policy policies/champion_parameterized.py --jobs 16 --output official_champion_score.json
```

The private diagnostic runner is `ratchet.py`; profiles, manifests, episode-level
traces, scores, hashes, paired resource comparisons and patches are retained.
No candidate proof of solvability exists; readiness is for an explicitly allowed
hard-open generation, not a solved-reference benchmark.
