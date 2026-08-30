# Exact public contract, version 1

## Artifact

One UTF-8 JSON object, at most 65,536 bytes. Duplicate keys, unknown fields,
nonfinite numbers, booleans used as numbers, and unsupported values are invalid.
No code, expressions, file paths, seed selectors, or external resources are
accepted. `policy.schema.json` provides the machine-readable grammar;
`cascade_sim.validate_policy` is authoritative.

The root has exactly these fields:

- `version`: integer 1.
- `max_passes`: integer 4 through 20, an unconditional pass budget.
- `schedule`: four complete actions, for pass indices 0, 1, 2, and all later passes.
- `rules`: zero through 64 ordered rules.

A complete action has `size`, `reuse`, `batch`, and `stop`. In the schedule,
`stop` must be false. Each rule is `{"when": [...], "action": {...}}`; `when`
contains 1–8 conditions and `action` contains a nonempty subset of action fields.
Each condition is `[feature, operator, finite_number]`, where the operator is
`lt`, `le`, `gt`, or `ge`. All conditions must hold. The **first matching rule
only** overrides the scheduled action; rules do not accumulate. A `size`
override replaces the entire size object. Rules have no persistent state.

Action values:

- `reuse`: `all` considers all cached blocks during backtracking; `roots`
  considers only top-level blocks; `recent` considers all roots plus subblocks
  first registered in the current or immediately preceding pass. All modes
  retain cached parities and can infer siblings during a search. This setting
  controls eligibility for starting backtracking, not erasure of information.
- `batch`: `pass` restricts each backtracking wave to the earliest eligible
  pass, then greedily takes disjoint shortest blocks. `smallest` greedily takes
  disjoint shortest blocks across all passes. Ties are broken by registration
  pass and order. New top-level mismatches are always searched in parallel.
- `stop`: boolean; a true rule action stops before the pass, but only at
  `pass_index >= 3`. Earlier stop requests are ignored, including at index 0.
- `size`: exactly `{"basis": ..., "scale": ..., "round": ...}`. Scale is in
  `[1/16,16]`; rounding is `ceil`, `floor`, or `nearest` in base-two log space
  (nearest ties round upward). Clamp the resulting power of two to `[2,N/2]`.

Size bases, before multiplying by scale:

| basis | value |
|---|---|
| `paper_first` | `2**ceil(alpha)`, `alpha=log2(1/max(q_est,1/N))-0.5` |
| `paper_second` | `2**ceil((alpha+log2(N/4))/2)` |
| `frame` | `N` |
| `first` | first pass block size, or the reference first size before pass 0 |
| `estimate` | `1/max(q_est,1/N)` |
| `parity` | `1/max(parity_est,1/N)` |
| `remaining` | `1/max(parity_est-corrected_fraction,1/N)` |

The reference uses `paper_first`, `paper_second`, `frame*0.25`, then
`frame*0.5`, with reuse `all`, batching `pass`, 14 passes, and no rules. For
`N=16384` this is the paper's optimization (8) formula. Smaller frames scale
the third-pass block to `N/4`; this is an explicit benchmark extension.

## Observable features

Every rule is evaluated immediately before a pass. No other features exist.

| feature | exact meaning |
|---|---|
| `frame_bits` | `N`, frame length |
| `q_est` | smoothed noisy estimate, fixed for the frame |
| `sample_size` | number of independent estimator samples |
| `q_se` | `sqrt(q_est*(1-q_est)/(sample_size+1))` |
| `latency` | normalized cost per communication round |
| `pass_index` | zero-based index of the pass about to start |
| `first_size` | selected first block size; reference first size before pass 0 |
| `parity_est` | first-pass odd-block inversion described next; `q_est` initially |
| `estimate_ratio` | `parity_est/q_est`; 1 initially |
| `corrected_fraction` | total publicly located corrections divided by `N` |
| `last_corrected_fraction` | previous pass's located corrections divided by `N` |
| `last_odd_fraction` | previous pass's odd roots before searches divided by root count |
| `quiet_passes` | consecutive completed passes with no located corrections |
| `last_rounds` | previous pass's parity communication rounds |
| `last_leak_fraction` | previous pass's disclosed parity count divided by `N` |
| `known_per_bit` | number of distinct cached blocks divided by `N` |

