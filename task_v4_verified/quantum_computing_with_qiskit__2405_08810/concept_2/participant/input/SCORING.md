# Exact costs and acceptance

## Count and weighted depth

The CX count is the number of submitted pairs. Gates are counted literally:
identity padding, cancelling pairs and explicit SWAP decompositions are not
removed by the checker.

Weighted depth is the ASAP completion time for the submitted wire order:

```python
ready = [0] * qubit_count
for control, target in gates:
    finish = max(ready[control], ready[target]) + duration[control, target]
    ready[control] = finish
    ready[target] = finish
weighted_depth = max(ready)
```

Durations are integer ticks, not seconds or unweighted layers. Gates on disjoint
wires can overlap even when separated in the list. Gates sharing **either** wire
must execute in their listed order, including mathematically commuting gates
with a shared control. The checker performs no commutation optimization. There
are no additional crosstalk, edge-neighborhood, controller or global-layer
constraints. No start times are submitted. The empty circuit has count and depth
zero. Both caps are inclusive, with exact integer comparison and no tolerance.

## Scores

`valid` means the complete JSON contract and all native-gate restrictions hold;
it does not imply correctness or efficiency. A target is `solved` exactly when
its matrix is correct **and** its count and weighted depth satisfy their caps.

For a valid submission:

- `core_score` is the number of solved targets divided by four.
- Each `family_scores` entry is the solved fraction among the two targets in that
  family; `worst_family_score` is the minimum of those two fractions.
- For each correct target, its resource score is
  `min(1, max_cx / max(1, cx_count), max_weighted_depth / max(1, weighted_depth))`.
  An incorrect target's resource score is zero. `resource_score` is the minimum
  of these four target scores, not an average and not a substitute for acceptance.
- `passed` is true **only if all four targets are solved**. Neither a high mean
  score nor one cheap target can compensate for another target's failure.

Malformed, incomplete, oversized or non-native submissions have `valid=false`,
`passed=false`, and all aggregate/family scores zero. Per-target diagnostics may
still show results for individually well-formed circuits, but earn no aggregate
credit on an invalid artifact. Incorrect matrices and exceeded scientific caps
do not alone make a structurally legal artifact invalid.

Reports contain `valid`, `passed`, `reason`, `core_score`, `worst_family_score`,
`resource_score`, `solved_targets`, `total_targets`, `family_scores` and
`per_target`. Each target includes its name, family, validity, correctness,
`cx_count`, `weighted_depth`, both caps, `count_ok`, `depth_ok`, `solved`, resource
score and reason. Correctly parsed native circuits also report the exact number
of `mismatch_entries`. Unmeasurable costs are JSON null in reports; report booleans
and nulls do not relax the stricter submission format.

## Local use

From the participant directory:

```bash
python baseline/solve.py --output /path/to/output/solution.json
python workspace/checker.py /path/to/output/solution.json
```

The baseline command exits zero when its artifact is legal and exact, even when
it misses the caps. The checker exits zero for full acceptance, one for a rejected
or unsolved artifact, and two for an invalid instance bundle. It writes a JSON
report to stdout. `--instances PATH` is available only on the local checker for
your own experiments; official evaluation always uses the fixed suite.

There is no submission-program runtime score. Offline synthesis effort is governed
by the surrounding attempt budget; grading only reads the bounded JSON artifact.
