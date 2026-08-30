# Files and policy schema, version 1

An input directory is one fleet. `manifest.json` contains `schema_version`,
`fleet_id`, `shared_sensor_count`, `shared_action_count`, integer dictionaries
`sensor_usage_caps` and `action_usage_caps`, and an ordered `cases` list.
Each case entry gives `case_id`, a `configuration` JSON filename, and a
`responses` NPZ filename. IDs are opaque strings; ordering and numerical
parameters can change. Design IDs are common across a fleet, while physical
phases, sensor times and permutation orders can differ by ring.

## Case configuration

The JSON contains the scalar Hamiltonian and loss fields in `PHYSICS.md`;
`L`, `nup`, `initial_up_sites`, `entropy_sites`, `t_final`, `open_loop_time`,
and integer `total_budget`; and these ordered lists:

- `regimes`: `regime_id`, `j2_multiplier`, `delta_multiplier`,
  `drive_multiplier`, `omega_multiplier`.
- `prior_scenarios`: `scenario_id` and `prior`, a normalized regime-ID map.
- `actions`: `action_id`, integer `cost`, and length-L `phase`.
- `sensors`: `sensor_id`, `time`, integer `cost`, `order`, length-L
  `permutation`, and `bridge_phase_by_sector`, an order-by-L real array.

`calibration_test` has `test_id`, integer `cost`, an ordered `results` list,
`likelihood_by_regime` (regime ID to normalized result-probability map),
`allowed_first_sensor_ids` (result to list), and
`allowed_second_sensor_ids_by_sector` (first ID to an order-length list of
second-sensor-ID lists). Those lists define admissible transitions.

NPZ archives contain only finite float64 arrays, loaded without pickle:

- `open`: shape `(number_of_regimes, number_of_actions)`, conditional loss.
- `route_F_K_S`: shape `(number_of_regimes, second_sensor_order,
  number_of_actions)`, **joint Born probability times conditional loss**.
  F and S are the first and second sensor indices in the case's sensors
  list. K is the first sector index. Arrays contain no calibration or prior
  factor. Their second axis is the second outcome.
- `probability_route_F_K_S`: shape `(number_of_regimes, second_sensor_order)`,
  joint Born probabilities of the first and second outcomes.

Only admissible route keys are present. Summing a probability route over its
second outcomes gives the first-sector probability, independent of second
sensor choice. Summing those first probabilities over all first sectors is
one. Zero-probability routes are retained.

## Output

Only the following keys are accepted, with `cases` in manifest order:

```
{
  "fleet_id": "...",
  "shared_sensors": ["..."],
  "shared_actions": ["..."],
  "cases": [
    {"case_id": "...", "root": "open", "action": "..."},
    {"case_id": "...", "root": "probe", "branches": [
      {"first_sensor": "...", "seconds": [
        {"second_sensor": "...", "actions": ["...", "..."]}
      ]}
    ]}
  ]
}
```

A probe policy has exactly one branch per calibration result in result order,
exactly one `seconds` entry per first sector in sector order, and exactly one
action per second sector in sector order. Open and probe cases can be mixed.
Actions cannot depend on the unobserved regime or prior scenario.

Shared lists contain distinct known IDs, **at most** their respective count
limits, and include every used design. They can include unused designs.
For every complete path, calibration cost + first sensor cost + second sensor
cost + action cost must not exceed `total_budget`. An open path pays only
its action cost. Bridge kicks cost zero.

Capacity counts **policy-tree occurrences**, never probability-weighted uses:
one first sensor per result branch, one second sensor per first-sector branch,
and one action per second-sector leaf, plus one action per open policy. Sum
these counts over the fleet and enforce every ID's cap. All branches count,
including mathematically zero-probability branches. No pruning or default
branches are permitted.

For a fleet the objective is the maximum of all case/scenario expected losses.
For each hidden fleet define `improvement = 100*(1-objective/baseline_objective)`.
Average within each family; `core_score` is the mean of those family averages
and `worst_family_score` their minimum. Negative improvements are not clipped.
Both targets in `TASK.md` must be met and every fleet must be valid within its
resource allowance. Runtime has no quality bonus; resource score is diagnostic.

Hidden envelopes: 6-10 rings per fleet, L in {6,8,10}, at most 5 regimes,
6 scenarios, 3 calibration results, 9 sensor designs, 12 action designs,
permutation order at most 5, and shared count limits between 3 and 5. At least
one feasible fleet policy exists. Public examples use four rings for convenience.
The solver has one input fleet per process and cannot retain state between
fleets. The evaluator's private physics time is outside the solver allowance.