Other than the specified initial values, history features start at zero.
After pass 0, with `odd` odd roots and `roots` total roots, let
`probability=min(0.499,(odd+0.5)/(roots+1))`. Then
`parity_est=clip((1-(1-2*probability)**(1/first_size))/2, 1/N, 0.15)`.
This estimate is not refreshed in later passes. Corrections are transcript
observations, not an oracle for the number of remaining errors.

The policy never receives true QBER, bias, error positions, frame seeds,
permutations, case indices, family labels, residual error count, or a
verification result. The sampler and scorer know those quantities, but they
are not inputs to `choose_action`.

## Channel and trusted protocol

Each normal frame contains independent Bernoulli errors with parameter
`q_true`. Independent estimation samples have probability
`clip(q_true*estimate_bias,0.0001,0.15)`; if `sample_errors` errors occur,
`q_est=clip((sample_errors+0.5)/(sample_size+1),1/N,0.15)`.
The estimator uses separate sacrificed samples and incurs no candidate-dependent
cost. Errors, samples, and pass permutations have separate domain-separated
SHA-256-derived Python Random streams. Permutations are freshly shuffled even
on pass 0. A pass's permutation does not depend on earlier policy decisions.
Candidate and reference use exactly the same frame and estimator realization.

Only Alice's parity disclosures count as leakage. Distinct known subsets are
cached by their exact bit mask. For later passes, the final root parity is
inferred from the known even total parity and the other roots. During binary
search the parent parity and one child determine the other child. A new pair
of children costs one disclosed parity; cached/inferred splits cost zero.
No arbitrary Gaussian-elimination rank reduction is performed. This is a
conservative disclosure count, not a claim of optimal entropy accounting.

All new root queries cost one communication round as a batch. Within a
disjoint batch of searches, all locally known splits are traversed for free;
the next unknown split from each active search is combined into one round.
Located errors are corrected simultaneously; then backtracking recomputes
eligible odd blocks until none remain. There are no stale overlapping
searches. Current-pass roots are included when restoring even parities.
One round denotes one noiseless request/response exchange. Bob's control
messages, authentication, and local compute time are outside this model.

Every frame pays a terminal 32-bit verification disclosure and one round.
Verification is idealized as collision-free for scoring and never feeds back
to the policy. A residual error means frame discard. Even already-correct
frames continue until the policy stops or uses its pass budget. There is no
oracle early exit. An empty-error frame still incurs all selected operations.

## Scoring and target

For each normal frame, let `D` include the terminal 32 verification bits,
`R` include its terminal round, and `F` indicate a residual error. Define:

```text
h2(q) = -q*log2(q) - (1-q)*log2(1-q)
effective_leakage = 1 if F else min(1,D/N)
joint_cost = effective_leakage/h2(q_true) + latency*R
family_ratio = mean(candidate joint_cost)/mean(reference joint_cost)
overall_ratio = mean(family_ratio over the four families)
```

All normal frames in a family have equal weight, and families have equal
weight regardless of sample count. Failure discards the whole frame and
therefore already replaces its leakage by one; do not add its parity leakage
again. Latency cost is paid on both failed and successful frames.

A qualifying hidden submission must simultaneously satisfy:

- `overall_ratio <= 0.92`.
- Every `family_ratio <= 0.97`.
- Overall normal-frame FER `<= 0.003`.
- Every normal-family FER `<= 0.005`.
- Every normal-family one-sided 95% Wilson upper FER bound `<= 0.01`.
- Conditional collision-tail stress FER `<= 0.005`.

