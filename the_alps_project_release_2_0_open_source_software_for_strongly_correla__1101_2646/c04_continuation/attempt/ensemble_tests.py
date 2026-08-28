from research import *
from continuation import continue_matrix


def run():
    for kind in ['finite','scalarband','band','band2']:
        for seed in range(1,4):
            case = generated(kind,seed,dimension=2+seed%3,error=0 if seed%2 else 2e-13,eta=.06 if seed==3 else .12)
            center = np.mean(case['support'])
            scale = np.diff(case['support'])[0]/2
            identity = np.eye(len(case['bare']))
            moments = [identity,(case['moments'][1]-center*identity)/scale,(case['moments'][2]-2*center*case['moments'][1]+center**2*identity)/scale**2]
            start = time.monotonic()
            prediction = continue_matrix((1j*case['iw']-center)/scale,case['data']*scale,moments,(case['omega']+1j*case['eta']-center)/scale,2e-13*scale,debug=True)/scale
            print('RESULT',kind,seed,metrics(prediction,case),'seconds',time.monotonic()-start,flush=True)


if __name__=='__main__':
    run()
