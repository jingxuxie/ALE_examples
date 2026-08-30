import json
import math
import numpy as np
from search import Database, OUTPUT, SPEC


def main():
    database = Database()
    result = []
    for bank in range(3):
        orders = {order for identity, order, scale, seed in database.data if identity == bank}
        complete = [order for order in orders if all((bank, order, scale, seed) in database.data
                    for scale in SPEC['scales'] for seed in SPEC['public_seeds'])]
        profiles = {}
        for order in complete:
            public = database.values(bank, order, SPEC['public_seeds'])
            noise = [np.array([values for (identity, candidate, strength, seed), values in database.data.items()
                              if identity == bank and candidate == order and strength == scale and seed is not None])
                     for scale in SPEC['scales']]
            profiles[order] = public, noise
        ranked = []
        for high in complete:
            high_public, high_noise = profiles[high]
            for low in complete:
                low_public, low_noise = profiles[low]
                gap = np.abs(high_public[:, :, 0] - low_public[:, :, 0])
                separation = high_public[:, :, 1] - low_public[:, :, 1]
                if (gap.mean(axis=1).max() > 0.02 or gap.max() > 0.045
                        or separation.mean(axis=1).min() < 0.28 or separation.min() < 0.24):
                    continue
                expected = []
                noisy_separation = []
                for high_values, low_values in zip(high_noise, low_noise):
                    delta = abs(high_values[:, 0].mean() - low_values[:, 0].mean())
                    spread = np.sqrt(high_values[:, 0].var() + low_values[:, 0].var())
                    spread = max(spread, 0.005)
                    expected.append(float(spread * np.sqrt(2 / np.pi) * np.exp(-delta ** 2 / (2 * spread ** 2))
                                          + delta * math.erf(delta / (np.sqrt(2) * spread))))
                    noisy_separation.append(float(high_values[:, 1].mean() - low_values[:, 1].mean()))
                score = max(expected) + 2 * max(0, 0.29 - min(noisy_separation))
                ranked.append({'score': score, 'high': high, 'low': low, 'expected_gap': expected,
                               'mean_separation': noisy_separation})
        ranked.sort(key=lambda record: record['score'])
        result.append(ranked)
        print('PUBLIC AUDIT BANK', bank + 1, 'complete', len(complete), 'passing pairs', len(ranked),
              'best', ranked[:3], flush=True)
    (OUTPUT / 'public_candidates.json').write_text(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
