import argparse
import time
from adapt import *
from turnover import canonical


def search(instance, source='local', seed=0, rounds=1000):
    random = np.random.default_rng(seed)
    if source == 'best':
        options = []
        for path in Path('.').glob(instance['id'] + '*partial.json'):
            circuit = json.loads(path.read_text())
            if len(circuit['layers']) > instance['budgets']['max_depth']:
                continue
            trial_edges, trial_parameters = unpack(circuit)
            if len(trial_edges) > instance['budgets']['max_gates']:
                continue
            error = np.linalg.norm(Fit(instance, trial_edges).evaluate(trial_parameters.ravel())[0])
            options.append((error, path.name, circuit))
        _, path, circuit = min(options, key=lambda item: item[0])
        print('SOURCE', path, flush=True)
    else:
        circuit = json.loads(Path(instance['id'] + '_' + source + '.json').read_text())
    edges, parameters = unpack(circuit)
    maximum = instance['budgets']['max_gates']
    depth_limit = instance['budgets']['max_depth']
    started = time.monotonic()
    def depth_of(topology):
        return len(schedule([(first, second, 0, 0) for first, second in topology], instance['n_modes']))
    def objective(error, topology):
        return error + 0.02 * max(0, depth_of(topology) - depth_limit)
    while len(edges) > maximum:
        choices = []
        for removed in range(len(edges)):
            trial_edges = edges[:removed] + edges[removed + 1:]
            trial_parameters = np.delete(parameters, removed, axis=0)
            solver = Fit(instance, trial_edges)
            trial_parameters, error = solver.solve(trial_parameters, evaluations=90)
            choices.append((objective(error, trial_edges), error, trial_edges, trial_parameters))
        score, error, edges, parameters = min(choices, key=lambda item: item[0])
        print('TRIM', instance['id'], len(edges), depth_of(edges), error, 'time', time.monotonic() - started, flush=True)
    solver = Fit(instance, edges)
    parameters, error = solver.solve(parameters, evaluations=250)
    current = objective(error, edges)
    best = (current, error, list(edges), parameters.copy())
    stalled = 0
    tabu = []
    for iteration in range(rounds):
        accepted = False
        alternatives = []
        previous_signature = canonical([(first, second, 0, 0) for first, second in edges], instance['n_modes'])
        tabu.append(previous_signature)
        tabu = tabu[-80:]
        seen = {previous_signature}
        priorities = np.linalg.norm(parameters, axis=1) * random.uniform(0.5, 1.5, size=len(edges))
        for removed in np.argsort(priorities):
            reduced_edges = edges[:removed] + edges[removed + 1:]
            reduced_parameters = np.delete(parameters, removed, axis=0)
            solver = Fit(instance, reduced_edges)
            reduced_parameters, deleted_error = solver.solve(reduced_parameters, evaluations=70, tolerance=1e-10)
            proposals = insertion_candidates(instance, reduced_edges, reduced_parameters)
            attempts = 0
            for gain, position, edge in proposals:
                trial_edges = reduced_edges[:position] + [edge] + reduced_edges[position:]
                if trial_edges == edges or depth_of(trial_edges) > max(depth_limit + 1, depth_of(edges)):
                    continue
                signature = canonical([(first, second, 0, 0) for first, second in trial_edges], instance['n_modes'])
                if signature in seen or signature in tabu:
                    continue
                seen.add(signature)
                trial_parameters = np.insert(reduced_parameters, position, [0.0, 0.0], axis=0)
                solver = Fit(instance, trial_edges)
                trial_parameters, trial_error = solver.solve(trial_parameters, evaluations=90, tolerance=1e-11)
                score = objective(trial_error, trial_edges)
                alternatives.append((score, trial_error, trial_edges, trial_parameters))
                attempts += 1
                if score < current - max(1e-10, 1e-5 * current):
                    current, error, edges, parameters = score, trial_error, trial_edges, trial_parameters
                    accepted = True
                    break
                if attempts >= 6:
                    break
            if accepted:
                break
        if not accepted:
            stalled += 1
            if not alternatives:
                break
            alternatives.sort(key=lambda item: item[0])
            distinct = [entry for entry in alternatives if entry[0] > current + max(1e-9, current * 1e-4)]
            alternatives = distinct or alternatives
            choice = random.integers(min(5, len(alternatives)))
            current, error, edges, parameters = alternatives[choice]
        else:
            stalled = 0
        if current < best[0]:
            best = (current, error, list(edges), parameters.copy())
            Path(instance['id'] + f'_mutate_{source}_{seed}_partial.json').write_text(json.dumps(pack(instance, edges, parameters)))
        print('STEP', instance['id'], iteration, 'error', error, 'best', best[1], 'depth', depth_of(edges),
              'accepted', accepted, 'time', round(time.monotonic() - started, 1), flush=True)
        if error < 1e-8 and depth_of(edges) <= depth_limit:
            parameters, error = Fit(instance, edges).solve(parameters, evaluations=250)
            Path(instance['id'] + '_mutate.json').write_text(json.dumps(pack(instance, edges, parameters)))
            print('SOLVED', instance['id'], len(edges), depth_of(edges), error, flush=True)
            return
        if stalled >= 8:
            current, error, edges, parameters = best[0], best[1], list(best[2]), best[3].copy()
            parameters += random.normal(scale=0.05, size=parameters.shape)
            parameters, error = Fit(instance, edges).solve(parameters, evaluations=200)
            current = objective(error, edges)
            stalled = 0
    print('FAILED', instance['id'], best[1], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--source', default='local')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--rounds', type=int, default=1000)
    arguments = parser.parse_args()
    search(INSTANCES[arguments.index], arguments.source, arguments.seed, arguments.rounds)
