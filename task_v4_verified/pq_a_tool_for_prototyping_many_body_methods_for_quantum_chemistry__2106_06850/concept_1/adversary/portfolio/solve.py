import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'participant/workspace'))

from contract import validate
from graph import Graph
from optimize import coordinate_search, feasible_edges, joint_lp_search, weighted_choices
from schedule import Scheduler, baseline_module, root_order


def fingerprint(case):
    return hashlib.sha256(json.dumps(case, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def search(case, seconds=20, trials=32, seed=0, delayed=False, exhaust_trials=False):
    started = time.monotonic()
    graph = Graph(case, delayed=delayed) if delayed else Graph(case)
    graph_seconds = time.monotonic() - started
    allowed = feasible_edges(graph)
    best_plan = baseline_module().solve(case)
    best_result = validate(case, best_plan)
    candidates = [{'method': 'exact_independent_baseline', **best_result}]
    best_label = candidates[0]['method']
    current = weighted_choices(graph, allowed)
    assignments = [('independent_tree_CSE', current)]
    global_choices, bound = joint_lp_search(graph, allowed, current, seconds=max(0.1, seconds * 0.5))
    if bound['root_certificate']:
        bound['root_certificate']['delayed_summation'] = delayed
    assignments.append(('global_LP_branch_bound', global_choices))
    for exponent in (0.35, 0.7, 1.0, 1.5, 2.0):
        weights = {node_id: max(1, len(node.roots)) ** -exponent for node_id, node in enumerate(graph.nodes)}
        chosen = weighted_choices(graph, allowed, weights=weights)
        chosen = coordinate_search(graph, allowed, chosen, seed=seed, sweeps=6)
        assignments.append(('amortized_' + str(exponent), chosen))
    for trial in range(trials):
        if trial >= len(assignments) and time.monotonic() - started > seconds:
            break
        if trial < len(assignments):
            label, chosen = assignments[trial]
        else:
            weights = {node_id: max(1, len(node.roots)) ** -(0.2 + trial % 8 / 4) for node_id, node in enumerate(graph.nodes)}
            chosen = weighted_choices(graph, allowed, weights=weights, seed=seed + trial, noise=0.5 + (trial % 5) / 2)
            chosen = coordinate_search(graph, allowed, chosen, seed=seed + trial, sweeps=4, group_size=1 + trial % 5)
            label = 'multiroot_' + str(trial)
        for mode in ('original', 'large', 'small', 'overlap', 'random'):
            order = root_order(graph, chosen, mode, seed=seed + trial)
            for eviction in ('value', 'belady', 'frequency', 'size'):
                trial_started = time.monotonic()
                metadata = {'method': label, 'order': mode, 'eviction': eviction,
                            'seed': seed + trial, 'relaxed_flops': graph.cost(chosen)}
                try:
                    plan, scheduling = Scheduler(graph, chosen, order, eviction=eviction).run()
                    validation_started = time.monotonic()
                    result = validate(case, plan)
                    metadata.update(result)
                    metadata.update(scheduling)
                    metadata['validation_seconds'] = time.monotonic() - validation_started
                    if (result['flops'], result['peak_elements']) < (best_result['flops'], best_result['peak_elements']):
                        best_plan, best_result = plan, result
                        best_label = label + '/' + mode + '/' + eviction
                        metadata['new_best'] = True
                except Exception as error:
                    metadata.update({'valid': False, 'reason': str(error)})
                metadata['seconds'] = time.monotonic() - trial_started
                candidates.append(metadata)
        if not exhaust_trials and trial >= 6 and best_result['flops'] <= bound['joint_lower_flops'] + 0.01:
            break
    return best_plan, {'case_sha256': fingerprint(case), 'graph': graph.statistics(),
                       'delayed_summation': delayed, 'graph_seconds': graph_seconds,
                       'generation_seconds': time.monotonic() - started, 'optimization': bound,
                       'winner': best_label, 'result': best_result, 'candidates': candidates,
                       'validated_candidates': sum(candidate['valid'] for candidate in candidates),
                       'invalid_candidates': sum(not candidate['valid'] for candidate in candidates)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--seconds', type=float, default=20)
    parser.add_argument('--trials', type=int, default=32)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--delayed', action='store_true')
    parser.add_argument('--exhaust-trials', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    case = json.loads(args.input.read_text())
    plan, report = search(case, args.seconds, args.trials, args.seed, args.delayed, args.exhaust_trials)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key not in {'candidates', 'optimization'}}), flush=True)


if __name__ == '__main__':
    main()
