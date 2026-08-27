import json
from pathlib import Path

from generated import generate
from numerics import diagonalize, hamiltonian
from physics import physical_couplings


def run(source, directory):
    source = Path(source)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    case = json.loads(source.read_text())['cases'][-1]
    records = []
    for stress in [False, True]:
        selected = dict(case)
        if stress:
            selected['length'] = 5.5
            selected['couplings'] = [{'degree': 4, 'value': 2.0},
                                     {'degree': 4, 'transfer': 2, 'value': 0.7},
                                     {'degree': 4, 'transfer': -2, 'value': 0.7},
                                     {'degree': 2, 'transfer': 2, 'value': 0.12},
                                     {'degree': 2, 'transfer': -2, 'value': 0.12}]
        coefficients, constant = physical_couplings(selected)
        cutoff = 24 if stress else 30
        for sector in selected['sectors']:
            for window in [6, 8, 12, 1000000]:
                basis = generate(selected, sector, cutoff, sorted(coefficients),
                                 directory / f'{stress}_{sector["name"]}_{window}', momentum_window=window)
                values = diagonalize(hamiltonian(basis, coefficients, constant))
                result = {'stress': stress, 'sector': sector['name'], 'cutoff': cutoff, 'window': window,
                          'dimension': len(basis['energy']), 'energies': values.tolist()}
                records.append(result)
                print(result, flush=True)
                (directory / 'windows.json').write_text(json.dumps(records, indent=2))


if __name__ == '__main__':
    import sys
    run(sys.argv[1], sys.argv[2])
