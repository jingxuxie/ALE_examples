import argparse
import time
from local_compile import *


def search(instance, width=200, extra=0):
    compiler = LocalCompiler(instance)
    matrix = target(instance)
    initial = np.diag(compiler.initial)
    active = compiler.freeze(matrix, tuple(range(len(matrix))))
    beam = [(matrix, active, [])]
    started = time.monotonic()
    best = None
    for iteration in range(len(matrix)):
        following = {}
        for matrix, active, previous in beam:
            for result, gates, after, root in compiler.options(matrix, active, extra=extra):
                combined = previous + gates
                count = len(combined)
                depth = len(schedule(combined, len(matrix)))
                if count > instance['budgets']['max_gates'] or depth > instance['budgets']['max_depth']:
                    continue
                if not after:
                    error = np.linalg.norm(result - initial)
                    if error < 1e-8:
                        inverse = [(first, second, -theta, phi) for first, second, theta, phi in reversed(combined)]
                        circuit = dict(id=instance['id'], layers=schedule(inverse, len(matrix)))
                        Path(instance['id'] + '_local_beam.json').write_text(json.dumps(circuit))
                        print('SOLVED', instance['id'], count, depth, error, flush=True)
                        return circuit
                    continue
                impurity = np.sum(result.diagonal().real * (1 - result.diagonal().real))
                zeros = np.count_nonzero(abs(result) < 1e-9)
                distances = np.full((len(after), len(after)), 100.0)
                np.fill_diagonal(distances, 0)
                for first_index, first in enumerate(after):
                    for second_index, second in enumerate(after):
                        if second in compiler.neighbors[first]:
                            distances[first_index, second_index] = 1
                for center in range(len(after)):
                    distances = np.minimum(distances, distances[:, center, None] + distances[None, center, :])
                locality = np.sum(abs(result[np.ix_(after, after)]) ** 2 * distances ** 2)
                score = (count + len(after), depth, impurity, -zeros, locality)
                real, imag = np.round(result.real, 8), np.round(result.imag, 8)
                real[real == 0] = 0
                imag[imag == 0] = 0
                signature = real.tobytes() + imag.tobytes()
                if signature not in following or score < following[signature][0]:
                    following[signature] = (score, result, after, combined)
        selected = []
        used = set()
        for ranking in [lambda entry: entry[1][0], lambda entry: (entry[1][0][1], entry[1][0][0], entry[1][0][2]),
                        lambda entry: (entry[1][0][0] + 2 * np.sqrt(entry[1][0][4]), entry[1][0][1])]:
            added = 0
            for signature, entry in sorted(following.items(), key=ranking):
                if signature not in used:
                    used.add(signature)
                    selected.append(entry)
                    added += 1
                    if added >= width // 3:
                        break
        beam = [(result, active, gates) for _, result, active, gates in selected]
        print(instance['id'], iteration, len(following), selected[0][0] if selected else None, 'time', round(time.monotonic() - started, 1), flush=True)
        if not beam:
            break
    print('FAILED', instance['id'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--width', type=int, default=200)
    parser.add_argument('--extra', type=int, default=0)
    arguments = parser.parse_args()
    search(INSTANCES[arguments.index], arguments.width, arguments.extra)
