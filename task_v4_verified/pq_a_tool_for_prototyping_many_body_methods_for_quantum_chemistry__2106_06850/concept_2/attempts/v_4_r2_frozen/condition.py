import inverse
from search import np, oracle, basis, free, axes
from api import robust_screen
import json
from pathlib import Path

source=json.loads(Path('quiet_multi0q5.json').read_text())
coordinates=np.einsum('kij,ij->k',axes,np.array(source['pair_matrix']))
result=oracle.solve(free+np.einsum('k,kij->ij',coordinates,basis),source['amplitudes'])
multipliers,_,_=oracle.lambda_state(result)
kinematic=np.r_[result.amplitudes,multipliers]
for number,gap in enumerate([.15,.25,.4,.6]):
    coordinates=inverse.design(kinematic,f'condition{number}',coordinates,gap=gap)
    interaction=np.einsum('k,kij->ij',coordinates,axes)
    report=robust_screen(interaction,result.amplitudes,check_paths=False)
    Path(f'condition{number}.screen.json').write_text(json.dumps(report,indent=2))
    print('SCREEN',number,{key:value for key,value in report.items() if key not in ['points','adaptive_response']},flush=True)
