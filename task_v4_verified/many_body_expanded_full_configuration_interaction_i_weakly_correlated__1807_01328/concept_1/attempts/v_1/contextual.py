import itertools
import time

import numpy as np
import torch
from torch import nn

from experiment import MASKS, report, transform
from neural import features


def context_features(energy, orbitals):
    terms = transform(energy)
    singles = -terms[:, MASKS[1]]
    ordering = np.argsort(-singles, axis=1)
    model_indices = np.arange(len(energy))[:, None, None]
    pairs = np.array(list(itertools.combinations(range(8), 2)))
    other = np.array([[node for node in range(8) if node not in pair] for pair in pairs])
    first = np.broadcast_to(ordering[:, pairs[:, 0], None], (len(energy), 28, 6))
    second = np.broadcast_to(ordering[:, pairs[:, 1], None], first.shape)
    third = ordering[:, other]
    node_values = [-terms[model_indices, 1 << nodes] for nodes in [first, second, third]]
    scale = sum(node_values)
    inputs = [value / scale for value in node_values]
    inputs += [orbitals[model_indices, nodes + 3] - 1.5 for nodes in [first, second, third]]
    pair_values = [terms[model_indices, (1 << left) | (1 << right)] / scale for left, right in [(first, second), (first, third), (second, third)]]
    inputs += [value / 0.05 for value in pair_values]
    triple = terms[model_indices, (1 << first) | (1 << second) | (1 << third)] / scale
    inputs.append(triple / 0.005)
    inputs += [pair_values[0] * pair_values[1] / (node_values[0] / scale + 0.01) / 0.005,
               pair_values[0] * pair_values[2] / (node_values[1] / scale + 0.01) / 0.005,
               pair_values[1] * pair_values[2] / (node_values[2] / scale + 0.01) / 0.005]
    contexts = np.stack(inputs, axis=3).astype(np.float32)
    combinations = np.array(list(itertools.combinations(range(8), 4)))
    quad_nodes = np.broadcast_to(combinations[None, :, :], (len(energy), 70, 4)).copy()
    quad_nodes = np.take_along_axis(quad_nodes, np.argsort(-singles[np.arange(len(energy))[:, None, None], quad_nodes], axis=2), axis=2)
    ranks = np.argsort(ordering, axis=1)
    quad_ranks = ranks[np.arange(len(energy))[:, None, None], quad_nodes]
    pair_lookup = np.zeros((8, 8), dtype=np.int64)
    pair_lookup[pairs[:, 0], pairs[:, 1]] = np.arange(28)
    mappings = np.stack([pair_lookup[quad_ranks[:, :, left], quad_ranks[:, :, right]] for left, right in itertools.combinations(range(4), 2)], axis=2)
    return contexts, mappings


class ContextModel(nn.Module):
    def __init__(self, local_size):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(13, 48), nn.SiLU(), nn.Linear(48, 24), nn.SiLU())
        self.predictor = nn.Sequential(nn.Linear(local_size + 144, 192), nn.SiLU(), nn.Linear(192, 128), nn.SiLU(), nn.Linear(128, 64), nn.SiLU(), nn.Linear(64, 1))

    def forward(self, local, context, mapping):
        encoded = self.encoder(context).mean(dim=2)
        collected = encoded[torch.arange(len(local))[:, None, None], mapping].reshape(len(local), 70, -1)
        return self.predictor(torch.cat((local, collected), dim=2)).squeeze(2)


def main():
    torch.set_num_threads(2)
    torch.manual_seed(2026)
    data = np.load('train.npz')
    started = time.time()
    local, targets, scales, masks = features(data['energies'], data['orbitals'], data['families'])
    contexts, mappings = context_features(data['energies'], data['orbitals'])
    local, contexts, mappings, targets, scaled = [torch.from_numpy(value) for value in [local, contexts, mappings, targets, scales / 4e-5]]
    split = len(local) - 1800
    model = ContextModel(local.shape[-1])
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.0015, weight_decay=0.002)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, 80, eta_min=0.00005)
    for epoch in range(80):
        ordering = torch.randperm(split)
        model.train()
        total = 0
        for indices in ordering.split(64):
            prediction = model(local[indices], contexts[indices], mappings[indices])
            loss = torch.mean(((prediction - targets[indices]) * scaled[indices]) ** 2)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += float(loss) * len(indices)
        scheduler.step()
        if epoch == 0 or epoch % 5 == 4:
            model.eval()
            with torch.no_grad():
                predicted = torch.cat([model(local[indices], contexts[indices], mappings[indices]) for indices in torch.arange(split, len(local)).split(128)]).numpy() * scales[split:]
            errors = predicted - targets[split:].numpy() * scales[split:]
            print(epoch + 1, 'loss', total / split, 'time', time.time() - started, 'local RMSE', np.sqrt(np.mean(errors ** 2)) * 1e6, flush=True)
            report(errors.sum(1), data['families'][split:], 'sum error')
            torch.save(model.state_dict(), 'context.pt')
            np.savez('context.npz', **{key: value.detach().numpy() for key, value in model.state_dict().items()})
            np.savez('context_validation.npz', predicted=predicted, truth=targets[split:].numpy() * scales[split:], masks=masks)


if __name__ == '__main__':
    main()
