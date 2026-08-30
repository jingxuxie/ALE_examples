import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import ctypes
import json
import math
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize, least_squares
from fermion import load_cases, allowed_excitations, rotation_pairs, reference_state, circuit_state, squared_overlap

ROOT = Path(__file__).resolve().parent
LIB = ctypes.CDLL(str(ROOT / 'engine.so'))
INTS = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
FLOATS = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
LIB.setup.argtypes = [ctypes.c_int] * 3 + [INTS] * 3 + [FLOATS] * 3
LIB.forward.argtypes = [ctypes.c_int, INTS, FLOATS, FLOATS]
LIB.fungrad.argtypes = [ctypes.c_int, INTS, FLOATS, FLOATS]
LIB.fungrad.restype = ctypes.c_double
LIB.residual_jac.argtypes = [ctypes.c_int, INTS, FLOATS, FLOATS, FLOATS]
LIB.scan.argtypes = [ctypes.c_int, INTS, FLOATS, ctypes.c_int, FLOATS, FLOATS]
LIB.apply.argtypes = [FLOATS, ctypes.c_int, ctypes.c_double]
LIB.entropy_scan.argtypes = [FLOATS, ctypes.c_int, FLOATS, FLOATS]
LIB.insertion_tangents.argtypes = [ctypes.c_int, INTS, FLOATS, FLOATS]

class Engine:
    def __init__(self, case_index):
        self.case_index = case_index
        self.case = load_cases()[case_index]
        self.labels = allowed_excitations(self.case.n_orbitals)
        self.keep = np.array([index for index, mask in enumerate(self.case.determinants) if (mask & 341).bit_count() == self.case.n_alpha])
        self.dimension = len(self.keep)
        lookup = {index: reduced for reduced, index in enumerate(self.keep)}
        pairs = []
        for label in self.labels:
            full = rotation_pairs(self.case.n_orbitals, self.case.n_electrons, label)
            selected = [(lookup[source], lookup[destination], sign) for source, destination, sign in zip(*full) if source in lookup]
            pairs.append(selected)
        self.width = max(map(len, pairs))
        self.sources = np.zeros((250, self.width), dtype=np.int32)
        self.destinations = np.zeros_like(self.sources)
        self.signs = np.zeros((250, self.width))
        self.lengths = np.array(list(map(len, pairs)), dtype=np.int32)
        for label, selected in enumerate(pairs):
            for position, (source, destination, sign) in enumerate(selected):
                self.sources[label, position] = source
                self.destinations[label, position] = destination
                self.signs[label, position] = sign
        self.reference = reference_state(self.case)[self.keep].copy()
        self.target = self.case.target[self.keep].copy()
        self.setup()
        self.best = float('inf')
        self.started = time.time()

    def setup(self, reference=None, target=None):
        if reference is not None:
            self.reference = np.ascontiguousarray(reference)
        if target is not None:
            self.target = np.ascontiguousarray(target)
        LIB.setup(self.dimension, 250, self.width, self.lengths, self.sources, self.destinations, self.signs, self.reference, self.target)

    def state(self, labels, angles):
        result = np.empty(self.dimension)
        LIB.forward(len(labels), np.asarray(labels, dtype=np.int32), np.asarray(angles, dtype=float), result)
        return result

    def apply(self, state, label, angle):
        result = state.copy()
        LIB.apply(result, int(label), float(angle))
        return result

    def optimize(self, labels, angles, iterations=160, precise=False):
        labels = np.asarray(labels, dtype=np.int32)
        angles = np.asarray(angles, dtype=float)
        if not len(labels):
            return 0.5*np.sum((self.reference-self.target)**2), angles
        gradient = np.empty(len(labels))
        def objective(parameters):
            value = LIB.fungrad(len(labels), labels, parameters, gradient)
            return value, gradient.copy()
        result = minimize(objective, angles, jac=True, method='L-BFGS-B', options={'maxiter': iterations, 'ftol': 1e-14, 'gtol': 1e-10, 'maxls': 25, 'maxcor': 30})
        if precise or result.fun < 1e-6:
            residual = np.empty(self.dimension)
            jacobian = np.empty((self.dimension, len(labels)))
            cached = None
            def update(parameters):
                nonlocal cached
                if cached is None or not np.array_equal(parameters, cached):
                    LIB.residual_jac(len(labels), labels, parameters, residual, jacobian)
                    cached = parameters.copy()
            def fun(parameters):
                update(parameters)
                return residual.copy()
            def jac(parameters):
                update(parameters)
                return jacobian.copy()
            refined = least_squares(fun, result.x, jac=jac, method='lm' if len(labels) <= self.dimension else 'trf', ftol=2e-14, xtol=2e-14, gtol=2e-14, max_nfev=iterations)
            if refined.cost < result.fun:
                return refined.cost, (refined.x + np.pi) % (2*np.pi) - np.pi
        return float(result.fun), (result.x + np.pi) % (2*np.pi) - np.pi

    def scan(self, labels, angles, replacement=False):
        count = len(labels) + 1 - int(replacement)
        values = np.empty((count,250))
        best_angles = np.empty_like(values)
        LIB.scan(len(labels), np.asarray(labels,dtype=np.int32), np.asarray(angles,dtype=float), int(replacement), values, best_angles)
        return values, best_angles

    def save(self, labels, angles, value, tag='best'):
        if tag == 'best' and (ROOT / f'best_{self.case_index}.json').exists():
            old_labels, old_angles = self.load()
            old_value = 0.5 * np.sum((self.state(old_labels,old_angles)-self.target)**2)
            self.best = min(self.best,old_value)
        if value >= self.best and tag == 'best':
            return
        if tag == 'best':
            self.best = value
        payload = {'case_id': self.case.case_id, 'gates': [{'annihilate':list(self.labels[int(label)].annihilate), 'create':list(self.labels[int(label)].create), 'theta':float((angle+np.pi)%(2*np.pi)-np.pi)} for label,angle in zip(labels,angles)]}
        destination = ROOT / f'{tag}_{self.case_index}.json'
        temporary = ROOT / f'.{tag}_{self.case_index}_{os.getpid()}.json'
        temporary.write_text(json.dumps(payload))
        os.replace(temporary,destination)
        print('SAVE',self.case_index, tag, 'gates',len(labels),'loss',value,'seconds',time.time()-self.started,flush=True)

    def load(self, tag='best'):
        payload = json.loads((ROOT/f'{tag}_{self.case_index}.json').read_text())
        lookup = {(label.annihilate,label.create):index for index,label in enumerate(self.labels)}
        labels = [lookup[(tuple(gate['annihilate']),tuple(gate['create']))] for gate in payload['gates']]
        return labels, np.array([gate['theta'] for gate in payload['gates']])

