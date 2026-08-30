# Observation law and JSON-lines API

## Public specification

The first line is `{"type":"hello","spec":{...}}`. The specification contains:

- `protocol`: `efficient-detector-calibration-v2`;
- `detector_count`: D, between 14 and 20;
- `detector_edges`: connected undirected locality graph, zero-based endpoints;
- `regime`: `chain_hooks`, `patch_crosstalk`, or `burst_aliases`;
- `topology`: ladder, patch, or triangular, respectively;
- `channels`: ordered K objects with `id`, `family`, `masks`, `rate_bounds`, and
  `sector`. Families are boundary, bulk, hook, rare. `sector` is a public
  intervention grouping, not an unobserved label;
- `actions`: ordered action objects with `id`, `name`, `mode_weights` (length 2),
  `exposures` (2 by K), and `alternate_probability` (length K);
- budget fields `shot_budget`, `max_queries`, `max_shots_per_query`,
  `cpu_seconds`, `wall_seconds`, and `observation_encoding`.

Masks are integer bitmasks. Bit d is detector d. Each channel has two known
possible XOR footprints, `masks[0]` (primary) and `masks[1]` (alternate), which
may coincide. Their union is local, of graph diameter at most two and at most
four detectors. Boundary footprints are singletons; bulk channels are graphlike;
hook and rare channels include higher-order footprints and overlapping aliases.
All detectors participate. K scales with actual graph structure, not padding.

The target is one positive intensity rate lambda[k] for each channel in this
order, constrained by its published `rate_bounds`. It is NOT an action-specific
firing probability. No rates are tied or known. Public controls include broad,
sector-selective, correlation-selective, and rare-channel gain-ladder exposures.
Their numerical arrays are authoritative; do not infer behavior just from names.

## Exact per-shot stochastic law

For a requested action a, independently for each shot:

1. Draw one shared mode m with probabilities `actions[a].mode_weights`.
2. Conditional on that mode, each channel k fires independently with
   `q[a,m,k] = (1 - exp(-2 * exposures[a,m,k] * lambda[k])) / 2`.
3. Independently choose that channel's alternate footprint with probability
   `alternate_probability[a,k]`, otherwise its primary footprint.
4. The observed syndrome is the bitwise XOR of the chosen footprints of all
   firing channels. Non-firing channels contribute zero.

There is only one shared mode per shot, not one mode per channel. Footprint
choices are independent of the mode and of other choices given the action.
Modes are not observed. Marginalizing the mode generally makes disjoint
channel firings dependent. Shots are independent conditional on the fixed
episode's rates and requested actions; no temporal drift occurs.

For an arbitrary parity mask t define

```
o[a,k,t] = (1-alt[a,k]) * parity(mask[k,0] & t)
           + alt[a,k] * parity(mask[k,1] & t)
phi[a,t] = sum_m weight[a,m]
           * product_k (1 - (1-exp(-2*exposure[a,m,k]*lambda[k])) * o[a,k,t])
```

Here `phi[a,t] = E[(-1)^popcount(syndrome & t)]`. This gives exact projected
moments, not a pairwise-covariance shortcut. For two such observed characters,
their same-shot covariance is `phi[a,t XOR u] - phi[a,t]*phi[a,u]`.
Treating overlapping marginals or shared-mode blocks as independent is an approximation,
not a property of the law. `moments.py` supplies an exact selected-parity helper;
it does not supply a full efficient estimator or an experiment-design policy.

## Queries and observations

Send exactly these keys, with integer action index and shot count:

```
{"type":"query","action":3,"shots":1000}
```

The parent returns one sparse histogram:

```
{"type":"observation","action":3,"shots":1000,"encoding":"sparse_histogram_v1","syndromes":[0,1,3],"multiplicities":[950,30,20],"shots_remaining":39000,"queries_remaining":63}
```

The sample numbers illustrate encoding, not a promised distribution. Syndrome
codes are sorted, unique integers in `[0, 2**D)`. Multiplicities are positive
integers summing to `shots`. Absent codes have count zero. This is lossless
compression of the full shot sample for this independent-shot experiment;
there is no truncation, censoring, marginal-only response, or extra free sample.
At most one outstanding request is permitted. Flush stdout after each line.
Actions may be repeated. All shots cost one unit, regardless of exposure.

## Final answer and errors

Send exactly `{"type":"final","rates":[...]}` with K finite positive numbers
in channel order, then exit successfully without further output. Bounds are
useful modeling information; positivity and finiteness are mandatory. You may
finish before exhausting the budget. No accuracy or reward feedback is sent
to the worker, during or after an episode. A new process starts each episode.

Wrong keys/types, nonfinite or nonpositive estimates, malformed JSON, invalid
indices, overspending, oversized output lines (>1 MiB), extra output after the
final answer, nonzero exit, or exceeding CPU/wall limits invalidates the run.
No networking or package installation is available. Writable submission files
may persist; neither private sibling directories nor rates/seeds are mounted.

CPU includes Python imports, numerical computation, and waited-for descendant
processes. The trusted supervisor enforces CPU/address-space limits and signs
its usage report. Runtime score is `max(0, 1-max_episode_cpu/60)`; recovery
thresholds and resource validity, not a separate minimum runtime score, decide
pass. Core/worst scores are exp(-mean log RMSE) and exp(-worst cell log RMSE).

## Development and reference compatibility

`training.json` has six public episodes, including rates and sampling seeds.
`simulator.py` implements the explicit event law. `local.py` uses ordinary
subprocesses so it works inside a participant-only allowlist without nested
bwrap. Supply an existing writable `--workdir`; any `--output` must be inside
it. It sets `DETECTOR_INPUT_DIR` for a copied baseline, so public files can stay
read-only. It reports training accuracy, not hidden-suite pass or resource
qualification. Run from the participant directory and set `ATTEMPT_DIR` to the
launcher-provided writable path, as shown in `TASK.md`. The hidden evaluator's
`/participant` and `/submission` names are not assumed in public development.
Only the hidden evaluator requires escalated bwrap.

To test the supplied historical policy without changing its source, run from
the participant directory with `ATTEMPT_DIR` set as described above:

```
/usr/bin/python3 input/local.py --episode 0 --workdir "$ATTEMPT_DIR" --output "$ATTEMPT_DIR/reference_report.json" -- /usr/bin/python3 "$PWD/input/legacy_bridge.py" /usr/bin/python3 "$PWD/baseline/previous_champion.py"
```

The bridge expands sparse observations inside the worker and restores its old
protocol identifier. It does not reveal latent values or change the law.
Both reference programs are optional starting points; neither is a promised
passing solution for this task.

## Scientific scope

Sparse Blossom (arXiv:2303.15933) motivates decoding with known weighted graph
models; arXiv:2504.20212 motivates syndrome-only graph/hypergraph calibration
and higher-order information. This benchmark introduces synthetic intervention
and shared-mode mechanisms. It does not reproduce either paper's physical
experiments, claim hardware fidelity, or measure logical decoding performance.
The scored objective is solely rate recovery under constrained experimentation.
