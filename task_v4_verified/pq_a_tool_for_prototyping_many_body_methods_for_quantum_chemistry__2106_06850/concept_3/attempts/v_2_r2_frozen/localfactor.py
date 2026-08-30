from synth import *
from reverse import entropy_optimize
from scipy.optimize import linear_sum_assignment

def tensor_maps(engine):
    submasks=[mask for mask in range(32) if mask.bit_count()==engine.case.n_alpha]
    rows=[];cols=[];signs=[]
    for index in engine.keep:
        mask=engine.case.determinants[index]
        alpha=sum(1<<(orbital//2) for orbital in range(0,10,2) if mask>>orbital&1)
        beta=sum(1<<(orbital//2) for orbital in range(1,10,2) if mask>>orbital&1)
        sign=(-1)**sum(bool(mask>>alpha_orbital&1 and mask>>beta_orbital&1) for alpha_orbital in range(0,10,2) for beta_orbital in range(1,alpha_orbital,2))
        rows.append(submasks.index(alpha));cols.append(submasks.index(beta));signs.append(sign)
    return np.array(rows),np.array(cols),np.array(signs)

def run(case_index,seed):
    engine=Engine(case_index)
    rng=np.random.default_rng(seed)
    rows,cols,signs=tensor_maps(engine)
    tensor=np.zeros((10,10));tensor[rows,cols]=engine.target*signs
    left,singular,right=np.linalg.svd(tensor)
    allowed=[index for index,label in enumerate(engine.labels) if all(orbital%2==0 for orbital in label.annihilate+label.create)]
    for side,unitary in enumerate((left,right.T)):
        reference=unitary[rows,cols]*signs/np.sqrt(10)
        engine.setup(reference=reference)
        best=1.0
        for trial in range(8):
            labels=[];angles=np.zeros(0);state=reference.copy()
            for depth in range(20):
                gains=np.empty(250);guesses=np.empty(250)
                LIB.fourth_scan(state,gains,guesses)
                order=sorted(allowed,key=lambda label:-gains[label])
                chosen=order[int(rng.integers(3)) if depth<4 and trial>0 else 0]
                labels.append(chosen);angles=np.append(angles,guesses[chosen])
                value,angles=entropy_optimize(labels,angles,iterations=300)
                state=engine.state(labels,angles)
                matrix=np.zeros((10,10));matrix[rows,cols]=state*signs*np.sqrt(10)
                selected_rows,selected_cols=linear_sum_assignment(-abs(matrix))
                permutation=np.zeros((10,10));permutation[selected_rows,selected_cols]=np.sign(matrix[selected_rows,selected_cols])
                endpoint=permutation[rows,cols]*signs/np.sqrt(10)
                error=0.5*np.sum((state-endpoint)**2)
                if depth in (5,7,9,11,15,19) or error<1e-8:
                    print('LOCAL',case_index,side,trial,depth+1,error,'fourth',np.sum(state**4),time.time()-engine.started,flush=True)
                if error<1e-8:
                    engine.setup(target=endpoint)
                    error,angles=engine.optimize(labels,angles,iterations=600,precise=True)
                    payload={'case':case_index,'side':side,'labels':labels,'angles':angles.tolist(),'permutation':permutation.tolist(),'loss':error,'singular':singular.tolist()}
                    (ROOT/f'local_{case_index}_{side}_{seed}.json').write_text(json.dumps(payload))
                    break

if __name__=='__main__':
    import sys
    run(int(sys.argv[1]),int(sys.argv[2]))
