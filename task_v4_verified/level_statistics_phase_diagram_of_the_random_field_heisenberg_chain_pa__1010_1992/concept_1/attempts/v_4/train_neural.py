import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import pickle
import gzip
import time
import numpy as np
import torch
from torch import nn
from sklearn.preprocessing import QuantileTransformer
from training_data import load
from data_io import metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', default='full')
    parser.add_argument('--prefix', default='round1')
    parser.add_argument('--seeds', type=int, default=3)
    parser.add_argument('--width', type=int, default=128)
    parser.add_argument('--epochs', type=int, default=600)
    parser.add_argument('--final', action='store_true')
    args = parser.parse_args()
    torch.set_num_threads(1)
    cases, features, target, train, public, extra = load(args.variant, args.final)
    evaluation = np.concatenate([public, extra])
    print('records', len(train), len(public), len(extra), 'features', features.shape[1], flush=True)
    transformer = QuantileTransformer(n_quantiles=300, output_distribution='normal', random_state=31)
    features = transformer.fit(features[train]).transform(features).astype(np.float32)
    matrix = torch.from_numpy(np.clip(features, -3, 3))
    targets = torch.tensor(target, dtype=torch.float32)
    saved = []
    ensemble_predictions = []
    swa_predictions = []
    for seed in range(args.seeds):
        torch.manual_seed(seed + 510)
        model = nn.Sequential(nn.Linear(features.shape[1], args.width), nn.SiLU(), nn.Dropout(.1),
                              nn.Linear(args.width, args.width // 2), nn.SiLU(), nn.Dropout(.05),
                              nn.Linear(args.width // 2, 1), nn.Sigmoid())
        optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.04)
        started = time.monotonic()
        averages = []
        snapshots = []
        for epoch in range(args.epochs + 1):
            model.train()
            permutation = torch.tensor(np.random.default_rng(seed * 10000 + epoch).permutation(train))
            for subset in permutation.split(256):
                optimizer.zero_grad()
                prediction = model(matrix[subset]).flatten()
                loss = ((prediction - targets[subset]) ** 2).mean()
                loss.backward()
                optimizer.step()
            if epoch >= args.epochs - 140 and epoch % 10 == 0:
                model.eval()
                with torch.no_grad():
                    averages.append(model(matrix[evaluation]).flatten().numpy())
                snapshots.append({key: value.detach().numpy().copy() for key, value in model.state_dict().items()})
        saved.extend(snapshots)
        ensemble_predictions.append(np.mean(averages, axis=0))
        averaged = {key: np.mean([snapshot[key] for snapshot in snapshots], axis=0) for key in snapshots[0]}
        model.load_state_dict({key: torch.from_numpy(value) for key, value in averaged.items()})
        model.eval()
        with torch.no_grad():
            swa_predictions.append(model(matrix[evaluation]).flatten().numpy())
        for name, estimates in [('snapshots', ensemble_predictions), ('swa', swa_predictions)]:
            prediction = np.mean(estimates, axis=0)
            print(seed, name, 'public', metrics([cases[index] for index in public], prediction[:len(public)]), flush=True)
            if len(extra):
                print(seed, name, 'independent', metrics([cases[index] for index in extra], prediction[len(public):]), flush=True)
        print('seconds', time.monotonic() - started, flush=True)
    name = f'{args.prefix}_neural_{args.variant}_{args.width}'
    with gzip.open(name + '.pkl.gz', 'wb', compresslevel=3) as stream:
        pickle.dump({'variant': args.variant, 'transformer': transformer, 'snapshots': saved,
                     'training_count': len(train), 'target_training_count': sum(cases[index]['L'] == 14 for index in train),
                     'final_fit': args.final, 'epochs': args.epochs, 'seeds': args.seeds, 'width': args.width}, stream, protocol=4)
    np.savez(name + '_predictions.npz', indices=evaluation, predictions=np.mean(ensemble_predictions, axis=0))


if __name__ == '__main__':
    main()