def grow(engine, rng, mode='insert', beam=1):
    labels, angles = [], np.zeros(0)
    for depth in range(engine.case.max_gates):
        values, guesses = engine.scan(labels,angles)
        if mode == 'append':
            values[:-1] = np.inf
        elif mode == 'prepend':
            values[1:] = np.inf
        picks = np.argsort(values,axis=None)[:max(beam,1)]
        best = None
        for pick in picks:
            position,label = np.unravel_index(pick,values.shape)
            proposal = labels[:position] + [int(label)] + labels[position:]
            parameters = np.insert(angles,position,guesses[position,label])
            value,parameters = engine.optimize(proposal,parameters)
            if best is None or value < best[0]:
                best = value,proposal,parameters
        value,labels,angles = best
        print('GROW',engine.case_index,depth+1,value,flush=True)
    engine.save(labels,angles,value)
    return value,labels,angles

def search(engine, rng, seconds, mode):
    value,labels,angles = grow(engine,rng,mode)
    deadline = time.time()+seconds
    best_value,best_labels,best_angles = value,labels.copy(),angles.copy()
    iteration = 0
    stagnation = 0
    while time.time() < deadline and best_value > 1e-11:
        values,guesses = engine.scan(labels,angles,replacement=True)
        order = np.argsort(values,axis=None)
        picks = [int(pick) for pick in order if labels[pick//250] != pick%250]
        proposals = []
        for pick in picks[:12 if stagnation < 4 else 4]:
            position,label = divmod(pick,250)
            proposal = labels.copy(); proposal[position]=label
            parameters=angles.copy(); parameters[position]=guesses[position,label]
            loss,parameters=engine.optimize(proposal,parameters,iterations=120)
            proposals.append((loss,proposal,parameters))
        loss,proposal,parameters=min(proposals,key=lambda item:item[0])
        if loss < value-1e-10:
            value,labels,angles=loss,proposal,parameters
            stagnation=0
        else:
            stagnation+=1
            labels=best_labels.copy(); angles=best_angles.copy(); value=best_value
            count = 1 + min(4,stagnation//5)
            for position in rng.choice(len(labels),size=count,replace=False):
                if rng.random()<0.5:
                    new_position=int(rng.integers(len(labels)))
                    label=labels.pop(position); angle=angles[position]; angles=np.delete(angles,position)
                    labels.insert(new_position,label); angles=np.insert(angles,new_position,angle)
                else:
                    labels[position]=int(rng.integers(250)); angles[position]=rng.uniform(-1,1)
            value,angles=engine.optimize(labels,angles,iterations=200)
        if value < best_value:
            best_value,best_labels,best_angles=value,labels.copy(),angles.copy()
            engine.save(labels,angles,value)
        iteration+=1
        if iteration%10==0:
            print('ITER',engine.case_index,iteration,'current',value,'best',best_value,'stagnation',stagnation,flush=True)

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--seconds',type=int,default=600)
    parser.add_argument('--seed',type=int,default=10)
    parser.add_argument('--mode',default='insert')
    arguments=parser.parse_args()
    search(Engine(arguments.case),np.random.default_rng(arguments.seed),arguments.seconds,arguments.mode)
