from research import *
from transform_tests import mapped, transform


def run():
    for kind in ['scalarband','band','band2']:
        case = generated(kind,error=0)
        print('\n',kind,flush=True)
        for method in ['raw','sigma','map','sigmamap','mapdiv','sigmamapdiv']:
            if method.startswith('sigma'):
                nodes,values,root = transform(case)
                rowweight = 1/np.maximum(1,np.abs(nodes)**2)
            else:
                nodes,values = 1j*case['iw'],case['data']
                rowweight = np.ones(len(nodes))
            target_nodes = case['omega']+1j*case['eta']
            factor = np.ones(len(target_nodes))
            if 'map' in method:
                nodes = mapped(nodes,case['support'])
                target_nodes = mapped(target_nodes,case['support'])
                if method.endswith('div'):
                    values = values/nodes[:,None,None]
                    rowweight *= np.abs(nodes)
                    factor = target_nodes
                nodes = np.r_[nodes,nodes.conj()]
                values = np.concatenate([values,values.conj().swapaxes(-1,-2)])
                rowweight = np.tile(rowweight,2)
            history = aaa(nodes,values,tolerance=4e-15,maximum=27,paired='map' in method,rowweight=rowweight)
            for model in history:
                if model[3] > 1e-10:
                    continue
                prediction = evaluate(model,target_nodes)*factor[:,None,None]
                if method.startswith('sigma'):
                    prediction = np.linalg.inv((case['omega']+1j*case['eta'])[:,None,None]*np.eye(len(root))-case['moments'][1]-root@prediction@root)
                print(method,len(model[0]), 'fit %.2g'%model[3], 'metrics', ['%.3g'%value for value in metrics(prediction,case)], flush=True)


if __name__=='__main__':
    run()
