import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import argparse
import heapq
import itertools
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog, linear_sum_assignment
from scipy.sparse import coo_matrix


class Case:
    def __init__(self, config, table, sensor_ids, action_ids):
        self.config = config
        self.case_id = config['case_id']
        self.sensor_ids = sensor_ids
        self.action_ids = action_ids
        sensor_index = {name: index for index, name in enumerate(sensor_ids)}
        action_index = {name: index for index, name in enumerate(action_ids)}
        regime_ids = [entry['regime_id'] for entry in config['regimes']]
        self.priors = np.array([[entry['prior'][name] for name in regime_ids]
                                for entry in config['prior_scenarios']])
        test = config['calibration_test']
        self.likelihood = np.array([[test['likelihood_by_regime'][name][result]
                                     for name in regime_ids] for result in test['results']])
        self.result_count = len(test['results'])
        self.scenario_count = len(self.priors)
        self.sensor_count = len(sensor_ids)
        self.action_count = len(action_ids)
        self.orders = np.zeros(len(sensor_ids), dtype=int)
        self.sensor_costs = np.zeros(len(sensor_ids), dtype=int)
        for sensor in config['sensors']:
            index = sensor_index[sensor['sensor_id']]
            self.orders[index] = sensor['order']
            self.sensor_costs[index] = sensor['cost']
        self.action_costs = np.zeros(len(action_ids), dtype=int)
        action_reorder = []
        original_actions = {entry['action_id']: index for index, entry in enumerate(config['actions'])}
        for name in action_ids:
            action_reorder.append(original_actions[name])
            self.action_costs[action_index[name]] = config['actions'][original_actions[name]]['cost']
        self.open = (self.priors @ table['open'])[:, action_reorder]
        self.open[:, self.action_costs > config['total_budget']] = np.inf
        self.allowed_first = [[sensor_index[name] for name in test['allowed_first_sensor_ids'][result]]
                              for result in test['results']]
        self.first_ids = sorted(set(sum(self.allowed_first, [])))
        self.routes = []
        self.route_by_first = {}
        original_sensors = {entry['sensor_id']: index for index, entry in enumerate(config['sensors'])}
        for first in self.first_ids:
            self.route_by_first[first] = []
            for sector, names in enumerate(test['allowed_second_sensor_ids_by_sector'][sensor_ids[first]]):
                indices = []
                for name in names:
                    second = sensor_index[name]
                    key = 'route_{}_{}_{}'.format(original_sensors[sensor_ids[first]], sector,
                                                  original_sensors[name])
                    raw = table[key][:, :, action_reorder]
                    loss = np.einsum('sq,rq,qoa->rsoa', self.priors, self.likelihood, raw)
                    allowed = self.action_costs + self.sensor_costs[first] + self.sensor_costs[second] + test['cost'] <= config['total_budget']
                    indices.append(len(self.routes))
                    self.routes.append((first, second, loss, allowed))
                self.route_by_first[first].append(indices)
        self.mean_costs = [entry[2].mean(axis=1) for entry in self.routes]

    def pack(self, tree, losses, sensors, actions):
        return (float(np.max(losses)), losses, sensors, actions, tree)

    def open_policy(self, action):
        sensors = np.zeros(self.sensor_count, dtype=int)
        actions = np.zeros(self.action_count, dtype=int)
        actions[action] = 1
        return self.pack(action, self.open[:, action].copy(), sensors, actions)

    def dynamic(self, sensor_set, action_set, sensor_caps, action_caps, weights=None,
                sensor_price=None, action_price=None, result_order=None):
        if weights is None:
            costs = self.mean_costs
        else:
            costs = [np.einsum('s,rsoa->roa', weights, entry[2]) for entry in self.routes]
        if sensor_price is None:
            sensor_price = np.zeros(self.sensor_count)
        if action_price is None:
            action_price = np.zeros(self.action_count)
        sensor_remaining = sensor_caps.copy()
        action_remaining = action_caps.copy()
        branches = [None] * self.result_count
        losses = np.zeros(self.scenario_count)
        if result_order is None:
            result_order = range(self.result_count)
        for result in result_order:
            best = None
            for first in self.allowed_first[result]:
                if not sensor_set[first] or sensor_remaining[first] < 1:
                    continue
                local_sensors = sensor_remaining.copy()
                local_actions = action_remaining.copy()
                local_sensors[first] -= 1
                branch_loss = np.zeros(self.scenario_count)
                branch_score = sensor_price[first]
                seconds = []
                for route_indices in self.route_by_first[first]:
                    best_second = None
                    for route_index in route_indices:
                        _, second, route_loss, allowed = self.routes[route_index]
                        if not sensor_set[second] or local_sensors[second] < 1:
                            continue
                        available = action_set & allowed & (local_actions > 0)
                        if not np.any(available):
                            continue
                        prices = costs[route_index][result] + action_price
                        masked = np.where(available, prices, np.inf)
                        chosen = np.argmin(masked, axis=1)
                        usage = np.bincount(chosen, minlength=self.action_count)
                        if np.any(usage > local_actions):
                            remaining = local_actions.copy()
                            chosen = chosen.copy()
                            for outcome in range(len(chosen)):
                                choices = np.where(available & (remaining > 0), prices[outcome], np.inf)
                                action = int(np.argmin(choices))
                                if not np.isfinite(choices[action]):
                                    break
                                chosen[outcome] = action
                                remaining[action] -= 1
                            else:
                                usage = local_actions - remaining
                                score = float(prices[np.arange(len(chosen)), chosen].sum()) + sensor_price[second]
                                if best_second is None or score < best_second[0]:
                                    best_second = (score, route_index, chosen, usage)
                            continue
                        score = float(prices[np.arange(len(chosen)), chosen].sum()) + sensor_price[second]
                        if best_second is None or score < best_second[0]:
                            best_second = (score, route_index, chosen, usage)
                    if best_second is None:
                        break
                    score, route_index, chosen, usage = best_second
                    _, second, route_loss, _ = self.routes[route_index]
                    branch_score += score
                    branch_loss += route_loss[result, :, np.arange(len(chosen)), chosen].sum(axis=0)
                    local_sensors[second] -= 1
                    local_actions -= usage
                    seconds.append((route_index, chosen))
                else:
                    if best is None or branch_score < best[0]:
                        best = (branch_score, first, seconds, branch_loss, local_sensors, local_actions)
            if best is None:
                return None
            _, first, seconds, branch_loss, sensor_remaining, action_remaining = best
            branches[result] = (first, seconds)
            losses += branch_loss
        return self.pack(branches, losses, sensor_caps - sensor_remaining, action_caps - action_remaining)

    def output(self, policy):
        tree = policy[4]
        if isinstance(tree, (int, np.integer)):
            return {'case_id': self.case_id, 'root': 'open', 'action': self.action_ids[tree]}
        return {'case_id': self.case_id, 'root': 'probe', 'branches': [
            {'first_sensor': self.sensor_ids[first], 'seconds': [
                {'second_sensor': self.sensor_ids[self.routes[route_index][1]],
                 'actions': [self.action_ids[action] for action in chosen]}
                for route_index, chosen in seconds]} for first, seconds in tree]}


