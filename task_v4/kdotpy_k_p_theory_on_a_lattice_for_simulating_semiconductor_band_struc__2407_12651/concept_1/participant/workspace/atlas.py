import json
from pathlib import Path

import numpy as np


def wrap_phase(value):
    return (value + np.pi) % (2 * np.pi) - np.pi


def orthonormalize(frames):
    gram = frames.conj().swapaxes(-1, -2) @ frames
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    if np.any(eigenvalues < 1e-12):
        raise ValueError('rank-deficient input frame')
    inverse_root = (eigenvectors / np.sqrt(eigenvalues)[..., None, :]) @ eigenvectors.conj().swapaxes(-1, -2)
    return frames @ inverse_root


def torus(nx, ny):
    vertex = np.arange(nx * ny)
    right = (vertex // nx) * nx + (vertex % nx + 1) % nx
    up = ((vertex // nx + 1) % ny) * nx + vertex % nx
    edges = np.stack((np.repeat(vertex, 2), np.stack((right, up), axis=1).ravel()), axis=1)
    plaquettes = np.stack((vertex, right, up[right], up), axis=1)
    return edges, plaquettes


class Atlas:
    def __init__(self, metadata, arrays):
        self.metadata = metadata
        self.frames = np.asarray(arrays['frames'], dtype=np.complex128)
        self.energies = np.asarray(arrays['energies'], dtype=float)
        self.costs = np.asarray(arrays['costs'], dtype=np.int64)
        self.scenarios, self.vertices, self.candidates, self.dimension, self.rank = self.frames.shape
        self.edges, self.plaquettes = torus(metadata['nx'], metadata['ny'])
        if self.rank != 2 or self.vertices != metadata['nx'] * metadata['ny']:
            raise ValueError('inconsistent rank or torus size')
        self.budget = int(metadata['budget'])
        self.seed = np.asarray(arrays['seed_choices'], dtype=np.int64)
        self.anchors = {int(vertex): int(choice) for vertex, choice in metadata['anchors'].items()}
        self.normalizers = np.array([row['normalizer'] for row in metadata['scenarios']])
        self.weights = np.array([row['weight'] for row in metadata['scenarios']])
        self.targets = np.array([row['target_chern'] for row in metadata['scenarios']])
        self.loss_weights = np.array([row['loss_weights'] for row in metadata['scenarios']])
        self.mean_weight = float(metadata['lambda_mean'])
        self.minimum_link = float(metadata['minimum_link'])
        self.branch_margin = float(metadata['branch_margin'])
        self.chern_tolerance = float(metadata['chern_tolerance'])
        if not np.all(np.isfinite(self.frames)) or np.any(self.normalizers <= 0):
            raise ValueError('invalid numerical input')
        self.bases = orthonormalize(self.frames)
        source, destination = self.edges.T
        products = np.einsum('seadi,sebdj->seabij', self.bases[:, source].conj(), self.bases[:, destination], optimize=True)
        determinants = np.linalg.det(products)
        self.link_magnitude = np.abs(determinants)
        overlap = -np.log(np.maximum(self.link_magnitude ** 2, 1e-30))
        dispersion = np.mean((self.energies[:, source, :, None] - self.energies[:, destination, None, :]) ** 2, axis=-1)
        unary = np.mean((self.energies - np.asarray(arrays['guide'])[:, :, None]) ** 2, axis=-1)
        horizontal = np.angle(determinants[:, 0::2])
        vertical = np.angle(determinants[:, 1::2])
        right, up = self.plaquettes[:, 1], self.plaquettes[:, 3]
        self.flux = wrap_phase(horizontal[:, :, :, :, None, None]
                               + vertical[:, right][:, :, None, :, :, None]
                               - horizontal[:, up].swapaxes(-1, -2)[:, :, None, None, :, :]
                               - vertical[:, :, :, None, None, :])
        flux_error = wrap_phase(self.flux - np.asarray(arrays['target_flux'])[:, :, None, None, None, None]) ** 2
        self.unary = self.loss_weights[:, 0, None, None] * unary
        self.pair = self.loss_weights[:, 1, None, None, None] * overlap + self.loss_weights[:, 2, None, None, None] * dispersion
        self.face = self.loss_weights[:, 3, None, None, None, None, None] * flux_error

    @classmethod
    def load(cls, directory):
        directory = Path(directory)
        metadata = json.loads((directory / 'case.json').read_text())
        with np.load(directory / 'arrays.npz', allow_pickle=False) as archive:
            arrays = {name: archive[name] for name in archive.files}
        return cls(metadata, arrays)

    def evaluate_many(self, choices):
        choices = np.asarray(choices)
        if choices.ndim != 2 or choices.shape[1] != self.vertices or choices.dtype.kind not in 'iu':
            raise ValueError('choices must be a batch of integer vectors')
        if np.any(choices < 0) or np.any(choices >= self.candidates):
            raise ValueError('candidate out of range')
        vertices = np.arange(self.vertices)
        edge_indices = np.arange(len(self.edges))
        source, destination = self.edges.T
        selected_flux = self.flux[:, vertices, choices[:, self.plaquettes[:, 0]], choices[:, self.plaquettes[:, 1]], choices[:, self.plaquettes[:, 2]], choices[:, self.plaquettes[:, 3]]]
        losses = self.unary[:, vertices, choices].sum(axis=-1)
        losses += self.pair[:, edge_indices, choices[:, source], choices[:, destination]].sum(axis=-1)
        losses += self.face[:, vertices, choices[:, self.plaquettes[:, 0]], choices[:, self.plaquettes[:, 1]], choices[:, self.plaquettes[:, 2]], choices[:, self.plaquettes[:, 3]]].sum(axis=-1)
        normalized = losses / self.normalizers[:, None]
        objective = normalized.max(axis=0) + self.mean_weight * (self.weights @ normalized) / self.weights.sum()
        chern = selected_flux.sum(axis=-1) / (2 * np.pi)
        cost = self.costs[vertices, choices].sum(axis=-1)
        link_min = self.link_magnitude[:, edge_indices, choices[:, source], choices[:, destination]].min(axis=(0, 2))
        margin = np.pi - np.abs(selected_flux).max(axis=(0, 2))
        topology_error = np.abs(chern - self.targets[:, None]).max(axis=0)
        feasible = (cost <= self.budget) & (topology_error <= self.chern_tolerance) & (link_min >= self.minimum_link) & (margin >= self.branch_margin)
        for vertex, choice in self.anchors.items():
            feasible &= choices[:, vertex] == choice
        return {'objective': objective, 'raw_loss': losses.T, 'normalized_loss': normalized.T,
                'chern': chern.T, 'cost': cost, 'minimum_link': link_min,
                'branch_margin': margin, 'topology_error': topology_error, 'feasible': feasible}

    def score(self, choices):
        result = self.evaluate_many(np.asarray(choices, dtype=np.int64)[None])
        return {key: value[0].tolist() for key, value in result.items()}


def single_descent(atlas, initial):
    choices = np.array(initial, dtype=np.int64).copy()
    current = atlas.score(choices)
    if not current['feasible']:
        raise ValueError('descent requires a feasible start')
    vertices = np.array([vertex for vertex in range(atlas.vertices) if vertex not in atlas.anchors])
    move_vertices = np.repeat(vertices, atlas.candidates)
    move_choices = np.tile(np.arange(atlas.candidates), len(vertices))
    for iteration in range(4 * atlas.vertices):
        neighbors = np.tile(choices, (len(move_vertices), 1))
        neighbors[np.arange(len(neighbors)), move_vertices] = move_choices
        values = atlas.evaluate_many(neighbors)
        objective = np.where(values['feasible'], values['objective'], np.inf)
        selected = int(np.argmin(objective))
        if objective[selected] >= current['objective'] - 1e-12:
            break
        choices = neighbors[selected].copy()
        current = atlas.score(choices)
    return choices
