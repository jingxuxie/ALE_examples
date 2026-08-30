import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import argparse
import ctypes
import json
import time
from pathlib import Path
import numpy as np
from scipy.linalg import eigh
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent.parent / 'participant' / 'input'
NAMES = ['X0', 'X1', 'Y0', 'Y1', 'V']
SPEC = json.loads((INPUT / 'spec.json').read_text())
FAMILIES = [family['name'] for family in SPEC['sampling']['families']]
LIB = ctypes.CDLL(str(ROOT / 'poly.so'))
LIB.polynomial.argtypes = [np.ctypeslib.ndpointer(np.int32, flags='C_CONTIGUOUS'),
    np.ctypeslib.ndpointer(np.float64, flags='C_CONTIGUOUS'),
    np.ctypeslib.ndpointer(np.float64, flags='C_CONTIGUOUS'),
    np.ctypeslib.ndpointer(np.float64, flags='C_CONTIGUOUS')]

def polynomial(word, half):
    cubic = np.empty(125)
    jac = np.empty((125, 17))
    LIB.polynomial(np.asarray(word, dtype=np.int32), np.asarray(half, dtype=np.float64), cubic, jac)
    return cubic, jac

def baseline():
    word, coeff = [], []
    for repeat in range(4):
        for position, comp in enumerate([0,1,2,3,4,3,2,1,0]):
            value = 0.25 if position == 4 else 0.125
            if word and word[-1] == comp:
                coeff[-1] += value
            else:
                word.append(comp)
                coeff.append(value)
    return np.array(word[:17], dtype=np.int32), np.array(coeff[:17])

def matrices(instance):
    size = np.prod(instance['shape'])
    ham = np.zeros((5,size,size), dtype=np.complex128)
    for component, source, target, amplitude, phase in instance['bonds']:
        comp = NAMES.index(component)
        ham[comp,source,target] = -amplitude*np.exp(1j*phase)
        ham[comp,target,source] = ham[comp,source,target].conjugate()
    ham[4] = np.diag(instance['site_potential'])
    return ham

def generate(count, seed):
    rng = np.random.default_rng(seed)
    instances = []
    for family in SPEC['sampling']['families']:
        for number in range(count):
            shape = SPEC['sampling']['lattice_shapes'][number%3]
            width, height = shape
            hopping_x = rng.uniform(*family['tx'])
            if family.get('ty') == 'tx':
                hopping_y = hopping_x
            elif 'ty_ratio' in family:
                hopping_y = hopping_x*rng.uniform(*family['ty_ratio'])
                if rng.random() < family['swap_axes_probability']:
                    hopping_x, hopping_y = hopping_y, hopping_x
            else:
                hopping_y = rng.uniform(*family['ty'])
            dimer_x, dimer_y = rng.uniform(*family['dx']), rng.uniform(*family['dy'])
            field = rng.uniform(*family['field_strength'])
            stagger = rng.uniform(*family['stagger'])
            chemical = rng.uniform(*family['chemical_potential'])
            bonds, potential = [], []
            for coord_y in range(height):
                for coord_x in range(width):
                    source = coord_x+width*coord_y
                    for component, target, hopping, dimer, coord in [
                        (NAMES[coord_x%2], (coord_x+1)%width+width*coord_y, hopping_x,dimer_x,coord_x),
                        (NAMES[2+coord_y%2], coord_x+width*((coord_y+1)%height), hopping_y,dimer_y,coord_y)]:
                        amplitude = hopping*(1+dimer*(-1)**coord)*rng.uniform(1-family['disorder'],1+family['disorder'])
                        phase = rng.uniform(-family['phase_width'], family['phase_width'])
                        bonds.append([component,source,target,amplitude,phase])
                    field_value = rng.choice([-1,1]) if family['field'] == 'binary' else np.clip(rng.normal(),-2,2)
                    potential.append(field*field_value+stagger*(-1)**(coord_x+coord_y)-chemical)
            instances.append(dict(id=family['name']+f'_generated_{number}',family=family['name'],shape=shape,bonds=bonds,site_potential=potential))
    return instances

def product(ham, word, half, step, eigens=None):
    if eigens is None:
        eigens = [eigh(component) for component in ham]
    result = np.eye(ham.shape[1], dtype=np.complex128)
    for index in list(range(17))+list(range(15,-1,-1)):
        values, vectors = eigens[word[index]]
        exponential = (vectors*np.exp(-step*half[index]*values)) @ vectors.conj().T
        result = result @ exponential
    return result