def load(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    sensor_ids = list(manifest['sensor_usage_caps'])
    action_ids = list(manifest['action_usage_caps'])
    cases = []
    for entry in manifest['cases']:
        config = json.loads((directory / entry['configuration']).read_text())
        with np.load(directory / entry['responses'], allow_pickle=False) as archive:
            table = {name: archive[name] for name in archive.files if not name.startswith('probability_')}
        cases.append(Case(config, table, sensor_ids, action_ids))
    return manifest, cases


def design_rank(cases, sensor_sets, action_sets, sensor_caps, deadline):
    sensor_count = len(sensor_sets)
    action_count = len(action_sets)
    rank = np.zeros((sensor_count, action_count))
    opens = []
    for case in cases:
        open_loss = np.max(case.open, axis=0)[action_sets].min(axis=1)
        opens.append(open_loss)
        bounds = np.zeros_like(rank)
        weights_list = [np.full(case.scenario_count, 1 / case.scenario_count)]
        weights_list.extend(np.eye(case.scenario_count))
        for weights in weights_list:
            route_values = []
            for _, second, loss, allowed in case.routes:
                scalar = np.einsum('s,rsoa->roa', weights, loss)
                scalar = np.where(allowed, scalar, np.inf)
                route_values.append(scalar[:, :, action_sets].min(axis=-1).sum(axis=1))
            probe_value = np.zeros_like(rank)
            for result in range(case.result_count):
                first_values = []
                for first in case.allowed_first[result]:
                    first_value = np.zeros_like(rank)
                    for indices in case.route_by_first[first]:
                        alternatives = [np.where(sensor_sets[:, case.routes[index][1], None],
                                                 route_values[index][result][None, :], np.inf)
                                        for index in indices]
                        first_value += np.minimum.reduce(alternatives) if alternatives else np.inf
                    first_value[~sensor_sets[:, first]] = np.inf
                    first_values.append(first_value)
                probe_value += np.minimum.reduce(first_values) if first_values else np.inf
            bounds = np.maximum(bounds, probe_value)
        rank = np.maximum(rank, np.minimum(bounds, open_loss[None, :]))
        if time.monotonic() > deadline:
            break
    if len(opens) == len(cases):
        first_ids = sorted(set(sum([case.first_ids for case in cases], [])))
        first_capacity = sensor_sets[:, first_ids] @ sensor_caps[first_ids]
        second_ids = sorted({route[1] for case in cases for route in case.routes})
        minimum_orders = np.min([case.orders for case in cases], axis=0)
        open_array = np.array(opens)
        for sensor_index in range(sensor_count):
            second_capacity = np.sum(sensor_caps[second_ids] * sensor_sets[sensor_index, second_ids])
            orders = []
            for first in first_ids:
                if sensor_sets[sensor_index, first]:
                    orders.extend([minimum_orders[first]] * min(int(sensor_caps[first]), 40))
            total_orders = np.cumsum(sorted(orders))
            branch_limit = min(first_capacity[sensor_index], np.searchsorted(total_orders, second_capacity, side='right'))
            limit = branch_limit // min(case.result_count for case in cases)
            if limit < len(cases):
                sorted_open = np.sort(open_array, axis=0)[::-1]
                rank[sensor_index] = np.maximum(rank[sensor_index], sorted_open[int(limit)])
    return rank


def construct(cases, sensor_set, action_set, sensor_caps, action_caps, rng, variation=0):
    sensor_remaining = sensor_caps.copy()
    action_remaining = action_caps.copy()
    open_costs = [np.where(action_set, np.max(case.open, axis=0), np.inf) for case in cases]
    selected = assign(open_costs, action_caps)
    if selected is None:
        return None
    policies = []
    for case, action in zip(cases, selected):
        policy = case.open_policy(action)
        policies.append(policy)
        action_remaining -= policy[3]
    order = np.argsort([-policy[0] for policy in policies])
    if variation % 5 == 2:
        rng.shuffle(order)
    elif variation % 5 == 3:
        order = np.argsort([-policy[0] * rng.uniform(.75, 1.25) for policy in policies])
    for position, index in enumerate(order):
        case = cases[index]
        old = policies[index]
        action_remaining += old[3]
        best = old
        weights = np.full(case.scenario_count, 1 / case.scenario_count)
        if variation % 4 == 1:
            weights = rng.dirichlet(np.full(case.scenario_count, .5))
        elif variation % 4 == 2:
            weights = np.eye(case.scenario_count)[np.argmax(old[1])]
        scale = [0, .001, .003, .0003, .008, .0001][variation % 6]
        sensor_price = scale * sensor_caps / np.maximum(sensor_remaining, .4)
        action_price = .15 * scale * action_caps / np.maximum(action_remaining, .4)
        result_order = np.arange(case.result_count)
        if variation % 3:
            rng.shuffle(result_order)
        for iteration in range(3 if variation else 2):
            candidate = case.dynamic(sensor_set, action_set, sensor_remaining, action_remaining,
                                     weights, sensor_price, action_price, result_order)
            if candidate is None:
                break
            if candidate[0] < best[0]:
                best = candidate
            worst = int(np.argmax(candidate[1]))
            weights *= .55
            weights[worst] += .45
        policies[index] = best
        sensor_remaining -= best[2]
        action_remaining -= best[3]
    return policies


def leaf_refine(cases, policies, action_set, action_caps, deadline, force=False):
    leaves = []
    case_leaves = [[] for _ in cases]
    for case_index, (case, policy) in enumerate(zip(cases, policies)):
        if isinstance(policy[4], (int, np.integer)):
            allowed = np.flatnonzero(action_set & np.isfinite(case.open[0]))
            case_leaves[case_index].append(len(leaves))
            leaves.append((case_index, None, None, None, allowed, case.open[:, allowed]))
        else:
            for result, (_, seconds) in enumerate(policy[4]):
                for sector, (route_index, chosen) in enumerate(seconds):
                    _, second, loss, allowed_mask = case.routes[route_index]
                    allowed = np.flatnonzero(action_set & allowed_mask)
                    for outcome in range(len(chosen)):
                        case_leaves[case_index].append(len(leaves))
                        leaves.append((case_index, result, sector, outcome, allowed, loss[result, :, outcome, :][:, allowed]))
    offsets = np.cumsum([0] + [len(leaf[4]) for leaf in leaves])
    variable_count = int(offsets[-1])
    row_indices, col_indices, values = [], [], []
    equality_rows, equality_cols = [], []
    scenario_offsets = np.cumsum([len(action_caps)] + [case.scenario_count for case in cases])
    for leaf_index, leaf in enumerate(leaves):
        case_index, _, _, _, allowed, loss = leaf
        columns = np.arange(offsets[leaf_index], offsets[leaf_index + 1])
        equality_rows.extend([leaf_index] * len(columns))
        equality_cols.extend(columns)
        row_indices.extend(allowed)
        col_indices.extend(columns)
        values.extend(np.ones(len(columns)))
        for scenario in range(cases[case_index].scenario_count):
            row_indices.extend([scenario_offsets[case_index] + scenario] * len(columns))
            col_indices.extend(columns)
            values.extend(loss[scenario])
    for row in range(len(action_caps), scenario_offsets[-1]):
        row_indices.append(row)
        col_indices.append(variable_count)
        values.append(-1.)
    matrix = coo_matrix((values, (row_indices, col_indices)),
                        shape=(scenario_offsets[-1], variable_count + 1)).tocsc()
    equality = coo_matrix((np.ones(len(equality_rows)), (equality_rows, equality_cols)),
                          shape=(len(leaves), variable_count + 1)).tocsc()
    objective = np.zeros(variable_count + 1)
    objective[-1] = 1
    upper = np.r_[action_caps, np.zeros(scenario_offsets[-1] - len(action_caps))]
    result = linprog(objective, A_ub=matrix, b_ub=upper, A_eq=equality, b_eq=np.ones(len(leaves)),
                     bounds=(0, None), method='highs', options={'time_limit': max(.01, min(2, deadline-time.monotonic()))})
    if not result.success:
        return None if force else policies
    probabilities = result.x[:variable_count]
    score = -probabilities
    score += 1e-5 * np.concatenate([leaf[5].mean(axis=0) for leaf in leaves])
    capacity_matrix = matrix[:len(action_caps), :variable_count]
    transport = linprog(score, A_ub=capacity_matrix, b_ub=action_caps,
                        A_eq=equality[:, :variable_count], b_eq=np.ones(len(leaves)),
                        bounds=(0, None), method='highs',
                        options={'time_limit': max(.01, min(2, deadline-time.monotonic()))})
    if not transport.success:
        return None if force else policies
    new_trees = []
    for policy in policies:
        if isinstance(policy[4], (int, np.integer)):
            new_trees.append(policy[4])
        else:
            new_trees.append([(first, [(route_index, chosen.copy()) for route_index, chosen in seconds])
                              for first, seconds in policy[4]])
    losses = [np.zeros(case.scenario_count) for case in cases]
    usages = [np.zeros(len(action_caps), dtype=int) for _ in cases]
    selections = []
    for leaf_index, leaf in enumerate(leaves):
        case_index, result_index, sector, outcome, allowed, loss = leaf
        selection = int(np.argmax(transport.x[offsets[leaf_index]:offsets[leaf_index+1]]))
        selections.append(selection)
        action = int(allowed[selection])
        losses[case_index] += loss[:, selection]
        usages[case_index][action] += 1
        if result_index is None:
            new_trees[case_index] = action
        else:
            new_trees[case_index][result_index][1][sector][1][outcome] = action
    total_usage = np.sum(usages, axis=0)
    for case_index in np.argsort([-np.max(loss) for loss in losses]):
        for iteration in range(35):
            current_score = np.max(losses[case_index]) + 1e-5 * np.mean(losses[case_index])
            best_change = None
            for leaf_index in case_leaves[case_index]:
                leaf = leaves[leaf_index]
                allowed, loss = leaf[4], leaf[5]
                old_selection = selections[leaf_index]
                old_action = int(allowed[old_selection])
                candidate_losses = losses[case_index][:, None] + loss - loss[:, old_selection, None]
                scores = candidate_losses.max(axis=0) + 1e-5 * candidate_losses.mean(axis=0)
                scores[(total_usage[allowed] >= action_caps[allowed]) & (allowed != old_action)] = np.inf
                selection = int(np.argmin(scores))
                if scores[selection] < current_score - 1e-11:
                    if best_change is None or scores[selection] < best_change[0]:
                        best_change = (scores[selection], leaf_index, selection)
            if best_change is None:
                break
            _, leaf_index, selection = best_change
            _, result_index, sector, outcome, allowed, loss = leaves[leaf_index]
            old_selection = selections[leaf_index]
            old_action, action = int(allowed[old_selection]), int(allowed[selection])
            losses[case_index] += loss[:, selection] - loss[:, old_selection]
            usages[case_index][old_action] -= 1
            usages[case_index][action] += 1
            total_usage[old_action] -= 1
            total_usage[action] += 1
            selections[leaf_index] = selection
            if result_index is None:
                new_trees[case_index] = action
            else:
                new_trees[case_index][result_index][1][sector][1][outcome] = action
            if time.monotonic() > deadline:
                break
    refined = [case.pack(tree, loss, old[2], usage)
               for case, tree, loss, old, usage in zip(cases, new_trees, losses, policies, usages)]
    if np.any(np.sum(usages, axis=0) > action_caps):
        return None if force else policies
    if force or max(policy[0] for policy in refined) < max(policy[0] for policy in policies):
        return refined
    return policies


def assign(costs, capacities):
    if len(costs) == 0:
        return []
    slots = np.repeat(np.arange(len(capacities)), np.minimum(capacities, len(costs)))
    if len(slots) < len(costs):
        return None
    matrix = np.asarray(costs)[:, slots]
    rows, columns = linear_sum_assignment(np.where(np.isfinite(matrix), matrix, 1e20))
    if not np.all(np.isfinite(matrix[rows, columns])):
        return None
    return slots[columns]


def joint_construct(cases, sensor_set, action_set, sensor_caps, action_caps, rng,
                    target, deadline, variation=0, weights=None, guidance=None):
    policies = []
    required = []
    for index, case in enumerate(cases):
        scores = np.where(action_set, np.max(case.open, axis=0), np.inf)
        action = int(np.argmin(scores))
        policies.append(case.open_policy(action))
        if scores[action] >= target - 1e-7:
            required.append(index)
    if weights is None:
        weights = []
        for case in cases:
            if variation % 3 == 0:
                weights.append(np.full(case.scenario_count, 1 / case.scenario_count))
            elif variation % 3 == 1:
                weights.append(rng.dirichlet(np.full(case.scenario_count, .4)))
            else:
                weights.append(np.eye(case.scenario_count)[rng.randint(case.scenario_count)])
    if sum(cases[index].result_count for index in required) > np.sum(sensor_caps[sensor_set]):
        return None
    route_values = {}
    action_choices = {}
    case_prices = rng.uniform(.8, 1.2, len(cases)) if variation else np.ones(len(cases))
    for index in required:
        case = cases[index]
        route_values[index] = []
        action_choices[index] = []
        for _, second, loss, allowed in case.routes:
            cost = np.einsum('s,rsoa->roa', weights[index], loss)
            cost = np.where(allowed & action_set, cost, np.inf)
            route_values[index].append(cost.min(axis=-1).sum(axis=-1))
            action_choices[index].append(np.argmin(cost, axis=-1))
    first_nodes = [(index, result) for index in required for result in range(cases[index].result_count)]
    first_costs = []
    order_price = [0, .001, .004, .02, .1, 1][variation % 6]
    for index, result in first_nodes:
        case = cases[index]
        costs = np.full(len(sensor_caps), np.inf)
        for first in case.allowed_first[result]:
            if not sensor_set[first]:
                continue
            value = 0
            for indices in case.route_by_first[first]:
                value += min((route_values[index][route_index][result] for route_index in indices
                              if sensor_set[case.routes[route_index][1]]), default=np.inf)
            costs[first] = value * case_prices[index] + order_price * case.orders[first]
            if guidance is not None:
                marginal = guidance[0].get((index, result, first), 0.)
                costs[first] = -.1 * marginal + .01 * value + order_price * case.orders[first]
        if variation:
            costs += rng.uniform(-1, 1, len(costs)) * [0, .0002, .001, .003][variation % 4]
        first_costs.append(costs)
    chosen_first = assign(first_costs, sensor_caps * sensor_set)
    if chosen_first is None:
        return None
    remaining = sensor_caps - np.bincount(chosen_first, minlength=len(sensor_caps))
    second_nodes = []
    second_costs = []
    trees = {index: [None] * cases[index].result_count for index in required}
    for (index, result), first in zip(first_nodes, chosen_first):
        case = cases[index]
        trees[index][result] = (int(first), [])
        for sector, indices in enumerate(case.route_by_first[first]):
            costs = np.full(len(sensor_caps), np.inf)
            for route_index in indices:
                second = case.routes[route_index][1]
                if sensor_set[second]:
                    costs[second] = route_values[index][route_index][result] * case_prices[index]
                    if guidance is not None:
                        parent = guidance[0].get((index, result, first), 0.)
                        marginal = guidance[1].get((index, result, first, sector, second), 0.)
                        costs[second] = -.1 * marginal / max(parent, 1e-6) + .01 * costs[second]
            if variation:
                costs += rng.uniform(-1, 1, len(costs)) * [0, .0001, .0005, .001][variation % 4]
            second_costs.append(costs)
            second_nodes.append((index, result, first, sector, indices))
    chosen_second = assign(second_costs, remaining * sensor_set)
    if chosen_second is None:
        return None
    for (index, result, first, sector, indices), second in zip(second_nodes, chosen_second):
        route_index = next(route_index for route_index in indices if cases[index].routes[route_index][1] == second)
        trees[index][result][1].append((route_index, action_choices[index][route_index][result].copy()))
    for index in required:
        case = cases[index]
        sensor_usage = np.zeros(len(sensor_caps), dtype=int)
        action_usage = np.zeros(len(action_caps), dtype=int)
        losses = np.zeros(case.scenario_count)
        for result, (first, seconds) in enumerate(trees[index]):
            sensor_usage[first] += 1
            for route_index, chosen in seconds:
                _, second, loss, _ = case.routes[route_index]
                sensor_usage[second] += 1
                action_usage += np.bincount(chosen, minlength=len(action_caps))
                losses += loss[result, :, np.arange(len(chosen)), chosen].sum(axis=0)
        policies[index] = case.pack(trees[index], losses, sensor_usage, action_usage)
    return leaf_refine(cases, policies, action_set, action_caps, deadline, force=True)


def tree_relaxation(cases, sensor_set, action_set, sensor_caps, action_caps, target, deadline, return_model=False):
    resource_count = len(sensor_caps) + len(action_caps)
    scenario_offsets = np.cumsum([resource_count] + [case.scenario_count for case in cases])
    row_indices, col_indices, values = [], [], []
    equality_rows, equality_cols, equality_values, equality_rhs = [], [], [], []
    objective = [1.]
    first_variables = {}
    second_variables = {}
    for row in range(resource_count, scenario_offsets[-1]):
        row_indices.append(row)
        col_indices.append(0)
        values.append(-1.)

    def variable(resource, loss=None, case_index=None):
        column = len(objective)
        objective.append(0. if loss is None else 1e-4 * float(np.mean(loss)))
        row_indices.append(resource)
        col_indices.append(column)
        values.append(1.)
        if loss is not None:
            for scenario, value in enumerate(loss):
                row_indices.append(scenario_offsets[case_index] + scenario)
                col_indices.append(column)
                values.append(value)
        return column

    def equality(positive, negative=None, rhs=0.):
        row = len(equality_rhs)
        equality_rhs.append(rhs)
        equality_rows.extend([row] * len(positive))
        equality_cols.extend(positive)
        equality_values.extend([1.] * len(positive))
        if negative is not None:
            equality_rows.append(row)
            equality_cols.append(negative)
            equality_values.append(-1.)

    for index, case in enumerate(cases):
        open_best = np.min(np.max(case.open, axis=0)[action_set])
        if open_best < target - 1e-7:
            columns = [variable(len(sensor_caps) + action, case.open[:, action], index)
                       for action in np.flatnonzero(action_set & np.isfinite(case.open[0]))]
            equality(columns, rhs=1.)
            continue
        for result in range(case.result_count):
            first_columns = []
            for first in case.allowed_first[result]:
                if not sensor_set[first]:
                    continue
                first_column = variable(first)
                first_variables[index, result, first] = first_column
                first_columns.append(first_column)
                for sector, indices in enumerate(case.route_by_first[first]):
                    second_columns = []
                    for route_index in indices:
                        _, second, loss, allowed = case.routes[route_index]
                        if not sensor_set[second]:
                            continue
                        actions = np.flatnonzero(action_set & allowed)
                        if len(actions) == 0:
                            continue
                        second_column = variable(second)
                        second_variables[index, result, first, sector, second] = second_column
                        second_columns.append(second_column)
                        for outcome in range(case.orders[second]):
                            columns = [variable(len(sensor_caps) + action, loss[result, :, outcome, action], index)
                                       for action in actions]
                            equality(columns, second_column)
                    equality(second_columns, first_column)
            equality(first_columns, rhs=1.)
    variable_count = len(objective)
    matrix = coo_matrix((values, (row_indices, col_indices)),
                        shape=(scenario_offsets[-1], variable_count)).tocsc()
    equality_matrix = coo_matrix((equality_values, (equality_rows, equality_cols)),
                                 shape=(len(equality_rhs), variable_count)).tocsc()
    upper = np.r_[sensor_caps, action_caps, np.zeros(scenario_offsets[-1] - resource_count)]
    result = linprog(objective, A_ub=matrix, b_ub=upper, A_eq=equality_matrix,
                     b_eq=equality_rhs, bounds=(0, None), method='highs',
                     options={'time_limit': max(.01, min(2, deadline-time.monotonic()))})
    if not result.success:
        return None
    first = {key: max(0., result.x[column]) for key, column in first_variables.items()}
    second = {key: max(0., result.x[column]) for key, column in second_variables.items()}
    weights = []
    for index, case in enumerate(cases):
        dual = np.maximum(0., -result.ineqlin.marginals[scenario_offsets[index]:scenario_offsets[index + 1]])
        dual += 1e-4 / case.scenario_count
        weights.append(dual / np.sum(dual))
    answer = (float(result.x[0]), (first, second), weights)
    if return_model:
        model = (objective, matrix, upper, equality_matrix, equality_rhs,
                 first_variables, second_variables, result)
        return answer + (model,)
    return answer


def tree_dive(cases, sensor_set, action_set, sensor_caps, action_caps, rng, target, deadline):
    relaxed = tree_relaxation(cases, sensor_set, action_set, sensor_caps, action_caps,
                              target, deadline, return_model=True)
    if relaxed is None or relaxed[0] >= target - 1e-7:
        return None
    _, _, weights, model = relaxed
    objective, matrix, upper, equality_matrix, equality_rhs, first_variables, second_variables, initial = model
    first_columns = np.array(list(first_variables.values()), dtype=int)
    second_columns = np.array(list(second_variables.values()), dtype=int)
    bounds = np.zeros((len(objective), 2))
    bounds[:, 1] = 1.
    bounds[0, 1] = target
    stack = [(bounds, initial)]
    best = None
    explored = 0
    while stack and time.monotonic() < deadline - .1 and explored < 180:
        node_bounds, result = stack.pop()
        if result is None:
            result = linprog(objective, A_ub=matrix, b_ub=upper, A_eq=equality_matrix,
                             b_eq=equality_rhs, bounds=node_bounds, method='highs',
                             options={'time_limit': max(.01, min(.5, deadline-time.monotonic()))})
        explored += 1
        if not result.success or result.x[0] >= target - 1e-7:
            continue
        selected_column = None
        for columns in [first_columns, second_columns]:
            fractional = columns[(result.x[columns] > 1e-6) & (result.x[columns] < 1-1e-6)]
            if len(fractional):
                selected_column = int(fractional[np.argmax(result.x[fractional])])
                break
        if selected_column is None:
            guidance = ({key: max(0., result.x[column]) for key, column in first_variables.items()},
                        {key: max(0., result.x[column]) for key, column in second_variables.items()})
            policies = joint_construct(cases, sensor_set, action_set, sensor_caps, action_caps,
                                       rng, target, deadline, 0, weights, guidance)
            if policies is not None:
                value = max(policy[0] for policy in policies)
                if value < target:
                    best = policies
                    target = value
            continue
        for value in [0., 1.]:
            child_bounds = node_bounds.copy()
            child_bounds[selected_column] = value
            child_bounds[0, 1] = target
            stack.append((child_bounds, None))
    return best


def integer_refine(cases, policies, action_set, action_caps, deadline):
    policies = list(policies)
    for case_index in np.argsort([-policy[0] for policy in policies]):
        if time.monotonic() > deadline - .05:
            break
        if policies[case_index][0] < .98 * max(policy[0] for policy in policies):
            continue
        case = cases[case_index]
        policy = policies[case_index]
        if isinstance(policy[4], (int, np.integer)):
            continue
        capacity = action_caps - sum((other[3] for index, other in enumerate(policies)
                                     if index != case_index), np.zeros(len(action_caps), dtype=int))
        leaves = []
        for result_index, (_, seconds) in enumerate(policy[4]):
            for sector, (route_index, chosen) in enumerate(seconds):
                _, second, loss, allowed = case.routes[route_index]
                actions = np.flatnonzero(allowed & action_set & (capacity > 0))
                for outcome in range(len(chosen)):
                    leaves.append((result_index, sector, outcome, actions,
                                   loss[result_index, :, outcome, :][:, actions]))
        offsets = np.cumsum([0] + [len(leaf[3]) for leaf in leaves])
        count = int(offsets[-1])
        row_indices, col_indices, values = [], [], []
        equality_rows, equality_cols = [], []
        for leaf_index, (_, _, _, actions, loss) in enumerate(leaves):
            columns = np.arange(offsets[leaf_index], offsets[leaf_index + 1])
            row_indices.extend(actions)
            col_indices.extend(columns)
            values.extend(np.ones(len(columns)))
            equality_rows.extend([leaf_index] * len(columns))
            equality_cols.extend(columns)
            for scenario in range(case.scenario_count):
                row_indices.extend([len(capacity) + scenario] * len(columns))
                col_indices.extend(columns)
                values.extend(loss[scenario])
        for scenario in range(case.scenario_count):
            row_indices.append(len(capacity) + scenario)
            col_indices.append(count)
            values.append(-1.)
        matrix = coo_matrix((values, (row_indices, col_indices)),
                            shape=(len(capacity) + case.scenario_count, count + 1)).tocsc()
        equality = coo_matrix((np.ones(len(equality_rows)), (equality_rows, equality_cols)),
                              shape=(len(leaves), count + 1)).tocsc()
        upper = np.r_[capacity, np.zeros(case.scenario_count)]
        objective = np.zeros(count + 1)
        objective[-1] = 1.
        bounds = np.zeros((count + 1, 2))
        bounds[:, 1] = 1.
        bounds[-1, 1] = policy[0]
        queue = [(0., 0, bounds)]
        serial = 1
        explored = 0
        while queue and explored < 140 and time.monotonic() < deadline - .05:
            bound, _, node_bounds = heapq.heappop(queue)
            if bound >= policy[0] - 1e-9:
                continue
            node_bounds[-1, 1] = policy[0]
            result = linprog(objective, A_ub=matrix, b_ub=upper, A_eq=equality,
                             b_eq=np.ones(len(leaves)), bounds=node_bounds, method='highs',
                             options={'time_limit': max(.01, min(.3, deadline-time.monotonic()))})
            explored += 1
            if not result.success or result.fun >= policy[0] - 1e-9:
                continue
            fraction = np.minimum(result.x[:count], 1 - result.x[:count])
            column = int(np.argmax(fraction))
            if fraction[column] < 1e-7:
                tree = [(first, [(route_index, chosen.copy()) for route_index, chosen in seconds])
                        for first, seconds in policy[4]]
                loss = np.zeros(case.scenario_count)
                usage = np.zeros(len(capacity), dtype=int)
                for leaf_index, (result_index, sector, outcome, actions, losses) in enumerate(leaves):
                    selection = int(np.argmax(result.x[offsets[leaf_index]:offsets[leaf_index+1]]))
                    action = int(actions[selection])
                    tree[result_index][1][sector][1][outcome] = action
                    loss += losses[:, selection]
                    usage[action] += 1
                if np.all(usage <= capacity) and np.max(loss) < policy[0]:
                    policy = case.pack(tree, loss, policy[2], usage)
                    policies[case_index] = policy
                continue
            for value in [1., 0.]:
                child_bounds = node_bounds.copy()
                child_bounds[column] = value
                heapq.heappush(queue, (float(result.fun), serial, child_bounds))
                serial += 1
    return policies


def solve(manifest, cases, deadline):
    rng = np.random.RandomState(710)
    sensor_caps = np.array(list(manifest['sensor_usage_caps'].values()), dtype=int)
    action_caps = np.array(list(manifest['action_usage_caps'].values()), dtype=int)
    sensor_combinations = list(itertools.combinations(range(len(sensor_caps)), manifest['shared_sensor_count']))
    sensor_sets = np.zeros((len(sensor_combinations), len(sensor_caps)), dtype=bool)
    for index, combination in enumerate(sensor_combinations):
        sensor_sets[index, list(combination)] = True
    action_sets = np.array(list(itertools.combinations(range(len(action_caps)), manifest['shared_action_count'])), dtype=int)
    rank = design_rank(cases, sensor_sets, action_sets, sensor_caps, deadline - 10)
    ranking = np.argsort(rank, axis=None)
    best = None
    open_costs = np.array([np.max(case.open, axis=0) for case in cases])
    for combination in action_sets:
        action_set = np.zeros(len(action_caps), dtype=bool)
        action_set[combination] = True
        selected = assign(np.where(action_set, open_costs, np.inf), action_caps)
        if selected is None:
            continue
        policies = [case.open_policy(action) for case, action in zip(cases, selected)]
        value = max(policy[0] for policy in policies)
        if best is None or value < best[0]:
            best = (value, sensor_sets[0].copy(), action_set, policies)
    trial = 0
    initial_end = min(deadline - 10, time.monotonic() + 2.)
    while time.monotonic() < initial_end or best is None:
        if trial % 2 == 0:
            flat = int(ranking[(trial // 2) % len(ranking)])
        else:
            flat = int(rng.randint(rank.size))
        variation = trial % 12
        sensor_index, action_index = np.unravel_index(flat, rank.shape)
        sensor_set = sensor_sets[sensor_index]
        action_set = np.zeros(len(action_caps), dtype=bool)
        action_set[action_sets[action_index]] = True
        policies = construct(cases, sensor_set, action_set, sensor_caps, action_caps, rng, variation)
        if policies is not None:
            value = max(policy[0] for policy in policies)
            if best is None or value < best[0]:
                best = (value, sensor_set.copy(), action_set.copy(), policies)
        trial += 1
        if time.monotonic() >= deadline - 3:
            break
    promising = []
    evaluated = 0
    screening_end = time.monotonic() + .55 * max(0., deadline - 3 - time.monotonic())
    for flat in ranking:
        if time.monotonic() > deadline - 3:
            break
        if best is not None and rank.flat[flat] >= best[0] - 1e-7:
            break
        sensor_index, action_index = np.unravel_index(flat, rank.shape)
        sensor_set = sensor_sets[sensor_index]
        action_set = np.zeros(len(action_caps), dtype=bool)
        action_set[action_sets[action_index]] = True
        target = best[0] if best is not None else 1e6
        relaxed = tree_relaxation(cases, sensor_set, action_set, sensor_caps, action_caps, target, deadline - 2)
        evaluated += 1
        if relaxed is None or relaxed[0] >= target - 1e-7:
            continue
        bound, guidance, weights = relaxed
        promising.append((bound, int(flat), target, guidance, weights))
        for variation in [0, 1, 2, 6]:
            if time.monotonic() > deadline - 3:
                break
            policies = joint_construct(cases, sensor_set, action_set, sensor_caps, action_caps,
                                       rng, target, deadline - 2, variation, weights, guidance)
            if policies is not None:
                value = max(policy[0] for policy in policies)
                if best is None or value < best[0]:
                    best = (value, sensor_set.copy(), action_set.copy(), policies)
                if value <= bound + 1e-5:
                    break
        if len(promising) >= 15 and time.monotonic() >= screening_end:
            break
    promising.sort(key=lambda entry: entry[0])
    repetition = 0
    while promising and time.monotonic() < deadline - 9:
        bound, flat, target, guidance, weights = promising[repetition % min(12, len(promising))]
        repetition += 1
        if best is not None and bound >= best[0] - 1e-7:
            promising = [entry for entry in promising if entry[0] < best[0] - 1e-7]
            continue
        sensor_index, action_index = np.unravel_index(flat, rank.shape)
        sensor_set = sensor_sets[sensor_index]
        action_set = np.zeros(len(action_caps), dtype=bool)
        action_set[action_sets[action_index]] = True
        variation = repetition % 24
        policies = joint_construct(cases, sensor_set, action_set, sensor_caps, action_caps, rng,
                                   target, deadline - 2, variation, weights, guidance if repetition % 4 else None)
        if policies is not None:
            value = max(policy[0] for policy in policies)
            if best is None or value < best[0]:
                best = (value, sensor_set.copy(), action_set.copy(), policies)
    for entry in promising[:3]:
        if time.monotonic() > deadline - 4:
            break
        bound, flat = entry[:2]
        if bound >= best[0] - 1e-7:
            continue
        sensor_index, action_index = np.unravel_index(flat, rank.shape)
        sensor_set = sensor_sets[sensor_index]
        action_set = np.zeros(len(action_caps), dtype=bool)
        action_set[action_sets[action_index]] = True
        policies = tree_dive(cases, sensor_set, action_set, sensor_caps, action_caps, rng,
                             best[0], min(deadline - 3, time.monotonic() + 2.2))
        if policies is not None:
            value = max(policy[0] for policy in policies)
            if value < best[0]:
                best = (value, sensor_set.copy(), action_set.copy(), policies)
    if best is None:
        raise RuntimeError('No feasible policy found')
    _, sensor_set, action_set, policies = best
    policies = leaf_refine(cases, policies, action_set, action_caps, deadline)
    policies = integer_refine(cases, policies, action_set, action_caps, deadline)
    if os.environ.get('SOLVE_DEBUG'):
        print('trials', trial, 'relaxations', evaluated, 'promising', len(promising),
              'roundings', repetition, 'objective', max(policy[0] for policy in policies), flush=True)
    return {'fleet_id': manifest['fleet_id'],
            'shared_sensors': [name for name, used in zip(cases[0].sensor_ids, sensor_set) if used],
            'shared_actions': [name for name, used in zip(cases[0].action_ids, action_set) if used],
            'cases': [case.output(policy) for case, policy in zip(cases, policies)]}


def main():
    start = time.monotonic()
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    manifest, cases = load(arguments.input)
    result = solve(manifest, cases, start + float(os.environ.get('SOLVE_SECONDS', '54')))
    Path(arguments.output).write_text(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()
