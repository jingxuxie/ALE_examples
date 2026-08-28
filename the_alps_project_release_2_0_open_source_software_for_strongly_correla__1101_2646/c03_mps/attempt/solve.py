import os

for variable in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS']:
    os.environ[variable] = '1'

import argparse
import json
import multiprocessing
import resource
import time
import traceback
from pathlib import Path

from dmrg import correlations, make_model, product_state, run_dmrg, shifted_state


def sector_worker(case, sector, deadline, measure, verbose, connection):
    try:
        model = make_model(case)
        maximum_bond = 384 if model.family == 'bose_hubbard' else 512
        schedule = [16, 32] + list(range(64, maximum_bond + 1, 32)) + [maximum_bond] * 5
        initial = None
        warmup_history = []
        if model.family != 'bose_hubbard' and deadline - time.monotonic() > 60:
            best_energy = float('inf')
            trial_deadline = time.monotonic() + 0.15 * (deadline - time.monotonic())
            for orientation in [1, -1]:
                trial_energy, trial_state, trial_history = run_dmrg(
                    model, sector, [16, 32, 48], trial_deadline,
                    initial=product_state(model, sector, orientation), verbose=verbose)
                if trial_energy < best_energy:
                    best_energy = trial_energy
                    initial = trial_state
                    warmup_history = trial_history
            schedule = schedule[2:]
        energy, state, history = run_dmrg(model, sector, schedule, deadline, initial=initial, verbose=verbose)
        history = warmup_history + history
        result = {'energy': energy, 'history': history}
        if measure:
            result['correlations'] = correlations(case, model, state)
        result['peak_mib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        connection.send(result)
    except BaseException:
        connection.send({'error': traceback.format_exc()})
    finally:
        connection.close()


def parallel_solve(case, budget, verbose):
    start = time.monotonic()
    bosons = case['family'] == 'bose_hubbard'
    sector = int(case['particles'] if bosons else case['ground_sector'])
    requested = [sector, sector + 1, sector - 1] if bosons else [sector, int(case['excited_sector'])]
    context = multiprocessing.get_context('fork')
    workers = {}
    results = {}
    try:
        for target in dict.fromkeys(requested):
            reader, writer = context.Pipe(duplex=False)
            deadline = start + max(0.9 * budget, budget - 15)
            process = context.Process(target=sector_worker,
                                      args=(case, target, deadline, target == sector, verbose, writer))
            process.start()
            writer.close()
            workers[target] = process, reader
        for target, (process, reader) in workers.items():
            result = reader.recv()
            if 'error' in result:
                raise RuntimeError(result['error'])
            results[target] = result
            reader.close()
            process.join()
    finally:
        for process, reader in workers.values():
            reader.close()
            if process.is_alive():
                process.terminate()
            process.join()
    energy = results[sector]['energy']
    gap = (results[sector + 1]['energy'] + results[sector - 1]['energy'] - 2 * energy if bosons
           else results[int(case['excited_sector'])]['energy'] - energy)
    return {'energy': float(energy), 'gap': float(gap),
            'correlations': results[sector]['correlations'],
            'method': 'U(1) two-site DMRG', 'sweeps': [results[target]['history'] for target in results],
            'worker_peak_mib': [results[target]['peak_mib'] for target in results],
            'runtime': time.monotonic() - start}


def solve(case, budget=560, verbose=False, parallel=None):
    start = time.monotonic()
    model = make_model(case)
    if parallel is None:
        parallel = model.length >= 16
    if parallel:
        return parallel_solve(case, budget, verbose)
    bosons = case['family'] == 'bose_hubbard'
    sector = int(case['particles'] if bosons else case['ground_sector'])
    schedule = [16, 32, 64, 96, 128, 160, 192, 224, 256, 256, 256, 256, 256, 256]
    ground_deadline = start + budget * (0.45 if bosons else 0.56)
    energy, ground, ground_history = run_dmrg(model, sector, schedule, ground_deadline, verbose=verbose)
    measured = correlations(case, model, ground)
    histories = [ground_history]
    if bosons:
        energies = []
        for position, shift in enumerate([1, -1]):
            remaining = start + budget - time.monotonic()
            deadline = time.monotonic() + remaining / (2 - position)
            initial = shifted_state(ground, model, sector + shift)
            extra_energy, _, history = run_dmrg(model, sector + shift,
                                               [64, 96, 128, 160, 192, 224, 256, 256, 256, 256, 256, 256],
                                               deadline, initial=initial, verbose=verbose)
            histories.append(history)
            energies.append(extra_energy)
        gap = sum(energies) - 2 * energy
    else:
        excited_sector = int(case['excited_sector'])
        if excited_sector == sector:
            gap = 0.
        else:
            initial = shifted_state(ground, model, excited_sector)
            extra_energy, _, history = run_dmrg(model, excited_sector,
                                               [64, 96, 128, 160, 192, 224, 256, 256, 256, 256, 256, 256],
                                               start + budget, initial=initial, verbose=verbose)
            histories.append(history)
            gap = extra_energy - energy
    return {'energy': float(energy), 'gap': float(gap), 'correlations': measured,
            'method': 'U(1) two-site DMRG', 'sweeps': histories,
            'runtime': time.monotonic() - start}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--budget', type=float, default=560.)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    case = json.loads(Path(args.input).read_text(encoding='utf-8'))
    result = solve(case, args.budget, args.verbose)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, allow_nan=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
