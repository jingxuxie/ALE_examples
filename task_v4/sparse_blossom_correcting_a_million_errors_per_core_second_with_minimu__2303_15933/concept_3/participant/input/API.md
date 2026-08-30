# Complete API and simulator specification

## Process and resources

The evaluator launches a fresh program for each episode:

```text
/usr/bin/python3 /submission/solution.py
```

`/participant` is the read-only public package. `/submission` is precisely your
designated writable directory, not its parent. `/tmp` is fresh ephemeral storage.
System Python/NumPy/SciPy are installed under `/usr`. There is no network, host
home directory, evaluator tree, or host process visibility. Only your own episode
and public training data may inform the algorithm. Do not inspect simulator
internals or evade the process/resource boundary. Files in the submission may
persist, but episodes' hidden parameters are independent; no feedback is placed
there. Flush every stdout message. Send debugging output to stderr.

Budget: 40,000 shots, at most 64 query messages, 1–4,000 shots per query. Every
shot costs one unit regardless of configuration. Queries are sequential: wait
for the response before issuing another. There is no setup cost or time drift.
You may stop early. CPU allowance is 60 seconds per episode, single-threaded
numerical libraries, including Python imports, inference, and any descendants.
The 900-second episode wall watchdog plus a separate 300-second sandbox startup
allowance protects against overloaded hosts; wall delay is not the CPU score.
Address space is limited to 3 GiB. Exit successfully after the final response.

## Initial message

The first stdin line is `{"type":"hello","spec":SPEC}`.
There are no rate values, sampling seeds, or private episode identifiers in SPEC.

SPEC contains:

- `protocol`: `detector-calibration-v1`.
- `regime`: one of the three names in TASK.md.
- `detector_count`: 6, 7, or 8; syndrome histograms have length `2**detector_count`.
- `channels`: ordered list of 22, 24, or 26 channel objects. Each has `id`,
  `family`, `masks` (two integer detector bitmasks), `sector`, and
  `rate_bounds` (known lower and upper bounds for its unknown positive rate).
  `sector` is descriptive; the explicit exposure arrays are authoritative.
- `actions`: 29 objects with consecutive integer `id`, descriptive `name`,
  `mode_weights` (length 2, summing to one), `exposures` (2 by channel_count),
  and `alternate_probability` (length channel_count).
- `shot_budget`, `max_queries`, `max_shots_per_query`, `cpu_seconds`, `wall_seconds`.

All structural coefficients are known exactly. Rates are fixed within an episode
but unrelated to the public structure seed. Public bounds by family are:

| Family | Rate lower | Rate upper |
|---|---:|---:|
| boundary | 0.003 | 0.050 |
| bulk | 0.002 | 0.060 |
| hook | 0.0015 | 0.028 |
| rare | 0.00005 | 0.015 |

Training instances are representative, not a finite list of possible hidden
instances. Hidden structures and rates differ. Bounds are not priors you must use.

## One synthetic shot at action a

Let the unknown base rates be `lambda[k]`. Independently for each shot:

1. Sample ONE shared unobserved mode `z` from `actions[a].mode_weights`.
2. Conditional on z, sample independent binary channel firings with
   `q[a,z,k] = (1 - exp(-2 * exposures[a,z,k] * lambda[k])) / 2`.
3. Independently for every firing, choose `masks[1]` with probability
   `alternate_probability[a,k]`, otherwise `masks[0]`.
4. XOR all selected masks. The resulting integer is the observed syndrome.

Bit `d` means detector `d` fired; the least significant bit is detector 0.
Mask 0 is the no-click syndrome. Multiple faults can reinforce or cancel.
There are no additional unmodeled nuisance parameters. Different channels are
independent conditional on the shared mode, NOT necessarily marginally.
The single-shot mode is not redrawn separately for each channel. Both primary
and alternate masks may coincide. A rate is an intensity parameter, not q.
At exposure 1, its binary firing probability is `(1-exp(-2*lambda))/2`.
The family names describe this synthetic model, not particular physical devices.

The reference action uses primary masks only and has deliberately aliased
channels. Interventions alter exposure and alternative-footprint probabilities.
Sixteen configurations form four rare-channel gain ladders at exposures
20, 120, 720, and 4320. The low-rate end needs amplification; the same gain
can saturate a high-rate channel. The full intervention family is locally identifiable over tested instances;
reference-only data is insufficient. Very rare channels are amplified in some
configurations, while amplification can saturate other channels. More shots are
not automatically best spent at the largest exposure.

## Query and response

Write one line such as:

```json
{"type":"query","action":3,"shots":1000}
```

The evaluator responds with:

