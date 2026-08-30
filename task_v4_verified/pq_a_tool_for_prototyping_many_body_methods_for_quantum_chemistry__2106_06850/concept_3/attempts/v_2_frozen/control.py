import argparse
import time
import numpy as np
from scipy.linalg import eigh
from scipy.optimize import minimize
import fermion
from search import Engine


class Control:
    def __init__(self, engine, length, active=None, fixed_labels=None):
        self.engine = engine
        self.length = length
        self.active = np.ones(length,dtype=bool) if active is None else np.asarray(active,dtype=bool)
        self.fixed_labels = fixed_labels
        self.generators = np.zeros((250,100,100))
        starts, sources, destinations, signs = engine.arrays
        for label in range(250):
            selected = slice(starts[label],starts[label+1])
            self.generators[label,destinations[selected],sources[selected]] = signs[selected]
            self.generators[label,sources[selected],destinations[selected]] = -signs[selected]
        self.flat = self.generators.reshape(250,-1)

    def evaluate(self, parameters, penalty=0, epsilon=0.003, old_penalty=0):
        controls = parameters.reshape(self.length,250)
        matrices = (controls @ self.flat).reshape(self.length,100,100)
        history = [self.engine.initial]
        decompositions = []
        for position,matrix in enumerate(matrices):
            if not self.active[position]:
                label=int(self.fixed_labels[position])
                angle=controls[position,label]
                starts,sources,destinations,signs=self.engine.arrays
                selected=slice(starts[label],starts[label+1])
                source,destination,sign=sources[selected],destinations[selected],signs[selected]
                state=history[-1].copy()
                first,second=state[source].copy(),state[destination].copy()
                state[source]=np.cos(angle)*first-sign*np.sin(angle)*second
                state[destination]=sign*np.sin(angle)*first+np.cos(angle)*second
                history.append(state)
                decompositions.append((None,label,angle,(source,destination,sign)))
                continue
            frequencies, vectors = eigh(1j * matrix,check_finite=False,driver='evr')
            phases = np.exp(-1j * frequencies)
            coordinates = vectors.conj().T @ history[-1]
            history.append((vectors @ (phases * coordinates)).real)
            decompositions.append((frequencies,vectors,phases,coordinates))
        overlap = self.engine.target @ history[-1]
        adjoint = -self.engine.target.copy()
        matrix_gradients = np.zeros_like(matrices)
        direct_gradient=np.zeros_like(controls)
        for position in range(self.length-1,-1,-1):
            frequencies,vectors,phases,coordinates = decompositions[position]
            if frequencies is None:
                label,angle=vectors,phases
                source,destination,sign=coordinates
                state=history[position+1]
                direct_gradient[position,label]=np.sum(sign*(state[source]*adjoint[destination]-state[destination]*adjoint[source]))
                first,second=adjoint[source].copy(),adjoint[destination].copy()
                adjoint[source]=np.cos(angle)*first+sign*np.sin(angle)*second
                adjoint[destination]=-sign*np.sin(angle)*first+np.cos(angle)*second
                continue
            backward = vectors.conj().T @ adjoint
            divided = np.exp(-0.5j * (frequencies[:,None]+frequencies[None,:])) * np.sinc((frequencies[:,None]-frequencies[None,:])/(2*np.pi))
            transformed = backward.conj()[:,None] * divided * coordinates[None,:]
            matrix_gradients[position] = (vectors.conj() @ transformed @ vectors.T).real
            adjoint = (vectors @ (phases.conj() * backward)).real
        gradient = (matrix_gradients.reshape(self.length,-1) @ self.flat.T)+direct_gradient
        absolute = np.sqrt(controls*controls + epsilon*epsilon)
        norm = np.sqrt(np.sum(controls*controls,axis=1,keepdims=True)+epsilon*epsilon)
        regularization = np.sum(absolute[self.active]) - 249*np.count_nonzero(self.active)*epsilon - np.sum(norm[self.active])
        gradient[self.active] += penalty * (controls/absolute-controls/norm)[self.active]
        bias=0.0
        if old_penalty:
            positions=np.flatnonzero(self.active)
            old_values=controls[positions,self.fixed_labels[positions]]
            old_absolute=np.sqrt(old_values*old_values+epsilon*epsilon)
            bias=old_penalty*np.sum(old_absolute-epsilon)
            gradient[positions,self.fixed_labels[positions]]+=old_penalty*old_values/old_absolute
        return 1-overlap+penalty*regularization+bias, gradient.ravel(), overlap, regularization


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int, default=0)
    parser.add_argument('--iterations', type=int, default=200)
    parser.add_argument('--cold', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--seed', type=int, default=365)
    args = parser.parse_args()
    engine = Engine(fermion.load_cases()[args.case])
    labels, angles, loss = engine.load()
    engine.best = loss
    rng = np.random.default_rng(args.seed)
    controls = np.zeros((engine.case.max_gates,250))
    controls[np.arange(len(labels)),labels]=angles
    if args.cold:
        controls=rng.normal(0,0.02,size=controls.shape)
    control = Control(engine,len(labels))
    parameters = controls.ravel()
    if args.check:
        parameters = rng.normal(0,0.01,size=parameters.shape)
        value,gradient,overlap,reg = control.evaluate(parameters,0.02)
        print('initial',value,'elapsed',time.time()-engine.started,flush=True)
        for position in [0,55,420,855,1580]:
            changed=parameters.copy();changed[position]+=1e-6
            value_plus=control.evaluate(changed,0.02)[0]
            changed[position]-=2e-6
            value_minus=control.evaluate(changed,0.02)[0]
            print('gradient',position,gradient[position],(value_plus-value_minus)/2e-6,flush=True)
        return
    for penalty in [0.00001,0.0001,0.001,0.005,0.02,0.1]:
        calls=0
        def objective(values):
            nonlocal calls
            result=control.evaluate(values,penalty)
            calls+=1
            if calls%100==0:
                print('eval',calls,'penalty',penalty,'overlap',result[2],'reg',result[3],'elapsed',time.time()-engine.started,flush=True)
            return result[:2]
        result=minimize(objective,parameters,jac=True,method='L-BFGS-B',options={'maxiter':args.iterations,'ftol':1e-11,'gtol':1e-7,'maxcor':10,'maxls':30})
        parameters=result.x
        controls=parameters.reshape(len(labels),250)
        labels=np.argmax(abs(controls),axis=1).astype(np.int32)
        chosen_angles=controls[np.arange(len(labels)),labels]
        saved_target=engine.target.copy()
        found=engine.optimize(labels,chosen_angles,400)
        engine.target=saved_target
        engine.save(*found)
        print('penalty done',penalty,'loss',result.fun,'hard',found[2],'elapsed',time.time()-engine.started,flush=True)
        np.save(engine.case.case_id+'_controls.npy',parameters)


if __name__=='__main__':
    main()
