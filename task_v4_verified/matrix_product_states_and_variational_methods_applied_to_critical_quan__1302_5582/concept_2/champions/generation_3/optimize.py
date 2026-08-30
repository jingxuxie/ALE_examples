import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import argparse
import json
import sys
import time
from pathlib import Path
import numpy as np
import scipy.optimize as so
import torch

ASSETS = Path(os.environ.get('ASSETS', '../../participant'))
sys.path.insert(0, str(ASSETS / 'workspace'))
from physics import exact_order, exact_density, exact_composite_covariance, COMPOSITE_QUARTETS

torch.set_num_threads(1)
torch.set_default_dtype(torch.float64)


def sector_basis(dimension, parity, antisymmetric=False):
    rows, columns = [], []
    for row in range(dimension):
        for column in range(row, dimension):
            if ((row < dimension // 2) == (column < dimension // 2)) == (parity == 0):
                if not antisymmetric or row != column:
                    rows.append(row)
                    columns.append(column)
    norms = np.where(np.array(rows) == np.array(columns), 1.0, np.sqrt(2.0))
    basis = np.zeros((len(rows), dimension, dimension))
    for index, (row, column) in enumerate(zip(rows, columns)):
        basis[index, row, column] = 1.0 / norms[index]
        basis[index, column, row] = (-1.0 if antisymmetric else 1.0) / norms[index]
    return torch.tensor(basis), torch.tensor(rows), torch.tensor(columns), torch.tensor(norms)


class Witness:
    def __init__(self, initial, full=False):
        self.dimension = initial.shape[1]
        self.half = self.dimension // 2
        self.even = sector_basis(self.dimension, 0)
        self.odd = sector_basis(self.dimension, 1)
        self.anti = sector_basis(self.dimension, 1, True)
        self.identity = torch.eye(self.dimension)
        self.unit = self.pack(self.identity, self.even)
        self.eye_even = torch.eye(len(self.unit))
        self.lengths = np.array([16, 32, 64, 96])
        self.specs = np.array([(self.lengths.tolist().index(second-first), third-second,
                                self.lengths.tolist().index(fourth-third))
                              for first, second, third, fourth in COMPOSITE_QUARTETS])
        self.samples = []
        for maximum, count in [(1024, 100), (256, 80), (128, 70)]:
            if full:
                distances = np.arange(1, maximum+1)
            else:
                distances = np.unique(np.r_[np.arange(1, 17), np.rint(np.geomspace(1, maximum, count)), self.lengths]).astype(int)
            self.samples.append(distances)
        self.targets = [torch.tensor([exact_order(int(distance)) for distance in self.samples[0]]),
                        torch.tensor([exact_density(int(distance)) for distance in self.samples[1]]),
                        torch.tensor([-exact_order(int(distance))/(4*distance*distance-1) for distance in self.samples[2]]),
                        torch.tensor([exact_composite_covariance(quartet) for quartet in COMPOSITE_QUARTETS])]
        self.initial = self.encode(initial)

    def encode(self, tensor):
        half = self.half
        return np.stack([np.concatenate([tensor[0,:half,:half], tensor[1,:half,half:]],axis=1),
                         np.concatenate([tensor[1,half:,:half], tensor[0,half:,half:]],axis=1)])

    def canonical(self, parameters):
        half = self.half
        rows = parameters.reshape(2, half, 2*half)
        orthogonal, triangular = torch.linalg.qr(rows.transpose(1,2), mode='reduced')
        signs = torch.sign(torch.diagonal(triangular, dim1=1, dim2=2))
        rows = (orthogonal * signs[:,None,:]).transpose(1,2)
        zero = torch.zeros((half,half))
        first = torch.cat([torch.cat([rows[0,:,:half],zero],1),torch.cat([zero,rows[1,:,half:]],1)],0)
        second = torch.cat([torch.cat([zero,rows[0,:,half:]],1),torch.cat([rows[1,:,:half],zero],1)],0)
        return torch.stack([first,second])

    @staticmethod
    def pack(matrices, sector):
        unused_basis, rows, columns, norms = sector
        return matrices[...,rows,columns] * norms

    def mapped(self, tensor, source, destination, operator='I'):
        basis = source[0]
        first, second = tensor
        if operator == 'I':
            mapped = first @ basis @ first.T + second @ basis @ second.T
        elif operator == 'Z':
            mapped = first @ basis @ first.T - second @ basis @ second.T
        elif operator == 'X':
            mapped = first @ basis @ second.T + second @ basis @ first.T
        else:
            mapped = -first @ basis @ second.T + second @ basis @ first.T
        return self.pack(mapped,destination).T

    @staticmethod
    def powers(transfer, maximum):
        result = [transfer]
        while 2**len(result) <= maximum:
            result.append(result[-1] @ result[-1])
        return result

    @staticmethod
    def propagate(powers, vectors, exponents, left=False):
        exponents = np.asarray(exponents)
        result = vectors.expand(len(exponents),-1) if vectors.ndim == 1 else vectors
        for index, power in enumerate(powers):
            indices = np.flatnonzero((exponents >> index) & 1)
            if len(indices):
                indices = torch.tensor(indices)
                updated = result[indices] @ (power if left else power.T)
                result = result.index_copy(0, indices, updated)
        return result

    def evaluate(self, parameters):
        tensor = self.canonical(parameters)
        first, second = tensor
        even_transfer = self.mapped(tensor,self.even,self.even)
        odd_transfer = self.mapped(tensor,self.odd,self.odd)
        anti_transfer = self.mapped(tensor,self.anti,self.anti)
        density = torch.linalg.solve(self.eye_even-even_transfer.T+torch.outer(self.unit,self.unit),self.unit)
        x_to_even = self.mapped(tensor,self.odd,self.even,'X')
        x_from_even = self.mapped(tensor,self.even,self.odd,'X')
        z_transfer = self.mapped(tensor,self.even,self.even,'Z')
        y_to_even = self.mapped(tensor,self.anti,self.even,'Y')
        x_right = x_from_even @ self.unit
        z_right = z_transfer @ self.unit
        y_right = self.pack(first@second.T-second@first.T,self.anti)
        x_left = density @ x_to_even
        z_left = density @ z_transfer
        y_left = density @ y_to_even
        magnetization = density @ z_right
        even_powers = self.powers(even_transfer,255)
        odd_powers = self.powers(odd_transfer,1023)
        anti_powers = self.powers(anti_transfer,127)
        order = self.propagate(odd_powers,x_right,self.samples[0]-1) @ x_left
        connected_density = self.propagate(even_powers,z_right-magnetization*self.unit,self.samples[1]-1) @ z_left
        y_values = self.propagate(anti_powers,y_right,self.samples[2]-1) @ y_left
        interval_right = self.propagate(odd_powers,x_right,self.lengths-1) @ x_to_even.T
        means = interval_right @ density
        centered = interval_right - means[:,None]*self.unit
        interval_left = self.propagate(odd_powers,x_left,self.lengths-1,left=True) @ x_from_even
        gaps = self.specs[:,1]-1
        propagated = self.propagate(even_powers,centered[self.specs[:,2]],gaps)
        covariances = (interval_left[self.specs[:,0]]*propagated).sum(1)
        energy = -(magnetization+order[0])+4/np.pi
        errors = [(values-target)/target for values,target in zip([order,connected_density,y_values,covariances],self.targets)]
        return energy, errors, tensor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input',default=str(ASSETS/'baseline/state.npz'))
    parser.add_argument('--prefix',default='run1')
    parser.add_argument('--seconds',type=float,default=900)
    parser.add_argument('--iterations',type=int,default=10000)
    parser.add_argument('--energy-scale',type=float,default=3e-5)
    parser.add_argument('--composite-scale',type=float,default=.007)
    parser.add_argument('--mode',choices=['balanced','hinge','composite'],default='balanced')
    parser.add_argument('--check',action='store_true')
    arguments = parser.parse_args()
    initial = np.load(arguments.input)['A'].real
    witness = Witness(initial)
    parameters = torch.tensor(witness.initial,requires_grad=True)
    started = time.monotonic()
    best = [float('inf')]
    calls = [0]
    best_loss = [float('inf')]

    def objective(flat):
        parameters = torch.tensor(flat.reshape(witness.initial.shape),requires_grad=True)
        energy, errors, tensor = witness.evaluate(parameters)
        scales = [.018,.075,.075,arguments.composite_scale]
        if arguments.mode == 'balanced':
            loss = (energy/arguments.energy_scale)**2
            for error,scale in zip(errors,scales):
                loss = loss + ((error/scale)**2).mean()
        else:
            loss = torch.relu(energy/arguments.energy_scale-1)**2
            for error,scale in zip(errors[:3],scales[:3]):
                loss = loss + 5*torch.relu(torch.abs(error)/scale-1).square().mean()
            loss = loss + (errors[3]/scales[3]).square().mean()
        loss.backward()
        calls[0] += 1
        maxima = np.array([float(error.detach().abs().max()) for error in errors])
        excess = float(energy.detach())
        ratios = np.r_[excess/5e-5,maxima/np.array([.025,.1,.1,.01])]
        score = np.maximum(1,ratios).prod()
        if score < best[0] and excess >= -5e-9:
            best[0] = score
            np.savez(arguments.prefix+'_best.npz',A=tensor.detach().numpy())
            np.savez('state.npz',A=tensor.detach().numpy())
        if float(loss.detach()) < best_loss[0]:
            best_loss[0] = float(loss.detach())
            np.savez(arguments.prefix+'_loss.npz',A=tensor.detach().numpy())
        if calls[0] % 25 == 1:
            print(json.dumps(dict(call=calls[0],seconds=round(time.monotonic()-started,2),loss=float(loss.detach()),energy=excess,maxima=maxima.tolist(),score=score,best=best[0])),flush=True)
        if time.monotonic()-started > arguments.seconds:
            raise TimeoutError
        return float(loss.detach()),parameters.grad.detach().numpy().reshape(-1)

    if arguments.check:
        energy, errors,tensor = witness.evaluate(parameters)
        print('energy',float(energy),'maxima',[float(error.abs().max()) for error in errors])
        objective(witness.initial.reshape(-1))
        direction = np.random.default_rng(41).normal(size=witness.initial.size)
        direction /= np.linalg.norm(direction)
        value,gradient = objective(witness.initial.reshape(-1))
        for epsilon in [1e-5,1e-6,1e-7]:
            plus = objective(witness.initial.reshape(-1)+epsilon*direction)[0]
            minus = objective(witness.initial.reshape(-1)-epsilon*direction)[0]
            print('gradcheck',epsilon,(plus-minus)/(2*epsilon),gradient@direction,flush=True)
        return
    try:
        result = so.minimize(objective,witness.initial.reshape(-1),method='L-BFGS-B',jac=True,
                             options=dict(maxiter=arguments.iterations,maxls=40,maxcor=100,ftol=1e-14,gtol=1e-8))
        final = witness.canonical(torch.tensor(result.x.reshape(witness.initial.shape))).numpy()
        np.savez(arguments.prefix+'_final.npz',A=final)
        print(result.message,flush=True)
    except TimeoutError:
        print('Time budget completed.',flush=True)


if __name__ == '__main__':
    main()
