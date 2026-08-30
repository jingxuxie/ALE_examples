import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'
import json
import pickle
import time
from pathlib import Path
import numpy as np
from scipy.spatial.distance import cdist
from scipy.linalg import solve
from experiment import ROOT, read, report


def kernel_trials(features, test, target, validation):
    importance = np.load('feature_importance.npy')
    predictions = {}
    for count in (40, 100, 250, 441):
        indices = np.argsort(importance)[-count:]
        if 0 not in indices:
            indices = np.r_[0, indices]
        joined = np.sign(features[:, indices]) * np.log1p(np.abs(features[:, indices]))
        testing = np.sign(test[:, indices]) * np.log1p(np.abs(test[:, indices]))
        mean, scale = joined.mean(axis=0), joined.std(axis=0)
        scale = np.maximum(scale, .001)
        joined = (joined - mean) / scale / np.sqrt(len(indices))
        testing = (testing - mean) / scale / np.sqrt(len(indices))
        distances = cdist(joined, joined, 'sqeuclidean')
        test_distances = cdist(testing, joined, 'sqeuclidean')
        for gamma in (.15, .4, 1., 2.5):
            kernel = np.exp(-gamma * distances)
            test_kernel = np.exp(-gamma * test_distances)
            for regularization in (.0001, .001, .01):
                adjusted = kernel.copy()
                adjusted.flat[::len(adjusted)+1] += regularization
                coefficients = solve(adjusted, target - target.mean(), assume_a='pos')
                prediction = test_kernel @ coefficients + target.mean()
                label = f'KRR_{count}_{gamma}_{regularization}'
                predictions[label] = prediction
                report(validation, prediction, label)
    np.savez('kernel_predictions.npz', **predictions)


def neural_trials(features, test, target, validation, prefix='nn_trial', epochs=1200, seeds=5):
    import torch
    from torch import nn
    torch.set_num_threads(1)
    joined = np.sign(features) * np.log1p(np.abs(features))
    testing = np.sign(test) * np.log1p(np.abs(test))
    mean, scale = joined.mean(axis=0), np.maximum(joined.std(axis=0), .001)
    joined = torch.tensor(np.clip((joined - mean) / scale, -10, 10), dtype=torch.float32)
    testing = torch.tensor(np.clip((testing - mean) / scale, -10, 10), dtype=torch.float32)
    labels = torch.tensor(target, dtype=torch.float32)[:, None]
    sample_weights = torch.tensor(np.where(features[:, 0] == 14, 1., np.where(features[:, 0] == 12, .6, .35)), dtype=torch.float32)[:, None]
    predictions = {}
    for seed in range(seeds):
        torch.manual_seed(891 + seed)
        model = nn.Sequential(nn.Linear(features.shape[1], 96), nn.SiLU(), nn.Dropout(.04), nn.Linear(96, 48), nn.SiLU(), nn.Dropout(.04), nn.Linear(48, 1), nn.Sigmoid())
        optimizer = torch.optim.AdamW(model.parameters(), lr=.0015, weight_decay=.03)
        started = time.monotonic()
        best_score = 1.
        for epoch in range(epochs):
            model.train()
            ordering = torch.randperm(len(joined))
            for batch in ordering.split(384):
                optimizer.zero_grad()
                loss = torch.mean(sample_weights[batch] * (model(joined[batch]) - labels[batch]) ** 2)
                loss.backward()
                optimizer.step()
            if (epoch + 1) % 100 == 0:
                model.eval()
                with torch.no_grad():
                    prediction = model(testing).numpy().ravel()
                label = f'NN_{seed}_{epoch+1}'
                predictions[label] = prediction
                score = report(validation, prediction, label)
                if score < best_score:
                    best_score = score
                    weights = {name: value.detach().numpy().copy() for name, value in model.state_dict().items()}
                    with open(f'{prefix}_{seed}.pkl', 'wb') as stream:
                        pickle.dump({'mean': mean, 'scale': scale, 'weights': weights, 'epoch': epoch + 1}, stream)
            if epoch == 599:
                for group in optimizer.param_groups:
                    group['lr'] = .0005
        print('nn seconds', seed, time.monotonic() - started, flush=True)
    np.savez(prefix + '_predictions.npz', **predictions)


if __name__ == '__main__':
    arrays = np.load('public_features.npz')
    training = read(ROOT / 'train.jsonl') + read(ROOT / 'auxiliary_train_L10_L12.jsonl') + read(ROOT / 'auxiliary_validation_L10_L12.jsonl')
    validation = read(ROOT / 'validation.jsonl')
    target = np.array([case['f'] for case in training])
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'kernel':
        kernel_trials(arrays['train'], arrays['test'], target, validation)
    else:
        neural_trials(arrays['train'], arrays['test'], target, validation)
