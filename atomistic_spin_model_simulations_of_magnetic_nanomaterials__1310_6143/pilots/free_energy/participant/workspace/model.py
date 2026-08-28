import math
import numpy as np


def adjacency(case):
    neighbors = [[] for _ in range(case["n_spins"])]
    for first, second, exchange, axial in case["bonds"]:
        neighbors[first].append((second, exchange, axial))
        neighbors[second].append((first, exchange, axial))
    return neighbors


def local_energy(case, spins, index, neighbors):
    spin = spins[index]
    tensor = case["onsite"][index]
    energy = -sum(tensor[axis]*spin[axis]**2 for axis in range(3))
    energy -= 2*(tensor[3]*spin[0]*spin[1]+tensor[4]*spin[0]*spin[2]+tensor[5]*spin[1]*spin[2])
    energy -= tensor[6]*sum(value**4 for value in spin)
    for other, exchange, axial in neighbors[index]:
        energy -= exchange*np.dot(spin,spins[other])+axial*spin[2]*spins[other,2]
    return float(energy)


def energy_and_torque(case, spins):
    tensors = np.asarray(case["onsite"],dtype=float)
    onsite_energy = -(tensors[:,:3]*spins**2).sum()
    onsite_energy -= 2*np.sum(tensors[:,3]*spins[:,0]*spins[:,1]+tensors[:,4]*spins[:,0]*spins[:,2]+tensors[:,5]*spins[:,1]*spins[:,2])
    onsite_energy -= np.sum(tensors[:,6,None]*spins**4)
    fields = 2*tensors[:,:3]*spins + 4*tensors[:,6,None]*spins**3
    fields[:,0] += 2*(tensors[:,3]*spins[:,1]+tensors[:,4]*spins[:,2])
    fields[:,1] += 2*(tensors[:,3]*spins[:,0]+tensors[:,5]*spins[:,2])
    fields[:,2] += 2*(tensors[:,4]*spins[:,0]+tensors[:,5]*spins[:,1])
    energy = onsite_energy
    for first, second, exchange, axial in case["bonds"]:
        energy -= exchange*np.dot(spins[first],spins[second])+axial*spins[first,2]*spins[second,2]
        fields[first] += exchange*spins[second]
        fields[second] += exchange*spins[first]
        fields[first,2] += axial*spins[second,2]
        fields[second,2] += axial*spins[first,2]
    return float(energy),float(np.cross(spins,fields)[:,1].sum())


def unconstrained_metropolis(case, sweeps=20, seed=None):
    random = np.random.default_rng(case["seed"] if seed is None else seed)
    spins = np.zeros((case["n_spins"],3))
    spins[:,2] = 1.0
    neighbors = adjacency(case)
    for _ in range(sweeps*case["n_spins"]):
        index = int(random.integers(case["n_spins"]))
        previous = spins[index].copy()
        previous_energy = local_energy(case,spins,index,neighbors)
        proposed = previous+0.3*random.normal(size=3)
        spins[index] = proposed/np.linalg.norm(proposed)
        change = local_energy(case,spins,index,neighbors)-previous_energy
        if change > 0 and random.random() >= math.exp(-change/case["temperature"]):
            spins[index] = previous
    return spins
