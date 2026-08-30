import json
import sys
from pathlib import Path


sys.dont_write_bytecode = True
assets = Path('/tmp/cascade-c2-v1-lrzw9x7v/participant')
output = Path(__file__).resolve().parent
sys.path.insert(0, str(assets / 'workspace'))
from replay import replay


deployment = json.loads((assets / 'input/deployment.json').read_text())
core = sorted(json.loads(Path(sys.argv[1]).read_text())['errors'])
assert 8 <= len(core) <= 18
assert len(core) == len(set(core))
core_set = set(core)
for specification in deployment['passes']:
    permutation = specification['permutation']
    block_size = specification['block_size']
    for start in range(0, deployment['n'], block_size):
        assert len(core_set.intersection(permutation[start:start + block_size])) % 2 == 0
first_pass = deployment['passes'][0]
activation = []
for start in range(0, deployment['n'], first_pass['block_size']):
    block = first_pass['permutation'][start:start + first_pass['block_size']]
    if not core_set.intersection(block):
        activation.append(block[0])
    if len(activation) == 6:
        break
assert len(activation) == 6
errors = sorted(core + activation)
assert 1 <= len(errors) <= 24
results = [replay(deployment, errors, priority) for priority in ('earliest', 'shortest')]
for result in results:
    assert result['initial_odd'] >= 6
    assert len(result['corrected']) >= 6
    assert len(result['residual']) >= 8
    assert result['corrected'] == sorted(activation)
    assert result['residual'] == core
(output / 'witness.json').write_text(json.dumps({'errors': errors}) + '\n')
(output / 'validation.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps({'errors': errors, 'core': core, 'activation': activation, 'replay': results}, indent=2))
