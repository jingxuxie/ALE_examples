import argparse
import itertools
import time

import numpy as np

from experiment import MASKS, ORDERS, SUBSETS, report, transform


def features(energy, orbitals, families, order=4):
    terms = transform(energy)
    combinations = np.array(list(itertools.combinations(range(8), order)))
    subset_masks = np.sum(1 << combinations, axis=1)
    nodes = np.broadcast_to(combinations[None, :, :], (len(energy), len(combinations), order)).copy()
    model_indices = np.arange(len(energy))[:, None, None]
    singles = -terms[model_indices, 1 << nodes]
    sorting = np.argsort(-singles, axis=2)
    nodes = np.take_along_axis(nodes, sorting, axis=2)
    singles = -terms[model_indices, 1 << nodes]
    scale = singles.sum(axis=2)
    normalized = singles / scale[:, :, None]
    gaps = orbitals[model_indices, nodes + 3]
    parts = [normalized, gaps - 1.5, np.log(np.maximum(scale, 1e-8))[:, :, None] / 5]
    lower = {}
    for cardinality, divisor in [(2, 0.05), (3, 0.005)]:
        selections = list(itertools.combinations(range(order), cardinality))
        masks = np.stack([np.sum(1 << nodes[:, :, selection], axis=2) for selection in selections], axis=2)
        values = terms[model_indices, masks] / scale[:, :, None]
        parts.append(values / divisor)
        lower[cardinality] = {selection: values[:, :, index] for index, selection in enumerate(selections)}
    if order == 4:
        products = []
        for triangle, values in lower[3].items():
            other = next(node for node in range(4) if node not in triangle)
            for node in triangle:
                products.append(values * lower[2][tuple(sorted((node, other)))] / (normalized[:, :, node] + 0.015) / 0.001)
        for path in itertools.permutations(range(4)):
            if path[0] < path[-1]:
                value = np.ones_like(scale)
                for left, right in zip(path[:-1], path[1:]):
                    value *= lower[2][tuple(sorted((left, right)))]
                value /= (normalized[:, :, path[1]] + 0.015) * (normalized[:, :, path[2]] + 0.015)
                products.append(value / 0.001)
        parts.append(np.stack(products, axis=2))
    family_encoding = np.eye(6)[families]
    parts.append(np.broadcast_to(family_encoding[:, None, :], (len(energy), len(combinations), 6)))
    inputs = np.concatenate(parts, axis=2)
    pair_strength = sum(np.abs(value) for value in lower[2].values())
    triple_strength = sum(np.abs(value) for value in lower[3].values())
    output_scale = scale * (0.15 * triple_strength + 0.01 * pair_strength ** 2) + 1e-10
    if order == 5:
        output_scale *= 0.15
    targets = terms[:, subset_masks] / output_scale
    return inputs.astype(np.float32), targets.astype(np.float32), output_scale.astype(np.float32), subset_masks


def main():
    import torch
    from torch import nn
    parser = argparse.ArgumentParser()
    parser.add_argument('--order', type=int, default=4)
    parser.add_argument('--epochs', type=int, default=80)
    arguments = parser.parse_args()
    torch.set_num_threads(2)
    torch.manual_seed(42)
    data = np.load('train.npz')
    started = time.time()
    inputs, targets, scales, masks = features(data['energies'], data['orbitals'], data['families'], arguments.order)
    split = len(inputs) - 1800
    train_inputs = torch.from_numpy(inputs[:split].reshape(-1, inputs.shape[-1]))
    train_targets = torch.from_numpy(targets[:split].reshape(-1, 1))
    train_scales = torch.from_numpy(scales[:split].reshape(-1, 1) / (4e-5 if arguments.order == 4 else 4e-6))
    test_inputs = torch.from_numpy(inputs[split:].reshape(-1, inputs.shape[-1]))
    model = nn.Sequential(nn.Linear(inputs.shape[-1], 192), nn.SiLU(), nn.Linear(192, 192), nn.SiLU(), nn.Linear(192, 96), nn.SiLU(), nn.Linear(96, 1))
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.002, weight_decay=0.001)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, arguments.epochs, eta_min=0.00005)
    for epoch in range(arguments.epochs):
        ordering = torch.randperm(len(train_inputs))
        model.train()
        total = 0
        for indices in ordering.split(4096):
            prediction = model(train_inputs[indices])
            loss = torch.mean(((prediction - train_targets[indices]) * train_scales[indices]) ** 2)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += float(loss) * len(indices)
        scheduler.step()
        if epoch % 5 == 4 or epoch == 0:
            model.eval()
            with torch.no_grad():
                predicted = torch.cat([model(batch) for batch in test_inputs.split(8192)]).numpy().reshape(-1, len(masks))
            errors = (predicted - targets[split:]) * scales[split:]
            print(epoch + 1, 'loss', total / len(train_inputs), 'time', time.time() - started, 'local RMSE', np.sqrt(np.mean(errors ** 2)) * 1e6, flush=True)
            report(errors.sum(1), data['families'][split:], 'sum error')
            torch.save(model.state_dict(), 'network' + str(arguments.order) + '.pt')
            weights = {str(index) + '_' + key: value.detach().numpy() for index, layer in enumerate(model) if isinstance(layer, nn.Linear) for key, value in layer.named_parameters()}
            np.savez('network' + str(arguments.order) + '.npz', **weights)
            np.savez('neural_validation' + str(arguments.order) + '.npz', predicted=predicted * scales[split:], truth=targets[split:] * scales[split:], masks=masks)


if __name__ == '__main__':
    main()
