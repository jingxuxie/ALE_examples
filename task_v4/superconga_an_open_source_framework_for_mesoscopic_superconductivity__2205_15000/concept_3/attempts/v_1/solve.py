import json
import os
import sys

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'
sys.dont_write_bytecode = True

import physics
from inference import InverseProblem, SearchTimeout


def reconstruct(query, model):
    problem = InverseProblem()
    try:
        for action in physics.uniform_actions(56)[:44]:
            site, energy = action['site'], action['energy_index']
            problem.add(site, energy, query(site, energy))
        problem.initial_fit()
        while len(problem.actions) < model['query_budget']:
            if problem.solved():
                site, energy = problem.design(1)[0]
                prediction = problem.table(problem.best[1], problem.best[2])[site * 41 + energy]
                value = query(site, energy)
                problem.add(site, energy, value)
                if abs(value - prediction) < 1e-6:
                    break
            else:
                for site, energy in problem.design(min(4, model['query_budget'] - len(problem.actions))):
                    problem.add(site, energy, query(site, energy))
            problem.refresh()
        round_index = 0
        while not problem.solved():
            problem.restart(round_index)
            round_index += 1
    except SearchTimeout:
        pass
    diagnostics = {'evaluations': problem.evaluations,
                   'residual_sum_squares': problem.best[0] if problem.best else None}
    return problem.scene(), diagnostics


def main():
    metadata = json.loads(sys.stdin.readline())
    if metadata.get('protocol') != 'ldos-jsonl-v1':
        raise ValueError('unsupported protocol')

    def query(site, energy):
        print(json.dumps({'type': 'query', 'site': int(site), 'energy_index': int(energy)}), flush=True)
        observation = json.loads(sys.stdin.readline())
        if observation.get('type') != 'observation':
            raise ValueError('expected observation')
        return float(observation['value'])

    scene, diagnostics = reconstruct(query, metadata['model'])
    print(json.dumps({'type': 'final', 'estimate': scene}, allow_nan=False), flush=True)
    print(json.dumps(diagnostics, allow_nan=False), file=sys.stderr)


if __name__ == '__main__':
    main()
