import argparse
from brick import run
from peel import *


def reduce_instance(instance, root=None):
    matrix = target(instance)
    undo = []
    if instance['id'] == 'ladder_14':
        root = 6 if root is None else root
        support = [1, 6, 9]
        _, vectors = np.linalg.eigh(matrix[np.ix_(support, support)])
        vector = np.zeros(len(matrix), complex)
        vector[support] = vectors[:, 0]
        pairs = [(9, 1), (6, 9)] if root == 6 else ([(9, 6), (1, 9)] if root == 1 else [(9, 1), (9, 6)])
        for first, second in pairs:
            upper, lower = vector[first], vector[second]
            gate = first, second, math.atan2(abs(lower), abs(upper)), float(np.angle(-lower / upper))
            matrix = rotate(matrix, *gate)
            vector[first] = np.cos(gate[2]) * upper - np.exp(-1j * gate[3]) * np.sin(gate[2]) * lower
            vector[second] = 0
            undo.append(gate)
        frozen = [root]
    elif instance['id'] == 'irregular_16':
        root = 7 if root is None else root
        first, second = (10, 7) if root == 7 else (7, 10)
        column = next(column for column in range(len(matrix)) if column not in (first, second) and abs(matrix[first, column]) > 1e-8)
        upper, lower = matrix[first, column], matrix[second, column]
        gate = first, second, math.atan2(abs(lower), abs(upper)), float(np.angle(-lower / upper))
        matrix = rotate(matrix, *gate)
        undo.append(gate)
        frozen = [root]
    else:
        outside = [mode for mode in range(len(matrix)) if mode not in (3, 8, 11, 15)]
        column = max(outside, key=lambda column: abs(matrix[3, column]))
        for first, second in [(3, 15), (8, 3)]:
            upper, lower = matrix[first, column], matrix[second, column]
            gate = first, second, math.atan2(abs(lower), abs(upper)), float(np.angle(-lower / upper))
            matrix = rotate(matrix, *gate)
            undo.append(gate)
        values, vectors = np.linalg.eigh(matrix[np.ix_([3, 11, 15], [3, 11, 15])])
        vector = np.zeros(len(matrix), complex)
        vector[[3, 11, 15]] = vectors[:, -1]
        for first, second in [(3, 15), (3, 11)]:
            upper, lower = vector[first], vector[second]
            gate = first, second, math.atan2(abs(lower), abs(upper)), float(np.angle(-lower / upper))
            matrix = rotate(matrix, *gate)
            vector[first] = np.cos(gate[2]) * upper - np.exp(-1j * gate[3]) * np.sin(gate[2]) * lower
            vector[second] = 0
            undo.append(gate)
        frozen = [3, 11, 15]
    active = [mode for mode in range(len(matrix)) if mode not in frozen]
    print(instance['id'], 'FROZEN', frozen, matrix.diagonal()[frozen], 'error', np.linalg.norm(matrix[np.ix_(frozen, active)]), flush=True)
    reduced = dict(instance)
    reduced['id'] = ('reduced_' if root is None else 'reduced_root' + str(root) + '_') + instance['id']
    reduced['n_modes'] = len(active)
    reduced['initial_occupied'] = [active.index(mode) for mode in instance['initial_occupied'] if mode in active]
    reduced['n_particles'] = len(reduced['initial_occupied'])
    reduced['edges'] = [[active.index(first), active.index(second)] for first, second in instance['edges'] if first in active and second in active]
    block = matrix[np.ix_(active, active)]
    reduced['target_projector'] = dict(real=block.real.tolist(), imag=block.imag.tolist())
    reduced['budgets'] = dict(max_gates=instance['budgets']['max_gates'] - len(undo), max_depth=instance['budgets']['max_depth'] - (1 if len(undo) == 1 else 2))
    return reduced, active, undo


def expand(instance, active, undo, reduced_id=None):
    solved = False
    for path in Path('.').glob((reduced_id or 'reduced_' + instance['id']) + '_*.json'):
        reduced = json.loads(path.read_text())
        if 'layers' not in reduced:
            continue
        gates = [(active[gate['u']], active[gate['v']], gate['theta'], gate['phi']) for layer in reduced['layers'] for gate in layer]
        gates.extend((first, second, -theta, phi) for first, second, theta, phi in reversed(undo))
        circuit = dict(id=instance['id'], layers=schedule(gates, instance['n_modes']))
        Path(instance['id'] + '_' + path.stem + '.json').write_text(json.dumps(circuit))
        if len(gates) <= instance['budgets']['max_gates'] and len(circuit['layers']) <= instance['budgets']['max_depth']:
            print('SOLVED EXPANDED', instance['id'], len(gates), len(circuit['layers']), flush=True)
            solved = True
    return solved


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=2)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--trials', type=int, default=10)
    parser.add_argument('--root', type=int)
    arguments = parser.parse_args()
    instance = INSTANCES[arguments.index]
    reduced, active, undo = reduce_instance(instance, arguments.root)
    Path(reduced['id'] + '_instance.json').write_text(json.dumps(reduced))
    for seed in range(arguments.seed, arguments.seed + arguments.trials):
        run(reduced, seed)
        if expand(instance, active, undo, reduced['id']):
            break
