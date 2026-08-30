import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent / 'participant' / 'workspace'))
from simulator import simulate, training_scenarios

def decode(values, name):
    return {'name': name, 'gain_a': float(values[0]), 'gain_b': float(values[1]),
            'zz_common': float(values[2]), 'zz_local': values[3:15].tolist(),
            'z_drift_radians_per_layer': values[15:].tolist()}

def main():
    artifact = ROOT / 'pulses.json'
    contents = artifact.read_bytes()
    payload = json.loads(contents)
    assert not artifact.is_symlink() and len(contents) <= 65536
    assert set(payload) == {'schema_version', 'angles'}
    assert type(payload['schema_version']) is int and payload['schema_version'] == 1
    assert len(payload['angles']) == 24 and all(len(layer) == 2 for layer in payload['angles'])
    assert all(type(value) in (int,float) for layer in payload['angles'] for value in layer)
    angles = np.array(payload['angles'])
    assert angles.shape == (24,2) and np.all(np.isfinite(angles)) and np.max(np.abs(angles)) <= np.pi
    groups = {'public': training_scenarios()}
    if (ROOT/'stress_scenarios.json').exists():
        groups['generated_stress'] = json.loads((ROOT/'stress_scenarios.json').read_text())['scenarios']
    generator = np.random.default_rng(781920443)
    bounds = np.array([.025,.025,.015] + [.005]*12 + [.01]*12)
    random_cases = []
    for index in range(int(os.environ.get('VALIDATION_RANDOM', 2048))):
        values = generator.uniform(-1,1,27) * bounds
        if index % 4 == 0:
            values = generator.choice([-1.,1.],27) * bounds
        elif index % 4 == 1:
            values[:3] = generator.choice([-1.,1.],3)*bounds[:3]
        elif index % 4 == 2:
            values[:3] = generator.choice([-1.,1.],3)*bounds[:3]
            values[3:15] = generator.choice([-1.,1.])*.005
        random_cases.append(decode(values, f'independent_random_{index}'))
    groups['independent_random'] = random_cases
    report = {'artifact_valid': True, 'artifact_sha256': hashlib.sha256(contents).hexdigest(),
              'note': 'Public and independently generated checks only; the private frozen suite is unavailable.',
              'groups': {}}
    started = time.time()
    for name, scenarios in groups.items():
        all_scores = []
        norm_error = 0.
        parity_error = 0.
        for offset in range(0,len(scenarios),32):
            batch = scenarios[offset:offset+32]
            states = simulate(angles,batch)
            all_scores.extend((np.abs((states[:,0]+states[:,-1])/np.sqrt(2))**2).tolist())
            norm_error = max(norm_error,float(np.max(np.abs(np.sum(np.abs(states)**2,axis=1)-1))))
            for scenario, state in zip(batch,states):
                if not np.any(scenario['z_drift_radians_per_layer']):
                    parity_error = max(parity_error,float(np.max(np.abs(state-state[::-1]))))
        worst = int(np.argmin(all_scores))
        summary = {'count':len(scenarios), 'minimum_fidelity':min(all_scores),
                   'mean_fidelity':float(np.mean(all_scores)), 'maximum_norm_error':norm_error,
                   'maximum_zero_drift_parity_error':parity_error,
                   'worst_scenario':scenarios[worst]}
        if name == 'public':
            summary['fidelities'] = all_scores
        report['groups'][name] = summary
        print(name, 'count',len(scenarios),'min',min(all_scores),'norm error',norm_error,'seconds',time.time()-started,flush=True)
    report['minimum_checked_fidelity'] = min(summary['minimum_fidelity'] for summary in report['groups'].values())
    report['runtime_seconds'] = time.time()-started
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__ == '__main__':
    main()
