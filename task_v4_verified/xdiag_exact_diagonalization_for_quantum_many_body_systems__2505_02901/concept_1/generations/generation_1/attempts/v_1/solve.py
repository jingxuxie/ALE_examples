import os
import time

START = time.monotonic()
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import argparse
import heapq
import json
import sys
from pathlib import Path

import numpy as np

from designs import capacity_possible, rank_designs, strengthen_bounds
from fleet import load_fleet, objective
from frozen import solve as baseline_solve
from lpsearch import ForestModel


def solve(manifest, cases, deadline, publish=None, verbose=False):
    best = baseline_solve(manifest, cases)
    best_value = objective(cases, best['cases'])
    if publish:
        publish(best)

    def log(*values):
        if verbose:
            print(round(time.monotonic() - START, 3), *values, file=sys.stderr, flush=True)

    def accept(policy):
        nonlocal best, best_value
        if policy is None:
            return False
        value = objective(cases, policy['cases'])
        if value < best_value - 1e-8:
            best, best_value = policy, value
            if publish:
                publish(best)
            log('improved', best_value, best['shared_sensors'], best['shared_actions'])
            return True
        return False

    log('baseline', best_value)
    if time.monotonic() < deadline - 3:
        accept(baseline_solve(manifest, cases, trials=160, seed=2710, diversify=True))
    if time.monotonic() >= deadline - 1:
        return best
    sensor_sets, action_sets, lower_bounds, open_losses = rank_designs(
        manifest, cases, best_value, min(deadline - 3, time.monotonic() + 10))
    log('ranked', len(sensor_sets), len(action_sets), 'bound',
        float(lower_bounds.min()) if lower_bounds.size else None)
    if not lower_bounds.size:
        return best
    strengthen_bounds(manifest, cases, sensor_sets, action_sets, lower_bounds, best_value,
                      min(deadline - 2, time.monotonic() + 7))
    log('strengthened', float(lower_bounds.min()))
    ordering = np.argsort(lower_bounds, axis=None)
    pending = []
    counter = 0
    models = 0
    nodes = 0
    random = np.random.RandomState(27391)
    for flat_index in ordering:
        now = time.monotonic()
        if now >= deadline - 1:
            break
        sensor_index, action_index = np.unravel_index(flat_index, lower_bounds.shape)
        lower_bound = lower_bounds[sensor_index, action_index]
        if lower_bound >= best_value - 1e-8:
            break
        sensors, actions = sensor_sets[sensor_index], action_sets[action_index]
        if not capacity_possible(manifest, cases, sensors, best_value, open_losses[:, action_index]):
            continue
        model = ForestModel(manifest, cases, sensors, actions, best_value)
        root = model.relaxation(deadline=min(deadline, time.monotonic() + 1.5))
        models += 1
        if root is None or root.fun >= best_value - 1e-8:
            continue
        rounded = model.decode(root.x, improve=True)
        accept(rounded)
        if root.fun < best_value - 1e-7:
            for sample in range(2):
                if time.monotonic() >= deadline - 0.05:
                    break
                accept(model.decode(root.x, random, improve=True))
        if root.fun < best_value - 1e-7:
            for attempt in range(3):
                if time.monotonic() >= deadline - 0.1:
                    break
                first_bounds = model.rounded_structure(root, random, attempt, first_only=True)
                if first_bounds is None:
                    continue
                first_bounds[0, 1] = best_value - 1e-8
                first_root = model.relaxation(first_bounds, min(deadline, time.monotonic() + 0.5))
                if first_root is None:
                    continue
                accept(model.decode(first_root.x, improve=True))
                fixed_bounds = model.rounded_structure(first_root, random, attempt, second_only=True)
                if fixed_bounds is None:
                    continue
                fixed_bounds[0, 1] = best_value - 1e-8
                fixed_root = model.relaxation(fixed_bounds, min(deadline, time.monotonic() + 0.5))
                if fixed_root is not None:
                    accept(model.decode(fixed_root.x, improve=True))
                    if fixed_root.fun < best_value - 1e-7:
                        candidate, value, node_count = model.search(
                            best_value, min(deadline, time.monotonic() + 0.12), fixed_root,
                            max_nodes=12, initial_bounds=fixed_bounds)
                        nodes += node_count
                        accept(candidate)
        if root.fun >= best_value - 1e-8:
            continue
        seconds = min(0.35 if models > 5 else 0.8, max(0.01, (deadline - time.monotonic()) / 5))
        result, value, node_count = model.search(best_value, min(deadline, time.monotonic() + seconds), root, 60)
        nodes += node_count
        accept(result)
        if root.fun < best_value - 1e-6:
            counter += 1
            heapq.heappush(pending, (root.fun, counter, sensors, actions))
        if pending and (models % 12 == 0 or time.monotonic() > deadline - 8):
            bound, count, retry_sensors, retry_actions = heapq.heappop(pending)
            if bound < best_value - 1e-6 and time.monotonic() < deadline - 0.1:
                retry = ForestModel(manifest, cases, retry_sensors, retry_actions, best_value)
                result, value, node_count = retry.search(best_value, min(deadline, time.monotonic() + 1.3), max_nodes=180)
                nodes += node_count
                accept(result)
    log('searched', models, 'models', nodes, 'nodes', len(pending), 'pending')
    while pending and time.monotonic() < deadline - 0.1:
        bound, count, sensors, actions = heapq.heappop(pending)
        if bound >= best_value - 1e-6:
            continue
        model = ForestModel(manifest, cases, sensors, actions, best_value)
        result, value, node_count = model.search(best_value, min(deadline, time.monotonic() + 2), max_nodes=400)
        nodes += node_count
        accept(result)
    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--seconds', type=float, default=54.0)
    parser.add_argument('--verbose', action='store_true')
    arguments = parser.parse_args()
    manifest, cases = load_fleet(arguments.input)
    output = Path(arguments.output)

    def publish(policy):
        temporary = output.with_name(output.name + '.partial')
        temporary.write_text(json.dumps(policy, allow_nan=False))
        os.replace(temporary, output)

    best = solve(manifest, cases, START + arguments.seconds, publish, arguments.verbose)
    publish(best)


if __name__ == '__main__':
    main()
