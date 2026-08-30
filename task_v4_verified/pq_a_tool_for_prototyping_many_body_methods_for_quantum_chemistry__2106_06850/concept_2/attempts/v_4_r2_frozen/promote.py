import argparse
import json
import time
from pathlib import Path
import numpy as np
from api import artifact,robust_screen,CONSTRAINTS
from adaptive import energy_error_gradient
from oracle import DeterminantCC

def promote(filename,center=True):
    source=json.loads(Path(filename).read_text())
    matrix=np.array(source['pair_matrix'])
    oracle=DeterminantCC()
    hamiltonian=oracle.hamiltonian(CONSTRAINTS['orbital_energies'],matrix)[0]
    result=oracle.solve(hamiltonian,source['amplitudes'])
    if center:
        for iteration in range(4):
            response=energy_error_gradient(matrix,result.amplitudes,oracle)
            direction=np.array(response['direction'])
            errors=[]
            for sign in (1,-1):
                perturbed=oracle.hamiltonian(CONSTRAINTS['orbital_energies'],matrix+sign*.001*direction)[0]
                neighbor=oracle.solve(perturbed,result.amplitudes,tolerance=2e-11)
                errors.append(neighbor.energy-np.linalg.eigvalsh(perturbed)[0])
            bias=sum(errors)/2
            print('CENTER',iteration,errors,'bias',bias,flush=True)
            if abs(bias)<1e-13:break
            step=np.clip(bias/response['norm'],-.0005,.0005)
            matrix=matrix-step*direction
            hamiltonian=oracle.hamiltonian(CONSTRAINTS['orbital_energies'],matrix)[0]
            result=oracle.solve(hamiltonian,result.amplitudes,tolerance=2e-11)
    candidate=artifact(matrix,result.amplitudes)
    output=Path(filename).with_name(Path(filename).stem+'_centered.json')
    output.write_text(json.dumps(candidate,indent=2))
    started=time.time()
    report=robust_screen(matrix,result.amplitudes,oracle)
    output.with_suffix('.validation.json').write_text(json.dumps(report,indent=2))
    print('REPORT',filename,{key:value for key,value in report.items() if key not in ['points','adaptive_response']},'seconds',time.time()-started,flush=True)
    failed=[point for point in report.get('points',[]) if point['failures']]
    print('FAILED',len(failed),failed[:12],flush=True)
    previous=json.loads(Path('submission.validation.json').read_text()) if Path('submission.validation.json').exists() else {'core_score':0}
    if report.get('core_score',0)>previous.get('core_score',0):
        Path('submission.json').write_text(json.dumps(candidate,indent=2))
        Path('submission.validation.json').write_text(json.dumps(report,indent=2))
        print('PROMOTED',report['core_score'],flush=True)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('filename')
    arguments=parser.parse_args()
    promote(arguments.filename)
