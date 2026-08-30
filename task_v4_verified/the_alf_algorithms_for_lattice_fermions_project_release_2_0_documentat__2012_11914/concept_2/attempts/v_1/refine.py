import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import json
import numpy as np
from search import ROOT, INPUT, FAMILIES, matrices, exact_data, optimize, load, save, evaluate, generate

def tail_gram(instances):
    grams = []
    for instance in instances:
        ham = matrices(instance)
        energies,vectors,eigenlayers,data = exact_data(ham)
        rotated = vectors.conj().T @ ham @ vectors
        triple = np.array([rotated[left]@rotated[middle]@rotated[right]
                          for left in range(5) for middle in range(5) for right in range(5)])
        step,repeat,exact,green,errors = data[-1]
        exponents = -repeat*step*energies
        halfdiff = (exponents[:,None]-exponents[None,:])/2
        midpoints = (exponents[:,None]+exponents[None,:])/2
        divided = np.ones_like(halfdiff)
        np.divide(np.sinh(halfdiff), halfdiff, out=divided, where=np.abs(halfdiff)>1e-14)
        weight = (repeat*step**3*np.exp(midpoints)*divided/errors[0])**2
        flat = triple.reshape(125,-1)
        grams.append(((flat*weight.reshape(-1))@flat.conj().T).real)
    return np.mean(grams,axis=0)

def main():
    word,coeff = load(ROOT/'submission.json')
    save(word,coeff,ROOT/'original_submission.json')
    design = json.loads((ROOT/'design_instances.json').read_text())
    mean = np.load(ROOT/'grams.npz')['grams'].mean(axis=0)
    tail = tail_gram(design)
    np.save(ROOT/'tail_gram.npy',tail)
    validation = json.loads((INPUT/'training_instances.json').read_text())['instances']+generate(60,132659)
    reports = []
    for weight in [0,0.05,0.125,0.25,0.5,1,2]:
        value,values,success = optimize(word,(mean+weight*tail)/(1+weight),coeff,maxiter=300)
        assert success
        path = ROOT/f'refined_{weight}.json'
        save(word,values,path)
        result = evaluate(validation,word,values,verbose=False)
        result.update(weight=weight,file=path.name)
        reports.append(result)
        print(json.dumps(result),flush=True)
    (ROOT/'refinement_report.json').write_text(json.dumps(reports,indent=2)+'\n')

if __name__ == '__main__':
    main()
