import pickle
from pathlib import Path
import numpy as np


def export(paths, destination='model.npz', kind='all'):
    arrays = {'count': np.array(len(paths)), 'kind': np.array(kind)}
    for index, path in enumerate(paths):
        with open(path, 'rb') as stream:
            model = pickle.load(stream)
        prefix = str(index) + '_'
        arrays[prefix + 'mean'] = model['mean']
        arrays[prefix + 'scale'] = model['scale']
        for name, values in model['weights'].items():
            arrays[prefix + name] = values
    np.savez_compressed(destination, **arrays)


if __name__ == '__main__':
    import sys
    paths = sorted(Path('.').glob(sys.argv[1] if len(sys.argv) > 1 else 'nn_trial_*.pkl'))
    export(paths, kind=sys.argv[2] if len(sys.argv) > 2 else 'all')
