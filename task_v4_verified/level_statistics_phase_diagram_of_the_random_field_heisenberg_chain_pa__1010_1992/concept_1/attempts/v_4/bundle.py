import argparse
import gzip
import pickle
import numpy as np
from transforms import QuantileMap


def load_neural(prefix, variant, width):
    with gzip.open(f'{prefix}_neural_{variant}_{width}.pkl.gz', 'rb') as stream:
        neural = pickle.load(stream)
    snapshots = neural['snapshots']
    neural['snapshots'] = [{key: np.mean([snapshot[key] for snapshot in snapshots[start:start + 15]], axis=0)
                            for key in snapshots[0]} for start in range(0, len(snapshots), 15)]
    return neural


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', default='round1')
    parser.add_argument('--neural-variant', default='base')
    parser.add_argument('--width', type=int, default=128)
    parser.add_argument('--neural-weight', type=float, default=.5)
    parser.add_argument('--secondary-variant')
    parser.add_argument('--secondary-width', type=int, default=128)
    parser.add_argument('--secondary-weight', type=float, default=.4)
    args = parser.parse_args()
    neural = load_neural(args.prefix, args.neural_variant, args.width)
    bundle = [{'kind': 'neural', 'weight': args.neural_weight, 'model': neural}]
    secondary_weight = 0
    if args.secondary_variant:
        secondary = load_neural(args.prefix, args.secondary_variant, args.secondary_width)
        primary_quantiles = neural['transformer'].quantiles_
        secondary_quantiles = secondary['transformer'].quantiles_
        if secondary_quantiles.shape[1] >= primary_quantiles.shape[1] and np.array_equal(primary_quantiles, secondary_quantiles[:, :primary_quantiles.shape[1]]):
            neural['transformer'] = secondary['transformer']
            neural['variant'] = secondary['variant']
        secondary_weight = args.secondary_weight
        bundle.append({'kind': 'neural', 'weight': secondary_weight, 'model': secondary})
    kernel_weight = 1 - args.neural_weight - secondary_weight
    if kernel_weight > 0:
        with gzip.open(f'{args.prefix}_kernel_base.pkl.gz', 'rb') as stream:
            kernel = pickle.load(stream)
        references = {}
        for model in kernel['models']:
            key = id(model['transformer'])
            if key not in references:
                references[key] = model['train']
            model['train'] = references[key]
        bundle.append({'kind': 'kernel', 'weight': kernel_weight, 'model': kernel})
    transformers = {}
    for component in bundle:
        models = [component['model']] if component['kind'] == 'neural' else component['model']['models']
        for model in models:
            original = model['transformer']
            key = id(original)
            if key not in transformers:
                transformers[key] = QuantileMap(original.quantiles_, original.references_)
            model['transformer'] = transformers[key]
    with gzip.open('model.pkl.gz', 'wb', compresslevel=3) as stream:
        pickle.dump(bundle, stream, protocol=4)


if __name__ == '__main__':
    main()
