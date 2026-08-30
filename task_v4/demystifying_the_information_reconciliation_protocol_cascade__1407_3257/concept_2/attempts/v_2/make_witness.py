import json
from pathlib import Path
import sys


assets = Path('/tmp/cascade-c2-g2-v2-d5teuwjq/participant')
sys.path.insert(0, str(assets / 'workspace'))
from replay import replay

deployment = json.loads((assets / 'input/deployment.json').read_text())
source = Path(sys.argv[1])
core = json.loads(source.read_text())
if isinstance(core, dict):
    core = core['errors']
if not 8 <= len(core) <= 18 or len(core) != len(set(core)):
    raise SystemExit('Invalid core size')
core_set = set(core)
for specification in deployment['passes']:
    permutation = specification['permutation']
    size = specification['block_size']
    for start in range(0, deployment['n'], size):
        assert len(core_set.intersection(permutation[start:start + size])) % 2 == 0
first = deployment['passes'][0]
activators = []
for start in range(0, deployment['n'], first['block_size']):
    block = first['permutation'][start:start + first['block_size']]
    if not core_set.intersection(block):
        activators.append(block[0])
    if len(activators) == 6:
        break
errors = sorted(core + activators)
assert len(errors) <= 24
results = [replay(deployment, errors, priority) for priority in ('earliest', 'shortest')]
for result in results:
    assert result['initial_odd'] >= 6
    assert len(result['corrected']) >= 6
    assert len(result['residual']) >= 8
Path('witness.json').write_text(json.dumps({'errors': errors}) + '\n')
Path('replay_results.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2), flush=True)
