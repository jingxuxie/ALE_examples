import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import json
import pickle
import time
from pathlib import Path
import numpy as np
import torch
from torch import nn
from experiment import ROOT, read, report
from features import feature_matrix
from export_model import export
from predict import load_model, estimate


def train(args):
    torch.set_num_threads(1)
    while True:
        simulations = read('simulated.jsonl')
        if len(simulations) >= args.simulations:
            break
        print('waiting', len(simulations), 'of', args.simulations, flush=True)
        time.sleep(30)
    simulations = simulations[:args.simulations]
    original = read(ROOT / 'train.jsonl') + read(ROOT / 'auxiliary_train_L10_L12.jsonl') + read(ROOT / 'auxiliary_validation_L10_L12.jsonl')
    public_validation = read(ROOT / 'validation.jsonl')
    training = original + public_validation + simulations[320:]
    validation = simulations[:320]
    public = np.load('public_features.npz')
    columns = np.r_[np.arange(250), np.concatenate([np.arange(308 + offset * 13, 317 + offset * 13) for offset in range(5)])]
    simulated_features = feature_matrix(simulations, kind='quick_particle')
    features = np.concatenate([public['train'][:, columns], public['test'][:, columns], simulated_features[320:]])
    test = simulated_features[:320]
    np.savez('final_training_features.npz', train=features, test=test)
    labels = np.array([case['f'] for case in training])
    transformed = np.sign(features) * np.log1p(np.abs(features))
    mean, scale = transformed.mean(axis=0), np.maximum(transformed.std(axis=0), .001)
    joined = torch.tensor(np.clip((transformed - mean) / scale, -10, 10), dtype=torch.float32)
    test_values = np.sign(test) * np.log1p(np.abs(test))
    testing = torch.tensor(np.clip((test_values - mean) / scale, -10, 10), dtype=torch.float32)
    target = torch.tensor(labels, dtype=torch.float32)[:, None]
    weights = torch.tensor(np.where(features[:, 0] == 14, 1., np.where(features[:, 0] == 12, .6, .35)), dtype=torch.float32)[:, None]
    print('training', len(training), 'validation', len(validation), 'features', features.shape[1], flush=True)
    predictions = []
    paths = []
    for seed in range(args.seeds):
        started = time.monotonic()
        torch.manual_seed(567091 + seed * 31)
        model = nn.Sequential(nn.Linear(features.shape[1], 96), nn.SiLU(), nn.Dropout(.04), nn.Linear(96, 48), nn.SiLU(), nn.Dropout(.04), nn.Linear(48, 1), nn.Sigmoid())
        optimizer = torch.optim.AdamW(model.parameters(), lr=.0015, weight_decay=.03)
        averaged = None
        average_count = 0
        for epoch in range(args.epochs):
            model.train()
            for batch in torch.randperm(len(joined)).split(384):
                optimizer.zero_grad()
                loss = torch.mean(weights[batch] * (model(joined[batch]) - target[batch])**2)
                loss.backward()
                optimizer.step()
            if epoch + 1 == args.epochs // 2:
                for group in optimizer.param_groups:
                    group['lr'] = .0005
            if epoch + 1 >= args.epochs * .625 and (epoch + 1) % 10 == 0:
                current = {name: values.detach().numpy().copy() for name, values in model.state_dict().items()}
                if averaged is None:
                    averaged = current
                else:
                    for name in averaged:
                        averaged[name] += (current[name] - averaged[name]) / (average_count + 1)
                average_count += 1
        payload = {'mean': mean, 'scale': scale, 'weights': averaged, 'epochs': args.epochs, 'seed': seed}
        path = Path(f'{args.prefix}_{seed}.pkl')
        with path.open('wb') as stream:
            pickle.dump(payload, stream, protocol=4)
        paths.append(path)
        export(paths, args.destination, kind='quick_particle')
        prediction = estimate(test, load_model(args.destination))
        report(validation, prediction, f'{args.prefix}_ensemble_{seed+1}')
        print('seed seconds', time.monotonic() - started, flush=True)
    residuals = (prediction - np.array([case['f'] for case in validation]))**2
    result = {
        'training_records': len(training), 'public_L14_training_records': 480,
        'auxiliary_records': 1920, 'simulated_training_records': len(simulations) - 320,
        'validation_records': 320, 'validation_source': 'simulated records 0 through 319, excluded from fitting',
        'public_validation_included_in_fit': True, 'seeds': args.seeds, 'epochs': args.epochs,
        'overall_rmse': float(np.sqrt(residuals.mean())),
        'family_rmse': {family: float(np.sqrt(residuals[[case['family'] == family for case in validation]].mean())) for family in sorted({case['family'] for case in validation})},
        'feature_kind': 'quick_particle', 'feature_count': int(features.shape[1]),
    }
    Path(args.prefix + '_metrics.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--simulations', type=int, default=1280)
    parser.add_argument('--epochs', type=int, default=800)
    parser.add_argument('--seeds', type=int, default=8)
    parser.add_argument('--prefix', default='final')
    parser.add_argument('--destination', default='model.npz')
    train(parser.parse_args())
