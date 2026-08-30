import sys

sys.dont_write_bytecode = True

import numpy as np

from contractor import canonicalize, hamiltonian_terms, transfer
from teacher_engine import make_mpo


def state_norm(tensors):
    tensors = [tensor.copy() for tensor in tensors]
    for site in range(len(tensors) - 1):
        left, physical, right = tensors[site].shape
        orthogonal, triangular = np.linalg.qr(tensors[site].reshape(left * physical, right))
        tensors[site] = orthogonal.reshape(left, physical, orthogonal.shape[1])
        tensors[site + 1] = np.tensordot(triangular, tensors[site + 1], axes=(1, 0))
    return float(np.linalg.norm(tensors[-1]))


def residual_norm(tensors, request, energy):
    applied = []
    for tensor, operator in zip(tensors, make_mpo(request)):
        combined = np.einsum("wxpq,aqb->awpbx", operator, tensor, optimize=True)
        applied.append(combined.reshape(tensor.shape[0] * operator.shape[0],
                                        tensor.shape[1], tensor.shape[2] * operator.shape[1]))
    residual = []
    for site, (image, tensor) in enumerate(zip(applied, tensors)):
        if site == 0:
            result = np.concatenate((image, -energy * tensor), axis=2)
        elif site == len(tensors) - 1:
            result = np.concatenate((image, tensor), axis=0)
        else:
            result = np.zeros((image.shape[0] + tensor.shape[0], tensor.shape[1],
                               image.shape[2] + tensor.shape[2]), dtype=np.result_type(image, tensor))
            result[:image.shape[0], :, :image.shape[2]] = image
            result[image.shape[0]:, :, image.shape[2]:] = tensor
        residual.append(result)
    return state_norm(residual)


def schmidt_spectra(tensors):
    tensors = [tensor.copy() for tensor in tensors]
    spectra = []
    for site in range(len(tensors) - 1, 0, -1):
        left, physical, right = tensors[site].shape
        vectors, values, basis = np.linalg.svd(tensors[site].reshape(left, physical * right),
                                              full_matrices=False)
        probabilities = values * values
        probabilities /= probabilities.sum()
        positive = probabilities[probabilities > 0]
        spectra.append({"cut": site, "probabilities": probabilities.tolist(),
                        "entropy": float(-np.sum(positive * np.log(positive))),
                        "tail_after_half": float(probabilities[len(probabilities) // 2:].sum()),
                        "last_two_weight": float(probabilities[-2:].sum())})
        tensors[site] = basis.reshape(len(values), physical, right)
        tensors[site - 1] = np.tensordot(tensors[site - 1], vectors * values, axes=(2, 0))
    return list(reversed(spectra))


def diagnostics(tensors, request, energy):
    tensors = canonicalize(tensors)
    spectra = schmidt_spectra(tensors)
    length = len(tensors)
    rights = [None] * (length + 1)
    rights[length] = np.ones((1, 1))
    for site in range(length - 1, -1, -1):
        rights[site] = np.einsum("apr,bps,rs->ab", tensors[site].conj(), tensors[site],
                                  rights[site + 1], optimize=True)
    edge_operator = np.diag([0.0] * (request["local_dim"] - 2) + [1.0, 1.0])
    left_environment = np.ones((1, 1))
    populations = []
    for site, tensor in enumerate(tensors):
        edge = transfer(left_environment, tensor, edge_operator)
        populations.append(float(np.einsum("ab,ab->", edge, rights[site + 1]).real))
        left_environment = transfer(left_environment, tensor)
    _, positions = hamiltonian_terms(request)
    correlation = np.ones((1, 1))
    selected = (length // 4, 3 * length // 4)
    for site, tensor in enumerate(tensors):
        correlation = transfer(correlation, tensor, positions[site] if site in selected else None)
    residual = residual_norm(tensors, request, energy)
    return {"schmidt": spectra,
            "center_entropy": spectra[length // 2 - 1]["entropy"],
            "max_entropy": max(item["entropy"] for item in spectra),
            "max_schmidt_tail_after_half": max(item["tail_after_half"] for item in spectra),
            "center_last_two_schmidt_weight": spectra[length // 2 - 1]["last_two_weight"],
            "hamiltonian_residual_norm": residual, "energy_variance": residual * residual,
            "site_top_two_population": populations, "max_cutoff_edge_population": max(populations),
            "quarter_chain_phi_phi": float(correlation.item().real),
            "correlation_sites": list(selected)}