```text
{"type":"observation","action":3,"shots":1000,"counts":[...],
 "shots_remaining":39000,"queries_remaining":63}
```

`counts[s]` is the number of observed syndromes equal to integer s, and its sum
equals shots. It is a full joint histogram, not separate detector marginals.
For independent shots this histogram loses no information about their stationary
syndrome distribution. New queries receive independent new samples conditional
on the same hidden rates. Query partitioning need not reproduce an identical
random stream. No mode, fault labels, rates, gradients, or likelihoods are returned.
JSON values `true` and `false` are not accepted in place of integer arguments.
Unknown message types, extra keys, overspending, and invalid JSON invalidate the
episode. Do not print Markdown, progress text, or blank lines to stdout.

## Final submission

```text
{"type":"final","rates":[estimated_lambda_0,...,estimated_lambda_K_minus_1]}
```

Return finite strictly positive numbers in channel order, with exactly K values.
No clipping is performed by the scorer. You may constrain estimates to the known
rate bounds. After writing the final line, exit with code 0; no further messages
or queries are allowed. This is the entire deliverable interface; no imports of
your program occur in the hidden simulator/evaluator process.

## Loss and fixed targets

For every regime r and family f, pool all channels in that family across its four
hidden episodes. Let `C[r,f] = sqrt(mean(log(estimate/true_rate)**2))`. The primary
loss is the unweighted mean of the 12 values C, and the guardrail is their maximum.
The exact frozen numeric limits are in `targets.json`; both must pass. Each
family has the same number of channels within its regime across episodes.

Report conventions: `core_score=exp(-mean(C))`,
`worst_family_score=exp(-max(C))`; larger is better.
`runtime_score=max(0,1-max_episode_cpu_seconds/60)` is diagnostic, not an extra
accuracy gate. `valid` requires legal protocol, sandbox success, and resource use.
`passed` additionally requires both accuracy thresholds. A subset/training report
is not an official full-suite pass. Whole-suite accuracy is not fed back during
an episode. Decoder logical error rate and decoder runtime are NOT scored.

## Optional public numerical helper

Add `/participant/input` to `sys.path`, then `from model import Model`.
`Model(spec).distribution(log_rates)` returns an action-by-syndrome PMF.
`distribution(log_rates, gradient=True)` also returns an
action-by-channel-by-syndrome derivative with respect to log rates.
`fit(counts, initial=None, iterations=140)` performs bounded full-histogram ML;
`initial`, if supplied, is in log-rate units. `fisher(log_rates)` gives per-shot
Fisher matrices for log rates, one matrix per action. These helpers are optional;
their presence does not determine an allocation or make the baseline pass.

For a parity mask t, the exact syndrome character is

```text
odd[a,k,t] = (1-alt[a,k])*parity(t & mask[k,0])
             + alt[a,k]*parity(t & mask[k,1])
phi[a,t] = sum_z weight[a,z] * product_k (1 - 2*q[a,z,k]*odd[a,k,t])
P[a,s] = 2**(-D) * sum_t (-1)**parity(t & s) * phi[a,t]
```

The mixture outside the product and alternative-footprint factors make a single
linear log-parity inversion generally invalid. A graph-only pairwise covariance
formula does not isolate the overlapping higher-order channels.

## Public local development

From the participant directory, run:

```text
/usr/bin/python3 input/local.py --episode 0 -- /usr/bin/python3 baseline/uniform_ml.py
/usr/bin/python3 input/local.py --episode 1 -- /usr/bin/python3 /path/to/your/solution.py
```

For writable scratch space and a saved result, use your actual attempt directory:

```text
/usr/bin/python3 input/local.py --episode 0 --workdir /path/to/attempt --output /path/to/attempt/training_result.json -- /usr/bin/python3 /path/to/attempt/solution.py
```

No scratch files are required by the driver; without `--output` it writes only
stdout. It uses an ordinary subprocess, never nested bubblewrap. The optional
workdir must already exist and be writable. The driver sets `DETECTOR_INPUT_DIR`
to the actual public input directory, so a copied `baseline/uniform_ml.py` works
as `solution.py`. In official evaluation the copied baseline instead uses
`/participant/input`. Custom solutions can use the same two-path convention.

The local driver uses disclosed rates from `training.json` and an independent
multinomial sampler based on the analytic PMF. It reports a family-wise log RMSE.
It runs trusted local code without sandbox/resource enforcement; do not use it
for hidden evaluation. The official simulator instead samples mode and channel
events directly. The two implementations are statistically equivalent, not
random-stream identical. You may freely inspect training rates, change the local
sampler, create synthetic training episodes, or ignore all supplied helpers.
