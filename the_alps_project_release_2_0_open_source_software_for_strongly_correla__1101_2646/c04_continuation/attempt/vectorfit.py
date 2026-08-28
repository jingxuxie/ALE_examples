from research import *


def fit_residues(nodes, values, roots, moments, rowweight=None):
    dimension = values.shape[-1]
    values = values.reshape(len(nodes),-1)
    if rowweight is None:
        rowweight = np.ones(len(nodes))
    basis = 1/(nodes[:,None]-roots)
    if len(moments):
        constraints = np.array([roots**order for order in range(len(moments))])
        constant = np.array(moments).reshape(len(moments),-1)
        particular = la.lstsq(constraints, constant, lapack_driver='gelsy')[0]
        nullspace = la.null_space(constraints)
        coefficients = la.lstsq((basis@nullspace)*rowweight[:,None],(values-basis@particular)*rowweight[:,None], lapack_driver='gelsy')[0]
        residues = particular + nullspace@coefficients
    else:
        residues = la.lstsq(basis*rowweight[:,None],values*rowweight[:,None], lapack_driver='gelsy')[0]
    fitted = basis@residues
    return residues.reshape(-1,dimension,dimension),np.max(la.norm(fitted-values,axis=1)*rowweight)


def vectorfit(nodes, values, roots, moments, rowweight=None, iterations=8):
    dimension = values.shape[-1]
    values = values.reshape(len(nodes),-1)
    if rowweight is None:
        rowweight = np.ones(len(nodes))
    moments = np.array(moments).reshape(len(moments),-1)
    outputs = []
    for iteration in range(iterations):
        basis = 1/(nodes[:,None]-roots)
        constraint_weight = 10
        constraints = np.array([roots**order for order in range(len(moments))])*constraint_weight
        extended_basis = np.r_[basis*rowweight[:,None],constraints]
        orthogonal,triangular = la.qr(extended_basis, mode='economic')
        system = []
        targets = []
        for channel in range(values.shape[1]):
            denominator_basis = -values[:,channel,None]*basis*rowweight[:,None]
            constraint_basis = np.zeros((len(moments),len(roots)), complex)
            for order in range(1,len(moments)):
                for degree in range(order):
                    constraint_basis[order] -= moments[order-degree-1,channel]*roots**degree*constraint_weight
            denominator_basis = np.r_[denominator_basis,constraint_basis]
            target = np.r_[values[:,channel]*rowweight,moments[:,channel]*constraint_weight]
            system.append(denominator_basis-orthogonal@(orthogonal.conj().T@denominator_basis))
            targets.append(target-orthogonal@(orthogonal.conj().T@target))
        system = np.concatenate(system)
        targets = np.concatenate(targets)
        scales = la.norm(system,axis=0)
        coefficients = la.lstsq(system/scales,targets,cond=1e-13,lapack_driver='gelsy')[0]/scales
        new_roots = la.eigvals(np.diag(roots)-np.ones((len(roots),1))*coefficients)
        roots = new_roots.real - 1j*np.abs(new_roots.imag)
        residues,error = fit_residues(nodes,values.reshape(-1,dimension,dimension),roots,moments.reshape(-1,dimension,dimension),rowweight)
        outputs.append((roots.copy(),residues,error))
    return outputs


def benchmark():
    from transform_tests import transform
    for kind in ['finite','scalarband','band','band2']:
        case = generated(kind)
        print('\n',kind,flush=True)
        for method in ['raw','sigma']:
            if method == 'raw':
                nodes,values = 1j*case['iw'],case['data']
                rowweight = np.ones(len(nodes))
                moments = case['moments']
            else:
                nodes,values,root = transform(case)
                rowweight = 1/np.maximum(1,np.abs(nodes)**2)
                moments = [np.eye(values.shape[-1])]
            history = aaa(nodes,values,tolerance=1e-12,maximum=22,rowweight=rowweight)
            for model in history[-3:]:
                print(method,len(model[0]),'aaa fit',model[3],flush=True)
                for index,(roots,residues,error) in enumerate(vectorfit(nodes,values,poles(model),moments,rowweight)):
                    prediction = green_from_spectrum(case['omega']+1j*case['eta'],roots,residues)
                    if method == 'sigma':
                        prediction = np.linalg.inv((case['omega']+1j*case['eta'])[:,None,None]*np.eye(len(root))-case['moments'][1]-root@prediction@root)
                    print(index,'fit %.3g'%error,'metrics', ['%.3g'%value for value in metrics(prediction,case)],flush=True)


if __name__=='__main__':
    benchmark()
