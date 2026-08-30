import itertools
import json
import random
from pathlib import Path

from baseline import baseline_policy
from cascade_sim import block_size, stable_seed

from experiment import ASSETS, OUTPUT


def build_suite(source_seed=2026082815, extra_excluded=None):
    source = random.Random(source_seed)
    grid = json.loads((ASSETS / 'input' / 'distribution.json').read_text())
    excluded = set()
    for split in ['train', 'dev']:
        suite = json.loads((ASSETS / 'input' / f'{split}.json').read_text())
        for case in suite['cases']:
            excluded.add(tuple(case[field] for field in ['family', 'frame_bits', 'q_true', 'estimate_bias', 'sample_size', 'latency']))
    for case in extra_excluded or []:
        excluded.add(tuple(case[field] for field in ['family', 'frame_bits', 'q_true', 'estimate_bias', 'sample_size', 'latency']))
    cases = []
    for family, values in grid.items():
        tuples = [operating for operating in itertools.product(values['sizes'], values['rates'], values['biases'], values['samples'], values['latencies'])
                  if (family, *operating) not in excluded]
        for operating in source.sample(tuples, 64):
            frame_bits, true_rate, bias, samples, latency = operating
            cases.append(dict(family=family, frame_bits=frame_bits, q_true=true_rate, estimate_bias=bias,
                              sample_size=samples, latency=latency,
                              frame_seeds=[source.getrandbits(120) for unused in range(16)]))
    stress = []
    for frame_bits in [512, 2048, 8192]:
        case = dict(family='collision_tail', frame_bits=frame_bits, q_true=.006, estimate_bias=1,
                    sample_size=256, latency=.001, frame_seeds=[], errors=[])
        for index in range(256):
            seed = source.getrandbits(120)
            estimator = random.Random(stable_seed(seed, 'estimate'))
            sample_errors = sum(estimator.random() < .006 for unused in range(256))
            estimate = min(.15, max(1/frame_bits, (sample_errors+.5)/257))
            features = dict(frame_bits=frame_bits, q_est=estimate, first_size=2, parity_est=estimate, corrected_fraction=0)
            first_size = block_size(baseline_policy()['schedule'][0]['size'], features)
            second_size = block_size(baseline_policy()['schedule'][1]['size'], features)
            partitions = []
            for pass_index, size in enumerate([first_size, second_size]):
                permutation = list(range(frame_bits))
                random.Random(stable_seed(seed, f'permutation:{pass_index}')).shuffle(permutation)
                partition = {}
                for position, bit in enumerate(permutation):
                    partition[bit] = position // size
                partitions.append(partition)
            intersections = {}
            for bit in range(frame_bits):
                intersections.setdefault((partitions[0][bit], partitions[1][bit]), []).append(bit)
            count = 4 if index % 3 == 0 else 2
            chosen = source.choice([bits for bits in intersections.values() if len(bits) >= count])
            case['frame_seeds'].append(seed)
            case['errors'].append(source.sample(chosen, count))
        stress.append(case)
    return dict(split='independent', cases=cases, stress=stress)


if __name__ == '__main__':
    suite = build_suite()
    (OUTPUT / 'independent.json').write_text(json.dumps(suite))
    print('normal frames', sum(len(case['frame_seeds']) for case in suite['cases']))
    print('stress frames', sum(len(case['frame_seeds']) for case in suite['stress']))
