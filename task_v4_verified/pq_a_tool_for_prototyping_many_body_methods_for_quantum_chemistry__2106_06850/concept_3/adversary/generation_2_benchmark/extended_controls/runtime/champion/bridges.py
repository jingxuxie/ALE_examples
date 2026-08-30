import argparse
import subprocess
from itertools import combinations
from collections import defaultdict
from continuous import *


def bridges(state, pairs_list):
    support = np.count_nonzero(np.abs(state)>1e-10)
    structures = []
    for label, pairs in enumerate(pairs_list):
        sources, destinations, signs = pairs
        source_present = np.abs(state[sources])>1e-10
        destination_present = np.abs(state[destinations])>1e-10
        both = source_present & destination_present
        singletons = np.count_nonzero(source_present ^ destination_present)
        full = np.flatnonzero(both)
        structures.append((full,singletons))
    result = []
    seen = set()
    for first, first_pairs in enumerate(pairs_list):
        full, singletons = structures[first]
        if singletons or not len(full):
            continue
        coefficients = np.zeros((len(state),3))
        coefficients[:,0] = state
        coefficients[:,2] = state
        sources,destinations,signs = first_pairs
        coefficients[sources,1] = -2*signs*state[destinations]
        coefficients[destinations,1] = 2*signs*state[sources]
        coefficients[sources,2] *= -1
        coefficients[destinations,2] *= -1
        for second, second_pairs in enumerate(pairs_list):
            if first == second:
                continue
            full,singletons = structures[second]
            if len(full)-singletons < 2:
                continue
            sources,destinations,signs = second_pairs
            for left,right in combinations(full,2):
                polynomial = signs[right]*np.convolve(coefficients[sources[left]],coefficients[destinations[right]])-signs[left]*np.convolve(coefficients[destinations[left]],coefficients[sources[right]])
                scale = np.max(np.abs(polynomial))
                if scale<1e-13:
                    continue
                polynomial /= scale
                polynomial[np.abs(polynomial)<1e-12] = 0
                roots = np.roots(np.trim_zeros(polynomial,'b')[::-1])
                for root in roots:
                    if abs(root.imag)>1e-7:
                        continue
                    angle = 2*math.atan(float(root.real))
                    if abs(angle)<1e-7 or abs(angle)>math.pi/2-1e-7:
                        continue
                    key = first,second,round(angle,7)
                    if key in seen:
                        continue
                    seen.add(key)
                    intermediate = apply_rotation(state, first_pairs, angle)
                    theta = math.remainder(math.atan2(-signs[left]*intermediate[destinations[left]],intermediate[sources[left]]),math.pi/2)
                    if abs(theta)<1e-7:
                        continue
                    for alternate in [theta, theta-math.copysign(math.pi/2,theta)]:
                        candidate = apply_rotation(intermediate, second_pairs, alternate)
                        new_support = np.count_nonzero(np.abs(candidate)>1e-8)
                        if new_support>support-2:
                            continue
                        entropy = -np.sum(candidate**2*np.log(candidate**2+1e-100))
                        result.append((new_support,entropy,first,angle,second,alternate,candidate))
    return sorted(result,key=lambda entry:entry[:2])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--depths',default='10,9,11,8,12,7,6')
    parser.add_argument('--limit',type=int,default=100)
    args = parser.parse_args()
    case = load_cases()[0]
    labels = allowed_excitations(case.n_orbitals)
    pairs = [rotation_pairs(case.n_orbitals,case.n_electrons,label) for label in labels]
    seed = json.loads(Path('seed104.json').read_text())
    lines = Path(case.case_id+'.dat').read_text().splitlines()
    alpha_mask = sum(1<<orbital for orbital in range(0,case.n_orbitals,2))
    keep = [index for index,mask in enumerate(case.determinants) if (mask&alpha_mask).bit_count()==case.n_alpha]
    trial = 0
    for depth in map(int,args.depths.split(',')):
        state = case.target.copy()
        prefix = seed['reverse'][:depth]
        for label,theta in prefix:
            state = apply_rotation(state,pairs[label],theta)
        started = time.perf_counter()
        options = bridges(state,pairs)
        print('DEPTH',depth,'support',np.count_nonzero(abs(state)>1e-10),'options',len(options),'seconds',time.perf_counter()-started,flush=True)
        print('TOP',[(entry[:6]) for entry in options[:10]],flush=True)
        for entry in options[:args.limit]:
            new_support,entropy,first,angle,second,theta,candidate = entry
            budget = case.max_gates-depth-2
            if new_support>2**budget:
                continue
            trial += 1
            header = lines[0].split()
            header[2] = str(budget)
            Path('bridge.dat').write_text(' '.join(header)+'\n'+' '.join(map(repr,candidate[keep].tolist()))+'\n'+'\n'.join(lines[2:])+'\n')
            completed = subprocess.run(['./beam3','bridge','2000','80','0.1','4'],capture_output=True,text=True)
            if completed.returncode==0:
                solution = json.loads(Path('bridge.reverse.json').read_text())
                solution['reverse'] = prefix+[[first,angle],[second,theta]]+solution['reverse']
                gates = from_reverse(case,solution)
                fidelity = squared_overlap(case.target,circuit_state(case,gates))
                print('SOLVED',trial,'fidelity',fidelity,'gates',len(gates),flush=True)
                if fidelity>0.999999999 and len(gates)<=case.max_gates:
                    Path(case.case_id+'.reverse.json').write_text(json.dumps(solution)+'\n')
                    return
            if trial%10==0:
                print('TRIAL',trial,'depth',depth,'last',completed.stdout.splitlines()[-1:] ,flush=True)


if __name__=='__main__':
    main()
