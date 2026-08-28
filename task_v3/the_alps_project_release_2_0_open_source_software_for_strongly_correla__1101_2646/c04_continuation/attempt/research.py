import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import time
import numpy as np
import scipy.linalg as la


def unpack(value):
    return np.asarray(value['real']) + 1j * np.asarray(value['imag'])


def aaa(nodes, values, tolerance=1e-12, maximum=40, paired=False, rowweight=None):
    original_shape = values.shape[1:]
    values = values.reshape(len(nodes), -1)
    if rowweight is None:
        rowweight = np.ones(len(nodes))
    selected = []
    residual = values - np.mean(values, axis=0)
    history = []
    for order in range(maximum):
        errors = la.norm(residual, axis=1)*rowweight
        errors[selected] = -1
        pivot = int(np.argmax(errors))
        selected.append(pivot)
        if paired:
            partner = (pivot + len(nodes)//2) % len(nodes)
            selected.append(partner)
        remaining = np.setdiff1d(np.arange(len(nodes)), selected)
        basis = 1 / (nodes[remaining, None] - nodes[selected][None, :])
        loewner = (values[remaining, :, None] - values[selected].T[None, :, :]) * basis[:, None, :]
        loewner *= rowweight[remaining,None,None]
        loewner = loewner.reshape(-1, len(selected))
        _, singular, right = la.svd(loewner, full_matrices=False, check_finite=False)
        weights = right[-1].conj()
        numerator = basis @ (weights[:, None] * values[selected])
        denominator = basis @ weights
        fit = numerator / denominator[:, None]
        residual = np.zeros_like(values)
        residual[remaining] = values[remaining] - fit
        error = np.max(la.norm(residual, axis=1)*rowweight)
        history.append((nodes[selected].copy(), values[selected].copy(), weights.copy(), error, singular[-1], original_shape))
        if error <= tolerance:
            break
    return history


def evaluate(model, points):
    nodes, values, weights, error, singular, shape = model
    basis = 1 / (points[:, None] - nodes[None, :])
    return ((basis @ (weights[:, None]*values)) / (basis @ weights)[:, None]).reshape((len(points),) + shape)


def poles(model):
    nodes, values, weights, error, singular, shape = model
    matrix = np.zeros((len(nodes)+1, len(nodes)+1), complex)
    matrix[0, 1:] = weights
    matrix[1:, 0] = 1
    matrix[1:, 1:] = np.diag(nodes)
    metric = np.eye(len(nodes)+1)
    metric[0, 0] = 0
    roots = la.eigvals(matrix, metric)
    return roots[np.isfinite(roots)]


def hermitian(matrix):
    return (matrix + matrix.conj().swapaxes(-1, -2))/2


def green_from_spectrum(points, energies, residues):
    return np.einsum('zk,kij->zij', 1/(points[:, None]-energies[None, :]), residues, optimize=True)


def generated(kind, seed=1, dimension=3, error=2e-13, eta=.12):
    rng = np.random.default_rng(seed)
    def random_matrix(size):
        return rng.normal(size=(size,size))+1j*rng.normal(size=(size,size))
    if kind == 'finite':
        total = dimension + 8 + seed % 6
        bare = hermitian(random_matrix(dimension))*.5
        bath = np.linspace(-2.5, 2.5, total-dimension) + rng.normal(size=total-dimension)*.1
        coupling = random_matrix(total)[:dimension, dimension:]*.18
        hamiltonian = np.block([[bare,coupling],[coupling.conj().T,np.diag(bath)]])
        energies, vectors = la.eigh(hamiltonian)
        residues = np.einsum('ik,jk->kij', vectors[:dimension], vectors[:dimension].conj())
    else:
        count = 4096
        phase = np.exp(2j*np.pi*np.arange(count)/count)
        bare = hermitian(random_matrix(dimension))*.5
        if kind == 'band':
            hopping = random_matrix(dimension)*.22 + np.eye(dimension)*.45
            second = random_matrix(dimension)*.025
        elif kind == 'scalarband':
            hopping = hermitian(random_matrix(dimension))*.2 + np.eye(dimension)*.5
            second = np.zeros_like(hopping)
        else:
            hopping = random_matrix(dimension)*.2
            second = random_matrix(dimension)*.12
        hamiltonian = bare[None] + phase[:,None,None]*hopping + phase.conj()[:,None,None]*hopping.conj().T
        hamiltonian += phase[:,None,None]**2*second + phase.conj()[:,None,None]**2*second.conj().T
        energies, vectors = np.linalg.eigh(hamiltonian)
        residues = np.einsum('nik,njk->nkij', vectors, vectors.conj()).reshape(-1,dimension,dimension)/count
        energies = energies.ravel()
    moments = [np.einsum('k,kij->ij', energies**order, residues) for order in range(3)]
    iw = np.unique(np.r_[np.pi/30*(2*np.arange(60)+1), np.geomspace(13,230,52)])
    omega = np.linspace(min(energies)-.6, max(energies)+.6,241)
    data = green_from_spectrum(1j*iw, energies, residues)
    data += error*.15*(rng.uniform(-1,1,size=data.shape)+1j*rng.uniform(-1,1,size=data.shape))
    target = green_from_spectrum(omega+1j*eta, energies, residues)
    return dict(iw=iw, data=data, moments=moments, bare=bare, omega=omega, eta=eta, support=[min(energies)-.15,max(energies)+.15], error=error, target=target)


def metrics(prediction, case):
    target = case['target']
    points = case['omega']+1j*case['eta']
    dimension = len(case['bare'])
    sigma_target = points[:,None,None]*np.eye(dimension)-case['bare']-np.linalg.inv(target)
    sigma_prediction = points[:,None,None]*np.eye(dimension)-case['bare']-np.linalg.inv(prediction)
    spectral = -(prediction-prediction.conj().swapaxes(-1,-2))/(2j)
    negativity = np.min(np.linalg.eigvalsh(spectral))
    return [la.norm(prediction-target)/la.norm(target), la.norm(sigma_prediction-sigma_target)/max(la.norm(sigma_target),1e-10),negativity]


def benchmark():
    for kind in ['finite','scalarband','band','band2']:
        case = generated(kind)
        print('\n',kind, flush=True)
        for paired in [False,True]:
            nodes = 1j*case['iw']
            values = case['data']
            if paired:
                nodes = np.r_[nodes,nodes.conj()]
                values = np.concatenate([values,values.conj().swapaxes(-1,-2)])
            history = aaa(nodes,values,tolerance=1e-12,maximum=28,paired=paired)
            for model in history:
                if len(model[0]) < 6:
                    continue
                prediction = evaluate(model,case['omega']+1j*case['eta'])
                print(paired,len(model[0]), 'fit %.2g'%model[3], 'metrics', ['%.3g'%value for value in metrics(prediction,case)], 'poles', np.round(poles(model),3) if model is history[-1] else '', flush=True)


if __name__ == '__main__':
    benchmark()
