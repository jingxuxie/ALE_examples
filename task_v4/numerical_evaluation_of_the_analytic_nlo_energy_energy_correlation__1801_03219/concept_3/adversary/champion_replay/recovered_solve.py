import argparse
import json
import time
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=120)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--beta', type=float, default=0.5)
    parser.add_argument('--spacing', action='store_true')
    parser.add_argument('--reverse', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).parent
    target = json.loads((root.parent.parent / 'participant/input/target.json').read_text())
    expected = np.array(target['cyclic_autocorrelation'])
    magnitudes = np.sqrt(np.maximum(np.fft.rfft(expected).real, 0))
    generator = np.random.default_rng(args.seed)
    values = generator.normal(0.25, 0.55, 512)
    discrete = np.zeros(512)

    def project_discrete(vector):
        discrete.fill(0)
        order = np.argsort(vector)[::-1]
        if not args.spacing:
            discrete[order[:32]] = 2
            discrete[order[32:96]] = 1
        else:
            count = 0
            for index in order:
                if discrete[(index - 1) % 512] or discrete[(index + 1) % 512]:
                    continue
                discrete[index] = 2 if count < 32 else 1
                count += 1
                if count == 96:
                    break
        return discrete

    def project_fourier(vector):
        spectrum = np.fft.rfft(vector)
        spectrum *= magnitudes / np.maximum(np.abs(spectrum), 1e-20)
        spectrum[0] = 128
        return np.fft.irfft(spectrum, n=512)

    start = time.monotonic()
    best_error = float('inf')
    iteration = 0
    while time.monotonic() - start < args.seconds:
        if args.reverse:
            first = project_fourier(values)
            second = project_discrete(2 * first - values)
        else:
            first = project_discrete(values)
            second = project_fourier(2 * first - values)
        difference = second - first
        values += args.beta * difference
        error = float(difference @ difference)
        if error < best_error:
            best_error = error
            if error < 10:
                print('best', args.seed, iteration, best_error, flush=True)
        if error < 1e-10 or iteration % 10000 == 0:
            correlation = np.rint(np.fft.irfft(np.abs(np.fft.rfft(discrete)) ** 2, n=512)).astype(int)
            cost = int(np.sum((correlation - expected) ** 2))
            print('progress', args.seed, iteration, round(time.monotonic()-start, 2), error, best_error, cost, flush=True)
            if cost == 0:
                artifact = {'schema_version': 1, 'a': discrete.astype(int).tolist()}
                (root / 'design.json').write_text(json.dumps(artifact) + '\\n')
                print('SOLVED', flush=True)
                return
        iteration += 1
    np.savez(root / f'state_{args.seed}.npz', values=values, discrete=discrete)
    print('finished', args.seed, iteration, best_error, flush=True)


if __name__ == '__main__':
    main()
