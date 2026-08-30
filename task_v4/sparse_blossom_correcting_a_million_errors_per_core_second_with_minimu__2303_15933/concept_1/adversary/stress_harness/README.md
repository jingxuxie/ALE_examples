# Private residual/compute stress sidecar

**Prepared for main; not a new task generation, frozen target, or official score.**
All new source, data, reports, snapshots, and caches stay in this directory.
The original participant, evaluator, datasets, targets, and root status are not
modified. The active `attempts/v_1` submission is neither inspected nor evaluated.
Its reported generated-sample improvement is not treated as an adjudicated score.

## What is prepared

- 33 scenarios in 10 groups, distances 7–15, one to seven rounds, including
  independent anchors from all six original distributions.
- Larger lattices; even distances; balanced/X-dominant/Z-dominant priors;
  stronger overlapping XX/ZZ crosstalk; longer memory; simultaneous spatial,
  temporal, and readout mechanisms; known noisy strips and known bad rounds;
  and measurement-dominated controls.
- Independent unconditional Bernoulli mechanism sampling with exact H/L parity.
  Model matrices come from the original `make_model`; no rejection, balancing,
  or selection of shots based on decoder mistakes.
- Known nonuniform profiles update both `probabilities` and every DEM error
  probability consistently. Scalar `px/pz/py/...` fields remain base rates;
  the supplied per-mechanism probabilities and DEM are authoritative. There is
  no hidden prior misspecification. These profiles are new exploratory inputs,
  not a retrospective change to the original task contract.
- Paired residual comparisons, Wilson failure-rate intervals, logical confusion
  masks, true sampled-mechanism support clusters, overlap/cancellation features,
  and detector/time/sector hotspots. All latent faults and labels stay private.
- Immutable, hash-checked snapshots gated on main's explicit confirmation of a
  completed, independently scored, promoted champion. Active attempts are rejected
  before their files are read. Optional portfolio variants require a confirmed
  parent and explicit main approval; they are never assumed to pass.
- Trusted isolated CPU/quality comparisons on identical shots. This supports
  choosing a future compute-matched target instead of simply granting a larger
  ensemble under the original loose 180-second limit.

The 256-shot-per-case discovery sweep has 8,448 shots. Its baseline results are
in `corpora/discovery_256/baseline_report.json`; the original known challenge
baseline is copied as a provenance-linked summary in
`reports/initial_baseline_reference.json`. The latter has 1,523/12,288 failures,
not a score for any fresh attempt.

## Regimes and scientific interpretation

The catalog is in `regimes.py` and its pre-sampling copy is stored with each
corpus. These are all **square periodic toric models**, not a claim to cover
surface-code boundaries, rectangular geometries, or unrelated code families.
Even sizes change geometry while retaining the same four-frame-bit API. New
code families would require another independently audited model construction.

`detector_support_strip` doubles each mechanism's rate when its nonzero H
support touches detector columns x=0 or x=1, capped at 0.25. This creates a known
nonuniform strip, rather than secretly changing the code or selecting labels.
`noisy_middle_round` multiplies readout rates by four, temporal YY rates by two,
and single-qubit X/Z/Y rates by 1.5 when their detector support touches the middle
time layer, with the same 0.25 cap. Correlated components still fire together.

Easy controls and severe stress cases are deliberate. Few residuals imply an
underpowered relative-error target; a high baseline failure rate does not prove
Bayes headroom. In particular, do not automatically promote a near-threshold
joint-noise case just because the old baseline fails often. The champion and a
credible stronger portfolio must establish a measurable, achievable gap first.

## Root-cause diagnostics: what they do and do not prove

`diagnostics.py` groups residuals by readout/burst coexistence, multiple spatial
pair events, extended active-mechanism components, large syndrome cancellation,
and small active components. It also bins fault count, syndrome weight, mechanism
counts, time extent, and mechanism-configuration surprisal. Strata overlap.

Components connect sampled active mechanism columns through nonzero H entries.
They are not a reconstruction of the candidate's physical correction, a unique
causal explanation, a proof of logical degeneracy, or a measured posterior gap.
The API returns logical bits only. Hotspots report failure conditional on a
detector firing, with exposure denominators and Wilson intervals; they are
descriptive associations, with uncorrected multiple comparisons. Reported logical
masks encode the four-bit XOR between prediction and sampled label.

