import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import json
import sys
import time
from pathlib import Path
import numpy as np
import scipy.optimize
import torch

torch.set_num_threads(1)
torch.set_default_dtype(torch.float64)
ASSETS = Path(__file__).resolve().parents[2] / 'participant'
sys.path.insert(0, str(ASSETS / 'workspace'))
import physics


def symmetric_basis(dimension, parity, skew=False):
    rows, columns = np.triu_indices(dimension, 1 if skew else 0)
    mask = ((rows < dimension // 2) == (columns < dimension // 2)) == (parity == 0)
    rows, columns = rows[mask], columns[mask]
    basis = np.zeros((len(rows), dimension, dimension))
    weights = np.where(rows == columns, 1., np.sqrt(2.))
    for index, (row, column, weight) in enumerate(zip(rows, columns, weights)):
        basis[index, row, column] = 1 / weight
        basis[index, column, row] = (-1 if skew else 1) / weight
    return torch.tensor(basis), rows, columns, torch.tensor(weights)


class Observables:
    def __init__(self, dimension=24, full=False):
        self.dimension = dimension
        self.half = dimension // 2
        self.even = symmetric_basis(dimension, 0)
        self.odd = symmetric_basis(dimension, 1)
        self.skew = symmetric_basis(dimension, 1, True)
        self.identity = self.project(torch.eye(dimension)[None], self.even)[:, 0]
        self.unit = torch.eye(len(self.identity))
        self.quartets = physics.COMPOSITE_QUARTETS
        self.sextuples = physics.THREE_INTERVAL_SEXTUPLES
        self.lengths = [16, 32, 64, 96]
        self.gaps = [32, 64, 96, 128]
        self.quartet_index = tuple(torch.tensor(values) for values in zip(*[
            (self.lengths.index(second-first), self.gaps.index(third-second), self.lengths.index(fourth-third))
            for first, second, third, fourth in self.quartets]))
        self.sextuple_index = tuple(torch.tensor(values) for values in zip(*[
            (self.lengths.index(second-first), self.gaps.index(third-second), self.lengths.index(fourth-third),
             self.gaps.index(fifth-fourth), self.lengths.index(sixth-fifth))
            for first, second, third, fourth, fifth, sixth in self.sextuples]))
        self.distances = []
        for maximum in (1024, 256, 128):
            distances = np.arange(1, maximum+1) if full else np.unique(np.r_[np.arange(1,17), np.round(np.geomspace(17,maximum,65)), maximum]) .astype(int)
            self.distances.append(distances)
        self.targets = [torch.tensor([physics.exact_order(int(distance)) for distance in self.distances[0]]),
                        torch.tensor(4/(np.pi**2*(4*self.distances[1]**2-1))),
                        torch.tensor([-physics.exact_order(int(distance))/(4*distance**2-1) for distance in self.distances[2]]),
                        torch.tensor([physics.exact_composite_covariance(sites) for sites in self.quartets]),
                        torch.tensor([physics.exact_three_interval_cumulant(sites) for sites in self.sextuples])]
        self.tolerances = [.025, .1, .1, .01, .1]

    @staticmethod
    def project(matrices, basis):
        unused_basis, rows, columns, weights = basis
        return (matrices[:, rows, columns] * weights).T

    def pack(self, tensor):
        half = self.half
        return np.stack([np.concatenate([tensor[0,:half,:half], tensor[1,:half,half:]], axis=1),
                         np.concatenate([tensor[0,half:,half:], tensor[1,half:,:half]], axis=1)])

    def tensor(self, parameters):
        blocks = parameters.reshape(2,self.half,self.dimension)
        lower = torch.linalg.cholesky(blocks @ blocks.transpose(1,2))
        blocks = torch.linalg.solve_triangular(lower, blocks, upper=False)
        zeros = torch.zeros((self.half,self.half))
        first = torch.cat([torch.cat([blocks[0,:,:self.half],zeros],1), torch.cat([zeros,blocks[1,:,:self.half]],1)],0)
        second = torch.cat([torch.cat([zeros,blocks[0,:,self.half:]],1), torch.cat([blocks[1,:,self.half:],zeros],1)],0)
        return torch.stack([first,second])

    @staticmethod
    def powers(matrix, maximum=1024):
        result = [matrix]
        while 2**len(result) <= maximum:
            result.append(result[-1] @ result[-1])
        return result

    @staticmethod
    def power(power_list, exponent):
        result = torch.eye(power_list[0].shape[0])
        for bit, matrix in enumerate(power_list):
            if exponent & (1 << bit):
                result = matrix @ result
        return result

    @staticmethod
    def propagate(power_list, vector, exponents):
        result = vector[:,None].expand(-1,len(exponents))
        for bit, matrix in enumerate(power_list):
            mask = torch.tensor((np.asarray(exponents) & (1 << bit)) != 0)
            if mask.any():
                result = torch.where(mask[None,:], matrix @ result, result)
        return result

    def evaluate(self, parameters, details=False):
        tensor = self.tensor(parameters)
        first, second = tensor.unbind()
        even_basis, odd_basis, skew_basis = self.even[0], self.odd[0], self.skew[0]
        even_first = first @ even_basis
        even_second = second @ even_basis
        first_first = even_first @ first.T
        second_second = even_second @ second.T
        even_transfer = self.project(first_first+second_second,self.even)
        density_map = self.project(first_first-second_second,self.even)
        first_second = even_first @ second.T
        second_first = even_second @ first.T
        order_right = self.project(first_second+second_first,self.odd)
        y_right = self.project(first_second-second_first,self.skew)
        odd_first = first @ odd_basis
        odd_second = second @ odd_basis
        odd_transfer = self.project(odd_first @ first.T + odd_second @ second.T,self.odd)
        order_left = self.project(odd_first @ second.T + odd_second @ first.T,self.even)
        skew_first = first @ skew_basis
        skew_second = second @ skew_basis
        skew_transfer = self.project(skew_first @ first.T + skew_second @ second.T,self.skew)
        y_left = self.project(skew_first @ second.T - skew_second @ first.T,self.even)
        identity = self.identity
        density = torch.linalg.solve(self.unit-even_transfer.T+torch.outer(identity,identity)/self.dimension, identity/self.dimension)
        mean_z = density @ density_map @ identity
        even_powers = self.powers(even_transfer,256)
        odd_powers = self.powers(odd_transfer,1024)
        skew_powers = self.powers(skew_transfer,128)
        order = (density @ order_left) @ self.propagate(odd_powers, order_right @ identity,self.distances[0]-1)
        connected = (density @ density_map - mean_z*density) @ self.propagate(even_powers,density_map @ identity - mean_z*identity,self.distances[1]-1)
        y_spin = -(density @ y_left) @ self.propagate(skew_powers,y_right @ identity,self.distances[2]-1)
        energy = -mean_z-order[0]
        pair_maps = torch.stack([order_left @ self.power(odd_powers,length-1) @ order_right for length in self.lengths])
        pair_right = pair_maps @ identity
        pair_means = pair_right @ density
        pair_left = density @ pair_maps
        right_centered = pair_right-pair_means[:,None]*identity
        left_centered = pair_left-pair_means[:,None]*density
        gap_maps = torch.stack([self.power(even_powers,gap-1) for gap in self.gaps])
        right_gap = gap_maps @ right_centered.T
        left_gap = left_centered @ gap_maps
        covariance = (left_centered @ right_gap).permute(1,0,2)[self.quartet_index]
        center_maps = pair_maps-pair_means[:,None,None]*torch.stack([self.power(even_powers,length+1) for length in self.lengths])
        middle_right = center_maps @ right_gap.permute(1,0,2).reshape(len(identity),-1)
        cumulants = (left_gap.reshape(-1,len(identity)) @ middle_right.permute(1,0,2).reshape(len(identity),-1)).reshape(4,4,4,4,4).permute(1,0,2,3,4)[self.sextuple_index]
        values = [order,connected,y_spin,covariance,cumulants]
        errors = [(value/target-1)/tolerance for value,target,tolerance in zip(values,self.targets,self.tolerances)]
        energy_error = (energy+4/np.pi)/5e-5
        if details:
            return tensor,energy,values,errors,density
        return energy_error,errors


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',default='state.npz')
    parser.add_argument('--iterations',type=int,default=1000)
    parser.add_argument('--mode',default='mean')
    parser.add_argument('--prefix',default='run')
    parser.add_argument('--full',action='store_true')
    parser.add_argument('--check',action='store_true')
    arguments=parser.parse_args()
    model=Observables(full=arguments.full)
    initial=np.load(arguments.input)['A'].real
    initial_parameters=model.pack(initial).reshape(-1)
    started=time.monotonic()
    calls=0
    best=float('inf')
    log=open(arguments.prefix+'.jsonl','a',buffering=1)
    def objective(array):
        nonlocal calls,best
        parameters=torch.tensor(array,requires_grad=True)
        energy_error,errors=model.evaluate(parameters)
        if arguments.mode == 'hinge':
            loss=4*torch.relu(energy_error-.8)**2
            for error in errors:
                loss=loss+torch.mean(torch.relu(abs(error)-.7)**2)+.05*torch.mean(error**2)
        elif arguments.mode == 'max':
            loss=.3*energy_error**2+2*torch.relu(energy_error-.7)**2
            for error in errors:
                loss=loss+torch.mean(error**2)+.2*torch.mean(error**8)**.25
        else:
            loss=.2*energy_error**2+10*torch.relu(energy_error-.85)**2
            for error in errors:
                loss=loss+torch.mean(error**2)
        loss.backward()
        calls+=1
        maxima=[float(abs(error).max()) for error in errors]
        worst=max(float(energy_error),*maxima)
        if worst < best:
            best=worst
            np.savez(arguments.prefix+'_best.npz',A=model.tensor(parameters).detach().numpy())
        if calls%10==1 or arguments.check:
            record=dict(calls=calls,seconds=time.monotonic()-started,loss=float(loss),energy=float(energy_error),errors=maxima,worst=worst,best=best)
            print(record,flush=True)
            log.write(json.dumps(record)+'\n')
            np.savez(arguments.prefix+'_latest.npz',A=model.tensor(parameters).detach().numpy())
        return float(loss),parameters.grad.numpy().copy()
    if arguments.check:
        objective(initial_parameters)
        with torch.no_grad():
            tensor,energy,values,errors,density=model.evaluate(torch.tensor(initial_parameters),True)
            np.savez(arguments.prefix+'_observables.npz',energy=float(energy),order=values[0].numpy(),density=values[1].numpy(),y=values[2].numpy(),covariance=values[3].numpy(),cumulants=values[4].numpy())
    else:
        result=scipy.optimize.minimize(objective,initial_parameters,jac=True,method='L-BFGS-B',options=dict(maxiter=arguments.iterations,maxls=30,maxcor=50,ftol=1e-14,gtol=1e-9))
        print(result.message,flush=True)
        np.savez(arguments.prefix+'_final.npz',A=model.tensor(torch.tensor(result.x)).detach().numpy())


if __name__=='__main__':
    main()
