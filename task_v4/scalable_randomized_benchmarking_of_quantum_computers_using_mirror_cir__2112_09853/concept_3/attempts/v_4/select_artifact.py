import json
import pathlib
import subprocess
import sys

participant = pathlib.Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/scalable_randomized_benchmarking_of_quantum_computers_using_mirror_cir__2112_09853/concept_3/participant')
sys.path.insert(0, str(participant))
from reference_core import validate_submission

spec = json.loads((participant / 'input/spec.json').read_text())
families = {family['id']: (index, family) for index, family in enumerate(spec['families'])}
words = ['I', 'H', 'S', 'HS', 'SH', 'HSH']
base = json.loads(pathlib.Path('artifact.json').read_text())
best = {}
records = {}
for path in sorted(pathlib.Path('.').glob('*.json')):
    try:
        circuit = json.loads(path.read_text())
        if set(circuit) != {'family', 'layers'} or circuit['family'] not in families:
            continue
        family_id = circuit['family']
        index, family = families[family_id]
        validation = {'schema_version': 1, 'circuits': [circuit if entry['family'] == family_id else entry for entry in base['circuits']]}
        validate_submission(validation, spec)
        text = [f"{family['n']} {len(circuit['layers'])}"]
        for layer in circuit['layers']:
            values = [words.index(word) for word in layer['local']]
            values.append(len(layer['cx']))
            values.extend(qubit for gate in layer['cx'] for qubit in gate)
            text.append(' '.join(map(str, values)))
        pathlib.Path('assess_input.txt').write_text('\n'.join(text) + '\n')
        report = json.loads(subprocess.check_output(['./assess', str(index), 'assess_input.txt'], text=True))
        rank = (report['core_score'], report['ideal_score'], -report['critical'], -report['ordinary'])
        records[str(path)] = report
        if family_id not in best or rank > best[family_id][0]:
            best[family_id] = (rank, circuit, str(path), report)
            print(family_id, str(path), report, flush=True)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print('skip', str(path), str(error), file=sys.stderr)

if len(best) == len(families):
    artifact = {'schema_version': 1, 'circuits': [best[family['id']][1] for family in spec['families']]}
    validate_submission(artifact, spec)
    pathlib.Path('artifact.json').write_text(json.dumps(artifact, indent=2) + '\n')
    pathlib.Path('selection.json').write_text(json.dumps({key: {'source': value[2], **value[3]} for key, value in best.items()}, indent=2) + '\n')
pathlib.Path('candidate_scores.json').write_text(json.dumps(records, indent=2) + '\n')
