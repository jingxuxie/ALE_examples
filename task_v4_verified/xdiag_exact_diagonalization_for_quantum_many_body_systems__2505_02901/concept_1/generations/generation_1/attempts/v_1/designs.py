import itertools
import time

import numpy as np

from fleet import route_array
from lpsearch import ForestModel


def capacity_possible(manifest, cases, sensor_set, ceiling, open_losses=None):
    selected = set(sensor_set)
    first_orders = {}
    second_ids = set()
    branches_needed = 0
    for case_index, data in enumerate(cases):
        case = data['configuration']
        if open_losses is None:
            affordable = [data['action_index'][entry['action_id']] for entry in case['actions']
                          if entry['cost'] <= case['total_budget']]
            open_loss = (np.max(data['priors'] @ data['table']['open'][:, affordable], axis=0).min()
                         if affordable else float('inf'))
        else:
            open_loss = open_losses[case_index]
        if open_loss < ceiling - 1e-8:
            continue
        probe = case['calibration_test']
        sensors = {entry['sensor_id']: entry for entry in case['sensors']}
        for result in probe['results']:
            available = []
            for first in probe['allowed_first_sensor_ids'][result]:
                if first not in selected:
                    continue
                sectors = probe['allowed_second_sensor_ids_by_sector'][first]
                if all(selected.intersection(allowed) for allowed in sectors):
                    available.append(first)
                    first_orders[first] = min(first_orders.get(first, 1000), sensors[first]['order'])
                    for allowed in sectors:
                        second_ids.update(selected.intersection(allowed))
            if not available:
                return False
            branches_needed += 1
    remaining = branches_needed
    second_needed = 0
    for first, order in sorted(first_orders.items(), key=lambda entry: entry[1]):
        count = min(remaining, manifest['sensor_usage_caps'][first])
        remaining -= count
        second_needed += count * order
    return remaining == 0 and second_needed <= sum(manifest['sensor_usage_caps'][name] for name in second_ids)


def rank_designs(manifest, cases, ceiling, deadline):
    sensor_ids = list(manifest['sensor_usage_caps'])
    action_ids = list(manifest['action_usage_caps'])
    sensor_sets = [selection for selection in itertools.combinations(
        sensor_ids, min(len(sensor_ids), manifest['shared_sensor_count']))
                   if capacity_possible(manifest, cases, selection, ceiling)]
    action_sets = list(itertools.combinations(action_ids, min(len(action_ids), manifest['shared_action_count'])))
    if not sensor_sets or not action_sets:
        return sensor_sets, action_sets, np.empty((0, 0)), None
    sensor_masks = {name: np.array([name in selection for selection in sensor_sets]) for name in sensor_ids}
    bounds = np.zeros((len(sensor_sets), len(action_sets)))
    open_losses = np.empty((len(cases), len(action_sets)))
    for case_index, data in enumerate(cases):
        case = data['configuration']
        selection_indices = np.array([[data['action_index'][name] for name in selection]
                                      for selection in action_sets])
        open_values = np.max(data['priors'] @ data['table']['open'], axis=0)
        for entry in case['actions']:
            if entry['cost'] > case['total_budget']:
                open_values[data['action_index'][entry['action_id']]] = np.inf
        open_losses[case_index] = open_values[selection_indices].min(axis=1)
    ordering = np.argsort(-open_losses.min(axis=1))
    for case_index in ordering:
        if time.monotonic() > deadline:
            break
        data = cases[case_index]
        case = data['configuration']
        probe = case['calibration_test']
        sensors = {entry['sensor_id']: entry for entry in case['sensors']}
        selection_indices = np.array([[data['action_index'][name] for name in selection]
                                      for selection in action_sets])
        action_costs = np.array([entry['cost'] for entry in case['actions']])
        weights = np.vstack((data['priors'], data['priors'].mean(axis=0)))
        shape = (len(sensor_sets), len(weights), len(action_sets))
        scores = np.zeros(shape)
        route_scores = {}
        for first, sectors in probe['allowed_second_sensor_ids_by_sector'].items():
            if first not in sensor_masks or not sensor_masks[first].any():
                continue
            for sector, allowed in enumerate(sectors):
                for second in allowed:
                    if not sensor_masks[second].any():
                        continue
                    route = route_array(data, first, sector, second)
                    losses = np.einsum('sq,rq,qla->rsla', weights, data['likelihood'], route)
                    available = (action_costs + probe['cost'] + sensors[first]['cost']
                                 + sensors[second]['cost'] <= case['total_budget'])
                    losses[..., ~available] = np.inf
                    route_scores[first, sector, second] = losses[..., selection_indices].min(axis=-1).sum(axis=2)
        for result_index, result in enumerate(probe['results']):
            first_best = np.full(shape, np.inf)
            for first in probe['allowed_first_sensor_ids'][result]:
                if not sensor_masks[first].any():
                    continue
                first_score = np.zeros(shape)
                for sector, allowed in enumerate(probe['allowed_second_sensor_ids_by_sector'][first]):
                    second_best = np.full(shape, np.inf)
                    for second in allowed:
                        key = first, sector, second
                        if key not in route_scores:
                            continue
                        included = sensor_masks[second]
                        second_best[included] = np.minimum(second_best[included], route_scores[key][result_index])
                    first_score += second_best
                first_score[~sensor_masks[first]] = np.inf
                np.minimum(first_best, first_score, out=first_best)
            scores += first_best
        case_bound = np.minimum(scores.max(axis=1), open_losses[case_index])
        np.maximum(bounds, case_bound, out=bounds)
    return sensor_sets, action_sets, bounds, open_losses


