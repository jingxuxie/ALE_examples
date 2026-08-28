from research import *


def transform(case):
    covariance = hermitian(case['moments'][2]-case['moments'][1]@case['moments'][1])
    eigenvalues, vectors = la.eigh(covariance)
    root = (vectors*np.sqrt(np.maximum(eigenvalues,1e-14)))@vectors.conj().T
    inverse_root = la.inv(root)
    selected = case['iw'] < 20
    points = 1j*case['iw'][selected]
    dimension = len(covariance)
    sigma = points[:,None,None]*np.eye(dimension)-case['moments'][1]-np.linalg.inv(case['data'][selected])
    return points, inverse_root@sigma@inverse_root, root


def mapped(points, support):
    center = np.mean(support)
    radius = (support[1]-support[0])/2
    scaled = (points-center)/radius
    branch = np.sqrt(scaled-1)*np.sqrt(scaled+1)
    coordinate = 1/(scaled+branch)
    return coordinate


def benchmark():
    for kind in ['finite','scalarband','band','band2']:
        case = generated(kind)
        print('\n',kind, flush=True)
        for method in ['sigma','map','sigmamap']:
            root = None
            if method.startswith('sigma'):
                nodes,values,root = transform(case)
            else:
                nodes,values = 1j*case['iw'],case['data']
            target_nodes = case['omega']+1j*case['eta']
            if method.endswith('map'):
                nodes = mapped(nodes,case['support'])
                target_nodes = mapped(target_nodes,case['support'])
                nodes = np.r_[nodes,nodes.conj()]
                values = np.concatenate([values,values.conj().swapaxes(-1,-2)])
            history = aaa(nodes,values,tolerance=1e-12,maximum=23,paired=method.endswith('map'))
            for model in history:
                if len(model[0]) < 8:
                    continue
                prediction = evaluate(model,target_nodes)
                if root is not None:
                    prediction = np.linalg.inv((case['omega']+1j*case['eta'])[:,None,None]*np.eye(len(root))-case['moments'][1]-root@prediction@root)
                print(method,len(model[0]), 'fit %.2g'%model[3], 'metrics', ['%.3g'%value for value in metrics(prediction,case)], flush=True)


if __name__ == '__main__':
    benchmark()