For actual root-cause attribution, use these clusters to choose hypotheses for
private controlled experiments after the champion is confirmed. A selected-error
oracle/expensive-portfolio study may diagnose ambiguity, but its accuracy must not
be misreported as an unbiased all-shot benchmark or an exact Bayes bound.

## Commands

Set `SIDE` to this directory. Commands use `/usr/bin/python3` and the existing
participant-local runtime, without installing or symlinking dependencies.

```
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 "$SIDE/test_harness.py"
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 "$SIDE/harness.py" build \
  --name discovery_new --shots 512 --role discovery
```

Existing corpora are not overwritten. Independent confirmation uses another name
and independent secret streams; it is not generated by selecting discovery errors.

**Stop here until main confirms the actual champion and promotes a code-only
directory under the original `champions/`.** Then, and only then:

```
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 "$SIDE/harness.py" register-champion \
  --name confirmed_v1 --submission "$PROMOTED_CODE_DIR/submission.py" \
  --official-report "$INDEPENDENT_OFFICIAL_REPORT" --confirm-promoted
```

The official report must say `valid=true` and `passed=true`. Main's confirmation
attests that the promoted code corresponds to that report; the original report
does not itself contain a source-tree hash. The sidecar verifies source stability
before/after copying and checks the copied tree hash on every subsequent run.

Run the following through **exec require_escalated**. The inner bwrap sandbox
remains mandatory; there is no unsandboxed fallback:

```
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 "$SIDE/harness.py" run \
  --name confirmed_v1_discovery --suite "$SIDE/corpora/discovery_256" \
  --champion-manifest "$SIDE/snapshots/confirmed_v1/manifest.json"
```

Use `--cases ID,ID,...` for a bounded subset. `--cpu-budget` defaults to 180 CPU
seconds and `--wall-watchdog` to 1,800 wall seconds **as exploratory safety
limits, not future task targets**. Initialization/imports are included in trusted
isolated CPU. Timeouts are reported as interrupted exploration, not adjudicated
new-task failures. The sandbox reuses the audited original launcher, with a
read-only overlay of stress models on `/participant/input/cases`. Only syndrome
NPZs enter `/request`; the entire corpus directory is never mounted.

For optional portfolio work, put a code-only variant under
`portfolio_sources/<name>/`. Register it with `register-portfolio`, providing
`--parent-manifest`, `--submission`, `--change-note`, and
`--main-approved-experiment`. A variant has `original_task_passed=null`; it is not
a champion. No variants or expensive portfolio runs are created by preparation.
Record whether a change is merely ensemble depth, another search budget, or a
genuinely different inference/refinement strategy.

Run two snapshots on the same corpus/case order, then:

```
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 "$SIDE/harness.py" compare \
  --reference "$SIDE/runs/reference/report.json" \
  --candidate "$SIDE/runs/variant/report.json" \
  --output "$SIDE/reports/paired_frontier.json"
```

The result contains paired errors removed relative to the reference, group-level
uncertainty, the trusted total-CPU ratio, and gain per extra CPU-second. It never
declares a future task passed. Trusted in-process baseline timings exclude imports
and must not be compared directly to isolated total CPU; use `--trusted-baseline`
for a compute-comparable baseline run. `--isolation-probe` runs only a fixed,
trusted probe and never reads active submissions.

## Before any future ratchet

1. Independently score and promote the actual champion; do not substitute the
   running agent's generated-sample report.
2. Measure genuine residual failures and their uncertainty on the discovery
   sweep. Keep easy controls and avoid letting one severe regime dominate pooled
   metrics. Do not filter evaluation shots by baseline/candidate mistakes.
3. Construct a compute/quality frontier. Include the same champion with increased
   ensemble/search work as a control, plus meaningfully different private methods
   if available. Expensive portfolio runs establish only measured, not assumed,
   achievability. Repeat matched runs when CPU noise is material.
4. Prefer a future gap relative to the **strong champion's measured CPU on the
   new protocol**, with explicit initialization accounting and scientific
   nonregression. Do not create a task whose solution is one larger ensemble
   parameter under 180 seconds. No multiplier or numerical target is chosen here.
5. Validate promising regimes on independent confirmation streams with sufficient
   residual counts. A zero-error pilot gives only an upper rate bound, not proof
   of optimality. Approximate paired intervals do not correct adaptive reuse.
6. Only then define a concise mission, representative public calibration, clear
   API/resources, fresh fixed challenge/holdout samples, and frozen targets for
   main's approval. None of those new-generation actions occur in this sidecar.
