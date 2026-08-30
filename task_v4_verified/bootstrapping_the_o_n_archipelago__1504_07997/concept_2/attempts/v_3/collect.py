import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
sys.dont_write_bytecode = True
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARTICIPANT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/bootstrapping_the_o_n_archipelago__1504_07997/concept_2/participant')
sys.path.insert(0, str(PARTICIPANT / 'workspace'))
from check import check_case, score

def collect():
    instances = json.loads((PARTICIPANT / 'input/instances.json').read_text())['instances']
    candidates = {instance['id']: [] for instance in instances}
    for path in ROOT.rglob('*.json'):
        try:
            data = json.loads(path.read_text())
            cases = data.get('cases', [data])
            for case in cases:
                if case.get('id') in candidates and 'atoms' in case:
                    candidates[case['id']].append(case)
        except Exception:
            pass
    answer = {'cases': []}
    for instance in instances:
        choices = candidates[instance['id']]
        if choices:
            best = min(choices, key=lambda case: (not check_case(instance, case)[0], check_case(instance, case)[1]))
            answer['cases'].append(best)
    report = score(instances, answer)
    (ROOT / 'answer.json').write_text(json.dumps(answer, indent=2, allow_nan=False) + '\n')
    (ROOT / 'output').mkdir(exist_ok=True)
    (ROOT / 'output/answer.json').write_text(json.dumps(answer, indent=2, allow_nan=False) + '\n')
    (ROOT / 'validation.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report, indent=2), flush=True)
    return report

if __name__ == '__main__':
    collect()
