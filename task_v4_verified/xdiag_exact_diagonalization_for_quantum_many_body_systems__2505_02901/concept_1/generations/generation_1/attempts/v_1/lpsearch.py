import time

import numpy as np
from scipy.optimize import linear_sum_assignment, linprog
from scipy.sparse import coo_matrix

from fleet import objective, policy_statistics, route_array


class ForestModel:
    def __init__(self, manifest, cases, sensor_set, action_set, ceiling):
        self.manifest = manifest
        self.cases = cases
        self.sensor_set = tuple(sensor_set)
        self.action_set = tuple(action_set)
        sensor_rows = {name: index for index, name in enumerate(sensor_set)}
        action_rows = {name: len(sensor_rows) + index for index, name in enumerate(action_set)}
        upper_rhs = [manifest['sensor_usage_caps'][name] for name in sensor_set]
        upper_rhs += [manifest['action_usage_caps'][name] for name in action_set]
        upper_rows, upper_cols, upper_vals = [], [], []
        equal_rows, equal_cols, equal_vals, equal_rhs = [], [], [], []
        self.metadata = [None]
        self.loss_vectors = [None]
        self.levels = [9]
        self.templates = []
        self.case_loss_rows = []
        self.open_floor = 0.0
        self.valid = True

        def variable(metadata, level):
            index = len(self.metadata)
            self.metadata.append(metadata)
            self.loss_vectors.append(None)
            self.levels.append(level)
            return index

        def equality(entries, rhs=0.0):
            row = len(equal_rhs)
            equal_rhs.append(rhs)
            for column, value in entries:
                equal_rows.append(row)
                equal_cols.append(column)
                equal_vals.append(value)

        def upper(row, column, value):
            if value:
                upper_rows.append(row)
                upper_cols.append(column)
                upper_vals.append(value)

        for case_index, data in enumerate(cases):
            case = data['configuration']
            feasible_open = [action for action in case['actions']
                             if action['action_id'] in action_set and action['cost'] <= case['total_budget']
                             and upper_rhs[action_rows[action['action_id']]] >= 1]
            if feasible_open:
                best_open = min(feasible_open, key=lambda action: float(np.max(
                    data['priors'] @ data['table']['open'][:, data['action_index'][action['action_id']]])))
                open_loss = float(np.max(data['priors'] @ data['table']['open'][
                    :, data['action_index'][best_open['action_id']]]))
                if open_loss < ceiling - 1e-8:
                    self.open_floor = max(self.open_floor, open_loss)
                    loss_rows = list(range(len(upper_rhs), len(upper_rhs) + len(data['priors'])))
                    self.case_loss_rows.append(loss_rows)
                    upper_rhs.extend([0.0] * len(loss_rows))
                    for row in loss_rows:
                        upper(row, 0, -1.0)
                    options = []
                    for entry in feasible_open:
                        action = entry['action_id']
                        losses = data['priors'] @ data['table']['open'][:, data['action_index'][action]]
                        if losses.max() >= ceiling - 1e-8:
                            continue
                        column = variable((case_index, action), 2)
                        self.loss_vectors[column] = losses
                        upper(action_rows[action], column, 1.0)
                        for row, loss in zip(loss_rows, losses):
                            upper(row, column, loss)
                        options.append((column, action))
                    equality([(column, 1.0) for column, action in options], 1.0)
                    self.templates.append({'case_id': case['case_id'], 'open_options': options})
                    continue
            probe = case['calibration_test']
            sensors = {entry['sensor_id']: entry for entry in case['sensors']}
            action_costs = {entry['action_id']: entry['cost'] for entry in case['actions']}
            loss_rows = list(range(len(upper_rhs), len(upper_rhs) + len(data['priors'])))
            self.case_loss_rows.append(loss_rows)
            upper_rhs.extend([0.0] * len(loss_rows))
            for row in loss_rows:
                upper(row, 0, -1.0)
            branches = []
            for result_index, result in enumerate(probe['results']):
                first_columns = []
                first_options = []
                for first in probe['allowed_first_sensor_ids'][result]:
                    if first not in sensor_rows:
                        continue
                    sector_options = []
                    for sector, allowed in enumerate(probe['allowed_second_sensor_ids_by_sector'][first]):
                        seconds = []
                        for second in allowed:
                            if second not in sensor_rows:
                                continue
                            available = [action for action in action_set
                                         if action_costs[action] + probe['cost'] + sensors[first]['cost']
                                         + sensors[second]['cost'] <= case['total_budget']]
                            if available:
                                seconds.append((second, available))
                        sector_options.append(seconds)
                    if not all(sector_options):
                        continue
                    first_column = variable((case_index, result_index, first), 0)
                    upper(sensor_rows[first], first_column, 1.0)
                    first_columns.append((first_column, 1.0))
                    second_options = []
                    for sector, seconds in enumerate(sector_options):
                        second_columns = [(first_column, -1.0)]
                        second_items = []
                        for second, available in seconds:
                            second_column = variable((case_index, result_index, first, sector, second), 1)
                            upper(sensor_rows[second], second_column, 1.0)
                            second_columns.append((second_column, 1.0))
                            route = route_array(data, first, sector, second)
                            losses = np.einsum('sq,q,qla->sla', data['priors'],
                                               data['likelihood'][result_index], route)
                            action_options = []
                            for outcome in range(sensors[second]['order']):
                                action_columns = [(second_column, -1.0)]
                                action_items = []
                                for action in available:
                                    action_column = variable((case_index, result_index, first, sector,
                                                              second, outcome, action), 2)
                                    self.loss_vectors[action_column] = losses[:, outcome, data['action_index'][action]].copy()
                                    upper(action_rows[action], action_column, 1.0)
                                    for scenario, row in enumerate(loss_rows):
                                        upper(row, action_column,
                                              losses[scenario, outcome, data['action_index'][action]])
                                    action_columns.append((action_column, 1.0))
                                    action_items.append((action_column, action))
                                equality(action_columns)
                                action_options.append(action_items)
                            second_items.append((second_column, second, action_options))
                        equality(second_columns)
                        second_options.append(second_items)
                    first_options.append((first_column, first, second_options))
                if not first_columns:
                    self.valid = False
                    return
                equality(first_columns, 1.0)
                branches.append(first_options)
            self.templates.append(branches)
        variable_count = len(self.metadata)
        self.upper = coo_matrix((upper_vals, (upper_rows, upper_cols)),
                                shape=(len(upper_rhs), variable_count)).tocsc()
        self.equal = coo_matrix((equal_vals, (equal_rows, equal_cols)),
                                shape=(len(equal_rhs), variable_count)).tocsc()
        self.upper_rhs = np.asarray(upper_rhs, dtype=float)
        self.equal_rhs = np.asarray(equal_rhs, dtype=float)
        self.cost = np.zeros(variable_count)
        self.cost[0] = 1.0
        self.bounds = np.zeros((variable_count, 2))
        self.bounds[:, 1] = 1.0
        self.bounds[0] = [self.open_floor, ceiling - 1e-9]
        self.levels = np.asarray(self.levels)

    def relaxation(self, bounds=None, deadline=None):
        if not self.valid:
            return None
        if bounds is None:
            bounds = self.bounds
        if bounds[0, 0] > bounds[0, 1]:
            return None
        remaining = 10.0 if deadline is None else deadline - time.monotonic()
        if remaining < 0.005:
            return None
        result = linprog(self.cost, A_ub=self.upper, b_ub=self.upper_rhs,
                         A_eq=self.equal, b_eq=self.equal_rhs, bounds=bounds,
                         method='highs', options={'time_limit': remaining,
                                                  'dual_feasibility_tolerance': 1e-8,
                                                  'primal_feasibility_tolerance': 1e-8})
        if result.success:
            return result
        return None

    def decode(self, values, random=None, improve=False):
        def choose(options):
            if random is None:
                return max(options, key=lambda entry: values[entry[0]])
            weights = np.maximum(0.0, [values[entry[0]] for entry in options])
            total = weights.sum()
            if total < 1e-7 or weights.max() > total - 1e-7:
                return options[int(np.argmax(weights))]
            threshold = random.random_sample() * total
            return options[min(len(options) - 1, int(np.searchsorted(np.cumsum(weights), threshold)))]

        policies = []
        leaves = []
        for case_index, (data, template) in enumerate(zip(self.cases, self.templates)):
            if isinstance(template, dict):
                column, action = max(template['open_options'], key=lambda entry: values[entry[0]])
                policy = {'case_id': template['case_id'], 'root': 'open', 'action': action}
                policies.append(policy)
                leaves.append([case_index, policy, 'action', template['open_options'], column])
                continue
            branches = []
            for first_options in template:
                first_column, first, second_options = choose(first_options)
                seconds = []
                for second_items in second_options:
                    second_column, second, action_options = choose(second_items)
                    chosen_actions = [max(items, key=lambda entry: values[entry[0]]) for items in action_options]
                    actions = [entry[1] for entry in chosen_actions]
                    for outcome, (column, action) in enumerate(chosen_actions):
                        leaves.append([case_index, actions, outcome, action_options[outcome], column])
                    seconds.append({'second_sensor': second, 'actions': actions})
                branches.append({'first_sensor': first, 'seconds': seconds})
            policies.append({'case_id': data['configuration']['case_id'], 'root': 'probe', 'branches': branches})
        sensor_used = dict.fromkeys(self.manifest['sensor_usage_caps'], 0)
        action_used = dict.fromkeys(self.manifest['action_usage_caps'], 0)
        case_losses = []
        for data, policy in zip(self.cases, policies):
            losses, sensor_counts, action_counts = policy_statistics(data, policy)
            case_losses.append(losses)
            for name, count in sensor_counts.items():
                sensor_used[name] += count
            for name, count in action_counts.items():
                action_used[name] += count
        if any(count > self.manifest['sensor_usage_caps'][name] for name, count in sensor_used.items()):
            return None
        caps = self.manifest['action_usage_caps']
        while any(count > caps[name] for name, count in action_used.items()):
            move = None
            for leaf in leaves:
                case_index, actions, outcome, options, old_column = leaf
                old_action = actions[outcome]
                if action_used[old_action] <= caps[old_action]:
                    continue
                old_loss = case_losses[case_index]
                for column, action in options:
                    if action_used[action] >= caps[action]:
                        continue
                    losses = old_loss + self.loss_vectors[column] - self.loss_vectors[old_column]
                    score = float(losses.max() - old_loss.max())
                    if move is None or score < move[0]:
                        move = score, leaf, column, action, losses
            if move is None:
                return None
            score, leaf, column, action, losses = move
            case_index, actions, outcome, options, old_column = leaf
            action_used[actions[outcome]] -= 1
            action_used[action] += 1
            actions[outcome] = action
            leaf[4] = column
            case_losses[case_index] = losses
        if improve:
            for sweep in range(2):
                changed = False
                for leaf in leaves:
                    case_index, actions, outcome, options, old_column = leaf
                    old_loss = case_losses[case_index]
                    old_score = float(old_loss.max() + 1e-5 * old_loss.mean())
                    best = None
                    for column, action in options:
                        if column == old_column or action_used[action] >= caps[action]:
                            continue
                        losses = old_loss + self.loss_vectors[column] - self.loss_vectors[old_column]
                        score = float(losses.max() + 1e-5 * losses.mean())
                        if score < old_score - 1e-10 and (best is None or score < best[0]):
                            best = score, column, action, losses
                    if best is not None:
                        score, column, action, losses = best
                        action_used[actions[outcome]] -= 1
                        action_used[action] += 1
                        actions[outcome] = action
                        leaf[4] = column
                        case_losses[case_index] = losses
                        changed = True
                if not changed:
                    break
        return {'fleet_id': self.manifest['fleet_id'], 'shared_sensors': list(self.sensor_set),
                'shared_actions': list(self.action_set), 'cases': policies}

    def rounded_structure(self, root, random, attempt=0, first_only=False, second_only=False):
        remaining = self.manifest['sensor_usage_caps'].copy()
        first_groups = []
        second_scores = {}
        first_scores = {}
        values = root.x
        temperature = (0.012, 0.003, 0.035, 0.001)[attempt % 4]
        for case_index, template in enumerate(self.templates):
            if isinstance(template, dict):
                continue
            weights = np.maximum(0.0, -root.ineqlin.marginals[self.case_loss_rows[case_index]])
            if weights.sum() < 1e-7:
                weights = np.ones(len(weights))
            weights = weights / weights.sum()
            for first_options in template:
                first_groups.append(first_options)
                for first_column, first, sector_options in first_options:
                    first_score = 0.0
                    for second_items in sector_options:
                        sector_best = float('inf')
                        for second_column, second, leaf_options in second_items:
                            score = sum(min(float(weights @ self.loss_vectors[column])
                                            for column, action in actions) for actions in leaf_options)
                            second_scores[second_column] = score
                            sector_best = min(sector_best, score)
                        first_score += sector_best
                    first_scores[first_column] = first_score

        def assignment(groups, scores):
            if not groups:
                return []
            slots = [name for name in self.sensor_set for count in range(min(len(groups), remaining[name]))]
            if len(slots) < len(groups):
                return None
            slot_map = {name: np.flatnonzero(np.array(slots) == name) for name in self.sensor_set}
            costs = np.full((len(groups), len(slots)), 1e6)
            for group_index, options in enumerate(groups):
                total = sum(max(0.0, values[entry[0]]) for entry in options)
                for entry in options:
                    column, name = entry[:2]
                    probability = max(0.0, values[column]) / max(total, 1e-8)
                    value = scores[column] - temperature * np.log(probability + 1e-5)
                    if attempt:
                        value += random.uniform(-temperature, temperature)
                    costs[group_index, slot_map[name]] = value
            row_indices, column_indices = linear_sum_assignment(costs)
            if np.any(costs[row_indices, column_indices] > 1e5):
                return None
            choices = []
            for group_index, column in zip(row_indices, column_indices):
                name = slots[column]
                entry = next(entry for entry in groups[group_index] if entry[1] == name)
                choices.append(entry)
                remaining[name] -= 1
            return choices

        if second_only:
            first_choices = [max(options, key=lambda entry: values[entry[0]]) for options in first_groups]
            for column, name, sectors in first_choices:
                remaining[name] -= 1
        else:
            first_choices = assignment(first_groups, first_scores)
        if first_choices is None:
            return None
        if first_only:
            bounds = self.bounds.copy()
            bounds[self.levels == 0] = 0.0
            for entry in first_choices:
                bounds[entry[0]] = 1.0
            return bounds
        second_groups = [options for column, name, sectors in first_choices for options in sectors]
        second_choices = assignment(second_groups, second_scores)
        if second_choices is None:
            return None
        bounds = self.bounds.copy()
        bounds[self.levels < 2] = 0.0
        for entry in first_choices + second_choices:
            bounds[entry[0]] = 1.0
        return bounds

    def search(self, ceiling, deadline, root=None, max_nodes=500, initial_bounds=None):
        if root is None:
            root = self.relaxation(deadline=deadline)
        if root is None:
            return None, ceiling, 0
        stack = [(self.bounds.copy() if initial_bounds is None else initial_bounds.copy(), root, 0)]
        best, nodes = None, 0
        while stack and nodes < max_nodes and time.monotonic() < deadline - 0.01:
            bounds, result, depth = stack.pop()
            bounds[0, 1] = min(bounds[0, 1], ceiling - 1e-8)
            if result is None:
                result = self.relaxation(bounds, deadline)
                nodes += 1
            if result is None or result.fun >= ceiling - 1e-8:
                continue
            rounded = self.decode(result.x, improve=depth < 2)
            if rounded is not None:
                value = objective(self.cases, rounded['cases'])
                if value < ceiling - 1e-8:
                    ceiling, best = value, rounded
                    if result.fun >= ceiling - 1e-7:
                        continue
            fractionality = np.minimum(result.x, 1.0 - result.x)
            fractional = np.flatnonzero((fractionality > 1e-6) & (self.levels < 9))
            if not len(fractional):
                continue
            minimum_level = self.levels[fractional].min()
            candidates = fractional[self.levels[fractional] == minimum_level]
            chosen = candidates[np.argmax(fractionality[candidates])]
            prefer_one = result.x[chosen] >= 0.45
            alternate = bounds.copy()
            preferred = bounds.copy()
            alternate[chosen] = [0.0, 0.0] if prefer_one else [1.0, 1.0]
            preferred[chosen] = [1.0, 1.0] if prefer_one else [0.0, 0.0]
            stack.append((alternate, None, depth + 1))
            stack.append((preferred, None, depth + 1))
        return best, ceiling, nodes
