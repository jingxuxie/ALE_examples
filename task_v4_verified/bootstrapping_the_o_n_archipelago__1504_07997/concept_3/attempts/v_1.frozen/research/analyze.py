import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import policy
import numpy as np
from scipy.linalg import cho_factor, cho_solve
from test_policy import summary, generate, Oracle, FAMILIES, SCALES

if __name__ == '__main__':
    results=[json.loads(line) for line in open(sys.argv[1])]
    tail=policy.Tail()
    mean,second,anis=policy.tail_moments(policy.TIMES)
    mass_mean=((2.-.4)/np.log(5)*5+(10.-4)/np.log(2.5))/6
    mass_second=((4.-.16)/(2*np.log(5))*5+(100.-16)/(2*np.log(2.5)))/6
    for result in results:
        instance=generate(result['seed'],result['family'])
        oracle=Oracle(instance,result['seed']+23487213)
        times=np.array([row[0] for row in result['design']])
        angles=np.array([row[1] for row in result['design']])
        indexes=np.argmin(np.abs(times[:,None]-policy.TIMES[None,:]),axis=1)
        values=np.array([oracle.measure(time,[np.cos(angle),np.sin(angle)])['y'] for time,angle in zip(times,angles)])
        features=tail.features(indexes,angles)
        covariance=features@features.T+np.diag(policy.noise_std(times)**2)
        residual=values-policy.predict(result['parameters'],times,angles)-tail.mean[indexes]
        mass_hat=mass_mean+.5*(mass_second-mass_mean**2)*mean[indexes]@cho_solve(cho_factor(covariance),residual)
        result['mass_hat']=float(mass_hat)
        result['mass_true']=float(np.sum(instance.tail_vectors**2)+np.trace(instance.continuum_matrix))
    for family in FAMILIES:
        selected=[result for result in results if result['family']==family]
        ratio=np.array([np.abs(result['error'])/result['radii'] for result in selected])
        masses=np.array([result['mass_hat'] for result in selected])
        print(family,'radius90 factors',np.round(np.quantile(ratio,.9,axis=0),3),'mass',np.round(np.quantile(masses,[.05,.5,.95]),3),'mass_error',np.mean([abs(result['mass_hat']-result['mass_true']) for result in selected]),flush=True)
    for threshold in (2.,2.5,3.,3.5,4.):
        for high_scale in (1.2,1.35,1.5):
            transformed=[]
            for result in results:
                new=dict(result)
                radii=np.array(result['radii'])*(high_scale if result['mass_hat']>threshold else .95)
                error=np.abs(result['error'])
                new['loss']=(.7*error/SCALES+.3*(2*radii+20*np.maximum(error-radii,0))/(4*SCALES)).tolist()
                new['coverage']=(error<=radii).tolist()
                transformed.append(new)
            family_loss=[np.mean([row['loss'] for row in transformed if row['family']==family]) for family in FAMILIES]
            family_coverage=[np.mean([row['coverage'] for row in transformed if row['family']==family]) for family in FAMILIES]
            print('CAL',threshold,high_scale,'robust',round(.35*np.mean(family_loss)+.65*np.max(family_loss),5),'coverage',np.round(family_coverage,3),flush=True)
    with open(sys.argv[1]+'.masses','w') as output:
        for result in results:
            output.write(json.dumps(result)+'\n')
    print('WORST CASES')
    for result in sorted(results,key=lambda row:sum(row['loss']),reverse=True)[:12]:
        print(result['seed'],result['family'],'loss',round(np.mean(result['loss']),4),'error',np.round(result['error'],5),'radius',np.round(result['radii'],5),'cost',round(result['cost'],3),'mass',round(result['mass_hat'],3))
