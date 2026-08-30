import argparse
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

from acquisition import CANDIDATES, DESIGN, UNKNOWN, acquire, prior
from experiment import MASKS, ORDERS, SUBSETS, report, transform
from neural import features


def local_predict(energy, orbitals, families):
    means = np.zeros_like(energy)
    for order in [4, 5]:
        weights = np.load('network' + str(order) + '.npz')
        for start in range(0, len(energy), 300):
            selected = slice(start, start + 300)
            inputs, _, scales, masks = features(energy[selected], orbitals[selected], families[selected], order)
            hidden = inputs
            for index in [0, 2, 4, 6]:
                hidden = hidden @ weights[str(index) + '_weight'].T + weights[str(index) + '_bias']
                if index != 6:
                    hidden = hidden / (1 + np.exp(np.clip(-hidden, -60, 60)))
            means[selected, masks] = hidden[:, :, 0] * scales
    means[(families == 0) | (families == 3) | (families == 4)] = 0
    return means


def global_features(terms, orbitals, family, mean, queries, observed_tails, covariance):
    selected = np.array([np.flatnonzero(CANDIDATES == mask)[0] for mask in queries])
    design = DESIGN[selected]
    gain = covariance @ design.T @ np.linalg.inv(design @ covariance @ design.T)
    posterior = mean.copy()
    posterior[UNKNOWN] += gain @ (observed_tails - design @ mean[UNKNOWN])
    sigma = np.sqrt(max(1e-20, np.sum(covariance) - np.sum(gain, axis=0) @ (design @ covariance @ np.ones(len(UNKNOWN)))))
    ordering = np.argsort(terms[MASKS[1]])
    canonical = np.array([sum(1 << int(ordering[orbital]) for orbital in range(8) if mask & (1 << orbital)) for mask in range(256)])
    strength = -terms[MASKS[1]].sum()
    tails = np.zeros(256)
    tails[queries] = observed_tails
    indicators = np.zeros(256)
    indicators[queries] = 1
    inputs = []
    for order, divisor in [(1, 1), (2, .05), (3, .005)]:
        inputs.append(terms[canonical[MASKS[order]]] / strength / divisor)
    for order, divisor in [(4, .001), (5, .0001), (6, .00001)]:
        inputs.append(posterior[canonical[MASKS[order]]] / strength / divisor)
    candidates = CANDIDATES[:-1]
    inputs += [tails[canonical[candidates]] / strength / .001, indicators[canonical[candidates]], orbitals[ordering + 3] - 1.5, np.eye(6)[family], np.array([np.log(strength), sigma / strength / .001, posterior[UNKNOWN].sum() / strength / .001])]
    return np.concatenate(inputs).astype(np.float32), max(sigma * .3, 1e-6), posterior[UNKNOWN].sum()


def prepare():
    data = np.load('train.npz')
    energy, orbitals, families = data['energies'], data['orbitals'], data['families']
    means = local_predict(energy, orbitals, families)
    terms = transform(energy)
    inputs, targets, scales, bases = [], [], [], []
    started = time.time()
    for index, (row, orbital, family, mean) in enumerate(zip(terms, orbitals, families, means)):
        covariance = prior(row, fifth_weight=2)
        queries, _, _ = acquire(row, covariance, mean=mean, power=.8, return_queries=True)
        observed_tails = SUBSETS[queries][:, UNKNOWN] @ row[UNKNOWN]
        features_row, scale, base = global_features(row, orbital, family, mean, queries, observed_tails, covariance)
        inputs.append(features_row)
        targets.append((row[UNKNOWN].sum() - base) / scale)
        scales.append(scale)
        bases.append(base)
        if index % 1000 == 999:
            print('prepare', index + 1, time.time() - started, flush=True)
    np.savez_compressed('global_data.npz', inputs=inputs, targets=targets, scales=scales, bases=bases, families=families)


def train():
    torch.set_num_threads(2)
    torch.manual_seed(27)
    data = np.load('global_data.npz')
    split = len(data['inputs']) - 1800
    center = data['inputs'][:split].mean(0)
    spread = np.maximum(data['inputs'][:split].std(0), .05)
    inputs = torch.from_numpy(np.clip((data['inputs'] - center) / spread, -20, 20).astype(np.float32))
    targets = torch.from_numpy(data['targets'].astype(np.float32))
    scales = torch.from_numpy(data['scales'].astype(np.float32) / 3e-5)
    model = nn.Sequential(nn.Linear(inputs.shape[1], 256), nn.SiLU(), nn.Dropout(.1), nn.Linear(256, 128), nn.SiLU(), nn.Dropout(.1), nn.Linear(128, 64), nn.SiLU(), nn.Linear(64, 1))
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, 250, eta_min=.00003)
    best = np.inf
    started = time.time()
    for epoch in range(250):
        model.train()
        for selected in torch.randperm(split).split(512):
            prediction = model(inputs[selected]).squeeze(1)
            loss = torch.mean(((prediction - targets[selected]) * scales[selected]) ** 2)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        scheduler.step()
        if epoch % 10 == 9:
            model.eval()
            with torch.no_grad():
                predicted = model(inputs[split:]).squeeze(1).numpy()
            errors = (predicted - data['targets'][split:]) * data['scales'][split:]
            score = np.mean(errors ** 2)
            report(errors, data['families'][split:], str(epoch + 1) + ' time ' + str(time.time() - started))
            if score < best:
                best = score
                torch.save(model.state_dict(), 'global.pt')
                np.savez('global.npz', center=center, spread=spread, **{key: value.detach().numpy() for key, value in model.state_dict().items()})
                np.savez('global_validation.npz', correction=predicted * data['scales'][split:], errors=errors)


if __name__ == '__main__':
    if not Path('global_data.npz').is_file():
        prepare()
    train()