def strengthen_bounds(manifest, cases, sensor_sets, action_sets, bounds, ceiling, deadline):
    all_actions = tuple(manifest['action_usage_caps'])
    for sensor_index in np.argsort(bounds.min(axis=1)):
        if time.monotonic() > deadline - 0.05:
            break
        sensors = sensor_sets[sensor_index]
        if bounds[sensor_index].min() >= ceiling - 1e-8:
            continue
        model = ForestModel(manifest, cases, sensors, all_actions, ceiling)
        if not model.valid:
            continue
        model.bounds[0, 0] = 0.0
        root = model.relaxation(deadline=min(deadline, time.monotonic() + 0.7))
        if root is None:
            continue
        weight_sum = sum(float(np.maximum(0.0, -root.ineqlin.marginals[rows]).sum())
                         for rows in model.case_loss_rows if rows is not None)
        weight_scale = max(1.0, weight_sum)
        prices = np.maximum(0.0, -root.ineqlin.marginals[:len(sensors) + len(all_actions)])
        sensor_prices = dict(zip(sensors, prices[:len(sensors)]))
        action_prices = dict(zip(all_actions, prices[len(sensors):]))
        capacity = np.array([manifest['sensor_usage_caps'][name] for name in sensors]
                            + [manifest['action_usage_caps'][name] for name in all_actions])
        lower = np.full(len(action_sets), -float(prices @ capacity))
        for case_index, data in enumerate(cases):
            rows = model.case_loss_rows[case_index]
            if rows is None:
                continue
            weights = np.maximum(0.0, -root.ineqlin.marginals[rows]) / weight_scale
            if weights.sum() < 1e-12:
                continue
            case = data['configuration']
            probe = case['calibration_test']
            sensor_map = {entry['sensor_id']: entry for entry in case['sensors']}
            selection_indices = np.array([[data['action_index'][name] for name in selection]
                                          for selection in action_sets])
            action_costs = np.array([entry['cost'] for entry in case['actions']])
            action_penalties = np.array([action_prices[entry['action_id']] for entry in case['actions']])
            regime_weights = weights @ data['priors']
            total = np.zeros(len(action_sets))
            for result_index, result in enumerate(probe['results']):
                first_best = np.full(len(action_sets), np.inf)
                posterior = regime_weights * data['likelihood'][result_index]
                for first in probe['allowed_first_sensor_ids'][result]:
                    if first not in sensor_prices:
                        continue
                    first_cost = np.full(len(action_sets), sensor_prices[first])
                    for sector, allowed in enumerate(probe['allowed_second_sensor_ids_by_sector'][first]):
                        second_best = np.full(len(action_sets), np.inf)
                        for second in allowed:
                            if second not in sensor_prices:
                                continue
                            route = route_array(data, first, sector, second)
                            loss = np.einsum('q,qla->la', posterior, route) + action_penalties
                            available = (action_costs + probe['cost'] + sensor_map[first]['cost']
                                         + sensor_map[second]['cost'] <= case['total_budget'])
                            loss[:, ~available] = np.inf
                            costs = loss[:, selection_indices].min(axis=-1).sum(axis=0) + sensor_prices[second]
                            np.minimum(second_best, costs, out=second_best)
                        first_cost += second_best
                    np.minimum(first_best, first_cost, out=first_best)
                total += first_best
            open_values = np.max(data['priors'] @ data['table']['open'], axis=0)
            affordable = action_costs <= case['total_budget']
            if affordable.any() and np.min(open_values[affordable]) < ceiling - 1e-8:
                scalar_open = regime_weights @ data['table']['open'] + action_penalties
                scalar_open[~affordable] = np.inf
                np.minimum(total, scalar_open[selection_indices].min(axis=1), out=total)
            lower += total
        np.maximum(bounds[sensor_index], lower - 2e-7, out=bounds[sensor_index])
