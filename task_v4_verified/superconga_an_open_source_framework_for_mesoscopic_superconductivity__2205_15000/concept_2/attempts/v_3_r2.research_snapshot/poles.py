import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'

import numpy as np
from scipy.linalg import svd, eig
from scipy.optimize import least_squares

from optimize import Model, OUTPUT


def aaa(nodes, values):
    available = np.ones(len(nodes), dtype=bool)
    selected = []
    approximation = np.mean(values, axis=1, keepdims=True)*np.ones((1, len(nodes)))
    for iteration in range(70):
        residual = np.sum((values-approximation)**2, axis=0)
        residual[~available] = -1
        index = np.argmax(residual)
        selected.append(index)
        available[index] = False
        supports = nodes[selected]
        coefficients = 1/(nodes[available, None]-supports[None, :])
        loewner = (values[:, available, None]-values[:, None, selected])*coefficients[None]
        _, singular, right = svd(loewner.reshape(-1,len(selected)), full_matrices=False)
        weights = right[-1]
        approximation[:, available] = ((coefficients*weights[None, :]) @ values[:, selected].T).T / (coefficients @ weights)[None, :]
        approximation[:, selected] = values[:, selected]
        error = np.max(np.abs(approximation-values))
        if iteration%10==0:
            print('AAA',iteration,error,flush=True)
        if error < 5e-13:
            break
    pencil = np.zeros((len(selected)+1,len(selected)+1))
    pencil[0,1:] = weights
    pencil[1:,0] = 1
    pencil[1:,1:] = np.diag(supports)
    denominator = np.eye(len(selected)+1)
    denominator[0,0] = 0
    roots = eig(pencil,denominator,right=False)
    return roots[np.isfinite(roots)]


def fit_poles(model):
    eigenvalues = []
    spectral_weights = []
    for condition_index in range(3):
        roots = aaa(model.energies, model.target[condition_index]/model.scale[condition_index])
        nearby = roots[(roots.real>0)&(roots.real<.4)&(roots.imag>0)]
        print('roots',condition_index,sorted(nearby,key=lambda root:root.real),flush=True)
        positive = np.sort(nearby.real[np.abs(nearby.imag-.01)<.0001])
        positive = positive[positive<.31]
        polynomial = np.polynomial.chebyshev.chebvander(model.energies/.3,24)
        observed = model.target[condition_index].T

        def basis(values):
            signed = np.concatenate([-values[::-1],values])
            lorentzian = .01/np.pi / ((model.energies[:,None]-signed[None])**2+.01**2)
            return np.concatenate([lorentzian,polynomial],axis=1)

        def residual(values):
            matrix = basis(values)
            weights = np.linalg.lstsq(matrix,observed,rcond=1e-13)[0]
            return ((matrix@weights-observed)/model.scale[condition_index].T).ravel()

        fitted = least_squares(residual,positive,xtol=1e-14,ftol=1e-14,gtol=1e-14,max_nfev=100)
        weights = np.linalg.lstsq(basis(fitted.x),observed,rcond=1e-13)[0][:2*len(positive)].T
        print('FITTED',condition_index,'poles',fitted.x,'error',np.sqrt(np.mean(fitted.fun**2)),'minweight',weights.min(),flush=True)
        eigenvalues.append(fitted.x)
        spectral_weights.append(weights)
    np.savez(OUTPUT/'poles.npz',**{f'values_{index}':values for index,values in enumerate(eigenvalues)},**{f'weights_{index}':weights for index,weights in enumerate(spectral_weights)})


if __name__=='__main__':
    fit_poles(Model())