Wilson uses `z=1.6448536269514722`, the exact formula in `scoring.py`.
No rounding is applied to gate comparisons. These are empirical finite-suite
requirements, not a security proof or evidence of FER below `10**-4`.
The conditional stress FER is a robustness gate, not a population FER
estimate, and stress costs do not enter the improvement objective.

## Splits and collision-tail stress

The public operating grids are in `input/distribution.json`. Normal frames
use four families. Each family has 8 training tuples with 8 frames each,
12 development tuples with 32 frames each, and 16 hidden tuples with 64
frames each. Normal operating tuples `(N,q_true,bias,sample_size,latency)`
are disjoint across all three splits. Every frame seed, including stress
seeds, is unique across all splits. Hidden tuples and seeds are fixed before
any fresh participant attempt and are not selected against submitted policies.

Each split also includes conditional stress at `N=512,2048,8192`, with
`q_true=0.006`, bias 1, and 256 estimator samples. There are respectively
24, 64, and 256 frames per size for train, dev, and hidden. These are **not**
Bernoulli frames. Construct the reference's first two partitions for the
seed and sampled estimate, group bit positions by their two block IDs,
uniformly select an intersection large enough, then uniformly select two
positions, or four positions on every third frame. Those errors survive
the first two reference passes, directly exercising finite tail reliability.
The construction is fixed and independent of candidate policies. All stress
errors and seeds for train/dev are public. Hidden stress uses independent
seeds from the same declared construction.

Public training has only 64 normal frames per family, so even zero failures
cannot pass the Wilson gate. This is intentional; training reports are
optimization feedback. Development can pass but is less statistically
precise than the 1,024-frame-per-family hidden suite. Do not confuse a lack
of observed errors with a guarantee that no errors occur.

## Execution and trust boundary

Use Python 3.10+ and the standard library only. From this workspace, run:

```sh
python3 scoring.py --policy /path/to/output/policy.json --split dev --jobs 4 --output /path/to/output/dev_report.json
```

All task assets are read-only. Replace `/path/to/output` with the runner's
writable output directory; put scripts, reports, and candidate artifacts
there, not inside the task directory. The `input/`, `workspace/`, and
`baseline/` directories are read-only inputs, not writable destinations.

For a diagnostic transcript, import `run_frame` from `cascade_sim` and call
`run_frame(public_case, public_seed, validated_policy, trace=True)`. The
`errors` argument is available for explicit public experiments; it is not
a submission capability.

Parent evaluation runs the reference tree's `evaluator/evaluate.py` with
`--policy /absolute/path/to/submitted.json --split hidden --output report.json`.
The evaluator loads only JSON from that path, imports simulator code only
from its own trusted reference tree, and verifies the frozen manifest.
Editing your public simulator copy does not change parent scoring. The
parent must keep the original reference tree immutable and expose only a
copy of `participant/` to the fresh worker. A JSON artifact does not require
executing an untrusted candidate program or exposing hidden seeds to it.
Parent-side output omits per-case results and seed identifiers.

Top-level result fields are `core_score=1-overall_ratio`,
`worst_family_score=min(1-family_ratio)`, and
`runtime_resource_score=min(reference_mean_rounds/candidate_mean_rounds)`
over families. All are higher-is-better; the reference has values 0, 0, 1.
`valid` means the artifact was accepted, `passed` equals `target_pass`, and
`reason` explains rejection or the unmet gate. The runtime/resource field
measures modeled communication rounds, not wall-clock speed; elapsed real
time is separately reported as `elapsed_seconds`. Policy bounds (64 KiB,
64 rules, 8 conditions per rule, and at most 20 passes) are enforced before
simulation. Scoring supports 1–16 trusted workers and has no hardware-dependent
wall-time acceptance gate. Missing, malformed, oversized, and nonfinite
artifacts produce a structured invalid report, not an uncaught traceback.
