import csv
import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
solution = ROOT / 'concept_01/solution'
manifest = ROOT / 'concept_01/participant/v_01/input/campaign.json'
scaling = []
for variant, config in [('primary', 'config.json'), ('ablation', 'ablation_config.json'), ('refinement', 'refinement_config.json')]:
    output = solution / 'experiments' / variant
    subprocess.run(['bash', str(solution / 'run.sh'), str(manifest), str(output), str(solution / config)], check=True)
    with open(output / 'scaling.csv') as stream:
        scaling.extend([dict(row, variant=variant) for row in csv.DictReader(stream)])
shutil.copyfile(solution / 'experiments/primary/results.csv', solution / 'results.csv')
shutil.copyfile(solution / 'experiments/ablation/results.csv', solution / 'ablation.csv')
with open(solution / 'scaling.csv', 'w') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(scaling[0]))
    writer.writeheader()
    writer.writerows(scaling)
primary = list(csv.DictReader(open(solution / 'results.csv')))
ablation = list(csv.DictReader(open(solution / 'ablation.csv')))
refinement = list(csv.DictReader(open(solution / 'experiments/refinement/results.csv')))


def last(rows, case):
    return [row for row in rows if row['case'] == case][-1]


vacancy = last(primary, 'vacancy')
cluster = last(primary, 'cluster')
fine = last(refinement, 'vacancy')
coarse_graph = last(ablation, 'vacancy')
claims = [dict(id='intervention_order', statement='The measured vacancy minus cluster far-bin correlation quantifies the intervention hierarchy within this finite observation window.', evidence=[dict(table='results.csv', case='vacancy', frame=int(vacancy['frame']), column='g6_far'), dict(table='results.csv', case='cluster', frame=int(cluster['frame']), column='g6_far')], comparison='difference', value=float(vacancy['g6_far']) - float(cluster['g6_far'])), dict(id='temporal_sensitivity', statement='The primary/finer-step vacancy compressible-energy ratio measures numerical sensitivity; a value near unity supports temporal convergence of this diagnostic.', evidence=[dict(table='results.csv', case='vacancy', frame=int(vacancy['frame']), column='Ec'), dict(table='experiments/refinement/results.csv', case='vacancy', frame=int(fine['frame']), column='Ec')], comparison='ratio', value=float(vacancy['Ec']) / float(fine['Ec'])), dict(id='guard_bias', statement='Cropping away guard vortices before constructing neighborhoods changes the apparent number of fivefold bulk cores.', evidence=[dict(table='ablation.csv', case='vacancy', frame=int(coarse_graph['frame']), column='n5'), dict(table='results.csv', case='vacancy', frame=int(vacancy['frame']), column='n5')], comparison='difference', value=float(coarse_graph['n5']) - float(vacancy['n5']))]
claims[2]['statement'] = 'Cropping away guard vortices before constructing neighborhoods changes the apparent number of sixfold bulk cores.'
for evidence in claims[2]['evidence']:
    evidence['column'] = 'n6'
claims[2]['value'] = float(coarse_graph['n6']) - float(vacancy['n6'])
(solution / 'claims.json').write_text(json.dumps(claims, indent=2))
subprocess.run(['python', str(solution / 'workspace/render.py'), str(solution)], check=True)
print(json.dumps({'claims': claims, 'endpoints': {case: last(primary, case) for case in ['control', 'vacancy', 'reverse', 'cluster']}}, indent=2))