def exact_data(ham):
    energies, vectors = eigh(ham.sum(axis=0))
    eigenlayers = [eigh(component) for component in ham]
    baseword, basecoeff = baseline()
    data = []
    for step in SPEC['sampling']['dtau']:
        base = product(ham,baseword,basecoeff,step,eigenlayers)
        for repeat in SPEC['sampling']['repetitions']:
            exact_values = np.exp(-repeat*step*energies)
            exact = (vectors*exact_values)@vectors.conj().T
            green = (vectors/(1+exact_values))@vectors.conj().T
            basepower = np.linalg.matrix_power(base,repeat)
            basegreen = np.linalg.inv(np.eye(len(energies))+basepower)
            errors = [np.linalg.norm(basepower-exact), np.linalg.norm(basegreen-green)]
            data.append((step,repeat,exact,green,errors))
    return energies,vectors,eigenlayers,data

def build_grams(instances):
    grams, labels = [], []
    for number, instance in enumerate(instances):
        ham = matrices(instance)
        energies,vectors,eigenlayers,data = exact_data(ham)
        rotated = vectors.conj().T @ ham @ vectors
        triple = np.array([rotated[left]@rotated[middle]@rotated[right]
                          for left in range(5) for middle in range(5) for right in range(5)])
        weight = np.zeros_like(ham[0].real)
        for step,repeat,exact,green,errors in data:
            exponents = -repeat*step*energies
            differences = exponents[:,None]-exponents[None,:]
            midpoints = (exponents[:,None]+exponents[None,:])/2
            halfdiff = differences/2
            divided = np.ones_like(halfdiff)
            np.divide(np.sinh(halfdiff), halfdiff, out=divided, where=np.abs(halfdiff)>1e-14)
            frechet = repeat*step**3*np.exp(midpoints)*divided
            greens = 1/(1+np.exp(exponents))
            weight += (frechet/errors[0])**2
            weight += (frechet*greens[:,None]*greens[None,:]/errors[1])**2
        flat = triple.reshape(125,-1)
        gram = ((flat*weight.reshape(-1))@flat.conj().T).real/16
        grams.append(gram)
        labels.append(FAMILIES.index(instance['family']))
        if number%20 == 0:
            print('gram',number,'/',len(instances),flush=True)
    return np.array(grams),np.array(labels)

def evaluate(instances, word, coeff, verbose=True):
    ratios = [[] for family in FAMILIES]
    worst = (0,None)
    for instance in instances:
        ham = matrices(instance)
        energies,vectors,eigenlayers,data = exact_data(ham)
        family = FAMILIES.index(instance['family'])
        products = {step:product(ham,word,coeff,step,eigenlayers) for step in SPEC['sampling']['dtau']}
        for step,repeat,exact,green,errors in data:
            power = np.linalg.matrix_power(products[step],repeat)
            approx_green = np.linalg.inv(np.eye(len(energies))+power)
            point = [np.linalg.norm(power-exact)/errors[0],np.linalg.norm(approx_green-green)/errors[1]]
            ratios[family].extend(point)
            if max(point)>worst[0]:
                worst = (max(point),(instance['id'],step,repeat,point))
    scores = [1/np.sqrt(np.mean(np.square(points))) for points in ratios]
    result = dict(scores=dict(zip(FAMILIES,scores)),core=float(np.prod(scores)**0.25),worst_family=min(scores),max_ratio=worst[0],worst_point=worst[1])
    if verbose:
        print(json.dumps(result,indent=2),flush=True)
    return result

def save(word, coeff, path):
    stages = [dict(component=NAMES[word[index]],coefficient=float(coeff[index]))
              for index in list(range(17))+list(range(15,-1,-1))]
    path.write_text(json.dumps(dict(schema_version=1,stages=stages),indent=2)+'\n')

def load(path):
    stages = json.loads(path.read_text())['stages'][:17]
    return np.array([NAMES.index(stage['component']) for stage in stages],dtype=np.int32),np.array([stage['coefficient'] for stage in stages])

def optimize(word, gram, initial=None, maxiter=120):
    word = np.asarray(word,dtype=np.int32)
    if set(word)!=set(range(5)) or np.any(word[1:]==word[:-1]):
        return None
    constraint = np.zeros((5,17))
    for index,comp in enumerate(word):
        constraint[comp,index] = 2 if index<16 else 1
    if initial is None:
        initial = 1/constraint.sum(axis=1)[word]
    else:
        initial = initial/(constraint@initial)[word]
    def objective(half):
        cubic,jac = polynomial(word,half)
        weighted = gram@cubic
        return cubic@weighted, 2*jac.T@weighted
    result = minimize(objective,initial,jac=True,method='SLSQP',bounds=[(1.000001e-5,1)]*17,
        constraints={'type':'eq','fun':lambda half:constraint@half-1,'jac':lambda half:constraint},
        options={'maxiter':maxiter,'ftol':1e-10})
    return result.fun,result.x,result.success

def search(grams, labels, seconds, seed):
    rng = np.random.default_rng(seed)
    gram = np.mean([grams[labels==family].mean(axis=0) for family in range(4)],axis=0)
    start = time.time()
    word,coeff = baseline()
    if (ROOT/'best.json').exists():
        word,coeff = load(ROOT/'best.json')
    score,coeff,success = optimize(word,gram,coeff)
    best = score
    population = [(score,word.copy(),coeff.copy())]
    seen = set()
    attempts = 0
    while time.time()-start<seconds:
        attempts += 1
        if attempts%40 == 0:
            candidate = rng.integers(0,5,size=17,dtype=np.int32)
            initial = None
        else:
            parent = population[min(int(rng.exponential(3)),len(population)-1)]
            candidate = parent[1].copy()
            initial = parent[2].copy()
            moves = rng.choice([1,2,3,5],p=[.55,.3,.1,.05])
            for move in range(moves):
                operation = rng.integers(0,4)
                left,right = sorted(rng.choice(17,2,replace=False))
                if operation == 0:
                    candidate[left],candidate[right] = candidate[right],candidate[left]
                    initial[left],initial[right] = initial[right],initial[left]
                elif operation == 1:
                    candidate[left] = rng.integers(5)
                elif operation == 2:
                    candidate[left:right+1] = candidate[left:right+1][::-1]
                    initial[left:right+1] = initial[left:right+1][::-1]
                else:
                    candidate[left:right+1] = np.roll(candidate[left:right+1],1)
                    initial[left:right+1] = np.roll(initial[left:right+1],1)
        key = tuple(candidate)
        if key in seen:
            continue
        seen.add(key)
        result = optimize(candidate,gram,initial)
        if result is None:
            continue
        value,values,success = result
        if not success or not np.isfinite(value):
            continue
        if value<best:
            best=value
            save(candidate,values,ROOT/'best.json')
            cubic,_ = polynomial(candidate,values)
            family_scores = [1/np.sqrt(cubic@grams[labels==family].mean(axis=0)@cubic) for family in range(4)]
            print('BEST',attempts,'time',round(time.time()-start,1),'objective',value,'scores',family_scores,'word',candidate.tolist(),flush=True)
        if len(population)<30 or value<population[-1][0]:
            population.append((value,candidate.copy(),values.copy()))
            population.sort(key=lambda entry:entry[0])
            population = population[:30]
        if attempts%100 == 0:
            print('progress',attempts,round(time.time()-start,1),'best',best,'pool',population[-1][0],flush=True)
    np.savez(ROOT/'population.npz',words=np.array([entry[1] for entry in population]),coefficients=np.array([entry[2] for entry in population]),values=np.array([entry[0] for entry in population]))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',choices=['prepare','search','evaluate'])
    parser.add_argument('--seconds',type=int,default=600)
    parser.add_argument('--seed',type=int,default=142)
    parser.add_argument('--count',type=int,default=24)
    parser.add_argument('--file',default='best.json')
    args = parser.parse_args()
    training = json.loads((INPUT/'training_instances.json').read_text())['instances']
    if args.mode == 'prepare':
        instances = training+generate(args.count,args.seed)
        (ROOT/'design_instances.json').write_text(json.dumps(instances))
        grams,labels = build_grams(instances)
        np.savez(ROOT/'grams.npz',grams=grams,labels=labels)
        word,coeff = baseline()
        cubic,_ = polynomial(word,coeff)
        print('baseline approximation',[cubic@grams[labels==family].mean(axis=0)@cubic for family in range(4)],flush=True)
        save(word,coeff,ROOT/'submission.json')
    elif args.mode == 'search':
        cache = np.load(ROOT/'grams.npz')
        search(cache['grams'],cache['labels'],args.seconds,args.seed)
    else:
        word,coeff = load(ROOT/args.file)
        print('TRAINING',flush=True)
        evaluate(training,word,coeff)
        print('INDEPENDENT GENERATED',flush=True)
        evaluate(generate(args.count,args.seed),word,coeff)

if __name__ == '__main__':
    main()
